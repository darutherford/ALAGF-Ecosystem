"""Invariant 2 (Non-Bypass) acceptance tests.

In Sprint-1 scope:
    - max_synthesis_depth must persist unmodified through the registration
      pipeline.
    - It must be retrievable by agent_id via the lookup API.

Sprint-3 scope (ACTIVE):
    - Structural enforcement of the depth ceiling. chain-minimum attribution
      (strictest upstream ceiling governs) eliminates the relay-laundering
      vector. DEPTH_LIMIT_REACHED is emitted BEFORE DepthLimitExceededError
      is raised (emit-before-raise discipline, Precondition 8).
    - Path-scoped session freeze: a depth-limited provenance chain blocks
      further synthesis on that chain, but parallel paths continue.
    - No override flag, escape hatch, or configuration switch permits
      bypass. The ceiling is architectural.
"""

from __future__ import annotations

import pytest

from multiagent.orchestrator.agent_lifecycle.registration import (
    get_agent_identity,
    register_agent,
)


@pytest.mark.parametrize("depth", [0, 1, 3, 7, 42])
def test_max_synthesis_depth_persists_unmodified(
    session_id: str, auditor_id: str, depth: int
) -> None:
    record = register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=depth,
    )
    assert record["max_synthesis_depth"] == depth
    # Round-trip via lookup API.
    fetched = get_agent_identity(record["agent_id"])
    assert fetched["max_synthesis_depth"] == depth


def test_max_synthesis_depth_rejects_negative(
    session_id: str, auditor_id: str
) -> None:
    """Schema enforces minimum: 0. Negative values fail ArtifactValidationError."""
    from multiagent.exceptions import ArtifactValidationError

    with pytest.raises(ArtifactValidationError):
        register_agent(
            session_id=session_id,
            auditor_id=auditor_id,
            agent_type="ORCHESTRATOR",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T1",
            authority_scope="ROUTING",
            max_synthesis_depth=-1,
        )


# ---------------------------------------------------------------------------
# Sprint-3 extensions: structural depth-ceiling enforcement
# ---------------------------------------------------------------------------

from multiagent.exceptions import DepthLimitExceededError, UnregisteredAgentError
from multiagent.ledger.hash_chain.events import read_session_events
from multiagent.orchestrator.synthesis.fs_adapter import FsLedger
from multiagent.orchestrator.synthesis.fs_agent_registry import FsAgentRegistry
from multiagent.orchestrator.synthesis.hypothesis import (
    FrozenPathError,
    emit_hypothesis,
)


def _emit(ledger, registry, session_id, auditor_id, agent, upstream=None, obs=None):
    return emit_hypothesis(
        session_id=session_id,
        source_agent_id=agent,
        observation_refs=obs or ["OBS_000000000001"],
        upstream_hypothesis_refs=upstream or [],
        composite_upstream_bme_score=0.1,
        auditor_id=auditor_id,
        registry=registry,
        ledger=ledger,
        ledger_writer=ledger,
    )


def test_depth_ceiling_emits_depth_limit_reached_event(
    session_id: str, auditor_id: str
) -> None:
    """Sprint-1 reserved this test as skipped; Sprint-3 activates it.

    With a ceiling of 2: depth=1 and depth=2 register successfully; depth=3
    emits DEPTH_LIMIT_REACHED then raises DepthLimitExceededError.
    """
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=2,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()

    evt1 = _emit(ledger, registry, session_id, auditor_id, agent["agent_id"])
    hyp1 = evt1["payload"]["hypothesis"]["artifact_id"]
    assert evt1["payload"]["hypothesis"]["synthesis_depth"] == 1

    evt2 = _emit(
        ledger, registry, session_id, auditor_id, agent["agent_id"],
        upstream=[hyp1],
    )
    hyp2 = evt2["payload"]["hypothesis"]["artifact_id"]
    assert evt2["payload"]["hypothesis"]["synthesis_depth"] == 2

    with pytest.raises(DepthLimitExceededError):
        _emit(
            ledger, registry, session_id, auditor_id, agent["agent_id"],
            upstream=[hyp2],
        )

    events = read_session_events(session_id)
    types = [e["event_type"] for e in events]
    assert "DEPTH_LIMIT_REACHED" in types
    # Only two HYPOTHESIS_REGISTERED (not three)
    assert types.count("HYPOTHESIS_REGISTERED") == 2


def test_depth_limit_reached_written_before_exception(
    session_id: str, auditor_id: str
) -> None:
    """Emit-before-raise (Precondition 8)."""
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=1,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()

    evt1 = _emit(ledger, registry, session_id, auditor_id, agent["agent_id"])
    hyp1 = evt1["payload"]["hypothesis"]["artifact_id"]

    with pytest.raises(DepthLimitExceededError):
        _emit(
            ledger, registry, session_id, auditor_id, agent["agent_id"],
            upstream=[hyp1],
        )

    events = read_session_events(session_id)
    last = events[-1]
    assert last["event_type"] == "DEPTH_LIMIT_REACHED"
    assert (
        last["payload"]["rejection_reason"] == "CHAIN_MINIMUM_CEILING_EXCEEDED"
    )


def test_post_freeze_path_is_architecturally_rejected(
    session_id: str, auditor_id: str
) -> None:
    """Path-scoped freeze (decision b): after DEPTH_LIMIT_REACHED, any
    further emission whose provenance chain intersects the frozen ancestors
    is rejected."""
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=1,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()

    evt1 = _emit(ledger, registry, session_id, auditor_id, agent["agent_id"])
    hyp1 = evt1["payload"]["hypothesis"]["artifact_id"]

    with pytest.raises(DepthLimitExceededError):
        _emit(
            ledger, registry, session_id, auditor_id, agent["agent_id"],
            upstream=[hyp1],
        )

    with pytest.raises(FrozenPathError):
        _emit(
            ledger, registry, session_id, auditor_id, agent["agent_id"],
            upstream=[hyp1],
        )


def test_parallel_path_survives_freeze(
    session_id: str, auditor_id: str
) -> None:
    """Path-scoped freeze (decision b): a parallel provenance path that does
    NOT include the frozen ancestor continues to work."""
    low = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=1,
    )
    high = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=5, parent_agent_id=low["agent_id"],
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()

    # Path A on low: ceiling 1, trips
    low_h1 = _emit(
        ledger, registry, session_id, auditor_id, low["agent_id"]
    )["payload"]["hypothesis"]["artifact_id"]
    with pytest.raises(DepthLimitExceededError):
        _emit(
            ledger, registry, session_id, auditor_id, low["agent_id"],
            upstream=[low_h1],
        )

    # Path B on high, independent chain: ceiling 5, succeeds
    high_h1 = _emit(
        ledger, registry, session_id, auditor_id, high["agent_id"]
    )["payload"]["hypothesis"]["artifact_id"]
    high_h2 = _emit(
        ledger, registry, session_id, auditor_id, high["agent_id"],
        upstream=[high_h1],
    )
    assert high_h2["payload"]["hypothesis"]["synthesis_depth"] == 2


def test_chain_minimum_closes_relay_vector(
    session_id: str, auditor_id: str
) -> None:
    """Decision (a): a high-ceiling agent cannot consume a low-ceiling
    agent's output to extend effective depth beyond the low-ceiling."""
    t1 = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=1,
    )
    t4 = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=10, parent_agent_id=t1["agent_id"],
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()

    evt_t1 = _emit(
        ledger, registry, session_id, auditor_id, t1["agent_id"]
    )
    hyp_t1 = evt_t1["payload"]["hypothesis"]["artifact_id"]

    # T4 agent tries to synthesize from T1's output. Computed depth=2 vs
    # chain-minimum ceiling=1. Rejected.
    with pytest.raises(DepthLimitExceededError) as exc_info:
        _emit(
            ledger, registry, session_id, auditor_id, t4["agent_id"],
            upstream=[hyp_t1],
        )
    assert exc_info.value.governing_ceiling == 1
    assert exc_info.value.binding_agent_id == t1["agent_id"]


def test_no_alternative_code_path_bypasses_ceiling(
    session_id: str, auditor_id: str
) -> None:
    """Negative test: emit_hypothesis is the only architecturally-sanctioned
    path. A caller cannot bypass — every retry re-evaluates chain-minimum
    against registered agents' ceilings and rejects."""
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=1,
    )
    ledger = FsLedger()
    registry = FsAgentRegistry()

    evt1 = _emit(ledger, registry, session_id, auditor_id, agent["agent_id"])
    hyp1 = evt1["payload"]["hypothesis"]["artifact_id"]

    # Every attempt to extend is rejected.
    for _ in range(3):
        with pytest.raises((DepthLimitExceededError, FrozenPathError)):
            _emit(
                ledger, registry, session_id, auditor_id, agent["agent_id"],
                upstream=[hyp1],
            )
