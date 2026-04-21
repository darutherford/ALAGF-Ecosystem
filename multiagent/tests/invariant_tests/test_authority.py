"""Invariant 1 (Authority) acceptance tests.

Only human Decisions and deterministic controller rules may produce binding
outcomes. AI outputs from any agent are always non-binding. The
non_authoritative_flag is hard-coded true on all AI-produced artifacts and
is non-overridable.

At the AgentIdentity layer this manifests as:
    - non_authoritative_flag cannot be constructed as anything other than true.
    - auditor_id must match the canonical human-identity pattern.
    - registered_by cannot resolve to an agent_id.
"""

from __future__ import annotations

import pytest

from multiagent.artifacts.AgentIdentity import build_agent_identity
from multiagent.exceptions import (
    ArtifactValidationError,
    AuthorityViolationError,
)
from multiagent.orchestrator.agent_lifecycle.registration import register_agent


def test_build_rejects_non_authoritative_flag_false() -> None:
    with pytest.raises(AuthorityViolationError):
        build_agent_identity(
            agent_type="ORCHESTRATOR",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T1",
            authority_scope="ROUTING",
            registered_by="AUDITOR_TEST",
            max_synthesis_depth=1,
            non_authoritative_flag=False,  # runtime violation
        )


def test_build_rejects_non_authoritative_flag_none_of_the_above() -> None:
    """Any non-true value — None-equivalent, string, int — must be rejected.

    The factory accepts True or absent. Anything else raises.
    """
    with pytest.raises(AuthorityViolationError):
        build_agent_identity(
            agent_type="ORCHESTRATOR",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T1",
            authority_scope="ROUTING",
            registered_by="AUDITOR_TEST",
            max_synthesis_depth=1,
            non_authoritative_flag="true",  # type: ignore[arg-type]
        )


def test_build_accepts_non_authoritative_flag_true() -> None:
    """Passing True explicitly is permitted (redundant but valid)."""
    artifact = build_agent_identity(
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        registered_by="AUDITOR_TEST",
        max_synthesis_depth=1,
        non_authoritative_flag=True,
    )
    assert artifact["non_authoritative_flag"] is True


def test_register_rejects_missing_auditor_pattern(session_id: str) -> None:
    with pytest.raises(AuthorityViolationError):
        register_agent(
            session_id=session_id,
            auditor_id="some-human",  # fails AUDITOR_[A-Z0-9_]+
            agent_type="ORCHESTRATOR",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T1",
            authority_scope="ROUTING",
            max_synthesis_depth=1,
        )


def test_register_rejects_empty_auditor(session_id: str) -> None:
    with pytest.raises(AuthorityViolationError):
        register_agent(
            session_id=session_id,
            auditor_id="",
            agent_type="ORCHESTRATOR",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T1",
            authority_scope="ROUTING",
            max_synthesis_depth=1,
        )


def test_register_rejects_lowercase_auditor(session_id: str) -> None:
    """The pattern requires uppercase after AUDITOR_. Lowercase is rejected."""
    with pytest.raises(AuthorityViolationError):
        register_agent(
            session_id=session_id,
            auditor_id="AUDITOR_dale_001",  # lowercase after prefix
            agent_type="ORCHESTRATOR",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            trust_tier="T1",
            authority_scope="ROUTING",
            max_synthesis_depth=1,
        )
