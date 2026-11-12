# code-review-opencode — Structured-output retry — root cause and fix

## Symptom

A finder sometimes ends its turn with no parseable structured result. The runner
logs `no structured result in assistant response`, retries the same session, and
the retry usually succeeds. Run 9 had two such retries (`angle-B`, `angle-D`)
with no step-limit message and no stall.

## Root cause

The finder's final turn is not guaranteed to contain JSON. The schema
instruction asks for a JSON object (or the `code_review_candidates` tool call),
but the model can still answer in prose. The old `fromText` path conflated two
different failures:

- no JSON found in the text, and
- JSON found but the wrong shape.

Both logged `no structured result`, so the retry looked like a parser problem
when it was a model-compliance problem. The retry then re-prompted the same
session, which costs a full extra turn and can repeat the prose.

The step-limit case is different: OpenCode injects
`CRITICAL - MAXIMUM STEPS REACHED ... Respond with text only`, which stays in
context and makes a same-session retry futile. That case already uses a fresh
formatter child.

## Fix

- **Split the diagnosis.** `fromText` now logs either
  `no JSON found in assistant response (<n> chars): <preview>` or
  `JSON found but did not match the <schema> shape`. The preview is the first
  240 characters of the whitespace-collapsed text.
- **Formatter-first recovery for candidates and reports.** When a finder or
  synthesizer returns non-JSON text, the runner creates a fresh formatter child
  with the prose and the schema instruction. The formatter has a small context
  and a full step budget, so it can convert the findings without re-reading the
  diff. If it fails, the same-session retry remains as the fallback.
- **Step-limit recovery stays.** A step-limited child still goes straight to the
  formatter; a same-session retry is skipped because the CRITICAL message is
  still in context.
- **Verdicts keep the reference retry.** Verifier verdicts still use the
  same-session retry, because the candidate context is what the verifier needs
  to quote.

The formatter prompt preserves every finding and supplies a placeholder
`failure_scenario` when the prose does not state one, matching the validator.

## Tests

`test/runner.test.ts` covers:

- a prose-only finder recovered by the formatter with **no** same-session retry;
- a step-limited finder recovered by the formatter;
- a missing `failure_scenario` repaired with the placeholder;
- the three-schema-failure cap still suppressing retries.

Suite: **253 tests passing**.
