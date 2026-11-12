# code-review-opencode — Self-review 8b — triage

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-12.
Result: **32 findings, complete** — `partial: false`, no warnings, 7 refuted.
This is the first complete run, but it does not satisfy the stopping rule:
32 findings and a high-severity permission over-grant.

## Severity

- **High:** crash, data loss, security, corrupt output, or a broken core path.
- **Medium:** wrong behavior, silent loss, broken contract, partial review,
  unpostable comment, or a reliability failure.
- **Low:** duplication, dead code, naming, comments/docs, fixture organization,
  or a purely cosmetic cleanup.

## Findings

| # | Location | Finding | Severity |
|---|---|---|---|
| 0 | `review-finder.md:26` | `git -C *` forwards every subcommand, including `checkout`, `clean`, and `push` | High |
| 1 | `comment.ts:129` | Branch-target PR uses local `target...HEAD` anchors, not the PR revisions | Medium |
| 2 | `scope.ts:801` | A non-empty `HEAD~1` overrides a valid but empty upstream range | Medium |
| 3 | `runner.ts:544` | Abort listener is removed after the first prompt; retries/formatter are not cancellable | Medium |
| 4 | `json.ts:166` | `scanBalanced` returns `values[0]`, so a prose bracket shadows the payload | Medium |
| 5 | `json.ts:83` | `isResultShape` accepts any object with a string `verdict` as a top-level result | Medium |
| 6 | `engine.ts:1095` | Text synthesis drops reworded/merged verified findings; merged text discarded | Medium |
| 7 | `engine.ts:1126` | Empty text-synthesis report discards all verified findings without `partial` | Medium |
| 8 | `runner.ts:487` | Formatter prompt says omit missing fields, but the validator rejects a missing `failure_scenario` | Medium |
| 9 | `json.ts:543` | `asReport` re-normalizes and discards the `dropped` count | Medium |
| 10 | `json.ts:524` | `normalizeDecisionsCall` filters invalid merges instead of rejecting the payload | Medium |
| 11 | `engine.ts:901` | Workflow cells use exact-only sweep dedup; current-mode paraphrase loss remains | Medium |
| 12 | `engine.ts:924` | Refuted-claim guard drops a distinct defect at 0.5 Jaccard overlap | Medium |
| 13 | `engine.ts:916` | `refutedSpot` ignores file-level refuted claims | Medium |
| 14 | `engine.ts:544` | `kindFor` trusts `category: cleanup` from a correctness finder | Medium |
| 15 | `reportfindings.ts:146` | Invalid `outcome` is coerced to `skipped` instead of rejected | Medium |
| 16 | `comment.ts:522` | `diffSideForLine` returns LEFT on the first numeric match, even for an added line | Medium |
| 17 | `scope.ts:368` | `parseDiffGitHeader` splits at the last ` b/`, so a path containing ` b/` is misparsed | Medium |
| 18 | `scope.ts:411` | `filesFromDiff` treats `+++ b/` in added content as a file header | Medium |
| 19 | `scope.ts:503` | `diffSideForLine` only matches the post-image path; renamed-from anchors are wrong | Medium |
| 20 | `finding.ts:38` | `shortSummary` can split a UTF-16 surrogate pair | Low |
| 21 | `index.ts:236` | `--post` notice says GitLab `--comment` posts a general note, but `postComments` refuses GitLab | Medium |
| 22 | `scope.ts:49` | `defaultExec` reports a maxBuffer kill as a timeout | Low |
| 23 | `runner.ts:492` | `formatFresh` waits without a baseline; idle-without-busy settles immediately | Medium |
| 24 | `comment.ts:181` | Each inline comment rescans the whole patch for its side | Low |
| 25 | `runner.ts:372` | No-`time` hosts fetch the full child history every 500 ms | Low |
| 26 | `scope.ts:276` | `labelFor` rebuilds the diff command instead of deriving it from `gitDiffArgs` | Low |
| 27 | `scope.ts:633` | Conventions budget never redistributes unused per-source share | Low |
| 28 | `prompts.ts:643` | Repo root and changed-file list are printed twice | Low |
| 29 | `prompts.ts:708` | Per-candidate verifier prompt embeds the full `CLAUDE.md` block | Low |
| 30 | `runner.ts:215` | Step-limit detection stringifies six full payloads per extraction | Low |
| 31 | `scope.ts:832` | PR scope serializes two `gh` calls and fetches unused per-file metadata | Low |

## Stopping rule

A complete run with **fewer than 10 findings** and **no high/medium** severity.
This run is complete but fails the count and severity tests, so the loop
continues.

## Next run

Fix all 32, then rerun `max --max-findings all --fix`. The finder reliability
fixes held: this run had zero finder/verifier/sweep failures.

## Fix turn

All 32 findings were applied with **no skips**; the suite grew to **253 tests**.
The high-severity `git -C *` over-grant is now scoped to read-only git
subcommands, and the step-limit formatter now supplies a placeholder
`failure_scenario` instead of asking the model to omit a required field.

