"""FastAPI endpoints for the multiagent orchestrator.

Governance rationale:
    - Invariant 1: every endpoint requires the X-Auditor-Id header.
      Requests missing the header are rejected at the API boundary.
    - Precondition 1: Pydantic is used ONLY for request/response I/O shapes.
      No Pydantic model replicates the AgentIdentity contract; the
      authoritative contract remains the JSON Schema in
      /shared/artifact-contracts/v2/. The POST /agents endpoint accepts
      a dict body and passes it through the jsonschema validator.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from ..exceptions import (
    AgentRegistrationError,
    ArtifactValidationError,
    AuthorityViolationError,
    LedgerIntegrityError,
    UnregisteredAgentError,
)
from .agent_lifecycle.registration import (
    emit_session_registry,
    get_agent_identity,
    list_session_active_agents,
    register_agent,
    revoke_agent,
    suspend_agent,
)


app = FastAPI(
    title="ALAGF multiagent orchestrator",
    version="v2-sprint-1",
    description=(
        "AgentIdentity lifecycle endpoints. All endpoints require the "
        "X-Auditor-Id header per Invariant 1 (Authority). Authoritative "
        "artifact contracts live in JSON Schema; Pydantic models here are "
        "I/O shapes only."
    ),
)


# ---------------------------------------------------------------------------
# I/O models (Pydantic; not artifact contracts)
# ---------------------------------------------------------------------------


class RegisterAgentRequest(BaseModel):
    """Request body for POST /agents. I/O shape only, not a contract."""

    session_id: str = Field(..., pattern=r"^SESSION_[0-9a-f]{8}$")
    agent_type: Literal["ORCHESTRATOR", "SUB_AGENT", "VALIDATOR", "HUMAN_PROXY"]
    model_id: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    trust_tier: Literal["T1", "T2", "T3", "T4"]
    authority_scope: Literal["OBSERVATIONS_ONLY", "HYPOTHESES", "ROUTING"]
    max_synthesis_depth: int = Field(..., ge=0)
    parent_agent_id: str | None = None
    agent_id: str | None = None


class StatusTransitionRequest(BaseModel):
    reason: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Header dependency
# ---------------------------------------------------------------------------


def _require_auditor(auditor_id: str | None) -> str:
    if not auditor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "X-Auditor-Id header is required. Invariant 1 (Authority) "
                "enforcement at the API boundary."
            ),
        )
    return auditor_id


# ---------------------------------------------------------------------------
# Exception translation to HTTP
# ---------------------------------------------------------------------------


def _translate(exc: Exception) -> HTTPException:
    """Convert typed domain exceptions to HTTP responses."""
    if isinstance(exc, AuthorityViolationError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, UnregisteredAgentError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, AgentRegistrationError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ArtifactValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, LedgerIntegrityError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail=f"Unexpected error: {exc}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/agents", status_code=201)
def post_register_agent(
    body: RegisterAgentRequest,
    x_auditor_id: str | None = Header(default=None, alias="X-Auditor-Id"),
) -> dict[str, Any]:
    auditor_id = _require_auditor(x_auditor_id)
    try:
        record = register_agent(
            session_id=body.session_id,
            auditor_id=auditor_id,
            agent_type=body.agent_type,
            model_id=body.model_id,
            provider=body.provider,
            trust_tier=body.trust_tier,
            authority_scope=body.authority_scope,
            max_synthesis_depth=body.max_synthesis_depth,
            parent_agent_id=body.parent_agent_id,
            agent_id=body.agent_id,
        )
    except Exception as exc:
        raise _translate(exc) from exc
    return record


@app.get("/agents/{agent_id}")
def get_agent(
    agent_id: str,
    x_auditor_id: str | None = Header(default=None, alias="X-Auditor-Id"),
) -> dict[str, Any]:
    _require_auditor(x_auditor_id)
    try:
        return get_agent_identity(agent_id)
    except Exception as exc:
        raise _translate(exc) from exc


@app.post("/agents/{agent_id}/suspend")
def post_suspend_agent(
    agent_id: str,
    body: StatusTransitionRequest,
    x_auditor_id: str | None = Header(default=None, alias="X-Auditor-Id"),
) -> dict[str, Any]:
    auditor_id = _require_auditor(x_auditor_id)
    try:
        return suspend_agent(
            agent_id=agent_id, auditor_id=auditor_id, reason=body.reason
        )
    except Exception as exc:
        raise _translate(exc) from exc


@app.post("/agents/{agent_id}/revoke")
def post_revoke_agent(
    agent_id: str,
    body: StatusTransitionRequest,
    x_auditor_id: str | None = Header(default=None, alias="X-Auditor-Id"),
) -> dict[str, Any]:
    auditor_id = _require_auditor(x_auditor_id)
    try:
        return revoke_agent(
            agent_id=agent_id, auditor_id=auditor_id, reason=body.reason
        )
    except Exception as exc:
        raise _translate(exc) from exc


@app.get("/sessions/{session_id}/registry")
def get_session_registry(
    session_id: str,
    snapshot: bool = False,
    x_auditor_id: str | None = Header(default=None, alias="X-Auditor-Id"),
) -> dict[str, Any]:
    """List ACTIVE agents for a session.

    If snapshot=true, emit an AGENT_SESSION_REGISTRY ledger event in addition
    to returning the list.
    """
    auditor_id = _require_auditor(x_auditor_id)
    try:
        if snapshot:
            event = emit_session_registry(
                session_id=session_id, auditor_id=auditor_id
            )
            return {
                "session_id": session_id,
                "active_agents": event["payload"]["active_agents"],
                "snapshot_event_id": event["event_id"],
            }
        active = list_session_active_agents(session_id)
        return {"session_id": session_id, "active_agents": active}
    except Exception as exc:
        raise _translate(exc) from exc
