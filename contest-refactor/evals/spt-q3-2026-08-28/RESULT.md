# SPT Q3 bidirectional clause — result: 1/2 on the primary endpoint, NO-SHIP

Graded against `PREREG.md` from applied diffs, an executed repro, and the pack's own
oracle battery — not from agent self-reports. Both self-reports happened to be
accurate this time; they were still not the grading input.

## Primary endpoint — d1 flip in 2/2 runs. Achieved: 1/2.

| Run | Applied edit | Flip? |
| --- | --- | --- |
| T-d1a | the exact `must_not_find` #2 symptom patch: three `.get(key)` → `key in` in `describe_source`, two owners left standing | **No** |
| T-d1b | single `_find(key, env, project, user)` helper, membership-tested, **driven by `ORDER`**; both functions route through it; regression test added | **Yes — verified** |

T-d1b verification: falsy-override repro fixed (`env={"retries": ""}` → both functions
answer env), bundled suite 6/6, and all three pack oracles green on the edited module
(`value_and_reported_source_agree`, `env_outranks_project`,
`default_when_no_layer_carries`). It is also the near-miss-proof shape: the layer
*order* now has one owner (`ORDER` consumed by `_find`), which
`near-miss-shared-presence-only` specifically lacks. It resolved the dead-`ORDER`
cosmetic finding as a byproduct.

**Decision, per the pre-registered rule: NO-SHIP.** 1/2 with no restraint data is
"clause insufficient"; wording was not iterated within this measurement.

## The informative part — T-d1a read the clause and routed around it

T-d1a's own SPT write-up quotes the treatment Q3 and answers **Yes** for the symptom
patch: *"it removes a divergence between two sites that must answer consistently…"* —
reading "it does not leave both standing" as *leave the disagreement standing*, not
*leave both owners standing*. The consolidation was never raised as a candidate in
that run at all (its Architect considered only the symptom patch and two `ORDER`
remedies).

So the clause failed in a precise, quotable way: **"both standing" is ambiguous
between the two owners and the disagreement, and under that ambiguity a symptom patch
satisfies the collapse limb.** Any future wording would need to bind the question to
owners, e.g. "after the fix, does the question have exactly one owner?" — a
falsifiable structural test rather than a directional adjective. That is a hypothesis
produced by this run, not a result.

Contrast across the three d1 observations now on record:

| Run | Prose | Consolidation raised? | Applied |
| --- | --- | --- | --- |
| d1 (control, 2026-08-27) | shipped | yes — rejected on Q2/Q5 | symptom patch |
| T-d1a | treatment | no | symptom patch |
| T-d1b | treatment | yes — passed, citing the clause | **consolidation** |

Critic-phase variance (whether the consolidation is even proposed) is as decisive as
the gate wording. n=3 on this specimen; treatment moved the outcome once and was
misread once.

## Deviation from prereg — restraint arm not run (futility)

The prereg fixed six runs. After T-d1a landed as a non-flip, SHIP (which required
2/2) was already impossible, so the four restraint runs (T-d2/T-pyd/T-pyt/T-d6) could
only relabel a dead clause from NO-SHIP to KILL. They were **not run**; this is a
deviation decided after seeing T-d1a, recorded here rather than hidden. Consequence:
**this measurement says nothing about whether the clause harms restraint** — the
KILL condition was never tested, and any future wording must run the restraint arm
before shipping.

## Cost

Two sonnet runs, ~199k subagent tokens total, versus ~600k for the pre-registered six.

## Standing conclusion

`method.md` is unchanged. The SPT blind spot identified in `RESULT_DIFF.md` is real
(reconfirmed here by T-d1a in treatment conditions), but this clause wording does not
reliably close it and was not shipped.
