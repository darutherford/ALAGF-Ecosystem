# ALAGF Multi-Agent Governance Extension

**STATUS: ACTIVE DEVELOPMENT**

This directory is the active development track for the multi-agent extension
of the Applied Lifecycle AI Governance Framework. All new implementation work
for the multi-agent topology occurs here.

## Track Scope

Extends ALAGF v1 artifact contracts and ledger schema to govern multi-agent
AI topologies. Introduces:

- `AgentIdentity` — canonical artifact. Every participating agent must be
  registered before any output is accepted into the ledger.
- `AgentHandoff` — ledger event type for inter-agent boundary crossings.
- Extensions to Observation, Hypothesis, Decision, and Action v1 contracts
  for multi-agent provenance tracking.
- Ledger event types: `AGENT_REGISTERED`, `AGENT_HANDOFF`,
  `AGENT_SESSION_REGISTRY`, `DEPTH_LIMIT_REACHED`,
  `UNREGISTERED_AGENT_OUTPUT`, `AGENT_SUSPENDED`, `AGENT_REVOKED`.

## Core Governance Principle

**Agent boundaries are governance boundaries.** Every crossing of an agent
boundary is an auditable ledger event, not an implementation detail.

## Invariant Enforcement in Multi-Agent Context

| Invariant | Multi-Agent Extension |
|---|---|
| **1. Authority** | `non_authoritative_flag` on AgentIdentity, AgentHandoff, and Hypothesis is `const: true`. No agent scope permits binding outputs. |
| **2. Non-Bypass** | `delegation_blocked` on Action; `max_synthesis_depth` on AgentIdentity. Orchestrator rejects violations — does not flag. |
| **3. Evidence-First** | `input_provenance_chain` on Observation; `agent_context_reviewed` on Decision; human affirmation required before binding. |
| **4. Reconstructability** | Every agent-boundary crossing emits an `AGENT_HANDOFF` ledger event. Session is reconstructible from ledger alone. |

## Directory Layout

```
multiagent/
├── ledger/
│   ├── append_only_store/          append-only write, no update/delete
│   ├── hash_chain/                 SHA-256 chained event store
│   └── agent_registry/             AgentIdentity artifact store
├── artifacts/
│   ├── AgentIdentity/              canonical — first priority
│   ├── AgentHandoff/               inter-agent boundary event
│   ├── AuditSession/
│   ├── ConstraintSet/
│   ├── Observation/
│   ├── Hypothesis/
│   ├── Decision/
│   └── Action/
├── orchestrator/
│   ├── boundary_enforcement/       depth limit, non-bypass checks
│   └── agent_lifecycle/            registration, suspension, revocation
├── ui/
│   └── screens/
├── simulators/
│   └── multi_agent_scenarios/
├── tests/
│   ├── invariant_tests/            four-invariant acceptance suite
│   └── agent_boundary_tests/       net-new test class for this track
└── docs/
    ├── schema_versions/            artifact contract changelogs
    └── sprint_prompts/             session initialization prompts
```

## Sprint Plan

| Sprint | Objective |
|---|---|
| ECOSYSTEM-SPRINT-0 | Scaffolding and schema initialization (this sprint) |
| ECOSYSTEM-SPRINT-1 | AgentIdentity implementation and ledger registration enforcement |
| ECOSYSTEM-SPRINT-2 | Agent-boundary ledger events and handoff logic |
| ECOSYSTEM-SPRINT-3 | Multi-agent orchestrator and depth enforcement |
| ECOSYSTEM-SPRINT-4 | BME attribution per agent + composite upstream score computation |
| ECOSYSTEM-SPRINT-5 | Human Decision Console — multi-agent extension |
| ECOSYSTEM-SPRINT-6 | Evidence pack export — agent-boundary aware |

Each sprint has explicit invariant acceptance tests. A sprint is not done
until all four invariants pass the acceptance suite.

## Schema Versioning

| Namespace | Location | Status |
|---|---|---|
| Canonical v1 | `/shared/artifact-contracts/v1/` | LOCKED |
| Canonical v2 | `/shared/artifact-contracts/v2/` | ACTIVE |
| Orchestration v1 | `/shared/orchestration-contracts/v1/` | LOCKED |

Any schema evolution requires a `/shared/artifact-contracts/CHANGELOG.md`
entry with governance rationale traceable to an invariant or BME metric.

## Dissertation-Level Contribution Gaps

Identified for future sprint scoping:

- **Cross-session agent reputation tracking** via persisted AgentIdentity
  contracts. Not addressed by current ISO/IEC 42001, NIST AI RMF, or EU AI
  Act standards. Novel contribution candidate.
