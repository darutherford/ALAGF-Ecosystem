"""API tests for Sprint-3 Hypothesis endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from multiagent.api.hypothesis_routes import (
    get_ledger_reader,
    get_ledger_writer,
    get_registry,
    router,
)
from multiagent.orchestrator.agent_lifecycle.registration import register_agent
from multiagent.orchestrator.synthesis.fs_adapter import FsLedger
from multiagent.orchestrator.synthesis.fs_agent_registry import FsAgentRegistry


@pytest.fixture
def hypothesis_client():
    """TestClient with Sprint-3 DI wired to filesystem-backed adapters."""
    ledger = FsLedger()
    registry = FsAgentRegistry()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_registry] = lambda: registry
    app.dependency_overrides[get_ledger_reader] = lambda: ledger
    app.dependency_overrides[get_ledger_writer] = lambda: ledger
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_post_hypothesis_without_auditor_header_returns_401(
    hypothesis_client, session_id: str
):
    resp = hypothesis_client.post(
        "/hypotheses",
        json={
            "session_id": session_id,
            "source_agent_id": "AGT_000000000001",
            "observation_refs": ["OBS_000000000001"],
            "composite_upstream_bme_score": 0.1,
        },
    )
    assert resp.status_code == 401


def test_post_hypothesis_with_malformed_auditor_returns_403(
    hypothesis_client, session_id: str
):
    resp = hypothesis_client.post(
        "/hypotheses",
        headers={"X-Auditor-Id": "not-an-auditor"},
        json={
            "session_id": session_id,
            "source_agent_id": "AGT_000000000001",
            "observation_refs": ["OBS_000000000001"],
            "composite_upstream_bme_score": 0.1,
        },
    )
    assert resp.status_code == 403


def test_post_hypothesis_success_returns_201(
    hypothesis_client, session_id: str, auditor_id: str
):
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=3,
    )
    resp = hypothesis_client.post(
        "/hypotheses",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": agent["agent_id"],
            "observation_refs": ["OBS_000000000001"],
            "upstream_hypothesis_refs": [],
            "composite_upstream_bme_score": 0.1,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["hypothesis"]["synthesis_depth"] == 1
    assert body["bme_score_source"] == "placeholder"


def test_post_hypothesis_with_ceiling_violation_returns_422(
    hypothesis_client, session_id: str, auditor_id: str
):
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=1,
    )
    r1 = hypothesis_client.post(
        "/hypotheses",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": agent["agent_id"],
            "observation_refs": ["OBS_000000000001"],
            "upstream_hypothesis_refs": [],
            "composite_upstream_bme_score": 0.1,
        },
    )
    assert r1.status_code == 201
    h1 = r1.json()["hypothesis"]["artifact_id"]

    r2 = hypothesis_client.post(
        "/hypotheses",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": agent["agent_id"],
            "observation_refs": ["OBS_000000000001"],
            "upstream_hypothesis_refs": [h1],
            "composite_upstream_bme_score": 0.1,
        },
    )
    assert r2.status_code == 422
    assert r2.json()["detail"]["error"] == "DEPTH_LIMIT_EXCEEDED"


def test_get_depth_state_returns_frozen_after_ceiling_hit(
    hypothesis_client, session_id: str, auditor_id: str
):
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=1,
    )
    r0 = hypothesis_client.get(
        f"/sessions/{session_id}/depth_state",
        headers={"X-Auditor-Id": auditor_id},
    )
    assert r0.status_code == 200
    assert r0.json()["frozen"] is False

    r1 = hypothesis_client.post(
        "/hypotheses",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": agent["agent_id"],
            "observation_refs": ["OBS_000000000001"],
            "composite_upstream_bme_score": 0.1,
        },
    )
    h1 = r1.json()["hypothesis"]["artifact_id"]
    hypothesis_client.post(
        "/hypotheses",
        headers={"X-Auditor-Id": auditor_id},
        json={
            "session_id": session_id,
            "source_agent_id": agent["agent_id"],
            "observation_refs": ["OBS_000000000001"],
            "upstream_hypothesis_refs": [h1],
            "composite_upstream_bme_score": 0.1,
        },
    )

    r2 = hypothesis_client.get(
        f"/sessions/{session_id}/depth_state",
        headers={"X-Auditor-Id": auditor_id},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["frozen"] is True
    assert h1 in body["frozen_provenance_ancestors"]


def test_list_hypotheses_returns_ordered_list(
    hypothesis_client, session_id: str, auditor_id: str
):
    agent = register_agent(
        session_id=session_id, auditor_id=auditor_id,
        agent_type="ORCHESTRATOR", model_id="claude-sonnet-4-6",
        provider="anthropic", trust_tier="T1", authority_scope="HYPOTHESES",
        max_synthesis_depth=5,
    )
    ids = []
    parent: list[str] = []
    for i in range(3):
        r = hypothesis_client.post(
            "/hypotheses",
            headers={"X-Auditor-Id": auditor_id},
            json={
                "session_id": session_id,
                "source_agent_id": agent["agent_id"],
                "observation_refs": ["OBS_000000000001"],
                "upstream_hypothesis_refs": parent,
                "composite_upstream_bme_score": 0.1,
            },
        )
        assert r.status_code == 201, r.json()
        hid = r.json()["hypothesis"]["artifact_id"]
        ids.append(hid)
        parent = [hid]

    r = hypothesis_client.get(
        f"/sessions/{session_id}/hypotheses",
        headers={"X-Auditor-Id": auditor_id},
    )
    assert r.status_code == 200
    payloads = r.json()
    assert [p["hypothesis"]["artifact_id"] for p in payloads] == ids
    assert [p["hypothesis"]["synthesis_depth"] for p in payloads] == [1, 2, 3]
