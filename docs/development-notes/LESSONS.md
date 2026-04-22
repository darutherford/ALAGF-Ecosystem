# ALAGF-Ecosystem Cross-Sprint Process Corrections

**Purpose.** Aggregator of engineering lessons that generalize beyond
any single sprint. Each lesson is derived from a specific defect or
recovery pattern in the sprint notes and stated as a process correction
for future sprints.

**Audience.** Future sprint execution. Read this file at the start of
every sprint initialization.

## Lesson Index

| ID | Lesson | Origin | Ratified |
|---|---|---|---|
| L1 | `.gitignore` discipline precedes any working-artifact generation | S0.D1 | Sprint-1 |
| L2 | Reserve forward-looking exception classes in the taxonomy early | Sprint-1 design | Sprint-1 |
| L3 | Introduce closed-enum rejection taxonomies at design time, not cleanup time | S2.D2 | Sprint-2 |
| L4 | Test conftest is owned by repo, extended by sprint; never replaced | S3.D1 | Sprint-3 |
| L5 | Sprint initialization prompts must include HEAD contents of every file to be modified | S3.D2 | Sprint-3 |
| L6 | When an adapter delegates to a canonical function, document which meta fields are preserved and which are stripped | S1.D1, S3.D3 | Sprint-3 |
| L7 | When two adapter iterations fail identically, the next step is a diagnostic probe, not a third iteration | S3.D3 | Sprint-3 |
| L8 | Sprints that extend existing code generate more integration defects than sprints that create net-new code | Defect density observation | Sprint-3 |

---

## L1. `.gitignore` discipline precedes any working-artifact generation

**Origin.** S0.D1. During Sprint-0 schema extraction, diagnostic dumps
and Office lock files were generated in `/shared/artifact-contracts/`
without corresponding `.gitignore` entries. These files then appeared
in every `git status` run through Sprint-1 planning, creating signal
noise.

**Correction.** Before generating any working artifact (diagnostic
dump, scratch file, temporary output), update `.gitignore` to exclude
the artifact category. The cost of the `.gitignore` entry is
negligible. The cost of cleaning up tracked pollution later is larger,
especially if the pollution enters commits before it is noticed.

**Process hook.** Sprint initialization checklist item: review
`.gitignore` against the categories of files the sprint will generate.

---

## L2. Reserve forward-looking exception classes in the taxonomy early

**Origin.** Sprint-1 design. `DepthLimitExceededError` was defined in
Sprint-1 with a docstring declaring it reserved for Sprint-3 structural
enforcement. Sprint-3 subclassed rather than introducing a new class,
preserving the Sprint-1 isinstance contract.

**Correction.** When a future sprint will introduce a typed exception,
reserve the class in the earliest sprint that defines the relevant
exception taxonomy. The future sprint can then extend with kwargs or
diagnostic attributes via subclassing without modifying the parent
class.

**Counter-example.** The Sprint-3 additions (`ScopeViolationError`,
`FrozenPathError`, `UpstreamResolutionError`,
`HypothesisValidationError`) were not reserved in Sprint-1 because
they were not anticipated at Sprint-1 design time. Sprint-4 is
scheduled to consolidate these into `multiagent/exceptions.py`. This
consolidation is a Sprint-4 tech-debt item, recorded in the Sprint-3
changelog.

---

## L3. Introduce closed-enum rejection taxonomies at design time

**Origin.** S2.D2. During Sprint-2 handoff precondition implementation,
I initially used free-form strings for `rejection_reason` values.
Within three preconditions, the strings had already drifted
(`"unregistered_target"` vs `"target not registered"`).

**Correction.** Any rejection path gets a closed enum at design time,
not at cleanup time. The enum is declared in the payload schema before
the first rejection path is implemented. The schema validation then
enforces the taxonomy at ledger-write time.

**Rationale.** Machine-verifiable audit requires that every rejection
map to a known category. Human auditors need to distinguish
`CROSS_SESSION` from `TARGET_UNREGISTERED` without parsing prose.
Closed enums also prevent silent addition of new rejection categories
in later sprints.

---

## L4. Test conftest is owned by repo, extended by sprint

**Origin.** S3.D1. Sprint-3's initial deliverable included a
`conftest.py` that replaced the Sprint-1/2 version, breaking 41 tests
via fixture-name mismatch.

**Correction.** The conftest is a shared-surface file, treated with
the same discipline as any shared schema: owned by the repo, extended
by each sprint, never replaced. Sprint additions to fixtures go under
clear delimiter comments preserving all prior fixture definitions
verbatim.

**Generalization.** This discipline applies to every shared-surface
file: `.gitignore`, shared schemas under `/shared/artifact-contracts/`,
the top-level `README.md`, the EventType Literal at
`multiagent/ledger/hash_chain/events.py`. Sprint work extends these
files; it does not replace them.

---

## L5. Sprint initialization prompts must include HEAD contents

**Origin.** S3.D2. Sprint-3's initialization prompt provided the
directory tree and the intent specifications but did not include the
HEAD contents of the Hypothesis schema or the LedgerEvent envelope
schema. The initial factory was authored against hypothesized schemas
and required a full rewrite at integration time.

**Correction.** Sprint initialization prompts include, by default, the
full HEAD contents of:

1. Every shared schema the sprint will touch.
2. Every Sprint-1/2 code file the sprint will modify.
3. The HEAD contents of any canonical function an adapter in the
   sprint will delegate to (see L6 for the rationale).

**Cost.** The initialization prompt grows by a factor of 2-5x for
sprints that extend existing code. This cost is lower than the cost
of a mid-sprint factory rewrite. Sprint-3's rewrite cost
approximately two hours of real time; the additional paste at
initialization would have cost five minutes.

**When not to apply.** Sprints that create exclusively net-new files
(like Sprint-1) do not need HEAD contents of Sprint-0 files beyond
the shared schemas they will consume. The rule scales to sprint
scope.

---

## L6. Document meta-field preservation in canonical-function docstrings

**Origin.** S1.D1 and S3.D3. Sprint-1's `get_agent_identity()`
silently strips `_session_id` and `_registration_event_id` meta
fields before returning. The stripping was an implicit contract not
documented at the function signature level. The Sprint-3
`FsAgentRegistry` adapter required three iterations because neither
the shipped Sprint-3 adapter (iteration 1) nor the canonical-delegation
adapter (iteration 2) correctly accounted for this behavior.

**Correction.** When a canonical function transforms its return value
relative to the on-disk representation (strips fields, computes
derived values, filters by status), the docstring explicitly lists:

1. Every field that exists on disk.
2. Every field preserved on return.
3. Every field stripped or transformed on return, with the reason.

**Example of sufficient docstring language.**

> Returns the AgentIdentity artifact with live status resolved from
> marker files. The on-disk registration file contains these meta
> fields prefixed with underscore: `_session_id`,
> `_registration_event_id`. These fields are stripped on return
> because they are orchestrator-internal and not part of the
> AgentIdentity schema. Callers requiring session scoping must read
> the raw registration file directly.

**Process hook.** Sprint-4 will audit
`multiagent/orchestrator/agent_lifecycle/registration.py` for any
other undocumented silent transformations before any new adapter is
written.

---

## L7. Two identical adapter failures warrant a diagnostic probe

**Origin.** S3.D3. Sprint-3's `FsAgentRegistry` adapter iterations 1
and 2 both failed with identical `UnregisteredAgentError` messages
against the same test. I wrote a third iteration before recognizing
the pattern; in retrospect, I should have written a diagnostic probe
at the end of iteration 1.

**Correction.** When an adapter fails, and a revised adapter fails in
exactly the same way (same exception, same tests, same error
message), the next step is not a third iteration. The next step is a
diagnostic probe that reveals which component is returning the
unexpected value.

**Diagnostic probe template.** The probe I eventually wrote:

1. Register an agent via the canonical registration function.
2. Print the return value and flag its key set.
3. Call the canonical lookup function with the returned agent_id.
4. Print the lookup return value and its key set.
5. Read the on-disk file directly and print its key set.
6. Compare the three key sets.

The probe produced a discriminating output: two different key sets
for the same underlying data, which pointed directly at the
canonical-function meta-field strip.

**Time cost.** The probe took approximately 15 minutes to write and
run. Iteration 2 cost approximately 45 minutes before I recognized
the pattern. The probe-first discipline would have saved 30 minutes
on this specific defect.

---

## L8. Extension-dense sprints surface more defects than net-new sprints

**Origin.** Defect density observation across Sprints 0-3. Sprints
that extend existing code (Sprint-3) generate more integration
defects than sprints that create net-new code (Sprint-1).

**Observation, not correction.** This is a planning heuristic, not a
process rule. Sprints that will extend Sprint-0 shared contracts,
Sprint-1 exception taxonomies, or Sprint-2 ledger conventions should
budget for integration defects and schedule diagnostic probes as
first-class work items.

**Practical implication for Sprint-4.** Sprint-4 extends the
Hypothesis payload with BME score computation and extends the
exception taxonomy via consolidation. Both are extension work. Sprint-4
should budget for integration defects at roughly Sprint-3 density,
not Sprint-1 density. This is the planning assumption going in.

---

## Lesson Maintenance

Lessons are ratified when the originating defect is resolved and the
process correction is demonstrably applicable to at least one future
sprint. Each new lesson gets an ID, an origin reference, and a
ratification sprint. Lessons are never deleted; if a lesson is
superseded, the superseding lesson references the prior ID and
explains the change.

Review this file at the start of every sprint initialization. The
reviewer should ask: does any lesson in this file apply to the
upcoming sprint, and is the process correction accounted for in the
sprint plan?
