# ECOSYSTEM-SPRINT-1 Changelog

**Sprint:** ECOSYSTEM-SPRINT-1 — AgentIdentity lifecycle and ledger registration enforcement
**Track:** /multiagent
**Prior commit:** 2bdfa42 (Sprint-0 scaffold and schema initialization)
**Auditor:** AUDITOR_DALE_001

## Scope

Sprint-1 implemented the AgentIdentity lifecycle — create, register, persist, suspend, revoke — with full ledger event emission and runtime schema enforcement. No schemas in `/shared/artifact-contracts/` were modified; Sprint-1 is pure runtime and test implementation on top of the Sprint-0 v2 contracts.

## Additions

### Runtime modules

| Path | Purpose | Governance traceability |
|---|---|---|
| `multiagent/exceptions.py` | Typed exception taxonomy | Invariant 4 — no silent failures |
| `multiagent/artifacts/ContractValidator.py` | jsonschema wrapper, cache | Precondition 1 — schemas are single source of truth |
| `multiagent/artifacts/AgentIdentity/__init__.py` | Factory, validation, serialization | Invariant 1 — runtime rejection of `non_authoritative_flag` override |
| `multiagent/ledger/hash_chain/events.py` | Append-only hash-chained event writer | Invariant 4 — ledger-alone reconstructability |
| `multiagent/orchestrator/agent_lifecycle/registration.py` | Register, suspend, revoke, lookup, manifest | Invariants 1, 3, 4 |
| `multiagent/orchestrator/api.py` | FastAPI endpoints with header enforcement | Invariant 1 — API-boundary auditor gate |

### Event payload schemas (`multiagent/ledger/hash_chain/event_schemas/v2/`)

| Schema | Event type | Rationale |
|---|---|---|
| `AGENT_REGISTERED.payload.schema.json` | AGENT_REGISTERED | Invariant 4 — full AgentIdentity captured at registration |
| `AGENT_SUSPENDED.payload.schema.json` | AGENT_SUSPENDED | Invariant 3 — requires `prior_registration_event_id` |
| `AGENT_REVOKED.payload.schema.json` | AGENT_REVOKED | Invariant 3 — requires `prior_registration_event_id` |
| `UNREGISTERED_AGENT_OUTPUT.payload.schema.json` | UNREGISTERED_AGENT_OUTPUT | Invariant 4 — structured rejection reason |
| `AGENT_SESSION_REGISTRY.payload.schema.json` | AGENT_SESSION_REGISTRY | Invariant 4 — session manifest |
| `LedgerEvent.envelope.schema.json` | (envelope for all) | Invariant 4 — SHA-256 hash chain, causal refs |

### Sprint-1 design decisions (ratified)

1. **agent_id format.** Factory generates canonical `AGT_<12 hex chars>`. Schema permits any non-empty string for external submissions.
2. **auditor_id pattern.** Orchestrator-layer stricter regex `^AUDITOR_[A-Z0-9_]+$` on top of the schema's permissive `minLength: 1`. Schema unchanged.
3. **event_id format.** ULID prefixed `evt_` for lexicographic ordering and uniqueness. `sequence_number` remains authoritative for ordering within a session.
4. **Genesis event.** Per-session chain. First event in a session has `prev_hash: null`. Formal `SESSION_START` is deferred to the sprint that implements AuditSession v2 runtime.
5. **Append-only registry.** Registration files are written with `O_CREAT | O_EXCL` and never modified. Status transitions emit marker files named `<agent_id>__<status>__<event_id>.json`. Current status is computed by scanning markers.

## Invariant acceptance — Sprint-1

All four invariants have passing acceptance suites. Total: **40 passed, 1 skipped** (Sprint-3 placeholder).

- **Invariant 1 (Authority):** 6 tests — non_authoritative_flag override rejection, auditor pattern enforcement, empty and lowercase auditor rejection.
- **Invariant 2 (Non-Bypass):** 6 tests — max_synthesis_depth persistence across parametrized values, schema minimum enforcement, Sprint-3 ceiling enforcement reserved.
- **Invariant 3 (Evidence-First):** 3 tests — AGENT_REGISTERED carries auditor/session, suspension/revocation reference prior registration event.
- **Invariant 4 (Reconstructability):** 4 tests — ledger-alone reconstruction of ACTIVE set, no-silent-failure rejection, hash chain tamper detection, clean replay verification.

Plus 11 agent boundary tests and 10 API integration tests.

## Deferred to later sprints

| Feature | Sprint |
|---|---|
| `AGENT_HANDOFF` event and inter-agent boundary crossing logic | Sprint-2 |
| `BOUNDARY_HANDSHAKE` event | Sprint-2 |
| `DEPTH_LIMIT_REACHED` event and structural ceiling enforcement | Sprint-3 |
| Multi-agent orchestrator control flow | Sprint-3 |
| BME attribution per agent, `composite_upstream_bme_score` computation | Sprint-4 |
| Human Decision Console (multi-agent extension) | Sprint-5 |
| Evidence pack export (agent-boundary aware) | Sprint-6 |

## Schema changes

**None.** Sprint-1 did not modify any v1 or v2 artifact schema.

## Cross-track impact

**None.** `/demo` untouched. `/shared/artifact-contracts/v2/` schemas unchanged.

## Known defects — routed to Sprint-0 remediation backlog

See `/docs/release-notes/sprint-0-reconciliation.md` for the full reconciliation record. Summary:

1. v2 schemas committed in `2bdfa42` were missing from the working tree. Recovered via `git checkout HEAD -- shared/artifact-contracts/v2/`.
2. `/demo/ledger/` contains untracked directory shells with no committed Python source. The frozen v1 demo ledger does not exist in history at `2bdfa42`. Sprint-1 proceeded with Path A: author the v2 ledger de novo.
3. v2 Hypothesis schema does not declare `source_agent_id`, while Observation and Action do. This blocks direct agent attribution on Hypothesis artifacts and weakens BME-A attribution (Sprint-4 dependency). Logged as Sprint-0 backlog; no Sprint-1 runtime impact since Hypothesis is out of scope.
