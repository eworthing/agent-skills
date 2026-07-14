# Detection probes — token-tiered skill-improvement measurement

A full loop costs ~300k tokens; ~75% is Steps 2–3 (fix, tests, reviewer, gates),
which are identical across RED/GREEN arms and measure nothing about detection.
The entire lens-promotion delta lives in the Step-1 findings list. These tiers
buy the answer at the cheapest sufficient rung; escalate only when the cheaper
tier shows separation (RED-first applied to the measurement itself).

| Tier | Vehicle | ~Cost | Question it answers |
|---|---|---|---|
| 0 | selftests + validators (committed) | free | schema/fixture sanity |
| 1 | decision-diff probe (below) | 25–40k/rep | did the prose change move *detection* at all — improved vs lateral, with reps |
| 2 | Step-1-only loop replay (verbatim loop prompt, stop after Critic emit) | ~100k/arm | in-protocol confirmation, n=1 |
| 3 | full RED→GREEN quad (MEASUREMENT-*.md protocol) | ~600k/fixture | release-gate evidence for a promotion |

Salvage rule: a loop that dies mid-run still holds its detection verdict —
grep the task transcript for the loop's own finding statements before paying
for a re-run (both dead GREEN arms of 2026-07-13 were recovered this way).

## Tier 1 — decision-diff probe

One fresh subagent per rep. Loop model tier (`claude-sonnet-5`); helpers and
executor-tier debates don't apply — the probe executes nothing.

Prompt contents, in order (host-assembled; keep the fixture blind — never
include smell/primary_file/expected):

1. The materialized fixture path (or the fixture `codebase/` read-only).
2. `references/method.md` Steps 1–2 investigation rules + the Evidence Chain
   contract, `references/architecture-rubric.md`, severity anchors.
3. The lens set — **the A/B variable**: control = stack lens + always-included
   per the pre-change skill; treat = same + the changed/new lens text.
4. Output contract: JSON only — `{"findings": [{id, title, severity,
   dimension, evidence[], remedy}]}`. No scorecard, no artifacts, no commits,
   no fix. An empty findings array is a legitimate answer.

Grade each rep:

```
python3 scripts/loop_replay_grade.py <fixture-id> <findings.json> --detection-only
```

Exit 0 = DETECTED, 3 = NOT DETECTED. The grader prints every finding;
**read them** — restraint (near-miss control flagged?) is judged by the
operator, not mechanized, per the microtest doctrine.

Decision rule (fixed before running; same shape as the peer-plan-review
microtest gate): a change is an **improvement** iff treat detects in >= 4/5
reps AND control detects in <= 2/5, with zero restraint failures in treat.
Overlapping distributions = lateral; do not ship on lateral, do not escalate
tiers on lateral.

## Calibration set (probe designs must reproduce these before their results count)

Full-loop ground truth, banked from real runs:

| Fixture | Arm (skill state) | Known verdict |
|---|---|---|
| recomputed-derived-1 | RED `26297a4` / GREEN `27e5071` | miss / catch (D1 pair, MEASUREMENT-2026-07-13.md) |
| startup-blocking-1 | RED `26297a4` | miss (clean severity-floor signature) |
| closure-retention-1 | RED `26297a4` | **catch** — base critic needs no lens for D4-as-planted |

A Tier-1 probe that cannot reproduce this row set (probe-RED misses
startup-blocking, probe-RED *catches* closure-retention) is measuring
something other than the loop's detection behavior — fix the probe, not the
fixture.

## What tiers 1–2 cannot see

Execution-side regressions (fix quality, risk-boundary handling, guardrail
wording in remedies, `what_changed` honesty). Those stay Tier-3 concerns —
which is why Tier 3 remains the release gate, run once per promotion, never
per iteration.
