# code-review-opencode — Self-review 4 — triage and fix plan

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-11.
Result: **15 findings, partial** — 4 finders and the sweep returned no usable
structured output, and one verifier was dropped. The count is down from 32,
but the run is not complete; the partial causes are fixed alongside the 15.

## Findings

| # | Location | Finding | Disposition |
|---|---|---|---|
| 0 | `json.ts:178` | `scanBalanced` aborts at the first unbalanced bracket, so a valid bare-array payload after an unmatched bracket in prose is never parsed | **FIX** — do not break on the first unbalanced fragment; filter to plausible JSON starts and continue. |
| 1 | `json.ts:317` | `asCandidates` rejects the whole finder payload when one candidate is malformed, discarding valid candidates in the text fallback | **FIX** — split the tool boundary (strict, re-prompt) from the text fallback (tolerant, keep valid and report drops). |
| 2 | `json.ts:339` | One verdict without evidence makes `asGroupVerdicts` return null, dropping every candidate at that location | **FIX** — same split: strict tool boundary, tolerant text fallback; the engine already marks missing verdicts partial. |
| 3 | `runner.ts:150` | `CODE_REVIEW_STALL_MS=0` is documented as disabling the watchdog but is coerced to 180000 | **FIX** — parse 0 as disabled; only unset/invalid uses the default. |
| 4 | `index.ts:537` | `parent.model` is read without unwrapping the `{data}` envelope | **FIX** — unwrap `data` before reading the model; share the helper with the runner. |
| 5 | `index.ts:879` | The recursion guard receives the raw `ctx.session.get` result, so a `{data}` session has no visible `parentID` | **FIX** — unwrap the envelope before `isChildSession`. |
| 6 | `engine.ts:844` | The pre-verify semantic-merge fallback no longer merges paraphrased candidates, so duplicates are verified multiple times | **FIX** — conservative fallback: same file+line plus high summary *and* failure-scenario overlap; keep exact-only as the last resort. |
| 7 | `json.ts:137` | `scanBalanced` reimplements `balancedAt` | **FIX** — share the string-aware matcher. |
| 8 | `scope.ts:418` | `countPatchLines` duplicates the hunk walker in `buildContextPackage` | **FIX** — extract one hunk walker. |
| 9 | `engine.ts:233` | `dedupeExact` duplicates the seen-set loop in `dedupe162` | **FIX** — share the keyed dedupe helper. |
| 10 | `engine.ts:819` | `barrierDedup === "key162"` is unreachable (every such cell streams) | **FIX** — remove the dead branch. |
| 11 | `engine.ts:915` | The `sweepDedup` key318 check is subsumed by `sameDefect` | **FIX** — simplify to the shared check. |
| 12 | `index.ts:394` | `verifyFollowUp` and `verifyFollowUpForTarget` duplicate the skill-list fetch | **FIX** — extract one skill probe. |
| 13 | `index.ts:66` | Unused imports after the normalizer refactor | **FIX** — remove them. |
| 14 | `prompts.ts:60` | Local `pluralize` duplicates `pluralWord` | **FIX** — use the shared helper. |

## Partial causes

- **Tolerant text fallback:** findings 1 and 2. The strict tool boundary stays
  (the reference re-prompts on schema failure), but the text salvage keeps
  valid entries and reports the drops so the engine can mark the run partial.
- **Structured-output shape:** accept a bare array and the common `findings`
  alias for candidates; add the exact expected JSON shape to the retry
  instruction instead of a generic “return the object.”
- **Sweep stall:** the sweep hit the 180s stall twice. Raise the default to
  180s (still a no-activity watchdog, not a wall-clock cap) and keep
  `CODE_REVIEW_STALL_MS=0` as the disable switch.
- **Verifier drop:** the tolerant group-verdict fallback keeps the valid
  verdicts and the engine already marks the missing ones partial.

## Stopping criterion

Stop the recursive self-review when **all** of these hold:

- The run is **complete** (`partial: false`; no failed finder, verifier, or
  sweep).
- The report has **fewer than 10 findings**.
- **No high or medium severity findings remain** — only low-severity
  cleanup/docs findings.

Severity mapping for triage:

- **High:** crash, data loss, security issue, corrupt output, or a broken
  core path.
- **Medium:** wrong behavior, silent loss, broken contract, partial review,
  unpostable comment, or a reliability failure.
- **Low:** duplication, dead code, naming, comments/docs, test-fixture
  organization, or a purely cosmetic cleanup.

A partial run never satisfies the criterion, regardless of its finding count.
Fix the partial cause and rerun.

## Next run

Fix all 15 findings, the four partial causes, and rerun
`max --max-findings all --fix`. The target is a **complete** run with a
confirmed count in the single digits and only low-severity findings.
