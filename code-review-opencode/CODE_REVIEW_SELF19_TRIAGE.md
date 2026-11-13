# self-review 19 triage

Run: `max --max-findings all --json --concurrency 6 HEAD~1..HEAD` against the
production-only copy at `f883af1`, on 2026-11-13.

Result: **33 findings**. The copy predates `c4ffb47`, so findings 1, 14, 15,
and 32 include work already fixed in that commit. Batch 4 (`b52236c`) fixes the
remaining correctness/recall findings.

## Fixed in batch 4

| # | Finding | Fix |
|---|---|---|
| 2 | A capped 1-based decision plan was not shifted because its max index was below the survivor count | Shift any plan with no index 0 and all indices in range, not only a full-length plan. |
| 3 | An evidence-free REFUTED verdict silently dropped the candidate | The tolerant text path now downgrades any evidence-free verdict to PLAUSIBLE. |
| 4 | Group verdicts were discarded when index 0 was absent | The text fallback accepts partial lists and shifts a contiguous 1-based list; the strict tool path still rejects offset payloads. |
| 5 | A prose verifier was retried in place and could be dropped | The fresh formatter is tried for every schema, not only candidates/reports. |
| 6 | v2.1.162 verifier-budget exhaustion was silent | Adds one warning and marks the run partial when candidates are left unverified. |
| 7 | Adjacent cleanup claims sharing two generic tokens merged | Generic cleanup vocabulary is excluded; only two specific domain tokens can merge an adjacent pair. |
| 8 | An invented sweep category claimed correctness priority | Only the explicit `correctness` slug can; unknown slugs fall back to cleanup. |
| 9 | An unrelated added line at the same number moved an old-path anchor to the right side | Old-path requests only use RIGHT for a same-number replacement. |
| 10 | A free-form target suppressed branch recording | The current branch is recorded for the default/free-form scope. |
| 11 | U+2028/U+2029 survived path escaping | Added to `renderPath` and the terminal sanitizer. |
| 12 | Untracked files blocked `--comment` | Status uses `--untracked-files=no` and ignores `??` lines. |
| 13 | The user-level CLAUDE.md competed with nested project files | Its 512-character reserve is allocated separately. |
| 17 | An uncaught transcript RPC failure discarded a completed child | Both transcript reads are wrapped and logged. |
| 18 | An unbounded merge array overflowed `Math.max(...)` | Replaced with a loop. |
| 19 | Plain `git diff/show/log` could run a configured textconv/external driver | Agent permissions require `--no-ext-diff --no-textconv` (and `--no-textconv` for blame); the agent bodies instruct the same. |
| 23 | The semantic-merge fallback claimed a deterministic merge but only exact-key deduped | The fallback now runs `mergeNearDuplicates` before the deterministic report. |
| 25 | Verifier recall bias came from two different inputs | One `recallLadder`/`recallSentence` pair feeds every verifier path. |
| 27 | The child schema said an invalid verdict drops the finding, but the normalizer kept it | The schema now says the verdict is omitted, matching behavior. |
| 28 | The stored max-findings policy was keyed on the literal `low-sonnet5` | Added `Cell.suppressMaxFindings`. |
| 29 | `REPORT_FINDINGS_SCHEMA` hardcoded 32 | Uses `HARD_FINDINGS_CAP`. |

## Already fixed before run 19's copy

| # | Finding | Status |
|---|---|---|
| 1 | v2.1.162 dedup bucket ignored the claim | Fixed in `c4ffb47`: the full normalized claim is in the key. |
| 14 | `truncatedFrom`/`budgetDropped` not rendered | `truncatedFrom` and budget warnings are rendered. `--json` stays a bare array by contract. |
| 15 | The synthesized summary never reached the user | Typed metadata carries it; human output shows non-bookkeeping summaries. |
| 32 | Low prompts duplicated Turn 1/Turn 2 | Shared constants in `c4ffb47`; prompt snapshots unchanged. |

## Deferred or rejected (low/informational)

| # | Finding | Decision |
|---|---|---|
| 16 | Displayed diff command omits the orchestrator's `-c` hardening flags | Accepted: `gitDiffArgs` already carries the safe `--no-ext-diff/--no-textconv` flags, and the child permission table denies `-c`. The code comment documents the difference. |
| 20 | Permission table duplicated across three agent files | Accepted format constraint; no include mechanism. |
| 21 | Schema-echo detection only recognizes the exact sample payload | Rejected: `schemaExample` is generated from `SAMPLE_VALUE`, and `isLabeledExample` catches a paraphrased labeled copy. |
| 22 | `scope.branch` has two meanings | Deferred low; comment posting still resolves the PR. A `headBranch` field would be a larger scope-model change. |
| 24 | `if (scope.diffBase)` is unreachable after the earlier guard | Deferred low; harmless dead branch. |
| 26 | `waitForChild` repeats its settle/stall blocks | Deferred low; a refactor needs dedicated polling tests. |
| 30 | `gitlabComment` is exported but unused | Deferred: retained as part of the recovered prompt corpus; the live host path refuses GitLab comments. |
| 31 | `detectHost`/`resolvePrNumber` wrappers have no production callers | Rejected: tests use them as public helpers. |
| 33 | `multiHigh` repeats `multiMedium` scaffolding | Deferred low; the prompts differ in angles, caps, intro, and verifier fragment. |

## Verification

`node --test test/*.test.ts` → **360 passed, 0 failed** after batch 4.
