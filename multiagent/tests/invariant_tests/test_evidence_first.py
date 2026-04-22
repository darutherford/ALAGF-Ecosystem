"""Invariant 3 (Evidence-First) acceptance tests.

Every ledger event produced by Sprint-1 carries a causal chain pointer:
    - AGENT_REGISTERED references the session_id and auditor_id.
    - AGENT_SUSPENDED references the ledger event ID of the prior
      AGENT_REGISTERED via causal_refs.prior_event_id AND the payload's
      prior_registration_event_id.
    - AGENT_REVOKED references the prior AGENT_REGISTERED identically.

Sprint-2 extensions:
    - AGENT_HANDOFF references registered source_agent_id and target_agent_id.
    - Cross-session handoffs are rejected with CROSS_SESSION.
    - Handoffs involving a SUSPENDED agent are rejected with the appropriate
      *_INACTIVE reason.
    - Handoffs whose payload_artifact_id is not discoverable are rejected
      with UNKNOWN_PAYLOAD.
"""

from __future__ import annotations

import pytest

from multiagent.exceptions import BoundaryViolationError, HandshakeError
from multiagent.ledger.hash_chain.events import read_session_events
from multiagent.orchestrator.agent_lifecycle.registration import (
    register_agent,
    revoke_agent,
    suspend_agent,
)
from multiagent.orchestrator.boundary_enforcement import (
    emit_handoff,
    emit_handshake,
)


def test_agent_registered_carries_auditor_and_session(
    session_id: str, auditor_id: str
) -> None:
    register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    events = read_session_events(session_id)
    assert len(events) == 1
    evt = events[0]
    assert evt["event_type"] == "AGENT_REGISTERED"
    assert evt["auditor_id"] == auditor_id
    assert evt["session_id"] == session_id
    assert evt["actor"]["actor_type"] == "HUMAN"
    assert evt["actor"]["actor_id"] == auditor_id


def test_agent_suspended_references_prior_registration(
    session_id: str, auditor_id: str
) -> None:
    record = register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    registration_event_id = record["_registration_event_id"]

    suspend_agent(
        agent_id=record["agent_id"],
        auditor_id=auditor_id,
        reason="acceptance test",
    )

    events = read_session_events(session_id)
    suspended = next(e for e in events if e["event_type"] == "AGENT_SUSPENDED")

    # Envelope-level causal ref.
    assert suspended["causal_refs"]["prior_event_id"] == registration_event_id
    assert suspended["causal_refs"]["referenced_event_id"] == registration_event_id
    # Payload-level ref for redundant traceability.
    assert (
        suspended["payload"]["prior_registration_event_id"]
        == registration_event_id
    )


def test_agent_revoked_references_prior_registration(
    session_id: str, auditor_id: str
) -> None:
    record = register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    registration_event_id = record["_registration_event_id"]

    revoke_agent(
        agent_id=record["agent_id"],
        auditor_id=auditor_id,
        reason="acceptance test",
    )

    events = read_session_events(session_id)
    revoked = next(e for e in events if e["event_type"] == "AGENT_REVOKED")
    assert revoked["causal_refs"]["prior_event_id"] == registration_event_id
    assert revoked["payload"]["prior_registration_event_id"] == registration_event_id


# ---------------------------------------------------------------------------
# Sprint-2 extensions: handoff evidence chains
# ---------------------------------------------------------------------------


def _register_orchestrator(session_id: str, auditor_id: str) -> dict:
    return register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )


def _register_sub_agent(session_id: str, auditor_id: str, parent_id: str) -> dict:
    return register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=parent_id,
    )


def test_handoff_references_registered_source_and_target(
    session_id: str, auditor_id: str
) -> None:
    orch = _register_orchestrator(session_id, auditor_id)
    sub = _register_sub_agent(session_id, auditor_id, orch["agent_id"])

    event = emit_handoff(
        session_id=session_id,
        auditor_id=auditor_id,
        source_agent_id=orch["agent_id"],
        target_agent_id=sub["agent_id"],
        payload_artifact_id=sub["agent_id"],  # registry-path discoverable
    )
    assert event["event_type"] == "AGENT_HANDOFF"
    handoff = event["payload"]["agent_handoff"]
    assert handoff["source_agent_id"] == orch["agent_id"]
    assert handoff["target_agent_id"] == sub["agent_id"]
    assert handoff["non_authoritative_flag"] is True


def test_handoff_rejects_cross_session(session_id: str, auditor_id: str) -> None:
    """Agents registered in different sessions cannot participate in the same handoff."""
    orch_a = _register_orchestrator(session_id, auditor_id)
    other_session = "SESSION_99999999"
    orch_b = _register_orchestrator(other_session, auditor_id)

    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=orch_a["agent_id"],
            target_agent_id=orch_b["agent_id"],
            payload_artifact_id=orch_a["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert len(violations) == 1
    assert violations[0]["payload"]["rejection_reason"] == "CROSS_SESSION"


def test_handoff_to_suspended_agent_is_rejected(
    session_id: str, auditor_id: str
) -> None:
    orch = _register_orchestrator(session_id, auditor_id)
    sub = _register_sub_agent(session_id, auditor_id, orch["agent_id"])
    suspend_agent(agent_id=sub["agent_id"], auditor_id=auditor_id, reason="test")

    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=orch["agent_id"],
            target_agent_id=sub["agent_id"],
            payload_artifact_id=sub["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert violations[-1]["payload"]["rejection_reason"] == "TARGET_INACTIVE"


def test_handoff_from_revoked_agent_is_rejected(
    session_id: str, auditor_id: str
) -> None:
    orch = _register_orchestrator(session_id, auditor_id)
    sub = _register_sub_agent(session_id, auditor_id, orch["agent_id"])
    revoke_agent(agent_id=sub["agent_id"], auditor_id=auditor_id, reason="test")

    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=sub["agent_id"],  # revoked
            target_agent_id=orch["agent_id"],
            payload_artifact_id=orch["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert violations[-1]["payload"]["rejection_reason"] == "SOURCE_INACTIVE"


def test_handoff_rejects_unknown_payload(
    session_id: str, auditor_id: str
) -> None:
    orch = _register_orchestrator(session_id, auditor_id)
    sub = _register_sub_agent(session_id, auditor_id, orch["agent_id"])

    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=orch["agent_id"],
            target_agent_id=sub["agent_id"],
            payload_artifact_id="GHOST_ARTIFACT_0001",
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert violations[-1]["payload"]["rejection_reason"] == "UNKNOWN_PAYLOAD"
