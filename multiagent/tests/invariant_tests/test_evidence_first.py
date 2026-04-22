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

Sprint-3 extensions:
    - HYPOTHESIS_REGISTERED carries the Hypothesis artifact with
      synthesis_depth, upstream_hypothesis_refs, observation_refs
      (minItems: 1), and composite_upstream_bme_score.
    - Upstream refs must resolve to prior HYPOTHESIS_REGISTERED events
      in the same session; unresolved refs raise UpstreamResolutionError.
    - Self-reference in upstream_hypothesis_refs is rejected by the factory
      (and architecturally impossible at emission time: the artifact_id
      is generated during build, so a caller cannot pre-supply it in the
      refs list without triggering UpstreamResolutionError at resolve time).
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


# ---------------------------------------------------------------------------
# Sprint-3 extensions: Hypothesis evidence chains
# ---------------------------------------------------------------------------

from multiagent.orchestrator.synthesis.fs_adapter import FsLedger
from multiagent.orchestrator.synthesis.fs_agent_registry import FsAgentRegistry
from multiagent.orchestrator.synthesis.hypothesis import (
    UpstreamResolutionError,
    emit_hypothesis,
)


def _emit_hyp(
    ledger, registry, session_id, auditor_id, agent, upstream=None,
    observation_refs=None,
):
    return emit_hypothesis(
        session_id=session_id,
        source_agent_id=agent,
        observation_refs=observation_refs or ["OBS_000000000001"],
        upstream_hypothesis_refs=upstream or [],
        composite_upstream_bme_score=0.1,
        auditor_id=auditor_id,
        registry=registry,
        ledger=ledger,
        ledger_writer=ledger,
    )


def test_hypothesis_registered_carries_provenance(
    session_id: str, auditor_id: str
) -> None:
    """HYPOTHESIS_REGISTERED payload carries synthesis_depth,
    upstream_hypothesis_refs, observation_refs, and ceiling_attribution."""
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=3,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()
    evt = _emit_hyp(
        ledger, registry, session_id, auditor_id, agent["agent_id"],
        observation_refs=["OBS_111111111111"],
    )
    hyp = evt["payload"]["hypothesis"]
    assert hyp["synthesis_depth"] == 1
    assert hyp["upstream_hypothesis_refs"] == []
    assert hyp["observation_refs"] == ["OBS_111111111111"]
    # Governance denormalizations on payload
    assert evt["payload"]["governing_ceiling"] == 3
    assert (
        evt["payload"]["ceiling_attribution"]["binding_agent_id"]
        == agent["agent_id"]
    )
    # Invariant 3: envelope actor carries the AI agent identity
    assert evt["actor"]["actor_type"] == "AGENT"
    assert evt["actor"]["actor_id"] == agent["agent_id"]


def test_hypothesis_upstream_refs_must_resolve(
    session_id: str, auditor_id: str
) -> None:
    """Upstream refs must point to prior HYPOTHESIS_REGISTERED events."""
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=3,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()
    with pytest.raises(UpstreamResolutionError):
        _emit_hyp(
            ledger, registry, session_id, auditor_id, agent["agent_id"],
            upstream=["HYP_" + "9" * 12],
        )


def test_hypothesis_upstream_chain_resolves_correctly(
    session_id: str, auditor_id: str
) -> None:
    """Multi-hop provenance chain resolves through upstream_hypothesis_refs."""
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=5,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()
    h1 = _emit_hyp(
        ledger, registry, session_id, auditor_id, agent["agent_id"]
    )["payload"]["hypothesis"]["artifact_id"]
    h2_evt = _emit_hyp(
        ledger, registry, session_id, auditor_id, agent["agent_id"],
        upstream=[h1],
    )
    h2 = h2_evt["payload"]["hypothesis"]
    assert h2["synthesis_depth"] == 2
    assert h2["upstream_hypothesis_refs"] == [h1]


def test_hypothesis_observation_refs_required(
    session_id: str, auditor_id: str
) -> None:
    """Decision (g-i): every Hypothesis carries observation_refs with
    minItems: 1, regardless of depth."""
    from multiagent.exceptions import ArtifactValidationError

    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=3,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()
    with pytest.raises(ArtifactValidationError):
        emit_hypothesis(
            session_id=session_id,
            source_agent_id=agent["agent_id"],
            observation_refs=[],  # violates minItems: 1
            upstream_hypothesis_refs=[],
            composite_upstream_bme_score=0.1,
            auditor_id=auditor_id,
            registry=registry,
            ledger=ledger,
            ledger_writer=ledger,
        )
