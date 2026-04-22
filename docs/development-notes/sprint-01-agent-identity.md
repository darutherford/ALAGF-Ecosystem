# Sprint-1 Development Notes --- AgentIdentity Lifecycle

**Close date:** 2026-04-21
**Close time (local):** 07:02 CDT
**Close commit:** `c511ba8`

## What I Built

The AgentIdentity runtime. Exception taxonomy, envelope and payload schemas,
ContractValidator, factory with runtime Invariant 1 enforcement, append-only
hash-chained ledger writer, lifecycle orchestrator with filesystem registry,
FastAPI endpoints, test suite.

40 tests passed, 1 skipped at close. The skipped test
(`test_depth_ceiling_emits_depth_limit_reached_event`) carried a rationale
string declaring it reserved for Sprint-3.

## Defects Encountered

One defect surfaced during Sprint-1 that had downstream implications I did
not fully understand at the time.

### Defect S1.D1 --- `get_agent_identity()` strips meta fields on return

The canonical lookup function at
`multiagent/orchestrator/agent_lifecycle/registration.py` reads the
registration file at `/multiagent/ledger/agent_registry/<agent_id>.json`,
but strips the underscore-prefixed meta fields (`_session_id`,
`_registration_event_id`) from the returned dict before handing it to the
caller. The rationale at the time was: these are meta fields used by the
lifecycle orchestrator internally, not part of the AgentIdentity contract.
Callers should work against the AgentIdentity schema, not meta-enriched
variants.

I did not document this stripping behavior anywhere. It was an implicit
contract of the lookup function.

This became a Sprint-3 integration defect. The Sprint-3 `FsAgentRegistry`
adapter initially tried to delegate session scoping to
`get_agent_identity()` by reading `_session_id` from the returned artifact.
The field was always None. Sprint-3 required three adapter iterations
before I correctly identified the cause via a diagnostic probe. See
`sprint-03-integration-notes.md`, Defect S3.D3 for the full recovery.

## Decisions I Made

I built the exception taxonomy as a tree rooted at `ALAGFError` rather than
using raw `Exception` subclasses. The cost was minor (one base class file);
the benefit was that callers can catch `ALAGFError` as a wildcard for any
ALAGF-origin failure, or catch specific subclasses for targeted recovery.
This pattern paid off immediately in the ledger writer, which catches
`ArtifactValidationError` and converts it into an `UNREGISTERED_AGENT_OUTPUT`
event before re-raising.

I chose the marker-file registry pattern over in-place mutation of the
registration file. The cost is a proliferation of marker files for any agent
that transitions status more than once. The benefit is append-only
discipline at the filesystem level and trivial reconstruction of status
history by filename scan. Given that Invariant 4 is architectural, and the
demo v1 prototype had already established append-only ledger discipline,
extending that discipline to the registry was the defensible choice.

I reserved `DepthLimitExceededError` in Sprint-1 without raising it. This
was forward-looking: Sprint-3 would implement the structural depth ceiling,
and defining the class now meant Sprint-3's implementation could reference
an existing taxonomy entry rather than introducing a new class at the point
of use. When Sprint-3 needed kwargs on the exception, it subclassed rather
than modified, which preserved the Sprint-1 isinstance contract for any
code that might catch the base class.

## What I Would Do Differently

Two things.

First, I should have documented the meta-field-stripping behavior of
`get_agent_identity()` at the function signature level, not just in the
implementation. A docstring line like "Returns the AgentIdentity artifact
with meta fields (`_session_id`, `_registration_event_id`) removed" would
have prevented the Sprint-3 adapter defect entirely. The cost of the
docstring is trivial. The cost of three adapter iterations in Sprint-3 was
approximately one hour of real time plus cognitive overhead.

Second, I should have given the lookup function a docstring section listing
every meta field the registration file contains and whether each is
preserved on return. Three meta fields exist on disk:
`_registration_event_id`, `_session_id`, and implicitly the status markers
via filename convention. The return dict preserves status (computed from
markers) but strips the other two. This asymmetry is surprising. The
docstring should have said so explicitly.

## Handoff to Sprint-2

Sprint-2 inherits:

- Working AgentIdentity runtime
- Exception taxonomy with room for boundary-specific additions
- Append-only ledger with `EventType` Literal closed at five event types
- Registry with marker-file status transitions
- FastAPI endpoint convention (auditor header, 401/403 semantics)
- 40 passing tests, 1 Sprint-3-reserved skip

Sprint-2 will extend the `EventType` Literal with boundary-crossing event
types (`AGENT_HANDOFF`, `BOUNDARY_HANDSHAKE`, `BOUNDARY_VIOLATION`), add
`BoundaryViolationError` and `HandshakeError` to the exception taxonomy,
and introduce the boundary_enforcement package. The Sprint-1 foundation
should accommodate this without modification to Sprint-1 code; the
`EventType` extension is the single unavoidable touch.
