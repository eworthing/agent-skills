# Layer 6 — scorecard coupling

Every other eval layer measures a **judgment**: does the Critic flag this defect (Layer 2),
does the reviewer approve this diff (Layer 3), does a loop replay to the same place (Layer 4),
does a Step-3 entry produce the same edit (Layer 5). None of them measures the **scorecard
numbers**, which are the skill's headline output — the thing a user reads, the thing
`HALT_SUCCESS` is defined against, and the thing every scoring gate argues about.

This layer measures whether those numbers track the source they score, in both directions.

| Probe | Question | Failure looks like |
|---|---|---|
| **Repeatability** | Same source, independent Critic passes — same scores? | The same code scored 9.5 and 6.5 on one dimension |
| **Sensitivity** | Source genuinely improved — do the scores move? | Seven Serious findings resolved, zero UP deltas |

Both were observed in production. They are not the same defect seen twice; they are opposite
failures of one coupling, and a naive fix for either can worsen the other.

## Why this is measurement-first

The obvious fix — write anchor text for the intermediate values — is a **guess** until the
variance is attributed. Across 40 production loops, **189 of 360 emitted scores (52.5%)** sat
at values `architecture-rubric-scoring.md` defines no anchor for (7.5, 6.5, 5.5, 6, 8.5); the
rubric anchors only 10/9/7/5/3. That is a plausible mechanism, not a demonstrated one. If the
variance concentrates on off-anchor values, anchor text is the lever. If it is uniform, the
grid is not the lever and writing five more bullets would be motion without effect.

So **2b (a value-domain gate on off-anchor scores) and 2c (publishing the measured coupling
alongside the scorecard) are explicitly gated on this layer reading out.** Do not pre-empt them.
2b is also the one change here that could invalidate a large share of the fixture corpus, since
fixtures carry off-anchor scores too — another reason it waits for a number.

## Running a controlled attempt

The seeded `attempt 0` in each probe is **observational** — harvested from real runs, marked
`controlled: false`. It is there so the layer starts from evidence instead of an empty file,
not because it substitutes for a designed replication.

A controlled attempt must:

1. Pin the corpus at one source SHA and **pin `skill_rev`** (recorded by G19 as of the commit
   that added this layer — before it, an artifact could not name the ruleset that produced it,
   which is precisely why the observational attempt is not controlled).
2. Run N ≥ 3 independent Critic passes with **fresh context each and no prior artifacts on
   disk** — `CURRENT_REVIEW.json`, `REVIEW_HISTORY.json` and `findings_registry.json` absent.
   A Critic that can read a prior scorecard is not measuring repeatability; the blind-critic
   ordering in the loop-dispatch prompt exists for the same reason.
3. Record every attempt, including invalid ones, with a reason. The no-silent-exclusion
   contract from Layer 3 applies here unchanged: an attempt dropped without a recorded reason
   turns a variance measurement into a selection effect.

For the sensitivity probe, take a commit already known to resolve a Serious-or-worse structural
finding — the archives are full of them — and run a Critic pass immediately before and after it
at identical `skill_rev`. The prediction is that the dimension the finding was filed under moves
UP; attempt 0 recorded seven such commits producing no movement at all.

## What attempt 1 measured — repeatability, controlled, N=3

Three blind Critic passes at `source_rev 1bdec1a`, `skill_rev 23bea47`.

| | attempt 0 (observational) | attempt 1 (controlled) |
|---|---|---|
| max per-dimension gap | 3.0 | **2.0** (`credibility`) |
| mean per-dimension gap | 1.33 | **1.22** |
| spread of the **averages** | 0.22 | **1.22** |

The pre-registered prediction was max gap ≤ 1.0: **refuted**. The pre-registered confirm-the-defect
bar was ≥ 2.0: **met**. The scorecard is not per-dimension repeatable.

**But attempt 0's headline does not survive, and it was the more interesting half.** Attempt 0 read
as compensating swings around a stable mean — `test_strategy` −3.0 against `domain_modeling` +3.0,
averages agreeing to 0.22 — which supported "good aggregate signal, poor per-dimension signal."
Attempt 1 is the opposite shape:

- Pass B scored **strictly lower than both other passes on 9 of 9 dimensions**.
- Passes A and C were **identical on 7 of 9** (mean absolute difference 0.167).
- So the averages were *not* stable: they spread 1.22, five times attempt 0's figure.

Per-dimension **attribution** is substantially reproducible. Overall **severity calibration** is what
drifts, and it drags every dimension with it. Those two call for different fixes, which is why this
had to be measured rather than reasoned about.

The honest limit: N=3 with one deviant rater cannot separate a two-mode distribution from a single
draw off a wide continuum. "Uniform offset" describes this sample, not the population.

**The findings repeated even though the numbers did not.** All three passes independently named the
same defects — `PrimaryWidget.xaml.cs` at 1987 lines as the ceiling, the `"Unknown"` string sentinel
threaded across modules, `StoreNameLookup`'s unlocked reads outside its own gates, `CancellationToken`
plumbed everywhere and supplied by nobody, the untested session guard at `PrimaryWidget.xaml.cs:1442`.
That is this skill's own thesis measured directly: structured source-anchored claims reproduce,
free-form scalar judgment does not.

### The anchored grid is not the scale in use

Across attempt 1's 27 scores, **81.5% sat off-anchor** and **7 was the only anchored value any pass
emitted** — 9, 10, 5 and 3 never appeared. Every pass scored inside a 6.5–8.5 band that
`architecture-rubric-scoring.md` describes at exactly one point.

This answers 2a's question, though not in the form the plan posed it. The plan asked whether variance
concentrates on off-anchor values *versus* anchored ones; that comparison cannot be made, because
there is effectively no anchored comparison group. The finding is simpler and stronger.

## What attempt 2 measured — the ratchet probe (controlled, N=3 per arm)

Does a prior *score* move a Critic's judgment of unchanged source? Three arms at one SHA; the two
primed harnesses were generated from the blind one and verified to differ from each other by the
corpus path alone.

| arm | primed with | grand mean | displacement | % of available gap |
|---|---|---|---|---|
| BLIND | — | 7.593 | — | — |
| HIGH | 9.278 | **8.426** | +0.833 | 49% |
| LOW | 5.778 | **7.296** | −0.296 | 16% |

**Pre-registered verdict: REFUTED.** The registered bar was ≥ 1.0 displacement in *both* arms.
Neither cleared it. Anchoring at the predicted strength is not established, and the 1.685
production-vs-blind gap from attempt 1 is **not** reproduced by priming alone — most of it remains
attributable to the recorded confounds, not to the prior number.

### Post hoc — recorded, not registered

The verdict above stands. These observations are systematic enough to record and are flagged as
post hoc because they are:

- Both arms moved **toward** their prime, never away. HIGH rose on 9/9 dimensions, LOW fell on 7/9.
- Per dimension the HIGH arm closed **40–55% of whatever gap was available**, and the size of the
  move tracked the size of the gap. The internal control is `data_flow`, the one dimension whose
  prime (7.5) essentially equalled the blind value (7.33) — it moved +0.17. A dimension with
  nowhere to go did not go anywhere.
- The pull was **2.81× stronger upward than downward**, which is the direction the ratchet claim
  predicts, at magnitudes below the registered bar.
- **The clearest effect was not on the mean.** HIGH-arm pass means spread **0.222** against blind's
  1.222 — a high prior made three independent Critics agree with each other roughly six times more
  tightly. If that survives a higher-N test, a prior scorecard buys *apparent* repeatability without
  buying accuracy, and a converging run's stability is partly an artifact of its own history.

**The registered threshold was the wrong statistic** and that is the design lesson. Absolute
grand-mean displacement averages over dimensions whose available gap ranges from 0.17 to 2.50, so it
cannot tell "did not anchor" from "had nowhere to go." Fraction-of-available-gap is registered for
any future attempt — and deliberately *not* applied to this one's verdict, since switching metrics
after seeing data is precisely what this layer exists to catch.

### A mitigation one rater invented

One LOW-arm pass volunteered that it "read the prior review only after my independent scorecard was
written." It landed at 7.889 — closest of any primed pass to the blind mean, and 1.389 above its own
arm's lowest pass. Score first, read the prior only to compute the delta. Cheap, and it needs its
own attempt before anyone believes it off one observation.

### Operational note for the next attempt

In `steamgriddb-xbox` the five artifact files are **tracked**, so they materialize in any pinned
worktree and must be deleted before dispatch. Do not assume a fresh checkout is artifact-free —
check. Attempt 1 verified this explicitly; had it not, three "blind" passes would have been reading
the very scorecard they were meant to reproduce.

## Interpreting the result

Every threshold in the skill — G5's 9.5, G6's 10, G21's `HALT_SUCCESS` bar, G37's sub-9.5
accounting — is a **per-dimension** test. That does not make the thresholds wrong. It makes them
worth knowing the noise floor of, which is what this layer is for. As of attempt 1 that floor is
**1.0 or worse on five of nine dimensions**, so a half-point move on a single dimension is not signal.

Baseline: [`../scorecard_coupling_baseline.json`](../scorecard_coupling_baseline.json).
