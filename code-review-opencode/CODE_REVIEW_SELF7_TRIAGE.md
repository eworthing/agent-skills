# code-review-opencode — Self-review 7 — triage

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-11/12.
Result: **32 findings, partial** — four finders (`angle-A`, `angle-C`,
`angle-D`, `reuse`) hit OpenCode's 30-step cap and one verifier returned a
non-object verdict. The report is not eligible for the stopping rule.

## Severity

- **High:** crash, data loss, security, corrupt output, or a broken core path.
- **Medium:** wrong behavior, silent loss, broken contract, partial review,
  unpostable comment, or a reliability failure.
- **Low:** duplication, dead code, naming, comments/docs, fixture organization,
  or a purely cosmetic cleanup.

## Findings

| # | Location | Finding | Severity |
|---|---|---|---|
| 0 | `comment.ts:95` | Numeric-PR guard removed; a dirty worktree can post to its branch's PR head | High |
| 1 | `engine.ts:181` | `canonFile` suffix-matches any absolute path onto a changed file | Medium |
| 2 | `engine.ts:1083` | wf162 synthesis drops reworded verified findings | Medium |
| 3 | `engine.ts:910` | Sweep gaps discarded by shared tokens with a refuted claim | Medium |
| 4 | `index.ts:542` | All-finders-failed fallback loses the `--json` bare-array contract | Medium |
| 5 | `engine.ts:532` | Candidate-declared kind overrides the producing finder's kind | Medium |
| 6 | `scope.ts:142` | `findGitRoot` walks the unresolved symlink path | Medium |
| 7 | `scope.ts:550` | Root `CLAUDE.md` gets half the conventions budget when nested files exist | Medium |
| 8 | `index.ts:746` | Recursion guard refuses `code_review` for every child session | Medium |
| 9 | `parse.ts:141` | `--keep-sessions` strips only the first occurrence | Medium |
| 10 | `index.ts:663` | Grouped-verdict boundary accepts invalid entries instead of re-emitting | Medium |
| 11 | `reportfindings.ts:156` | 32-entry cap truncates by position instead of rejecting | Medium |
| 12 | `comment.ts:54` | GitHub comment hard-codes `side=RIGHT`; removed-line anchors misplaced | Medium |
| 13 | `test/prompts.test.ts:36` | Test reads untracked `sources/skill-code-review/*.md`; ENOENT on clean checkout | Medium |
| 14 | `runner.ts:307` | Idle inference is stale between a retry prompt and the new busy timestamp | Medium |
| 15 | `parse.ts:101` | Extension flags are stripped from free-form targets | Medium |
| 16 | `scope.ts:681` | Range dispatch precedes path detection; a path containing `..` fails | Medium |
| 17 | `index.ts:811` | `--json` bare output calls `synthetic` without `resume: false` | Medium |
| 18 | `index.ts:669` | `code_review_report` discards dropped-finding notes; loss is not partial | Medium |
| 19 | `runner.ts:299` | A live child with no `time` object is classified as gone | Medium |
| 20 | `comment.ts:67` | GitHub Enterprise remotes are treated as "other" | Medium |
| 21 | `index.ts:832` | Completed review spends a model turn to acknowledge its own report | Low |
| 22 | `prompts.ts:673` | Module-level `renderDiff` cache pins the raw diff | Low |
| 23 | `index.ts:697` | `reportedOutcomeHashes` grows without bound | Low |
| 24 | `index.ts:283` | `/verify` resolves a full scope only to test runtime surface | Low |
| 25 | `engine.ts:160` | `canonFile` calls `realpathSync` per candidate | Low |
| 26 | `scope.ts:812` | Serial diff passes recompute the same diff | Low |
| 27 | `json.ts:387` | Missing-evidence sentinel is a duplicated contract | Low |
| 28 | `engine.ts:99` | `EngineOptions.version` is never read | Low |
| 29 | `scope.ts:590` | `Plan.kind` is written but never read | Low |
| 30 | `prompts.ts:391` | `inlineFallback` has no production caller | Low |
| 31 | `README.md:81` | Step budgets documented as 30/20 while the agent files differ | Low |

## Partial causes

- Four finders hit the 30-step cap. OpenCode injects
  `CRITICAL - MAXIMUM STEPS REACHED ... Respond with text only`; the finder
  summarizes in prose and the same-session retry is ignored. Fixed by raising
  finder/sweep `steps` to 60 and adding the fresh formatter recovery.
- One verifier returned a non-object verdict. The tolerant fallback handles
  missing evidence, not a wrong top-level shape; keep the strict boundary and
  add a shape-tolerant text fallback if it recurs.

## Fix turn

All 32 findings were reviewed; **30 were fixed** and **2 were intentionally
skipped**:

- `engine.ts:1083` — lowering the wf162 match threshold would let an invented
  finding inherit a `CONFIRMED` verdict. Unmatched findings already mark the run
  partial, so the silent-loss finding is a deliberate tradeoff.
- `parse.ts:101` — extension flags are intentionally accepted anywhere in the
  command; existing tests require flags after the target. Flag-shaped free-form
  target text is treated as options.

The suite grew to **253 tests** after the fixes and the step-limit formatter
test. The run remains partial (four finders and one verifier), so it does not
satisfy the stopping rule.

## Next run

Rerun `max --max-findings all --fix` after the 30 fixes. The stopping rule is
unchanged: **complete**, **fewer than 10 findings**, **no high/medium**.
