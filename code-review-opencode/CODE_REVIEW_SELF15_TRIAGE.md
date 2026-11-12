# code-review-opencode — Self-review 15 triage

Run 15: `max --max-findings all --fix --concurrency 6 .opencode` in `cr-self4`,
DeepSeek V4.1 Flash `#max`, production code only.

Report `981d921b-7352-4215-8c06-fd42e6f52db1`, complete (`partial: false`,
0 warnings). Stats: 10 finders, 63 candidates, 55 verifier agents, 12 refuted,
4 dupes, 32 reported. `truncated_from: 47` — the ReportFindings 32-entry cap
dropped the 15 lowest-ranked findings, so the next pass must be expected to
surface them.

Severity rubric: **high** = crash, data loss, security, or corrupt core output;
**medium** = wrong behavior, silent loss, broken contract, partial or
unpostable result; **low** = cleanup, docs, naming, efficiency, rare edge case.

## Findings

| # | Location | Finding | Severity | Validation |
|---|---|---|---|---|
| 1 | `prompts.ts:650` | filenames from `unquoteGitPath` reach the prompt with real newlines, so a changed filename can inject scope instructions | high | validated: `listFiles` decodes git quotes and `renderScope`/`buildContextPackage` interpolate raw |
| 2 | `index.ts:874` | recursion guard rejects any session with a `parentID`, not just review descendants, so unrelated subagents cannot start a review | medium | validated: `isChildSession` is true for every child |
| 3 | `json.ts:478` | text-fallback verdict without evidence is kept, including `CONFIRMED` | medium | validated: `tolerateMissingEvidence` substitutes `NO_EVIDENCE`; engine only marks partial |
| 4 | `runner.ts:139` | shared validator accepts a 1-based group-verdict list; the engine then drops the whole group | medium | validated: validator has no zero-index check; `asGroupVerdicts` rejects no-index-0 |
| 5 | `engine.ts:1063` | sweep candidates overlapping a refuted claim at 0.7 Jaccard can be dropped even when they describe a different defect | low | heuristic tradeoff; no concrete distinct-defect case yet |
| 6 | `parse.ts:256` | typed tool passes `maxFindings` through unnormalized, so string `"5"` is neither a number nor `all` and the cap is lost | medium | validated: `resolveMaxFindings` only understands number/`all`/`default` |
| 7 | `index.ts:641` | engine report appends `fixBlock` but not `FIX_LATER`, so the model is never told to re-report outcomes | medium | validated: only `decorate` adds `FIX_LATER` |
| 8 | `engine.ts:660` | mixed-lens candidates with no kind/category default to cleanup, so a real bug can rank below cleanup | low | deliberate tradeoff documented in the comment; no concrete misrank |
| 9 | `engine.ts:184` | `canonFile` unquotes a real filename that starts and ends with a quote | low | edge case; valid |
| 10 | `scope.ts:1122` | `root.trim()` strips significant trailing whitespace from the repository path | low | edge case; valid |
| 11 | `scope.ts:830` | `readCapped` mixes byte counts with a UTF-16 character budget, truncating non-ASCII conventions early | low | valid, conservative under-use |
| 12 | `index.ts:272` | `--post` notice embeds a model-facing sentence and is shown verbatim when `needsModel` is false | low | valid |
| 13 | `scope.ts:1084` | an explicit nonexistent path target falls back to the whole repository | medium | validated: `resolveDiffScope` returns `isPath:false`, no pathspec |
| 14 | `prompts.ts:805` | grouped verifier at xhigh/max uses the strict ladder with no recall bias | medium | validated: `groupVerifierPrompt` has no recall option |
| 15 | `format.ts:121` | `formatOutcomeSummary` hides findings without an `outcome` and presents the subset as the complete status | medium | validated |
| 16 | `comment.ts:277` | comment posting resolves the repo from `gh repo view` (fork clone) instead of the PR's base repository | medium | validated |
| 17 | `scope.ts:1074` | diff discovery aborts every git/gh call after 120 s | low | hardening choice; make configurable |
| 18 | `comment.ts:241` | every comment gh/git call has a hard 10 s timeout | medium | too short for a slow network; raise/config |
| 19 | `reportfindings.ts:152` | 60-char limit uses UTF-16 `.length`, not schema code points | low | valid |
| 20 | `parse.ts:205` | an invalid spaced extension value still consumes the next token, which can be the effort level | low | valid |
| 21 | `index.ts:553` | a synchronous throw from the progress callback aborts the review | low | valid |
| 22 | `runner.ts:439` | `session.context` is consumed as a bare array and cannot handle an envelope-shaped host result | low | host-variance edge case |
| 23 | `index.ts:684` | plugin-scoped `schemaResults`/`schemaFailures` maps are unbounded | low | valid over a long process |
| 24 | `index.ts:388` | host detection re-derives the review root with path-only precedence, which can disagree with `resolveScope` | medium | validated |
| 25 | `engine.ts:390` | `sameDefect` hardcodes paraphrase/failure thresholds instead of `CLAIM_POLICY` | low | valid |
| 26 | `reportfindings.ts:123` | hand-maintained validator duplicates `REPORT_FINDINGS_SCHEMA` | low | valid |
| 27 | `runner.ts:794` | every retry re-reads the full transcript for a baseline | low | valid |
| 28 | `runner.ts:680` | `formatFresh` repeats the runner's child lifecycle | low | valid |
| 29 | `index.ts:729` | tool names are re-listed instead of using `SCHEMAS` | low | valid |
| 30 | `engine.ts:137` | `scopeBlock` copies every `Scope` field into a parallel type | low | valid |
| 31 | `engine.ts:1220` | three synthesis fallbacks repeat the same slice/map/truncate code | low | valid |
| 32 | `engine.ts:671` | `buildFinders` splits both the base and extended corpora on every review | low | valid |

Totals: **1 high, 11 medium, 20 low**. The report cap also means 15 lower-ranked
findings are not in this table; they will reappear after the fixes.

## Fix status

The run-15 `--fix` turn fixed 30 of the 32 reported findings and added nine
regression tests (338 pass). Two were left as deliberate no-change calls:

- #3 (evidence-free `CONFIRMED`) was kept tolerant by the fix turn because the
  run is marked partial. Main additionally downgrades an evidence-free
  `CONFIRMED` to `PLAUSIBLE`: a partial run still reports and posts findings,
  so an unauditable claim must not keep confirmed status.
- #8 (unattributed mixed-lens candidates rank as cleanup) is a deliberate
  tradeoff: the aggregate kind of a mixed group is always correctness, and
  letting a cleanup candidate inherit it lets cleanup findings outrank real
  bugs under the report cap. The candidate's own lens still decides when it
  has one.

All other findings are fixed, including the timeout regressions (both timeout
controls are now opt-in via `CODE_REVIEW_SCOPE_TIMEOUT_MS` and
`CODE_REVIEW_COMMENT_TIMEOUT_MS`), the fork-clone comment repository, and the
prompt filename sanitization.

## Next

## Gate

The production gate is a report with fewer than 10 findings and no medium/high
severity. The 15 hidden findings mean the next pass must be run before the gate
can be declared, even after all 32 above are fixed.

## Next

1. Sync main to `cr-self4`, run the full suite, and start the next
   production-only pass.
2. Triage the next report; the 15 findings hidden by the 32-entry cap should
   surface now that the reported 32 are fixed.
3. Repeat until the production report has fewer than 10 findings and no
   medium/high severity.
