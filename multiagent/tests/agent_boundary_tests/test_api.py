"""API integration tests for /multiagent/orchestrator/api.py.

Governance rationale:
    - Invariant 1: missing X-Auditor-Id header must produce 401, proving
      the boundary enforcement is wired, not just declared.
    - End-to-end exception translation: typed domain exceptions must surface
      as the correct HTTP status codes (AuthorityViolationError -> 403,
      UnregisteredAgentError -> 404, AgentRegistrationError -> 409,
      ArtifactValidationError -> 422).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from multiagent.orchestrator.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _valid_body(
    session_id: str,
    *,
    agent_type: str = "ORCHESTRATOR",
    parent_agent_id: str | None = None,
) -> dict:
    body = {
        "session_id": session_id,
        "agent_type": agent_type,
        "model_id": "claude-sonnet-4-6",
        "provider": "anthropic",
        "trust_tier": "T1",
        "authority_scope": "ROUTING",
        "max_synthesis_depth": 2,
    }
    if parent_agent_id is not None:
        body["parent_agent_id"] = parent_agent_id
    return body


def test_post_agents_without_auditor_header_returns_401(
    client: TestClient, session_id: str
) -> None:
    response = client.post("/agents", json=_valid_body(session_id))
    assert response.status_code == 401
    assert "X-Auditor-Id" in response.json()["detail"]


def test_post_agents_with_malformed_auditor_returns_403(
    client: TestClient, session_id: str
) -> None:
    response = client.post(
        "/agents",
        json=_valid_body(session_id),
        headers={"X-Auditor-Id": "not-an-auditor"},
    )
    assert response.status_code == 403


def test_post_agents_success_returns_201(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    response = client.post(
        "/agents",
        json=_valid_body(session_id),
        headers={"X-Auditor-Id": auditor_id},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["agent_type"] == "ORCHESTRATOR"
    assert body["status"] == "ACTIVE"
    assert body["non_authoritative_flag"] is True
    assert body["agent_id"].startswith("AGT_")


def test_get_agent_roundtrip(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    created = client.post(
        "/agents",
        json=_valid_body(session_id),
        headers={"X-Auditor-Id": auditor_id},
    ).json()
    agent_id = created["agent_id"]
    response = client.get(
        f"/agents/{agent_id}", headers={"X-Auditor-Id": auditor_id}
    )
    assert response.status_code == 200
    assert response.json()["agent_id"] == agent_id


def test_get_nonexistent_agent_returns_404(
    client: TestClient, auditor_id: str
) -> None:
    response = client.get(
        "/agents/AGT_nonexistent1", headers={"X-Auditor-Id": auditor_id}
    )
    assert response.status_code == 404


def test_suspend_roundtrip(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    created = client.post(
        "/agents",
        json=_valid_body(session_id),
        headers={"X-Auditor-Id": auditor_id},
    ).json()
    agent_id = created["agent_id"]

    response = client.post(
        f"/agents/{agent_id}/suspend",
        json={"reason": "test"},
        headers={"X-Auditor-Id": auditor_id},
    )
    assert response.status_code == 200
    assert response.json()["event_type"] == "AGENT_SUSPENDED"

    fetched = client.get(
        f"/agents/{agent_id}", headers={"X-Auditor-Id": auditor_id}
    ).json()
    assert fetched["status"] == "SUSPENDED"


def test_revoke_is_terminal(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    created = client.post(
        "/agents",
        json=_valid_body(session_id),
        headers={"X-Auditor-Id": auditor_id},
    ).json()
    agent_id = created["agent_id"]

    first = client.post(
        f"/agents/{agent_id}/revoke",
        json={"reason": "terminal"},
        headers={"X-Auditor-Id": auditor_id},
    )
    assert first.status_code == 200

    second = client.post(
        f"/agents/{agent_id}/revoke",
        json={"reason": "again"},
        headers={"X-Auditor-Id": auditor_id},
    )
    assert second.status_code == 409


def test_sub_agent_with_null_parent_returns_422(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    """Schema violation surfaces as 422 (ArtifactValidationError)."""
    body = _valid_body(session_id, agent_type="SUB_AGENT")
    # Explicitly omit parent_agent_id; schema allOf rejects.
    response = client.post(
        "/agents", json=body, headers={"X-Auditor-Id": auditor_id}
    )
    assert response.status_code == 422


def test_session_registry_endpoint(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    client.post(
        "/agents",
        json=_valid_body(session_id),
        headers={"X-Auditor-Id": auditor_id},
    )
    response = client.get(
        f"/sessions/{session_id}/registry",
        headers={"X-Auditor-Id": auditor_id},
    )
    assert response.status_code == 200
    assert len(response.json()["active_agents"]) == 1


def test_session_registry_snapshot_emits_event(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    client.post(
        "/agents",
        json=_valid_body(session_id),
        headers={"X-Auditor-Id": auditor_id},
    )
    response = client.get(
        f"/sessions/{session_id}/registry?snapshot=true",
        headers={"X-Auditor-Id": auditor_id},
    )
    assert response.status_code == 200
    assert "snapshot_event_id" in response.json()
    assert response.json()["snapshot_event_id"].startswith("evt_")
