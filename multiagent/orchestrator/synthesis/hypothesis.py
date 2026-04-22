"""
Hypothesis emission orchestrator (Sprint-3).

Governance rationale:
    This module is the Invariant 2 architectural enforcement point. No code
    path in this module permits:
      - Hypothesis emission without a registered ACTIVE source agent
      - Hypothesis emission from an agent lacking HYPOTHESES/ROUTING scope
        (decision d: ScopeViolationError is introduced as a distinct class)
      - Upstream refs that do not resolve to prior HYPOTHESIS_REGISTERED
      - Emission on a frozen provenance path
      - Depth-ceiling bypass (chain-minimum governs; decision a)
      - Silent errors (emit-before-raise discipline; Precondition 8)

    Invariants enforced end-to-end:
      - Invariant 1 (Authority): non_authoritative_flag = True at schema and
        factory; envelope actor_type=ORCHESTRATOR or AGENT, never HUMAN for
        Hypothesis emission.
      - Invariant 2 (Non-Bypass): ceiling is architectural.
      - Invariant 3 (Evidence-First): observation_refs minItems:1 on every
        Hypothesis (decision g-i).
      - Invariant 4 (Reconstructability): every failure path emits a ledger
        event before raising where emit-before-raise is meaningful.

HEAD envelope production:
    This orchestrator produces envelopes conforming to
    /multiagent/ledger/hash_chain/event_schemas/v2/LedgerEvent.envelope.schema.json.
    ULID event_id, schema_version=v2, actor with ORCHESTRATOR type,
    causal_refs with prior_event_id=latest session event, referenced_artifact_id
    =hypothesis artifact_id (or attempted artifact for DEPTH_LIMIT_REACHED),
    SHA-256 hash chain with sha256: prefix.

    The LedgerWriter protocol is designed to accept these fields and do the
    hashing/sequencing. Sprint-1/2's append_event is compatible; this
    module routes through it via the injected writer. For standalone testing
    the tests inject a minimal writer that preserves the envelope shape.
"""

from __future__ import annotations

from typing import Protocol

from multiagent.artifacts.Hypothesis import (
    HypothesisValidationError,
    build_hypothesis,
)
from multiagent.orchestrator.synthesis.depth import (
    AgentRegistryReader,
    DepthLimitExceededError,
    LedgerReader,
    build_depth_limit_payload,
    evaluate_depth_ceiling,
    is_session_depth_frozen,
)


# --- Exceptions -------------------------------------------------------------
#
# Sprint-3 extends the canonical Sprint-1 exception taxonomy at
# multiagent.exceptions. DepthLimitExceededError is already reserved there
# and inherits from ALAGFError; Sprint-3 imports and re-raises the Sprint-3
# subclass with diagnostic attributes (see depth.py).
#
# ScopeViolationError and FrozenPathError are net-new Sprint-3 additions and
# are defined here as subclasses of ALAGFError to remain consistent with the
# canonical taxonomy. They are NOT added to multiagent.exceptions because
# Sprint-3's instruction discipline prefers not to modify Sprint-1/2 files
# beyond what is mechanically required. The two classes being defined here
# rather than in multiagent.exceptions is a Sprint-4 consolidation item.

from multiagent.exceptions import ALAGFError


class UnregisteredAgentError(ALAGFError):
    """Re-export of the Sprint-1 canonical class for import convenience.

    Sprint-3 uses the canonical class at multiagent.exceptions. This local
    name is a typed re-import, not a new class. isinstance checks against
    the canonical class work identically.
    """


def _unregistered_agent_error_class():
    from multiagent.exceptions import UnregisteredAgentError as _U
    return _U


class ScopeViolationError(ALAGFError):
    """Source agent's authority_scope does not permit Hypothesis emission
    (decision d). Net-new in Sprint-3."""

    def __init__(self, *, agent_id: str, authority_scope: str):
        self.agent_id = agent_id
        self.authority_scope = authority_scope
        super().__init__(
            f"Agent {agent_id} authority_scope={authority_scope} cannot emit "
            "Hypothesis. Required scope: HYPOTHESES or ROUTING."
        )


class FrozenPathError(ALAGFError):
    """Prospective Hypothesis's provenance chain intersects a frozen ancestor.
    Net-new in Sprint-3."""

    def __init__(self, *, session_id: str):
        self.session_id = session_id
        super().__init__(
            f"Hypothesis rejected: provenance chain includes a frozen "
            f"ancestor in session {session_id}. Human Decision required "
            "(Sprint-5) to clear freeze."
        )


class UpstreamResolutionError(ALAGFError):
    """An upstream_hypothesis_ref does not resolve in the session ledger.
    Net-new in Sprint-3."""


# --- Ledger writer protocol -------------------------------------------------


class LedgerWriter(Protocol):
    """Append-only ledger writer protocol.

    Sprint-1/2 canonical implementation: multiagent.ledger.hash_chain.events
    .append_event. Sprint-3 uses the same writer signature via an injected
    adapter that translates Sprint-3-specific kwargs to the canonical call.
    """

    def append_event(
        self,
        *,
        event_type: str,
        session_id: str,
        auditor_id: str,
        actor: dict,
        causal_refs: dict,
        payload: dict,
    ) -> dict:
        """Append an event and return the written envelope."""
        ...


# --- Emission helpers -------------------------------------------------------


def _build_actor(agent_id: str) -> dict:
    """Emit Hypothesis events with actor_type=AGENT (the AI agent producing
    the Hypothesis). Invariant 1 pairs this with non_authoritative_flag=True
    on the artifact: the actor is non-human, the output is non-binding."""
    return {"actor_type": "AGENT", "actor_id": agent_id}


def _latest_event_id(
    *, session_id: str, ledger: LedgerReader
) -> str | None:
    """Return the event_id of the most recently written event in the session
    (i.e., max sequence_number). None if session is empty.

    Used as prior_event_id for causal chaining per the HEAD envelope schema.
    """
    latest: tuple[int, str | None] = (-1, None)
    for event in ledger.iter_events(session_id):
        seq = event.get("sequence_number")
        if seq is None:
            continue
        if seq > latest[0]:
            latest = (seq, event.get("event_id"))
    return latest[1]


def _emit_unregistered_agent_output(
    *,
    ledger_writer: LedgerWriter,
    ledger: LedgerReader,
    session_id: str,
    agent_id: str,
    auditor_id: str,
) -> None:
    """Emit UNREGISTERED_AGENT_OUTPUT. Matches the Sprint-1 event shape
    so the existing reject_unregistered_output helper could alternatively be
    used by the caller."""
    ledger_writer.append_event(
        event_type="UNREGISTERED_AGENT_OUTPUT",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "ORCHESTRATOR", "actor_id": "orchestrator"},
        causal_refs={
            "prior_event_id": _latest_event_id(
                session_id=session_id, ledger=ledger
            ),
            "referenced_artifact_id": agent_id,
            "referenced_event_id": None,
        },
        payload={
            "attempted_agent_id": agent_id,
            "artifact_type": "Hypothesis",
            "rejection_reason": "NOT_REGISTERED",
        },
    )


def emit_depth_limit_reached(
    *,
    ledger_writer: LedgerWriter,
    ledger: LedgerReader,
    session_id: str,
    auditor_id: str,
    source_agent_id: str,
    payload: dict,
) -> dict:
    """Emit DEPTH_LIMIT_REACHED. Called immediately before
    DepthLimitExceededError is raised (Precondition 8)."""
    return ledger_writer.append_event(
        event_type="DEPTH_LIMIT_REACHED",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "ORCHESTRATOR", "actor_id": "orchestrator"},
        causal_refs={
            "prior_event_id": _latest_event_id(
                session_id=session_id, ledger=ledger
            ),
            "referenced_artifact_id": source_agent_id,
            "referenced_event_id": None,
        },
        payload=payload,
    )


# --- Precondition validation -----------------------------------------------


def validate_synthesis_preconditions(
    *,
    session_id: str,
    source_agent_id: str,
    upstream_hypothesis_refs: list[str],
    registry: AgentRegistryReader,
    ledger: LedgerReader,
    ledger_writer: LedgerWriter,
    auditor_id: str,
) -> dict:
    """Run the precondition pipeline. Returns the agent dict on success."""
    # (1) Agent registration + ACTIVE status
    agent = registry.get_agent(session_id, source_agent_id)
    if agent is None or agent.get("status") != "ACTIVE":
        _emit_unregistered_agent_output(
            ledger_writer=ledger_writer,
            ledger=ledger,
            session_id=session_id,
            agent_id=source_agent_id,
            auditor_id=auditor_id,
        )
        UnregisteredAgentErrorClass = _unregistered_agent_error_class()
        raise UnregisteredAgentErrorClass(
            f"Source agent {source_agent_id} is not registered ACTIVE in "
            f"session {session_id}"
        )

    # (2) authority_scope check (decision d)
    scope = agent.get("authority_scope")
    if scope not in {"HYPOTHESES", "ROUTING"}:
        # No dedicated ledger event for scope violations in Sprint-3.
        # Sprint-4 will decide whether to add SCOPE_VIOLATION event type.
        raise ScopeViolationError(
            agent_id=source_agent_id, authority_scope=str(scope)
        )

    # (3) Upstream refs resolve to prior HYPOTHESIS_REGISTERED events
    registered_ids: set[str] = set()
    for event in ledger.iter_events(session_id):
        if event.get("event_type") != "HYPOTHESIS_REGISTERED":
            continue
        hyp = (event.get("payload") or {}).get("hypothesis") or {}
        aid = hyp.get("artifact_id")
        if aid:
            registered_ids.add(aid)
    for ref in upstream_hypothesis_refs:
        if ref not in registered_ids:
            raise UpstreamResolutionError(
                f"upstream_hypothesis_ref {ref} not found among "
                f"HYPOTHESIS_REGISTERED events in session {session_id}"
            )

    # (4) Path-scoped freeze
    if is_session_depth_frozen(
        session_id=session_id,
        ledger=ledger,
        upstream_hypothesis_refs=upstream_hypothesis_refs,
    ):
        raise FrozenPathError(session_id=session_id)

    return agent


# --- Public emission entry point -------------------------------------------


def emit_hypothesis(
    *,
    session_id: str,
    source_agent_id: str,
    observation_refs: list[str],
    upstream_hypothesis_refs: list[str],
    composite_upstream_bme_score: float,
    auditor_id: str,
    registry: AgentRegistryReader,
    ledger: LedgerReader,
    ledger_writer: LedgerWriter,
    bme_score_source: str = "placeholder",
    # Optional rich fields on the HEAD-locked Hypothesis schema
    hypothesis_text: str | None = None,
    confidence_score: float | None = None,
    source_model: str | None = None,
    reasoning_trace: str | None = None,
    tier_justification: str | None = None,
    risk_flags: list[dict] | None = None,
    compliance_gaps: list[dict] | None = None,
    recommendations: list[str] | None = None,
    governance_narrative: str | None = None,
    entropy_assessment: str | None = None,
    raw_api_response: dict | None = None,
    cached_response: bool | None = None,
) -> dict:
    """Emit a Hypothesis. Returns the written HYPOTHESIS_REGISTERED event.

    Pipeline:
        1. Preconditions: registration, scope, upstream resolution, freeze.
        2. Depth + chain-minimum ceiling evaluation.
        3. If ceiling exceeded: emit DEPTH_LIMIT_REACHED, raise
           DepthLimitExceededError.
        4. Build and validate Hypothesis artifact (HEAD schema).
        5. Emit HYPOTHESIS_REGISTERED with HEAD envelope fields.

    bme_score_source (decision e-revised):
        "placeholder" (Sprint-3 default) or "computed" (Sprint-4). The
        HEAD schema requires composite_upstream_bme_score as a number
        in [0.0, 1.0]; this field on the envelope payload marks whether
        that number is a caller-supplied placeholder or a BME-attributed
        computation.
    """
    # (1) Preconditions
    validate_synthesis_preconditions(
        session_id=session_id,
        source_agent_id=source_agent_id,
        upstream_hypothesis_refs=upstream_hypothesis_refs,
        registry=registry,
        ledger=ledger,
        ledger_writer=ledger_writer,
        auditor_id=auditor_id,
    )

    # (2) Chain-minimum ceiling evaluation
    evaluation = evaluate_depth_ceiling(
        source_agent_id=source_agent_id,
        upstream_hypothesis_refs=upstream_hypothesis_refs,
        ledger=ledger,
        registry=registry,
        session_id=session_id,
    )

    # (3) Ceiling check (emit BEFORE raise)
    if evaluation.exceeds_ceiling:
        payload = build_depth_limit_payload(
            evaluation=evaluation,
            source_agent_id=source_agent_id,
            upstream_hypothesis_refs=upstream_hypothesis_refs,
            ledger=ledger,
            session_id=session_id,
        )
        emit_depth_limit_reached(
            ledger_writer=ledger_writer,
            ledger=ledger,
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            payload=payload,
        )
        raise DepthLimitExceededError(
            computed_depth=evaluation.computed_depth,
            governing_ceiling=evaluation.governing_ceiling,
            binding_agent_id=evaluation.attribution.binding_agent_id,
            session_id=session_id,
        )

    # (4) Build and validate artifact
    artifact = build_hypothesis(
        session_id=session_id,
        observation_refs=observation_refs,
        synthesis_depth=evaluation.computed_depth,
        upstream_hypothesis_refs=upstream_hypothesis_refs,
        composite_upstream_bme_score=composite_upstream_bme_score,
        hypothesis_text=hypothesis_text,
        confidence_score=confidence_score,
        source_model=source_model,
        reasoning_trace=reasoning_trace,
        tier_justification=tier_justification,
        risk_flags=risk_flags,
        compliance_gaps=compliance_gaps,
        recommendations=recommendations,
        governance_narrative=governance_narrative,
        entropy_assessment=entropy_assessment,
        raw_api_response=raw_api_response,
        cached_response=cached_response,
    )

    # (5) Emit HYPOTHESIS_REGISTERED
    payload = {
        "hypothesis": artifact,
        "governing_ceiling": evaluation.governing_ceiling,
        "ceiling_attribution": {
            "binding_agent_id": evaluation.attribution.binding_agent_id,
            "binding_max_synthesis_depth": evaluation.attribution.binding_max_synthesis_depth,
        },
        "bme_score_source": bme_score_source,
    }
    # prior_event_id: the latest event in the session (commonly an
    # AGENT_HANDOFF if this Hypothesis was synthesized after a handoff).
    # referenced_artifact_id: the Hypothesis being registered.
    # referenced_event_id: if the immediate prior event is an AGENT_HANDOFF
    # that transported an upstream Hypothesis into the source agent's scope,
    # we link it; otherwise null.
    prior_id = _latest_event_id(session_id=session_id, ledger=ledger)
    referenced_event_id = _resolve_handoff_link(
        ledger=ledger, session_id=session_id,
        source_agent_id=source_agent_id,
        upstream_hypothesis_refs=upstream_hypothesis_refs,
    )
    return ledger_writer.append_event(
        event_type="HYPOTHESIS_REGISTERED",
        session_id=session_id,
        auditor_id=auditor_id,
        actor=_build_actor(source_agent_id),
        causal_refs={
            "prior_event_id": prior_id,
            "referenced_artifact_id": artifact["artifact_id"],
            "referenced_event_id": referenced_event_id,
        },
        payload=payload,
    )


def _resolve_handoff_link(
    *,
    ledger: LedgerReader,
    session_id: str,
    source_agent_id: str,
    upstream_hypothesis_refs: list[str],
) -> str | None:
    """If the most recent AGENT_HANDOFF into source_agent_id transported one
    of our upstream_hypothesis_refs, return that handoff's event_id. Else
    None.

    This is the Sprint-2 boundary-ledger-event link (decision f separation):
    handoffs move artifacts but do not count as synthesis hops; however the
    envelope's referenced_event_id slot is the correct place to record the
    causal handoff when synthesis immediately follows it.
    """
    if not upstream_hypothesis_refs:
        return None
    ref_set = set(upstream_hypothesis_refs)
    chosen: tuple[int, str | None] = (-1, None)
    for event in ledger.iter_events(session_id):
        if event.get("event_type") != "AGENT_HANDOFF":
            continue
        payload = event.get("payload") or {}
        handoff = payload.get("agent_handoff") or {}
        if handoff.get("target_agent_id") != source_agent_id:
            continue
        if handoff.get("payload_artifact_id") not in ref_set:
            continue
        seq = event.get("sequence_number", -1)
        if seq > chosen[0]:
            chosen = (seq, event.get("event_id"))
    return chosen[1]


# --- Query helpers ----------------------------------------------------------


def list_session_hypotheses(
    *, session_id: str, ledger: LedgerReader
) -> list[dict]:
    """Return all HYPOTHESIS_REGISTERED payloads for a session, in ledger
    sequence order."""
    out: list[dict] = []
    for event in ledger.iter_events(session_id):
        if event.get("event_type") == "HYPOTHESIS_REGISTERED":
            out.append(event.get("payload", {}))
    return out


def get_hypothesis(
    *, session_id: str, artifact_id: str, ledger: LedgerReader
) -> dict | None:
    """Return the HYPOTHESIS_REGISTERED payload for a specific artifact_id."""
    for event in ledger.iter_events(session_id):
        if event.get("event_type") != "HYPOTHESIS_REGISTERED":
            continue
        hyp = (event.get("payload") or {}).get("hypothesis") or {}
        if hyp.get("artifact_id") == artifact_id:
            return event.get("payload", {})
    return None


__all__ = [
    "FrozenPathError",
    "LedgerWriter",
    "ScopeViolationError",
    "UnregisteredAgentError",
    "UpstreamResolutionError",
    "emit_depth_limit_reached",
    "emit_hypothesis",
    "get_hypothesis",
    "list_session_hypotheses",
    "validate_synthesis_preconditions",
]
