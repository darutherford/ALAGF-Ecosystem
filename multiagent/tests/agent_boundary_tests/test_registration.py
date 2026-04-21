"""Agent boundary tests: registration rules per agent_type.

These tests cover the structural rules of AgentIdentity registration:
    - ORCHESTRATOR registers with parent_agent_id: null.
    - SUB_AGENT and VALIDATOR require a non-null, registered parent.
    - Duplicate agent_id within a session is rejected.
    - REVOKED is terminal: a revoked agent_id cannot be re-registered,
      and the same object cannot transition out of REVOKED.
"""

from __future__ import annotations

import pytest

from multiagent.exceptions import (
    AgentRegistrationError,
    ArtifactValidationError,
    UnregisteredAgentError,
)
from multiagent.orchestrator.agent_lifecycle.registration import (
    register_agent,
    revoke_agent,
    suspend_agent,
)


def test_orchestrator_null_parent_succeeds(
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
        max_synthesis_depth=2,
    )
    assert record["parent_agent_id"] is None
    assert record["agent_type"] == "ORCHESTRATOR"
    assert record["status"] == "ACTIVE"


def test_orchestrator_with_parent_is_rejected(
    session_id: str, auditor_id: str
) -> None:
    """Schema allOf enforces: ORCHESTRATOR => parent_agent_id is null."""
    with pytest.raises(ArtifactValidationError):
        register_agent(
            session_id=session_id,
            auditor_id=auditor_id,
            agent_type="ORCHESTRATOR",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T1",
            authority_scope="ROUTING",
            max_synthesis_depth=1,
            parent_agent_id="AGT_someparent",
        )


def test_sub_agent_null_parent_is_rejected(
    session_id: str, auditor_id: str
) -> None:
    """SUB_AGENT with null parent fails schema validation."""
    with pytest.raises(ArtifactValidationError):
        register_agent(
            session_id=session_id,
            auditor_id=auditor_id,
            agent_type="SUB_AGENT",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T2",
            authority_scope="HYPOTHESES",
            max_synthesis_depth=1,
            parent_agent_id=None,
        )


def test_sub_agent_references_registered_parent(
    session_id: str, auditor_id: str
) -> None:
    parent = register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=3,
    )
    child = register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="SUB_AGENT",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T2",
        authority_scope="HYPOTHESES",
        max_synthesis_depth=2,
        parent_agent_id=parent["agent_id"],
    )
    assert child["parent_agent_id"] == parent["agent_id"]


def test_sub_agent_parent_must_exist(
    session_id: str, auditor_id: str
) -> None:
    """Non-existent parent_agent_id raises AgentRegistrationError."""
    with pytest.raises(AgentRegistrationError):
        register_agent(
            session_id=session_id,
            auditor_id=auditor_id,
            agent_type="SUB_AGENT",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T2",
            authority_scope="HYPOTHESES",
            max_synthesis_depth=1,
            parent_agent_id="AGT_does_not_exist",
        )


def test_sub_agent_parent_must_be_active(
    session_id: str, auditor_id: str
) -> None:
    """A SUSPENDED parent cannot adopt new children."""
    parent = register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=2,
    )
    suspend_agent(
        agent_id=parent["agent_id"], auditor_id=auditor_id, reason="blocked"
    )
    with pytest.raises(AgentRegistrationError):
        register_agent(
            session_id=session_id,
            auditor_id=auditor_id,
            agent_type="SUB_AGENT",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T2",
            authority_scope="HYPOTHESES",
            max_synthesis_depth=1,
            parent_agent_id=parent["agent_id"],
        )


def test_duplicate_agent_id_is_rejected(
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
        agent_id="AGT_fixedvalue01",
    )
    with pytest.raises(AgentRegistrationError):
        register_agent(
            session_id=session_id,
            auditor_id=auditor_id,
            agent_type="ORCHESTRATOR",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T1",
            authority_scope="ROUTING",
            max_synthesis_depth=1,
            agent_id="AGT_fixedvalue01",
        )


def test_revoked_agent_cannot_be_re_revoked(
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
    revoke_agent(
        agent_id=record["agent_id"], auditor_id=auditor_id, reason="terminal"
    )
    with pytest.raises(AgentRegistrationError):
        revoke_agent(
            agent_id=record["agent_id"], auditor_id=auditor_id, reason="again"
        )


def test_revoked_agent_cannot_be_suspended(
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
    revoke_agent(
        agent_id=record["agent_id"], auditor_id=auditor_id, reason="terminal"
    )
    with pytest.raises(AgentRegistrationError):
        suspend_agent(
            agent_id=record["agent_id"],
            auditor_id=auditor_id,
            reason="cannot",
        )


def test_suspended_agent_cannot_be_re_suspended(
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
    suspend_agent(
        agent_id=record["agent_id"], auditor_id=auditor_id, reason="pause"
    )
    with pytest.raises(AgentRegistrationError):
        suspend_agent(
            agent_id=record["agent_id"],
            auditor_id=auditor_id,
            reason="again",
        )


def test_lookup_nonexistent_raises(
    session_id: str, auditor_id: str
) -> None:
    from multiagent.orchestrator.agent_lifecycle.registration import (
        get_agent_identity,
    )

    with pytest.raises(UnregisteredAgentError):
        get_agent_identity("AGT_nonexistent1")
