"""Invariant 2 (Non-Bypass) acceptance tests.

In Sprint-1 scope:
    - max_synthesis_depth must persist unmodified through the registration
      pipeline.
    - It must be retrievable by agent_id via the lookup API.

Reserved for Sprint-3:
    - Structural enforcement of the depth ceiling (DEPTH_LIMIT_REACHED event,
      HITL routing). Placeholder test records the Sprint-1 boundary.
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


@pytest.mark.skip(
    reason="Sprint-3 scope: DEPTH_LIMIT_REACHED emission and HITL routing. "
    "Placeholder to reserve the test slot in the invariant suite."
)
def test_depth_ceiling_emits_depth_limit_reached_event() -> None:  # pragma: no cover
    pass
