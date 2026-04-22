"""Invariant 4 (Reconstructability) acceptance tests.

The ledger alone must enable full causal reconstruction of every session
event. Silent failures are prohibited; every error condition produces a
ledger event.

Sprint-1 tests:
    - Given only the ledger, reconstruct the set of ACTIVE agents for a
      session at any point in time.
    - UNREGISTERED_AGENT_OUTPUT is emitted BEFORE the exception is raised.
    - The hash chain is verified on replay; tampering is detected.

Sprint-2 extensions:
    - Given only the ledger, reconstruct the full handoff chain for a
      session, tracing payload_artifact_id flow through source/target pairs.
    - BOUNDARY_VIOLATION events are emitted BEFORE BoundaryViolationError or
      HandshakeError is raised (no silent failure).
    - Hash chain integrity verifies across mixed event types
      (AGENT_REGISTERED, BOUNDARY_HANDSHAKE, AGENT_HANDOFF).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from multiagent.exceptions import (
    BoundaryViolationError,
    HandshakeError,
    LedgerIntegrityError,
    UnregisteredAgentError,
)
from multiagent.ledger.hash_chain.events import read_session_events
from multiagent.orchestrator.agent_lifecycle.registration import (
    register_agent,
    reject_unregistered_output,
    revoke_agent,
    suspend_agent,
)
from multiagent.orchestrator.boundary_enforcement import (
    emit_handoff,
    emit_handshake,
)


def _reconstruct_active_at_end(events: list[dict]) -> set[str]:
    """Pure-ledger reconstruction: derive ACTIVE agent_ids from events only.

    Governance rationale: the registry files are a convenience index, not the
    source of truth. If the test can reconstruct the ACTIVE set using only
    events, Invariant 4 holds.
    """
    status_by_agent: dict[str, str] = {}
    for e in events:
        if e["event_type"] == "AGENT_REGISTERED":
            agent_id = e["payload"]["agent_identity"]["agent_id"]
            status_by_agent[agent_id] = "ACTIVE"
        elif e["event_type"] == "AGENT_SUSPENDED":
            status_by_agent[e["payload"]["agent_id"]] = "SUSPENDED"
        elif e["event_type"] == "AGENT_REVOKED":
            status_by_agent[e["payload"]["agent_id"]] = "REVOKED"
    return {a for a, s in status_by_agent.items() if s == "ACTIVE"}


def test_ledger_alone_reconstructs_active_set(
    session_id: str, auditor_id: str
) -> None:
    a = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=2,
    )
    b = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=a["agent_id"],
    )
    c = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=a["agent_id"],
    )
    suspend_agent(agent_id=b["agent_id"], auditor_id=auditor_id, reason="test")
    revoke_agent(agent_id=c["agent_id"], auditor_id=auditor_id, reason="test")

    events = read_session_events(session_id)
    active = _reconstruct_active_at_end(events)
    assert active == {a["agent_id"]}


def test_unregistered_output_emits_event_before_rejection(
    session_id: str, auditor_id: str
) -> None:
    """No silent failure. The event must be written BEFORE the exception."""
    with pytest.raises(UnregisteredAgentError):
        reject_unregistered_output(
            session_id=session_id,
            auditor_id=auditor_id,
            attempted_agent_id="AGT_ghostghost01",
            artifact_type="Observation",
        )
    events = read_session_events(session_id)
    assert len(events) == 1
    evt = events[0]
    assert evt["event_type"] == "UNREGISTERED_AGENT_OUTPUT"
    assert evt["payload"]["attempted_agent_id"] == "AGT_ghostghost01"
    assert evt["payload"]["rejection_reason"] == "NOT_REGISTERED"


def test_hash_chain_detects_tampering(
    session_id: str, auditor_id: str
) -> None:
    """Mutate a committed event file; replay must raise LedgerIntegrityError."""
    record = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    suspend_agent(
        agent_id=record["agent_id"], auditor_id=auditor_id, reason="for tamper"
    )

    # Locate and mutate the first event file.
    ledger_root = (
        Path(__file__).resolve().parent.parent.parent
        / "ledger"
        / "hash_chain"
        / "sessions"
        / session_id
    )
    first_file = sorted(
        p for p in ledger_root.iterdir()
        if p.name.endswith(".json") and not p.name.startswith("_")
    )[0]
    with first_file.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    # Tamper with the payload.
    data["payload"]["agent_identity"]["trust_tier"] = "T4"
    with first_file.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, sort_keys=True, indent=2)

    with pytest.raises(LedgerIntegrityError):
        read_session_events(session_id)


def test_hash_chain_verifies_clean_replay(
    session_id: str, auditor_id: str
) -> None:
    """Sanity: untampered replay succeeds and returns events in order."""
    record = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    suspend_agent(
        agent_id=record["agent_id"], auditor_id=auditor_id, reason="ok"
    )
    events = read_session_events(session_id)
    assert [e["sequence_number"] for e in events] == [1, 2]
    assert events[0]["prev_hash"] is None
    assert events[1]["prev_hash"] == events[0]["event_hash"]


# ---------------------------------------------------------------------------
# Sprint-2 extensions: handoff-chain reconstruction and mixed hash chain
# ---------------------------------------------------------------------------


def _reconstruct_handoff_chain(events: list[dict]) -> list[tuple[str, str, str]]:
    """Pure-ledger derivation of the handoff chain as (source, target, payload)."""
    chain: list[tuple[str, str, str]] = []
    for e in events:
        if e["event_type"] != "AGENT_HANDOFF":
            continue
        h = e["payload"]["agent_handoff"]
        chain.append(
            (h["source_agent_id"], h["target_agent_id"], h["payload_artifact_id"])
        )
    return chain


def test_ledger_alone_reconstructs_handoff_chain(
    session_id: str, auditor_id: str
) -> None:
    """Given only the event log, reconstruct the full sequence of handoffs."""
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )
    sub_a = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    sub_b = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )

    # Orchestrator to sub_a (no handshake required).
    emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=orch["agent_id"], target_agent_id=sub_a["agent_id"],
        payload_artifact_id=sub_a["agent_id"],
    )
    # Peer handshake, then peer handoff.
    emit_handshake(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
    )
    emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
        payload_artifact_id=orch["agent_id"],  # arbitrary registered payload
    )

    events = read_session_events(session_id)
    chain = _reconstruct_handoff_chain(events)
    assert chain == [
        (orch["agent_id"], sub_a["agent_id"], sub_a["agent_id"]),
        (sub_a["agent_id"], sub_b["agent_id"], orch["agent_id"]),
    ]


def test_boundary_violation_emitted_before_exception(
    session_id: str, auditor_id: str
) -> None:
    """No silent failure. BOUNDARY_VIOLATION must be written BEFORE the raise."""
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=orch["agent_id"],
            target_agent_id="AGT_ghostghost01",  # unregistered target
            payload_artifact_id=orch["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert len(violations) == 1
    assert violations[0]["payload"]["rejection_reason"] == "TARGET_UNREGISTERED"


def test_handshake_error_emitted_before_exception(
    session_id: str, auditor_id: str
) -> None:
    """Peer handoff without prior handshake: event emitted BEFORE HandshakeError."""
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )
    sub_a = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    sub_b = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    with pytest.raises(HandshakeError):
        emit_handoff(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
            payload_artifact_id=orch["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert len(violations) == 1
    assert violations[0]["payload"]["rejection_reason"] == "MISSING_HANDSHAKE"


def test_hash_chain_integrity_across_mixed_event_types(
    session_id: str, auditor_id: str
) -> None:
    """Replay verifies across AGENT_REGISTERED, BOUNDARY_HANDSHAKE, AGENT_HANDOFF."""
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )
    sub_a = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    sub_b = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    emit_handshake(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
    )
    emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
        payload_artifact_id=orch["agent_id"],
    )

    events = read_session_events(session_id)
    # Expect 3 AGENT_REGISTERED, 1 BOUNDARY_HANDSHAKE, 1 AGENT_HANDOFF = 5 events.
    assert len(events) == 5
    types = [e["event_type"] for e in events]
    assert "BOUNDARY_HANDSHAKE" in types
    assert "AGENT_HANDOFF" in types
    # Each event's prev_hash chains to the previous event's event_hash.
    for i in range(1, len(events)):
        assert events[i]["prev_hash"] == events[i - 1]["event_hash"]


def test_tampered_handoff_event_detected(
    session_id: str, auditor_id: str
) -> None:
    """Mutate a committed AGENT_HANDOFF file; replay must raise LedgerIntegrityError."""
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=2,
    )
    sub = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=orch["agent_id"], target_agent_id=sub["agent_id"],
        payload_artifact_id=sub["agent_id"],
    )

    ledger_root = (
        Path(__file__).resolve().parent.parent.parent
        / "ledger" / "hash_chain" / "sessions" / session_id
    )
    files = sorted(
        p for p in ledger_root.iterdir()
        if p.name.endswith(".json") and not p.name.startswith("_")
    )
    handoff_file = next(
        p for p in files
        if json.loads(p.read_text())["event_type"] == "AGENT_HANDOFF"
    )
    data = json.loads(handoff_file.read_text())
    data["payload"]["agent_handoff"]["target_agent_id"] = "AGT_tampered0001"
    handoff_file.write_text(json.dumps(data, sort_keys=True, indent=2))

    with pytest.raises(LedgerIntegrityError):
        read_session_events(session_id)
