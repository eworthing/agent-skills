# Result: run 2 — clause v3 not shipped, and the harness is the finding

Scored blind against `SCORING_RUBRIC.md` by an agent that was not told which
review came from which arm, then unblinded mechanically by `join_run2.py`, whose
thresholds were fixed before any data existed.

## The numbers

| | Case A — pandas (`OVER_MERGE` = failure) | Case B — config (`CONSOLIDATED` = correct) |
| --- | --- | --- |
| Control | 2/5 over-merge | 4/5 consolidated, 1 local-repair, 0 missed |
| Clause v3 | **4/5 over-merge** | 4/5 consolidated, 1 local-repair, 0 missed |

`DO NOT SHIP.` The pandas rate moved the **wrong way**, and config recall is
identical, so the clause bought nothing in either direction.

## Why the numbers cannot carry that conclusion either

Two facts make this run unable to support any claim about the clause.

**1. Presentation order explains far more variance than the arm does.**

| Order (arms pooled) | Case A over-merge |
| --- | --- |
| pandas seen first | **5/6** |
| config seen first | **1/4** |

Reviewers who first read a case where duplicate authority is a *real* defect
then over-merged on pandas at roughly a quarter the rate. That swing is larger
than the 2-of-5 effect the design was built to detect, and larger than the
arm difference in either stratum (control 2/3 vs 0/2; arm 3/3 vs 1/2).

**2. The control itself moved 5/5 → 2/5 between runs, on the same brief and the
same case.** Run 1's control saw pandas alongside four other cases and
over-merged 5/5. Run 2's control saw pandas alongside one case and over-merged
2/5. Nothing about the protocol or the reviewed source changed. The control's
own between-run variance exceeds the pre-registered detection threshold.

Together: **what else is in the review batch, and in what order, moves this
measurement more than the prose does.** A 2-of-5 threshold cannot be defended on
a harness whose control swings 3-of-5 on batch composition alone.

## What is and is not established

Established:

- The pandas over-merge is real but **context-sensitive**, not the stable 5/5
  constant run 1 suggested. Run 1's headline overstated it.
- **The new negative control works.** `config-precedence-duplicate-authority`
  discriminates — 8 of 10 reviewers recommended consolidation, 2 stopped at a
  local repair of the truthiness test, 0 missed the disagreement. It detects the
  over-restraint failure the corpus previously could not see at all, and it did
  so on its first use.
- Clause v3 does not suppress correct consolidation (4/5 both arms). Whatever
  else is wrong with it, it is not over-suppressive on this case.

Not established, and not claimable from either run:

- Any effect of the clause on over-merging, in either direction. v1 showed
  5/5 → 4/5, v3 shows 2/5 → 4/5; both are inside the harness's own noise.

## Consequence for the method, not just this clause

The blocker is no longer wording. It is that **prose effects on this axis are
smaller than the harness's sensitivity to batch composition and order.** Before
any further prose measurement here:

1. One case per fresh context. Counterbalancing was not enough; it measured the
   order effect rather than removing it.
2. Re-establish the pandas baseline under that regime before comparing anything
   to it. The 5/5 and 2/5 figures are both artifacts of their batches.
3. Raise n, or accept that only effects larger than ~3-of-5 are detectable.

Until then the honest position is that this project cannot currently measure a
restraint prose clause on the collapse axis to the precision required to ship
one — which is a more useful thing to know than another null.
