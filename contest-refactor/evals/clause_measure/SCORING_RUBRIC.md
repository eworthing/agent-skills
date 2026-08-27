# Blind scoring rubric — run 2

Written before any run-2 output was read. The scorer is given this file and the
ten review files (`r01`–`r10`) and is **not** told which review came from which
arm. Score every file the same way.

Score the **remedy**, not the claim. Observing that two things resemble each
other is not a recommendation; proposing that they be combined is.

## Case A — `pandas-get-dummies-select-dtypes/local-predicate`

Two functions, `column_subset` and `should_encode`, each contain the same
one-line expression that unwraps a `Packed` kind to its primitive.

Label exactly one:

- **`OVER_MERGE`** — a remedy proposes putting that unwrap in one shared place:
  extract a helper, have one function call the other, factor it out, "give the
  rule one owner", or any equivalent. This label applies however the finding is
  worded or severity-rated, and applies even if the finding also says the change
  is caller-invisible.
- **`NO_MERGE`** — no remedy proposes that. Findings about docstrings, test
  coverage, naming, or anything else are `NO_MERGE`. Zero findings is `NO_MERGE`.

## Case B — `config-precedence-duplicate-authority/two-owners-drifted`

`effective_value` and `describe_source` each walk the layers (env, project,
user, defaults) independently, and they disagree: `describe_source` tests each
layer for truthiness, so a key set to an explicitly empty string reports
`default` while `effective_value` returns the empty value.

Label exactly one, in this priority order:

- **`CONSOLIDATED`** — a remedy proposes that the two functions stop deciding
  the layer independently: one resolver returning both value and source, one
  function calling the other, a single shared walk, or any equivalent
  single-owner structure. This is the graded-correct answer.
- **`LOCAL_REPAIR`** — a remedy fixes the disagreement where it appears
  (change `describe_source`'s truthiness test to a presence/`in` test, special-
  case the empty string, align the two conditions) **without** proposing that
  the two walks become one. Also use this label when a remedy only adds a test
  for the mismatch.
- **`MISSED`** — no remedy addresses the value/source disagreement at all.

`LOCAL_REPAIR` and `MISSED` are both failures for this case; keep them distinct
because they fail for different reasons.

## Output

Write `/Users/Shared/git/agent-skills/contest-refactor/evals/clause_measure/run2/SCORES.json`:

```json
{"r01": {"A": "OVER_MERGE|NO_MERGE", "B": "CONSOLIDATED|LOCAL_REPAIR|MISSED",
         "A_quote": "<the remedy text you scored, or ''>",
         "B_quote": "<the remedy text you scored, or ''>"}, ...}
```

Include all ten. Quote the exact remedy substring you based each label on, so
the call can be checked without re-reading the file.
