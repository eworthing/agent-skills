# code-review-opencode — Self-review 9 — triage

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-12.
Result: **32 findings, complete** — `partial: false`, no warnings, 8 refuted.
The second complete run; the stopping rule still fails on count and one high
severity finding.

## Severity

- **High:** crash, data loss, security, corrupt output, or a broken core path.
- **Medium:** wrong behavior, silent loss, broken contract, partial review,
  unpostable comment, or a reliability failure.
- **Low:** duplication, dead code, naming, comments/docs, fixture organization,
  or a purely cosmetic cleanup.

## Findings

| # | Location | Finding | Severity |
|---|---|---|---|
| 0 | `review-finder.md:86` | Read-only shell allowlist grants write-capable `echo *`, `sort *`, and `git diff/log/show --output` | High |
| 1 | `engine.ts:1161` | Cancelled final merge is reported as a complete review | Medium |
| 2 | `engine.ts:1104` | Text synthesis matches any unclaimed same-line finding before checking relatedness | Medium |
| 3 | `engine.ts:759` | Grouped verdicts map by raw index without requiring coverage 0..n-1 | Medium |
| 4 | `json.ts:226` | First parseable fenced block can be an echoed schema example, not the payload | Medium |
| 5 | `runner.ts:250` | `hitStepLimit` can match the literal in the initial diff prompt | Medium |
| 6 | `json.ts:310` | Malformed candidates beyond the cap reject the whole finder payload | Medium |
| 7 | `json.ts:66` | `repairEscapes` accepts `\u` without four hex digits | Medium |
| 8 | `comment.ts:173` | Branch PR posting checks HEAD but not the reviewed diff base | Medium |
| 9 | `engine.ts:992` | `--no-semantic-merge` cannot disable workflow synthesis | Medium |
| 10 | `scope.ts:1041` | `defaultExec` returns code 1 for timeout/abort/maxBuffer; probes read it as a git result | Medium |
| 11 | `scope.ts:1091` | PR files-only discovery treats a failed `gh` call as no files | Medium |
| 12 | `scope.ts:862` | User-level conventions file gets an equal share and truncates the root rules | Medium |
| 13 | `scope.ts:407` | `parseDiffGitHeader` splits a rename whose new path contains ` b/` | Medium |
| 14 | `index.ts:233` | GitLab notice says comments were ignored while the prompt still appends posting instructions | Medium |
| 15 | `parse.ts:101` | Flag-shaped text in a free-form target is stripped as options | Medium |
| 16 | `index.ts:493` | No-changes return drops option notices and partial warnings | Medium |
| 17 | `engine.ts:713` | xhigh verifier prompt omits the recovered recall bias | Medium |
| 18 | `index.ts:417` | Parent model is forwarded without `modelRef` normalization | Medium |
| 19 | `prompts.ts:638` | `renderScope` drops the file list when a context package exists | Medium |
| 20 | `runner.ts:375` | No-time fallback settles on the previous turn's finished message | Medium |
| 21 | `scope.ts:944` | Ambiguous branch resolution runs in the path's git root | Medium |
| 22 | `parse.ts:144` | `--keep-sessions` value check is case-sensitive | Medium |
| 23 | `scope.ts:912` | Scope discovery adds a 10s hard timeout to every git/gh call | Medium |
| 24 | `json.ts:295` | `category` uses raw UTF-16 `slice(0, 40)` | Low |
| 25 | `index.ts:765` | Recursion guard disables itself when the session lookup fails | Medium |
| 26 | `engine.ts:701` | Missing `category` defaults from the finder, misranking cleanup candidates | Medium |
| 27 | `runner.ts:180` | Step-limit recovery fabricates a failure scenario without marking it lossy | Low |
| 28 | `runner.ts:284` | Agent-model cache is written after lookup, so concurrent children duplicate the call | Low |
| 29 | `engine.ts:362` | Pairwise dedup re-tokenizes the same summaries per comparison | Low |
| 30 | `scope.ts:733` | `readCapped` loads the whole conventions file before truncating | Low |
| 31 | `runner.ts:101` | Three hand-maintained dispatch tables over the same schema names | Low |

## Stopping rule

Complete, **fewer than 10 findings**, **no high/medium**. This run is complete
but fails both the count and severity tests.

## Fix turn

All 32 findings were fixed and merged into the main tree. The fix turn changed
the three read-only agent allowlists, `comment.ts`, `engine.ts`, `index.ts`,
`json.ts`, `parse.ts`, `prompts.ts`, `runner.ts`, and `scope.ts`. Fourteen
regression tests were added for the parser, JSON recovery, scope discovery,
the step-limit detector, workflow synthesis, and branch-comment posting; the
suite is now **267 tests**, all passing.

## Next run

Run **run 10 with concurrency 6** (the default is now 6; 4 remains the
fallback). Compare run 9's 4-way result with run 10's 6-way result: if run 10
stalls or drops children, revert to 4. Run 10 is the first run on the merged
fixes and the first 6-way run.
