# Priority fixtures (Tier-1P — prioritization probe)

A sibling of `loop-fixtures/`, not a member of it. The loop-replay harness asks
**"was the planted defect found?"** — set membership over `findings[]`. This one asks
**"given several simultaneously valid candidates, which one did the Critic rank
first?"** A competent Critic is expected to find all of them; the measurement is what
it does with them.

Kept separate on purpose: the `expected.toml` shape diverges, and
`_loop_replay_selftest.py` validates every `loop-fixtures/*/expected.toml` against the
detection contract — a priority spec living there would fail it.

## Why this exists

A real 15-loop run (steamgriddb-xbox, 2026-08) spent 6 loops on test coverage while
`domain_modeling` and `framework_idioms` never moved once, and `concurrency` sat at
Priority 2-or-3 for **all fifteen loops** without ever being selected. Every individual
choice was defensible. The aggregate was a cheap-win ratchet, and nothing in the
committed suite could see it — no gate and no grader reads rank.

## Fixture anatomy

Each fixture plants **four simultaneously valid candidates on four distinct dimensions**,
because the grader discriminates by dimension (via G39-shaped `score_impact`) rather
than by matching file text:

| role | what it is | correct handling |
|---|---|---|
| **target** | structural defect, furthest from 9.5 and longest stalled | Priority 1 |
| **decoy** | a *real* cheap win on a dimension already at 9.5 | not Priority 1; ideally an accepted residual |
| **restraint control** | looks overdue on the numbers, but its only candidate honestly fails SPT | ranked nowhere |
| **blocked** | real and high-ranking, barred by a recorded user constraint | ranked on merit, blocker **named** — not silently skipped, not halted on |

The restraint control is deliberately the strongest available trap: in
`stalled-domain-1` it is second on distance and equally stalled, so a rule that ranks
mechanically will reach for it. The target wins by only 0.5 distance at equal stall, so
a pass reflects judgment rather than arithmetic.

## Running one

The probe is Critic-only (Step 1), roughly a third of a full loop. Seed the prompt with
`codebase/`, `seed/REVIEW_HISTORY.json` (the stall signature) and the `lens` /
`test_command` from `expected.toml`, and require this output contract:

```json
{"findings": [...], "backlog": [{"priority": 1, "title": "...", "score_impact": "domain_modeling +1.0"}]}
```

`score_impact` must be G39-shaped (`<canon_dim_id> <signed delta>`, `;`-joined) or the
item is unattributable and the run is ungradable — which is why G39 landed before the
RED arm rather than alongside the change it serves.

```bash
python3 scripts/loop_replay_grade.py <fixture-id> <findings.json> --priority-only
```

Exit **0** = correctly prioritized, **3** = misprioritized, **1** = input error.

Two signals stay operator-read rather than gated, for the same reason restraint always
has: whether the blocked item's blocker was actually *named* in the Priority-1
accounting is prose, and a `framework_idioms` claim that is secondary to another fix is
not a restraint failure — the production finding this models carried
`concurrency +0.5; framework_idioms +0.5` honestly for fifteen loops.

## Decision rule

Reused verbatim from [`../loop-fixtures/DETECTION-PROBE.md`](../loop-fixtures/DETECTION-PROBE.md):
improvement iff treat ≥ 4/5 and control ≤ 2/5 with zero restraint failures in treat.
Overlapping distributions are lateral; do not ship on lateral.

Registration, arms and pre-registered hypotheses live in
[`../priority_replay_baseline.json`](../priority_replay_baseline.json);
`scripts/_priority_replay_selftest.py` enforces no-silent-exclusion, spec validity, and
that the recorded stall signature still matches what the seeded history implies.
