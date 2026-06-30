# peer-plan-review — efficacy harness

Measures whether the skill's prompts actually elicit good plan reviews — recall of
real defects, precision, format/verdict adherence — and lets you **micro-test a prose
change against a no-guidance control before shipping it** (the writing-skills bar).

This is an *efficacy* harness (does the reviewer output get better?), distinct from
`../scripts/tests/` (does the runner code work?) and `eval-skill.py` (structural score).

## Layout

```
evals/
  fixtures/
    digest-plan.md              # seeded-defect plan (6 blocking, 2 non-blocking, + clean tasks)
    digest-plan.answer-key.md   # ground truth + expected catch sets + domain-context block
  build_prompts.py              # fixture -> prompt variants (baseline + micro-test pairs) in _generated/
  run_reviews.py                # parallel driver over ../scripts/run_review.py
  score.py                      # verdict/recall/format + per-battery control-vs-treat signals
  results/                      # dated result snapshots (committed)
  _generated/, runs/            # reproducible, gitignored
```

## Run

```bash
cd peer-plan-review/evals

# Baseline: cross-family recall / precision / format on the seeded fixture
python3 run_reviews.py baseline   && python3 score.py baseline

# Micro-test: control vs treat wording, 5 reps each (cheap models)
python3 run_reviews.py microtest  && python3 score.py microtest
```

Defaults to the cheapest model that proves the path (Haiku for behavioral batteries,
Sonnet for judgment-subtle ones, Codex-mini for the cross-family check). Edit the
`BASELINE` / `MICRO` matrices in `run_reviews.py` to change providers, models, or reps.
Requires the relevant reviewer CLIs installed (`run_review.py --self-check --reviewer X`).
Codex must run from inside a git repo (`evals/` qualifies).

## Method (writing-skills TDD for prompts)

1. **RED** — run `baseline`; score against the answer key. A defect category missed
   across runs is a candidate prose gap.
2. **Micro-test** — encode the candidate as a `mt-<battery>-{control,treat}` pair in
   `build_prompts.py`. Ship only if `treat` beats `control` over 5+ reps with low
   variance. **Read every flagged match** — regex prescreens, it does not decide
   (a reviewer quoting a hedge to attack it looks like a "credit" hit).
3. **GREEN** — apply the winning wording to `../references/output-format.md` (or the
   relevant reference) verbatim, then re-baseline.

## 2026-06-29 result (summary; full snapshot in `results/`)

5-run baseline (Haiku+Sonnet×3+Codex-mini): verdict **5/5 correct**, format/parse
**5/5 clean**, domain-context two-pass **validated** by controlled std-vs-dom. Of five
micro-tested candidates, **two shipped** (observability lens 1/5→5/5; seam-severity
heuristic 3/4→5/5) and **three were rejected** because the control already passed
(worked example, Pass-B reframe, adversarial reframe).
