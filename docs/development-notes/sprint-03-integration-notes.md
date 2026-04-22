# Sprint-3 Development Notes --- Hypothesis Runtime

**Close date:** 2026-04-22
**Close time (local):** 12:15 CDT
**Close commit:** `1237009`

## What I Built

The Hypothesis runtime. Factory, depth computation with chain-minimum
ceiling attribution, path-scoped freeze derivation, emission
orchestrator, filesystem adapters, FastAPI router, extended invariant
tests, agent boundary tests, documentation.

110 tests passed, 0 skipped. Sprint-1's reserved depth-ceiling test
was activated.

## Defects Encountered

Sprint-3 was the most defect-dense sprint of the project to date. Three
significant defects, all surfaced at integration time, all resolved
before commit. The defect pattern and recovery approach are worth
capturing in detail because they shape how I will scope future sprints.

### Defect S3.D1 --- conftest collision

My initial Sprint-3 deliverable included a `conftest.py` that replaced
the Sprint-1/2 version entirely. This broke 41 tests immediately via
a fixture-name mismatch: Sprint-1/2 tests depend on a fixture named
`auditor_id`, and my replacement conftest exposed only `auditor`. The
full test suite went from 78 passed / 1 skipped to 41 failures against
the Sprint-1/2 baseline.

The resolution was a hotfix conftest that restored the Sprint-1/2
fixtures verbatim (`session_id`, `auditor_id`, `_clean_ledger` autouse)
and added `auditor` as an alias for Sprint-3-specific use. Sprint-3
fixtures (ledger, registry) were added additively rather than
replacing anything.

Lesson: test isolation across sprints must be verified by extension,
not by replacement. My initial approach treated the conftest as
owned-by-sprint-3; the correct approach treats it as owned-by-repo
and extended-by-sprint.

### Defect S3.D2 --- HEAD schema incompatibility

My initial Hypothesis factory was written against a hypothesized
schema, not the HEAD-locked Sprint-0 schema. Multiple mismatches
surfaced during integration:

- Factory used `hypothesis_id`; HEAD schema specifies `artifact_id`.
- Factory omitted `artifact_type` and `authority_level`; HEAD schema
  marks both required.
- Factory treated `observation_refs` as optional; HEAD schema
  specifies `minItems: 1`.
- Factory allowed `composite_upstream_bme_score` to be null; HEAD
  schema specifies required, non-nullable, in the range `[0.0, 1.0]`.
- Factory emitted envelopes with a non-HEAD format: no ULID event_id,
  no `actor`/`causal_refs`/`schema_version` fields, no `sha256:`
  hash prefix.

The root cause was that Sprint-3's initialization prompt provided the
directory tree but not the HEAD contents of the Hypothesis schema or
the LedgerEvent envelope schema. I worked from the project
instructions' specification, which was correct in intent but lacked
field-level HEAD fidelity.

Resolution was a full factory rewrite against HEAD. The rewrite cost
approximately two hours of real time and produced a factory that is
now HEAD-compliant across every field.

Lesson: sprint initialization prompts must include the HEAD contents
of every file to be modified. "Here are the directories involved" is
insufficient; the contents matter.

### Defect S3.D3 --- `FsAgentRegistry` adapter, three iterations

The `FsAgentRegistry` adapter needed to expose a session-scoped
read of the agent registry. My first two attempts both failed, and
the failure surfaced only at test-execution time. The three
iterations:

**Iteration 1.** The adapter read the registry file at
`/multiagent/ledger/agent_registry/<agent_id>.json` directly and
compared `artifact.get("session_id")` against the lookup session_id.
The artifact on disk uses `_session_id` (underscore-prefixed meta key),
not `session_id`. The comparison was always `None != session_id`, so
the adapter returned None for every agent. All 23 Sprint-3 tests
failed with the same `UnregisteredAgentError`.

**Iteration 2.** I delegated session scoping to the canonical
`get_agent_identity()` function and read `_session_id` from the
returned dict. The canonical function strips the `_session_id` meta
field on return, a Sprint-1 implementation detail that was not
documented at the function-signature level. The returned dict's
`_session_id` was always None. The same 23 tests failed with the
same error.

**Iteration 3 (shipped).** I wrote a diagnostic probe that called
`register_agent()`, then called `get_agent_identity()` directly,
printed the keys of the returned dict, and compared against the
on-disk registration file. The probe confirmed the meta-field-strip
behavior. The shipped adapter reads the raw registration file for
session scoping via `_session_id` and calls `get_agent_identity()`
only for live status resolution (SUSPENDED/REVOKED markers). It
merges the two reads before returning.

The diagnostic probe was the inflection point. Iterations 1 and 2
both failed in exactly the same way (same exception, same tests,
same error message) and without the probe I would have iterated
further without gaining information. The probe produced a
discriminating output: it showed me that `get_agent_identity()`
returned `_session_id = None` while the on-disk file had
`_session_id = 'SESSION_abcdef01'`. That asymmetry was the clue.

Lesson: when two different adapter implementations produce identical
failure modes against the same test, the next step is not a third
implementation. The next step is a diagnostic probe that reveals
which component is actually returning the unexpected value. I lost
approximately 45 minutes on iteration 2 before recognizing this.

## Decisions I Made

I ratified the chain-minimum ceiling attribution over two alternatives
I considered. The first alternative was per-agent ceiling (use only
the emitting agent's `max_synthesis_depth`). This would have been
simpler but fails the relay adversary model. The second was
weighted-average ceiling across the upstream chain. This would have
produced a softer enforcement gradient but introduces floating-point
ambiguity into a structural enforcement boundary, which violates the
"structural, not procedural" principle I was working toward. The
minimum operator is integer-valued, deterministic, and unambiguously
auditable.

I ratified the path-scoped freeze over session-wide freeze. The
session-wide alternative would have been simpler and would have
provided a stronger forcing function (any depth violation halts all
synthesis in the session). But it would have produced audit evidence
that over-reports enforcement scope: a freeze on one provenance chain
should not imply invalid state on parallel chains that do not depend
on the frozen ancestor. The path-scoped approach produces audit
evidence that exactly matches the enforcement action.

I accepted the revised Decision S3.5 (`composite_upstream_bme_score`
placeholder with payload marker) without resistance once I understood
the HEAD schema constraint. The initial nullable-field proposal was a
Sprint-4-forward optimization that I had made without checking the
Sprint-0 lock. When the lock was confirmed, the placeholder-plus-marker
approach was the immediate fallback that preserves the schema contract
and Sprint-4's ability to populate computed values without schema
modification.

I reserved the Sprint-3 exception additions in the synthesis modules
(`ScopeViolationError`, `FrozenPathError`, `UpstreamResolutionError`,
`HypothesisValidationError`) rather than consolidating them into
`multiagent/exceptions.py`. The rationale was scope discipline:
Sprint-3 touched as few Sprint-1/2 files as possible. The only
Sprint-1/2 code modification in Sprint-3 is the two-line EventType
Literal extension. Consolidating new exception classes into
`multiagent/exceptions.py` would have added another touch for minor
organizational benefit. Sprint-4 can consolidate as a dedicated
tech-debt item.

## What I Would Do Differently

Three things.

First, I should have requested the HEAD contents of the Hypothesis
schema at sprint initialization. The cost would have been one
additional paste in the initialization prompt. The benefit would have
been skipping the full factory rewrite. My initial authoring against
the project instructions' specification was correct in intent but
missed HEAD fidelity. For Sprint-4, I will include a HEAD-contents
pull as part of the initialization discipline.

Second, I should have written the diagnostic probe earlier in the
`FsAgentRegistry` recovery. Iterations 1 and 2 both failed identically,
which is the signature of a hidden assumption that neither
implementation tests. When that pattern repeats, the correct move is
a probe, not a third iteration. I recognized this in retrospect;
Sprint-4 should recognize it at 30 minutes of the same failure mode.

Third, I should have documented the canonical-function meta-field-strip
behavior in Sprint-1. This is more a Sprint-1 retrospective than a
Sprint-3 one, but it is worth noting here because the Sprint-3 defect
is the Sprint-1 omission surfacing. Sprint-4 should scan
`multiagent/orchestrator/agent_lifecycle/registration.py` for any
other undocumented silent transformations on return values before
any new adapter is written.

## Handoff to Sprint-4

Sprint-4 inherits:

- Working Hypothesis runtime with structural Invariant 2 enforcement
- 110 passing tests, 0 skipped
- Six explicitly-recorded Sprint-4 candidate items (see Lab Journal
  entry Outstanding Items at Sprint Close)
- Three process-correction lessons (HEAD-contents at initialization,
  probe-before-third-iteration, canonical-function meta-field audit)

Sprint-4's primary focus is BME attribution: populating
`composite_upstream_bme_score` with computed floats, setting
`bme_score_source: "computed"`, and wiring this into the per-agent
BAR-A / ECPI-A / IQD-A attributions called out in the project
instructions' BME Metric Suite section. Given that Sprint-3 closed
with clean test discipline and established the Hypothesis event
format, Sprint-4 should be able to focus on BME logic without
additional structural sprint work.
