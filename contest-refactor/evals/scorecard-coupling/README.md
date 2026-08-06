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

## Interpreting the result

The averages were **stable** across the observational attempt (7.11 vs 7.33, a 0.22 shift) while
per-dimension attribution moved by a mean of 1.33 and a max of 3.0. That asymmetry is the useful
part: it says the scorecard is a reasonable aggregate signal and a poor per-dimension one, which
is the opposite of how the rubric's gates use it. Every threshold in the skill — G5's 9.5, G6's
10, G21's HALT_SUCCESS bar, G37's sub-9.5 accounting — is a **per-dimension** test.

That does not make the thresholds wrong. It makes them worth knowing the noise floor of, which
is what this layer is for.

Baseline: [`../scorecard_coupling_baseline.json`](../scorecard_coupling_baseline.json).
