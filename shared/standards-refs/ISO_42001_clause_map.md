# ISO/IEC 42001 Clause Map

**Standard:** ISO/IEC 42001:2023 — Artificial Intelligence Management System
**Purpose:** Traceability map between ALAGF artifacts, invariants, and BME metrics
to ISO/IEC 42001 clauses. Supports compliance evidence generation for audit
review.

**Status:** STUB — populated incrementally as sprints produce evidence.

---

## Clause Mapping Template

| ISO/IEC 42001 Clause | Clause Title | ALAGF Artifact / Invariant / Module | Evidence Location |
|---|---|---|---|
| 4.1 | Understanding the organization and its context | — | — |
| 4.2 | Needs and expectations of interested parties | — | — |
| 4.3 | Scope of the AI management system | AuditSession (audit_target, session_purpose) | `/demo/artifacts/AuditSession/` |
| 5.1 | Leadership and commitment | Decision (auditor_id required) | Invariant 1 (Authority) |
| 5.2 | AI policy | ConstraintSet (policy_references) | Invariant 3 (Evidence-First) |
| 6.1.2 | AI risk assessment | MetricObservation (BME metrics) | `/shared/bme-metric-suite/` |
| 6.1.3 | AI risk treatment | Action (decision_ref, policy_reference) | Invariant 2 (Non-Bypass) |
| 7.5 | Documented information | Append-only ledger with SHA-256 chain | Invariant 4 (Reconstructability) |
| 8.2 | AI system impact assessment | Hypothesis (non-binding advisory) | Invariant 1 (Authority) |
| 9.1 | Monitoring, measurement, analysis, evaluation | SPC/CUSUM on BME metrics | `/shared/bme-metric-suite/spc_cusum.py` |
| 9.2 | Internal audit | Full ledger reconstruction | Invariant 4 (Reconstructability) |
| 10.2 | Nonconformity and corrective action | UNREGISTERED_AGENT_OUTPUT, rejection events | Invariant 2 (Non-Bypass) |

---

## Multi-Agent Extension Additions (v2)

| ISO/IEC 42001 Clause | Multi-Agent Artifact / Mechanism | Governance Rationale |
|---|---|---|
| 5.1 | AgentIdentity.registered_by (human required) | Human accountability preserved across agent topology |
| 6.1.2 | composite_upstream_bme_score | Risk assessment aggregates across agent chain |
| 6.1.3 | Action.delegation_blocked | Risk treatment cannot be circumvented by sub-agent delegation |
| 7.5 | AgentHandoff ledger events | Documented information includes every boundary crossing |
| 8.2 | Hypothesis.synthesis_depth | Impact assessment bounded by structural depth ceiling |
| 9.2 | input_provenance_chain | Internal audit reconstructs full agent chain from ledger |

---

## Population Instructions

Entries are added as sprint deliverables produce concrete evidence artifacts.
Each entry requires:

- Specific clause identifier and title
- ALAGF artifact, invariant, or module reference
- Evidence file path or ledger event type
- Governance rationale (one sentence minimum)

No clause entry is marked complete without a traceable evidence pointer.
