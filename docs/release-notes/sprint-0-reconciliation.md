# Sprint-0 Reconciliation Record

**Logged during:** ECOSYSTEM-SPRINT-1
**Auditor:** AUDITOR_DALE_001
**Prior commit:** 2bdfa42 (ECOSYSTEM-SPRINT-0: Scaffold and schema initialization)

## Purpose

Capture discrepancies between Sprint-0 completion claims (per the Sprint-1 session initialization prompt) and the actual local repository state at Sprint-1 open. Preserves an audit trail of what was found, what was decided, and what remains open. Invariant 4 (Reconstructability) applies to project history and governance decisions, not only runtime events.

## Discrepancy 1 — v2 schemas absent from working tree

**Finding.** The Sprint-1 session init prompt stated six v2 schemas were delivered at Sprint-0 close. The filesystem check showed the v2 directory was empty.

**Root cause.** Working tree was out of sync with the committed index. `git ls-tree -r HEAD shared/artifact-contracts/v2/` showed all six schema blobs present in commit 2bdfa42; the files had simply been deleted or were never materialized on disk after the commit.

**Resolution.** `git checkout HEAD -- shared/artifact-contracts/v2/` restored all six files with correct sizes (AgentIdentity 5404 bytes, Hypothesis 3681, Action 2459, Decision 2413, Observation 2161, AgentHandoff 2094).

**Status.** Resolved. No code change required.

## Discrepancy 2 — /demo/ledger untracked, no committed source

**Finding.** Project instructions describe `/demo` as "Complete through seven development sprints. Full passing test suite. Frozen as the v1 dissertation defense artifact." The working tree shows `/demo/ledger/` exists as empty directory shells. `git status` reports the directory as untracked; `git ls-tree -r HEAD demo/ledger/` returned zero results, confirming no `/demo/ledger/` source was ever committed at 2bdfa42.

**Root cause.** Not investigated in Sprint-1 scope. Possibilities: v1 demo lived in a separate repository that was not merged into the ecosystem monorepo; v1 demo was scaffolded but never committed; local directory shells are leftovers from Sprint-0 scaffolding that were never populated.

**Resolution — Sprint-1.** Section 9 of the Sprint-1 session init prompt instructed Claude to reference the v1 demo ledger pattern for the v2 envelope design. With no v1 source available, we chose **Path A**: author the v2 ledger de novo from Sprint-0 schema decisions, ALAGF invariants, and standard append-only hash-chain practice. The v2 ledger envelope is documented in `/multiagent/docs/schema_versions/sprint-1-changelog.md` and encoded in `/multiagent/ledger/hash_chain/event_schemas/v2/LedgerEvent.envelope.schema.json`.

**Status — Sprint-1.** Resolved for Sprint-1 purposes. The v2 ledger is fully functional and tested. Cross-track envelope reconciliation is deferred to Sprint-6 (evidence pack export, agent-boundary aware).

**Open question for future work.** Should the frozen v1 demo be located, imported, or formally declared out-of-scope for the ecosystem monorepo? The research narrative in the project instructions treats v1 as "the defensible, complete prototype." If the v1 source is not available in the monorepo, the narrative depends on external artifacts not governed by this repository.

## Discrepancy 3 — v2 Hypothesis schema missing source_agent_id

**Finding.** Project instructions Section 5 state that every AI-produced artifact carries a `source_agent_id` field. Review of the committed v2 schemas shows:

- `Observation.schema.json` v2 — requires `source_agent_id`. Consistent with instructions.
- `Action.schema.json` v2 — includes nullable `source_agent_id`. Consistent.
- `Hypothesis.schema.json` v2 — **does not declare `source_agent_id`**. Inconsistent.

**Impact.** Hypothesis artifacts cannot be directly attributed to their producing agent. Attribution is only recoverable via transitive traversal of `upstream_hypothesis_refs` and the `input_provenance_chain` on referenced Observations. This weakens Invariant 3 (Evidence-First) for hypotheses and complicates BME-A per-agent attribution required by Sprint-4.

**Decision.** Sprint-1 scope forbids schema modifications (Section 6 of the Sprint-1 prompt). Defer to Sprint-0 remediation backlog. Address before Hypothesis runtime logic is implemented (Sprint-3 or later). No Sprint-1 runtime impact since Hypothesis artifacts are not constructed in Sprint-1.

**Status.** Open. Action required before Sprint-4 (BME attribution) begins implementation.

## Housekeeping — untracked scratch files

During Sprint-1 diagnostics, the following scratch files were generated on the local tree:

- `shared/artifact-contracts/v2/_v2_schemas_dump.txt`
- `shared/artifact-contracts/v2/_v2_schemas_dump_2.txt`
- `shared/artifact-contracts/v2/~$2_schemas_dump.txt` (Office lock file)
- `shared/artifact-contracts/v1/_v1_schemas_dump.txt`

**Recommendation.** Add to `.gitignore`:

```
# Transient schema dump and Office lock artifacts
**/shared/artifact-contracts/**/_*_dump*.txt
**/shared/artifact-contracts/**/~$*
```

## Summary

| Discrepancy | Status | Blocking? |
|---|---|---|
| v2 schemas missing from working tree | Resolved | No |
| /demo/ledger untracked, no committed source | Resolved for Sprint-1 (Path A) | No |
| Hypothesis missing source_agent_id | Open, backlog | Blocks Sprint-4 |
