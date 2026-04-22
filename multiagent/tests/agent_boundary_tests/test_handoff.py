"""AgentHandoff boundary enforcement tests.

Scope: the handoff protocol rules defined by Sprint-2 decisions:
    (a) directional handshake enforcement
    (e) VALIDATOR origination restriction
    (f) HUMAN_PROXY origination restriction
    plus self-handoff rejection and orchestrator-involving handshake bypass.
"""

from __future__ import annotations

import pytest

from multiagent.exceptions import BoundaryViolationError, HandshakeError
from multiagent.ledger.hash_chain.events import read_session_events
from multiagent.orchestrator.agent_lifecycle.registration import register_agent
from multiagent.orchestrator.boundary_enforcement import (
    emit_handoff,
    emit_handshake,
)


def _orch(session_id: str, auditor_id: str) -> dict:
    return register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )


def _sub(session_id: str, auditor_id: str, parent_id: str) -> dict:
    return register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=parent_id,
    )


def _validator(session_id: str, auditor_id: str, parent_id: str) -> dict:
    return register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="VALIDATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="OBSERVATIONS_ONLY",
        max_synthesis_depth=0, parent_agent_id=parent_id,
    )


def _human_proxy(session_id: str, auditor_id: str) -> dict:
    return register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="HUMAN_PROXY", model_id="human",
        provider="internal", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=0,
    )


def test_orchestrator_to_sub_agent_no_handshake_required(
    session_id: str, auditor_id: str
) -> None:
    orch = _orch(session_id, auditor_id)
    sub = _sub(session_id, auditor_id, orch["agent_id"])
    event = emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=orch["agent_id"], target_agent_id=sub["agent_id"],
        payload_artifact_id=sub["agent_id"],
    )
    assert event["event_type"] == "AGENT_HANDOFF"


def test_peer_sub_agent_handoff_requires_handshake(
    session_id: str, auditor_id: str
) -> None:
    orch = _orch(session_id, auditor_id)
    sub_a = _sub(session_id, auditor_id, orch["agent_id"])
    sub_b = _sub(session_id, auditor_id, orch["agent_id"])

    with pytest.raises(HandshakeError):
        emit_handoff(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
            payload_artifact_id=orch["agent_id"],
        )


def test_peer_sub_agent_handoff_succeeds_after_handshake(
    session_id: str, auditor_id: str
) -> None:
    orch = _orch(session_id, auditor_id)
    sub_a = _sub(session_id, auditor_id, orch["agent_id"])
    sub_b = _sub(session_id, auditor_id, orch["agent_id"])

    emit_handshake(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
    )
    event = emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
        payload_artifact_id=orch["agent_id"],
    )
    assert event["event_type"] == "AGENT_HANDOFF"


def test_validator_follows_peer_handshake_rule_when_peer(
    session_id: str, auditor_id: str
) -> None:
    """VALIDATOR as handoff target from a SUB_AGENT source requires a handshake."""
    orch = _orch(session_id, auditor_id)
    sub = _sub(session_id, auditor_id, orch["agent_id"])
    val = _validator(session_id, auditor_id, orch["agent_id"])

    with pytest.raises(HandshakeError):
        emit_handoff(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=sub["agent_id"], target_agent_id=val["agent_id"],
            payload_artifact_id=orch["agent_id"],
        )
    emit_handshake(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub["agent_id"], target_agent_id=val["agent_id"],
    )
    event = emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub["agent_id"], target_agent_id=val["agent_id"],
        payload_artifact_id=orch["agent_id"],
    )
    assert event["event_type"] == "AGENT_HANDOFF"


def test_validator_disallowed_originator_to_sub_agent(
    session_id: str, auditor_id: str
) -> None:
    """VALIDATOR may only originate to ORCHESTRATOR or HUMAN_PROXY (decision e)."""
    orch = _orch(session_id, auditor_id)
    sub = _sub(session_id, auditor_id, orch["agent_id"])
    val = _validator(session_id, auditor_id, orch["agent_id"])

    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=val["agent_id"], target_agent_id=sub["agent_id"],
            payload_artifact_id=orch["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert violations[-1]["payload"]["rejection_reason"] == "DISALLOWED_ORIGINATOR_VALIDATOR"


def test_validator_may_originate_to_orchestrator(
    session_id: str, auditor_id: str
) -> None:
    orch = _orch(session_id, auditor_id)
    val = _validator(session_id, auditor_id, orch["agent_id"])
    event = emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=val["agent_id"], target_agent_id=orch["agent_id"],
        payload_artifact_id=val["agent_id"],
    )
    assert event["event_type"] == "AGENT_HANDOFF"


def test_human_proxy_disallowed_originator_to_sub_agent(
    session_id: str, auditor_id: str
) -> None:
    """HUMAN_PROXY may only originate to ORCHESTRATOR (decision f)."""
    orch = _orch(session_id, auditor_id)
    sub = _sub(session_id, auditor_id, orch["agent_id"])
    proxy = _human_proxy(session_id, auditor_id)

    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=proxy["agent_id"], target_agent_id=sub["agent_id"],
            payload_artifact_id=orch["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert violations[-1]["payload"]["rejection_reason"] == "DISALLOWED_ORIGINATOR_HUMAN_PROXY"


def test_human_proxy_may_receive_from_sub_agent(
    session_id: str, auditor_id: str
) -> None:
    """HUMAN_PROXY receives HITL escalations from any active agent without handshake."""
    orch = _orch(session_id, auditor_id)
    sub = _sub(session_id, auditor_id, orch["agent_id"])
    proxy = _human_proxy(session_id, auditor_id)
    event = emit_handoff(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub["agent_id"], target_agent_id=proxy["agent_id"],
        payload_artifact_id=orch["agent_id"],
    )
    assert event["event_type"] == "AGENT_HANDOFF"


def test_self_handoff_rejected(session_id: str, auditor_id: str) -> None:
    orch = _orch(session_id, auditor_id)
    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=orch["agent_id"], target_agent_id=orch["agent_id"],
            payload_artifact_id=orch["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert violations[-1]["payload"]["rejection_reason"] == "SELF_HANDOFF"
