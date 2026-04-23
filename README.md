# ALAGF-Ecosystem

**Adaptive Lifecycle Agentic Governance Framework** — Ecosystem Monorepo

**Owner:** Dale Rutherford, PhD Candidate, University of Arkansas at Little Rock
**Domain:** Agentic AI Governance | Multi-Agent Architecture Extension
**Auditor Identity:** AUDITOR_DALE_001

---

## Ecosystem Structure

This repository contains two parallel research tracks that share canonical
artifact schemas and BME metric modules through a versioned `/shared` namespace.

### `/demo` — ALAGF Audit Demonstration Prototype (FROZEN)

The v1 defense artifact. Complete through seven sprints with a full passing
test suite. Preserved as-is for dissertation defense. **Read-only.** Not
modified, extended, or used as a test target in the multi-agent track.

### `/multiagent` — Multi-Agent Governance Extension (ACTIVE)

Extends the ALAGF tripartite architecture to govern multi-agent AI topologies.
Introduces `AgentIdentity` as a canonical artifact, ledger event types for
agent-boundary crossings, and structural enforcement of the four ALAGF
invariants across multi-agent sessions.

### `/shared` — Canonical Schemas and Metric Modules

Single source of truth for artifact contracts and BME metric computation.
Schemas are versioned: v1 is locked; v2 is active for the multi-agent track.
Changes to shared schemas require explicit changelog entries at
`/shared/artifact-contracts/CHANGELOG.md`.

### `/docs` — Ecosystem Documentation

Dissertation artifacts, release notes, architecture specifications.

---

## The ALAGF Governance Tripartite

ALAGF is not a monolithic framework. It is a tripartite architecture of three
functionally distinct, informationally coupled subsystems:

| Subsystem | Role | Function |
|---|---|---|
| **BAAGF** (Behavioral Assurance and Agentic Governance Framework) | Architectural Conscience | Defines behavioral specifications, manages the escalation model, owns the BME Metric Suite definitions and calibration authority, issues binding governance directives |
| **SymPrompt+** | Operational Voice | Translates governance directives into prompt-level behavioral modulations, maintains the intervention version registry, executes entropy-calibrated targeting |
| **MIDCOT** (Multi-Dataset IQ Drift and Cost Optimization Training) | Performance Memory | Ingests behavioral metric data, maintains running SPC control charts, detects drift signals, triggers escalation events |

The BME Metric Suite operates as the shared diagnostic layer across all three
subsystems, owned by BAAGF to prevent operational subsystems from adjusting
the measurement system to improve their own metrics.

---

## Non-Negotiable Governance Invariants

All code, schemas, ledger logic, and UI components enforce four invariants
architecturally, not through documentation:

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

## BME Metric Suite

The Behavioral Measurement of Entropy Suite provides the shared diagnostic
layer across all three ALAGF subsystems.

### SPC Process Control Family (BAAGF Appendix C)

| Metric | Governance Function | Classical Analogue |
|---|---|---|
| **ECPI** (Entropy-Calibrated Performance Index) | Process capability | Cp / Cpk |
| **BAR** (Behavioral Assurance Rating) | Control limits | x̄ ± 3σ |
| **ECI** (Entropy Control Index) | Sigma-level equivalent | Z-score |
| **SPAR** (Stochastic Process Adherence Ratio) | Process yield | DPMO |
| **CBMES** (Composite BME Evaluation Score) | Aggregate escalation metric | — |

### Governance-Layer Metrics

| Metric | Function |
|---|---|
| **IQD** (Information Quality Deviation) | Corpus-level data quality |
| **AHRS** (Architectural Hallucination Risk Score) | Pre-deployment architectural risk |
| **PTDI** (Prompt Traceability and Disclosure Index) | Prompt governance traceability |
| **Bias Amplification Rate** (NOBE/BAR whitepaper) | Per-turn bias trajectory measurement |

**BAR Disambiguation:** This ecosystem contains two distinct metrics sharing
the BAR acronym. In the BME Suite and SPC context, BAR = Behavioral Assurance
Rating (control limit analogue). In the NOBE methodology context, BAR = Bias
Amplification Rate (|BMS(turn_N)| / |BMS(turn_1)|). The multi-agent extension
metric BAR-A is a Behavioral Assurance Rating extension, not a Bias
Amplification Rate extension. See `/docs/nomenclature/BAR_disambiguation.md`.

### Multi-Agent BME Extensions (v2)

- **BAR-A** — Agentic Behavioral Assurance Rating (agent-scoped control limits)
- **ECPI-A** — Agentic Entropy-Calibrated Performance Index
- **IQD-A** — Recursive Information Quality Deviation (across agent chain)

### CBMES Tier Thresholds

| CBMES Range | Tier | Governance Response |
|---|---|---|
| 0.00–0.10 | T0 Optimal | Routine monitoring |
| 0.11–0.25 | T1 Stable | Standard oversight |
| 0.26–0.50 | T2 Moderate Drift | Enhanced review |
| 0.51–0.75 | T3 High Risk | Escalation protocol activation |
| 0.76–0.90 | T4 Critical | Mandatory remediation |
| > 0.90 | T5 Emergency | Automatic suspension; post-incident review |

---

## Standards Alignment

- ISO/IEC 42001:2023 — AI Management System Standard
- NIST AI RMF 1.0 — Govern / Map / Measure / Manage functions
- EU AI Act (Regulation 2024/1689) — Articles 9, 10, 11, 13, 17, 29
- ISO/IEC 27001 — Information security governance of audit artifacts
- IEEE P2863 / IEEE 7010 — Decision authority and wellbeing-relevant CTG dimensions

Clause mappings: `/shared/standards-refs/`

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
    ├── dissertation-artifacts/
    ├── nomenclature/
    └── release-notes/
```

---

## Current Sprint

**ECOSYSTEM-SPRINT-1** — AgentIdentity Implementation and Ledger Registration
Enforcement (OPEN)

See `/multiagent/docs/sprint_prompts/` for sprint initialization prompts and
Definition of Done acceptance criteria.

## Prior Work Reference Corpus

The theoretical foundations for this ecosystem are documented in the project
artifact corpus. Key references:

- Rutherford, D. A. (2026). *Behavioral Assurance: SPC-Based Governance of
  Stochastic AI Systems under ALAGF*. (11-chapter treatise; canonical ALAGF
  reference.)
- Rutherford, D. A., & Wu, N. (2026). *Near-Objectivity Bias Evaluation (NOBE)
  and Bias Amplification Rate (BAR)*. Publication Tracker PT-2026-007.
- Rutherford, D. A., & Wu, N. (2026). *Assessing Architectural Hallucination
  Risk in Language Models: A Dual-Purpose Framework*. (AHRS specification.)
- Wu, N., & Rutherford, D. A. (2026). *Interaction-Induced Knowledge Narrowing:
  Lifecycle Governance Risk in LLM Systems*. (IIKN paper.)
- Rutherford, D. A. (2026). *Large Language Model Autophagy: Quantifying
  Epistemic Decay and Governance Intervention in Recursive AI Training
  Ecosystems*. AI Governance Review, Vol. I, Issue 1.1.
  DOI: 10.5281/zenodo.19452160
