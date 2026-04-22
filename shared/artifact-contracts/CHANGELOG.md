# Artifact Contracts Changelog

All notable changes to canonical ALAGF artifact schemas are documented here.
This changelog is a first-class governance artifact. Schema evolution requires
an entry with governance rationale traceable to one of the four ALAGF invariants
or a named BME metric.

---

## [v2.0.0-sprint3] — 2026-04-22

### ECOSYSTEM-SPRINT-3 — Hypothesis Runtime and Depth-Ceiling Enforcement

**Track:** `/multiagent` (Multi-Agent Governance Extension)
**Auditor:** AUDITOR_DALE_001
**Primary invariant:** Invariant 2 (Non-Bypass) — structural enforcement

### Schema changes

**No modifications to v2 canonical artifact schemas in Sprint-3.**

`shared/artifact-contracts/v2/Hypothesis.schema.json` was finalized in
Sprint-0 with all fields required by Sprint-3 already in place:
`synthesis_depth`, `upstream_hypothesis_refs`, `composite_upstream_bme_score`,
`observation_refs` (minItems: 1), `non_authoritative_flag` (const: true).
Sprint-3 provides the runtime that enforces these schema constraints at
emission time rather than altering the contract itself.

**Rationale for no-amendment:** The Sprint-0 contract is complete for
multi-agent Hypothesis emission. The only field Sprint-3 initially wanted
to modify — `composite_upstream_bme_score` nullability — was resolved via
a ledger-payload marker (`bme_score_source`: `placeholder` or `computed`)
on the `HYPOTHESIS_REGISTERED` event payload rather than a schema change.
This preserves the locked contract while allowing Sprint-3 emission with
caller-supplied placeholder scores that Sprint-4 will supersede.

### Sprint-3 ratified design decisions (reference)

Full rationale lives at
`multiagent/docs/schema_versions/sprint-3-changelog.md`. Summary:

| ID | Decision | Governance |
|---|---|---|
| (a) | Chain-minimum ceiling attribution | Closes relay-laundering vector; Invariant 2 architectural |
| (b) | Path-scoped freeze | Proportional rejection; ledger-derived; Invariant 2 + 4 |
| (c) | Observations = depth 0 floor | Invariant 3 grounding |
| (d) | New `ScopeViolationError` class | Audit taxonomy differentiation |
| (e-revised) | `composite_upstream_bme_score` placeholder with payload marker | Sprint-0 schema locked; marker preserves traceability |
| (f) | Handoff ≠ synthesis hop | Orchestration vs. inference separation |
| (g-i) | `observation_refs` minItems: 1 on every Hypothesis regardless of depth | Every inferential artifact traces to evidence |

### New ledger event payload schemas (not canonical artifacts)

Two net-new event payload schemas under
`multiagent/ledger/hash_chain/event_schemas/v2/`:

- `HYPOTHESIS_REGISTERED.payload.schema.json` — wraps the full Hypothesis
  artifact plus `governing_ceiling`, `ceiling_attribution`, and
  `bme_score_source`.
- `DEPTH_LIMIT_REACHED.payload.schema.json` — carries
  `attempted_source_agent_id`, `attempted_upstream_hypothesis_refs`,
  `computed_depth`, `governing_ceiling`, `ceiling_attribution`,
  `frozen_provenance_ancestors`, and `rejection_reason`
  (closed enum: `CHAIN_MINIMUM_CEILING_EXCEEDED`).

These are event schemas, not canonical lifecycle artifacts. They live in
the `/multiagent` track and do not affect `/shared/artifact-contracts/v2/`.

### Envelope schema extension

`multiagent/ledger/hash_chain/event_schemas/v2/LedgerEvent.envelope.schema.json`
is modified in exactly one place: the `event_type` enum is extended with
two members: `HYPOTHESIS_REGISTERED` and `DEPTH_LIMIT_REACHED`. All other
envelope fields are preserved verbatim (Precondition 7).

### Open items for Sprint-4

- `ScopeViolationError` ledger event treatment (new `SCOPE_VIOLATION`
  event type vs. extending `UNREGISTERED_AGENT_OUTPUT`).
- `FrozenPathError` ledger event treatment (new `FROZEN_PATH_REJECTED`
  event type vs. reliance on prior `DEPTH_LIMIT_REACHED`).
- BME attribution wire-up: populate `composite_upstream_bme_score` with
  computed floats; set `bme_score_source: "computed"` on event payload.

---

## [v2.0.0-sprint0] — 2026-04-21

### ECOSYSTEM-SPRINT-0 — Scaffolding and Schema Initialization

**Track:** `/multiagent` (Multi-Agent Governance Extension)
**Auditor:** AUDITOR_DALE_001
**Commit reference:** Pending initial push to `DARutherford/ALAGF-Ecosystem`

### v1 Formalization (Path B)

v1 canonical artifact contracts were formalized as JSON Schema during Sprint-0.
Prior to this sprint, v1 contracts existed only as Python dataclasses in
`alagf-demo/artifacts/__init__.py`. No portable contract existed. Per Path B
selected by the auditor, this changelog entry explicitly records the v1-to-
portable-contract transition rather than asserting a "verbatim copy" that did
not exist.

**Provenance:** All v1 schemas extracted from `alagf-demo/artifacts/__init__.py`
as of Sprint-0 session. Runtime invariants hard-coded in the Python source
(frozen dataclasses, `init=False` flags, `__post_init__` validation) are
preserved in JSON Schema through `const`, `enum`, `pattern`, and `minLength`
constraints.

**v1 canonical lifecycle artifacts** (`/shared/artifact-contracts/v1/`):

| Schema | Authority Level | Key Invariant Enforcement |
|---|---|---|
| `AuditSession.schema.json` | orchestration | `auditor_id` required (human provenance anchor) |
| `ConstraintSet.schema.json` | orchestration | Policy references carried forward for Invariant 3 |
| `Observation.schema.json` | observational | No conclusion-producing fields |
| `Hypothesis.schema.json` | non_binding | `non_authoritative_flag` const `true`; `observation_refs` `minItems: 1` |
| `Decision.schema.json` | binding | `auditor_id` required; `observation_refs` `minItems: 1` |
| `Action.schema.json` | binding | `decision_ref` pattern `^DEC_...` rejects `HYP_` prefix (EB-1); `policy_reference` `minLength: 1` |

**v1 orchestration-support contracts** (`/shared/orchestration-contracts/v1/`):

Per Path C, three artifacts present in `alagf-demo/artifacts/__init__.py` are
classified as orchestration-support rather than canonical lifecycle. They are
versioned in a parallel namespace to preserve the canonical-six framing of the
project instructions while closing the reconstructability gap for ledger
reconstruction.

| Schema | Authority Level | Rationale |
|---|---|---|
| `EnvelopeValidated.schema.json` | orchestration | Boundary handshake event; not part of lifecycle chain |
| `StressObservation.schema.json` | observational | M2 stress engine output; feeds Observation pipeline |
| `MetricObservation.schema.json` | observational | M3 telemetry output; constrained to CANONICAL_METRICS and VALID_SPC_FLAGS |

**v1 lock status:** All v1 schemas above are **LOCKED** as of this changelog
entry. Modification is prohibited by Instruction Discipline Rule 3. Any
corrective change to v1 requires a formal amendment process and a new
changelog entry documenting the remediation.

### v2 Initialization

**v2 canonical lifecycle artifacts** (`/shared/artifact-contracts/v2/`):

| Schema | Status | Net-New Fields |
|---|---|---|
| `AgentIdentity.schema.json` | Full contract | All fields net-new. Canonical artifact. No v1 precursor. |
| `AgentHandoff.schema.json` | Full contract | All fields net-new. Ledger event type for inter-agent boundary crossings. |
| `Observation.schema.json` | Extended from v1 | `source_agent_id`, `input_provenance_chain` |
| `Hypothesis.schema.json` | Extended from v1 | `synthesis_depth`, `upstream_hypothesis_refs`, `composite_upstream_bme_score` |
| `Decision.schema.json` | Extended from v1 | `agent_context_reviewed`, `synthesis_depth_at_decision` |
| `Action.schema.json` | Extended from v1 | `source_agent_id`, `delegation_blocked` |

### Governance Rationale for v2 Net-New Fields

Every net-new field is traceable to one of the four ALAGF invariants or a
named BME metric per Behavioral Rule 7.

| Field | Invariant / Metric | Enforcement Mechanism |
|---|---|---|
| `AgentIdentity.non_authoritative_flag` | Invariant 1 (Authority) | `const: true` at schema level |
| `AgentIdentity.max_synthesis_depth` | Invariant 2 (Non-Bypass) | Orchestrator compares `Hypothesis.synthesis_depth` against ceiling; emits `DEPTH_LIMIT_REACHED` |
| `AgentIdentity.registered_by` | Invariant 1 (Authority) | Human provenance anchor for agent registry |
| `AgentHandoff.non_authoritative_flag` | Invariant 1 (Authority) | `const: true`; handoff does not confer authority |
| `Observation.source_agent_id` | Invariant 3 (Evidence-First) | Required; references `AgentIdentity.agent_id` |
| `Observation.input_provenance_chain` | Invariants 3, 4 | Complete chain required before Decision presentation |
| `Hypothesis.synthesis_depth` | Invariant 2 (Non-Bypass) | Counter enforced against `max_synthesis_depth` ceiling |
| `Hypothesis.upstream_hypothesis_refs` | Invariant 4 (Reconstructability) | Ledger-alone chain traversal |
| `Hypothesis.composite_upstream_bme_score` | BME Metric Suite (BAR-A, ECPI-A, IQD-A) | Weighted aggregate per `composite_bme_ci.py` |
| `Decision.agent_context_reviewed` | Invariant 3 (Evidence-First) | `const: true` affirmation required for validation |
| `Decision.synthesis_depth_at_decision` | Invariant 4 (Reconstructability) | Captures depth state at moment of binding |
| `Action.source_agent_id` | Invariant 2 (Non-Bypass) | Paired with `delegation_blocked` check |
| `Action.delegation_blocked` | Invariant 2 (Non-Bypass) | `const: true`; orchestrator rejects if `source_agent_id` non-null AND `decision_ref` missing |

### Sprint-0 Scope Adjustment (Path B)

Original DoD stated: "populated with locked v1 schemas (copied verbatim from
alagf-demo — no modifications)."

Adjusted DoD: "v1 JSON Schemas formalized from canonical Python source at
`alagf-demo/artifacts/__init__.py` and frozen as the v1 portable contract."

Original DoD stated: "/shared/artifact-contracts/v2/ scaffolded with stub
files for all seven v2 contracts."

Adjusted DoD: "/shared/artifact-contracts/v2/ contains full contracts for
AgentIdentity and AgentHandoff, and full v2 extension schemas for
Observation, Hypothesis, Decision, and Action. All schemas validate against
JSON Schema Draft 2020-12."

Net scope addition: `/shared/orchestration-contracts/v1/` parallel namespace
with three orchestration-support schemas (Path C selection).

---

## Future Entries

Entries are added in reverse chronological order. Required fields per entry:

- Sprint identifier and date
- Track (`/demo` or `/multiagent`)
- Affected schemas and version
- Net-new or modified fields with governance rationale
- Invariant or BME metric traceability
- Lock status change (if any)
