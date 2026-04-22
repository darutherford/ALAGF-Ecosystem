"""BOUNDARY_HANDSHAKE emission and channel lookup.

Governance rationale:
    - Invariant 3 (Evidence-First): peer-level sub-agent channels have
      explicit ledger evidence of their establishment. SUB_AGENT-to-SUB_AGENT
      handoffs check is_channel_established(...) before proceeding; absence
      of the handshake record is an evidence gap that must block the handoff.
    - Invariant 4 (Reconstructability): channel state is derived purely from
      ledger events by scanning BOUNDARY_HANDSHAKE entries. No external
      index is authoritative; the ledger alone answers "is channel A to B
      established?"
    - Directional channels (Sprint-2 decision a): a handshake establishes
      the source-to-target direction only. The reverse direction requires
      its own BOUNDARY_HANDSHAKE event. This preserves per-direction audit
      granularity at the cost of one additional event for bidirectional
      channels.
    - Durable for session (Sprint-2 decision d): once established, a
      channel remains established for the lifetime of both agents' ACTIVE
      status. If either endpoint transitions to SUSPENDED or REVOKED, the
      channel is implicitly unusable (handoff-time checks will reject with
      SOURCE_INACTIVE or TARGET_INACTIVE). No explicit revocation event in
      Sprint-2.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from ...exceptions import (
    BoundaryViolationError,
    HandshakeError,
)
from ...ledger.hash_chain.events import append_event, read_session_events
from ..agent_lifecycle.registration import (
    get_agent_identity,
    is_agent_active,
)


_AUDITOR_ID_PATTERN = re.compile(r"^AUDITOR_[A-Z0-9_]+$")


def _utc_now_iso() -> str:
    """ISO 8601 UTC timestamp with microseconds, Z suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _validate_auditor_id(auditor_id: str) -> None:
    """Orchestrator-layer auditor pattern enforcement."""
    if not _AUDITOR_ID_PATTERN.match(auditor_id):
        # For handshake emission, an invalid auditor at the orchestrator
        # layer is primarily an Invariant-1 (Authority) concern. We route
        # through HandshakeError here because the caller is in the handshake
        # protocol. The API layer additionally emits BOUNDARY_VIOLATION with
        # INVALID_AUDITOR when the rejection is at the HTTP boundary.
        raise HandshakeError(
            f"auditor_id '{auditor_id}' does not match required pattern "
            f"AUDITOR_[A-Z0-9_]+. Invariant 1 (Authority) requires a canonical "
            f"human auditor identifier."
        )


def _emit_boundary_violation(
    *,
    session_id: str,
    auditor_id: str,
    source_agent_id: str,
    target_agent_id: str,
    attempted_artifact_type: str,
    rejection_reason: str,
    detail: str,
    attempted_payload_artifact_id: str | None = None,
) -> dict[str, Any]:
    """Emit a BOUNDARY_VIOLATION event prior to raising the typed exception.

    Shared helper used by both handshake.py and handoff.py. Centralized so
    the emit-then-raise discipline (Invariant 4) cannot be forgotten by
    any caller.
    """
    payload: dict[str, Any] = {
        "attempted_source_agent_id": source_agent_id,
        "attempted_target_agent_id": target_agent_id,
        "attempted_artifact_type": attempted_artifact_type,
        "rejection_reason": rejection_reason,
        "detail": detail,
    }
    if attempted_payload_artifact_id is not None:
        payload["attempted_payload_artifact_id"] = attempted_payload_artifact_id

    return append_event(
        event_type="BOUNDARY_VIOLATION",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "ORCHESTRATOR", "actor_id": "orchestrator"},
        payload=payload,
    )


def _agent_session(agent_id: str) -> str | None:
    """Return the session_id an agent is registered to, or None if unknown."""
    try:
        # get_agent_identity raises UnregisteredAgentError if missing; we
        # also need the session, which is not on the returned artifact.
        # Read the registration record directly via the private helper.
        from ..agent_lifecycle.registration import _session_id_from_registration

        return _session_id_from_registration(agent_id)
    except Exception:
        return None


def emit_handshake(
    *,
    session_id: str,
    auditor_id: str,
    source_agent_id: str,
    target_agent_id: str,
    channel_purpose: str | None = None,
) -> dict[str, Any]:
    """Emit a BOUNDARY_HANDSHAKE event establishing a directional channel.

    Preconditions:
        - auditor_id matches AUDITOR_[A-Z0-9_]+.
        - source_agent_id != target_agent_id.
        - Both agents are registered and ACTIVE in session_id.
          Cross-session handshakes are rejected with CROSS_SESSION.

    Emits a BOUNDARY_VIOLATION event BEFORE raising on any precondition
    failure (Invariant 4). Returns the emitted BOUNDARY_HANDSHAKE event
    on success.

    Raises:
        HandshakeError: any precondition violation except auditor pattern
            handled at API boundary.
        BoundaryViolationError: when precondition failure is categorically
            a boundary issue (cross-session, inactive agent, unregistered).
    """
    _validate_auditor_id(auditor_id)

    if source_agent_id == target_agent_id:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="BoundaryHandshake",
            rejection_reason="SELF_HANDOFF",
            detail="source_agent_id equals target_agent_id.",
        )
        raise HandshakeError(
            f"Handshake rejected: source and target are identical ({source_agent_id})."
        )

    # Registration and activity checks. We must distinguish unregistered
    # from inactive from cross-session to produce the correct rejection_reason.
    source_session = _agent_session(source_agent_id)
    if source_session is None:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="BoundaryHandshake",
            rejection_reason="SOURCE_UNREGISTERED",
            detail=f"source_agent_id '{source_agent_id}' has no registration.",
        )
        raise BoundaryViolationError(
            f"Handshake rejected: source_agent_id '{source_agent_id}' is not registered."
        )
    if source_session != session_id:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="BoundaryHandshake",
            rejection_reason="CROSS_SESSION",
            detail=(
                f"source_agent_id '{source_agent_id}' is registered in "
                f"session '{source_session}', not '{session_id}'."
            ),
        )
        raise BoundaryViolationError(
            f"Handshake rejected: source and handshake session do not match."
        )
    if not is_agent_active(source_agent_id, session_id=session_id):
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="BoundaryHandshake",
            rejection_reason="SOURCE_INACTIVE",
            detail=f"source_agent_id '{source_agent_id}' is not ACTIVE.",
        )
        raise BoundaryViolationError(
            f"Handshake rejected: source_agent_id '{source_agent_id}' is not ACTIVE."
        )

    target_session = _agent_session(target_agent_id)
    if target_session is None:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="BoundaryHandshake",
            rejection_reason="TARGET_UNREGISTERED",
            detail=f"target_agent_id '{target_agent_id}' has no registration.",
        )
        raise BoundaryViolationError(
            f"Handshake rejected: target_agent_id '{target_agent_id}' is not registered."
        )
    if target_session != session_id:
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="BoundaryHandshake",
            rejection_reason="CROSS_SESSION",
            detail=(
                f"target_agent_id '{target_agent_id}' is registered in "
                f"session '{target_session}', not '{session_id}'."
            ),
        )
        raise BoundaryViolationError(
            f"Handshake rejected: target and handshake session do not match."
        )
    if not is_agent_active(target_agent_id, session_id=session_id):
        _emit_boundary_violation(
            session_id=session_id,
            auditor_id=auditor_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            attempted_artifact_type="BoundaryHandshake",
            rejection_reason="TARGET_INACTIVE",
            detail=f"target_agent_id '{target_agent_id}' is not ACTIVE.",
        )
        raise BoundaryViolationError(
            f"Handshake rejected: target_agent_id '{target_agent_id}' is not ACTIVE."
        )

    # All preconditions satisfied. Emit the handshake.
    payload: dict[str, Any] = {
        "source_agent_id": source_agent_id,
        "target_agent_id": target_agent_id,
        "handshake_timestamp": _utc_now_iso(),
    }
    if channel_purpose is not None:
        payload["channel_purpose"] = channel_purpose

    event = append_event(
        event_type="BOUNDARY_HANDSHAKE",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "ORCHESTRATOR", "actor_id": "orchestrator"},
        payload=payload,
    )
    return event


def is_channel_established(
    *,
    session_id: str,
    source_agent_id: str,
    target_agent_id: str,
) -> bool:
    """Return True iff a directional BOUNDARY_HANDSHAKE exists for (source -> target).

    Derived purely from ledger events (Invariant 4): scans the session's
    event log for a matching BOUNDARY_HANDSHAKE. Directionality is strict —
    an A-to-B handshake does NOT satisfy a B-to-A query.
    """
    events = read_session_events(session_id)
    for e in events:
        if e["event_type"] != "BOUNDARY_HANDSHAKE":
            continue
        p = e["payload"]
        if (
            p["source_agent_id"] == source_agent_id
            and p["target_agent_id"] == target_agent_id
        ):
            return True
    return False


def list_established_channels(session_id: str) -> list[dict[str, str]]:
    """Return all established directional channels in the session.

    Each entry has keys source_agent_id, target_agent_id, handshake_event_id,
    handshake_timestamp, and optionally channel_purpose. Ordered by
    sequence_number (handshake emission order).
    """
    events = read_session_events(session_id)
    channels: list[dict[str, str]] = []
    for e in events:
        if e["event_type"] != "BOUNDARY_HANDSHAKE":
            continue
        p = e["payload"]
        entry: dict[str, str] = {
            "source_agent_id": p["source_agent_id"],
            "target_agent_id": p["target_agent_id"],
            "handshake_event_id": e["event_id"],
            "handshake_timestamp": p["handshake_timestamp"],
        }
        if "channel_purpose" in p:
            entry["channel_purpose"] = p["channel_purpose"]
        channels.append(entry)
    return channels
