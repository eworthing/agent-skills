# code-review-opencode — Self-review 3 — triage and fix plan

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-11.
Engine result: 32 findings, no partial warning, 10 finders, 9 refuted candidates.
The `--fix` turn is in progress; this table tracks every finding so none is
silently skipped.

Legend: **FIX** = real defect, fix it. **DOC** = intentional behavior, correct
the documentation. **DESIGN** = deliberate extension, keep but document.

| # | Location | Finding | Disposition |
|---|---|---|---|
| 0 | `scope.ts:738` | `git diff`/`--name-status` failures and timeouts are swallowed; an empty scope looks clean | **FIX** — check exit/timeout/abort; throw a clear error or mark the run partial instead of returning “No changes found”. |
| 1 | `scope.ts:121` | `looksLikeRange` rejects dotted refs (`v1.2.3...HEAD`) | **FIX** — allow dots inside each ref segment; only the `..`/`...` separator is special. |
| 2 | `parse.ts:99` | Repeated extension flags leave the second occurrence in the target | **FIX** — global regex + `replaceAll` in `take`/`bool`/`stripFlags`. |
| 3 | `index.ts:776` | `code_review` tool calls `session.get` before the child-session gate | **FIX** — guard `session.get` or move the call after the capability check. |
| 4 | `review-finder.md:22` | Allowlists lack `git -C *` | **FIXED in main** — added to finder, sweep, verifier; sync to `cr-self4`. |
| 5 | `cells.ts:379` | Workflow modes fall back to the default family’s inline recipe at low/medium | **FIX** — resolve the workflow version’s own low/medium cells; never hard-code the default family. |
| 6 | `json.ts:350` | Group-verdict normalizer fabricates evidence | **FIX** — require non-empty evidence; reject the call so the runner retries. |
| 7 | `engine.ts:997` | wf162 fuzzy 0.3 overlap lets an invented finding inherit CONFIRMED | **FIX** — match only exact/near-exact wording (normalized summary equality) across a corrected anchor; drop the 0.3 fallback. |
| 8 | `json.ts:293` | Malformed finder candidates are dropped silently at the tool boundary | **FIX** — strict tool boundary: if any candidate is dropped, return `ok:false` and re-prompt; keep tolerant text parsing for the fallback. |
| 9 | `engine.ts:1016` | wf162 backfill duplicates a finding the synthesizer merged | **FIX** — dedupe the final emitted list with `sameDefect` before capping; do not re-add a merged-away defect. |
| 10 | `engine.ts:840` | One shared token with a refuted claim drops a real sweep finding | **FIX** — require two shared specific tokens or a high overlap; one token is not enough. |
| 11 | `prompts.ts:667` | `renderDiff` memo returns `""` on the first `undefined` call | **FIX** — distinguish “not cached yet” from “cached empty”; compute the placeholder. |
| 12 | `json.ts:405` | Decision `merge` rejects numeric strings while `index` accepts them | **FIX** — use `num` for merge entries; record invalid entries in notes. |
| 13 | `json.ts:218` | Line numbers reject numeric strings | **FIX** — `positiveLine` accepts integer strings; keep the positive-integer rule. |
| 14 | `scope.ts:262` | `unquoteGitPath` trims unquoted paths with leading/trailing spaces | **FIX** — trim only for the quote test; return the raw path when unquoted. |
| 15 | `scope.ts:404` | `countPatchLines` treats `+++`/`---` content as headers | **FIX** — skip only real file headers (`+++ b/`, `+++ /dev/null`, quoted forms), not content lines. |
| 16 | `scope.ts:724` | `diffLines` counts only `plan[0]`; a dirty worktree reports 0 | **FIX** — sum numstat over every plan entry (committed + worktree). |
| 17 | `index.ts:605` | `--json` partial runs have no machine-readable flag | **FIX** — keep stdout a bare array, but emit a single JSON warning object on stderr (`{"partial":true,"warnings":[...]}`) so CI can detect an incomplete run. |
| 18 | `scope.ts:509` | Convention budget is 50/50 even when only root files exist | **FIX** — give the full budget to the only side; split only when both sides exist. |
| 19 | `index.ts:620` | `/verify` follow-up is engine-only | **FIX** — resolve the scope (or path hint) for inline/prompt cells and append the same follow-up. |
| 20 | `index.ts:578` | Missing-subagent detection is a regex over warnings | **FIX** — count typed runner failures; fall back only when every finder failed and no candidates exist. |
| 21 | `parse.ts:266` | `o5-bmin` applies the 32 cap to the JSON contract | **FIX** — remove the `cell.id === "o5-bmin"` clause; `hasReportFindings` governs the cap. |
| 22 | `engine.ts:292` | Pre-verify Jaccard dedup can collapse distinct defects | **FIX** — require same line plus summary and failure-scenario overlap (or exact normalized summary); keep the semantic synthesizer as the primary dedup. |
| 23 | `engine.ts:495` | Finding kind is inferred from a free-text category | **FIX** — add an optional `kind` to the candidate schema/prompt and carry it; keep `category` for the report. |
| 24 | `engine.ts:154` | `canonFile` misses `b/`-prefixed and absolute paths | **FIX** — strip `b/`, try root-relative, then a guarded unique suffix match; keep the raw path when ambiguous. |
| 25 | `engine.ts:920` | Equal rank+location ties depend on verifier completion order | **FIX** — add file/line/summary tie-breakers to the sort. |
| 26 | `prompts.ts:272` | Minimal prompt asks for `severity`/`comment`, not the ReportFindings schema | **FIX** — inspect the cell; either use the schema fields or accept the aliases at the normalizer. Do not lose findings. |
| 27 | `index.ts:603` | Report artifact contradicts the read-only contract | **FIX** — the artifact is now opt-in via `CODE_REVIEW_REPORT_DIR`; a normal review writes nothing into the checkout. |
| 28 | `index.ts:438` | `hostRoot` uses the raw free-form target | **FIX** — resolve `extractPathHint` before host detection, or defer host selection until after scope resolution. |
| 29 | `index.ts:845` | `--json` non-synthetic fallback prompts the model | **FIX** — add a strict “output exactly this JSON and nothing else” guard, or log and skip rather than break the bare-array contract. |
| 30 | `parse.ts:222` | `looksLikeLevel` flags “maximum”, “highlight”, “lowercase” | **FIX** — tighten the typo matcher (length + edit distance, or a known-typo list). |
| 31 | `json.ts:89` | `scanBalanced` counts brackets inside an unbalanced code quote | **FIX** — only count plausible JSON starts; skip code-like brackets. |

## Result

The third run's `--fix` turn applied **all 32 findings, with no skips**:
191 tests passed after the fixes. The fourth run found 15 more (mostly
regressions in the new strict/tolerant split); the `--fix` turn applied all 15
with no skips (207 tests), and the partial-run reliability fixes brought the
suite to **218 tests**. The artifact is now opt-in, the `--json` partial warning
is a machine-readable stderr line, and the minimal prompt uses the registered
`ReportFindings` fields.

C3 (per-role model/effort) and C7 (`--fix` outcome summary) were then added on
top: **218 tests pass**. The next run should validate the combined result.

## Pre-next-run work

1. **Fix all of the above.** No validated finding is skipped. The fix turn’s
   diff is the starting point; the remaining items are applied on top.
2. **Implement C3 (per-role model/effort)** — one-line runner change plus
   tests. Small, high confidence, directly closes the largest fidelity gap
   after the prompts.
3. **Implement C7 (`--fix` outcomes)** — synthetic outcome summary plus tests.
   Small and independent.
4. **Keep C8/C9 docs** (effort precedence, concurrency) as written.
5. **Do not implement C1/C4 or the benchmarks before the next run.** They add
   new surface area (background promise, comment schema, benchmark harness)
   and would make the next self-review measure two things at once. Land them
   after the next run, when the finding count is down and the fixes are stable.
6. Re-run `node --test test/*.test.ts`, `git diff --check`, and the plugin-load
   check; sync `cr-self4`; then start the next full run.

## Decision rule for the next runs

- Keep running `max --max-findings all --fix` until the confirmed finding
  count drops significantly (target: single digits, with no new high-severity
  correctness findings).
- Each run’s real findings are fixed before the next run. Design-choice
  findings are either implemented or documented, never ignored.
- Do not count the same finding twice across runs; compare locations and
  summaries.
