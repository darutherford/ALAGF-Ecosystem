# ALAGF-Ecosystem Development Notes

**Purpose.** Engineering log capturing defects, adapter iterations,
diagnostic approaches, and process corrections encountered during sprint
execution. First-person register, technical detail.

**Audience.** Future sprint execution. The primary reader of these notes
is me, six months from now, trying to remember why a particular Sprint-N
implementation went three iterations before it shipped.

**Relationship to other documentation.**

- `/docs/development-notes/` (this directory): per-sprint engineering
  logs and the cross-sprint LESSONS.md aggregator.
- `/docs/lab-journal/`: scholarly narrative of design decisions and
  invariant enforcement. Third-person register.
- `/multiagent/docs/schema_versions/`: per-sprint changelogs with
  commit-level technical detail.

## Reading Order

1. [LESSONS.md](LESSONS.md) --- cross-sprint process corrections. Start
   here for new sprint planning. This file captures patterns that
   repeat across sprints and the specific process changes that prevent
   them.
2. Per-sprint notes in sprint order:
   - [Sprint-0: Scaffolding](sprint-00-scaffolding.md)
   - [Sprint-1: AgentIdentity lifecycle](sprint-01-agent-identity.md)
   - [Sprint-2: Boundary enforcement](sprint-02-boundary-enforcement.md)
   - [Sprint-3: Hypothesis runtime (integration-dense)](sprint-03-integration-notes.md)

## Defect Density by Sprint

| Sprint | Defects Surfaced | Defects Resolved Within Sprint | Latent Defects Surfaced in Later Sprints |
|---|---|---|---|
| 0 | 2 | 0 | 0 |
| 1 | 0 | 0 | 1 (surfaced Sprint-3) |
| 2 | 2 | 2 | 0 |
| 3 | 3 | 3 | --- |

**Observation.** Sprints that extend existing code generate more
integration defects than sprints that create net-new code. Sprint-3 is
the first sprint to extend a Sprint-0 shared contract and the first
sprint to integrate with Sprint-1/2 fixture conventions. Both
extension points produced defects (schema incompatibility, conftest
collision). See LESSONS.md for the process corrections derived from
this pattern.

## Defect Catalog

Cross-sprint defect index. Each defect has a stable identifier of the
form `SN.DM` where N is the sprint number and M is the defect number
within the sprint. Defects are listed in chronological order of
encounter, not chronological order of creation.

| ID | Description | Status | Notes |
|---|---|---|---|
| S0.D1 | Schema extraction scratch files pollute `/shared` | Resolved Sprint-1 | .gitignore additions |
| S0.D2 | `/demo/ledger/` runtime state untracked | Resolved Sprint-1 | Declared out-of-scope; intentionally untracked |
| S1.D1 | `get_agent_identity()` strips `_session_id` meta field silently | Latent; surfaced as S3.D3 | Undocumented implementation detail |
| S2.D1 | `EventType` Literal extension pattern (Enum vs. Literal) | Resolved Sprint-2 | Chose append-only Literal extension; Sprint-3 followed the pattern |
| S2.D2 | Rejection reason free-form strings drifted during implementation | Resolved Sprint-2 | Introduced closed-enum at design time; pattern now standard |
| S3.D1 | conftest replacement broke 41 Sprint-1/2 tests | Resolved Sprint-3 | Extension discipline, not replacement |
| S3.D2 | Hypothesis factory authored against hypothesized schema, not HEAD | Resolved Sprint-3 | Full factory rewrite against HEAD |
| S3.D3 | `FsAgentRegistry` adapter required three iterations | Resolved Sprint-3 | Caused by S1.D1 latent defect; diagnostic probe was inflection point |

## Ma

$content = @'
# Sprint-0: Scaffolding and Schema Initialization

**Sprint identifier:** ECOSYSTEM-SPRINT-0
**Close date:** 2026-04-21
**Close time (local):** 05:58 CDT
**Close commit:** `2bdfa42`
**Primary invariant:** Invariant 4 (Reconstructability) --- establishing the
structural preconditions under which later sprints can enforce the remaining
three invariants.

## Purpose

ECOSYSTEM-SPRINT-0 established the monorepo structure required to host two
distinct development tracks within a single research artifact: a frozen v1
dissertation defense prototype (`/demo`) and an active multi-agent extension
track (`/multiagent`). The sprint produced no runtime behavior. Its
contribution was the governance scaffold that subsequent sprints build on.

## Strategic Context

The Applied Lifecycle AI Governance Framework (ALAGF; Rutherford, 2025) was
originally developed as a single-agent governance architecture, demonstrated
through the `alagf-demo` prototype completed in seven development sprints.
Extending ALAGF to govern multi-agent AI topologies required a structural
decision: whether to extend the existing demo codebase in place, or to
preserve v1 as a frozen defense artifact and establish a parallel v2 track.

The second option was selected. The research narrative requires that ALAGF v1
remain the defensible, complete prototype for dissertation defense, while the
multi-agent extension operates as its operationalized future-work track. This
preservation matters for committee review: modifying the demo in place would
blur the boundary between defended work and extension work, weakening the
academic position.

## Scope and Deliverables

Sprint-0 produced four categories of artifact:

**Monorepo scaffold.** The `/demo`, `/multiagent`, `/shared`, and `/docs`
directory tree described in Section 7 of the project instructions. Each
directory received a `README.md` declaring its status (frozen, active, or
shared).

**Canonical artifact contracts (v1 locked).** JSON Schema formalizations of
the six canonical artifacts produced by the demo prototype: AuditSession,
ConstraintSet, Observation, Hypothesis, Decision, and Action. These were
extracted post-hoc from the demo's dataclass implementations and placed under
`/shared/artifact-contracts/v1/`. This directory was declared locked;
modification requires the formal amendment process documented in
`/demo/README.md`.

**Canonical artifact contracts (v2 seed).** Empty placeholder schemas for the
v2 artifacts at `/shared/artifact-contracts/v2/`. These would be populated in
subsequent sprints: AgentIdentity and AgentHandoff in Sprint-1, extensions to
Observation/Hypothesis/Decision/Action in their respective sprint additions.

**BME metric suite and standards reference material.** The composite BME-CI
formula and tier thresholds (Rutherford, 2024) were placed at
`/shared/bme-metric-suite/` as the canonical reference. Standards clause
mappings for ISO/IEC 42001:2023, NIST AI RMF 1.0 (National Institute of
Standards and Technology [NIST], 2023), and EU AI Act Articles 9, 10, 11, 13,
17, and 29 were placed at `/shared/standards-refs/`.

## Design Decisions

Two decisions made during Sprint-0 shape every subsequent sprint.

**Decision S0.1 --- Post-hoc v1 schema extraction.** The demo prototype
implemented v1 artifacts as Python dataclasses without JSON Schema
formalization. Formalizing them post-hoc was optional; the demo would have
continued to function without it. The decision was made to extract formal
schemas because Invariant 4 (Reconstructability) requires that the ledger be
self-describing, and the v2 multi-agent extension would share the v1 contract
as a parent. Without formal v1 schemas, v2 artifacts would inherit from
implementation detail rather than from a versioned contract. This decision is
documented in `/docs/release-notes/sprint-0-reconciliation.md`.

**Decision S0.2 --- Shared-schema versioning policy.** All shared schemas are
versioned. v1 schemas are locked; v2 schemas are the active extension point.
Any change to a shared schema requires a changelog entry at
`/shared/artifact-contracts/CHANGELOG.md`. This policy was made absolute
because the alternative --- allowing silent schema evolution --- would violate
Invariant 4 on any cross-version artifact inspection.

## Invariant Enforcement Status at Sprint Close

Sprint-0 produced no runtime enforcement. Its invariant contribution is
preparatory:

- **Invariant 1 (Authority):** No enforcement yet. The scaffold establishes
  where AgentIdentity will live so that the `non_authoritative_flag`
  hard-coding can be implemented in Sprint-1.
- **Invariant 2 (Non-Bypass):** No enforcement yet. `delegation_blocked` on
  Action and `max_synthesis_depth` on AgentIdentity are declared as v2 schema
  fields awaiting implementation.
- **Invariant 3 (Evidence-First):** No enforcement yet. The v1
  Observation/Decision/Action provenance chain is preserved as locked v1
  contracts.
- **Invariant 4 (Reconstructability):** Preparatory enforcement via the
  shared-schema versioning policy and the scaffold's self-describing
  directory conventions.

## Outstanding Items at Sprint Close

Three items were recorded as sprint-transition-blocking or
sprint-transition-noted:

1. **Hypothesis v2 missing source_agent_id field.** Identified during
   Sprint-0 schema extraction but declared out-of-scope for Sprint-0.
   Recorded in the Sprint-0 reconciliation note as blocking for Sprint-4
   (BME attribution) but non-blocking for Sprint-1 through Sprint-3. Resolved
   during Sprint-3 via a different mechanism: the
   `composite_upstream_bme_score` placeholder approach with payload marker.
2. **Demo ledger state untracked.** The `/demo/ledger/` directory contained
   test-generated runtime state not suitable for version control. Declared
   out-of-scope for Sprint-1 and deferred indefinitely.
3. **Untracked scratch files in `/shared/artifact-contracts/`.** Office lock
   files and diagnostic dumps generated during schema extraction. Remediated
   in Sprint-1 via `.gitignore` additions.

## Novel Contribution Indicators

Sprint-0 produced no novel methodological contribution. The scaffold is
standards-aligned engineering. Its significance is structural: it makes the
novel contributions of later sprints --- chain-minimum ceiling attribution
(Sprint-3), path-scoped freeze derivation (Sprint-3), cross-session agent
reputation tracking (future sprint) --- architecturally possible within a
defensible research artifact.

## References

International Organization for Standardization. (2023). *Information
technology --- Artificial intelligence --- Management system* (ISO/IEC 42001:2023).

National Institute of Standards and Technology. (2023). *Artificial
Intelligence Risk Management Framework (AI RMF 1.0)* (NIST AI 100-1).
U.S. Department of Commerce. https://doi.org/10.6028/NIST.AI.100-1

Rutherford, D. (2024). *The BME metric suite: Behavioral measurement of
entropy in agentic AI systems* [Unpublished manuscript]. University of
Arkansas at Little Rock.

Rutherford, D. (2025). *The Applied Lifecycle AI Governance Framework*
[Unpublished manuscript]. University of Arkansas at Little Rock.

