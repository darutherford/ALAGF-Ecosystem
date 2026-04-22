# Sprint-3 Changelog

**Sprint:** ECOSYSTEM-SPRINT-3
**Track:** /multiagent
**Auditor:** AUDITOR_DALE_001
**Primary invariant:** Invariant 2 (Non-Bypass) — structural enforcement
**Sprint-1/2 baseline at sprint open:** 78 passed, 1 skipped
**Sprint-3 close target:** Sprint-1/2 baseline unchanged (78 passed), Sprint-3
additions pass, 0 skips (the reserved Sprint-3 test is activated).

## Scope

Sprint-3 transforms `max_synthesis_depth` from persisted-but-unenforced
metadata into architectural enforcement. Hypothesis runtime is introduced
end-to-end: factory conforming to the HEAD-locked Sprint-0 schema, precondition
pipeline, depth computation, ceiling evaluation, HEAD-format ledger emission,
API surface, and invariant acceptance tests that extend (not replace) the
Sprint-1/2 baseline.

## Ratified design decisions

All seven decisions below are recorded as the Sprint-3 decision ledger.
Decision (e) and (g) were revised after discovering HEAD contract constraints
during integration.

### (a) Ceiling attribution — chain-minimum

`governing_ceiling = min(max_synthesis_depth)` over the union of the emitting
agent and every agent in the transitive upstream chain. Closes the
relay-laundering vector: a T4 agent with `max_synthesis_depth=10` cannot
consume a T1 agent's `max_synthesis_depth=1` Hypothesis to extend effective
depth beyond 1.

Implementation: `multiagent/orchestrator/synthesis/depth.py::evaluate_depth_ceiling`.

### (b) Freeze scope — path-scoped

Only Hypotheses whose provenance chain includes a depth-limited ancestor are
blocked. Parallel provenance paths continue. Derivable purely from the ledger
by walking `upstream_hypothesis_refs` transitively against
`frozen_provenance_ancestors` from prior `DEPTH_LIMIT_REACHED` events.

Implementation: `depth.py::is_session_depth_frozen`.

### (c) Observation depth semantics — depth=0 floor

Observations are the provenance floor, not inferential hops. A Hypothesis with
`upstream_hypothesis_refs=[]` has `synthesis_depth=1`. A Hypothesis with
upstream refs has `synthesis_depth = max(upstream_depths) + 1`. The HEAD
Hypothesis schema permits `synthesis_depth` minimum of 0, so the floor is
representable in the schema; Sprint-3 policy constrains the factory to emit
`>= 1` for Hypotheses (since Hypotheses are inferential, not observational).

### (d) Authority-scope rejection type — new `ScopeViolationError`

`ScopeViolationError` introduced as a net-new subclass of `ALAGFError`.
`AuthorityViolationError` remains reserved for `non_authoritative_flag`
override attempts (Invariant 1 binding-outcome class). This preserves audit
taxonomy differentiation.

Open item for Sprint-4: the `ScopeViolationError` raise path does not emit a
dedicated ledger event. Sprint-4 should decide whether to add a
`SCOPE_VIOLATION` event type.

### (e-revised) `composite_upstream_bme_score` — placeholder with payload marker

**HEAD-locked schema constraint surfaced during integration:** the Sprint-0
`shared/artifact-contracts/v2/Hypothesis.schema.json` specifies
`composite_upstream_bme_score` as a required non-nullable number in
`[0.0, 1.0]`. The original Sprint-3 proposal to make the field nullable is
prohibited by the Sprint-0 lock.

Revised approach: Sprint-3 accepts caller-supplied placeholder values in range
and records `bme_score_source: "placeholder"` on the `HYPOTHESIS_REGISTERED`
event payload. Sprint-4 BME attribution will populate real values and set
`bme_score_source: "computed"`.

This preserves the schema integrity without touching the shared contract, and
retains reconstructability of score provenance via the ledger payload marker.

### (f) Handoff vs. synthesis for depth — separation

`AGENT_HANDOFF` moves artifacts (orchestration, Invariant 2 boundary layer).
`upstream_hypothesis_refs` determines depth (inference, Invariant 3
provenance). Handoffs are NOT counted as inferential hops.

The envelope's `causal_refs.referenced_event_id` slot is populated with the
`AGENT_HANDOFF` event_id when synthesis immediately follows a handoff that
transported an upstream Hypothesis into the source agent's scope. This is an
annotation, not a synthesis hop.

### (g-i) `observation_refs` — required on every Hypothesis

**HEAD-locked schema constraint:** `observation_refs` has `minItems: 1`.
Sprint-3 enforces this at emission time regardless of depth. Every Hypothesis
in a chain carries its own observation provenance; downstream Hypotheses do
not merely inherit from upstream refs.

Rationale: every inferential artifact traces to evidence independently.
Orchestrator-layer consistency checks (downstream observation_refs subset of
upstream transitive closure) are deferred to Sprint-4.

## New ledger event types

| Event type | Purpose | Emit timing |
|---|---|---|
| `HYPOTHESIS_REGISTERED` | Successful Hypothesis synthesis | After all preconditions pass and artifact validates |
| `DEPTH_LIMIT_REACHED` | Ceiling-exceeding synthesis attempt | BEFORE `DepthLimitExceededError` is raised |

Payload schemas (new files):
- `multiagent/ledger/hash_chain/event_schemas/v2/HYPOTHESIS_REGISTERED.payload.schema.json`
- `multiagent/ledger/hash_chain/event_schemas/v2/DEPTH_LIMIT_REACHED.payload.schema.json`

## Envelope schema modification

`multiagent/ledger/hash_chain/event_schemas/v2/LedgerEvent.envelope.schema.json`:
`event_type` enum extended with `HYPOTHESIS_REGISTERED` and
`DEPTH_LIMIT_REACHED`. No other envelope changes.

## EventType Literal modification (Sprint-1/2 code)

`multiagent/ledger/hash_chain/events.py`: the `EventType = Literal[...]`
declaration is extended with the two new event types. This is a type annotation
only; runtime enforcement happens via the envelope schema. Required for
type-checker acceptance and IDE support. **This is the only modification to a
Sprint-1/2 code file in Sprint-3.**

## New Python modules

- `multiagent/artifacts/Hypothesis/__init__.py` — HEAD-schema-conformant factory
- `multiagent/orchestrator/synthesis/__init__.py` — package
- `multiagent/orchestrator/synthesis/depth.py` — ceiling evaluation, freeze derivation
- `multiagent/orchestrator/synthesis/hypothesis.py` — emission pipeline
- `multiagent/orchestrator/synthesis/fs_adapter.py` — LedgerReader/Writer over Sprint-1/2
- `multiagent/orchestrator/synthesis/fs_agent_registry.py` — AgentRegistryReader adapter
- `multiagent/api/hypothesis_routes.py` — FastAPI endpoints

## New exception classes

| Exception | Base | Net-new in Sprint-3? |
|---|---|---|
| `DepthLimitExceededError` | `ALAGFError` (Sprint-1 reserved); Sprint-3 subclass adds kw attributes | Subclassed in Sprint-3 |
| `ScopeViolationError` | `ALAGFError` | Yes |
| `FrozenPathError` | `ALAGFError` | Yes |
| `UpstreamResolutionError` | `ALAGFError` | Yes |
| `HypothesisValidationError` | `ArtifactValidationError` | Yes |

**Location:** Defined in `multiagent/orchestrator/synthesis/hypothesis.py`
and `multiagent/artifacts/Hypothesis/__init__.py` (via import from there).
Consolidation into `multiagent/exceptions.py` is a Sprint-4 tech-debt item.

## Extended invariant tests

All four invariant test files are **extended**, not replaced. HEAD content is
preserved verbatim; Sprint-3 tests append after a clear delimiter comment.

- `test_authority.py`: 10 HEAD tests preserved + 7 Sprint-3 tests
- `test_non_bypass.py`: 6 HEAD tests preserved + 6 Sprint-3 tests; the
  previously-skipped `test_depth_ceiling_emits_depth_limit_reached_event` is
  activated
- `test_evidence_first.py`: 9 HEAD tests preserved + 4 Sprint-3 tests
- `test_reconstructability.py`: 9 HEAD tests preserved + 4 Sprint-3 tests

New agent boundary tests:

- `test_hypothesis.py`: 5 tests for Hypothesis emission, scope, cross-agent depth
- `test_api_hypothesis.py`: 6 API tests

## Open items for Sprint-4

1. **`ScopeViolationError` ledger event treatment.** Decide `SCOPE_VIOLATION`
   event type vs. extending `UNREGISTERED_AGENT_OUTPUT`.
2. **`FrozenPathError` ledger event treatment.** Decide `FROZEN_PATH_REJECTED`
   event type vs. reliance on prior `DEPTH_LIMIT_REACHED`.
3. **BME attribution wire-up.** Populate `composite_upstream_bme_score` with
   computed floats; set `bme_score_source: "computed"`.
4. **Exception taxonomy consolidation.** Move `ScopeViolationError`,
   `FrozenPathError`, `UpstreamResolutionError`, `HypothesisValidationError`
   into `multiagent/exceptions.py`.
5. **Downstream observation consistency.** Consider enforcing that a
   Hypothesis's `observation_refs` is a subset of the transitive union of
   upstream Hypotheses' `observation_refs`.
6. **Registry adapter consolidation.** `FsAgentRegistry` reimplements a minimal
   slice of Sprint-1 agent lookup. Consolidate with the canonical Sprint-1
   function.

## Integration lessons recorded

Two integration defects surfaced during this sprint and are recorded as
process lessons:

1. **Conftest collision (resolved hotfix).** Initial Sprint-3 deliverable
   overwrote the Sprint-1/2 `conftest.py` rather than extending it. The merged
   version preserves `_clean_ledger` autouse, `session_id`, `auditor_id`, and
   Sprint-1/2 fixture surface while adding no Sprint-3-specific fixtures
   (Sprint-3 tests construct adapters directly per-test rather than via
   fixtures).
2. **HEAD schema incompatibility (resolved rewrite).** Initial Sprint-3
   deliverable authored the Hypothesis factory against a hypothesized schema
   rather than the HEAD-locked Sprint-0 schema. Integration exposed field-name
   mismatches (`artifact_id` vs. `hypothesis_id`), field-requirement
   mismatches (`observation_refs` minItems: 1 omitted), and
   null-permissibility mismatches (`composite_upstream_bme_score`). Full
   rewrite aligned all fields to HEAD.

**Process correction for future sprints:** Sprint initialization prompts
should include the HEAD contents of every file to be modified, not just the
directory tree. Sprint-1 and Sprint-2 were authored end-to-end without this
issue because they created net-new files; Sprint-3 is the first sprint
extending Sprint-0 scaffolds.

## Integration lesson: canonical lookup strips meta fields

The `FsAgentRegistry` adapter required three iterations to reach a working form:

1. **v1** read registry files directly, compared `artifact.get("session_id")`.
   The artifact on disk uses `_session_id` (underscore-prefixed meta key),
   so the comparison always returned None. All 23 Sprint-3 tests failed.
2. **v2** delegated fully to `get_agent_identity(agent_id)` and read
   `_session_id` from the returned dict. The canonical function strips
   meta fields on return, so `_session_id` was always None. Same 23
   failures recurred.
3. **v3 (shipped)** reads the raw registration file for session scoping
   via `_session_id` and calls `get_agent_identity()` only for live
   status resolution (which honors SUSPENDED / REVOKED markers). Merges
   the two reads before returning.

**Sprint-4 consolidation opportunity:** Extend Sprint-1's canonical
lookup with an optional `session_id` filter parameter. That would
eliminate Sprint-3's need for raw-file reads here and make the adapter
a one-line pass-through.

**Process correction for future sprints:** When an adapter reads through
a canonical function, the decision ledger entry for that adapter must
explicitly document which meta fields the canonical function preserves
and which it strips. This would have caught the v1 and v2 defects at
design time.
