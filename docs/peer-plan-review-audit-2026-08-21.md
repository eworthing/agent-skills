# peer-plan-review — remediated multi-skill audit (2026-08-21)

Original audit: opencode (GLM-5.3) applying `skill-writer`, `writing-for-agents`, and the community `skill-creator`.

Validation and remediation: Codex applying both `skill-creator` variants (Codex system and community), `skill-writer`, and `writing-for-agents`, with graph-first source/caller discovery and direct checks of non-code artifacts.

Original target: `peer-plan-review/` @ commit `5be2de1` (2026-08-21 13:43). Validation corrections were committed in `a0969b5`; the remediation below was applied against that clean tree.

> Charter note: `docs/README.md` scopes this directory to cross-skill work. This audit is single-skill, filed here on explicit user instruction.

## Summary

All **seven actionable findings** are resolved: 1 P1, 3 P2, and 3 P3. Five findings disappeared with deletion of the unconsumed 08-21 `evals/evals.json` scaffold; the unsupported 194-invocation claim was removed; and the provider-selection cue was restored in the runtime router. The three original style-only findings remain rejected.

The existing prompt efficacy harness is unchanged. No transport code, provider adapter, test, fixture, trigger description, or review semantics changed; SKILL.md only makes its existing Preflight branch visible at the router.

## Changes Made

- Deleted `peer-plan-review/evals/evals.json`.
- Removed the scaffold from `evals/README.md` and replaced its `SPEC.md` mandate with a runnable-evidence invariant.
- Removed the unsupported 194-invocation claim and stale scaffold claim from `EVAL.md`.
- Added one provider-selection sentence before the SKILL.md router table.
- Updated this audit and its `docs/README.md` index row.

Precision pass: **deleted** an artifact with no consumer; **replaced** stale maintenance/provenance claims; **added with reason** one runtime branch cue already required by Preflight. No new files or abstractions.

## Validation Results (live, 2026-08-21)

| Gate | Result |
|---|---|
| Approved-invariant red/green check | failed on all 5 targeted conditions before the edit; passed after |
| `eval-skill.py peer-plan-review` | 100% (15/15 checks) |
| `pytest scripts/tests/` | 160 passed |
| `common/scripts/sync_common.py --check` | clean (2 consumers byte-identical) |
| `ruff check` + `ruff format --check` (scripts + evals) | clean |
| `run_review.py --self-check` | 6/6 provider CLIs found and healthy |
| skill-writer `quick_validate.py` (machine-local repo copy) | valid, 0 warnings |
| `git diff --check` | clean |

Both `skill-creator` validators still reject the repo-accepted `argument-hint` key. That pre-existing cross-validator mismatch affects `peer-plan-review`, `quorum-review`, and `contest-refactor`; it is not fixed in one skill.

## Resolution Ledger

| ID | Severity | Status | Resolution |
|---|---|---|---|
| W1 | P1 | Resolved | Deleted eval 0 and the unconsumed workflow-eval scaffold, eliminating the incorrect always-two-pass assertion. |
| W2 | P2 | Resolved | Removed the repository-unverifiable 194-invocation sentence from `EVAL.md`. |
| W3 | P2 | Resolved | Deleted the workflow cases that referenced three missing plan inputs; the real efficacy fixtures remain. |
| C1 | P2 | Resolved | Deleted the schema-less, consumer-less `evals.json`; README/SPEC now describe only the runnable efficacy harness. |
| A1 | P3 | Resolved | Restored “after choosing the reviewer, read exactly one provider reference” directly above the router table. |
| C2 | P3 | Resolved | Deleted the cases that universalized Gemini adjudication and used the nonexistent `--stance` flag. |
| C3 | P3 | Resolved | Deleted the thin, unexecuted trigger-query set with its unowned scaffold. |

## Rejected Original Findings

**A2 — SKILL.md Contents section.** Rejected: the 276-line workflow benefits from direct anchors, and neither `skill-creator` variant requires pruning it at this size.

**A3 — duplicated timeout cue.** Rejected: SKILL.md tells the host when to change the launcher argument; `adapter-cli.md` explains the flag and failure mechanics. The short repeated cue prevents a real timeout mistake.

**W4 — `opencode.md` at 101 lines.** Rejected: the file is already split under descriptive headings. Trimming one line solely to cross a rubric threshold would not improve retrieval.

## Positive Verification

- All 10 runtime references remain flat under `references/` and directly linked from SKILL.md.
- `evals/` remains outside runtime routing.
- The Default-OFF domain-context predicate, two-pass branch, background launcher, exit-code-gated read, and Finalize STOP remain internally consistent.
- The dated 2026-06-29 efficacy result and its seeded-defect fixtures remain intact.

## Open Gaps

No open `peer-plan-review` findings remain from this audit.

Cross-skill tooling still needs one decision: align the Codex/community `skill-creator` validators with the repository's multi-agent frontmatter contract, or document why `argument-hint` is intentionally outside their schema. The repo-local skill-writer validator is also gitignored/machine-local, so a fresh clone cannot reproduce that named gate.
