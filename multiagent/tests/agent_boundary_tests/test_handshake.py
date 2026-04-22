"""BOUNDARY_HANDSHAKE protocol tests.

Scope: channel establishment, directionality (Sprint-2 decision a), session
isolation, and the pure-ledger channel-lookup semantics.
"""

from __future__ import annotations

import pytest

from multiagent.exceptions import BoundaryViolationError, HandshakeError
from multiagent.ledger.hash_chain.events import read_session_events
from multiagent.orchestrator.agent_lifecycle.registration import (
    register_agent,
    suspend_agent,
)
from multiagent.orchestrator.boundary_enforcement import (
    emit_handshake,
    is_channel_established,
    list_established_channels,
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


def test_is_channel_established_false_before_handshake(
    session_id: str, auditor_id: str
) -> None:
    orch = _orch(session_id, auditor_id)
    sub_a = _sub(session_id, auditor_id, orch["agent_id"])
    sub_b = _sub(session_id, auditor_id, orch["agent_id"])
    assert not is_channel_established(
        session_id=session_id,
        source_agent_id=sub_a["agent_id"],
        target_agent_id=sub_b["agent_id"],
    )


def test_is_channel_established_true_after_handshake(
    session_id: str, auditor_id: str
) -> None:
    orch = _orch(session_id, auditor_id)
    sub_a = _sub(session_id, auditor_id, orch["agent_id"])
    sub_b = _sub(session_id, auditor_id, orch["agent_id"])
    emit_handshake(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
    )
    assert is_channel_established(
        session_id=session_id,
        source_agent_id=sub_a["agent_id"],
        target_agent_id=sub_b["agent_id"],
    )


def test_channel_direction_is_strict(session_id: str, auditor_id: str) -> None:
    """Decision (a): an A-to-B handshake does NOT establish B-to-A."""
    orch = _orch(session_id, auditor_id)
    sub_a = _sub(session_id, auditor_id, orch["agent_id"])
    sub_b = _sub(session_id, auditor_id, orch["agent_id"])
    emit_handshake(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
    )
    # Forward direction established.
    assert is_channel_established(
        session_id=session_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
    )
    # Reverse direction NOT established.
    assert not is_channel_established(
        session_id=session_id,
        source_agent_id=sub_b["agent_id"], target_agent_id=sub_a["agent_id"],
    )


def test_handshake_cross_session_rejected(
    session_id: str, auditor_id: str
) -> None:
    orch_a = _orch(session_id, auditor_id)
    other = "SESSION_77777777"
    orch_b = _orch(other, auditor_id)
    with pytest.raises(BoundaryViolationError):
        emit_handshake(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=orch_a["agent_id"],
            target_agent_id=orch_b["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert violations[-1]["payload"]["rejection_reason"] == "CROSS_SESSION"


def test_handshake_between_suspended_agent_rejected(
    session_id: str, auditor_id: str
) -> None:
    orch = _orch(session_id, auditor_id)
    sub_a = _sub(session_id, auditor_id, orch["agent_id"])
    sub_b = _sub(session_id, auditor_id, orch["agent_id"])
    suspend_agent(agent_id=sub_a["agent_id"], auditor_id=auditor_id, reason="test")

    with pytest.raises(BoundaryViolationError):
        emit_handshake(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
        )
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert violations[-1]["payload"]["rejection_reason"] == "SOURCE_INACTIVE"


def test_handshake_self_rejected(session_id: str, auditor_id: str) -> None:
    orch = _orch(session_id, auditor_id)
    with pytest.raises(HandshakeError):
        emit_handshake(
            session_id=session_id, auditor_id=auditor_id,
            source_agent_id=orch["agent_id"], target_agent_id=orch["agent_id"],
        )


def test_list_established_channels_returns_emitted_channels(
    session_id: str, auditor_id: str
) -> None:
    orch = _orch(session_id, auditor_id)
    sub_a = _sub(session_id, auditor_id, orch["agent_id"])
    sub_b = _sub(session_id, auditor_id, orch["agent_id"])
    emit_handshake(
        session_id=session_id, auditor_id=auditor_id,
        source_agent_id=sub_a["agent_id"], target_agent_id=sub_b["agent_id"],
        channel_purpose="hypothesis-exchange",
    )
    channels = list_established_channels(session_id)
    assert len(channels) == 1
    assert channels[0]["source_agent_id"] == sub_a["agent_id"]
    assert channels[0]["target_agent_id"] == sub_b["agent_id"]
    assert channels[0]["channel_purpose"] == "hypothesis-exchange"
