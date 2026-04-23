# BAR Disambiguation

**Status:** CANONICAL — required reading before any BME Suite or NOBE work.
**Audience:** All contributors to the ALAGF Ecosystem.
**Last updated:** ECOSYSTEM-SPRINT-0 post-corpus-review remediation.

---

## Problem Statement

The ALAGF research corpus contains two distinct, well-defined metrics that
both use the acronym BAR. Both are authoritative. Both appear in published
or publication-track work. Neither is deprecated. Treating them as a single
metric introduces silent governance failures in implementation, attribution,
and empirical analysis.

This document establishes canonical naming, scope, and usage discipline
across the ecosystem.

---

## The Two BARs

### BAR-BAR — Behavioral Assurance Rating (BME Suite)

**Source:** Rutherford (2026), *Behavioral Assurance*, Appendix C.
**Governance function:** Control limit analogue. Replaces classical `x̄ ± 3σ`.
**Owner subsystem:** BAAGF (architectural conscience).
**Operational scope:** SPC monitoring of any governed behavioral metric.

**Definition:** Empirical quantile-based thresholds defining the boundaries of
expected behavioral variation. Set at the 0.135th and 99.865th percentiles of
the validated baseline behavioral distribution.

**Interpretation:** Points within BAR thresholds reflect common-cause
variation. Points outside trigger special-cause investigation per the
escalation protocol.

**Recalculation triggers:** Re-baselining following authorized system changes
(model updates, corpus changes, SymPrompt+ modulations). BAAGF approval
required before updated thresholds are activated.

**Unit:** Quantile threshold (empirical, distribution-free).
**Typical notation:** `BAR_L`, `BAR_U` for lower and upper thresholds.

### BAR-NOBE — Bias Amplification Rate (NOBE Methodology)

**Source:** Rutherford and Wu (2026), *NOBE/BAR Whitepaper*, Publication
Tracker PT-2026-007. Also Rutherford (2025) dissertation, Table 8.
**Governance function:** Per-turn bias trajectory metric.
**Owner context:** NOBE Phase 1B methodology; output-layer bias governance.
**Operational scope:** Multi-turn LLM conversation monitoring.

**Definition:**

```
BAR = |BMS(turn_N)| / |BMS(turn_1)|
```

where BMS is the Bias Magnitude Score aggregated across the four NOBE layers
(Structural, Semantic, Comparative, AI-Augmented).

**Interpretation:**
- BAR > 1.0 — amplification
- BAR = 1.0 — stability
- BAR < 1.0 — moderation

**Tier thresholds (from NOBE/BAR whitepaper Section 5.4):**

| Tier | Range | Governance Response |
|---|---|---|
| 0 Stable | BAR < 1.10 | No governance action |
| 1 Caution | BAR 1.10–1.25 | Console alert, enhanced monitoring flag, audit log entry |
| 2 Review | BAR 1.25–1.50 | Response flagged with governance annotation, internal audit, mandatory HITL review |
| 3 Critical | BAR > 1.50 | Response suppression, governance override message, formal risk audit |

**Unit:** Dimensionless ratio.
**Typical notation:** `BAR_t` or just `BAR` with turn index context.

---

## Canonical Naming Convention

In all code, schemas, documentation, tests, and dissertation artifacts
produced within this ecosystem, the following disambiguation applies:

| Context | Use | Do Not Use |
|---|---|---|
| SPC control limits in BAAGF / BME Suite | **`BAR` (unqualified)** OR **`BAR-BAR`** (in documents where both metrics appear) | "Bias Amplification Rate" — this is not what the BME Suite BAR measures |
| Bias trajectory in NOBE / per-turn monitoring | **`BAR-NOBE`** (when both metrics may be confused) OR **`Bias Amplification Rate`** (spelled out) | "BAR" unqualified in any document where BME Suite is also in scope |
| Multi-agent extension metric | **`BAR-A`** — extends BAR-BAR (Behavioral Assurance Rating) to agent-scoped control limits | Do not conflate with a Bias Amplification Rate extension |

### Rule of Precedence

Within any single document, schema, module, or sprint:

1. If the document is scoped to BAAGF, BME Suite, SPC monitoring, or the
   broader `/multiagent` track architecture, **BAR without qualifier means
   Behavioral Assurance Rating**.
2. If the document is scoped to NOBE, PT-2026-007, bias evaluation
   methodology, or output-layer bias governance, **BAR without qualifier
   means Bias Amplification Rate**.
3. If a document crosses both scopes, neither metric may appear unqualified.
   Use `BAR-BAR` and `BAR-NOBE` throughout, or spell out the full name on
   first use.

---

## Implications for the Multi-Agent Extension

**BAR-A** in the `/multiagent` track is the **Agentic Behavioral Assurance
Rating**. It extends BAR-BAR to agent-scoped control limits. It is NOT an
agent-scoped Bias Amplification Rate.

**Rationale:** The multi-agent extension's governance theory centers on
agent boundaries as SPC process boundaries. BAR-BAR, as a control-limit
metric, is the natural SPC construct to extend into agent-scoped monitoring.
A per-agent bias trajectory metric is a separate, future research question
and would be named differently (e.g., `BAR-NOBE-A` if such a construct is
formalized).

**Implications for Sprint-4** (BME Attribution Per Agent):

- BAR-A computation uses empirical quantile thresholds per agent, recomputed
  on re-baselining events emitted by MIDCOT's multi-agent drift detector.
- ECPI-A extends ECPI per agent in the same quantile-based pattern.
- IQD-A extends IQD with recursive propagation across agent synthesis chains.
- If per-agent bias trajectory monitoring is added to the roadmap, it requires
  a separate metric definition and cannot be conflated with BAR-A.

---

## Implications for Empirical Reporting

Any empirical result reported in this ecosystem that cites BAR must:

1. Specify which BAR is being reported (BME Suite control limit or NOBE bias
   trajectory) at first mention.
2. Report the unit (threshold value vs dimensionless ratio).
3. If tier mapping is cited, specify whether tiers are CBMES tiers (T0–T5)
   or NOBE BAR tiers (0–3). These are not the same tier systems.

Cross-citation of a NOBE BAR finding in a BAAGF-scoped document requires
the full `BAR-NOBE` or `Bias Amplification Rate` expansion. Cross-citation
of a BAAGF BAR threshold in a NOBE-scoped document requires the full
`BAR-BAR` or `Behavioral Assurance Rating` expansion.

---

## Implications for White Paper Production

Any white paper, dissertation chapter, or peer-reviewed publication from this
ecosystem that references BAR must include a disambiguation footnote or
nomenclature section on first use. The disambiguation should point to this
document as the canonical source.

Failure to disambiguate will produce downstream confusion in citations and
implementation choices. This is a governance-epistemology failure, not
merely a style issue.

---

## Open Question (Deferred)

If future work produces a per-agent multi-turn bias trajectory metric (a
natural extension of NOBE BAR to agentic topologies), the naming will need a
third disambiguation tier. This work is not scoped in the current
seven-sprint plan and is a candidate future research question. When
scheduled, it will receive its own entry in this document.

---

## Revision History

| Date | Change | Sprint |
|---|---|---|
| Sprint-0 post-corpus-review | Initial canonical disambiguation established | ECOSYSTEM-SPRINT-0 remediation |
