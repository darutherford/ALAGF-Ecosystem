"""Agent lifecycle orchestrator.

Functions in this module are the only sanctioned path to create and transition
AgentIdentity state. They enforce Sprint-1 invariants:

    - Invariant 1: auditor_id must match AUDITOR_[A-Z0-9_]+ pattern
      (orchestrator-layer stricter enforcement on top of the v2 schema).
    - Invariant 1: registered_by cannot equal any agent_id in the session.
    - Invariant 3: every state transition emits a ledger event with causal
      refs to the registration event.
    - Invariant 4: all agent files are append-only. Status transitions write
      new files under <agent_id>__<status>__<event_id>.json; the original
      registration file is never modified.

Registry file layout:

    /multiagent/ledger/agent_registry/
        <agent_id>.json                               (registration; the ACTIVE record)
        <agent_id>__SUSPENDED__<event_id>.json        (suspension marker)
        <agent_id>__REVOKED__<event_id>.json          (revocation marker)

Live status is determined by scanning for markers. Append-only means the
registration file is never updated; status is computed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from ...artifacts.AgentIdentity import build_agent_identity, utc_now_iso
from ...artifacts.ContractValidator import ContractValidator
from ...exceptions import (
    AgentRegistrationError,
    AuthorityViolationError,
    UnregisteredAgentError,
)
from ...ledger.hash_chain.events import append_event


_AUDITOR_ID_PATTERN = re.compile(r"^AUDITOR_[A-Z0-9_]+$")

# Resolve registry directory relative to this file.
# /multiagent/orchestrator/agent_lifecycle/registration.py ->
# /multiagent/ledger/agent_registry/
_THIS_FILE = Path(__file__).resolve()
_MULTIAGENT_ROOT = _THIS_FILE.parent.parent.parent
_REGISTRY_DIR = _MULTIAGENT_ROOT / "ledger" / "agent_registry"


AgentType = Literal["ORCHESTRATOR", "SUB_AGENT", "VALIDATOR", "HUMAN_PROXY"]
TrustTier = Literal["T1", "T2", "T3", "T4"]
AuthorityScope = Literal["OBSERVATIONS_ONLY", "HYPOTHESES", "ROUTING"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_registry_dir() -> None:
    _REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


def _registration_path(agent_id: str) -> Path:
    return _REGISTRY_DIR / f"{agent_id}.json"


def _marker_path(agent_id: str, status: str, event_id: str) -> Path:
    return _REGISTRY_DIR / f"{agent_id}__{status}__{event_id}.json"


def _validate_auditor_id(auditor_id: str) -> None:
    if not _AUDITOR_ID_PATTERN.match(auditor_id):
        raise AuthorityViolationError(
            f"auditor_id '{auditor_id}' does not match required pattern "
            f"AUDITOR_[A-Z0-9_]+. Invariant 1 (Authority) requires a canonical "
            f"human auditor identifier."
        )


def _load_registration(agent_id: str) -> dict[str, Any] | None:
    path = _registration_path(agent_id)
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _list_markers(agent_id: str, status: str) -> list[Path]:
    pattern = f"{agent_id}__{status}__*.json"
    return sorted(_REGISTRY_DIR.glob(pattern))


def _resolve_current_status(agent_id: str) -> str | None:
    """Determine the effective status of an agent by scanning markers.

    Returns None if the agent is not registered. Otherwise returns one of
    ACTIVE, SUSPENDED, REVOKED. REVOKED is terminal and takes precedence.
    """
    if _load_registration(agent_id) is None:
        return None
    if _list_markers(agent_id, "REVOKED"):
        return "REVOKED"
    if _list_markers(agent_id, "SUSPENDED"):
        return "SUSPENDED"
    return "ACTIVE"


def _find_registration_event_id(agent_id: str) -> str | None:
    """Read the agent's registration file to extract the ledger event id.

    The registration event id is stored alongside the artifact at
    registration time under the '_registration_event_id' meta key.
    """
    registration = _load_registration(agent_id)
    if registration is None:
        return None
    return registration.get("_registration_event_id")


def _session_id_from_registration(agent_id: str) -> str | None:
    registration = _load_registration(agent_id)
    if registration is None:
        return None
    return registration.get("_session_id")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def register_agent(
    *,
    session_id: str,
    auditor_id: str,
    agent_type: AgentType,
    model_id: str,
    provider: str,
    trust_tier: TrustTier,
    authority_scope: AuthorityScope,
    max_synthesis_depth: int,
    parent_agent_id: str | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Register a new agent and emit an AGENT_REGISTERED ledger event.

    Returns the registration record written to disk (includes the artifact
    plus meta fields _session_id and _registration_event_id).

    Raises:
        AuthorityViolationError: if auditor_id does not match the required
            pattern, or if registered_by matches an existing agent_id.
        AgentRegistrationError: if the agent_id is already registered in
            this or any other session, or if schema validation fails.
    """
    _ensure_registry_dir()
    _validate_auditor_id(auditor_id)

    # Invariant 1 — registered_by must not collide with any existing agent_id.
    # We scan the registry directory for collisions. The human auditor pattern
    # (AUDITOR_*) makes collision practically impossible, but we still check.
    if (_REGISTRY_DIR / f"{auditor_id}.json").exists():
        raise AuthorityViolationError(
            f"auditor_id '{auditor_id}' collides with a registered agent_id. "
            f"registered_by must resolve to a human identity."
        )

    # Build and schema-validate the artifact.
    artifact = build_agent_identity(
        agent_type=agent_type,
        model_id=model_id,
        provider=provider,
        trust_tier=trust_tier,
        authority_scope=authority_scope,
        registered_by=auditor_id,
        max_synthesis_depth=max_synthesis_depth,
        parent_agent_id=parent_agent_id,
        agent_id=agent_id,
        status="ACTIVE",
    )
    final_agent_id = artifact["agent_id"]

    # Duplicate registration check — append-only discipline.
    if _load_registration(final_agent_id) is not None:
        raise AgentRegistrationError(
            f"agent_id '{final_agent_id}' is already registered. "
            f"Append-only: re-activation requires a new agent_id."
        )

    # Parent must exist and be ACTIVE for SUB_AGENT / VALIDATOR.
    if agent_type in ("SUB_AGENT", "VALIDATOR"):
        if parent_agent_id is None:
            # The schema's allOf should have caught this already. Defense in depth.
            raise AgentRegistrationError(
                f"{agent_type} requires parent_agent_id. Schema enforcement "
                f"escaped; this is a bug."
            )
        parent_status = _resolve_current_status(parent_agent_id)
        if parent_status is None:
            raise AgentRegistrationError(
                f"parent_agent_id '{parent_agent_id}' is not registered."
            )
        if parent_status != "ACTIVE":
            raise AgentRegistrationError(
                f"parent_agent_id '{parent_agent_id}' is not ACTIVE "
                f"(current status: {parent_status})."
            )

    # Emit the AGENT_REGISTERED ledger event.
    registration_event = append_event(
        event_type="AGENT_REGISTERED",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "HUMAN", "actor_id": auditor_id},
        payload={"agent_identity": artifact},
        referenced_artifact_id=final_agent_id,
    )

    # Persist the registration file. Includes meta fields that are NOT part
    # of the AgentIdentity artifact contract, hence the leading underscore.
    record = dict(artifact)
    record["_session_id"] = session_id
    record["_registration_event_id"] = registration_event["event_id"]

    registration_path = _registration_path(final_agent_id)
    # Use O_EXCL here too. Any collision is a bug given we checked above.
    with registration_path.open("x", encoding="utf-8") as fh:
        json.dump(record, fh, sort_keys=True, indent=2)

    return record


def get_agent_identity(agent_id: str) -> dict[str, Any]:
    """Retrieve an agent's registration record.

    Returns the record with meta fields stripped (pure artifact plus
    the resolved current status).

    Raises:
        UnregisteredAgentError: if the agent_id is not in the registry.
    """
    registration = _load_registration(agent_id)
    if registration is None:
        raise UnregisteredAgentError(
            f"agent_id '{agent_id}' is not registered."
        )
    current_status = _resolve_current_status(agent_id)
    # Return the artifact with the live-computed status, not the originally
    # registered one. Meta fields stripped.
    artifact = {k: v for k, v in registration.items() if not k.startswith("_")}
    artifact["status"] = current_status
    # If REVOKED, populate revocation_event_ref from the marker.
    if current_status == "REVOKED":
        markers = _list_markers(agent_id, "REVOKED")
        if markers:
            with markers[0].open("r", encoding="utf-8") as fh:
                marker = json.load(fh)
            artifact["revocation_event_ref"] = marker.get("event_id")
    return artifact


def is_agent_active(agent_id: str, session_id: str | None = None) -> bool:
    """Return True iff the agent is registered, ACTIVE, and (if session_id
    supplied) registered in that session."""
    status = _resolve_current_status(agent_id)
    if status != "ACTIVE":
        return False
    if session_id is not None:
        registered_session = _session_id_from_registration(agent_id)
        if registered_session != session_id:
            return False
    return True


def suspend_agent(
    *,
    agent_id: str,
    auditor_id: str,
    reason: str,
) -> dict[str, Any]:
    """Transition an ACTIVE agent to SUSPENDED.

    Raises:
        UnregisteredAgentError: if agent is not registered.
        AgentRegistrationError: if agent is already SUSPENDED or REVOKED.
        AuthorityViolationError: if auditor_id is malformed.
    """
    _validate_auditor_id(auditor_id)

    status = _resolve_current_status(agent_id)
    if status is None:
        raise UnregisteredAgentError(f"agent_id '{agent_id}' is not registered.")
    if status != "ACTIVE":
        raise AgentRegistrationError(
            f"agent_id '{agent_id}' cannot be suspended from status {status}."
        )

    session_id = _session_id_from_registration(agent_id)
    registration_event_id = _find_registration_event_id(agent_id)
    if session_id is None or registration_event_id is None:
        raise AgentRegistrationError(
            f"Registration record for '{agent_id}' is missing session or event metadata."
        )

    event = append_event(
        event_type="AGENT_SUSPENDED",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "HUMAN", "actor_id": auditor_id},
        payload={
            "agent_id": agent_id,
            "reason": reason,
            "prior_registration_event_id": registration_event_id,
        },
        prior_event_id=registration_event_id,
        referenced_artifact_id=agent_id,
        referenced_event_id=registration_event_id,
    )

    marker = {
        "agent_id": agent_id,
        "status": "SUSPENDED",
        "event_id": event["event_id"],
        "suspended_at": event["timestamp_utc"],
        "auditor_id": auditor_id,
        "reason": reason,
    }
    marker_path = _marker_path(agent_id, "SUSPENDED", event["event_id"])
    with marker_path.open("x", encoding="utf-8") as fh:
        json.dump(marker, fh, sort_keys=True, indent=2)
    return event


def revoke_agent(
    *,
    agent_id: str,
    auditor_id: str,
    reason: str,
) -> dict[str, Any]:
    """Transition an agent to REVOKED. Terminal. Re-activation impossible.

    Governance rationale: REVOKED is architecturally terminal. A new
    registration requires a new agent_id. This is enforced by the
    duplicate-registration check in register_agent().
    """
    _validate_auditor_id(auditor_id)

    status = _resolve_current_status(agent_id)
    if status is None:
        raise UnregisteredAgentError(f"agent_id '{agent_id}' is not registered.")
    if status == "REVOKED":
        raise AgentRegistrationError(f"agent_id '{agent_id}' is already REVOKED.")

    session_id = _session_id_from_registration(agent_id)
    registration_event_id = _find_registration_event_id(agent_id)
    if session_id is None or registration_event_id is None:
        raise AgentRegistrationError(
            f"Registration record for '{agent_id}' is missing session or event metadata."
        )

    event = append_event(
        event_type="AGENT_REVOKED",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "HUMAN", "actor_id": auditor_id},
        payload={
            "agent_id": agent_id,
            "reason": reason,
            "prior_registration_event_id": registration_event_id,
        },
        prior_event_id=registration_event_id,
        referenced_artifact_id=agent_id,
        referenced_event_id=registration_event_id,
    )

    marker = {
        "agent_id": agent_id,
        "status": "REVOKED",
        "event_id": event["event_id"],
        "revoked_at": event["timestamp_utc"],
        "auditor_id": auditor_id,
        "reason": reason,
    }
    marker_path = _marker_path(agent_id, "REVOKED", event["event_id"])
    with marker_path.open("x", encoding="utf-8") as fh:
        json.dump(marker, fh, sort_keys=True, indent=2)
    return event


def list_session_active_agents(session_id: str) -> list[dict[str, str]]:
    """Return compact records of all ACTIVE agents for a session."""
    _ensure_registry_dir()
    active: list[dict[str, str]] = []
    for path in sorted(_REGISTRY_DIR.glob("*.json")):
        # Skip marker files (they include double underscores).
        if "__" in path.stem:
            continue
        with path.open("r", encoding="utf-8") as fh:
            record = json.load(fh)
        if record.get("_session_id") != session_id:
            continue
        agent_id = record["agent_id"]
        if _resolve_current_status(agent_id) != "ACTIVE":
            continue
        active.append(
            {
                "agent_id": agent_id,
                "agent_type": record["agent_type"],
                "registration_event_id": record["_registration_event_id"],
            }
        )
    return active


def emit_session_registry(
    *,
    session_id: str,
    auditor_id: str,
) -> dict[str, Any]:
    """Emit an AGENT_SESSION_REGISTRY snapshot event for the session.

    This is the manifest of all ACTIVE agents at the moment of emission.
    """
    _validate_auditor_id(auditor_id)
    active_agents = list_session_active_agents(session_id)
    event = append_event(
        event_type="AGENT_SESSION_REGISTRY",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "HUMAN", "actor_id": auditor_id},
        payload={
            "session_id": session_id,
            "active_agents": active_agents,
            "snapshot_timestamp": utc_now_iso(),
        },
    )
    return event


def reject_unregistered_output(
    *,
    session_id: str,
    auditor_id: str,
    attempted_agent_id: str,
    artifact_type: str,
) -> dict[str, Any]:
    """Emit an UNREGISTERED_AGENT_OUTPUT event BEFORE rejecting, then raise.

    Governance rationale: Invariant 4 requires every failure path produce a
    ledger event. Silent rejection is prohibited. This helper centralizes
    the emit-then-raise pattern so callers cannot forget the event.

    Determines the appropriate rejection_reason based on the agent's state:
        - NOT_REGISTERED: no registration record exists.
        - SUSPENDED / REVOKED: record exists but status forbids output.
        - SESSION_MISMATCH: registered in a different session.
    """
    _validate_auditor_id(auditor_id)

    status = _resolve_current_status(attempted_agent_id)
    if status is None:
        reason = "NOT_REGISTERED"
    elif status in ("SUSPENDED", "REVOKED"):
        reason = status
    else:
        registered_session = _session_id_from_registration(attempted_agent_id)
        if registered_session != session_id:
            reason = "SESSION_MISMATCH"
        else:
            # Should not happen: agent is ACTIVE in this session but caller
            # invoked rejection. Still emit the event, tagged as mismatch.
            reason = "SESSION_MISMATCH"

    event = append_event(
        event_type="UNREGISTERED_AGENT_OUTPUT",
        session_id=session_id,
        auditor_id=auditor_id,
        actor={"actor_type": "ORCHESTRATOR", "actor_id": "orchestrator"},
        payload={
            "attempted_agent_id": attempted_agent_id,
            "artifact_type": artifact_type,
            "rejection_reason": reason,
        },
        referenced_artifact_id=attempted_agent_id,
    )
    raise UnregisteredAgentError(
        f"Rejected output from agent '{attempted_agent_id}': {reason}. "
        f"Ledger event {event['event_id']} emitted."
    )
