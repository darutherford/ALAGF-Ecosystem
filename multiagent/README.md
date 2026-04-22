# ALAGF Multiagent Track

Active development track for the ALAGF multi-agent governance extension.
Sprint-1 delivered the AgentIdentity lifecycle and v2 ledger. Sprint-2
extends the runtime with AgentHandoff emission, BOUNDARY_HANDSHAKE
protocol, and BOUNDARY_VIOLATION error-event discipline at every
inter-agent boundary crossing.

Core principle: **agent boundaries are governance boundaries**. Every
crossing is a first-class ledger event, not an implementation detail.

## Directory Layout

```
multiagent/
├── __init__.py
├── exceptions.py                         — typed exception taxonomy
├── artifacts/
│   ├── ContractValidator.py              — jsonschema wrapper, cache
│   ├── AgentIdentity/
│   │   └── __init__.py                   — factory, validation, serialization
│   └── AgentHandoff/
│       └── __init__.py                   — factory, Invariant 1 runtime enforcement
├── ledger/
│   ├── agent_registry/                   — one JSON file per agent (append-only)
│   └── hash_chain/
│       ├── events.py                     — writer, reader, chain verification
│       ├── sessions/<session_id>/        — event log per session
│       └── event_schemas/v2/             — payload and envelope schemas
├── orchestrator/
│   ├── api.py                            — FastAPI endpoints
│   ├── agent_lifecycle/
│   │   └── registration.py               — register, suspend, revoke, lookup
│   └── boundary_enforcement/             — Sprint-2 boundary runtime
│       ├── handshake.py                  — BOUNDARY_HANDSHAKE emission, channel lookup
│       └── handoff.py                    — AGENT_HANDOFF emission, precondition checks
├── tests/
│   ├── conftest.py                       — ledger-clean fixture
│   ├── invariant_tests/                  — one test file per invariant
│   └── agent_boundary_tests/             — structural rules + API integration
└── docs/
    ├── schema_versions/
    │   ├── sprint-1-changelog.md
    │   └── sprint-2-changelog.md
    └── sprint_prompts/
```

## Running Tests

From the repository root:

```powershell
python -m pytest multiagent/tests/ -v
```

Expected result at Sprint-2 close: **78 passed, 1 skipped** (the skip is
a Sprint-3 placeholder for `DEPTH_LIMIT_REACHED` structural enforcement).

## Running the API

```powershell
python -m uvicorn multiagent.orchestrator.api:app --reload
```

### Endpoints

All endpoints require the `X-Auditor-Id` header matching the pattern
`^AUDITOR_[A-Z0-9_]+$`. Boundary endpoints additionally emit
`BOUNDARY_VIOLATION` with `INVALID_AUDITOR` before returning 403 on
malformed values.

| Method | Path                                              | Introduced | Purpose                                       |
|--------|---------------------------------------------------|------------|-----------------------------------------------|
| POST   | `/agents`                                         | Sprint-1   | Register a new AgentIdentity                  |
| GET    | `/agents/{agent_id}`                              | Sprint-1   | Retrieve a registered identity                |
| POST   | `/agents/{agent_id}/suspend`                      | Sprint-1   | Transition to SUSPENDED                       |
| POST   | `/agents/{agent_id}/revoke`                       | Sprint-1   | Transition to REVOKED (terminal)              |
| GET    | `/sessions/{session_id}/registry`                 | Sprint-1   | List ACTIVE agents                            |
| GET    | `/sessions/{session_id}/registry?snapshot=true`   | Sprint-1   | Emit `AGENT_SESSION_REGISTRY` event           |
| POST   | `/handshakes`                                     | Sprint-2   | Emit a directional `BOUNDARY_HANDSHAKE`       |
| GET    | `/sessions/{session_id}/handshakes`               | Sprint-2   | List established channels                    |
| POST   | `/handoffs`                                       | Sprint-2   | Emit an `AGENT_HANDOFF` event                 |
| GET    | `/handoffs/{handoff_id}?session_id=...`           | Sprint-2   | Retrieve a specific handoff event             |
| GET    | `/sessions/{session_id}/handoffs`                 | Sprint-2   | List session handoffs by sequence order       |

### Exception-to-HTTP Mapping

| Exception                 | HTTP |
|---------------------------|------|
| `AuthorityViolationError` | 403  |
| `UnregisteredAgentError`  | 404  |
| `AgentRegistrationError`  | 409  |
| `BoundaryViolationError`  | 422  |
| `HandshakeError`          | 422  |
| `ArtifactValidationError` | 422  |
| `LedgerIntegrityError`    | 500  |

## Ledger Event Types (v2, post-Sprint-2)

| Event                       | Sprint     | Purpose                                                    |
|-----------------------------|------------|------------------------------------------------------------|
| `AGENT_REGISTERED`          | Sprint-1   | New `AgentIdentity` committed                              |
| `AGENT_SUSPENDED`           | Sprint-1   | Status transition to SUSPENDED                             |
| `AGENT_REVOKED`             | Sprint-1   | Status transition to REVOKED (terminal)                    |
| `UNREGISTERED_AGENT_OUTPUT` | Sprint-1   | Output received from unregistered/inactive agent           |
| `AGENT_SESSION_REGISTRY`    | Sprint-1   | Manifest of ACTIVE agents at snapshot time                 |
| `AGENT_HANDOFF`             | Sprint-2   | Inter-agent output boundary crossing                       |
| `BOUNDARY_HANDSHAKE`        | Sprint-2   | Directional channel establishment between two agents       |
| `BOUNDARY_VIOLATION`        | Sprint-2   | Rejected handoff or handshake attempt (emit-before-raise)  |

### BOUNDARY_VIOLATION rejection_reason enum (closed)

`SOURCE_UNREGISTERED` · `TARGET_UNREGISTERED` · `SOURCE_INACTIVE` ·
`TARGET_INACTIVE` · `CROSS_SESSION` · `MISSING_HANDSHAKE` ·
`BINDING_PAYLOAD` · `UNKNOWN_PAYLOAD` · `SELF_HANDOFF` ·
`INVALID_AUDITOR` · `DISALLOWED_ORIGINATOR_VALIDATOR` ·
`DISALLOWED_ORIGINATOR_HUMAN_PROXY`

## Invariant Enforcement — Scope Through Sprint-2

| Invariant | Enforced where |
|-----------|----------------|
| 1 — Authority | `AgentIdentity.non_authoritative_flag` and `AgentHandoff.non_authoritative_flag` hard-coded true (schema + factory); auditor pattern check; `BINDING_PAYLOAD` rejection on handoff |
| 2 — Non-Bypass | `max_synthesis_depth` persists unmodified; ceiling enforcement reserved for Sprint-3; handoff lifecycle introduces no bypass of future `delegation_blocked` |
| 3 — Evidence-First | Every state transition references prior events via `causal_refs` and payload; peer-level handoffs require prior `BOUNDARY_HANDSHAKE`; payload discoverability (registry ∪ prior ledger) |
| 4 — Reconstructability | Append-only files, SHA-256 hash chain, `UNREGISTERED_AGENT_OUTPUT` / `BOUNDARY_VIOLATION` emission before rejection, directional channels derived purely from ledger events |

## Dependencies

```
jsonschema
fastapi
pydantic>=2
pytest
httpx    # for TestClient in API tests
```

## Changelogs

- [Sprint-1](docs/schema_versions/sprint-1-changelog.md) — AgentIdentity lifecycle, v2 ledger
- [Sprint-2](docs/schema_versions/sprint-2-changelog.md) — Agent-boundary events and handoff logic
