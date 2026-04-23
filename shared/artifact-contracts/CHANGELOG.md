# Artifact Contracts Changelog

All notable changes to canonical ALAGF artifact schemas are documented here.
This changelog is a first-class governance artifact. Schema evolution requires
an entry with governance rationale traceable to one of the four ALAGF invariants
or a named BME metric.

---

## [v2.0.1-sprint0-remediation] — Sprint-0 Post-Corpus-Review Remediation

**Track:** `/multiagent` (Multi-Agent Governance Extension)
**Auditor:** AUDITOR_DALE_001
**Commit reference:** Pending; remediation commit message:
`ECOSYSTEM-SPRINT-0-REMEDIATION: Nomenclature correction and BAR disambiguation`

### Background

Sprint-0 deliverables were produced before the ecosystem's full research corpus
was reviewed. Post-corpus review revealed three substantive nomenclature
errors in the committed Sprint-0 artifacts that require correction before
Sprint-1 implementation begins. This changelog entry documents the remediation.

### Correction 1 — ALAGF Canonical Expansion

**Incorrect (Sprint-0):** "Applied Lifecycle AI Governance Framework"

**Canonical:** "Adaptive Lifecycle Agentic Governance Framework"

**Source:** Rutherford (2026), *Behavioral Assurance*, Preface and Acronym
glossary; BAAGF specification document; canonical treatise.

**Files updated:**
- `README.md` (ecosystem root)
- `shared/artifact-contracts/CHANGELOG.md` (this file)
- `shared/artifact-contracts/v2/*.schema.json` (`$comment` fields referencing
  ALAGF expansion)
- `shared/standards-refs/*.md` (ISO_42001, NIST_RMF, EU_AI_Act clause maps)

No schema structural changes. Only `$comment` textual updates where ALAGF was
expanded inline.

### Correction 2 — ALAGF Tripartite Architecture

**Incorrect framing (Sprint-0):** ALAGF treated as a monolithic framework.

**Canonical framing:** ALAGF is a governance tripartite architecture
comprising three functionally distinct, informationally coupled subsystems:

- **BAAGF** (Behavioral Assurance and Agentic Governance Framework) —
  architectural conscience; owns BME Metric Suite definitions and calibration
  authority; issues binding governance directives.
- **SymPrompt+** — operational voice; translates governance directives into
  prompt-level behavioral modulations; maintains intervention version
  registry.
- **MIDCOT** (Multi-Dataset IQ Drift and Cost Optimization Training) —
  performance memory; ingests behavioral metric data; maintains SPC control
  charts; detects drift signals.

The BME Metric Suite operates as the shared diagnostic layer across all three
subsystems, owned by BAAGF.

**Files updated:**
- `README.md` (new "ALAGF Governance Tripartite" section)
- `multiagent/README.md` (contextualizes the multi-agent extension within
  the tripartite)

No schema changes. The multi-agent extension operates within this tripartite
architecture; the v2 schemas remain valid as designed.

### Correction 3 — BAR Disambiguation

**Problem:** The ALAGF research corpus contains two distinct authoritative
metrics sharing the BAR acronym:

1. **BAR-BAR** = Behavioral Assurance Rating (BME Suite control limit
   analogue; replaces `x̄ ± 3σ`). Source: Rutherford (2026), *Behavioral
   Assurance*, Appendix C.
2. **BAR-NOBE** = Bias Amplification Rate (per-turn bias trajectory metric;
   `|BMS(turn_N)| / |BMS(turn_1)|`). Source: Rutherford and Wu (2026), NOBE/BAR
   Whitepaper, PT-2026-007.

**Original Sprint-0 project instructions:** Listed BAR as "Bias Amplification
Rate" in the BME Metric Suite description. This conflated the two metrics.

**Canonical disambiguation established:** The multi-agent extension metric
**BAR-A** is an **Agentic Behavioral Assurance Rating** (extension of BAR-BAR
to agent-scoped control limits). It is NOT an agent-scoped Bias Amplification
Rate.

**Governance rationale:** The multi-agent extension's theory centers on agent
boundaries as SPC process boundaries. BAR-BAR, as the SPC control-limit
metric, is the natural construct to extend. Conflating it with BAR-NOBE would
produce silent implementation errors in Sprint-4 (BME Attribution Per Agent).

**Files added:**
- `docs/nomenclature/BAR_disambiguation.md` (canonical disambiguation
  document; required reading before Sprint-4)

**Files updated:**
- `README.md` (BME Metric Suite section with explicit BAR disambiguation)
- `shared/artifact-contracts/v2/Hypothesis.schema.json` (`$comment` on
  `composite_upstream_bme_score` clarifies that upstream aggregation is of
  CBMES values, with BAR-BAR as a component metric)

### Lock Status

- v1 canonical lifecycle schemas: **remain LOCKED**. No structural changes.
  Only `$comment` field textual updates. Treated as metadata remediation,
  not schema evolution.
- v1 orchestration-support schemas: **remain LOCKED**. No changes.
- v2 canonical schemas: **remain ACTIVE**. No structural changes. Only
  `$comment` field textual updates where ALAGF expansion or BME metric
  terminology appeared.

**Reviewer note:** This remediation does NOT constitute schema evolution. It
is a metadata-layer correction. Any consumer that validates artifacts
against the v1 or v2 schemas will produce identical validation results
before and after this remediation.

---

## [v2.0.0-sprint0] — 2026-04-21

### ECOSYSTEM-SPRINT-0 — Scaffolding and Schema Initialization

**Track:** `/multiagent` (Multi-Agent Governance Extension)
**Auditor:** AUDITOR_DALE_001
**Commit reference:** `2bdfa42` on origin/main

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
preserved in JSON Schema through `const`, `enum`, `pattern`, `minItems`, and
`minLength` constraints.

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
versioned in a parallel namespace to preserve the canonical-six framing while
closing the reconstructability gap.

| Schema | Authority Level | Rationale |
|---|---|---|
| `EnvelopeValidated.schema.json` | orchestration | Boundary handshake event; not part of lifecycle chain |
| `StressObservation.schema.json` | observational | M2 stress engine output; feeds Observation pipeline |
| `MetricObservation.schema.json` | observational | M3 telemetry output; constrained to CANONICAL_METRICS and VALID_SPC_FLAGS |

**v1 lock status:** All v1 schemas above are **LOCKED** as of Sprint-0.
Modification prohibited by Instruction Discipline Rule 3.

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
named BME metric.

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
| `Hypothesis.composite_upstream_bme_score` | CBMES (BME Metric Suite composite) | Weighted aggregate per BAAGF composite formula. BAR-A (Behavioral Assurance Rating agentic extension) is one of the component metrics. See `/docs/nomenclature/BAR_disambiguation.md`. |
| `Decision.agent_context_reviewed` | Invariant 3 (Evidence-First) | `const: true` affirmation required for validation |
| `Decision.synthesis_depth_at_decision` | Invariant 4 (Reconstructability) | Captures depth state at moment of binding |
| `Action.source_agent_id` | Invariant 2 (Non-Bypass) | Paired with `delegation_blocked` check |
| `Action.delegation_blocked` | Invariant 2 (Non-Bypass) | `const: true`; orchestrator rejects if `source_agent_id` non-null AND `decision_ref` missing |

---

## Future Entries

Entries are added in reverse chronological order. Required fields per entry:

- Sprint identifier and date
- Track (`/demo` or `/multiagent`)
- Affected schemas and version
- Net-new or modified fields with governance rationale
- Invariant or BME metric traceability
- Lock status change (if any)
