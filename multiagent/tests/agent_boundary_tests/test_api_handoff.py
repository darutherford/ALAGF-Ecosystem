"""API integration tests for Sprint-2 boundary endpoints.

Scope: end-to-end routing, header enforcement, and exception translation for
    POST /handshakes
    GET  /sessions/{id}/handshakes
    POST /handoffs
    GET  /handoffs/{id}
    GET  /sessions/{id}/handoffs

Governance rationale: Invariant 1 at the API boundary (X-Auditor-Id required),
Invariant 4 across the boundary (INVALID_AUDITOR produces a ledger event).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from multiagent.ledger.hash_chain.events import read_session_events
from multiagent.orchestrator.agent_lifecycle.registration import register_agent
from multiagent.orchestrator.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _setup_orch_and_sub(session_id: str, auditor_id: str) -> tuple[dict, dict]:
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )
    sub = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    return orch, sub


def test_post_handoffs_without_auditor_header_returns_401(
    client: TestClient, session_id: str
) -> None:
    resp = client.post(
        "/handoffs",
        json={
            "session_id": session_id,
            "source_agent_id": "AGT_000000000001",
            "target_agent_id": "AGT_000000000002",
            "payload_artifact_id": "AGT_000000000003",
        },
    )
    assert resp.status_code == 401


def test_post_handshakes_without_auditor_header_returns_401(
    client: TestClient, session_id: str
) -> None:
    resp = client.post(
        "/handshakes",
        json={
            "session_id": session_id,
            "source_agent_id": "AGT_000000000001",
            "target_agent_id": "AGT_000000000002",
        },
    )
    assert resp.status_code == 401


def test_post_handoffs_with_boundary_violation_returns_422(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    """Target unregistered -> BoundaryViolationError -> 422."""
    orch, _ = _setup_orch_and_sub(session_id, auditor_id)
    resp = client.post(
        "/handoffs",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": orch["agent_id"],
            "target_agent_id": "AGT_ghostghost01",  # unregistered
            "payload_artifact_id": orch["agent_id"],
        },
    )
    assert resp.status_code == 422


def test_post_handoffs_with_invalid_auditor_emits_boundary_violation(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    """API boundary INVALID_AUDITOR path: event emitted BEFORE 403."""
    orch, sub = _setup_orch_and_sub(session_id, auditor_id)
    resp = client.post(
        "/handoffs",
        headers={"X-Auditor-Id": "not-a-real-auditor"},  # fails pattern
        json={
            "session_id": session_id,
            "source_agent_id": orch["agent_id"],
            "target_agent_id": sub["agent_id"],
            "payload_artifact_id": sub["agent_id"],
        },
    )
    assert resp.status_code == 403
    events = read_session_events(session_id)
    violations = [e for e in events if e["event_type"] == "BOUNDARY_VIOLATION"]
    assert len(violations) == 1
    assert violations[0]["payload"]["rejection_reason"] == "INVALID_AUDITOR"


def test_post_handoffs_success_returns_201_and_event(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    orch, sub = _setup_orch_and_sub(session_id, auditor_id)
    resp = client.post(
        "/handoffs",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": orch["agent_id"],
            "target_agent_id": sub["agent_id"],
            "payload_artifact_id": sub["agent_id"],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["event_type"] == "AGENT_HANDOFF"
    assert body["payload"]["agent_handoff"]["source_agent_id"] == orch["agent_id"]
    assert body["payload"]["agent_handoff"]["target_agent_id"] == sub["agent_id"]


def test_get_session_handoffs_returns_ordered_list(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    orch, sub = _setup_orch_and_sub(session_id, auditor_id)
    # Emit two handoffs.
    for _ in range(2):
        client.post(
            "/handoffs",
            headers={"X-Auditor-Id": auditor_id},
            json={
                "session_id": session_id,
                "source_agent_id": orch["agent_id"],
                "target_agent_id": sub["agent_id"],
                "payload_artifact_id": sub["agent_id"],
            },
        )
    resp = client.get(
        f"/sessions/{session_id}/handoffs",
        headers={"X-Auditor-Id": auditor_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert len(body["handoffs"]) == 2
    seqs = [h["sequence_number"] for h in body["handoffs"]]
    assert seqs == sorted(seqs)


def test_get_single_handoff_by_id(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    orch, sub = _setup_orch_and_sub(session_id, auditor_id)
    emit = client.post(
        "/handoffs",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": orch["agent_id"],
            "target_agent_id": sub["agent_id"],
            "payload_artifact_id": sub["agent_id"],
        },
    ).json()
    handoff_id = emit["payload"]["agent_handoff"]["artifact_id"]

    resp = client.get(
        f"/handoffs/{handoff_id}",
        params={"session_id": session_id},
        headers={"X-Auditor-Id": auditor_id},
    )
    assert resp.status_code == 200
    assert resp.json()["payload"]["agent_handoff"]["artifact_id"] == handoff_id


def test_post_handshakes_success_and_listing(
    client: TestClient, session_id: str, auditor_id: str
) -> None:
    orch = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="ROUTING",
        max_synthesis_depth=3,
    )
    sub_a = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    sub_b = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="SUB_AGENT", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T2", authority_scope="HYPOTHESES",
        max_synthesis_depth=1, parent_agent_id=orch["agent_id"],
    )
    resp = client.post(
        "/handshakes",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": sub_a["agent_id"],
            "target_agent_id": sub_b["agent_id"],
            "channel_purpose": "api-test",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["event_type"] == "BOUNDARY_HANDSHAKE"

    listing = client.get(
        f"/sessions/{session_id}/handshakes",
        headers={"X-Auditor-Id": auditor_id},
    )
    assert listing.status_code == 200
    channels = listing.json()["channels"]
    assert len(channels) == 1
    assert channels[0]["source_agent_id"] == sub_a["agent_id"]
    assert channels[0]["target_agent_id"] == sub_b["agent_id"]
