# ALAGF Audit Demonstration Prototype (v1)

**STATUS: FROZEN — READ-ONLY**

This directory is the ALAGF v1 dissertation defense artifact. It is the
complete, passing-test-suite reference implementation produced across seven
development sprints of the `alagf-demo` project.

## Freeze Conditions

The contents of this directory are preserved verbatim as of the Sprint-7
completion snapshot. The following rules are enforced by Instruction
Discipline Rule 7 and Hard Stop policy in the project instructions:

- No modifications to source code, tests, UI, or schemas.
- No extensions to ledger logic or artifact contracts.
- No use as a test target by the `/multiagent` track.
- No schema edits to files referenced by the v1 canonical contracts in
  `/shared/artifact-contracts/v1/`.

## What This Directory Contains

- Full M0–M7 module implementations (Orchestrator through Ledger)
- AuditSession, ConstraintSet, Observation, Hypothesis, Decision, Action
  artifact logic as Python dataclasses
- SHA-256 hash-chained append-only ledger
- Human Decision Console UI
- Stress Engine and Metrics Engine with SPC/CUSUM
- AI Hypothesis Engine integration with Claude API (non-binding outputs)
- Full test suite (Sprint 1–7 acceptance tests)

## What This Directory Does Not Contain

- JSON Schema formalizations of v1 contracts (these now live at
  `/shared/artifact-contracts/v1/`, extracted post-hoc during ECOSYSTEM-
  SPRINT-0 per Path B; see `/shared/artifact-contracts/CHANGELOG.md`)
- Multi-agent extensions (these live in `/multiagent/`)

## Governance Rationale for Freeze

The `/demo` track represents the ALAGF v1 defensible prototype. The
dissertation research narrative is:

> ALAGF v1 is the complete, defensible prototype. The multi-agent extension
> is its operationalized future-work track.

Freezing `/demo` preserves that narrative architecturally. Any modification
would blur the boundary between v1 (defense) and v2 (extension) and weaken
the academic position.

## If Modification Is Required

A modification to `/demo` is a hard stop per project instructions Section 10.
It requires:

1. Explicit auditor authorization documented in `/docs/release-notes/`
2. A formal amendment process with changelog entries in
   `/shared/artifact-contracts/CHANGELOG.md` (if affecting shared schemas)
3. Re-verification of the v1 acceptance test suite

Do not modify without following this process.
