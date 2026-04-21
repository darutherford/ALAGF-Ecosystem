"""ContractValidator — thin wrapper over the jsonschema library.

Loads JSON Schema files from /shared/artifact-contracts/v2/ and from
/multiagent/ledger/hash_chain/event_schemas/v2/ at import time. Compiled
validators are cached.

Governance rationale: Precondition 1 (from Sprint-0) designates the JSON
Schema files as the single source of truth. Python code must consume them,
not replicate them. Invariant 4 (Reconstructability) is preserved because
contracts remain portable and language-agnostic.

All validation failures raise ArtifactValidationError with the jsonschema
error message preserved in the exception message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from ..exceptions import ArtifactValidationError


# Resolve repository root relative to this file's location.
# /multiagent/artifacts/ContractValidator.py -> repo root is two levels up.
_THIS_FILE = Path(__file__).resolve()
_MULTIAGENT_ROOT = _THIS_FILE.parent.parent
_REPO_ROOT = _MULTIAGENT_ROOT.parent

_SHARED_CONTRACTS_DIR = _REPO_ROOT / "shared" / "artifact-contracts" / "v2"
_EVENT_SCHEMAS_DIR = (
    _MULTIAGENT_ROOT / "ledger" / "hash_chain" / "event_schemas" / "v2"
)


class ContractValidator:
    """Singleton-style validator cache.

    Schemas are loaded lazily on first request and cached by logical name.
    The logical name is the schema filename stem (e.g., 'AgentIdentity' for
    AgentIdentity.schema.json).

    Governance rationale: a single compilation point ensures every runtime
    validation uses the identical contract. No per-call re-parsing means
    no opportunity for drift between calls.
    """

    _validators: dict[str, Draft202012Validator] = {}
    _schemas: dict[str, dict[str, Any]] = {}

    @classmethod
    def _load_schema(cls, schema_path: Path, logical_name: str) -> None:
        """Load and compile a schema from disk, caching the result."""
        if not schema_path.is_file():
            raise ArtifactValidationError(
                f"Schema file not found for '{logical_name}' at {schema_path}. "
                f"Cannot proceed without the authoritative contract."
            )
        try:
            with schema_path.open("r", encoding="utf-8") as fh:
                schema = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ArtifactValidationError(
                f"Schema file '{schema_path}' is not valid JSON: {exc}"
            ) from exc

        # check_schema raises if the schema itself is malformed.
        Draft202012Validator.check_schema(schema)
        cls._schemas[logical_name] = schema
        cls._validators[logical_name] = Draft202012Validator(schema)

    @classmethod
    def _ensure_loaded(cls, logical_name: str) -> None:
        """Ensure the named schema is loaded; resolve its path."""
        if logical_name in cls._validators:
            return

        # Artifact contracts live in /shared/artifact-contracts/v2/.
        # Event payload / envelope schemas live in /multiagent/.../event_schemas/v2/.
        candidate_paths = [
            _SHARED_CONTRACTS_DIR / f"{logical_name}.schema.json",
            _EVENT_SCHEMAS_DIR / f"{logical_name}.payload.schema.json",
            _EVENT_SCHEMAS_DIR / f"{logical_name}.envelope.schema.json",
            _EVENT_SCHEMAS_DIR / f"{logical_name}.schema.json",
        ]
        for path in candidate_paths:
            if path.is_file():
                cls._load_schema(path, logical_name)
                return

        raise ArtifactValidationError(
            f"No schema found for logical name '{logical_name}'. "
            f"Searched: {[str(p) for p in candidate_paths]}"
        )

    @classmethod
    def validate(cls, logical_name: str, instance: dict[str, Any]) -> None:
        """Validate an instance against the named schema.

        Raises:
            ArtifactValidationError: on schema violation or missing schema.
        """
        cls._ensure_loaded(logical_name)
        validator = cls._validators[logical_name]
        errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
        if errors:
            msgs = [cls._format_error(e) for e in errors]
            raise ArtifactValidationError(
                f"{logical_name} validation failed: " + "; ".join(msgs)
            )

    @classmethod
    def is_valid(cls, logical_name: str, instance: dict[str, Any]) -> bool:
        """Boolean check without raising."""
        try:
            cls.validate(logical_name, instance)
            return True
        except ArtifactValidationError:
            return False

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the schema cache. Intended for tests only."""
        cls._validators.clear()
        cls._schemas.clear()

    @staticmethod
    def _format_error(err: JsonSchemaValidationError) -> str:
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        return f"at {path}: {err.message}"
