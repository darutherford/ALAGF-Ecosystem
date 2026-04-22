"""Invariant 1 (Authority) acceptance tests.

Only human Decisions and deterministic controller rules may produce binding
outcomes. AI outputs from any agent are always non-binding. The
non_authoritative_flag is hard-coded true on all AI-produced artifacts and
is non-overridable.

At the AgentIdentity layer this manifests as:
    - non_authoritative_flag cannot be constructed as anything other than true.
    - auditor_id must match the canonical human-identity pattern.
    - registered_by cannot resolve to an agent_id.

Sprint-2 extensions:
    - AgentHandoff.non_authoritative_flag is hard-coded true at both the
      schema level (const: true) and the factory level (AuthorityViolationError
      on any non-true value).
    - A handoff attempting to transport a binding-authority payload is
      rejected with BoundaryViolationError and produces a BOUNDARY_VIOLATION
      event with rejection_reason BINDING_PAYLOAD.

Sprint-3 extensions:
    - Hypothesis.non_authoritative_flag is hard-coded true at both the
      schema level (const: true) and the factory level (AuthorityViolationError
      on any non-true value).
    - Hypothesis emission requires a registered ACTIVE source agent; emission
      against an unregistered agent raises UnregisteredAgentError and emits
      UNREGISTERED_AGENT_OUTPUT.
"""

from __future__ import annotations

import pytest

from multiagent.artifacts.AgentHandoff import build_agent_handoff
from multiagent.artifacts.AgentIdentity import build_agent_identity
from multiagent.exceptions import (
    ArtifactValidationError,
    AuthorityViolationError,
    BoundaryViolationError,
    UnregisteredAgentError,
)
from multiagent.ledger.hash_chain.events import (
    append_event,
    read_session_events,
)
from multiagent.orchestrator.agent_lifecycle.registration import register_agent
from multiagent.orchestrator.boundary_enforcement import emit_handoff


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


# ---------------------------------------------------------------------------
# Sprint-2 extensions: AgentHandoff and boundary-level authority enforcement
# ---------------------------------------------------------------------------


def test_handoff_rejects_non_authoritative_flag_false(session_id: str) -> None:
    """Factory-level Invariant 1 rejection on non-true non_authoritative_flag."""
    with pytest.raises(AuthorityViolationError):
        build_agent_handoff(
            session_id=session_id,
            source_agent_id="AGT_000000000001",
            target_agent_id="AGT_000000000002",
            payload_artifact_id="AGT_000000000003",
            non_authoritative_flag=False,
        )


def test_handoff_rejects_non_authoritative_flag_non_boolean(session_id: str) -> None:
    """Any non-true value — string, int, None-equivalent — must raise authority error."""
    with pytest.raises(AuthorityViolationError):
        build_agent_handoff(
            session_id=session_id,
            source_agent_id="AGT_000000000001",
            target_agent_id="AGT_000000000002",
            payload_artifact_id="AGT_000000000003",
            non_authoritative_flag="true",  # type: ignore[arg-type]
        )


def test_handoff_non_authoritative_flag_is_hardcoded_true(session_id: str) -> None:
    """Default construction produces non_authoritative_flag: true."""
    artifact = build_agent_handoff(
        session_id=session_id,
        source_agent_id="AGT_000000000001",
        target_agent_id="AGT_000000000002",
        payload_artifact_id="AGT_000000000003",
    )
    assert artifact["non_authoritative_flag"] is True
    assert artifact["authority_level"] == "orchestration"


def test_handoff_rejects_binding_payload(
    session_id: str, auditor_id: str
) -> None:
    """A payload_artifact_id whose declared authority_level is 'binding' must be
    rejected via BINDING_PAYLOAD. Invariant 1 forbids binding artifacts from
    traversing agent boundaries; they cross only through a human Decision gate.

    We fabricate a binding payload by appending an AGENT_REGISTERED-like event
    whose payload carries a synthetic binding artifact. This simulates a future
    Decision artifact that the current sprint cannot construct natively.
    """
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

    # Fabricate a prior ledger reference to a binding-authority artifact by
    # embedding it in an AGENT_REGISTERED payload with a distinct id. The
    # discoverability resolver will find it and read its authority_level.
    fake_binding_id = "FAKE_BINDING_0001"
    fake_agent = dict(orch)
    # Strip meta fields and inject a non-AgentIdentity identifier so the
    # resolver finds it via the ledger-scan path, not the registry path.
    fake_agent = {k: v for k, v in fake_agent.items() if not k.startswith("_")}
    fake_agent["agent_id"] = fake_binding_id
    fake_agent["authority_level"] = "binding"
    append_event(
        event_type="AGENT_REGISTERED",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "HUMAN", "actor_id": auditor_id},
        payload={"agent_identity": fake_agent},
        referenced_artifact_id=fake_binding_id,
    )

    with pytest.raises(BoundaryViolationError):
        emit_handoff(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=orch["agent_id"],
            target_agent_id=sub["agent_id"],
            payload_artifact_id=fake_binding_id,
        )

    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert len(violations) == 1
    assert violations[0]["payload"]["rejection_reason"] == "BINDING_PAYLOAD"


# ---------------------------------------------------------------------------
# Sprint-3 extensions: Hypothesis authority enforcement
# ---------------------------------------------------------------------------

from multiagent.artifacts.Hypothesis import (
    HypothesisValidationError,
    build_hypothesis,
    validate_hypothesis,
)
from multiagent.orchestrator.synthesis.fs_adapter import FsLedger
from multiagent.orchestrator.synthesis.fs_agent_registry import FsAgentRegistry
from multiagent.orchestrator.synthesis.hypothesis import emit_hypothesis


def _build_valid_hypothesis(session_id: str, **overrides) -> dict:
    """Helper that builds a minimally-valid Hypothesis with sensible defaults."""
    kwargs = dict(
        session_id=session_id,
        observation_refs=["OBS_000000000001"],
        synthesis_depth=1,
        upstream_hypothesis_refs=[],
        composite_upstream_bme_score=0.1,
    )
    kwargs.update(overrides)
    return build_hypothesis(**kwargs)


def test_hypothesis_factory_rejects_non_authoritative_flag_false(
    session_id: str,
) -> None:
    """Invariant 1: override attempts on non_authoritative_flag raise
    AuthorityViolationError at the factory level."""
    with pytest.raises(AuthorityViolationError):
        _build_valid_hypothesis(
            session_id=session_id,
            non_authoritative_flag=False,
        )


def test_hypothesis_factory_rejects_non_authoritative_flag_none(
    session_id: str,
) -> None:
    with pytest.raises(AuthorityViolationError):
        _build_valid_hypothesis(
            session_id=session_id,
            non_authoritative_flag=None,  # type: ignore[arg-type]
        )


def test_hypothesis_validate_rejects_tampered_flag(session_id: str) -> None:
    """Invariant 1 double-enforcement: a manually-tampered artifact with
    non_authoritative_flag=False is rejected by validate_hypothesis."""
    artifact = _build_valid_hypothesis(session_id=session_id)
    artifact["non_authoritative_flag"] = False
    with pytest.raises(AuthorityViolationError):
        validate_hypothesis(artifact)


def test_hypothesis_factory_hardcodes_non_authoritative_flag(
    session_id: str,
) -> None:
    """Default construction produces non_authoritative_flag: true,
    authority_level: 'non_binding', artifact_type: 'Hypothesis'."""
    artifact = _build_valid_hypothesis(session_id=session_id)
    assert artifact["non_authoritative_flag"] is True
    assert artifact["authority_level"] == "non_binding"
    assert artifact["artifact_type"] == "Hypothesis"


def test_hypothesis_emission_requires_registered_source_agent(
    session_id: str, auditor_id: str
) -> None:
    """Invariant 1: AI outputs must have AI-agent provenance. Emission
    against an unregistered agent raises UnregisteredAgentError and emits
    UNREGISTERED_AGENT_OUTPUT before raising."""
    ledger = FsLedger()
    registry = FsAgentRegistry()
    with pytest.raises(UnregisteredAgentError):
        emit_hypothesis(
            session_id=session_id,
            source_agent_id="AGT_000000000000",  # not registered
            observation_refs=["OBS_000000000001"],
            upstream_hypothesis_refs=[],
            composite_upstream_bme_score=0.1,
            auditor_id=auditor_id,
            registry=registry,
            ledger=ledger,
            ledger_writer=ledger,
        )

    events = read_session_events(session_id)
    assert any(
        e["event_type"] == "UNREGISTERED_AGENT_OUTPUT" for e in events
    )


def test_hypothesis_emission_requires_active_source_agent(
    session_id: str, auditor_id: str
) -> None:
    """Invariant 1: A SUSPENDED agent cannot emit a Hypothesis."""
    from multiagent.orchestrator.agent_lifecycle.registration import (
        suspend_agent,
    )

    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=3,
    )
    suspend_agent(
        agent_id=orch["agent_id"], auditor_id=auditor_id, reason="test"
    )

    ledger = FsLedger()
    registry = FsAgentRegistry()
    with pytest.raises(UnregisteredAgentError):
        emit_hypothesis(
            session_id=session_id,
            source_agent_id=orch["agent_id"],
            observation_refs=["OBS_000000000001"],
            upstream_hypothesis_refs=[],
            composite_upstream_bme_score=0.1,
            auditor_id=auditor_id,
            registry=registry,
            ledger=ledger,
            ledger_writer=ledger,
        )


def test_hypothesis_schema_rejects_invalid_session_id_pattern() -> None:
    """Invariant 3/schema: Hypothesis session_id must match SESSION_<8 hex>."""
    with pytest.raises((HypothesisValidationError, ArtifactValidationError)):
        _build_valid_hypothesis(session_id="not-a-session-id")
