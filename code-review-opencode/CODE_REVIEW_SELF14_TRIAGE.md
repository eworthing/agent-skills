# code-review-opencode — Self-review 14 triage

Run 14: `max --max-findings all --fix`, concurrency 4, DeepSeek V4.1 Flash.
Report `e687f979-cbd5-4385-b74b-872cc517e6ba`, complete (`partial: false`,
no warnings), 32 findings, 31 production (`.opencode`) and 1 test finding.

Stats: 10 finders, 64 candidates, 3 dupes, 59 verified, 13 refuted, 32
reported, 59 verifier agents, 0 finder failures.

Severity rubric: **high** = crash, data loss, security, or corrupt core output;
**medium** = wrong behavior, silent loss, broken contract, partial or
unpostable result; **low** = cleanup, docs, naming, efficiency.

## Findings

| # | Location | Finding | Severity | Status |
|---|---|---|---|---|
| 1 | `json.ts:319` | whole-body schema echo accepted as a real result | high | fixed |
| 2 | `runner.ts:54` | `provider/#variant` creates an empty model id | medium | fixed |
| 3 | `runner.ts:588` | cancellation never observed when the host lacks `session.interrupt` | medium | fixed |
| 4 | `index.ts:782` | fix-outcome cache written before delivery; failures swallowed | medium | fixed |
| 5 | `scope.ts:1217` | `HEAD~1` plus dirty tree duplicates every working-tree hunk | medium | fixed |
| 6 | `comment.ts:231` | `samePrBase` strips any first segment, so `release/main` matches `main` | medium | fixed |
| 7 | `parse.ts:175` | attached booleans (`--json=true`) fall into the review target | medium | fixed |
| 8 | `reportfindings.ts:110` | schema violations were dropped/truncated instead of rejecting the call | high | fixed (strict validation) |
| 9 | `engine.ts:388` | 0.55 dedup threshold stops 0.5–0.55 paraphrases from merging | medium | fixed (0.52) |
| 10 | `scope.ts:134` | `quote` leaves `{}`/`~` unquoted, so the shell rewrites paths | medium | fixed |
| 11 | `scope.ts:1378` | PR name-only fallback trims leading/trailing whitespace in filenames | medium | fixed |
| 12 | `cells.ts:381` | zero-line diff returns the full finder fleet instead of the floor of 2 | low | fixed |
| 13 | `comment.ts:345` | renamed-file comment uses the old path; GitHub rejects it | medium | fixed |
| 14 | `format.ts` | `sanitizeControl` preserves a lone `\r` | low | fixed |
| 15 | `host.ts:71` | `isChildSession` guard is unused; unregistered descendants can fan out | medium | fixed |
| 16 | `index.ts:549` | pre-run progress rejection aborts the whole review | medium | fixed |
| 17 | `index.ts:909` | bare `--json` path loses the array when `synthetic` rejects | medium | fixed |
| 18 | `prompts.ts:652` | re-parses joined diff commands instead of carrying the command list | low | fixed (`diffCommands[]`) |
| 19 | `prompts.ts:764` | children re-run the diff even though it is already in the prompt | medium | fixed (main) |
| 20 | `engine.ts:656` | cleanup categories are case-sensitive and can outrank bugs | medium | fixed |
| 21 | `runner.ts:554` | post-`wait` poll reads the full transcript every 2 s with no backoff | medium | fixed |
| 22 | `runner.ts:619` | transcript is fetched twice on the completion path | low | fixed (cached) |
| 23 | `comment.ts:267` | `git remote get-url origin` is executed twice | low | fixed |
| 24 | `engine.ts:640` | dead `c.kind` branch and no-op comparison in `kindFor` | low | fixed |
| 25 | `json.ts:171` | schema-echo detector duplicates the sample values | low | fixed (`samples.ts`) |
| 26 | `json.ts:104` | structured-result key vocabulary duplicated across scanners | low | fixed |
| 27 | `scope.ts:1055` | numeric PR predicate duplicated at four sites | low | fixed (`prTargetNumber`) |
| 28 | `scope.ts:1133` | `needMeta = true` leaves dead fallback code | low | fixed |
| 29 | `scope.ts:1410` | conventions are read when the diff has no changed files | low | fixed |
| 30 | `scope.ts:980` | each conventions file is stat'ed four to five times | low | fixed (size map) |
| 31 | `test/prompts.test.ts:306` | reference equality tests skip when `sources/` is absent | low | fixed (fixtures) |
| 32 | `runner.ts:318` | session-record envelope unwrap duplicated instead of using `host.ts` | low | fixed (`sessionRecord`) |

Totals: **2 high, 16 medium, 14 low**. All 32 are fixed in main.

## Notes

- The run-14 `--fix` turn produced valid patches for most findings; they were
  reviewed and adopted. Two changes were re-applied from main because the fix
  turn did not have them: the included-diff child instruction and per-child
  duration logging.
- `ReportFindings` now rejects the entire call for an invalid verdict, missing
  required field, unknown property, or overlong `short_summary`/`category`,
  matching the reference's strict structured-output loop. The level remains
  tolerant because it is optional metadata.
- The test-only fixture change makes the reference equality checks run in a
  clean checkout; it does not weaken the byte-for-byte assertions.
- No captured parent prompt changed: the prompt corpus hashes, low-prompt
  equality, dispatch, caps, and schemas still pass.

## Next

Production-only pass, not tests/docs:

```
/code-review-opencode max --max-findings all --concurrency 6 .opencode
```

Stop when the production report has fewer than 10 findings and no
medium/high severity.
