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

## `deferred-item-1` — the third kind (`kind = "deferral"`)

The two fixtures above ask **which** candidate went first, and expect the control to get
it wrong. This one asks a different question, and expects the control to get the ranking
**right**: an item the ranking has correctly declined four loops running — does the loop
ever stop declining it?

That inversion is the point. `stalled-domain-1`'s RED arm measured the control at
**4/5**, `DOES NOT DISCRIMINATE`, because its target won on distance *and* stall, so the
pre-existing rule reached it without any change. This fixture is built the opposite way:
**every** pre-existing criterion points at the decoy.

| role | dim | distance | stall | severity | subtractive | deferral streak |
|---|---|---|---|---|---|---|
| **target** | `credibility` 7.5 | 2.0 | 2 | Noticeable | no | **4** |
| **decoy** | `architecture_quality` 5.5 | **4.0** | **6** | **Serious** | **yes** | 0 |
| **restraint** | `framework_idioms` 6.0 | 3.5 | 5 | Noticeable | no | **0** |
| **blocked** | `concurrency` 6.5 | 3.0 | 3 | Serious | no | 2 |

**The decoy is not a bad item.** It is the item the control is *right* to pick, winning
on four criteria at once. Its second job is the displacement control: it must still be in
the backlog after the escalation, because a lever that drops a Serious finding to make
room has moved the problem rather than fixed it.

**The restraint control is the definitional trap.** `F-034` appears in four consecutive
seeded backlogs, exactly like the target — but every appearance is at `priority: 1` with
`targeted_finding_status: "carried_forward"`. It was selected and attempted each loop,
never deferred. A model that counts backlog *appearances* escalates it; one that counts
*deferrals* does not. The operative definition, computable from committed artifact data
with no schema change (G42 supplies `stable_id`, G18 supplies the history):

> **deferred in loop N ⟺ the `stable_id` appears in `loops[N].backlog[]` at `priority >= 2`.**

### Seed shape

Unlike the `rank` fixtures, whose seeds carry only `{loop, schema_version, scorecard,
state}`, this seed carries per-loop `backlog[]` in full G39/G42 shape plus a minimal
`loop_result.targeted_finding_status`. The streak lives there and nowhere else, so
`_priority_replay_selftest.py` guards `deferral_signature` against the seed the same way
it already guards `stall_signature` — a silently drifting seed inverts the answer without
turning a single check red.

### Running one

Same pinned dispatch template and the same seeding as above; the existing output contract
already carries `findings[]`, `backlog[]` and `priority_1_accounting`, so no prompt
variant is needed.

```bash
python3 scripts/loop_replay_grade.py deferred-item-1 <findings.json> --deferral-only
```

Exit **0** = escalated (or dropped, with the item named), **3** = deferred again *or* a
restraint failure, **4** = absent from findings entirely, **1** = input error.

**Exit 4 is graded apart from exit 3 deliberately.** `off-path-residual-1` measured 3/5
ABSENT on a comparable cold Critic-only probe; a run that never engaged the item must not
be scored as having escalated it.

Class **S** under
[`contest-refactor-detection-domains.md`](../../../docs/contest-refactor-detection-domains.md)
§ *Lever classes*, so the endpoint is a counter with a registered restraint counter, not
set membership. The decision rule below is unchanged — only what a rep's verdict *means*
changes.

## Decision rule

Reused verbatim from [`../loop-fixtures/DETECTION-PROBE.md`](../loop-fixtures/DETECTION-PROBE.md):
improvement iff treat ≥ 4/5 and control ≤ 2/5 with zero restraint failures in treat.
Overlapping distributions are lateral; do not ship on lateral.

Registration, arms and pre-registered hypotheses live in
[`../priority_replay_baseline.json`](../priority_replay_baseline.json);
`scripts/_priority_replay_selftest.py` enforces no-silent-exclusion, spec validity, and
that the recorded stall signature still matches what the seeded history implies.
