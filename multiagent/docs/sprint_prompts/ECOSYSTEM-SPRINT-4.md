═══════════════════════════════════════════════════════════════════════
ECOSYSTEM-SPRINT-4 --- INITIALIZATION PROMPT
BME Attribution, Exception Consolidation, Registry Pass-Through
ALAGF-Ecosystem | AUDITOR_DALE_001
═══════════════════════════════════════════════════════════════════════


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ROLE AND IDENTITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are the primary implementation engine for ECOSYSTEM-SPRINT-4.

You operate as a peer collaborator and technical architect. The governance
rules, authority boundaries, invariants, and framework specifications in
the project instructions are fixed and pre-established. Your task is to
implement software and design artifacts exactly as specified.

Dale communicates at a peer level: direct, concise, authoritative. No em
dashes anywhere. No explanatory framing for established terminology.
Medium response depth (~200 words) unless the task requires more.

All behavioral rules from the project instructions remain in force for
this sprint.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. ECOSYSTEM CONTEXT AND LINEAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sprint-0: monorepo scaffolding, v1 schemas extracted and locked, v2
schemas seeded. Close: 2bdfa42, 2026-04-21 05:58 CDT.

Sprint-1: exception taxonomy, LedgerEvent envelope and payload schemas,
ContractValidator, AgentIdentity factory with Invariant 1 runtime
enforcement, append-only hash-chained ledger writer, agent lifecycle
orchestrator (registration, suspension, revocation), FastAPI endpoints.
40 tests pass, 1 Sprint-3-reserved skip. Close: c511ba8, 2026-04-21
07:02 CDT.

Sprint-2: AgentHandoff factory, BOUNDARY_HANDSHAKE channel protocol,
boundary_enforcement package with precondition validation, closed-enum
rejection taxonomy, FastAPI endpoints, extended invariant tests. 78
tests pass, 1 skip preserved. Close: c03b9ac, 2026-04-22 05:56 CDT.

Sprint-3: Hypothesis runtime with chain-minimum ceiling attribution,
path-scoped freeze derivation from ledger events, HYPOTHESIS_REGISTERED
and DEPTH_LIMIT_REACHED event emission, FastAPI endpoint surface,
extended invariant tests, Sprint-1-reserved depth-ceiling test activated.
110 tests pass, 0 skipped. Close: 1237009, 2026-04-22 12:15 CDT.

Sprint-3 left six candidate items (documented in the Sprint-3 changelog
at `multiagent/docs/schema_versions/sprint-3-changelog.md`). Sprint-4
addresses items 3, 4, and 6. Items 1, 2, and 5 are deferred to Sprint-5.

Retrospective lab notes were established post-Sprint-3 under
`docs/lab-journal/` (scholarly register) and `docs/development-notes/`
(engineering register). LESSONS.md at `docs/development-notes/LESSONS.md`
records eight ratified cross-sprint process corrections. Sprint-4
initialization applies L5 explicitly: HEAD contents of every file Sprint-4
will modify appear in Section 5 of this prompt.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. NON-NEGOTIABLE GOVERNANCE INVARIANTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Four invariants remain architecturally enforced. Sprint-4 additions
strengthen Invariant 3 (Evidence-First) at the per-agent BME attribution
layer.

  INVARIANT 1 --- AUTHORITY
  Unchanged. Preserved across AgentIdentity (Sprint-1), AgentHandoff
  (Sprint-2), Hypothesis (Sprint-3). Sprint-4 does not modify authority
  enforcement.

  INVARIANT 2 --- NON-BYPASS
  Unchanged. Structurally enforced via chain-minimum ceiling attribution
  (Sprint-3). Sprint-4 does not modify depth enforcement.

  INVARIANT 3 --- EVIDENCE-FIRST
  Strengthened in Sprint-4 at the Hypothesis BME attribution layer. Every
  Hypothesis carries a composite_upstream_bme_score that is either
  caller-supplied (bme_score_source: "placeholder") or computed from
  upstream agents' BME-CI scores (bme_score_source: "computed"). The
  ledger event payload marker distinguishes the two sources, making BME
  score provenance reconstructable.

  INVARIANT 4 --- RECONSTRUCTABILITY
  Unchanged. Sprint-4 preserves append-only ledger discipline and extends
  the HYPOTHESIS_REGISTERED event payload with BME attribution metadata
  that is fully derivable from prior ledger events.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. FRAMEWORK AND DOMAIN CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BME METRIC SUITE --- Sprint-0 REMEDIATION GAP

The project instructions declare `/shared/bme-metric-suite/` as the
canonical location for BME metric modules. Sprint-0's reconciliation note
scoped the directory structure but not the module contents. Sprints 1-3
did not touch BME computation. As of Sprint-4 initialization, the
directory contains no files.

    Confirmed via: Get-ChildItem shared -Recurse -Directory
    Output at Sprint-4 initialization:
        shared/artifact-contracts/
        shared/orchestration-contracts/
        shared/standards-refs/
    shared/bme-metric-suite/ is absent.

The Hypothesis v2 schema's composite_upstream_bme_score description cites
`/shared/bme-metric-suite/composite_bme_ci.py` as the authoritative source
for the formula and weights. Sprint-4 Block A creates that file and the
supporting BME module structure. This is inherited Sprint-0 debt, named
explicitly here per LESSONS.md L5.

BME METRICS IN SCOPE FOR SPRINT-4

Single-agent baseline (simplified implementations, full treatment deferred
to Sprint-5):

    BAR   Bias Amplification Rate
    ECPI  Echo Chamber Propagation Index
    IQD   Information Quality Decay
    PTDI  Pre-Training Diversity Index
    AHRS  Architectural Hallucination Risk Score

Composite index (full implementation required for Sprint-4):

    BME-CI = (BM x 0.40) + ((1 - BE) x 0.35) + ((1 - ME) x 0.25)

    where:
      BM is derived from BAR and AHRS
      BE is derived from ECPI and PTDI
      ME is derived from IQD

    Sprint-4 delivers BME-CI computation for single-agent input; the
    per-metric extraction of BM, BE, ME from the five inputs uses
    simplified formulas with explicit Sprint-5 deepening targets.

Multi-agent extensions (full Sprint-4 implementation required):

    BAR-A   Agentic Bias Amplification Rate
    ECPI-A  Agentic Echo Chamber Propagation Index
    IQD-A   Recursive Information Quality Decay

    These are the Sprint-4 novel contribution surface. Their formulas
    operate over the upstream agent chain (transitive agents resolved
    via upstream_hypothesis_refs walk), aggregating each agent's
    BME-CI into a chain-aware weighted score.

Composite upstream score (Sprint-4 wire-up target):

    composite_upstream_bme_score is the Hypothesis field Sprint-3 accepts
    as placeholder. Sprint-4 computes it from the upstream chain using
    the BAR-A, ECPI-A, IQD-A extensions combined with each upstream
    agent's BME-CI.

GOVERNANCE TIER THRESHOLDS (unchanged, already operative):

    T1  BME-CI < 0.20   Monitor
    T2  BME-CI 0.20 to 0.29   Review
    T3  BME-CI 0.30 to 0.38   Escalate
    T4  BME-CI > 0.38   Freeze or architectural intervention

Sprint-4 does not add new tier enforcement. Sprint-5 or later may.

SPRINT-4 NOVEL CONTRIBUTION SURFACE

Per-agent BME attribution in multi-agent topology with ledger-integrated
score provenance. Two claims:

    1. Methodological: BAR-A, ECPI-A, IQD-A extensions applied over
       transitive upstream agent chains via chain-walk aggregation.
    2. Architectural: bme_score_source payload marker in
       HYPOTHESIS_REGISTERED events distinguishes placeholder and
       computed scores in the ledger, making BME score provenance
       auditable over time.

Both are dissertation-level citations. See Sprint-4 Lab Journal entry
(close-of-sprint deliverable).


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. SYSTEM STATE AT SESSION OPEN AND HEAD SURFACE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HEAD: 348427a (Lab Journal establishment close; Sprint-3 runtime close
was 1237009, nine commits prior).

Test suite state: 110 passed, 0 skipped on multiagent/tests.

Working tree expected clean at sprint initialization.

HEAD SURFACE OF FILES SPRINT-4 WILL MODIFY (L5 discipline)

File: multiagent/exceptions.py

    Current class hierarchy (ALAGFError root with eight subclasses):

        ALAGFError
        ArtifactValidationError      (v1 parity; JSON Schema violations)
        AuthorityViolationError      (v1 parity; Invariant 1 breach)
        AgentRegistrationError       (Sprint-1 net-new)
        UnregisteredAgentError       (Sprint-1 net-new)
        DepthLimitExceededError      (Sprint-1 reserved; Sprint-3 enforcement)
        LedgerIntegrityError         (Sprint-1 net-new; hash-chain violations)
        BoundaryViolationError       (Sprint-2 net-new; handoff precondition breach)
        HandshakeError               (Sprint-2 net-new; channel protocol violation)

    Sprint-4 Block C adds four classes, relocated from their Sprint-3
    module-local definitions:

        ScopeViolationError          (Sprint-3 hypothesis.py -> consolidated)
        FrozenPathError              (Sprint-3 hypothesis.py -> consolidated)
        UpstreamResolutionError      (Sprint-3 hypothesis.py -> consolidated)
        HypothesisValidationError    (Sprint-3 artifacts/Hypothesis -> consolidated,
                                      preserves ArtifactValidationError subclass)

    Consolidation MUST preserve isinstance contracts. Any code catching
    the Sprint-3 module-local classes must continue to catch the
    consolidated versions without modification.

File: shared/artifact-contracts/v2/Hypothesis.schema.json

    The composite_upstream_bme_score field specification at HEAD:

        "composite_upstream_bme_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Net-new in v2. Weighted aggregate of upstream
          agents' BME-CI scores at the moment of synthesis. Formula and
          weights defined in /shared/bme-metric-suite/composite_bme_ci.py."
        }

    Sprint-4 does NOT modify this schema. The field remains required,
    non-nullable, in [0.0, 1.0]. Sprint-4 populates it with computed
    values instead of caller-supplied placeholders.

File: multiagent/orchestrator/synthesis/hypothesis.py

    Current exception class declarations (to be relocated in Block C):

        UnregisteredAgentError       (re-export of canonical Sprint-1 class;
                                      Sprint-4 removes re-export, imports direct)
        ScopeViolationError          (net-new Sprint-3; Sprint-4 relocates)
        FrozenPathError              (net-new Sprint-3; Sprint-4 relocates)
        UpstreamResolutionError      (net-new Sprint-3; Sprint-4 relocates)

    Sprint-4 Block B extends emit_hypothesis() to compute
    composite_upstream_bme_score and set bme_score_source appropriately.

File: multiagent/artifacts/Hypothesis/__init__.py

    Current exception class declaration:

        HypothesisValidationError(ArtifactValidationError)

    Sprint-4 Block C relocates this class to multiagent/exceptions.py.
    ArtifactValidationError subclass contract is preserved.

File: multiagent/orchestrator/synthesis/fs_agent_registry.py

    Current implementation: reads raw registration file for session
    scoping via _session_id, calls canonical get_agent_identity() for
    live status resolution, merges two reads.

    Sprint-4 Block D requires extending the canonical function at
    multiagent/orchestrator/agent_lifecycle/registration.py with an
    optional session_id filter parameter, then reducing FsAgentRegistry
    to a thin pass-through.

File: multiagent/orchestrator/agent_lifecycle/registration.py

    Sprint-4 Block D extends get_agent_identity() with optional
    session_id parameter. When provided, returns the agent only if
    its registered session matches; otherwise returns None. Meta
    fields remain stripped on return (preserving Sprint-1 contract).

File: multiagent/ledger/hash_chain/event_schemas/v2/HYPOTHESIS_REGISTERED.payload.schema.json

    Current payload schema accepts bme_score_source with enum values
    ["placeholder", "computed"]. Sprint-4 does NOT modify the schema.
    Sprint-4 implementation flips the emitted value from "placeholder"
    to "computed" when the wire-up succeeds.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. REPOSITORY FILE STRUCTURE AFTER SPRINT-4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sprint-4 adds under /shared/bme-metric-suite/:

    shared/bme-metric-suite/
    |-- __init__.py
    |-- README.md                          (module purpose, formula index)
    |-- metrics.py                         (BAR, ECPI, IQD, PTDI, AHRS, simplified)
    |-- composite_bme_ci.py                (BME-CI composite, full)
    |-- agentic_extensions.py              (BAR-A, ECPI-A, IQD-A, full)
    `-- tests/
        |-- __init__.py
        |-- test_metrics.py                (per-metric unit tests)
        |-- test_composite_bme_ci.py       (BME-CI composite tests)
        `-- test_agentic_extensions.py     (BAR-A/ECPI-A/IQD-A chain-walk tests)

Sprint-4 modifies (Block B wire-up):

    multiagent/orchestrator/synthesis/hypothesis.py
        (emit_hypothesis() calls into BME suite for score computation)

Sprint-4 modifies (Block C consolidation):

    multiagent/exceptions.py
        (four new subclass declarations)
    multiagent/orchestrator/synthesis/hypothesis.py
        (four class declarations removed; imports from exceptions)
    multiagent/artifacts/Hypothesis/__init__.py
        (HypothesisValidationError removed; imports from exceptions)

Sprint-4 modifies (Block D registry consolidation):

    multiagent/orchestrator/agent_lifecycle/registration.py
        (get_agent_identity extended with optional session_id parameter)
    multiagent/orchestrator/synthesis/fs_agent_registry.py
        (reduced to pass-through; raw-file read removed)

Sprint-4 extends (test coverage):

    multiagent/tests/invariant_tests/test_evidence_first.py
        (Sprint-4 section: BME score provenance, bme_score_source marker
        verification, chain-walk BAR-A/ECPI-A/IQD-A attribution)

Sprint-4 adds:

    multiagent/tests/agent_boundary_tests/test_bme_attribution.py
        (per-agent BME wire-up tests)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. ARTIFACT CONTRACT EXTENSIONS IN SCOPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

No shared-schema modifications. No v2/ schema touches.

The HYPOTHESIS_REGISTERED payload schema already accepts bme_score_source
with enum ["placeholder", "computed"]. Sprint-4 flips the emitted value;
the schema is unchanged.

Exception taxonomy additions in multiagent/exceptions.py:

    ScopeViolationError(ALAGFError)
        Raised when a source agent's authority_scope does not permit
        Hypothesis emission. Sprint-3 net-new; Sprint-4 relocation.

    FrozenPathError(ALAGFError)
        Raised when a prospective Hypothesis's provenance chain
        intersects a depth-frozen ancestor. Sprint-3 net-new; Sprint-4
        relocation.

    UpstreamResolutionError(ALAGFError)
        Raised when an upstream_hypothesis_ref does not resolve in the
        session ledger. Sprint-3 net-new; Sprint-4 relocation.

    HypothesisValidationError(ArtifactValidationError)
        Raised when a Hypothesis artifact fails schema or governance
        validation. Preserves ArtifactValidationError subclass contract.
        Sprint-3 net-new; Sprint-4 relocation.

Registry function signature extension:

    get_agent_identity(agent_id: str, session_id: str | None = None) -> dict | None

    When session_id is None: behaves identically to Sprint-1.
    When session_id is provided: returns the agent only if its registered
    session matches; returns None otherwise.

    Meta fields remain stripped on return. Docstring updated per LESSONS.md
    L6 to explicitly document stripping behavior.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. LEDGER EVENT SEQUENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sprint-4 introduces no new ledger event types.

HYPOTHESIS_REGISTERED events continue to carry bme_score_source in the
payload. The value shifts from "placeholder" (Sprint-3) to "computed"
(Sprint-4) when the Hypothesis is emitted through the BME-wired path.

Legacy Hypotheses with bme_score_source: "placeholder" remain valid
ledger events. The ledger is append-only; historical events are never
rewritten. Sprint-4 tests must verify that replay of Sprint-3-era
sessions (with placeholder scores) continues to succeed against the
Sprint-4 codebase.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. SPRINT OBJECTIVE AND DEFINITION OF DONE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OBJECTIVE

Deliver per-agent BME attribution in multi-agent topology with
ledger-integrated score provenance. Close three Sprint-3 candidate items
(items 3, 4, 6). Leave items 1, 2, 5 for Sprint-5.

BLOCK A --- BME SUITE CREATION

Deliverable: /shared/bme-metric-suite/ populated with:
  - metrics.py: simplified BAR, ECPI, IQD, PTDI, AHRS computations
  - composite_bme_ci.py: full BME-CI formula (BM x 0.40 + (1-BE) x 0.35
    + (1-ME) x 0.25) with input derivation from the five base metrics
  - agentic_extensions.py: full BAR-A, ECPI-A, IQD-A implementations
    operating over transitive upstream agent chains
  - README.md: module purpose, formula index, Sprint-5 deepening list
  - tests/: unit tests for each metric and composite; chain-walk tests
    for the agentic extensions

Acceptance:
  - Every formula in project instructions Section 4 has a corresponding
    function in the module
  - Chain-walk aggregation for BAR-A / ECPI-A / IQD-A correctly handles
    empty upstream chains, single-upstream chains, and multi-hop chains
  - All metric functions are pure (no file I/O, no ledger access)
  - Test coverage >= 90% on the module

BLOCK B --- BME ATTRIBUTION WIRE-UP

Deliverable: emit_hypothesis() computes composite_upstream_bme_score
from the upstream chain using the BME suite. The
HYPOTHESIS_REGISTERED event payload marks bme_score_source: "computed"
when BME suite computation succeeds.

Acceptance:
  - Computed score value is in [0.0, 1.0] (schema compliance)
  - bme_score_source: "computed" on every Sprint-4-era Hypothesis
  - Empty upstream chain produces a valid baseline score (not zero,
    not null; documented default that reflects no upstream contamination)
  - Single-upstream chain produces a score derived from the single
    upstream agent's BME-CI
  - Multi-hop chain correctly aggregates across the full transitive
    upstream agent set via BAR-A / ECPI-A / IQD-A
  - Sprint-3-era Hypotheses with bme_score_source: "placeholder"
    remain valid on ledger replay (no rewrites, no migration)

BLOCK C --- EXCEPTION TAXONOMY CONSOLIDATION

Deliverable: four Sprint-3 exception classes relocated into
multiagent/exceptions.py. Module-local declarations removed from
multiagent/orchestrator/synthesis/hypothesis.py and
multiagent/artifacts/Hypothesis/__init__.py. Imports updated.

Acceptance:
  - All four classes exist in multiagent/exceptions.py with correct
    inheritance (ScopeViolationError, FrozenPathError,
    UpstreamResolutionError subclass ALAGFError;
    HypothesisValidationError subclasses ArtifactValidationError)
  - No module-local duplicate declarations survive in the synthesis
    or artifacts module
  - isinstance checks against the consolidated classes succeed
    identically to Sprint-3 module-local checks
  - Sprint-3 Re-export of UnregisteredAgentError from synthesis.hypothesis
    is removed; synthesis code imports directly from multiagent.exceptions
  - All existing tests continue to pass without modification

BLOCK D --- REGISTRY ADAPTER CONSOLIDATION

Deliverable: get_agent_identity() extended with optional session_id
parameter. FsAgentRegistry reduced to pass-through. Docstring of
get_agent_identity updated to explicitly document meta-field stripping
behavior per LESSONS.md L6.

Acceptance:
  - get_agent_identity(agent_id) behaves identically to Sprint-1
    (backward-compatible)
  - get_agent_identity(agent_id, session_id=X) returns None when the
    agent is registered under a different session
  - FsAgentRegistry.get_agent(session_id, agent_id) is a single-line
    delegation to the canonical function
  - Docstring on get_agent_identity explicitly lists stripped meta
    fields (_session_id, _registration_event_id) and the reason for
    stripping
  - No raw-file read code remains in FsAgentRegistry

DEFINITION OF DONE (SPRINT-4 CLOSE)

  - All four Block acceptance criteria met
  - Full test suite (multiagent/tests + shared/bme-metric-suite/tests)
    passes with zero skips
  - Test count increases from 110 (Sprint-3 close) to at least 130
    (estimate: ~15 BME metric tests + ~8 chain-walk tests + ~5
    consolidation regression tests)
  - Sprint-4 changelog at
    multiagent/docs/schema_versions/sprint-4-changelog.md records all
    four Blocks, deviations from this prompt, and Sprint-5 candidate
    items (E, F, single-agent metric deepening)
  - Sprint-4 Lab Journal entry at docs/lab-journal/sprint-04-bme-attribution.md
    and Development Notes entry at
    docs/development-notes/sprint-04-bme-attribution.md produced at sprint
    close per the documentation discipline established post-Sprint-3
  - LESSONS.md amended with any Sprint-4 process corrections
  - All commits follow single-logical-unit discipline (estimate: 10-14
    commits for Sprint-4)
  - origin/main updated


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10. INSTRUCTION DISCIPLINE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE 1 --- SPRINT-0 REMEDIATION IS EXPLICIT

The missing /shared/bme-metric-suite/ is named in Section 4 as inherited
Sprint-0 debt. Sprint-4 creates the directory and populates it. The
Sprint-4 changelog records this remediation explicitly. Do not present
the BME suite as a Sprint-4 net-new deliverable without acknowledging
the Sprint-0 scaffolding gap.

RULE 2 --- HEAD CONTENTS ARE AUTHORITATIVE

The HEAD surface excerpts in Section 5 are the contract. If implementation
discovers HEAD state different from what is documented here, halt and
report the discrepancy before proceeding. This rule is L5 from LESSONS.md
applied structurally to this sprint.

RULE 3 --- EXCEPTION TAXONOMY PRESERVES ISINSTANCE CONTRACTS

Block C consolidation must not break any existing code that catches the
Sprint-3 module-local classes. isinstance checks against the relocated
classes must succeed identically. Verify via regression test before
committing Block C.

RULE 4 --- BLOCK B IS GATED BY BLOCK A

Do not begin Block B wire-up until Block A's BME suite is committed and
tests pass. Block B's acceptance criteria require calling into functions
that Block A defines; attempting Block B before Block A forces placeholder
return values that mask real integration defects.

RULE 5 --- NO SHARED-SCHEMA MODIFICATIONS

/shared/artifact-contracts/v2/Hypothesis.schema.json remains untouched.
Every field constraint Sprint-3 worked around (composite_upstream_bme_score
non-null, observation_refs minItems: 1, field name artifact_id) is still
in force. Sprint-4 works within the schema, not around it.

RULE 6 --- TEST ISOLATION VIA EXTENSION, NOT REPLACEMENT

LESSONS.md L4 remains in force. conftest.py is owned by the repo and
extended by each sprint. Sprint-4 tests add fixtures under clear delimiter
comments preserving all Sprint-1/2/3 fixture definitions verbatim.

RULE 7 --- DIAGNOSTIC PROBES WHEN ADAPTERS FAIL IDENTICALLY

LESSONS.md L7. If Block B wire-up produces identical test failures across
two implementation attempts, write a diagnostic probe before attempting
a third. Probe-first discipline.

RULE 8 --- BLOCKS LAND IN ORDER

Commit sequence: Block A (BME suite), then Block C (exception
consolidation), then Block D (registry consolidation), then Block B
(wire-up). Block B last because it depends on both A (module exists)
and C (clean exception taxonomy for wire-up error paths). Block D can
run in parallel with C but should land before B to avoid registry
adapter churn mid-wire-up.

RULE 9 --- NOVEL CONTRIBUTION LANGUAGE IS RESERVED FOR LAB JOURNAL

Code comments, commit messages, and changelog entries describe what
Sprint-4 does mechanically. The novel contribution claim
(per-agent BME attribution with ledger-integrated score provenance)
appears only in the Sprint-4 Lab Journal entry. Engineering artifacts
state facts; scholarly artifacts interpret them.

RULE 10 --- CLOSE-OF-SPRINT DOCUMENTATION IS NON-OPTIONAL

Sprint close requires both a Lab Journal entry (third-person scholarly,
APA 7) and a Development Notes entry (first-person engineering log).
LESSONS.md amendment is required only if a Sprint-4 defect ratifies a
new cross-sprint correction or amends an existing one.

═══════════════════════════════════════════════════════════════════════
END OF SPRINT-4 INITIALIZATION PROMPT
ALAGF-Ecosystem | AUDITOR_DALE_001
═══════════════════════════════════════════════════════════════════════
