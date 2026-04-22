"""
Agent boundary tests for Sprint-3 Hypothesis emission.

These tests exercise the structural rules on Hypothesis emission that
depend on agent registration state and cross-agent provenance.
"""

from __future__ import annotations

import pytest

from multiagent.exceptions import DepthLimitExceededError
from multiagent.orchestrator.agent_lifecycle.registration import register_agent
from multiagent.orchestrator.synthesis.fs_adapter import FsLedger
from multiagent.orchestrator.synthesis.fs_agent_registry import FsAgentRegistry
from multiagent.orchestrator.synthesis.hypothesis import (
    ScopeViolationError,
    emit_hypothesis,
)


def _emit(ledger, registry, session_id, auditor_id, agent, upstream=None):
    return emit_hypothesis(
        session_id=session_id,
        source_agent_id=agent,
        observation_refs=["OBS_000000000001"],
        upstream_hypothesis_refs=upstream or [],
        composite_upstream_bme_score=0.1,
        auditor_id=auditor_id,
        registry=registry,
        ledger=ledger,
        ledger_writer=ledger,
    )


def test_orchestrator_source_depth1_succeeds(
    session_id: str, auditor_id: str
) -> None:
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()
    evt = _emit(ledger, registry, session_id, auditor_id, orch["agent_id"])
    assert evt["payload"]["hypothesis"]["synthesis_depth"] == 1


def test_observations_only_scope_rejected(
    session_id: str, auditor_id: str
) -> None:
    """Decision (d): OBSERVATIONS_ONLY agents cannot emit Hypotheses."""
    obs = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1",
        authority_scope="OBSERVATIONS_ONLY",
        max_synthesis_depth=3,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()
    with pytest.raises(ScopeViolationError) as exc_info:
        _emit(ledger, registry, session_id, auditor_id, obs["agent_id"])
    assert exc_info.value.agent_id == obs["agent_id"]
    assert exc_info.value.authority_scope == "OBSERVATIONS_ONLY"


def test_hypotheses_and_routing_scopes_permitted(
    session_id: str, auditor_id: str
) -> None:
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )
    sub = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=3, parent_agent_id=orch["agent_id"],
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()
    assert _emit(ledger, registry, session_id, auditor_id, orch["agent_id"])
    assert _emit(ledger, registry, session_id, auditor_id, sub["agent_id"])


def test_cross_agent_depth_walk(
    session_id: str, auditor_id: str
) -> None:
    """Depth walks across agent boundaries via upstream_hypothesis_refs
    regardless of source_agent_id."""
    a = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=5,
    )
    b = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=5, parent_agent_id=a["agent_id"],
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()

    h1 = _emit(ledger, registry, session_id, auditor_id, a["agent_id"])[
        "payload"
    ]["hypothesis"]["artifact_id"]
    h2 = _emit(
        ledger, registry, session_id, auditor_id, b["agent_id"],
        upstream=[h1],
    )["payload"]["hypothesis"]["artifact_id"]
    h3 = _emit(
        ledger, registry, session_id, auditor_id, a["agent_id"],
        upstream=[h2],
    )["payload"]["hypothesis"]
    assert h3["synthesis_depth"] == 3


def test_depth_at_ceiling_registers_next_step_fails(
    session_id: str, auditor_id: str
) -> None:
    """Depth == ceiling registers successfully; depth > ceiling on the next
    hop fails by construction."""
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=2,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()
    h1 = _emit(ledger, registry, session_id, auditor_id, agent["agent_id"])[
        "payload"
    ]["hypothesis"]["artifact_id"]
    evt2 = _emit(
        ledger, registry, session_id, auditor_id, agent["agent_id"],
        upstream=[h1],
    )
    assert evt2["payload"]["hypothesis"]["synthesis_depth"] == 2

    h2 = evt2["payload"]["hypothesis"]["artifact_id"]
    with pytest.raises(DepthLimitExceededError):
        _emit(
            ledger, registry, session_id, auditor_id, agent["agent_id"],
            upstream=[h2],
        )
