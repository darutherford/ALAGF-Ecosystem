"""AGENT_HANDOFF emission with full precondition validation.

Governance rationale:
    - Invariant 1 (Authority): handoffs cannot carry binding-authority
      payloads. BINDING_PAYLOAD rejection prevents an AI-to-AI boundary
      crossing from transporting Decision-equivalent artifacts. Binding
      artifacts cross only through a human Decision gate, not via handoff.
    - Invariant 2 (Non-Bypass, forward compatibility): handoff emission
      does not produce an Action. Decision-referenced authority remains
      the sole pathway to Action execution. The handoff layer introduces
      no code path that weakens future delegation_blocked enforcement.
    - Invariant 3 (Evidence-First): every precondition failure is
      categorized into a closed rejection_reason enum. Peer-level
      SUB_AGENT/VALIDATOR handoffs require a prior BOUNDARY_HANDSHAKE;
      absence is treated as an evidence gap.
    - Invariant 4 (Reconstructability): every boundary crossing (accepted
      or rejected) produces exactly one first-class ledger event. Accepted
      crossings produce AGENT_HANDOFF; rejections produce BOUNDARY_VIOLATION
      BEFORE the typed exception is raised.

Sprint-2 decisions applied:
    (a) Directional handshakes — peer-to-peer handoffs check the exact
        (source -> target) direction.
    (b) Union discoverability — payload_artifact_id resolves if present
        in the agent registry OR referenced by a prior ledger event.
    (d) Durable-for-session handshakes — no explicit revocation in Sprint-2;
        implicit invalidation via agent status change is caught by the
        SOURCE_INACTIVE/TARGET_INACTIVE checks.
    (e) VALIDATOR origination restriction — may only originate to
        ORCHESTRATOR or HUMAN_PROXY.
    (f) HUMAN_PROXY origination restriction — may only originate to
        ORCHESTRATOR (prevents Decision-gate bypass).
"""

from __future__ import annotations

import re
from typing import Any

from ...artifacts.AgentHandoff import build_agent_handoff
from ...exceptions import (
    BoundaryViolationError,
    HandshakeError,
)
from ...ledger.hash_chain.events import append_event, read_session_events
from ..agent_lifecycle.registration import (
    get_agent_identity,
    is_agent_active,
)
from .handshake import (
    _emit_boundary_violation,
    is_channel_established,
)


_AUDITOR_ID_PATTERN = re.compile(r"^AUDITOR_[A-Z0-9_]+$")


def _validate_auditor_id(auditor_id: str) -> None:
    """Orchestrator-layer auditor pattern enforcement.

    At the orchestrator layer we raise BoundaryViolationError. At the API
    boundary the handler additionally emits a BOUNDARY_VIOLATION event with
    INVALID_AUDITOR before translating to HTTP 401/403.
    """
    if not _AUDITOR_ID_PATTERN.match(auditor_id):
        raise BoundaryViolationError(
            f"auditor_id '{auditor_id}' does not match required pattern "
            f"AUDITOR_[A-Z0-9_]+."
        )


def _agent_session(agent_id: str) -> str | None:
    """Return the session_id an agent is registered to, or None if unknown."""
    from ..agent_lifecycle.registration import _session_id_from_registration

    return _session_id_from_registration(agent_id)


def _agent_type(agent_id: str) -> str | None:
    """Return an agent's declared agent_type, or None if unregistered."""
    try:
        artifact = get_agent_identity(agent_id)
    except Exception:
        return None
    return artifact.get("agent_type")


def _resolve_payload_authority(
    *, session_id: str, payload_artifact_id: str
) -> tuple[bool, str | None]:
    """Resolve discoverability and authority_level for a payload artifact.

    Returns (discoverable, authority_level). discoverable is True if the
    payload_artifact_id resolves to an AgentIdentity in the registry or to
    an artifact embedded in a prior ledger event in the session.
    authority_level is the declared authority of the resolved artifact, or
    None if the artifact does not declare one.

    Governance rationale (Sprint-2 decision b): union discoverability —
    registry OR prior ledger event satisfies the precondition.
    """
    # Registry path: payload_artifact_id may name a registered agent.
    try:
        agent = get_agent_identity(payload_artifact_id)
        # AgentIdentity always carries authority_level: non_binding (schema const).
        return True, agent.get("authority_level")
    except Exception:
        pass

    # Ledger path: scan prior events in the session for a payload-embedded
    # artifact with a matching identifier field. Known locations:
    #   - AGENT_REGISTERED.payload.agent_identity.agent_id
    #   - AGENT_HANDOFF.payload.agent_handoff.artifact_id
    #   - AGENT_HANDOFF.payload.agent_handoff.payload_artifact_id (if a
    #     prior handoff transported this artifact, it is discoverable)
    #   - causal_refs.referenced_artifact_id (last-resort match)
    #
    # Priority order: payload-embedded matches first so we can read the
    # declared authority_level. Envelope-level referenced_artifact_id is a
    # fallback that returns authority_level=None (safe default — the caller
    # must treat absence as non-binding to avoid false rejections on
    # future event types, but this weakens BINDING_PAYLOAD enforcement for
    # artifacts referenced only at the envelope level).
    try:
        events = read_session_events(session_id)
    except Exception:
        events = []

    envelope_ref_hit = False
    for e in events:
        p = e.get("payload", {})
        # AGENT_REGISTERED embeds an AgentIdentity.
        if e["event_type"] == "AGENT_REGISTERED":
            ai = p.get("agent_identity", {})
            if ai.get("agent_id") == payload_artifact_id:
                return True, ai.get("authority_level")
        # AGENT_HANDOFF embeds an AgentHandoff; either its own id or its
        # payload_artifact_id count as prior ledger references.
        elif e["event_type"] == "AGENT_HANDOFF":
            ah = p.get("agent_handoff", {})
            if ah.get("artifact_id") == payload_artifact_id:
                return True, ah.get("authority_level")
            if ah.get("payload_artifact_id") == payload_artifact_id:
                # Re-use of a previously transported payload counts as
                # discoverable. authority_level of the inner payload is
                # unknown at this layer; return None for safe default.
                return True, None
        # Track envelope-level hits but do NOT return yet — a later event
        # may embed the artifact directly and let us read its authority_level.
        if e.get("causal_refs", {}).get("referenced_artifact_id") == payload_artifact_id:
            envelope_ref_hit = True

    if envelope_ref_hit:
        return True, None

    return False, None


def _is_peer_pair(source_type: str | None, target_type: str | None) -> bool:
    """True iff the pair is peer-level and requires a prior handshake.

    Peer pairs are any combination of SUB_AGENT and VALIDATOR endpoints
    with no ORCHESTRATOR or HUMAN_PROXY involvement. ORCHESTRATOR-involving
    handoffs rely on parent-child registration; HUMAN_PROXY-involving
    handoffs are either HITL routing (target) or ORCHESTRATOR-bound (source),
    neither requiring a handshake.
    """
    peer_types = {"SUB_AGENT", "VALIDATOR"}
    return (source_type in peer_types) and (target_type in peer_types)


def _check_origination_rules(
    source_type: str | None, target_type: str | None
) -> str | None:
    """Apply Sprint-2 origination restrictions (decisions e and f).

    Returns a rejection_reason string if the origination is disallowed,
    or None if permitted.
    """
    if source_type == "VALIDATOR" and target_type not in ("ORCHESTRATOR", "HUMAN_PROXY"):
        return "DISALLOWED_ORIGINATOR_VALIDATOR"
    if source_type == "HUMAN_PROXY" and target_type != "ORCHESTRATOR":
        return "DISALLOWED_ORIGINATOR_HUMAN_PROXY"
    return None


def validate_handoff_preconditions(
    *,
    session_id: str,
    source_agent_id: str,
    target_agent_id: str,
    payload_artifact_id: str,
) -> None:
    """Run all Sprint-2 handoff preconditions as a pure validator (no emission).

    Raises BoundaryViolationError or HandshakeError with a descriptive
    message on the FIRST failed precondition. Does NOT emit a
    BOUNDARY_VIOLATION event — that is the responsibility of emit_handoff
    when enforcement is performed in the full emit-or-reject pathway.

    This function exists primarily for API-layer dry-run validation and for
    tests that assert specific failure modes without producing a ledger
    event as a side effect. Production enforcement flows through
    emit_handoff.
    """
    if source_agent_id == target_agent_id:
        raise BoundaryViolationError(
            f"Self-handoff rejected: source equals target ({source_agent_id})."
        )

    source_session = _agent_session(source_agent_id)
    if source_session is None:
        raise BoundaryViolationError(
            f"source_agent_id '{source_agent_id}' is not registered."
        )
    if source_session != session_id:
        raise BoundaryViolationError(
            f"source_agent_id '{source_agent_id}' registered in different session."
        )
    if not is_agent_active(source_agent_id, session_id=session_id):
        raise BoundaryViolationError(
            f"source_agent_id '{source_agent_id}' is not ACTIVE."
        )

    target_session = _agent_session(target_agent_id)
    if target_session is None:
        raise BoundaryViolationError(
            f"target_agent_id '{target_agent_id}' is not registered."
        )
    if target_session != session_id:
        raise BoundaryViolationError(
            f"target_agent_id '{target_agent_id}' registered in different session."
        )
    if not is_agent_active(target_agent_id, session_id=session_id):
        raise BoundaryViolationError(
            f"target_agent_id '{target_agent_id}' is not ACTIVE."
        )

    source_type = _agent_type(source_agent_id)
    target_type = _agent_type(target_agent_id)

    orig_reason = _check_origination_rules(source_type, target_type)
    if orig_reason is not None:
        raise BoundaryViolationError(
            f"Origination rejected: {source_type} -> {target_type} ({orig_reason})."
        )

    discoverable, authority_level = _resolve_payload_authority(
        session_id=session_id, payload_artifact_id=payload_artifact_id
    )
    if not discoverable:
        raise BoundaryViolationError(
            f"payload_artifact_id '{payload_artifact_id}' is not discoverable."
        )
    if authority_level == "binding":
        raise BoundaryViolationError(
            f"payload_artifact_id '{payload_artifact_id}' has binding authority; "
            f"handoffs cannot transport binding payloads."
        )

    if _is_peer_pair(source_type, target_type):
        if not is_channel_established(
            session_id=session_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
        ):
            raise HandshakeError(
                f"Peer handoff {source_agent_id} -> {target_agent_id} rejected: "
                f"no prior BOUNDARY_HANDSHAKE."
            )


def emit_handoff(
    *,
    session_id: str,
    auditor_id: str,
    source_agent_id: str,
    target_agent_id: str,
    payload_artifact_id: str,
) -> dict[str, Any]:
    """Emit an AGENT_HANDOFF event after full precondition validation.

    On precondition failure, emits BOUNDARY_VIOLATION with the specific
    rejection_reason BEFORE raising BoundaryViolationError or HandshakeError.
    On success, constructs and validates an AgentHandoff artifact, then
    writes the AGENT_HANDOFF ledger event embedding that artifact.

    Raises:
        BoundaryViolationError: on any precondition failure except missing
            peer handshake.
        HandshakeError: on missing prior BOUNDARY_HANDSHAKE for peer-level
            (SUB_AGENT / VALIDATOR) pair.
    """
    _validate_auditor_id(auditor_id)

    # Self-handoff
    if source_agent_id == target_agent_id:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="SELF_HANDOFF",
            detail="source_agent_id equals target_agent_id.",
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: source and target are identical ({source_agent_id})."
        )

    # Source registration and activity
    source_session = _agent_session(source_agent_id)
    if source_session is None:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="SOURCE_UNREGISTERED",
            detail=f"source_agent_id '{source_agent_id}' has no registration.",
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: source_agent_id '{source_agent_id}' is not registered."
        )
    if source_session != session_id:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="CROSS_SESSION",
            detail=(
                f"source_agent_id '{source_agent_id}' registered in session "
                f"'{source_session}', not '{session_id}'."
            ),
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: source session mismatch."
        )
    if not is_agent_active(source_agent_id, session_id=session_id):
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="SOURCE_INACTIVE",
            detail=f"source_agent_id '{source_agent_id}' is not ACTIVE.",
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: source_agent_id '{source_agent_id}' is not ACTIVE."
        )

    # Target registration and activity
    target_session = _agent_session(target_agent_id)
    if target_session is None:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="TARGET_UNREGISTERED",
            detail=f"target_agent_id '{target_agent_id}' has no registration.",
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: target_agent_id '{target_agent_id}' is not registered."
        )
    if target_session != session_id:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="CROSS_SESSION",
            detail=(
                f"target_agent_id '{target_agent_id}' registered in session "
                f"'{target_session}', not '{session_id}'."
            ),
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: target session mismatch."
        )
    if not is_agent_active(target_agent_id, session_id=session_id):
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="TARGET_INACTIVE",
            detail=f"target_agent_id '{target_agent_id}' is not ACTIVE.",
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: target_agent_id '{target_agent_id}' is not ACTIVE."
        )

    # Agent-type origination rules (decisions e and f)
    source_type = _agent_type(source_agent_id)
    target_type = _agent_type(target_agent_id)
    orig_reason = _check_origination_rules(source_type, target_type)
    if orig_reason is not None:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason=orig_reason,
            detail=(
                f"{source_type} may not originate a handoff to {target_type}."
            ),
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: {source_type} -> {target_type} ({orig_reason})."
        )

    # Payload discoverability and authority check
    discoverable, authority_level = _resolve_payload_authority(
        session_id=session_id, payload_artifact_id=payload_artifact_id
    )
    if not discoverable:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="UNKNOWN_PAYLOAD",
            detail=(
                f"payload_artifact_id '{payload_artifact_id}' not found in "
                f"registry or prior ledger events for session '{session_id}'."
            ),
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: payload_artifact_id '{payload_artifact_id}' is not discoverable."
        )
    if authority_level == "binding":
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="AgentHandoff",
            rejection_reason="BINDING_PAYLOAD",
            detail=(
                f"payload_artifact_id '{payload_artifact_id}' has "
                f"authority_level='binding'; Invariant 1 prohibits binding "
                f"payloads from traversing agent handoffs."
            ),
            attempted_payload_artifact_id=payload_artifact_id,
        )
        raise BoundaryViolationError(
            f"Handoff rejected: binding payload cannot traverse agent boundary."
        )

    # Handshake requirement (peer-level pairs only)
    if _is_peer_pair(source_type, target_type):
        if not is_channel_established(
            session_id=session_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
        ):
            _emit_boundary_violation(
                session_id=session_id,
                auditor_id=auditor_id,
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
                attempted_artifact_type="AgentHandoff",
                rejection_reason="MISSING_HANDSHAKE",
                detail=(
                    f"Peer handoff {source_agent_id} -> {target_agent_id} "
                    f"requires a prior BOUNDARY_HANDSHAKE in this direction."
                ),
                attempted_payload_artifact_id=payload_artifact_id,
            )
            raise HandshakeError(
                f"Handoff rejected: peer-level handoff requires prior handshake."
            )

    # All preconditions satisfied. Build and emit.
    handoff_artifact = build_agent_handoff(
        session_id=session_id,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        payload_artifact_id=payload_artifact_id,
    )
    event = append_event(
        event_type="AGENT_HANDOFF",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "ORCHESTRATOR", "actor_id": "orchestrator"},
        payload={"agent_handoff": handoff_artifact},
        referenced_artifact_id=handoff_artifact["artifact_id"],
    )
    return event


def get_handoff(session_id: str, handoff_id: str) -> dict[str, Any]:
    """Retrieve a specific AGENT_HANDOFF event by handoff artifact_id.

    Raises BoundaryViolationError if not found. Pure-ledger derivation:
    scans the session's events for an AGENT_HANDOFF whose embedded
    artifact_id matches.
    """
    events = read_session_events(session_id)
    for e in events:
        if e["event_type"] != "AGENT_HANDOFF":
            continue
        if e["payload"]["agent_handoff"]["artifact_id"] == handoff_id:
            return e
    raise BoundaryViolationError(
        f"Handoff '{handoff_id}' not found in session '{session_id}'."
    )


def list_session_handoffs(session_id: str) -> list[dict[str, Any]]:
    """Return all AGENT_HANDOFF events for a session, ordered by sequence_number."""
    events = read_session_events(session_id)
    return [e for e in events if e["event_type"] == "AGENT_HANDOFF"]
