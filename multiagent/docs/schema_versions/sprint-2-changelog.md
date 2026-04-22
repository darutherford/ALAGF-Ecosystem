# ECOSYSTEM-SPRINT-2 Changelog

**Sprint:** ECOSYSTEM-SPRINT-2 — Agent-boundary ledger events and handoff logic
**Auditor:** AUDITOR_DALE_001
**Baseline:** Sprint-1 @ `344f3bc`
**Scope:** AgentHandoff lifecycle, BOUNDARY_HANDSHAKE protocol, boundary
precondition enforcement, BOUNDARY_VIOLATION error-event discipline, API
endpoints, and expanded invariant acceptance coverage.

---

## 1. Design Decision Ledger

Six open design questions were surfaced at Sprint-2 open. The following
decisions were ratified before implementation and drive the runtime.

### (a) Channel Directionality — DIRECTIONAL

A BOUNDARY_HANDSHAKE establishes the source-to-target channel only. The
reverse direction requires its own handshake event. Each direction of
information flow is an independently auditable boundary crossing.

**Governance rationale:** Invariant 3 (Evidence-First). Per-direction
granularity preserves the evidence record for each distinct information
flow. Bidirectional handshakes would have conflated two distinct channels
into one event, weakening the audit posture.

**Alternative considered:** Bidirectional (single event establishes both
directions). Rejected because agent boundaries are governance boundaries;
each direction is a distinct boundary.

### (b) Payload Artifact Discoverability — UNION (Registry ∪ Prior Ledger)

A `payload_artifact_id` resolves if it matches an AgentIdentity in the
session registry OR an artifact referenced by a prior ledger event in the
same session. Anything outside these two sets is UNKNOWN_PAYLOAD.

**Governance rationale:** Invariant 3. Restricting to registry-only would
prohibit artifact handoffs; restricting to ledger-only would prohibit
first-move handoffs referencing registered agents. Union resolution
satisfies Invariant 3 without being over-permissive.

**Implementation note:** The resolver inspects AGENT_REGISTERED payloads
(via `payload.agent_identity.agent_id`), AGENT_HANDOFF payloads (via both
`artifact_id` and transported `payload_artifact_id`), and envelope-level
`causal_refs.referenced_artifact_id`. Forward-compatible with future
event types that embed artifacts.

### (c) BOUNDARY_VIOLATION Rejection Reason Enum — CLOSED, 12 MEMBERS

Final enum:

```
SOURCE_UNREGISTERED
TARGET_UNREGISTERED
SOURCE_INACTIVE
TARGET_INACTIVE
CROSS_SESSION
MISSING_HANDSHAKE
BINDING_PAYLOAD
UNKNOWN_PAYLOAD
SELF_HANDOFF
INVALID_AUDITOR
DISALLOWED_ORIGINATOR_VALIDATOR
DISALLOWED_ORIGINATOR_HUMAN_PROXY
```

The initial proposal was 10 members. During implementation two additional
members were added to carry decisions (e) and (f) as first-class audit
categories rather than folding them into a generic reason + free-text
detail. This preserves the machine-verifiable audit property of the
closed enum.

**Governance rationale:** Invariant 4. A closed enum makes failure-mode
audit machine-verifiable. Free-text rejection reasons would force audit
tooling to parse prose, introducing interpretation ambiguity.

### (d) Handshake Revocation — DURABLE FOR SESSION, IMPLICIT INVALIDATION

Handshakes remain in effect for the lifetime of both endpoints' ACTIVE
status. No explicit BOUNDARY_HANDSHAKE_REVOKED event in Sprint-2. If
either endpoint transitions to SUSPENDED or REVOKED, the channel becomes
implicitly unusable: handoff-time checks reject with SOURCE_INACTIVE or
TARGET_INACTIVE.

**Governance rationale:** Invariant 3 and scope discipline. Explicit
revocation introduces a new event type, new API surface, new test matrix,
and a semantic question (does revocation retroactively invalidate prior
handoffs along the channel?) that belongs with Sprint-3 depth-enforcement
and trust-tier dynamics.

**Deferred to future sprint:** Explicit `BOUNDARY_HANDSHAKE_REVOKED` event
with forward-only semantics (prior handoffs remain valid ledger events
even after channel revocation).

### (e) VALIDATOR Handoff Semantics — ASYMMETRIC

VALIDATOR may be a handoff target from any agent_type. VALIDATOR may
originate handoffs ONLY to ORCHESTRATOR or HUMAN_PROXY. Origination to
SUB_AGENT or VALIDATOR targets produces
`DISALLOWED_ORIGINATOR_VALIDATOR`.

**Governance rationale:** Invariant 3. Validators exist to attest to
upstream work. Validator-to-sub_agent originations would create
validation-chaining patterns that obscure the attestation boundary.
Routing validator output up to the orchestrator or out to a human proxy
keeps attestation flow legible.

### (f) HUMAN_PROXY Handoff Semantics — STRICT UPSTREAM

HUMAN_PROXY may receive handoffs from any ACTIVE agent (HITL escalation
semantics). HUMAN_PROXY may originate handoffs ONLY to ORCHESTRATOR.
Origination to any other type produces
`DISALLOWED_ORIGINATOR_HUMAN_PROXY`.

**Governance rationale:** Invariants 1 and 2. A handoff FROM HUMAN_PROXY
to a SUB_AGENT or VALIDATOR would let a human delegate work to an AI
agent through the handoff mechanism. That is a Decision-gated action,
not a handoff. Permitting it would create a pathway to bypass
`delegation_blocked` enforcement (Sprint-3+ scope). Closed at the
handoff-emission boundary in Sprint-2 to prevent future weakening.

---

## 2. Invariant Traceability Matrix

| Artifact / Control                               | Inv 1 | Inv 2 | Inv 3 | Inv 4 |
| ------------------------------------------------ | ----- | ----- | ----- | ----- |
| AgentHandoff.non_authoritative_flag (const true) | X     |       |       |       |
| AgentHandoff factory rejects non-true flag       | X     |       |       |       |
| BINDING_PAYLOAD rejection                        | X     | X     |       |       |
| DISALLOWED_ORIGINATOR_HUMAN_PROXY                |       | X     |       |       |
| DISALLOWED_ORIGINATOR_VALIDATOR                  |       |       | X     |       |
| Source/Target registration check                 |       |       | X     | X     |
| Source/Target activity check                     |       |       | X     | X     |
| CROSS_SESSION rejection                          |       |       | X     | X     |
| Payload discoverability (union)                  |       |       | X     |       |
| BOUNDARY_HANDSHAKE before peer handoff           |       |       | X     |       |
| Handshake directionality (strict A→B)            |       |       | X     | X     |
| BOUNDARY_VIOLATION emit-before-raise             |       |       |       | X     |
| AGENT_HANDOFF in append-only hash chain          |       |       |       | X     |
| Pure-ledger channel lookup                       |       |       |       | X     |
| INVALID_AUDITOR API-boundary ledger event        | X     |       |       | X     |

---

## 3. Files Added

### Schemas
- `multiagent/ledger/hash_chain/event_schemas/v2/AGENT_HANDOFF.payload.schema.json`
- `multiagent/ledger/hash_chain/event_schemas/v2/BOUNDARY_HANDSHAKE.payload.schema.json`
- `multiagent/ledger/hash_chain/event_schemas/v2/BOUNDARY_VIOLATION.payload.schema.json`

### Runtime modules
- `multiagent/artifacts/AgentHandoff/__init__.py`
- `multiagent/orchestrator/boundary_enforcement/__init__.py`
- `multiagent/orchestrator/boundary_enforcement/handoff.py`
- `multiagent/orchestrator/boundary_enforcement/handshake.py`

### Tests
- `multiagent/tests/agent_boundary_tests/test_handoff.py` (9 tests)
- `multiagent/tests/agent_boundary_tests/test_handshake.py` (7 tests)
- `multiagent/tests/agent_boundary_tests/test_api_handoff.py` (8 tests)

---

## 4. Files Modified

- `multiagent/ledger/hash_chain/event_schemas/v2/LedgerEvent.envelope.schema.json`
  Extended `event_type` enum with AGENT_HANDOFF, BOUNDARY_HANDSHAKE,
  BOUNDARY_VIOLATION. No other envelope changes.
- `multiagent/ledger/hash_chain/events.py` — `EventType` Literal extended.
- `multiagent/exceptions.py` — Added `BoundaryViolationError`, `HandshakeError`.
- `multiagent/orchestrator/api.py` — Four new endpoints, exception translator
  extended, API-boundary INVALID_AUDITOR emit-before-raise helper, version
  string bumped to `v2-sprint-2`.
- `multiagent/tests/invariant_tests/test_authority.py` (+4 tests)
- `multiagent/tests/invariant_tests/test_evidence_first.py` (+5 tests)
- `multiagent/tests/invariant_tests/test_reconstructability.py` (+5 tests)
- `multiagent/README.md` — Event-type and endpoint tables updated.

No modifications to `/demo`, `/shared/artifact-contracts/v1/`, or
`/shared/artifact-contracts/v2/AgentHandoff.schema.json` (Sprint-0 locked).

---

## 5. Ledger Event Registry (v2, post-Sprint-2)

| Event Type                | Introduced | Actor         | Causal Refs Used                  |
| ------------------------- | ---------- | ------------- | --------------------------------- |
| AGENT_REGISTERED          | Sprint-1   | HUMAN         | referenced_artifact_id (agent_id) |
| AGENT_SUSPENDED           | Sprint-1   | HUMAN         | prior_event_id, referenced_event_id |
| AGENT_REVOKED             | Sprint-1   | HUMAN         | prior_event_id, referenced_event_id |
| UNREGISTERED_AGENT_OUTPUT | Sprint-1   | ORCHESTRATOR  | referenced_artifact_id            |
| AGENT_SESSION_REGISTRY    | Sprint-1   | HUMAN         | —                                 |
| AGENT_HANDOFF             | Sprint-2   | ORCHESTRATOR  | referenced_artifact_id (handoff_id) |
| BOUNDARY_HANDSHAKE        | Sprint-2   | ORCHESTRATOR  | —                                 |
| BOUNDARY_VIOLATION        | Sprint-2   | ORCHESTRATOR  | —                                 |

---

## 6. API Endpoint Registry (v2, post-Sprint-2)

All endpoints require `X-Auditor-Id` header (Invariant 1). Sprint-2 boundary
endpoints additionally emit BOUNDARY_VIOLATION with INVALID_AUDITOR on
pattern failure before returning 403.

| Method | Path                                    | Introduced |
| ------ | --------------------------------------- | ---------- |
| POST   | /agents                                 | Sprint-1   |
| GET    | /agents/{agent_id}                      | Sprint-1   |
| POST   | /agents/{agent_id}/suspend              | Sprint-1   |
| POST   | /agents/{agent_id}/revoke               | Sprint-1   |
| GET    | /sessions/{session_id}/registry         | Sprint-1   |
| POST   | /handshakes                             | Sprint-2   |
| GET    | /sessions/{session_id}/handshakes       | Sprint-2   |
| POST   | /handoffs                               | Sprint-2   |
| GET    | /handoffs/{handoff_id}                  | Sprint-2   |
| GET    | /sessions/{session_id}/handoffs         | Sprint-2   |

Exception-to-HTTP mapping:

| Exception                 | HTTP |
| ------------------------- | ---- |
| AuthorityViolationError   | 403  |
| UnregisteredAgentError    | 404  |
| AgentRegistrationError    | 409  |
| BoundaryViolationError    | 422  |
| HandshakeError            | 422  |
| ArtifactValidationError   | 422  |
| LedgerIntegrityError      | 500  |

---

## 7. Test Summary

| File                                             | Sprint-1 | Added | Total |
| ------------------------------------------------ | -------- | ----- | ----- |
| test_authority.py                                | 6        | +4    | 10    |
| test_evidence_first.py                           | 3        | +5    | 8     |
| test_non_bypass.py                               | 7        | 0     | 7     |
| test_reconstructability.py                       | 4        | +5    | 9     |
| test_registration.py                             | 11       | 0     | 11    |
| test_api.py                                      | 10       | 0     | 10    |
| test_handoff.py (new)                            | —        | +9    | 9     |
| test_handshake.py (new)                          | —        | +7    | 7     |
| test_api_handoff.py (new)                        | —        | +8    | 8     |
| **Total**                                        | **41**   | +38   | **79** |

Result: **78 passed, 1 skipped** (Sprint-3 reservation from Sprint-1).
Zero Sprint-1 regressions.

---

## 8. Deferred Items

Carried forward to future sprints:

- **DEPTH_LIMIT_REACHED event and structural depth ceiling** (Sprint-3)
- **Action runtime and delegation_blocked enforcement** (Sprint-3+)
- **Hypothesis runtime with source_agent_id provenance** (later)
- **BME attribution per agent and composite upstream scoring** (Sprint-4)
- **Explicit BOUNDARY_HANDSHAKE_REVOKED event** (revisit if dynamic trust
  adjustment becomes required; current implicit-via-status model suffices)
- **HITL-routing semantics for handoffs targeting HUMAN_PROXY** — Sprint-2
  treats these as ordinary handoffs; future sprint may mark them as
  `ROUTE_TO_HITL` for decision-console visibility.

---

## 9. Open Items from Sprint-1 Remaining Open

- Hypothesis `source_agent_id` gap (Hypothesis runtime not in Sprint-2
  scope per Section 6 of the Sprint-2 prompt).
- Sprint-1 skipped test (`test_non_bypass.py`) remains reserved for
  Sprint-3.
