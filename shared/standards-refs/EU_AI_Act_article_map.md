# EU AI Act Article Map

**Standard:** Regulation (EU) 2024/1689 — Artificial Intelligence Act
**Purpose:** Traceability map between ALAGF artifacts, invariants, and BME metrics
to EU AI Act articles relevant to high-risk AI system obligations.
**Status:** STUB — populated incrementally as sprints produce evidence.

---

## Article Mapping (Project Instructions §4 Scope)

### Article 9 — Risk management system

Obligation: Establish, implement, document, and maintain a risk management
system for high-risk AI systems throughout the lifecycle.

| Obligation Element | ALAGF Mechanism | Location |
|---|---|---|
| Identification and analysis of risks | StressObservation, MetricObservation | Orchestration v1 |
| Estimation and evaluation | BME-CI composite index (T1–T4 thresholds) | BME Metric Suite |
| Adoption of risk management measures | Action (decision_ref required) | Invariant 2 |
| Documentation throughout lifecycle | Append-only SHA-256 hash-chained ledger | Invariant 4 |

### Article 10 — Data and data governance

Obligation: Training, validation, and testing data sets subject to data
governance and management practices.

| Obligation Element | ALAGF Mechanism | Location |
|---|---|---|
| Data quality assessment | IQD (Information Quality Decay) metric | BME Metric Suite |
| Diversity assessment | PTDI (Pre-Training Diversity Index) | BME Metric Suite |
| Multi-agent data quality | IQD-A (Recursive Information Quality Decay) | v2 BME extension |

### Article 11 — Technical documentation

Obligation: Technical documentation drawn up before placing on market;
kept up-to-date.

| Obligation Element | ALAGF Mechanism | Location |
|---|---|---|
| General description of the AI system | AuditSession, ConstraintSet | v1 canonical |
| Detailed information on monitoring | MetricObservation + SPC/CUSUM trace | Orchestration v1 |
| Risk management system | Invariant enforcement acceptance tests | `/multiagent/tests/invariant_tests/` |
| Post-market monitoring system | Full ledger with reconstruction capability | Invariant 4 |

### Article 13 — Transparency and provision of information to deployers

Obligation: High-risk AI systems must be designed and developed in such a way
that their operation is sufficiently transparent to enable deployers to
interpret the system's output and use it appropriately.

| Obligation Element | ALAGF Mechanism | Location |
|---|---|---|
| Instructions for use | Per-artifact governance rationale in CHANGELOG | `/shared/artifact-contracts/CHANGELOG.md` |
| Characteristics and capabilities | AgentIdentity.authority_scope, trust_tier | v2 canonical |
| Level of accuracy and performance metrics | BME Metric Suite (5 canonical metrics) | BME Metric Suite |
| Known or foreseeable circumstances | StressObservation.stress_type (8 enumerated categories) | Orchestration v1 |

### Article 14 — Human oversight (referenced for context; not in §4 scope list)

Covered structurally via Invariant 1 (Authority) and Decision.auditor_id
requirement. Multi-agent extension adds Decision.agent_context_reviewed
requirement.

### Article 17 — Quality management system

Obligation: Providers of high-risk AI systems must establish a quality
management system ensuring compliance with the Regulation.

| Obligation Element | ALAGF Mechanism | Location |
|---|---|---|
| Strategy for regulatory compliance | Four-invariant architecture | Project instructions §3 |
| Techniques, procedures for design | Sprint prompts + Definition of Done | `/multiagent/docs/sprint_prompts/` |
| Examination, test, and validation procedures | Invariant acceptance test suite | `/multiagent/tests/invariant_tests/` |
| Quality control procedures | CHANGELOG-gated schema evolution | `/shared/artifact-contracts/CHANGELOG.md` |
| Record keeping | Append-only ledger with SHA-256 chain | Invariant 4 |

### Article 29 — Obligations of deployers of high-risk AI systems

Obligation: Deployers must take appropriate technical and organisational
measures to ensure use in accordance with instructions for use.

| Obligation Element | ALAGF Mechanism | Location |
|---|---|---|
| Human oversight assignment | Decision.auditor_id (required) | Invariant 1 |
| Monitoring of operation | MetricObservation + SPC/CUSUM | Orchestration v1 |
| Logging of operation | Append-only ledger with AGENT_HANDOFF events | Invariants 3, 4 |
| Suspension of use on serious incident | AgentIdentity.status transitions (SUSPENDED, REVOKED) | v2 canonical |

---

## Multi-Agent Extension Considerations

The EU AI Act does not currently specify obligations for multi-agent AI
system governance. ALAGF v2 contributes interpretive structures:

- **Article 9 gap:** Multi-agent risk management via composite_upstream_bme_score
- **Article 11 gap:** Technical documentation extended to agent-boundary events
- **Article 13 gap:** Transparency extended to input_provenance_chain disclosure
- **Article 29 gap:** Deployer logging obligations extended to AGENT_HANDOFF events

---

## Population Instructions

Each entry requires:

- Specific Article identifier and obligation element
- ALAGF artifact, invariant, or module reference
- Evidence file path or ledger event type
- Cross-reference to ISO/IEC 42001 clauses and NIST AI RMF subcategories
- Compliance evidence generation procedure (if operational)
