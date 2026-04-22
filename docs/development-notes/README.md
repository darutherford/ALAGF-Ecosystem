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

## Maintenance

One Development Notes entry per sprint, authored at sprint close
alongside the Lab Journal entry. LESSONS.md is updated whenever a
process correction is ratified --- typically at sprint close but
occasionally mid-sprint if a pattern is recognized and acted on
immediately.

