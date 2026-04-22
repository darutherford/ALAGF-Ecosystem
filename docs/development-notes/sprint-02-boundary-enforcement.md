# Sprint-2 Development Notes --- Boundary Enforcement

**Close date:** 2026-04-22
**Close time (local):** 05:56 CDT
**Close commit:** `c03b9ac`

## What I Built

The boundary enforcement runtime. AgentHandoff artifact factory,
BOUNDARY_HANDSHAKE protocol, handoff preconditions with closed-enum
rejection taxonomy, FastAPI endpoints for the handshake and handoff
lifecycle, invariant test extensions, agent boundary tests.

78 tests passed, 1 skipped (the Sprint-3-reserved depth ceiling test).
This was the expected close state.

## Defects Encountered

Sprint-2 ran cleaner than I expected. Two minor defects, both caught and
resolved within the sprint.

### Defect S2.D1 --- `EventType` Literal extension pattern

The Sprint-1 `EventType = Literal[...]` declaration at
`multiagent/ledger/hash_chain/events.py` needed extension for the three
new Sprint-2 event types. I initially considered two approaches: (a)
restructure `EventType` as an Enum class to allow dynamic extension, or
(b) treat the Literal as append-only and extend it in place.

Option (a) would have been cleaner from a Python type-system perspective.
Enum subclasses support `auto()` and iteration; dynamic discovery would
have matched the ContractValidator pattern. But Option (a) would have
forced a breaking change to every Sprint-1 callsite that type-hints
against `EventType`. Option (b) preserved the Sprint-1 contract at the
cost of making each new sprint touch `events.py`.

I chose (b). The choice was pragmatic: Sprint-1 code was already
committed and tested, and the cost of each future sprint touching one
file is bounded. This pattern persisted into Sprint-3, which touched
`events.py` for the same reason.

### Defect S2.D2 --- Rejection taxonomy drift during precondition design

While implementing handoff preconditions, I initially wrote
`rejection_reason` as a free-form string to get the happy-path tests
passing. After writing the first three precondition checks, I realized
the rejection reasons were already drifting (I had used both
`"unregistered_target"` and `"target not registered"` in different code
paths). I stopped, defined the closed enum in the payload schema, and
refactored the three checks to use the enum values. The refactor cost
about 30 minutes; the alternative, committing the free-form strings
and dealing with enum drift in a later sprint, would have been more
expensive.

This became a design principle: any rejection path gets a closed enum
at design time, not at cleanup time. Sprint-3 applied this to
`DEPTH_LIMIT_REACHED` (rejection_reason:
`CHAIN_MINIMUM_CEILING_EXCEEDED`).

## Decisions I Made

I declined to implement `max_synthesis_depth` enforcement in Sprint-2
even though the infrastructure was close. The reasoning was scope
discipline: Sprint-2's primary invariant was Invariant 3
(Evidence-First), and scope-creeping into Sprint-3's primary invariant
(Non-Bypass) would have made Sprint-2's invariant test suite harder to
interpret. The dissertation narrative benefits from each sprint having
a clear primary invariant.

I chose to require explicit handshakes for peer-to-peer handoffs but
not for orchestrator-to-sub-agent handoffs. The alternative, require
handshakes universally, would have added a ledger event to every
handoff in the common case, doubling the event count without adding
audit value. Parent-child registration already establishes the channel
authorization at registration time; requiring an additional handshake
would have been redundant evidence. For peer channels, no prior
registration event establishes authorization, so the handshake is the
only available evidence.

I made `BINDING_PAYLOAD` rejection a Sprint-2 deliverable rather than
deferring it to the Decision sprint. The rationale was defense in
depth: by the time the Decision console exists, the handoff layer will
have had multiple sprints to develop edge cases. Enforcing the
binding-payload rule at the handoff layer now means the Decision
console can rely on the invariant holding at the boundary crossing
regardless of which sprint delivers it. This is architectural pessimism
in the correct direction.

## What I Would Do Differently

One thing.

I should have invested in an integration-test harness that exercises
the full handoff lifecycle end-to-end (register A, register B, handshake
A to B, handoff A to B, handoff B to A rejected for missing reverse
handshake, verify all ledger events) as a single test. The Sprint-2
tests are well-factored into Invariant 1/3/4-specific test modules, but
none of them exercises the full workflow. The cost of adding an
integration test would have been modest. The benefit would have been a
canonical "happy path plus rejections" example that future sprints
could reference when extending the lifecycle. Sprint-3's API tests do
this for Hypothesis emission; Sprint-2 does not do it for handoff.

## Handoff to Sprint-3

Sprint-3 inherits:

- Working AgentIdentity and boundary enforcement runtime
- `EventType` Literal closed at eight types
- Exception taxonomy with `DepthLimitExceededError` reserved but not
  raised
- 78 passing tests, 1 Sprint-3-reserved skip
- The `auditor_id`-header convention, closed-enum rejection pattern,
  and schema plus orchestrator double-enforcement pattern, all three
  ready for Sprint-3 to reuse

Sprint-3's primary invariant is Invariant 2 (Non-Bypass) structural
enforcement. The extension pattern is well established: extend the
`EventType` Literal (single touch), add payload schemas (new files),
add the Sprint-3 exception subclasses, add the Hypothesis factory and
emission runtime, extend invariant tests additively. The known risks
are Sprint-1 meta-field assumptions and any undocumented canonical
function behavior that Sprint-3 adapters would discover by contact.
