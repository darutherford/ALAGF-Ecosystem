"""
Depth computation and ceiling enforcement.

Governance rationale (Sprint-3 ratified decisions):
    (a) Chain-minimum ceiling attribution (strictest upstream ceiling governs;
        closes the relay-laundering vector).
    (b) Path-scoped freeze (only Hypotheses whose provenance chain includes
        a depth-limited ancestor are blocked).
    (c) Observations are the depth=0 floor.
    (f) AGENT_HANDOFF moves artifacts; upstream_hypothesis_refs determines
        depth.

Key HEAD-schema alignment:
    - HYPOTHESIS_REGISTERED payload wraps the artifact under `hypothesis`.
    - Hypothesis artifact IDs use `artifact_id`, not `hypothesis_id`.
    - AgentIdentity lives in AGENT_REGISTERED payload under `agent_identity`
      (per /multiagent/ledger/hash_chain/event_schemas/v2/
      AGENT_REGISTERED.payload.schema.json and Sprint-1 precedent).
    - Depth values are integer >= 0 (HEAD Hypothesis schema minimum: 0).
      Observations = 0; first inferential hop = 1 (policy, not schema).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


# --- Protocols --------------------------------------------------------------


class LedgerReader(Protocol):
    """Abstract ledger reader. In production this is backed by the
    Sprint-1/2 append-only JSON store. In tests, an in-memory fake is
    injected."""

    def iter_events(self, session_id: str) -> Iterable[dict]:
        """Yield events for the session in sequence_number order."""
        ...


class AgentRegistryReader(Protocol):
    """Abstract AgentIdentity registry reader. Sprint-1 produced the
    canonical implementation under multiagent.orchestrator.agent_lifecycle."""

    def get_agent(self, session_id: str, agent_id: str) -> dict | None:
        """Return the registered AgentIdentity artifact or None if absent."""
        ...


# --- Exceptions -------------------------------------------------------------
#
# Sprint-3 uses the canonical DepthLimitExceededError class reserved in the
# Sprint-1 exception taxonomy at multiagent.exceptions. Sprint-1 declared the
# class as "Reserved for Sprint-3 structural enforcement"; this sprint is
# the one that raises it.
#
# The Sprint-1 class does not take kwargs. Sprint-3 attaches diagnostic
# attributes (computed_depth, governing_ceiling, binding_agent_id,
# session_id) via a helper constructor so the canonical class stays
# unmodified while API-layer exception translators can access the fields.

from multiagent.exceptions import DepthLimitExceededError as _DepthLimitExceededError


class DepthLimitExceededError(_DepthLimitExceededError):
    """Sprint-3 instance of the Sprint-1-reserved DepthLimitExceededError.

    Extends the canonical class with kw-only diagnostic attributes required
    by the API-layer exception translator. The canonical class inheritance
    (ALAGFError) is preserved; isinstance checks against the Sprint-1 class
    continue to work.
    """

    def __init__(
        self,
        *,
        computed_depth: int,
        governing_ceiling: int,
        binding_agent_id: str,
        session_id: str,
    ):
        self.computed_depth = computed_depth
        self.governing_ceiling = governing_ceiling
        self.binding_agent_id = binding_agent_id
        self.session_id = session_id
        super().__init__(
            f"Depth {computed_depth} exceeds ceiling {governing_ceiling} "
            f"bound by agent {binding_agent_id} in session {session_id}."
        )


# --- Data classes -----------------------------------------------------------


@dataclass(frozen=True)
class CeilingAttribution:
    binding_agent_id: str
    binding_max_synthesis_depth: int


@dataclass(frozen=True)
class DepthEvaluation:
    computed_depth: int
    governing_ceiling: int
    attribution: CeilingAttribution
    upstream_chain_agents: tuple[str, ...]
    frozen_provenance_ancestors: tuple[str, ...]

    @property
    def exceeds_ceiling(self) -> bool:
        return self.computed_depth > self.governing_ceiling


# --- Ledger payload accessors ----------------------------------------------
#
# HEAD ledger events wrap artifacts under a named key inside `payload`:
#   AGENT_REGISTERED    -> payload.agent_identity
#   HYPOTHESIS_REGISTERED -> payload.hypothesis  (Sprint-3)
# These helpers make the indirection explicit and single-sourced.


def _hypothesis_from_event(event: dict) -> dict | None:
    if event.get("event_type") != "HYPOTHESIS_REGISTERED":
        return None
    return (event.get("payload") or {}).get("hypothesis")


def _agent_from_event(event: dict) -> dict | None:
    if event.get("event_type") != "AGENT_REGISTERED":
        return None
    return (event.get("payload") or {}).get("agent_identity")


# --- Depth computation ------------------------------------------------------


def compute_hypothesis_depth(
    *,
    upstream_hypothesis_refs: list[str],
    ledger: LedgerReader,
    session_id: str,
) -> int:
    """Compute the synthesis_depth of a prospective Hypothesis.

    Depth semantics (decision c):
      - Observations are the depth=0 floor.
      - Hypothesis with no upstream refs: depth=1 (first inferential hop).
      - Hypothesis with upstream refs: depth = max(upstream_depths) + 1.

    Raises:
        KeyError: if any upstream ref does not resolve to a
                  HYPOTHESIS_REGISTERED event in the session.
    """
    if not upstream_hypothesis_refs:
        return 1

    registered: dict[str, int] = {}
    for event in ledger.iter_events(session_id):
        hyp = _hypothesis_from_event(event)
        if hyp is None:
            continue
        aid = hyp.get("artifact_id")
        depth = hyp.get("synthesis_depth")
        if aid is not None and depth is not None:
            registered[aid] = depth

    upstream_depths: list[int] = []
    for ref in upstream_hypothesis_refs:
        if ref not in registered:
            raise KeyError(
                f"upstream_hypothesis_ref {ref} not found among "
                f"HYPOTHESIS_REGISTERED events in session {session_id}"
            )
        upstream_depths.append(registered[ref])

    return max(upstream_depths) + 1


def _walk_upstream_agents(
    *,
    upstream_hypothesis_refs: list[str],
    ledger: LedgerReader,
    session_id: str,
) -> tuple[set[str], set[str]]:
    """Return (transitive_upstream_agents, transitive_upstream_hyp_ids).

    Used for chain-minimum attribution (decision a) and for path-scoped freeze
    ancestor closure (decision b).
    """
    by_id: dict[str, dict] = {}
    for event in ledger.iter_events(session_id):
        hyp = _hypothesis_from_event(event)
        if hyp is None:
            continue
        aid = hyp.get("artifact_id")
        if aid:
            by_id[aid] = hyp

    visited: set[str] = set()
    agents: set[str] = set()
    stack = list(upstream_hypothesis_refs)
    while stack:
        hid = stack.pop()
        if hid in visited:
            continue
        visited.add(hid)
        hyp = by_id.get(hid)
        if hyp is None:
            raise KeyError(
                f"upstream_hypothesis_ref {hid} not found in session "
                f"{session_id} ledger"
            )
        # HEAD schema does not store source_agent_id on the Hypothesis
        # artifact itself (decision matter for Sprint-4 review). Instead,
        # the HYPOTHESIS_REGISTERED envelope's actor.actor_id identifies
        # the emitting agent. We resolve via the envelope, not the artifact.
        for event in ledger.iter_events(session_id):
            if event.get("event_type") != "HYPOTHESIS_REGISTERED":
                continue
            ev_hyp = _hypothesis_from_event(event)
            if ev_hyp is not None and ev_hyp.get("artifact_id") == hid:
                actor = event.get("actor") or {}
                aid = actor.get("actor_id")
                if aid:
                    agents.add(aid)
                break
        for parent in hyp.get("upstream_hypothesis_refs") or []:
            stack.append(parent)
    return agents, visited


def evaluate_depth_ceiling(
    *,
    source_agent_id: str,
    upstream_hypothesis_refs: list[str],
    ledger: LedgerReader,
    registry: AgentRegistryReader,
    session_id: str,
) -> DepthEvaluation:
    """Evaluate whether a prospective Hypothesis synthesis respects the
    chain-minimum depth ceiling.

    Chain-minimum attribution (decision a):
        governing_ceiling = min(max_synthesis_depth) over the union of
        {source_agent_id} \u222a all agents in the transitive upstream chain.
    """
    computed_depth = compute_hypothesis_depth(
        upstream_hypothesis_refs=upstream_hypothesis_refs,
        ledger=ledger,
        session_id=session_id,
    )

    upstream_agents, _visited = _walk_upstream_agents(
        upstream_hypothesis_refs=upstream_hypothesis_refs,
        ledger=ledger,
        session_id=session_id,
    )
    chain_agents = upstream_agents | {source_agent_id}

    binding_agent_id = source_agent_id
    binding_ceiling: int | None = None
    for agent_id in chain_agents:
        agent = registry.get_agent(session_id, agent_id)
        if agent is None:
            raise KeyError(
                f"agent {agent_id} not registered in session {session_id}; "
                "upstream chain contains an unregistered agent"
            )
        candidate = agent.get("max_synthesis_depth")
        if candidate is None:
            raise ValueError(
                f"agent {agent_id} missing max_synthesis_depth field"
            )
        if binding_ceiling is None or candidate < binding_ceiling:
            binding_ceiling = candidate
            binding_agent_id = agent_id

    assert binding_ceiling is not None  # chain_agents is non-empty

    frozen_ancestors: set[str] = set()
    for event in ledger.iter_events(session_id):
        if event.get("event_type") != "DEPTH_LIMIT_REACHED":
            continue
        payload = event.get("payload", {})
        for anc in payload.get("frozen_provenance_ancestors") or []:
            frozen_ancestors.add(anc)

    return DepthEvaluation(
        computed_depth=computed_depth,
        governing_ceiling=binding_ceiling,
        attribution=CeilingAttribution(
            binding_agent_id=binding_agent_id,
            binding_max_synthesis_depth=binding_ceiling,
        ),
        upstream_chain_agents=tuple(sorted(chain_agents)),
        frozen_provenance_ancestors=tuple(sorted(frozen_ancestors)),
    )


# --- Session freeze derivation ---------------------------------------------


def is_session_depth_frozen(
    *,
    session_id: str,
    ledger: LedgerReader,
    upstream_hypothesis_refs: list[str] | None = None,
) -> bool:
    """Path-scoped freeze check (decision b). Pure-ledger derivation.

    If upstream_hypothesis_refs is None, returns True iff any
    DEPTH_LIMIT_REACHED event exists (session-level diagnostic view).

    If provided, returns True iff the transitive upstream closure of those
    refs intersects any frozen ancestor from a prior DEPTH_LIMIT_REACHED.
    """
    frozen: set[str] = set()
    any_depth_limit = False
    registered: dict[str, dict] = {}
    for event in ledger.iter_events(session_id):
        et = event.get("event_type")
        payload = event.get("payload", {})
        if et == "DEPTH_LIMIT_REACHED":
            any_depth_limit = True
            for anc in payload.get("frozen_provenance_ancestors") or []:
                frozen.add(anc)
        elif et == "HYPOTHESIS_REGISTERED":
            hyp = payload.get("hypothesis")
            if hyp:
                aid = hyp.get("artifact_id")
                if aid:
                    registered[aid] = hyp

    if upstream_hypothesis_refs is None:
        return any_depth_limit

    if not frozen:
        return False

    visited: set[str] = set()
    stack = list(upstream_hypothesis_refs)
    while stack:
        hid = stack.pop()
        if hid in visited:
            continue
        visited.add(hid)
        if hid in frozen:
            return True
        hyp = registered.get(hid)
        if hyp is None:
            continue
        for parent in hyp.get("upstream_hypothesis_refs") or []:
            stack.append(parent)
    return False


def build_depth_limit_payload(
    *,
    evaluation: DepthEvaluation,
    source_agent_id: str,
    upstream_hypothesis_refs: list[str],
    ledger: LedgerReader,
    session_id: str,
) -> dict:
    """Assemble the DEPTH_LIMIT_REACHED payload with transitive ancestor
    closure for path-scoped freeze membership."""
    closure: set[str] = set()
    registered: dict[str, dict] = {}
    for event in ledger.iter_events(session_id):
        if event.get("event_type") == "HYPOTHESIS_REGISTERED":
            hyp = (event.get("payload") or {}).get("hypothesis") or {}
            aid = hyp.get("artifact_id")
            if aid:
                registered[aid] = hyp

    stack = list(upstream_hypothesis_refs)
    while stack:
        hid = stack.pop()
        if hid in closure:
            continue
        closure.add(hid)
        hyp = registered.get(hid, {})
        for parent in hyp.get("upstream_hypothesis_refs") or []:
            stack.append(parent)

    return {
        "attempted_source_agent_id": source_agent_id,
        "attempted_upstream_hypothesis_refs": list(upstream_hypothesis_refs),
        "computed_depth": evaluation.computed_depth,
        "governing_ceiling": evaluation.governing_ceiling,
        "ceiling_attribution": {
            "binding_agent_id": evaluation.attribution.binding_agent_id,
            "binding_max_synthesis_depth": evaluation.attribution.binding_max_synthesis_depth,
        },
        "frozen_provenance_ancestors": sorted(closure),
        "rejection_reason": "CHAIN_MINIMUM_CEILING_EXCEEDED",
    }


__all__ = [
    "AgentRegistryReader",
    "CeilingAttribution",
    "DepthEvaluation",
    "DepthLimitExceededError",
    "LedgerReader",
    "build_depth_limit_payload",
    "compute_hypothesis_depth",
    "evaluate_depth_ceiling",
    "is_session_depth_frozen",
]
