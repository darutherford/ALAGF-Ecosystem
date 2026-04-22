"""
Hypothesis artifact package (Sprint-3).

Governance rationale:
    Hypothesis is an AI-produced inferential artifact. Invariant 1 (Authority)
    requires non_authoritative_flag hard-coded true and non-overridable.
    Invariant 3 (Evidence-First) requires observation_refs (direct evidence)
    and upstream_hypothesis_refs (inferential ancestry). Invariant 4
    (Reconstructability) requires canonical IDs and deterministic
    serialization for ledger-only reconstruction.

    The v2 schema at /shared/artifact-contracts/v2/Hypothesis.schema.json was
    locked in Sprint-0 and is not modified by Sprint-3. This factory produces
    artifacts conforming to that HEAD-locked schema.

Key schema-driven constraints enforced here:
    - artifact_type: "Hypothesis" (const)
    - authority_level: "non_binding" (const)
    - non_authoritative_flag: True (const, double-enforced at factory)
    - artifact_id: "HYP_<12 hex>" (pattern)
    - session_id: "SESSION_<8 hex>" (pattern)
    - observation_refs: minItems 1 (decision g-i: every Hypothesis traces
      to evidence independently of upstream refs)
    - synthesis_depth: integer >= 0
    - upstream_hypothesis_refs: array of strings
    - composite_upstream_bme_score: number in [0.0, 1.0] (decision e-revised:
      Sprint-3 accepts caller-supplied placeholders; Sprint-4 overwrites
      with computed values. The envelope payload carries bme_score_source
      to distinguish the two.)

Public API:
    new_hypothesis_id() -> str
    build_hypothesis(...) -> dict
    validate_hypothesis(artifact: dict) -> None   (raises on violation)
    serialize_hypothesis(artifact: dict) -> str
"""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "jsonschema is required per Sprint-1/2 Precondition 1. "
        "Install with: pip install jsonschema"
    ) from exc


# --- Schema loading ---------------------------------------------------------

_SCHEMA_ENV_VAR = "ALAGF_V2_SCHEMA_DIR"
_DEFAULT_SCHEMA_REL = Path("shared/artifact-contracts/v2")
_HYPOTHESIS_SCHEMA_FILE = "Hypothesis.schema.json"

_HYP_ID_RE = re.compile(r"^HYP_[0-9a-f]{12}$")
_AGT_ID_RE = re.compile(r"^AGT_[0-9a-f]{12}$")
_SESSION_ID_RE = re.compile(r"^SESSION_[0-9a-f]{8}$")


def _locate_schema_dir() -> Path:
    env = os.environ.get(_SCHEMA_ENV_VAR)
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        candidate = parent / _DEFAULT_SCHEMA_REL
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        f"v2 shared schema dir not found. Set {_SCHEMA_ENV_VAR} or ensure "
        f"{_DEFAULT_SCHEMA_REL} exists in a parent of {here}."
    )


_SCHEMA_CACHE: dict[str, Any] = {}


def _load_schema() -> dict:
    if "hypothesis" not in _SCHEMA_CACHE:
        schema_path = _locate_schema_dir() / _HYPOTHESIS_SCHEMA_FILE
        with schema_path.open("r", encoding="utf-8") as fh:
            _SCHEMA_CACHE["hypothesis"] = json.load(fh)
    return _SCHEMA_CACHE["hypothesis"]


# --- Exceptions -------------------------------------------------------------
#
# Sprint-3 reuses the canonical AuthorityViolationError from the Sprint-1
# exception taxonomy at multiagent.exceptions. HypothesisValidationError
# is net-new to Sprint-3 and subclasses the canonical ArtifactValidationError
# to preserve the Sprint-1 isinstance contract (JSON Schema violations are
# ArtifactValidationError regardless of the artifact type).

from multiagent.exceptions import (
    ArtifactValidationError,
    AuthorityViolationError,
)


class HypothesisValidationError(ArtifactValidationError):
    """Raised when a Hypothesis artifact fails schema or governance validation.

    Subclasses ArtifactValidationError so callers that catch the Sprint-1
    canonical class also catch Sprint-3 Hypothesis violations.
    """


def _authority_violation_error_class():
    return AuthorityViolationError


# --- Factory ----------------------------------------------------------------


def new_hypothesis_id() -> str:
    """Generate a canonical HYP_<12 hex> Hypothesis ID.

    Governance rationale: Invariant 4. IDs are opaque and centrally generated.
    """
    return f"HYP_{secrets.token_hex(6)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def build_hypothesis(
    *,
    session_id: str,
    observation_refs: list[str],
    synthesis_depth: int,
    upstream_hypothesis_refs: list[str],
    composite_upstream_bme_score: float,
    artifact_id: str | None = None,
    created_at: str | None = None,
    non_authoritative_flag: bool = True,
    # Optional rich fields carried forward from the HEAD-locked schema.
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
    """Construct a Hypothesis artifact dict conforming to HEAD's v2 schema.

    Required (schema-required):
        session_id              SESSION_<8 hex>
        observation_refs        non-empty list (decision g-i)
        synthesis_depth         int >= 0
        upstream_hypothesis_refs list (may be empty)
        composite_upstream_bme_score  number in [0.0, 1.0]
                                (decision e-revised: placeholder in Sprint-3)

    Optional (schema-optional):
        hypothesis_text, confidence_score, source_model, reasoning_trace,
        tier_justification, risk_flags, compliance_gaps, recommendations,
        governance_narrative, entropy_assessment, raw_api_response,
        cached_response

    Governance-controlled:
        artifact_id             factory-generated if omitted
        created_at              now() if omitted
        non_authoritative_flag  hard-coded True; override raises
                                AuthorityViolationError
        artifact_type           "Hypothesis" (not a parameter; const in schema)
        authority_level         "non_binding" (not a parameter; const in schema)

    Raises:
        AuthorityViolationError: non_authoritative_flag override attempt.
        HypothesisValidationError: any other schema violation.
    """
    if non_authoritative_flag is not True:
        AuthorityViolationError = _authority_violation_error_class()
        raise AuthorityViolationError(
            "non_authoritative_flag must be True. AI outputs are non-binding "
            "by Invariant 1; override is structurally prohibited."
        )

    artifact: dict[str, Any] = {
        "artifact_type": "Hypothesis",
        "authority_level": "non_binding",
        "non_authoritative_flag": True,
        "artifact_id": artifact_id or new_hypothesis_id(),
        "session_id": session_id,
        "observation_refs": list(observation_refs),
        "synthesis_depth": synthesis_depth,
        "upstream_hypothesis_refs": list(upstream_hypothesis_refs),
        "composite_upstream_bme_score": composite_upstream_bme_score,
        "created_at": created_at or _now_iso(),
    }

    # Optional fields only included when provided, to preserve
    # additionalProperties: false in the HEAD schema (optional fields that
    # are present must match their schema types; omission is valid).
    optional_fields = {
        "hypothesis_text": hypothesis_text,
        "confidence_score": confidence_score,
        "source_model": source_model,
        "reasoning_trace": reasoning_trace,
        "tier_justification": tier_justification,
        "risk_flags": risk_flags,
        "compliance_gaps": compliance_gaps,
        "recommendations": recommendations,
        "governance_narrative": governance_narrative,
        "entropy_assessment": entropy_assessment,
        "raw_api_response": raw_api_response,
        "cached_response": cached_response,
    }
    for key, value in optional_fields.items():
        if value is not None:
            artifact[key] = value

    validate_hypothesis(artifact)
    return artifact


def validate_hypothesis(artifact: dict) -> None:
    """Validate a Hypothesis artifact against the HEAD v2 JSON Schema plus
    factory-level invariants."""
    # Invariant 1 double enforcement
    if artifact.get("non_authoritative_flag") is not True:
        AuthorityViolationError = _authority_violation_error_class()
        raise AuthorityViolationError(
            "non_authoritative_flag must be True (Invariant 1)."
        )

    # Self-reference guard: a Hypothesis's upstream refs must not include
    # its own ID. The schema cannot express this; enforcement is runtime-only.
    aid = artifact.get("artifact_id", "")
    if not _HYP_ID_RE.match(aid):
        raise HypothesisValidationError(
            f"artifact_id {aid!r} does not match HYP_<12 hex> pattern."
        )
    if aid in (artifact.get("upstream_hypothesis_refs") or []):
        raise HypothesisValidationError(
            "upstream_hypothesis_refs must not contain the Hypothesis's own "
            "artifact_id (self-reference prohibited)."
        )

    sid = artifact.get("session_id", "")
    if not _SESSION_ID_RE.match(sid):
        raise HypothesisValidationError(
            f"session_id {sid!r} does not match SESSION_<8 hex> pattern."
        )

    # JSON Schema validation
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(artifact), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = ".".join(str(p) for p in first.absolute_path) or "<root>"
        raise HypothesisValidationError(
            f"Hypothesis schema violation at {path}: {first.message}"
        )


def serialize_hypothesis(artifact: dict) -> str:
    """Deterministic JSON serialization for hash chaining. Invariant 4."""
    validate_hypothesis(artifact)
    return json.dumps(artifact, sort_keys=True, separators=(",", ":"))


__all__ = [
    "HypothesisValidationError",
    "build_hypothesis",
    "new_hypothesis_id",
    "serialize_hypothesis",
    "validate_hypothesis",
]
