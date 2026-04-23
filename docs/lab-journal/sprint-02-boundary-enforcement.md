# Sprint-2: Agent Boundary Enforcement and Handoff Lifecycle

**Sprint identifier:** ECOSYSTEM-SPRINT-2
**Close date:** 2026-04-22
**Close time (local):** 05:56 CDT (10:56 UTC)
**Close commit:** `c03b9ac`
**Primary invariant:** Invariant 3 (Evidence-First). Every inter-agent
boundary crossing is an auditable ledger event with complete provenance,
not an implementation detail.

## Purpose

Sprint-2 operationalized the core governance principle of the multi-agent
extension: agent boundaries are governance boundaries (Rutherford, 2025).
It produced the `AgentHandoff` artifact contract, the `BOUNDARY_HANDSHAKE`
channel protocol, the boundary_enforcement package implementing handoff
and handshake runtime with precondition validation, and the FastAPI
endpoints exposing these primitives. It extended the Sprint-1 invariant
test suite with boundary-specific acceptance tests. Sprint-2 closed with
the full baseline of 78 passing tests, one Sprint-3-reserved skip carried
forward from Sprint-1.

## Strategic Context

Sprint-1 established that every participating agent must be registered
before any output is accepted. Sprint-2 addressed the question that follows
immediately: what happens when a registered agent's output must cross into
another registered agent's scope? Three cases exist in multi-agent
topologies. An orchestrator passes work to a sub-agent. Two peer sub-agents
exchange intermediate results under a validated channel. A validator
reviews output from a peer before it proceeds to the orchestrator. In each
case, the boundary crossing is where governance invariants are most at
risk: Authority can be diluted if a binding artifact transits a
non-binding channel; Evidence-First fails if the crossing leaves no
ledger trace; Reconstructability fails if the boundary handshake exists
only in runtime memory.

Sprint-2's scope was therefore the full lifecycle of authorized boundary
crossings. This scope required three structural decisions documented
below (decisions S2.1, S2.2, S2.3) and produced eleven logical commits
between 05:54:21 and 05:56:16 CDT on 2026-04-22.

## Scope and Deliverables

**LedgerEvent envelope extension.** The `event_type` enum was extended with
`AGENT_HANDOFF`, `BOUNDARY_HANDSHAKE`, and `BOUNDARY_VIOLATION`. This was
the single modification to a Sprint-1 shared schema file; subsequent
sprints would follow this pattern of additive enum extension rather than
envelope restructuring.

**Sprint-2 payload schemas.** Three new payload schemas for the new event
types at `multiagent/ledger/hash_chain/event_schemas/v2/`: handoff,
handshake, and violation. Each declares a `rejection_reason` enum where
applicable, ensuring that Invariant-3 violations produce machine-verifiable
audit evidence, not free-form strings.

**Exception taxonomy extension.** Two new subclasses of `ALAGFError`:
`BoundaryViolationError` for precondition failures in the handoff pipeline,
and `HandshakeError` for channel protocol violations. Both follow the
Sprint-1 emit-before-raise discipline: the orchestrator writes a
`BOUNDARY_VIOLATION` event before raising.

**AgentHandoff factory.** The `build_agent_handoff()` function at
`multiagent/artifacts/AgentHandoff/__init__.py` follows the Sprint-1
factory template: schema enforces `non_authoritative_flag: const: true`,
factory raises `AuthorityViolationError` on any override attempt. The
`authority_level` field is hard-coded to `"orchestration"` on every
handoff; handoffs move artifacts, they do not produce binding outcomes.

**boundary_enforcement package.** Two submodules at
`multiagent/orchestrator/boundary_enforcement/`: `handshake.py` and
`handoff.py`. The handshake module implements directional channel
establishment between registered ACTIVE agents within a single session;
the handoff module implements full precondition validation with a
closed-enum rejection taxonomy (`CROSS_SESSION`, `SOURCE_INACTIVE`,
`TARGET_INACTIVE`, `TARGET_UNREGISTERED`, `UNKNOWN_PAYLOAD`,
`BINDING_PAYLOAD`, `MISSING_HANDSHAKE`, `SELF_HANDOFF`). Each rejection
emits a `BOUNDARY_VIOLATION` event before raising the appropriate
exception.

**FastAPI endpoints for handoff and handshake lifecycle.** Eight new
endpoints extending the Sprint-1 auditor header convention.

**Invariant acceptance test extensions.** Four test modules extended with
Sprint-2 sections: boundary-specific Invariant 1 enforcement (binding
payload rejection, handoff authority flag hardcoding), boundary-specific
Invariant 3 enforcement (handoff evidence chains, cross-session rejection,
inactive-agent rejection), boundary-specific Invariant 4 enforcement
(handoff chain reconstruction from ledger alone, emit-before-raise
verification, hash chain integrity across mixed event types). The
Sprint-1 baseline of 40 passing tests was preserved; Sprint-2 added 38
tests for a total of 78 passing, 1 skipped.

## Design Decisions

Sprint-2 resolved three decisions that Sprint-3 would inherit.

**Decision S2.1. Handshake required for peer-to-peer handoffs; implicit
for orchestrator-to-sub-agent.** Two registered agents of peer status
(SUB_AGENT to SUB_AGENT, or VALIDATOR to peer VALIDATOR) require an
explicit `BOUNDARY_HANDSHAKE` event before any `AGENT_HANDOFF` is accepted
between them. The alternative (allowing any two registered agents to
exchange artifacts without channel establishment) would have left peer
channels with no ledger evidence of authorization, violating Invariant 3.
Orchestrator-to-sub-agent handoffs do not require a handshake because the
parent-child registration relationship already establishes channel
authorization at registration time. This decision was recorded in the
Sprint-2 changelog as the handshake directionality rule.

**Decision S2.2. `BINDING_PAYLOAD` rejection at the handoff layer.** A
payload artifact whose declared `authority_level` is `"binding"` cannot
transit an agent boundary via `AGENT_HANDOFF`. The rationale is Invariant
1: binding artifacts are produced only by human Decisions and deterministic
controller rules. If a binding artifact could cross agent boundaries via
orchestration, the boundary itself would become a vector for authority
inflation; a sub-agent could receive a binding payload and treat it as
input to its own non-binding output pipeline, blurring authority lines.
The handoff layer rejects with `BINDING_PAYLOAD` before the crossing
completes. Binding artifacts cross agent scope only through the human
Decision Console (future sprint).

**Decision S2.3. Closed-enum rejection reasons on `BOUNDARY_VIOLATION`.**
The `rejection_reason` field on every `BOUNDARY_VIOLATION` event is a
closed enum. Free-form strings were rejected because machine-verifiable
audit requires that every rejection map to a known category, and human
auditors reviewing ledger evidence need to distinguish (for example)
`CROSS_SESSION` from `TARGET_UNREGISTERED` without parsing prose. The
closed-enum approach also prevents drift: a future sprint cannot quietly
introduce a new rejection category without updating the schema.

## Invariant Enforcement Status at Sprint Close

- **Invariant 1 (Authority):** Enforced at the AgentHandoff factory layer
  (`non_authoritative_flag` override rejection) and at the handoff
  precondition layer (`BINDING_PAYLOAD` rejection). Cumulative with
  Sprint-1 enforcement at AgentIdentity.
- **Invariant 2 (Non-Bypass):** Unchanged from Sprint-1.
  `max_synthesis_depth` persists; structural enforcement remains deferred
  to Sprint-3.
- **Invariant 3 (Evidence-First):** Substantially advanced. Every
  successful `AGENT_HANDOFF` carries registered source and target
  identifiers and a payload artifact reference. Every precondition failure
  produces a `BOUNDARY_VIOLATION` event with a closed-enum rejection
  reason before the exception is raised. Peer channels are established
  via explicit `BOUNDARY_HANDSHAKE` events, creating ledger evidence of
  channel authorization.
- **Invariant 4 (Reconstructability):** Substantially advanced. Given only
  the event log, the full handoff chain for a session (including which
  artifacts transited which boundaries, when, and between which
  registered agents) is reconstructible by pure ledger derivation. Hash
  chain integrity verification extends across the mixed event-type
  sequence (`AGENT_REGISTERED` plus `BOUNDARY_HANDSHAKE` plus
  `AGENT_HANDOFF`).

## Outstanding Items at Sprint Close

One item was recorded:

1. **Invariant 2 structural enforcement remains deferred.** Sprint-2
   did not address `max_synthesis_depth` runtime enforcement; this was
   Sprint-3's primary invariant. The deferral was explicit in the
   Sprint-2 changelog.

## Novel Contribution Indicators

Sprint-2 produced one architectural contribution worth noting for the
dissertation: the closed-enum rejection taxonomy for boundary violations.
Existing multi-agent orchestration frameworks commonly implement boundary
enforcement as runtime assertions with free-form error messages (for
example, CrewAI, AutoGen). The closed-enum approach aligns with ISO/IEC
42001:2023 clause 9.1 monitoring and measurement requirements (ISO,
2023) by ensuring that every boundary rejection produces audit evidence
in a known category. This approach is a candidate for formalization in
the dissertation's standards-alignment section.

The methodological novelty (the claim that agent boundaries are
governance boundaries and must produce ledger evidence) was articulated
in the project's core governance principle. Sprint-2 is the architectural
implementation of that principle.

## References

International Organization for Standardization. (2023). *Information
technology. Artificial intelligence. Management system* (ISO/IEC 42001:2023).

Rutherford, D. (2025). *The Adaptive Lifecycle Agentic Governance Framework*
[Unpublished manuscript]. University of Arkansas at Little Rock.
