# code-review-opencode — Self-review 5 — triage and stopping rule

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-11.
Result: **18 findings, partial** — 4 finders and 2 verifiers failed structured
output. The count is down from 32 → 15 → 18, but the run is not complete.

## Severity

- **High:** crash, data loss, security, corrupt output, or a broken core path.
- **Medium:** wrong behavior, silent loss, broken contract, partial review,
  unpostable comment, or a reliability failure.
- **Low:** duplication, dead code, naming, comments/docs, fixture organization,
  or a purely cosmetic cleanup.

## Findings

| # | Location | Finding | Severity | Disposition |
|---|---|---|---|---|
| 0 | `engine.ts:1057` | Text synthesis drops reworded/merged findings but does not mark the run partial | Medium | FIX — set `partial = true` when `unmatched > 0`. |
| 1 | `engine.ts:898` | Sweep dedup over-applies `sameDefect` to workflow cells, dropping reworded distinct gaps | Medium | FIX — use the exact key for workflow cells; keep `sameDefect` for the token path. |
| 2 | `scope.ts:193` | `explicitPathTarget` treats every `@` target as a path, so an `@`-named branch is never resolved | Medium | FIX — try the branch first unless the stripped `@` path exists. |
| 3 | `parse.ts:162` | `parseStructured` stores the typed tool target verbatim, bypassing `cleanTarget` | Medium | FIX — clean the target before storing it. |
| 4 | `runner.ts:259` | Idle check settles a child with `idle` but no `busy` timestamp | Low / review | **REVIEW** — an already-idle child should settle; confirm no false positive. |
| 5 | `runner.ts:204` | Agent-model precedence passes the documented `provider/model#variant` string to `session.create` | Medium | FIX — normalize string and object forms to `ModelRef`. |
| 6 | `scope.ts:703` | The default probe keeps `HEAD~1` even when git rejects it | Medium | FIX — only use a probe revision that `rev-parse` accepts; fall back to the worktree/fresh ladder. |
| 7 | `parse.ts:107` | `bool()` strips only the first repeated extension flag | Medium | FIX — use the same global strip as `take()`. |
| 8 | `runner.ts:202` | Agent-model lookup caches a transient failure as “no configured model” | Low | FIX — cache only successful lookups. |
| 9 | `host.ts:47` | Capability probe requires `session.remove` although the runner calls it optionally | Low | FIX — require only the methods the runner needs; keep optional methods optional. |
| 10 | `parse.ts:252` | The edit-distance typo check flags ordinary words (`flow`, `slow`, `mid`) | Medium | FIX — require the first character to match the level, so these stay targets. |
| 11 | `runner.ts:102` | `hasSchemaShape` re-implements the normalizers | Low | FIX — reuse the normalizer validation. |
| 12 | `index.ts:500` | Three branches hand-build the same `decorate()` argument object | Low | FIX — hoist one helper. |
| 13 | `json.ts:288` | `asCandidates` has no production caller | Low | FIX — remove it or use it from the engine. |
| 14 | `engine.ts:1125` | `engine.ts` re-exports `finderCount` | Low | FIX — remove the duplicate export. |
| 15 | `cells.ts:46` | `Cell.modelEffort` and `Cell.minFindings` are configured but never read | Low | FIX — remove or use them. |
| 16 | `runner.ts:59` | `SCHEMA_EXAMPLE` restates the tool schemas | Low | FIX — derive one example from the schema/normalizer or document it as the fallback. |
| 17 | `test/reportfindings.test.ts:89` | The fixture builder duplicates copies in other tests | Low | FIX — move it to `test/helpers.ts`. |

## Partial causes (must be fixed before a run counts)

- **Verifier text fallback:** keep a verdict with a placeholder evidence and
  mark the run partial; strict tool boundary stays. Accept `reason`/
  `justification` aliases.
- **Finder step budget:** raise finder/sweep `steps` from 20 to 30 and verifier
  from 15 to 20 (documented adaptation; DeepSeek needs more turns).
- **Second retry:** allow one more structured-output retry after an empty
  response, still bounded by the three-failure rule.
- **Stall watchdog:** 180s default; `0` disables.

## Stopping rule

Stop the recursive self-review only when **all** of these hold:

1. The run is **complete** (`partial: false`; no failed finder, verifier, or
   sweep).
2. The report has **fewer than 10 findings**.
3. **No high or medium severity findings remain** — only low-severity
   cleanup/docs findings.

A partial run never satisfies the rule, regardless of its count. Fix the
partial cause and rerun.

## Next run

Fix all 18 findings and the four partial causes, then run
`max --max-findings all --fix` again. If the run is complete, under 10, and
only low-severity findings remain, stop. Otherwise fix the medium/high
findings and repeat.

## Result

All 18 findings were fixed with no skips (216 tests). The reliability follow-ups
were then added: tolerant verdict text fallback with partial marking,
`reason`/`justification` aliases, finder/sweep `steps` 30 and verifier/synth
`steps` 20, and a second structured-output retry (**253 tests**). The next run
is the first one judged against the stopping rule.

Run 6 was aborted at ~22 minutes: eight concurrent max-effort finders saturated
the provider and the retry-after-stall cascade repeated the wait. See
`CODE_REVIEW_SELF6_TRIAGE.md` for the concurrency/stall fixes.
