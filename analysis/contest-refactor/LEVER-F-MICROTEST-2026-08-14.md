# Lever F micro-test — plan

## Question
Does the reading-discipline recipe measurably reduce billed cost on a realistic
Critic sub-task, without reducing finding quality?

## Design
- 2 arms x 5 reps = 10 fresh-context subagent runs.
- **Control**: task + the Method Step-4 text verbatim (current HEAD prose).
- **Treatment**: identical, plus the 248-tok reading-discipline recipe.
- Same task, same target, fresh context per rep. Arms interleaved.

## Task (both arms, verbatim)
> Review ownership and state authority in `contest-refactor/scripts/` per Method
> Step 4: map the actual writers of mutable state (do not infer from access
> control alone). Report each finding with `file:line` evidence and a one-line
> claim. Report at most 5 findings, highest-confidence first.

Real target, real structure (76 Python files, ~1.3 MB) — large enough that read
strategy matters, scoped enough to finish in one context.

## Primary metric
`total_tokens` from each run's completion notification. This is billed cost,
the thing Lever F exists to reduce — not a proxy.

## Secondary
- Findings count and whether each cites a real `file:line` (quality guard:
  a cheaper run that finds less is not a win).
- Variance across reps. Per writing-skills, five different shapes across five
  reps means the wording is not binding.

## Pass criteria (pre-registered, before any run)
1. Treatment median `total_tokens` < control median. Any increase = fail.
2. Treatment finds >= as many *verified* findings as control (spot-check every
   cited `file:line` by hand — automated counts overstate both directions).
3. If (1) holds but (2) fails, the recipe is trading quality for cost: reject.
4. If medians are within 5%, treat as no effect and do not ship 248 tokens
   that buy nothing.

## Cost
10 subagent runs on a scoped read-only task.
