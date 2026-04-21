"""AgentIdentity factory, validation, and serialization.

Governance rationale:
    - Invariant 1 (Authority): the factory REJECTS any attempt to construct
      an AgentIdentity with non_authoritative_flag set to any value other
      than true. The flag is set internally and cannot be passed as an input.
    - Invariant 4 (Reconstructability): the factory generates a canonical
      agent_id in the AGT_<12 hex> format so identities are uniform across
      the ledger even though the v2 schema permits any non-empty string.

Design note:
    The v2 AgentIdentity schema permits agent_id as any non-empty string.
    Sprint-1 decision 1(b): the factory generates AGT_<12 hex>; external
    callers can still submit other formats and pass schema validation, but
    the primary orchestrator flow uses factory-generated IDs.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Literal

from ..ContractValidator import ContractValidator
from ...exceptions import ArtifactValidationError, AuthorityViolationError


AgentType = Literal["ORCHESTRATOR", "SUB_AGENT", "VALIDATOR", "HUMAN_PROXY"]
TrustTier = Literal["T1", "T2", "T3", "T4"]
AuthorityScope = Literal["OBSERVATIONS_ONLY", "HYPOTHESES", "ROUTING"]
AgentStatus = Literal["ACTIVE", "SUSPENDED", "REVOKED"]


def generate_agent_id() -> str:
    """Generate a canonical agent_id in the AGT_<12 hex> format.

    Governance rationale: matches the v1 artifact ID convention for cross-
    track visual consistency. secrets module used for unpredictability.
    """
    return f"AGT_{secrets.token_hex(6)}"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string with microseconds."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def build_agent_identity(
    *,
    agent_type: AgentType,
    model_id: str,
    provider: str,
    trust_tier: TrustTier,
    authority_scope: AuthorityScope,
    registered_by: str,
    max_synthesis_depth: int,
    parent_agent_id: str | None = None,
    agent_id: str | None = None,
    registration_timestamp: str | None = None,
    status: AgentStatus = "ACTIVE",
    revocation_event_ref: str | None = None,
    non_authoritative_flag: bool | None = None,
) -> dict[str, Any]:
    """Construct and validate an AgentIdentity artifact.

    The non_authoritative_flag parameter exists only to enforce the
    invariant: if provided, it MUST be true or omitted. Any other value
    raises AuthorityViolationError.

    Raises:
        AuthorityViolationError: if non_authoritative_flag is passed as
            anything other than true.
        ArtifactValidationError: if the constructed artifact fails JSON
            Schema validation (e.g., parent_agent_id constraints for
            SUB_AGENT/VALIDATOR, REVOKED status without revocation_event_ref).
    """
    # --- Invariant 1 enforcement (runtime layer) ---
    # The schema's const: true already ensures ArtifactValidationError on
    # a literally-false input. We ALSO reject here to produce an authority-
    # typed exception, so callers can distinguish Invariant-1 breaches from
    # general schema failures.
    if non_authoritative_flag is not None and non_authoritative_flag is not True:
        raise AuthorityViolationError(
            "AgentIdentity.non_authoritative_flag is hard-coded true and "
            "non-overridable. Invariant 1 (Authority) violation."
        )

    artifact: dict[str, Any] = {
        "artifact_type": "AgentIdentity",
        "authority_level": "non_binding",
        "agent_id": agent_id or generate_agent_id(),
        "agent_type": agent_type,
        "model_id": model_id,
        "provider": provider,
        "registration_timestamp": registration_timestamp or utc_now_iso(),
        "trust_tier": trust_tier,
        "authority_scope": authority_scope,
        "non_authoritative_flag": True,  # HARD-CODED — not caller-controlled
        "registered_by": registered_by,
        "parent_agent_id": parent_agent_id,
        "max_synthesis_depth": max_synthesis_depth,
        "status": status,
        "revocation_event_ref": revocation_event_ref,
    }

    # Schema-level validation catches:
    #   - ORCHESTRATOR with non-null parent_agent_id
    #   - SUB_AGENT/VALIDATOR with null parent_agent_id
    #   - REVOKED status without revocation_event_ref
    #   - Invalid enum values
    #   - Negative max_synthesis_depth
    ContractValidator.validate("AgentIdentity", artifact)
    return artifact


def is_active(artifact: dict[str, Any]) -> bool:
    """Return True if the AgentIdentity is in ACTIVE status."""
    return artifact.get("status") == "ACTIVE"
