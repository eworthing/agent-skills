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

## What attempt 3 measured — variance collapse at N=6

Both arms extended from 3 to 6 passes; harness files verified unchanged by hash, prime regenerated
to the same 9.278.

| arm | mean | SD | spread |
|---|---|---|---|
| BLIND (n=6) | 7.630 | 0.460 | 1.222 |
| HIGH (n=6) | 8.389 | **0.196** | 0.556 |

**Pre-registered verdict: CONFIRMED, marginally.** F(5,5) = 5.538 against the registered 5.050,
p = 0.0418. A high prior does reduce inter-rater variance on identical source. The registered
prediction held in both directions — HIGH's SD rose from the implausibly tight 0.116 to 0.196
exactly as regression to the mean predicts, and BLIND's fell from 0.663 to 0.460 — so the real
effect is about **half** what N=3 suggested (SD ratio 5.7× → 2.35×) and still clears the bar.

**This is weak evidence and should not be reported as more.** The *registered* robust check
disagrees: Brown-Forsythe on absolute deviations from the median gives t(10) = 1.797 against a 2.228
critical value — not significant. The F-test assumes normality and is outlier-sensitive at this n;
blind pass B2 (6.833) does real work in the numerator. Supporting but not decisive: HIGH's spread is
narrower on 7 of 9 dimensions. N=10–12 per arm would settle it.

Also restated at N=6: the mean displacement is **+0.759**, so attempt 2's ≥ 1.0 ratchet bar is still
not met — that REFUTED verdict is now firmer, on twice the data.

### The band unlock — post hoc, and the sharpest thing here

| | BLIND | HIGH |
|---|---|---|
| scores ≥ 9.0 | **0 / 54** | **15 / 54** (Fisher p = 9.9e-06) |
| scores ≥ 9.5 | 0 / 54 | 3 / 54 (p = 0.121, *not* significant) |
| highest score emitted | **8.5** | 9.5 |
| passes reaching ≥ 9.0 | 0 / 6 | 5 / 6 |

Across 54 scores from six independent blind Critics, **not one exceeded 8.5.** Primed Critics
emitted fifteen at 9.0 or above. A prior does not nudge scores by a constant — **it removes a
ceiling.** The blind rater will not enter a band on this evidence that the primed rater enters
routinely.

Why that matters: **every gate that certifies convergence lives above the blind ceiling.** G5's
residual requirement triggers at 9.5, G6 at 10, G21's `HALT_SUCCESS` bar sits at 9.5 across all nine
dimensions. On this corpus at this `skill_rev`, a Critic reading no prior scorecard *cannot reach
`HALT_SUCCESS` at all*; a Critic reading its own prior can. Certification would then be partly a
function of having certified before.

Stated limits: this is **post hoc** — 9.0 is a rubric anchor, not a fitted cutpoint, but it was
chosen after seeing the data and needs its own pre-registration. The ≥ 9.5 comparison, which is the
one that touches the actual gate, is **not** significant on three occurrences.

## Attempt 4 — is the ceiling the corpus or the rubric? (archival, zero cost)

The obvious next probe was a second corpus at N=6, ~1.5M tokens. It was unnecessary: **loop 1 of an
archived run is already a blind Critic pass** whenever no prior `REVIEW_HISTORY` was on disk. The
evidence was sitting in the archives the whole time.

One classification matters first. **Run C's loop 1 is not blind** — the combined history file carries
loop numbers `[1..10, 1..15]`, so Run C's first loop was appended after Run B's ten and that Critic
could read a prior scorecard for the same codebase. Run A, Run B and Run S loop 1 do qualify.

| blind pass | corpus | mean | max | ≥9.0 |
|---|---|---|---|---|
| Run A loop 1 | steamgriddb (C#) | 5.222 | 6.0 | 0 |
| Run B loop 1 | steamgriddb (C#) | 7.333 | 8.5 | 0 |
| **Run S loop 1** | **agent-skills (Python)** | 8.222 | **9.0** | **4** |
| attempts 1–3 ×6 | steamgriddb (C#) | 7.63 avg | 8.5 | 0 |

**Pooled: 81 blind scores, 9 passes, 2 corpora, 3+ skill revisions.**

**First result — attempt 3's stronger reading is refuted.** The 8.5 ceiling is **corpus-specific**. A
blind Critic over a Python codebase emitted 9.0 on four of nine dimensions immediately, so "no blind
Critic scores above 8.5" is a fact about the steamgriddb codebase, not about the instrument.

**Second result — what survives, and it is the part that matters.** Across all 81 blind scores,
**not one reached 9.5** — the threshold G5's residual requirement, G6's 10-anchor and G21's
`HALT_SUCCESS` bar all certify against.

### The natural experiment the archive was hiding

Run C began at Run B's HEAD, so their loop 1s describe the same codebase at most one loop apart:

| | Run B loop 1 (**blind**) | Run C loop 1 (**primed**) |
|---|---|---|
| max score | 8.5 | **9.5** |
| dimensions ≥ 9.5 | 0 | **3** |

Near-identical source. Only the primed pass crosses the gate threshold — on three dimensions at
once, in its first loop, before touching a line of code. That is the claim attempt 3's N=6 test
could not establish (p = 0.121 on three occurrences), showing up for free.

**Caveats, and they are real:** observational, n=1 per run; the archived passes ran the *full*
protocol at different skill revisions, which strengthens the 9.5 claim (more rulesets, still no 9.5)
while weakening any per-pass comparison; `skill_rev` is null in every archived artifact because the
field did not exist yet — the exact attribution gap Change 1 closed, and why the Run B / Run C pair
is suggestive rather than clean, since 29 skill commits also separate them. Run S is the skill
reviewing its own repository and is the sole source of every blind score at or above 9.0.

### A mitigation one rater invented

One LOW-arm pass volunteered that it "read the prior review only after my independent scorecard was
written." It landed at 7.889 — closest of any primed pass to the blind mean, and 1.389 above its own
arm's lowest pass. Score first, read the prior only to compute the delta. Cheap, and it needs its
own attempt before anyone believes it off one observation.

## Attempt 5 — re-analysis with the right estimator (no new sampling)

Attempts 1–3 analysed a 9-dimension × 6-rater design with raw spread, sample SD and an F-test on
grand means. That collapses each rater to one number and throws away the structure that decides the
practical question. The standard analysis is a two-way variance decomposition plus the **intraclass
correlation**. On the data already collected:

| variance source | BLIND | PRIMED |
|---|---|---|
| dimension (signal) | 20.8% | 61.4% |
| **rater severity** | **59.3%** | 10.2% |
| rater × dimension | 20.0% | 28.4% |
| **ICC(2,1)** — one rater, absolute | **0.166** | **0.575** |
| ICC(3,1) — consistency, severity removed | 0.412 | 0.621 |
| raters for 0.80 reliability (Spearman-Brown) | **20** | 3 |

**Nearly 60% of blind-arm variance is which rater, not which dimension.** That is
[rater severity](https://languagetestingasia.springeropen.com/articles/10.1186/s40468-020-0098-3) —
the effect Many-Facet Rasch Measurement exists to
[separate and adjust out](https://www.repository.cam.ac.uk/items/db7bc448-f687-4f78-b7d1-e2b71f18a058).
It also explains attempt 1's headline mechanically: "pass B strictly lower on 9/9" is a rater main
effect, which is the *most benign* form of unreliability, because a main effect is modellable.

### The cut-score consequence

Single-rater SEM is **0.283**, so the 95% band is **± 0.56**. Clearing G21's 9.5 bar by more than
measurement error requires an observed score of **≥ 10.06 — above the scale maximum.** On the mean of
three passes it requires ≥ 9.82.

**A single Critic pass cannot certify the 9.5 threshold.** This holds independently of every
anchoring question in attempts 2–4.

### Calibration or contagion? Both — and the mixture is the point

The primed arm's ICC is higher partly because its between-dimension variance is 3× the blind arm's.
Either the anchor fixed the scale and let raters resolve real differences, or raters copied the
prime's profile. ICC cannot tell those apart; correlating each arm's 9-dimension profile against the
prime's can.

| profile correlation | r |
|---|---|
| BLIND vs PRIME | +0.361 |
| **HIGH vs PRIME** | **+0.844** |
| HIGH vs BLIND | +0.756 |

Priming more than **doubled** the profile's correlation with the prime, so raters adopted the
anchor's *pattern* and not merely its level. But the primed profile still correlates +0.756 with the
blind one, so it is not purely the anchor reflected back. And once severity is removed, primed raters
disagree about individual dimensions *slightly more* (residual SEM 0.346 vs 0.283).

**Priming's entire measurable benefit is severity removal.** Everything else it does — level
inflation, band unlock, shape capture — is cost.

## What this layer licenses

**Retracted before it shipped:** an earlier draft of this recommendation set proposed blinding the
`HALT_SUCCESS` challenger, which `halt-verifier.md:48` currently hands the candidate scorecard. On
these numbers that would move the *only* independent certification check in the skill from ICC 0.575
to **ICC 0.166** — the least reliable configuration measured. The prior is not purely a bias; it is
also doing a calibration anchor's job.

1. **Certification cannot rest on one pass.** Licensed by measurement alone: require N ≥ 3
   independent passes at the `HALT_SUCCESS_candidate` step and certify on the **median** (robust to
   one severe rater), or state an explicit guard band. Independent of the anchoring debate.
2. **Replace the self-prior anchor with an external calibration set** — fixed scored exemplars with
   justified scores, shipped with the skill. This is
   [standard practice for LLM judges](https://galileo.ai/blog/calibrate-llm-judge-human-annotations)
   and [reduces volatility while raising agreement](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0339920).
   It buys the severity correction without the self-confirmation loop. **Supersedes** the
   "mechanize score-then-read" proposal — score-then-read leaves the rater uncalibrated, which is
   measurably the worse failure — and **absorbs 2b**, since the real fix is scored exemplars rather
   than more prose anchor text.
3. **Publish the noise floor** in `architecture-rubric-scoring.md § Score Anchors` and the HALT
   handoff templates: ICC(2,1) = 0.17 blind / 0.58 primed, SEM 0.28, ~59% of blind variance being
   rater identity.
4. **Consider judging `delta` directly** rather than deriving it from absolute scores. Honest
   caveat: pairwise is not a clean win —
   [preferences flipped in ~35% of cases against 9% for absolute scores](https://arxiv.org/abs/2504.14716),
   and pairwise discards the per-dimension diagnostic axis this skill exists to produce. Supplement,
   do not replace.

**Methodological lesson:** a two-way ANOVA on the *first six* passes would have produced every number
above. Attempt 3 spent ~1.5M tokens extending N to answer a narrower question than the same data
could already answer. Reach for the standard estimator before buying more samples.

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
