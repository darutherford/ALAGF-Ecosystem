"""Append-only ledger event writer with SHA-256 hash chaining.

Governance rationale:
    - Invariant 4 (Reconstructability): every event written here is self-
      describing and causally chained to its predecessor. The ledger alone
      suffices to reconstruct session history.
    - Append-only discipline: files are written with O_CREAT | O_EXCL.
      No update, no delete API. Collision on event_id raises
      LedgerIntegrityError.
    - No silent failures: every failure path raises a typed exception.
      Callers at the orchestrator layer convert exceptions into
      UNREGISTERED_AGENT_OUTPUT events or propagate as registration failures.

File layout:
    /multiagent/ledger/hash_chain/sessions/<session_id>/
        000001_<event_id>.json      (zero-padded sequence prefix)
        000002_<event_id>.json
        ...
        _chain_head.json            (index: last event_id, hash, sequence)

Chain scope is per-session. Genesis event has prev_hash = null.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from ...artifacts.ContractValidator import ContractValidator
from ...exceptions import ArtifactValidationError, LedgerIntegrityError


EventType = Literal[
    "AGENT_REGISTERED",
    "AGENT_SUSPENDED",
    "AGENT_REVOKED",
    "UNREGISTERED_AGENT_OUTPUT",
    "AGENT_SESSION_REGISTRY",
    "AGENT_HANDOFF",
    "BOUNDARY_HANDSHAKE",
    "BOUNDARY_VIOLATION",
]


# Resolve ledger root relative to this file.
# /multiagent/ledger/hash_chain/events.py -> /multiagent/ledger/hash_chain/
_THIS_FILE = Path(__file__).resolve()
_HASH_CHAIN_DIR = _THIS_FILE.parent
_SESSIONS_DIR = _HASH_CHAIN_DIR / "sessions"


# Crockford base32 alphabet used by ULID (excludes I, L, O, U).
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _generate_ulid() -> str:
    """Generate a ULID as a 26-character Crockford base32 string.

    Implemented inline to avoid an external dependency. Format:
        48-bit timestamp ms + 80-bit randomness, base32-encoded.
    """
    # Timestamp: milliseconds since epoch, 48 bits.
    timestamp_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    # Randomness: 80 bits.
    random_bits = secrets.randbits(80)
    combined = (timestamp_ms << 80) | random_bits

    # Encode 128 bits as 26 base32 characters (Crockford).
    chars = []
    for i in range(26):
        shift = (25 - i) * 5
        idx = (combined >> shift) & 0x1F
        chars.append(_CROCKFORD[idx])
    return "".join(chars)


def generate_event_id() -> str:
    """Generate a ULID-based event_id with the evt_ prefix."""
    return f"evt_{_generate_ulid()}"


def utc_now_iso() -> str:
    """ISO 8601 UTC timestamp with microseconds, Z suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _canonical_json(data: dict[str, Any]) -> bytes:
    """Canonical JSON serialization for hashing.

    Rules: sorted keys, no whitespace, UTF-8 allowed (ensure_ascii=False).
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _session_dir(session_id: str) -> Path:
    return _SESSIONS_DIR / session_id


def _chain_head_path(session_id: str) -> Path:
    return _session_dir(session_id) / "_chain_head.json"


def _read_chain_head(session_id: str) -> dict[str, Any] | None:
    """Return the cached chain head, or None if no events exist yet."""
    path = _chain_head_path(session_id)
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_chain_head(session_id: str, head: dict[str, Any]) -> None:
    """Atomically update the chain head cache via write-temp + rename.

    Governance rationale: the chain head is an index, not part of the chain
    itself. Loss of this file is recoverable by scanning the session
    directory. Atomic rename prevents partial writes on failure.
    """
    path = _chain_head_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(head, fh, sort_keys=True, indent=2)
    os.replace(tmp, path)


def _event_filename(sequence_number: int, event_id: str) -> str:
    return f"{sequence_number:06d}_{event_id}.json"


def append_event(
    *,
    event_type: EventType,
    session_id: str,
    auditor_id: str,
    actor: dict[str, str],
    payload: dict[str, Any],
    prior_event_id: str | None = None,
    referenced_artifact_id: str | None = None,
    referenced_event_id: str | None = None,
) -> dict[str, Any]:
    """Append a new event to the session's chain.

    Returns the full LedgerEvent (post-hash). Raises LedgerIntegrityError
    on any integrity violation (duplicate event_id, out-of-order sequence,
    hash mismatch detection in future reads).

    Schema validation is layered:
        1. Payload is validated against its per-event-type payload schema.
        2. The full envelope (minus event_hash) is validated against the
           LedgerEvent.envelope schema.
        3. event_hash is computed and written to disk with O_EXCL semantics.

    Governance rationale: layered validation ensures the payload contract
    is honored separately from the envelope contract. Invariant 4 requires
    both. The O_EXCL write prevents accidental overwrites of existing
    events, enforcing append-only discipline at the filesystem level.
    """
    ContractValidator.validate(event_type, payload)

    head = _read_chain_head(session_id)
    if head is None:
        sequence_number = 1
        prev_hash: str | None = None
    else:
        sequence_number = head["last_sequence_number"] + 1
        prev_hash = head["last_event_hash"]

    event_id = generate_event_id()
    envelope: dict[str, Any] = {
        "event_id": event_id,
        "event_type": event_type,
        "schema_version": "v2",
        "session_id": session_id,
        "sequence_number": sequence_number,
        "timestamp_utc": utc_now_iso(),
        "auditor_id": auditor_id,
        "actor": actor,
        "causal_refs": {
            "prior_event_id": prior_event_id,
            "referenced_artifact_id": referenced_artifact_id,
            "referenced_event_id": referenced_event_id,
        },
        "payload": payload,
        "prev_hash": prev_hash,
    }

    # Validate envelope shape BEFORE hashing so hash is always of valid content.
    # We validate a copy including a placeholder event_hash because the schema
    # requires the field. The placeholder is replaced immediately after.
    envelope_for_validation = dict(envelope)
    envelope_for_validation["event_hash"] = (
        "sha256:" + "0" * 64
    )  # placeholder satisfying pattern
    ContractValidator.validate("LedgerEvent", envelope_for_validation)

    # Compute event_hash over the canonical form WITHOUT event_hash.
    event_hash = _sha256(_canonical_json(envelope))
    envelope["event_hash"] = event_hash

    # Final validation of the completed envelope (defense in depth).
    ContractValidator.validate("LedgerEvent", envelope)

    # Write with O_EXCL semantics to enforce append-only at the filesystem level.
    session_dir = _session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    filename = _event_filename(sequence_number, event_id)
    event_path = session_dir / filename
    try:
        # "x" mode -> O_CREAT | O_EXCL. Fails if file exists.
        with event_path.open("x", encoding="utf-8") as fh:
            json.dump(envelope, fh, sort_keys=True, indent=2)
    except FileExistsError as exc:
        raise LedgerIntegrityError(
            f"Event file already exists: {event_path}. Duplicate event_id or "
            f"sequence collision."
        ) from exc

    # Update chain head cache.
    _write_chain_head(
        session_id,
        {
            "last_event_id": event_id,
            "last_event_hash": event_hash,
            "last_sequence_number": sequence_number,
        },
    )

    return envelope


def read_event(session_id: str, event_id: str) -> dict[str, Any]:
    """Read a specific event by ID. Raises LedgerIntegrityError if not found."""
    session_dir = _session_dir(session_id)
    if not session_dir.is_dir():
        raise LedgerIntegrityError(
            f"No session directory for {session_id}; cannot read event {event_id}."
        )
    # Filename prefix includes sequence number; glob by event_id suffix.
    matches = list(session_dir.glob(f"*_{event_id}.json"))
    if not matches:
        raise LedgerIntegrityError(
            f"Event {event_id} not found in session {session_id}."
        )
    if len(matches) > 1:
        raise LedgerIntegrityError(
            f"Multiple files match event_id {event_id} in session {session_id}: {matches}."
        )
    with matches[0].open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_session_events(session_id: str) -> list[dict[str, Any]]:
    """Return all events for a session in sequence order.

    Raises LedgerIntegrityError if the hash chain fails verification.
    """
    session_dir = _session_dir(session_id)
    if not session_dir.is_dir():
        return []

    event_files = sorted(
        [p for p in session_dir.iterdir() if p.name.endswith(".json") and not p.name.startswith("_")],
        key=lambda p: p.name,
    )
    events: list[dict[str, Any]] = []
    prev_hash: str | None = None
    expected_seq = 1
    for path in event_files:
        with path.open("r", encoding="utf-8") as fh:
            event = json.load(fh)
        if event["sequence_number"] != expected_seq:
            raise LedgerIntegrityError(
                f"Sequence gap in session {session_id} at {path.name}: "
                f"expected {expected_seq}, got {event['sequence_number']}."
            )
        if event["prev_hash"] != prev_hash:
            raise LedgerIntegrityError(
                f"Hash chain break in session {session_id} at {path.name}: "
                f"event.prev_hash does not match computed prev_hash."
            )
        # Verify event_hash by recomputing over envelope-minus-event_hash.
        envelope_without_hash = {k: v for k, v in event.items() if k != "event_hash"}
        computed = _sha256(_canonical_json(envelope_without_hash))
        if computed != event["event_hash"]:
            raise LedgerIntegrityError(
                f"event_hash verification failed in session {session_id} at {path.name}."
            )
        events.append(event)
        prev_hash = event["event_hash"]
        expected_seq += 1
    return events
