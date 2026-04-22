"""
FastAPI router for Sprint-3 Hypothesis endpoints.

Governance rationale:
    Endpoints follow the Sprint-1/2 convention:
      - Missing X-Auditor-Id -> 401 INVALID_AUDITOR
      - Malformed X-Auditor-Id -> 403 INVALID_AUDITOR_FORMAT
    Exception translator aligns with the Sprint-1/2 HTTP mapping table
    (see multiagent/README.md). Sprint-3 additions:
      - DepthLimitExceededError -> 422
      - ScopeViolationError -> 403
      - FrozenPathError -> 409
      - UpstreamResolutionError -> 422
      - HypothesisValidationError (subclass of ArtifactValidationError) -> 422

Endpoints:
    POST  /hypotheses                              emit
    GET   /hypotheses/{artifact_id}?session_id=    retrieve
    GET   /sessions/{session_id}/hypotheses        list
    GET   /sessions/{session_id}/depth_state       freeze + ceilings
"""

from __future__ import annotations

import re
from typing import Any, Optional

try:
    from fastapi import (
        APIRouter, Depends, Header, HTTPException, Path, Query,
    )
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI is required per Precondition 2."
    ) from exc

from multiagent.exceptions import (
    ArtifactValidationError,
    AuthorityViolationError,
    DepthLimitExceededError,
    UnregisteredAgentError,
)
from multiagent.orchestrator.synthesis.depth import (
    AgentRegistryReader,
    LedgerReader,
    is_session_depth_frozen,
)
from multiagent.orchestrator.synthesis.hypothesis import (
    FrozenPathError,
    LedgerWriter,
    ScopeViolationError,
    UpstreamResolutionError,
    emit_hypothesis,
    get_hypothesis,
    list_session_hypotheses,
)


_AUDITOR_ID_RE = re.compile(r"^AUDITOR_[A-Z0-9_]+$")


# --- DI hooks ---------------------------------------------------------------


def get_registry() -> AgentRegistryReader:  # pragma: no cover — overridden
    raise RuntimeError(
        "get_registry dependency must be overridden at app composition time"
    )


def get_ledger_reader() -> LedgerReader:  # pragma: no cover — overridden
    raise RuntimeError(
        "get_ledger_reader dependency must be overridden at app composition time"
    )


def get_ledger_writer() -> LedgerWriter:  # pragma: no cover — overridden
    raise RuntimeError(
        "get_ledger_writer dependency must be overridden at app composition time"
    )


def require_auditor(
    x_auditor_id: Optional[str] = Header(default=None, alias="X-Auditor-Id"),
) -> str:
    """Sprint-1/2 auditor header convention: 401 missing, 403 malformed."""
    if x_auditor_id is None:
        raise HTTPException(status_code=401, detail="INVALID_AUDITOR")
    if not _AUDITOR_ID_RE.match(x_auditor_id):
        raise HTTPException(status_code=403, detail="INVALID_AUDITOR_FORMAT")
    return x_auditor_id


# --- DTOs -------------------------------------------------------------------


class HypothesisEmitRequest(BaseModel):
    session_id: str
    source_agent_id: str
    observation_refs: list[str]
    upstream_hypothesis_refs: list[str] = Field(default_factory=list)
    composite_upstream_bme_score: float
    bme_score_source: str = "placeholder"
    hypothesis_text: str | None = None
    confidence_score: float | None = None
    source_model: str | None = None
    reasoning_trace: str | None = None


class HypothesisPayloadResponse(BaseModel):
    hypothesis: dict[str, Any]
    governing_ceiling: int
    ceiling_attribution: dict[str, Any]
    bme_score_source: str


class DepthStateResponse(BaseModel):
    session_id: str
    frozen: bool
    frozen_provenance_ancestors: list[str]
    active_ceilings: dict[str, int]


# --- Router -----------------------------------------------------------------


router = APIRouter()


@router.post(
    "/hypotheses", response_model=HypothesisPayloadResponse, status_code=201,
)
def post_hypothesis(
    body: HypothesisEmitRequest,
    auditor: str = Depends(require_auditor),
    registry: AgentRegistryReader = Depends(get_registry),
    ledger: LedgerReader = Depends(get_ledger_reader),
    ledger_writer: LedgerWriter = Depends(get_ledger_writer),
):
    try:
        event = emit_hypothesis(
            session_id=body.session_id,
            source_agent_id=body.source_agent_id,
            observation_refs=body.observation_refs,
            upstream_hypothesis_refs=body.upstream_hypothesis_refs,
            composite_upstream_bme_score=body.composite_upstream_bme_score,
            bme_score_source=body.bme_score_source,
            auditor_id=auditor,
            registry=registry,
            ledger=ledger,
            ledger_writer=ledger_writer,
            hypothesis_text=body.hypothesis_text,
            confidence_score=body.confidence_score,
            source_model=body.source_model,
            reasoning_trace=body.reasoning_trace,
        )
    except DepthLimitExceededError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "DEPTH_LIMIT_EXCEEDED",
                "computed_depth": getattr(exc, "computed_depth", None),
                "governing_ceiling": getattr(exc, "governing_ceiling", None),
                "binding_agent_id": getattr(exc, "binding_agent_id", None),
            },
        ) from exc
    except UnregisteredAgentError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "UNREGISTERED_AGENT", "message": str(exc)},
        ) from exc
    except ScopeViolationError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "SCOPE_VIOLATION",
                "agent_id": exc.agent_id,
                "authority_scope": exc.authority_scope,
            },
        ) from exc
    except FrozenPathError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "FROZEN_PATH", "session_id": exc.session_id},
        ) from exc
    except UpstreamResolutionError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "UPSTREAM_UNRESOLVED", "message": str(exc)},
        ) from exc
    except AuthorityViolationError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "AUTHORITY_VIOLATION", "message": str(exc)},
        ) from exc
    except ArtifactValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "ARTIFACT_VALIDATION", "message": str(exc)},
        ) from exc

    return HypothesisPayloadResponse(**event["payload"])


@router.get(
    "/hypotheses/{artifact_id}", response_model=HypothesisPayloadResponse,
)
def get_one_hypothesis(
    artifact_id: str = Path(..., pattern=r"^HYP_[0-9a-f]{12}$"),
    session_id: str = Query(...),
    auditor: str = Depends(require_auditor),
    ledger: LedgerReader = Depends(get_ledger_reader),
):
    payload = get_hypothesis(
        session_id=session_id, artifact_id=artifact_id, ledger=ledger
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="HYPOTHESIS_NOT_FOUND")
    return HypothesisPayloadResponse(**payload)


@router.get(
    "/sessions/{session_id}/hypotheses",
    response_model=list[HypothesisPayloadResponse],
)
def list_hypotheses(
    session_id: str,
    auditor: str = Depends(require_auditor),
    ledger: LedgerReader = Depends(get_ledger_reader),
):
    payloads = list_session_hypotheses(session_id=session_id, ledger=ledger)
    return [HypothesisPayloadResponse(**p) for p in payloads]


@router.get(
    "/sessions/{session_id}/depth_state", response_model=DepthStateResponse,
)
def get_depth_state(
    session_id: str,
    auditor: str = Depends(require_auditor),
    ledger: LedgerReader = Depends(get_ledger_reader),
    registry: AgentRegistryReader = Depends(get_registry),
):
    frozen = is_session_depth_frozen(session_id=session_id, ledger=ledger)

    frozen_ancestors: set[str] = set()
    active_agents: set[str] = set()
    for event in ledger.iter_events(session_id):
        et = event.get("event_type")
        payload = event.get("payload", {})
        if et == "DEPTH_LIMIT_REACHED":
            for anc in payload.get("frozen_provenance_ancestors") or []:
                frozen_ancestors.add(anc)
        elif et == "AGENT_REGISTERED":
            identity = payload.get("agent_identity") or {}
            aid = identity.get("agent_id")
            if aid:
                active_agents.add(aid)

    active_ceilings: dict[str, int] = {}
    for aid in active_agents:
        agent = registry.get_agent(session_id, aid)
        if agent and agent.get("status") == "ACTIVE":
            ceiling = agent.get("max_synthesis_depth")
            if ceiling is not None:
                active_ceilings[aid] = int(ceiling)

    return DepthStateResponse(
        session_id=session_id,
        frozen=frozen,
        frozen_provenance_ancestors=sorted(frozen_ancestors),
        active_ceilings=active_ceilings,
    )


__all__ = [
    "DepthStateResponse",
    "HypothesisEmitRequest",
    "HypothesisPayloadResponse",
    "get_ledger_reader",
    "get_ledger_writer",
    "get_registry",
    "require_auditor",
    "router",
]
