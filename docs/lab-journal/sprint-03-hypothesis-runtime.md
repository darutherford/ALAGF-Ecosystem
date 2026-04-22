# Sprint-3: Hypothesis Runtime and Depth Ceiling Enforcement

**Sprint identifier:** ECOSYSTEM-SPRINT-3
**Close date:** 2026-04-22
**Close time (local):** 12:15 CDT
**Close commit:** `1237009`
**Primary invariant:** Invariant 2 (Non-Bypass). Structural enforcement of
`max_synthesis_depth` via chain-minimum ceiling attribution and path-scoped
freeze derivation.

## Purpose

Sprint-3 transformed `max_synthesis_depth` from persisted-but-unenforced
metadata into architectural enforcement. It delivered the Hypothesis
runtime end-to-end: the HEAD-schema-conformant factory, the synthesis
precondition pipeline, the chain-minimum depth computation, path-scoped
freeze derivation from ledger events, `HYPOTHESIS_REGISTERED` and
`DEPTH_LIMIT_REACHED` event emission, the FastAPI endpoint surface, and
the invariant acceptance test extensions that activate the Sprint-1
reserved depth-ceiling test. Sprint-3 closed with 110 passing tests, zero
skipped, on the full `multiagent/tests` suite.

## Strategic Context

Sprint-1 established agent registration with `max_synthesis_depth` as a
required field on the AgentIdentity artifact. Sprint-2 established that
agent boundaries are governance boundaries with full `AGENT_HANDOFF`
lifecycle enforcement. Sprint-3's question was: given a registered agent
with a declared depth ceiling and authenticated boundary-crossing
semantics, what prevents synthesis from exceeding the ceiling?

The answer must be structural, not procedural. A procedural answer (check
the ceiling at emission time, raise if exceeded) is necessary but
insufficient. Procedural checks can be bypassed by alternative code
paths; they can be disabled by configuration; they provide no audit
evidence when they succeed, only when they fail. A structural answer
makes exceeding the ceiling architecturally impossible within the
sanctioned emission path and produces ledger evidence on every
enforcement event.

Three adversary models motivated the structural framing. First, the
**relay model**: a high-ceiling agent consumes a low-ceiling agent's
output to extend effective synthesis depth beyond what the low-ceiling
agent was authorized to produce. Second, the **parallel path model**: a
session hits its depth ceiling on one provenance chain, and the
orchestrator attempts to continue synthesis on a separate chain rooted
at a different observation. Third, the **retry model**: a ceiling
violation is detected, and the orchestrator retries the same emission
after a transient delay in hopes the check was flaky.

Sprint-3's design decisions address each adversary model explicitly.

## Scope and Deliverables

Nine logical commits between 12:15:47 and 12:15:49 CDT on 2026-04-22
(commit timestamps collapse at this granularity because the commits were
issued in a tight sequence after the test-suite gate passed). Listed in
commit order:

**Commit 1. EventType Literal and envelope enum extension.** The
`EventType = Literal[...]` declaration at
`multiagent/ledger/hash_chain/events.py` was extended with
`HYPOTHESIS_REGISTERED` and `DEPTH_LIMIT_REACHED`. The envelope schema's
`event_type` enum was extended correspondingly. This is the only Sprint-3
modification to a Sprint-1 or Sprint-2 code file; all other Sprint-3 work
is net-new files.

**Commit 2. Event payload schemas.** New payload schemas for the two
Sprint-3 event types at
`multiagent/ledger/hash_chain/event_schemas/v2/`. The
`DEPTH_LIMIT_REACHED` payload carries a closed-enum `rejection_reason`
field with value `CHAIN_MINIMUM_CEILING_EXCEEDED`, consistent with the
Sprint-2 closed-enum rejection taxonomy.

**Commit 3. Hypothesis factory.** The `build_hypothesis()` and
`validate_hypothesis()` functions at
`multiagent/artifacts/Hypothesis/__init__.py` conform to the HEAD-locked
Sprint-0 Hypothesis schema and implement Invariant 1 double-enforcement
using the Sprint-1 factory template.

**Commit 4. Depth computation module.** The
`multiagent/orchestrator/synthesis/depth.py` module implements the
chain-minimum ceiling computation and path-scoped freeze derivation.
Both are pure functions over the registered-agent set and the session
ledger, with no runtime state. The `evaluate_depth_ceiling()` function
walks the transitive upstream agent set and returns the governing
ceiling as the minimum `max_synthesis_depth` across that set. The
`is_session_depth_frozen()` function derives freeze state from prior
`DEPTH_LIMIT_REACHED` events in the ledger.

**Commit 5. Emission orchestrator, ledger adapter, agent registry
adapter.** The `emit_hypothesis()` function at
`multiagent/orchestrator/synthesis/hypothesis.py` implements the full
precondition pipeline: registration check, scope check, upstream
resolution, ceiling evaluation, freeze check, emission. The `FsLedger`
and `FsAgentRegistry` adapters bridge the Sprint-3 synthesis code to the
Sprint-1/2 filesystem ledger and registry.

**Commit 6. FastAPI router.** Four endpoints at
`multiagent/api/hypothesis_routes.py`: POST `/hypotheses` for emission,
GET `/hypotheses/{artifact_id}` for retrieval, GET
`/sessions/{session_id}/hypotheses` for session listing, GET
`/sessions/{session_id}/depth_state` for freeze and ceiling inspection.
The router inherits the Sprint-1/2 auditor header convention.

**Commit 7. Extended invariant acceptance tests.** All four invariant
test modules (`test_authority.py`, `test_non_bypass.py`,
`test_evidence_first.py`, `test_reconstructability.py`) extended with
Sprint-3 sections under explicit delimiter comments. The Sprint-1
baseline of 78 passing tests was preserved. The
Sprint-1-reserved-and-skipped test `test_depth_ceiling_emits_depth_limit_reached_event`
was activated.

**Commit 8. Agent boundary tests.** Two new test modules at
`multiagent/tests/agent_boundary_tests/`: `test_hypothesis.py` for
source-agent scope and cross-agent depth walk verification, and
`test_api_hypothesis.py` for the Sprint-3 endpoint surface.

**Commit 9. Documentation.** README update, Sprint-3 changelog, shared
CHANGELOG prepended entry, Lab Journal and Development Notes retroactive
backfill (this document and its counterpart).

## Design Decisions

Sprint-3 ratified seven decisions. Two were revised after integration
exposed HEAD-schema constraints that the initial proposals had not
accommodated.

**Decision S3.1. Chain-minimum ceiling attribution.** The governing
ceiling for any synthesis event is the minimum `max_synthesis_depth`
across the union of the emitting agent and every agent in the transitive
upstream provenance chain. This closes the relay adversary model: a T4
agent with `max_synthesis_depth=10` cannot consume a T1 agent's
`max_synthesis_depth=1` Hypothesis to extend effective depth beyond 1,
because the chain-minimum computation returns 1 regardless of the T4
agent's own ceiling. The alternative, using only the emitting agent's
ceiling, would have made the ceiling per-agent rather than
per-provenance-chain, which fails to protect against relay laundering.

**Decision S3.2. Path-scoped freeze.** When a `DEPTH_LIMIT_REACHED`
event is emitted, only Hypotheses whose provenance chain intersects a
depth-limited ancestor are subsequently blocked. Parallel provenance
paths that do not include frozen ancestors continue to function. This
addresses the parallel path adversary model without producing a
session-wide shutdown that would be more restrictive than Invariant 2
requires. The freeze state is derivable purely from ledger events by
walking `upstream_hypothesis_refs` transitively against the
`frozen_provenance_ancestors` list from prior `DEPTH_LIMIT_REACHED`
events, preserving Invariant 4 (Reconstructability).

**Decision S3.3. Observations as the depth floor.** Observations are
the provenance floor, not inferential hops. A Hypothesis with no
upstream Hypothesis references has `synthesis_depth = 1`. A Hypothesis
with upstream references has `synthesis_depth = max(upstream_depths) + 1`.
This policy recognizes that Observations are not inferential acts:
asserting an Observation creates evidence; asserting a Hypothesis
generates an inference from evidence. The depth counter measures
inferential distance from evidence, so it begins at 1 on the first
inferential hop.

**Decision S3.4. New `ScopeViolationError` subclass of `ALAGFError`.**
The existing `AuthorityViolationError` is reserved for Invariant 1
binding-outcome class violations (overriding `non_authoritative_flag`).
A new exception type was introduced for Invariant 2 scope violations
(an `OBSERVATIONS_ONLY` agent attempting Hypothesis emission). This
preserves audit taxonomy differentiation: Invariant 1 violations and
Invariant 2 violations produce distinct typed exceptions, making
downstream log analysis and evidence-pack generation cleaner.

**Decision S3.5 (revised). `composite_upstream_bme_score` placeholder
with payload marker.** The initial Sprint-3 proposal was to make
`composite_upstream_bme_score` nullable for Sprint-3 and populate it in
Sprint-4. During integration, the HEAD-locked Sprint-0 Hypothesis
schema was discovered to specify the field as required, non-nullable,
and constrained to the interval `[0.0, 1.0]`. Modifying the shared
schema was prohibited by the Sprint-0 lock. The revised approach
accepts caller-supplied placeholder values in the valid range and
records `bme_score_source: "placeholder"` on the `HYPOTHESIS_REGISTERED`
event payload. Sprint-4 will populate computed values and set
`bme_score_source: "computed"`. This revision preserves schema
integrity without touching shared contracts and retains
reconstructability of score provenance via the ledger payload marker.

**Decision S3.6. Handoff versus synthesis for depth accounting.**
`AGENT_HANDOFF` events move artifacts across agent boundaries (Sprint-2
orchestration-layer semantics). `upstream_hypothesis_refs` determines
synthesis depth (Sprint-3 inference-layer semantics). These two
concepts are kept strictly separate: handoffs are not counted as
inferential hops. The envelope's `causal_refs.referenced_event_id`
slot is populated with the `AGENT_HANDOFF` event_id when synthesis
immediately follows a handoff that transported an upstream Hypothesis
into the source agent's scope. This annotation preserves
reconstructability without conflating orchestration with inference.

**Decision S3.7 (revised). `observation_refs` required on every
Hypothesis regardless of depth.** The initial Sprint-3 proposal was
that only depth-1 Hypotheses would require `observation_refs`, with
deeper Hypotheses inheriting observation provenance transitively from
upstream references. During integration, the HEAD-locked Sprint-0
Hypothesis schema was discovered to specify `observation_refs` with
`minItems: 1`, requiring the field on every Hypothesis. The revised
policy is that every Hypothesis in a chain carries its own observation
provenance. Downstream Hypotheses do not merely inherit from upstream
references; they trace their own evidence. This strengthens Invariant 3
(every inferential artifact traces to evidence independently) at the
cost of requiring callers to thread observation references through
deep synthesis chains.

## Invariant Enforcement Status at Sprint Close

- **Invariant 1 (Authority):** Fully enforced across AgentIdentity
  (Sprint-1), AgentHandoff (Sprint-2), and Hypothesis (Sprint-3). The
  factory template for double-enforcement (schema `const: true` plus
  factory-level typed exception) is applied consistently across all
  three factories.
- **Invariant 2 (Non-Bypass):** Structurally enforced. Chain-minimum
  ceiling attribution makes relay laundering architecturally impossible.
  Path-scoped freeze prevents post-freeze synthesis on depth-limited
  chains while permitting parallel path continuation. Emit-before-raise
  discipline ensures `DEPTH_LIMIT_REACHED` is committed to the ledger
  before `DepthLimitExceededError` propagates. Retry attempts
  re-evaluate ceiling and freeze state on every emission, making the
  retry adversary model architecturally defeated.
- **Invariant 3 (Evidence-First):** Enforced at Hypothesis emission.
  Every `HYPOTHESIS_REGISTERED` event carries the source agent as
  `actor.actor_id`, the synthesis_depth, the upstream_hypothesis_refs,
  the observation_refs (minItems: 1), and the governing ceiling
  attribution. Upstream references must resolve to prior
  `HYPOTHESIS_REGISTERED` events in the same session; unresolved
  references raise `UpstreamResolutionError`.
- **Invariant 4 (Reconstructability):** Fully enforced. The synthesis
  tree for any session is reconstructible from the ledger alone by
  walking `upstream_hypothesis_refs` through
  `HYPOTHESIS_REGISTERED` events back to the Observation floor. Freeze
  state is derivable from `DEPTH_LIMIT_REACHED` events. Hash chain
  integrity verifies across all five sprint event type categories
  (registration, boundary, handoff, synthesis, depth rejection).

## Outstanding Items at Sprint Close

Six items were recorded in the Sprint-3 changelog as Sprint-4
candidates:

1. **`ScopeViolationError` ledger event treatment.** The Sprint-3
   implementation raises the exception but does not emit a dedicated
   ledger event. Sprint-4 should decide whether to introduce a
   `SCOPE_VIOLATION` event type or extend the existing
   `UNREGISTERED_AGENT_OUTPUT` taxonomy.
2. **`FrozenPathError` ledger event treatment.** Same question as above
   for the path-scoped freeze rejection path.
3. **BME attribution wire-up.** Populate `composite_upstream_bme_score`
   with computed floats, set `bme_score_source: "computed"`.
4. **Exception taxonomy consolidation.** Move `ScopeViolationError`,
   `FrozenPathError`, `UpstreamResolutionError`, and
   `HypothesisValidationError` from their Sprint-3 module locations
   into `multiagent/exceptions.py`.
5. **Downstream observation consistency.** Consider enforcing that a
   Hypothesis's `observation_refs` is a subset of the transitive union
   of upstream Hypotheses' `observation_refs`.
6. **Registry adapter consolidation.** Extend Sprint-1's canonical
   `get_agent_identity()` with an optional `session_id` filter, reducing
   `FsAgentRegistry` to a one-line pass-through.

## Novel Contribution Indicators

Sprint-3 produced two architectural contributions that warrant
dissertation-level citation.

**Chain-minimum ceiling attribution.** To the best knowledge of the
auditor at the time of Sprint-3 close, existing multi-agent
orchestration frameworks that implement any form of depth limiting
(for example, LangGraph recursion limits, AutoGen max_turns) apply the
limit per-agent or per-conversation-turn rather than per-provenance-chain.
Per-agent limits fail under relay laundering; per-turn limits fail under
parallel-path fan-out. The chain-minimum approach applies the strictest
upstream ceiling across the full transitive provenance chain, which
defeats both adversary models simultaneously. This approach aligns with
NIST AI RMF 1.0's MEASURE function (NIST, 2023) by producing a
measurable, bounded, auditable constraint on AI inferential depth.

**Path-scoped freeze derivation from ledger events.** Depth-limit
enforcement typically produces a binary session state (active or
frozen). The path-scoped approach produces a derived, per-provenance-chain
freeze state that is recomputable at any point from the session's event
log. This supports ISO/IEC 42001:2023 clause 8.3 operational planning
(ISO, 2023) by allowing fine-grained session continuation policies:
frozen chains do not propagate their freeze state to parallel chains
that do not depend on them.

Both contributions are candidates for formalization in the dissertation's
Invariant 2 structural enforcement chapter.

## Integration Lessons

Sprint-3 surfaced three integration defects that warrant explicit record
in the project's lab notes. Full technical detail appears in
`docs/development-notes/sprint-03-integration-notes.md`. The high-level
lessons:

First, sprint initialization prompts must include the HEAD contents of
every file to be modified, not just the directory tree. Sprint-3's
initial deliverable was authored against a hypothesized Hypothesis
schema, and integration exposed multiple HEAD-schema field-name and
field-requirement mismatches. The fix was a full factory rewrite
aligned to HEAD. Sprint-1 and Sprint-2 did not encounter this problem
because they created net-new files; Sprint-3 was the first sprint
extending a Sprint-0 shared contract, and the gap in the initialization
discipline surfaced there.

Second, when an adapter delegates to a canonical function, the decision
ledger entry for that adapter must explicitly document which meta fields
the canonical function preserves and which it strips. The Sprint-3
`FsAgentRegistry` adapter required three iterations because
`get_agent_identity()` silently strips the `_session_id` meta field, a
Sprint-1 implementation detail that was not documented at the
function-signature level.

Third, test isolation across sprints must be verified by extension, not
by replacement. Sprint-3's initial deliverable overwrote the Sprint-1/2
`conftest.py`, breaking 41 tests via fixture-name mismatch. The
recovery preserved Sprint-1/2 fixtures verbatim and appended Sprint-3
additions under explicit delimiter comments. This extension discipline
is now the standard for all subsequent sprints.

## References

International Organization for Standardization. (2023). *Information
technology. Artificial intelligence. Management system* (ISO/IEC 42001:2023).

National Institute of Standards and Technology. (2023). *Artificial
Intelligence Risk Management Framework (AI RMF 1.0)* (NIST AI 100-1).
U.S. Department of Commerce. https://doi.org/10.6028/NIST.AI.100-1

Rutherford, D. (2025). *The Applied Lifecycle AI Governance Framework*
[Unpublished manuscript]. University of Arkansas at Little Rock.
