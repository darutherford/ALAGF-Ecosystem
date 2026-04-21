# ALAGF Multiagent Track

Active development track for the ALAGF multi-agent governance extension. Sprint-1 delivered the AgentIdentity lifecycle and v2 ledger.

## Directory Layout

```
multiagent/
├── __init__.py
├── exceptions.py                         — typed exception taxonomy
├── artifacts/
│   ├── ContractValidator.py              — jsonschema wrapper, cache
│   └── AgentIdentity/
│       └── __init__.py                   — factory, validation, serialization
├── ledger/
│   ├── agent_registry/                   — one JSON file per agent (append-only)
│   └── hash_chain/
│       ├── events.py                     — writer, reader, chain verification
│       ├── sessions/<session_id>/        — event log per session
│       └── event_schemas/v2/             — payload and envelope schemas
├── orchestrator/
│   ├── api.py                            — FastAPI endpoints
│   └── agent_lifecycle/
│       └── registration.py               — register, suspend, revoke, lookup
├── tests/
│   ├── conftest.py                       — ledger-clean fixture
│   ├── invariant_tests/                  — one test file per invariant
│   └── agent_boundary_tests/             — structural rules + API integration
└── docs/
    ├── schema_versions/
    │   └── sprint-1-changelog.md
    └── sprint_prompts/
```

## Running Tests

From the repository root:

```powershell
python -m pytest multiagent/tests/ -v
```

Expected result at Sprint-1 close: **40 passed, 1 skipped** (Sprint-3 placeholder for `DEPTH_LIMIT_REACHED`).

## Running the API

```powershell
python -m uvicorn multiagent.orchestrator.api:app --reload
```

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| POST | `/agents` | Register a new AgentIdentity |
| GET | `/agents/{agent_id}` | Retrieve a registered identity |
| POST | `/agents/{agent_id}/suspend` | Transition to SUSPENDED |
| POST | `/agents/{agent_id}/revoke` | Transition to REVOKED (terminal) |
| GET | `/sessions/{session_id}/registry` | List ACTIVE agents |
| GET | `/sessions/{session_id}/registry?snapshot=true` | Emit `AGENT_SESSION_REGISTRY` event |

All endpoints require the `X-Auditor-Id` header matching the pattern `^AUDITOR_[A-Z0-9_]+$`.

## Invariant Enforcement — Sprint-1 Scope

| Invariant | Enforced where |
|---|---|
| 1 — Authority | `AgentIdentity.non_authoritative_flag` hard-coded true (schema + factory); auditor pattern check; `registered_by` must be human |
| 2 — Non-Bypass | `max_synthesis_depth` persists unmodified and is retrievable; ceiling enforcement reserved for Sprint-3 |
| 3 — Evidence-First | Every state transition references the prior registration event via `causal_refs` and payload |
| 4 — Reconstructability | Append-only files, SHA-256 hash chain, `UNREGISTERED_AGENT_OUTPUT` emission before rejection |

## Dependencies

```
jsonschema
fastapi
pydantic>=2
pytest
httpx    # for TestClient in API tests
```
