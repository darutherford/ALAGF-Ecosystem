"""
Filesystem AgentIdentity registry reader for Sprint-3 synthesis.

Governance rationale:
    Sprint-3 synthesis needs (a) session scoping and (b) live status for a
    given agent. The Sprint-1 canonical lookup get_agent_identity() returns
    the live status but strips the _session_id meta field on return. The
    raw registration file on disk retains _session_id. Session scoping for
    Sprint-3 therefore requires reading the raw file; live status for
    Sprint-3 requires the canonical function.

    This adapter combines both reads:
      1. Read the raw registration file to enforce session scoping via
         _session_id (Sprint-1 meta key, underscore-prefixed).
      2. Call the canonical get_agent_identity() for live status
         resolution so SUSPENDED/REVOKED markers are honored.

    Sprint-4 consolidation item: extend Sprint-1's canonical function with
    an optional session_id filter, removing the raw-file read below.
"""

from __future__ import annotations

import json
from pathlib import Path

from multiagent.orchestrator.agent_lifecycle.registration import (
    get_agent_identity,
)

_THIS_FILE = Path(__file__).resolve()
_MULTIAGENT_ROOT = _THIS_FILE.parent.parent.parent
_REGISTRY_DIR = _MULTIAGENT_ROOT / "ledger" / "agent_registry"


class FsAgentRegistry:
    """AgentRegistryReader implementation over the Sprint-1 registry."""

    def get_agent(self, session_id: str, agent_id: str) -> dict | None:
        reg_path = _REGISTRY_DIR / f"{agent_id}.json"
        if not reg_path.is_file():
            return None

        with reg_path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)

        if raw.get("_session_id") != session_id:
            return None

        try:
            live = get_agent_identity(agent_id)
        except Exception:
            return None
        if live is None:
            return None

        # live has authoritative status; raw has _session_id meta. Merge.
        merged = dict(live)
        merged["_session_id"] = raw.get("_session_id")
        merged["_registration_event_id"] = raw.get("_registration_event_id")
        return merged


__all__ = ["FsAgentRegistry"]
