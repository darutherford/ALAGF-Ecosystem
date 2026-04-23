# NIST AI RMF Function Map

**Standard:** NIST AI Risk Management Framework (AI RMF 1.0)
**Purpose:** Traceability map between ALAGF artifacts, invariants, and BME metrics
to NIST AI RMF functions (Govern, Map, Measure, Manage).
**Status:** STUB — populated incrementally as sprints produce evidence.

---

## Function Mapping

### GOVERN

Establish and cultivate a culture of AI risk management.

| Subcategory | ALAGF Mechanism | Location |
|---|---|---|
| GOVERN 1.1 (policies) | ConstraintSet.policy_references | v1 canonical |
| GOVERN 1.2 (accountability) | Decision.auditor_id (required) | Invariant 1 |
| GOVERN 1.3 (workforce) | AgentIdentity.registered_by (human required) | v2 canonical |
| GOVERN 1.5 (documentation) | Append-only ledger with SHA-256 chain | Invariant 4 |
| GOVERN 4.1 (organizational practices) | Four invariants as architectural enforcement | Project instructions §3 |

### MAP

Context is recognized and risks are identified.

| Subcategory | ALAGF Mechanism | Location |
|---|---|---|
| MAP 1.1 (context) | AuditSession (audit_target, session_purpose) | v1 canonical |
| MAP 2.1 (AI system categorization) | AgentIdentity.agent_type, trust_tier | v2 canonical |
| MAP 3.1 (risk tolerance) | AgentIdentity.max_synthesis_depth | Invariant 2 |
| MAP 4.1 (third-party dependencies) | AgentIdentity.provider, model_id | v2 canonical |

### MEASURE

AI risks are assessed and tracked.

| Subcategory | ALAGF Mechanism | Location |
|---|---|---|
| MEASURE 1.1 (test suite) | `/demo/tests/`, `/multiagent/tests/invariant_tests/` | Sprint 0-7 |
| MEASURE 2.3 (performance) | MetricObservation (BME metrics) | Orchestration v1 |
| MEASURE 2.7 (security/resilience) | StressObservation (adversarial, robustness stress types) | Orchestration v1 |
| MEASURE 2.11 (fairness/bias) | BAR-NOBE (Bias Amplification Rate per NOBE methodology, PT-2026-007); per-turn bias trajectory monitoring | NOBE methodology |
| MEASURE 3.1 (ongoing monitoring) | SPC/CUSUM on BME metrics (BAR = Behavioral Assurance Rating, ECPI, ECI, SPAR) | `/shared/bme-metric-suite/` |

### MANAGE

AI risks are prioritized and acted upon.

| Subcategory | ALAGF Mechanism | Location |
|---|---|---|
| MANAGE 1.1 (risk response) | Action (decision_ref required) | Invariant 2 |
| MANAGE 2.1 (resource allocation) | Tier logic (T1 Monitor → T4 Freeze) | BME-CI thresholds |
| MANAGE 3.1 (third-party risk) | AgentHandoff (every boundary crossing logged) | v2 canonical |
| MANAGE 4.1 (post-deployment monitoring) | DEPTH_LIMIT_REACHED, UNREGISTERED_AGENT_OUTPUT events | Invariants 2, 4 |

---

## Multi-Agent Extension Considerations

The NIST AI RMF does not currently specify multi-agent governance patterns.
The ALAGF v2 extension contributes:

- **GOVERN gap:** Cross-session agent reputation tracking (dissertation-level
  contribution candidate, future sprint scope)
- **MAP gap:** Agent-boundary risk identification via `input_provenance_chain`
- **MEASURE gap:** Agentic BME metrics (BAR-A = Agentic Behavioral Assurance
  Rating, ECPI-A = Agentic Entropy-Calibrated Performance Index, IQD-A =
  Recursive Information Quality Deviation) capturing cross-agent contamination
  not visible in single-agent metrics. Note: BAR-A is the SPC control-limit
  extension, distinct from BAR-NOBE (Bias Amplification Rate). See
  `/docs/nomenclature/BAR_disambiguation.md`.
- **MANAGE gap:** Structural depth enforcement (`max_synthesis_depth`) as a
  non-bypassable risk control mechanism

---

## Population Instructions

Each entry requires:

- Specific NIST AI RMF subcategory identifier
- ALAGF artifact, invariant, or module reference
- Evidence file path or ledger event type
- Cross-reference to ISO/IEC 42001 clause map where applicable
