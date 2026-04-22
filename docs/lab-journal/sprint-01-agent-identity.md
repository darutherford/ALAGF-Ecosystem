# Sprint-1: AgentIdentity Lifecycle and Ledger Foundation

**Sprint identifier:** ECOSYSTEM-SPRINT-1
**Close date:** 2026-04-21
**Close time (local):** 07:02 CDT
**Close commit:** `c511ba8`
**Primary invariant:** Invariant 1 (Authority). Runtime enforcement of the
`non_authoritative_flag` hard-coding across the AgentIdentity artifact and
its registration lifecycle.

## Purpose

Sprint-1 transformed the Sprint-0 scaffold into a functioning governance
runtime for AgentIdentity. It produced the exception taxonomy, the JSON
Schema formalization of AgentIdentity and its ledger event envelope, the
append-only hash-chained ledger writer, the agent lifecycle orchestrator
(registration, suspension, revocation), and the FastAPI endpoints that expose
this lifecycle to human auditors. Sprint-1 is the first sprint in which
ALAGF invariants are enforced architecturally rather than scaffolded.

## Strategic Context

AgentIdentity is the architectural foundation of the multi-agent extension.
The core governance principle of the extension, that agent boundaries are
governance boundaries (Rutherford, 2025), requires that every participating
agent be registered before any output from that agent is accepted into the
ledger. Registration therefore precedes all other session events. If
registration fails or is bypassed, the remaining invariants become
unenforceable: Authority cannot be verified without a registered identity;
Evidence-First cannot trace provenance without a registered source;
Non-Bypass cannot reject delegation without a registered authority scope;
Reconstructability cannot reconstruct session history without a registered
participant manifest.

Sprint-1's scope was therefore the lifecycle primitives on which all
subsequent sprints depend. Sprint-2 would build boundary enforcement on this
foundation. Sprint-3 would build Hypothesis runtime on this foundation.
Every multi-agent sprint rests on Sprint-1.

## Scope and Deliverables

Sprint-1 produced ten logical units, committed in sequence between 07:01:46
and 07:02:55 CDT:

**Exception taxonomy.** The root `ALAGFError` class and eight subclasses
establishing a typed exception hierarchy consistent with the no-silent-failure
requirement of Invariant 4. Sprint-1 introduced `AgentRegistrationError`,
`UnregisteredAgentError`, and `LedgerIntegrityError`; it also reserved
`DepthLimitExceededError` for Sprint-3 structural enforcement and
`ArtifactValidationError` and `AuthorityViolationError` for v1 parity.

**LedgerEvent envelope and event payload schemas.** The v2 envelope schema at
`multiagent/ledger/hash_chain/event_schemas/v2/LedgerEvent.envelope.schema.json`
defines the self-describing ledger event structure: ULID-prefixed event
identifiers, SHA-256 hash chaining via `prev_hash`, canonical actor types
(HUMAN, AGENT, ORCHESTRATOR), and causal reference slots for prior events
and referenced artifacts. Payload schemas for `AGENT_REGISTERED`,
`AGENT_SUSPENDED`, `AGENT_REVOKED`, `AGENT_SESSION_REGISTRY`, and
`UNREGISTERED_AGENT_OUTPUT` were delivered alongside the envelope.

**ContractValidator.** A thin wrapper over the `jsonschema` library that
loads schemas from `/shared/artifact-contracts/v2/` and
`/multiagent/ledger/hash_chain/event_schemas/v2/` by filename convention.
This module is the single compilation point for JSON Schema validation,
consistent with Precondition 1 (schemas as single source of truth). It
auto-discovers payload schemas by filename stem, which later enabled
Sprint-2 and Sprint-3 to add new event types without modifying this module.

**AgentIdentity factory.** The `build_agent_identity()` function constructs
and validates an AgentIdentity artifact with runtime enforcement of
Invariant 1. The schema's `const: true` declaration on
`non_authoritative_flag` ensures `ArtifactValidationError` on any literally
false input; the factory additionally raises `AuthorityViolationError` on
any non-true value to distinguish Invariant-1 breaches from general schema
failures. This double-enforcement pattern became the template for Sprint-3's
Hypothesis factory.

**Append-only hash-chained ledger writer.** The `append_event()` function at
`multiagent/ledger/hash_chain/events.py` writes session events to disk with
`O_CREAT | O_EXCL` semantics, enforcing append-only discipline at the
filesystem level. Events are written under
`/multiagent/ledger/hash_chain/sessions/<session_id>/<sequence>_<event_id>.json`
with a `_chain_head.json` index for fast sequence-number lookup. Hash chain
verification happens on read via `read_session_events()`. Tampering with any
committed event produces `LedgerIntegrityError` on replay.

**Agent lifecycle orchestrator.** The `register_agent()`, `suspend_agent()`,
`revoke_agent()`, `get_agent_identity()`, and `reject_unregistered_output()`
functions at `multiagent/orchestrator/agent_lifecycle/registration.py`. These
enforce lifecycle invariants above the schema layer: `auditor_id` must match
the `AUDITOR_[A-Z0-9_]+` pattern (stricter than the v2 schema requires);
`registered_by` cannot resolve to an agent_id; parent references must exist
for SUB_AGENT and VALIDATOR types; revocation is terminal. Registry files
live at `/multiagent/ledger/agent_registry/` with append-only status
transitions via marker files (`<agent_id>__SUSPENDED__<event_id>.json` and
`<agent_id>__REVOKED__<event_id>.json`). The registration file itself is
never modified; status is computed.

**FastAPI endpoints.** Ten endpoints exposing the lifecycle to human
auditors, with the auditor header convention (401 for missing
`X-Auditor-Id`, 403 for malformed) that Sprint-2 and Sprint-3 would inherit.

**Invariant acceptance tests.** Four test modules, `test_authority.py`,
`test_non_bypass.py`, `test_evidence_first.py`, `test_reconstructability.py`,
establishing the baseline acceptance suite. One Sprint-3-reserved test
(`test_depth_ceiling_emits_depth_limit_reached_event`) was marked skipped
with an explicit rationale string. Sprint-1 closed with 40 tests passing and
1 skipped.

**Documentation.** README update for `/multiagent/`, `sprint-1-changelog.md`,
and the Sprint-0 reconciliation note carried forward.

## Design Decisions

Sprint-1 surfaced three decisions that shaped subsequent sprints.

**Decision S1.1. Orchestrator-layer `auditor_id` pattern enforcement.** The
v2 AgentIdentity schema accepts `registered_by` as any string. The
orchestrator layer enforces a stricter pattern (`AUDITOR_[A-Z0-9_]+`) before
calling the factory. This stacked enforcement is deliberate: the schema
defines the contract for persistence and interchange, while the orchestrator
defines the contract for session admission. Violating either raises a typed
exception. This pattern (schema plus orchestrator double-layer) became the
architectural template for all subsequent sprints.

**Decision S1.2. Registry status computed from marker files, not mutated.**
Agent status transitions (ACTIVE to SUSPENDED to REVOKED) produce marker
files; the original registration file is never modified. This preserves
append-only discipline at the registry layer and allows Invariant 4-compliant
reconstruction of any agent's status history from the filesystem alone. The
alternative (mutating the registration file's `status` field) would have
violated append-only discipline and made historical status reconstruction
require event-log scanning.

**Decision S1.3. `DepthLimitExceededError` reserved but not raised.** The
class is defined in Sprint-1's exception taxonomy with a docstring declaring
it reserved for Sprint-3 structural enforcement. This forward-declaration
prevented Sprint-3 from needing to retrofit an exception taxonomy that
Sprint-1 had already committed to. When Sprint-3 needed to extend the class
with diagnostic attributes, it subclassed rather than modified, preserving
the Sprint-1 isinstance contract.

## Invariant Enforcement Status at Sprint Close

- **Invariant 1 (Authority):** Enforced at the AgentIdentity factory layer.
  `non_authoritative_flag` override attempts raise
  `AuthorityViolationError`. Enforced at the orchestrator layer via
  `auditor_id` pattern matching and `registered_by != agent_id` checks.
- **Invariant 2 (Non-Bypass):** Partially prepared. `max_synthesis_depth`
  persists unmodified through registration and is retrievable via
  `get_agent_identity()`. Structural enforcement deferred to Sprint-3.
- **Invariant 3 (Evidence-First):** Enforced at the ledger event layer. Every
  `AGENT_REGISTERED` event carries `auditor_id`, `session_id`, and a HUMAN
  actor type. Every `AGENT_SUSPENDED` and `AGENT_REVOKED` event carries
  `causal_refs.prior_event_id` pointing to the original registration event.
- **Invariant 4 (Reconstructability):** Enforced. Given only the session's
  event log, the ACTIVE agent set at any point in time is reconstructible
  via pure ledger derivation. Hash-chain tampering is detected on replay.
  Every error condition produces a ledger event before the exception is
  raised (emit-before-raise discipline).

## Outstanding Items at Sprint Close

Two items were recorded as sprint-transition-noted:

1. **Hypothesis v2 schema missing `source_agent_id` field.** Carried forward
   from Sprint-0. Documented in the Sprint-1 changelog as blocking Sprint-4
   (BME attribution) but not Sprint-2 or Sprint-3. Resolved in Sprint-3 via
   the `bme_score_source` payload marker approach, which does not require
   schema modification.
2. **Integration sequencing with Sprint-0 remediation.** Sprint-1 inherited
   two remediation tasks from Sprint-0 (gitignore additions for scratch
   files, `demo/ledger/` declaration as out-of-scope). Both were completed
   in Sprint-1's first commit sequence before any AgentIdentity work
   began.

## Novel Contribution Indicators

Sprint-1 produced no novel methodological contribution at the framework
level. Its contribution is architectural: the schema plus orchestrator
double-enforcement pattern for Invariant 1, and the append-only marker-file
registry pattern for status transitions. Both are standards-consistent
implementations of ISO/IEC 42001:2023 lifecycle management requirements
(International Organization for Standardization [ISO], 2023) applied to
multi-agent AI governance.

The Sprint-1 foundation is what makes the Sprint-3 novel contribution
(chain-minimum ceiling attribution) implementable. Without registered
agents and persisted `max_synthesis_depth` values, the chain-minimum
computation has no data to operate on.

## References

International Organization for Standardization. (2023). *Information
technology. Artificial intelligence. Management system* (ISO/IEC 42001:2023).

Rutherford, D. (2025). *The Applied Lifecycle AI Governance Framework*
[Unpublished manuscript]. University of Arkansas at Little Rock.
