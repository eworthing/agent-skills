# code-review-opencode — Self-review 10 — triage

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-12, concurrency 6.

Result: **32 findings**, `partial: true` — one finder (angle-A) stalled after 10 minutes and was interrupted. The run fails the stopping rule on completeness, count, and severity.

## Run stats

- finders: 10, candidates: 57, verifier agents: 43
- verified: 43, refuted: 7, dupes: 6, reported: 32
- finder failures: 1
- warnings: ['finder angle-A returned no usable structured result; treated as zero candidates']

## Severity

- **High:** crash, data loss, security, corrupt output, or a broken core path.
- **Medium:** wrong behavior, silent loss, broken contract, partial review, unpostable comment, or a reliability failure.
- **Low:** duplication, dead code, naming, comments/docs, performance cleanup, or a purely cosmetic fix.

## Findings

| # | Location | Finding | Severity |
|---|---|---|---|
| 0 | `.opencode/plugins/code-review-opencode/index.ts:526` | Workflow cells pass their default `semanticMerge: false` as an explicit value, which the engine treats as `--no-semantic-merge`, disabling the workflow synthesizer. | Medium |
| 1 | `.opencode/agents/review-finder.md:50` | The read-only shell allowlist matches the whole command string, so a chained command after an allowed git command is permitted. | High |
| 2 | `.opencode/plugins/code-review-opencode/json.ts:381` | The group-verdict tool boundary accepts offset/1-based index lists that the engine parser rejects, discarding every candidate in the group. | Medium |
| 3 | `.opencode/plugins/code-review-opencode/comment.ts:129` | For an explicit branch target, `scope.branch` is the diff base but `resolvePrNumber` treats it as the PR head, so `--comment` resolves the wrong PR. | Medium |
| 4 | `.opencode/plugins/code-review-opencode/index.ts:806` | Session and prompt model IDs are read through ad-hoc fields instead of `modelRef`, so a host record in the other documented shape makes `detectFamily` fall back to `default`. | Medium |
| 5 | `.opencode/plugins/code-review-opencode/index.ts:167` | GitLab `--comment` on an inline or prompt-mode cell is silently dropped because the only 'ignored' notice is emitted for `--post`. | Medium |
| 6 | `.opencode/plugins/code-review-opencode/engine.ts:364` | `mergeNearDuplicates` never copies the absorbed finding's `line`, so a file-level representative can erase the only anchor. | Medium |
| 7 | `.opencode/plugins/code-review-opencode/engine.ts:569` | A grouped finder's cleanup candidate with a cleanup slug not in that group's lens list (for example `dead-code`) is classified as correctness and can outrank real bugs. | Medium |
| 8 | `.opencode/plugins/code-review-opencode/comment.ts:198` | The PR base guard compares branch-name suffixes, so a different base branch ending in the PR base is accepted as the same diff base. | Medium |
| 9 | `.opencode/plugins/code-review-opencode/engine.ts:1248` | `truncatedFrom` is set from the pre-synthesis survivor count, so a report whose synthesizer merged findings below the cap still claims it was truncated. | Medium |
| 10 | `.opencode/plugins/code-review-opencode/scope.ts:1188` | A partial `--name-status` failure with an empty successful listing leaves `Scope.files` empty even though the captured diff is non-empty, so the review reports no changes and discards the diff. | Medium |
| 11 | `.opencode/plugins/code-review-opencode/index.ts:449` | The scope-error catch ignores `flags.json` and returns a model prompt, breaking the bare-array contract for `--json`. | Medium |
| 12 | `.opencode/plugins/code-review-opencode/runner.ts:613` | The formatter path returns on a `gone` wait outcome before reading the child's messages, discarding a valid text answer. | Medium |
| 13 | `.opencode/plugins/code-review-opencode/engine.ts:366` | mergeNearDuplicates copies the longest failure scenario's text onto the representative even when that entry has a weaker verdict, so a CONFIRMED finding can be reworded with unverified sweep text. | Medium |
| 14 | `.opencode/plugins/code-review-opencode/engine.ts:346` | The same-line branch of sameDefect ignores the findings' kind, so a cleanup claim can absorb and rank a correctness claim. | Medium |
| 15 | `.opencode/plugins/code-review-opencode/comment.ts:46` | GitHub Enterprise is detected as GitHub, but the gh api comment call never passes the GHE hostname, so comments target github.com. | Medium |
| 16 | `.opencode/plugins/code-review-opencode/scope.ts:751` | `readCapped` decodes a raw byte slice as UTF-8, so a byte budget that lands mid-sequence injects a replacement character into the conventions text. | Medium |
| 17 | `.opencode/plugins/code-review-opencode/scope.ts:232` | extractPathHint removes only one leading and one trailing punctuation character, so a backticked path followed by a comma or colon is never found. | Medium |
| 18 | `.opencode/plugins/code-review-opencode/engine.ts:948` | A sweep candidate with kind `cleanup` but no category is assigned category `correctness`, mislabeling the finding in the report. | Medium |
| 19 | `.opencode/plugins/code-review-opencode/prompts.ts:31` | All 17 prompt fragments are read synchronously with `readFileSync` at module import (lines 31-47) and the angle strings are pre-joined, so plugin startup always pays those disk reads even when no review ever runs. | Low |
| 20 | `.opencode/plugins/code-review-opencode/engine.ts:968` | Finding identity is reimplemented with three unrelated matchers and thresholds (sameDefect 0.3/0.4, sweep-refuted 0.7, wf162 matchIndex 0.6/any token) instead of one shared claim comparator. | Low |
| 21 | `.opencode/plugins/code-review-opencode/engine.ts:888` | `partial` and `warnings` track the same incompleteness separately, and this fallback warning is pushed without setting partial; deriving one from the other or recording both in one helper would prevent drift. | Medium |
| 22 | `.opencode/plugins/code-review-opencode/index.ts:399` | Inline/prompt-only cells await a complete `resolveScope({filesOnly:true})` - several git subprocesses and, for PR targets, a `gh pr view` network call - before returning the prompt, only to decide whether to append a static `/verify` paragraph. | Low |
| 23 | `.opencode/plugins/code-review-opencode/scope.ts:781` | `buildContextPackage` re-parses the entire captured diff with `scanPatchChurn` and discards the returned `total`, while `resolveScope` already spawns `git diff --numstat` per plan entry to compute that same added/deleted count. | Low |
| 24 | `.opencode/plugins/code-review-opencode/scope.ts:1243` | The scope resolver awaits three separate Promise.all batches over the same diff plan (name-status listings, then numstat, then patch capture), so the slow patch capture is serialized behind the two probes instead of overlapping with them. | Low |
| 25 | `.opencode/plugins/code-review-opencode/runner.ts:457` | When the host's session record has no `time`, the stall watchdog calls `session.context` (the child's full transcript, including the diff-sized prompt) on every 2-second poll. | Low |
| 26 | `.opencode/plugins/code-review-opencode/scope.ts:454` | filesFromDiff, scanPatchChurn, and diffSideMap each implement their own unified-diff hunk state machine instead of sharing one patch parser. | Low |
| 27 | `.opencode/plugins/code-review-opencode/index.ts:364` | Every invocation computes `hostRoot` with a synchronous repo-root walk (`resolveDiffScope` -> `resolveTargetPath`/`findGitRoot` realpathSync + existsSync per ancestor, plus `extractPathHint` stats) although the value is only read inside the `--comment` branch. | Low |
| 28 | `.opencode/plugins/code-review-opencode/prompts.ts:621` | renderDiff truncates with String.slice instead of the shared surrogate-safe truncateText helper. | Medium |
| 29 | `.opencode/plugins/code-review-opencode/prompts.ts:416` | Multi-agent prompts inline copies of the recovered verify-3state.md, verify-recall.md, and sweep.md blocks instead of loading the fragments. | Low |
| 30 | `.opencode/plugins/code-review-opencode/json.ts:397` | normalizeCandidatesCall, normalizeGroupVerdictsCall, normalizeReportCall, and normalizeDecisionsCall each reimplement the same per-item cap/drop/notes/reject skeleton; one generic list normalizer parameterized by key, validator, and tolerance would replace four copies. | Low |
| 31 | `.opencode/plugins/code-review-opencode/index.ts:493` | Three branches hand-format the same CODE_REVIEW_PARTIAL stderr record instead of one helper. | Low |

## Concurrency

The clean 6-way run used exactly six concurrent finder children. One finder stalled for 600 s and was interrupted; the other five completed. The stall may have been contaminated by an earlier double-run (a killed command POST left its engine running, so a retry started a second engine in the same session). Even so, the rule is: **6 stalled, so revert the default to 4** for run 11. The 6-way trial did not produce a clean complete run.

## Next run

Apply all 32 findings, set the concurrency default back to 4, then run **run 11** with `max --max-findings all --fix`. Stop only when the run is complete (`partial: false`), has fewer than 10 findings, and has no high/medium severity findings.

## Fix turn

All 32 findings were fixed and merged into the main tree. The fix turn changed
the three agent allowlists, `comment.ts`, `engine.ts`, `index.ts`, `json.ts`,
`prompts.ts`, `runner.ts`, `scope.ts`, and two test files. The suite is now
**268 tests**, all passing. The concurrency default was reverted to **4** after
the 6-way stall: `parse.ts`, the parser test, README, and
`CODE_REVIEW_GO_LIMITS.md` now document 4 as the default and 6 as the
smaller-diff/off-peak option.

Run 11 is the first run on the merged fixes with concurrency 4.
