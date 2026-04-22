# ALAGF Multiagent Track

Active development track for the ALAGF multi-agent governance extension.
Sprint-1 delivered the AgentIdentity lifecycle and v2 ledger. Sprint-2
extends the runtime with AgentHandoff emission, BOUNDARY_HANDSHAKE
protocol, and BOUNDARY_VIOLATION error-event discipline at every
inter-agent boundary crossing. Sprint-3 introduces the Hypothesis runtime
and transforms `max_synthesis_depth` from persisted-but-unenforced
metadata into architectural enforcement via chain-minimum ceiling
attribution and path-scoped session freeze.

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
│   ├── AgentHandoff/
│   │   └── __init__.py                   — factory, Invariant 1 runtime enforcement
│   └── Hypothesis/                       — Sprint-3
│       └── __init__.py                   — factory, HEAD-schema conformance
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
│   ├── boundary_enforcement/             — Sprint-2 boundary runtime
│   │   ├── handshake.py                  — BOUNDARY_HANDSHAKE emission, channel lookup
│   │   └── handoff.py                    — AGENT_HANDOFF emission, precondition checks
│   └── synthesis/                        — Sprint-3
│       ├── depth.py                      — chain-minimum ceiling, freeze derivation
│       ├── hypothesis.py                 — precondition pipeline, emit_hypothesis
│       └── fs_adapter.py                 — LedgerReader/Writer over Sprint-1/2 ledger
├── tests/
│   ├── conftest.py                       — ledger-clean fixture
│   ├── invariant_tests/                  — one test file per invariant
│   └── agent_boundary_tests/             — structural rules + API integration
└── docs/
    ├── schema_versions/
    │   ├── sprint-1-changelog.md
    │   ├── sprint-2-changelog.md
    │   └── sprint-3-changelog.md         — Sprint-3
    └── sprint_prompts/
```

## Running Tests

From the repository root:

```powershell
python -m pytest multiagent/tests/ -v
```

Expected result at Sprint-3 close: **Sprint-1/2 baseline (78 passed) plus
Sprint-3 additions, with the previously-skipped
`test_depth_ceiling_emits_depth_limit_reached_event` now passing as a real
test.** Skip count drops to 0.

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
| POST   | `/hypotheses`                                     | Sprint-3   | Emit a Hypothesis                             |
| GET    | `/hypotheses/{artifact_id}?session_id=...`        | Sprint-3   | Retrieve a specific Hypothesis                |
| GET    | `/sessions/{session_id}/hypotheses`               | Sprint-3   | List session Hypotheses by sequence order     |
| GET    | `/sessions/{session_id}/depth_state`              | Sprint-3   | Freeze status and per-agent ceilings          |

### Exception-to-HTTP Mapping

| Exception                 | HTTP | Introduced |
|---------------------------|------|------------|
| `AuthorityViolationError` | 403  | Sprint-1   |
| `UnregisteredAgentError`  | 404  | Sprint-1   |
| `AgentRegistrationError`  | 409  | Sprint-1   |
| `BoundaryViolationError`  | 422  | Sprint-2   |
| `HandshakeError`          | 422  | Sprint-2   |
| `ArtifactValidationError` | 422  | Sprint-1   |
| `LedgerIntegrityError`    | 500  | Sprint-1   |
| `DepthLimitExceededError` | 422  | Sprint-3   |
| `ScopeViolationError`     | 403  | Sprint-3   |
| `FrozenPathError`         | 409  | Sprint-3   |
| `UpstreamResolutionError` | 422  | Sprint-3   |
| `HypothesisValidationError` | 422 | Sprint-3   |

## Ledger Event Types (v2, post-Sprint-3)

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
| `HYPOTHESIS_REGISTERED`     | Sprint-3   | Successful Hypothesis synthesis                            |
| `DEPTH_LIMIT_REACHED`       | Sprint-3   | Chain-minimum ceiling exceeded (emit-before-raise)         |

### BOUNDARY_VIOLATION rejection_reason enum (closed)

`SOURCE_UNREGISTERED` · `TARGET_UNREGISTERED` · `SOURCE_INACTIVE` ·
`TARGET_INACTIVE` · `CROSS_SESSION` · `MISSING_HANDSHAKE` ·
`BINDING_PAYLOAD` · `UNKNOWN_PAYLOAD` · `SELF_HANDOFF` ·
`INVALID_AUDITOR` · `DISALLOWED_ORIGINATOR_VALIDATOR` ·
`DISALLOWED_ORIGINATOR_HUMAN_PROXY`

### DEPTH_LIMIT_REACHED rejection_reason enum (closed)

`CHAIN_MINIMUM_CEILING_EXCEEDED` — the prospective Hypothesis's
`synthesis_depth` exceeds the chain-minimum `max_synthesis_depth` across
the union of the emitting agent and all agents in the transitive upstream
provenance chain (Sprint-3 decision (a)).

## Invariant Enforcement — Scope Through Sprint-3

| Invariant | Enforced where |
|-----------|----------------|
| 1 — Authority | `AgentIdentity.non_authoritative_flag`, `AgentHandoff.non_authoritative_flag`, and `Hypothesis.non_authoritative_flag` all hard-coded true (schema `const` + factory rejection); auditor pattern check; `BINDING_PAYLOAD` rejection on handoff; envelope `actor_type` distinguishes HUMAN / AGENT / ORCHESTRATOR |
| 2 — Non-Bypass | `max_synthesis_depth` persists unmodified (Sprint-1); **Sprint-3: chain-minimum ceiling evaluated at every Hypothesis emission — union of source agent and all upstream chain agents; depth-exceeding synthesis is architecturally rejected; emission of `DEPTH_LIMIT_REACHED` precedes `DepthLimitExceededError`; path-scoped session freeze derived from ledger prevents continued synthesis on the affected provenance path; no override flag, escape hatch, or configuration switch permits bypass.** Handoff lifecycle introduces no bypass of future `delegation_blocked`. |
| 3 — Evidence-First | Every state transition references prior events via `causal_refs` and payload; peer-level handoffs require prior `BOUNDARY_HANDSHAKE`; payload discoverability (registry ∪ prior ledger); **Sprint-3: every Hypothesis carries `observation_refs` with `minItems: 1` regardless of depth (decision (g-i)); upstream refs must resolve to prior `HYPOTHESIS_REGISTERED`; self-reference is rejected.** |
| 4 — Reconstructability | Append-only files, SHA-256 hash chain, `UNREGISTERED_AGENT_OUTPUT` / `BOUNDARY_VIOLATION` emission before rejection, directional channels derived purely from ledger events; **Sprint-3: freeze state derived purely from `DEPTH_LIMIT_REACHED` events (no external state); `DEPTH_LIMIT_REACHED` payload denormalizes `ceiling_attribution` (binding agent + bound) and `frozen_provenance_ancestors` for ledger-only reconstruction.** |

### Sprint-3 Depth-Ceiling Enforcement

Chain-minimum attribution (decision (a)): the governing ceiling for any
prospective Hypothesis synthesis is

```
min(max_synthesis_depth) over {source_agent} ∪ transitive_upstream_agents
```

This closes the relay-laundering vector: a high-ceiling agent cannot consume
a low-ceiling agent's output to extend effective inferential depth. The
binding agent is recorded on the event payload for reconstructability.

Path-scoped freeze (decision (b)): when `DEPTH_LIMIT_REACHED` fires, the
transitive closure of the attempted upstream chain is recorded as
`frozen_provenance_ancestors`. Subsequent emissions whose provenance chain
intersects this set are rejected with `FrozenPathError`. Parallel paths
continue. Freeze state is derived from the ledger at evaluation time;
there is no cached freeze object.

BME score source marker (decision (e-revised)): the HEAD Sprint-0 schema
requires `composite_upstream_bme_score` as a non-nullable number in
`[0.0, 1.0]`. Sprint-3 accepts caller-supplied placeholder values and
marks the event payload with `bme_score_source: "placeholder"`. Sprint-4
BME attribution will populate real values and set
`bme_score_source: "computed"`. This preserves schema integrity while
retaining traceability of provenance-of-value.

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
- [Sprint-3](docs/schema_versions/sprint-3-changelog.md) — Hypothesis runtime and depth-ceiling enforcement
