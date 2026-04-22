"""
Ledger adapter bridging Sprint-3 synthesis with Sprint-1/2 ledger primitives.

Governance rationale:
    Sprint-3 synthesis code is ledger-agnostic via the LedgerReader and
    LedgerWriter Protocols in depth.py and hypothesis.py. The Sprint-1/2
    canonical ledger lives at multiagent.ledger.hash_chain.events. This
    adapter is a thin shim that exposes that ledger as the protocols.

    The Sprint-1/2 append_event signature (confirmed from
    multiagent/ledger/hash_chain/events.py HEAD) is:
        append_event(*, event_type, session_id, auditor_id, actor, payload,
                     prior_event_id=None, referenced_artifact_id=None,
                     referenced_event_id=None) -> dict
    This adapter unpacks the Sprint-3 causal_refs dict into those three
    explicit kwargs.
"""

from __future__ import annotations

from typing import Iterable


class FsLedger:
    """LedgerReader + LedgerWriter adapter over Sprint-1/2 primitives."""

    def __init__(self) -> None:
        from multiagent.ledger.hash_chain.events import (
            append_event as _append,
            read_session_events as _read,
        )
        self._append = _append
        self._read = _read

    def iter_events(self, session_id: str) -> Iterable[dict]:
        return self._read(session_id)

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
        return self._append(
            event_type=event_type,
            session_id=session_id,
            auditor_id=auditor_id,
            actor=actor,
            payload=payload,
            prior_event_id=causal_refs.get("prior_event_id"),
            referenced_artifact_id=causal_refs.get("referenced_artifact_id"),
            referenced_event_id=causal_refs.get("referenced_event_id"),
        )


__all__ = ["FsLedger"]
