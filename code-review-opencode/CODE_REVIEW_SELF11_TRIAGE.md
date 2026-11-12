# code-review-opencode — Self-review 11 — triage

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-12, concurrency 4.

Result: **32 findings**, `partial: false` — no finder failures, no warnings, 7 refuted. The first complete 4-way run on the merged fixes. It fails the stopping rule on count and severity.

## Run stats

- finders: 10, candidates: 67, verifier agents: 57
- verified: 57, refuted: 7, dupes: 6, reported: 32
- finder failures: 0
- warnings: []

## Severity

- **High:** crash, data loss, security, corrupt output, or a broken core path.
- **Medium:** wrong behavior, silent loss, broken contract, partial review, unpostable comment, or a reliability failure.
- **Low:** duplication, dead code, naming, comments/docs, performance cleanup, or a purely cosmetic fix.

## Findings

| # | Location | Finding | Severity |
|---|---|---|---|
| 0 | `.opencode/agents/review-finder.md:26` | The `git -C * diff*` allow rule still permits config-driven command execution, so the supposedly read-only finder can run arbitrary shell code. | High |
| 1 | `.opencode/plugins/code-review-opencode/format.ts:95` | The human renderer sanitizes finding blocks but prints refuted summaries and warnings without `sanitizeControl`. | Medium |
| 2 | `.opencode/plugins/code-review-opencode/json.ts:165` | `scanAnchored` keeps the last result-shaped object, so a payload followed by an echoed schema example is parsed as the example. | Medium |
| 3 | `.opencode/plugins/code-review-opencode/json.ts:381` | asGroupVerdicts rejects the entire verdict list when index 0 is absent, even for a partially complete payload the tolerant normalizer already accepted. | Medium |
| 4 | `.opencode/plugins/code-review-opencode/engine.ts:1219` | The wf162 text-synthesis path copies the synthesizer's `line` onto the matched verified finding, so a hallucinated or off-by-N line replaces the only anchor. | Medium |
| 5 | `.opencode/plugins/code-review-opencode/engine.ts:200` | `canonFile` strips any leading `a/` or `b/` from a candidate path and maps it onto a changed root file with the same suffix. | Medium |
| 6 | `.opencode/plugins/code-review-opencode/scope.ts:766` | buildContextPackage ignores fallbackFiles whenever the churn map is non-empty, so scoped files missing from the parsed patch are dropped from the context index. | Medium |
| 7 | `.opencode/plugins/code-review-opencode/engine.ts:495` | The index-based merge keeps the representative's `line` and discards a merged finding's line anchor. | Medium |
| 8 | `.opencode/plugins/code-review-opencode/engine.ts:1274` | truncatedFrom is set when synthesis merged down to the cap | Medium |
| 9 | `.opencode/plugins/code-review-opencode/engine.ts:749` | The diff deleted `category: c.category ?? categoryFor(f)` (which always stamped a finding with its producing lens slug) and replaced it with `c.category ?? c.kind ?? ...`, which prefers the candidate's coarse kind. | Medium |
| 10 | `.opencode/plugins/code-review-opencode/json.ts:245` | extractJson maps all fences through parseCandidate (which runs scanAnchored plus up to 1000 bracket starts) before choosing one, so long prose or large code quotes cost O(fences x starts x length). | Medium |
| 11 | `.opencode/plugins/code-review-opencode/finding.ts:23` | positiveLine accepts any integer above zero, including values beyond Number.MAX_SAFE_INTEGER or in exponent form (1e21), which cannot address a real source line. | Medium |
| 12 | `.opencode/plugins/code-review-opencode/scope.ts:884` | The per-source minimum slice `readCapped(p, Math.max(1000, budget - used))` was deleted; each source is now clamped to `contentBudget - contentUsed`, so a source can receive a zero-byte slice and be silently skipped. | Medium |
| 13 | `.opencode/plugins/code-review-opencode/parse.ts:367` | resolveEffort feeds `sessionEffort` straight into coerceLevel, which maps every unrecognized non-empty string to "high" instead of the documented "medium" fallback. | Medium |
| 14 | `README.md:97` | The README's default-family medium recipe says ≤8 findings with floor 4, but the dispatch table maps medium to the inline-high cell (≤10, floor 5). | Low |
| 15 | `.opencode/plugins/code-review-opencode/scope.ts:1250` | Semicolon-joined diffCommand is rejected by the agents' new `*;*` shell deny | Medium |
| 16 | `.opencode/plugins/code-review-opencode/scope.ts:1239` | The `git diff --numstat` pass (and `numstatTimeoutMs`) was removed; `diffLines` now comes only from `scanPatchChurn(diffText).total` over successfully captured chunks. | Medium |
| 17 | `.opencode/plugins/code-review-opencode/runner.ts:213` | Synth child prompt tells it to read/run tools its agent denies | Medium |
| 18 | `.opencode/plugins/code-review-opencode/runner.ts:453` | A transient session.get failure is treated as the child being gone, ending the wait while the child is still alive. | Medium |
| 19 | `.opencode/plugins/code-review-opencode/runner.ts:393` | waitForChild accepts session.wait resolving to idle without checking the pre-prompt baseline, so an idle new child can settle before its turn starts. | Medium |
| 20 | `.opencode/plugins/code-review-opencode/runner.ts:470` | The idle fallback only settles when `busy` or `idle` changes, so a host session `time` with only `created`/`updated` never settles. | Medium |
| 21 | `.opencode/plugins/code-review-opencode/host.ts:46` | Capability probe requires session.interrupt the runner only uses optionally | Medium |
| 22 | `.opencode/plugins/code-review-opencode/index.ts:746` | The ReportFindings outcome summary is posted only through optional session.synthetic and silently disappears when that host method is absent. | Medium |
| 23 | `.opencode/plugins/code-review-opencode/index.ts:831` | The code_review tool's typed metadata is built by an adapter that drops the engine's partial flag and warnings, so incomplete runs are presented as complete typed reports. | Medium |
| 24 | `.opencode/plugins/code-review-opencode/prompts.ts:758` | groupVerifierPrompt concatenates the strict 3-state ladder and the recall-biased ladder back to back, so every grouped verifier receives two contradictory verdict rubrics. | Medium |
| 25 | `.opencode/plugins/code-review-opencode/reportfindings.ts:117` | The ReportFindings `level` is validated case-sensitively through `isLevel(String(obj.level))` while every other boundary in the pipeline normalizes levels case-insensitively, so a capitalized level is silently discarded from the typed metadata. | Medium |
| 26 | `.opencode/plugins/code-review-opencode/format.ts:47` | The control-character class was widened from `\u000B\u000C\u000E-\u001F` to `\u000B-\u000D\u000E-\u001F`, so U+000D (CR), which the deleted range deliberately excluded, is now replaced with a visible `␍` glyph. | Low |
| 27 | `test/helpers.ts:37` | Test callers contradict the new EngineOptions/Scope contracts (version, diffLines) | Low |
| 28 | `.opencode/plugins/code-review-opencode/engine.ts:371` | `sameDefect` still treats 30% summary-token overlap at the same line as proof of the same defect and never compares failure scenarios, so distinct verified bugs at one line are collapsed. | Medium |
| 29 | `.opencode/plugins/code-review-opencode/index.ts:169` | `--comment` decoration assumes every non-GitLab host is GitHub instead of gating the GitHub block on the resolved host, so unsupported remotes receive GitHub posting instructions. | Medium |
| 30 | `.opencode/plugins/code-review-opencode/parse.ts:150` | The `--max-findings` special case runs before parseExtensions' target-boundary checks, so a free-form target that mentions the flag is consumed as an option instead of target text. | Medium |
| 31 | `.opencode/plugins/code-review-opencode/scope.ts:871` | `discoverConventions` gives every root convention file a fixed equal share and never redistributes the unused portion, contradicting the 'unused per-source budget can be redistributed' comment. | Low |

## Themes

- **Security regression (#0):** the `git -C * diff*` prefix allow still accepts `-c core.pager=...`; add `-c`, `--config-env`, and short pager-option denies to all three agent allowlists.
- **Prompt/deny conflict (#15):** the new `*;*` deny blocks the semicolon-joined `Diff command`; render the diff commands as separate commands.
- **Fix-turn regressions:** the shared patch parser, `canonFile`, `readCapped`, `truncatedFrom`, and the text-synthesis anchor each introduced a new edge case. Fix them narrowly, without another broad refactor.
- **Runner reliability:** transient `session.get` failures and hosts with only `created`/`updated` can still end or hang the wait. The baseline and idle checks need one more pass.

## Concurrency

Run 11 used concurrency **4** and completed with no finder failures. Four remains the default; 6 stays the smaller-diff/off-peak option after the run 10 stall.

## Next run

Apply all 32 findings with minimal, targeted edits, then run **run 12** with `max --max-findings all --fix`. Stop only when the run is complete (`partial: false`), has fewer than 10 findings, and has no high/medium severity findings.

## Fix turn

All 32 findings were fixed and merged into the main tree. The fix turn changed
the three agent allowlists, `engine.ts`, `finding.ts`, `format.ts`, `host.ts`,
`index.ts`, `json.ts`, `parse.ts`, `prompts.ts`, `reportfindings.ts`,
`runner.ts`, `scope.ts`, and nine test files. The suite is now **280 tests**,
all passing. The high-severity shell bypass is closed with denies for `-c`,
`--config-env`, `--paginate`, and `-O`; the diff commands render as separate
bullets so the `*;*` deny no longer blocks them.

Run 12 is the first run on the merged fixes with concurrency 4.
