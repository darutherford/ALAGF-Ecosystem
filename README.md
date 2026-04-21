# ALAGF-Ecosystem

Applied Lifecycle AI Governance Framework — Ecosystem Monorepo

**Owner:** Dale Rutherford, PhD Candidate, University of Arkansas at Little Rock
**Domain:** Agentic AI Governance | Multi-Agent Architecture Extension
**Auditor Identity:** AUDITOR_DALE_001

---

## Ecosystem Structure

This repository contains two parallel research tracks that share canonical
artifact schemas and BME metric modules through `/shared`.

### `/demo` — ALAGF Audit Demonstration Prototype (FROZEN)

The v1 defense artifact. Complete through seven sprints with a full passing
test suite. Preserved as-is for dissertation defense. **Read-only.** Not
modified, extended, or used as a test target in the multi-agent track.

### `/multiagent` — Multi-Agent Governance Extension (ACTIVE)

Extends ALAGF artifact contracts and ledger schema to govern multi-agent AI
topologies. Introduces `AgentIdentity` as a canonical artifact, ledger event
types for agent-boundary crossings, and structural enforcement of all four
ALAGF invariants across multi-agent sessions.

### `/shared` — Canonical Schemas and Metric Modules

Single source of truth for artifact contracts and BME metric computation.
Schemas are versioned: v1 is locked; v2 is active for the multi-agent track.
Changes to shared schemas require explicit changelog entries at
`/shared/artifact-contracts/CHANGELOG.md`.

### `/docs` — Ecosystem Documentation

Dissertation artifacts, release notes, architecture specifications.

---

## Non-Negotiable Governance Invariants

All code, schemas, ledger logic, and UI components produced in this repository
enforce four invariants architecturally, not through documentation:

1. **Authority** — Only human Decisions and deterministic controller rules
   produce binding outcomes. AI outputs are always non-binding.
2. **Non-Bypass** — No Action may execute without a valid Decision reference.
   `delegation_blocked` enforces this at the Action contract level.
3. **Evidence-First** — Every binding outcome traces to Observation + Decision
   + Policy. In multi-agent topologies, the `input_provenance_chain` must be
   complete before Decision presentation.
4. **Reconstructability** — The ledger alone enables full causal reconstruction
   of every session event, including all agent-boundary crossings.

Violation of any invariant is a hard stop. No workarounds.

---

## Standards Alignment

- ISO/IEC 42001 — AI Management System Standard
- NIST AI RMF — Govern / Map / Measure / Manage functions
- EU AI Act — Articles 9, 10, 11, 13, 17, 29

Clause mappings: `/shared/standards-refs/`

---

## Core Frameworks

| Framework | Scope |
|---|---|
| **ALAGF** | Lifecycle governance architecture with four invariants |
| **BME Metric Suite** | BAR, ECPI, IQD, PTDI, AHRS + BME-CI composite |
| **SymPrompt+** | Structured prompt governance schema |
| **MIDCOT** | Multi-Dataset IQ Drift and Cost-Optimized Training |

### Multi-Agent BME Extensions (v2)

- **BAR-A** — Agentic Bias Amplification Rate
- **ECPI-A** — Agentic Echo Chamber Propagation Index
- **IQD-A** — Recursive Information Quality Decay

---

## Repository Layout

```
alagf-ecosystem/
├── shared/
│   ├── artifact-contracts/
│   │   ├── v1/                         LOCKED
│   │   ├── v2/                         ACTIVE
│   │   └── CHANGELOG.md
│   ├── orchestration-contracts/
│   │   └── v1/                         LOCKED
│   ├── bme-metric-suite/
│   └── standards-refs/
├── demo/                               FROZEN — v1 defense artifact
├── multiagent/                         ACTIVE development track
└── docs/
```

---

## Current Sprint

**ECOSYSTEM-SPRINT-0** — Scaffolding and Schema Initialization

See `/multiagent/docs/sprint_prompts/` for sprint initialization prompts and
Definition of Done acceptance criteria.
