"""AgentHandoff factory, validation, and serialization.

Governance rationale:
    - Invariant 1 (Authority): the factory REJECTS any attempt to construct
      an AgentHandoff with non_authoritative_flag set to any value other
      than true. Handoffs record, they do not authorize. The schema's
      const: true already catches a false value at validation; the factory
      produces an AuthorityViolationError so callers can distinguish an
      Invariant-1 breach from a general schema failure.
    - Invariant 4 (Reconstructability): the factory generates a canonical
      artifact_id in the HOF_<12 hex> format so handoffs are uniformly
      identifiable across the ledger.

Design note:
    The v2 AgentHandoff schema permits source_agent_id, target_agent_id,
    and payload_artifact_id as any non-empty string. The factory does NOT
    enforce registration, activity, or discoverability. Those preconditions
    are the responsibility of the orchestrator's boundary_enforcement layer,
    which runs BEFORE calling this factory. Separation of concerns:
    schema validity here, session-scoped precondition checks there.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from ..ContractValidator import ContractValidator
from ...exceptions import AuthorityViolationError


def generate_handoff_id() -> str:
    """Generate a canonical handoff artifact_id in the HOF_<12 hex> format.

    Governance rationale: matches the AGT_<12 hex> agent_id convention for
    cross-artifact visual consistency. secrets module used for unpredictability.
    """
    return f"HOF_{secrets.token_hex(6)}"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string with microseconds."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def build_agent_handoff(
    *,
    session_id: str,
    source_agent_id: str,
    target_agent_id: str,
    payload_artifact_id: str,
    artifact_id: str | None = None,
    handoff_timestamp: str | None = None,
    non_authoritative_flag: bool | None = None,
) -> dict[str, Any]:
    """Construct and validate an AgentHandoff artifact.

    The non_authoritative_flag parameter exists only to enforce the invariant:
    if provided, it MUST be true or omitted. Any other value raises
    AuthorityViolationError. The constructed artifact always carries
    non_authoritative_flag: true.

    Raises:
        AuthorityViolationError: if non_authoritative_flag is passed as
            anything other than true.
        ArtifactValidationError: if the constructed artifact fails JSON
            Schema validation (pattern mismatch on artifact_id or session_id,
            missing required fields, invalid authority_level).
    """
    # --- Invariant 1 enforcement (runtime layer) ---
    # The schema's const: true already ensures ArtifactValidationError on a
    # literally-false input. We ALSO reject here to produce an authority-typed
    # exception distinguishable from general schema failures.
    if non_authoritative_flag is not None and non_authoritative_flag is not True:
        raise AuthorityViolationError(
            "AgentHandoff.non_authoritative_flag is hard-coded true and "
            "non-overridable. Invariant 1 (Authority) violation."
        )

    artifact: dict[str, Any] = {
        "artifact_type": "AgentHandoff",
        "authority_level": "orchestration",
        "artifact_id": artifact_id or generate_handoff_id(),
        "session_id": session_id,
        "source_agent_id": source_agent_id,
        "target_agent_id": target_agent_id,
        "payload_artifact_id": payload_artifact_id,
        "handoff_timestamp": handoff_timestamp or utc_now_iso(),
        "non_authoritative_flag": True,  # HARD-CODED — not caller-controlled
    }

    ContractValidator.validate("AgentHandoff", artifact)
    return artifact
