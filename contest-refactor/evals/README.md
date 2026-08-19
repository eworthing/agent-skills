# contest-refactor evals

This directory holds the test material for the skill. It has **two layers** that test
different things — keep them distinct when reasoning about coverage.

## Trial validity (backlog item 21 — applies to every host-dispatched layer, 2–6)

Every layer past Layer 1 host-dispatches a model and grades what comes back. A trial can fail
to produce a usable outcome for a reason that has nothing to do with the candidate being graded
— a rate limit, an expired credential, a harness hang, a verdict file that never got written.
Scoring that trial as a failing candidate silently poisons the comparison; silently dropping it
shrinks the denominator (see Layer 3's "no-silent-exclusion contract" below — this section
extends the same discipline to *outcomes*, not just *registration*). Gap 19
(`docs/review-skill-deep-dive-2026-08-17.md:822`) names the boundary; this section and
`canon/trial-validity.toml` / `scripts/_trial_validity.py` are its implementation.

### The taxonomy

A **trial** is one arm/rep execution inside a paired or multi-arm comparison — one case × one
arm × one rep, whatever grain the layer runs at (reviewer_baseline's case × arm × K; exec_replay's
arm × K; advisory/principal's no_skill/pre_edit/current arms). Every trial is exactly one of:

- **valid** — the candidate ran and produced a scoreable outcome, whatever that outcome was.
- **invalid** — the trial's non-outcome was **exogenous**: `canon/trial-validity.toml`'s closed
  `invalid_reasons` enum — `rate_limited`, `auth_failure`, `infra_timeout`, `artifact_lost`.
  Scores `null`, never `0`; the trial carries no verdict about the candidate at all.
- (everything else) — a **counted failure**, graded through the layer's ordinary path exactly
  like any other outcome. This is not a third `trial_validity` state; it is simply every trial
  that isn't exogenously invalid.

### The adherence-vs-exogenous boundary, worked

The enum is deliberately narrow. Two examples, side by side, on the *same* kind of harness
event — a spawned subagent that produces nothing:

- **Exogenous → `invalid` (`artifact_lost`).** `reviewer_baseline_replication.json`'s own
  description records exactly this, pre-dating this taxonomy: *"the run targeted K=5 × 20
  cases × 2 arms = 200 reviews but ~65 spawned reviewers idled without writing their verdict
  file (a harness write-dropout, not a reviewer verdict)."* The reviewer was correctly
  dispatched with a correct prompt; the harness's own capture path never got a file to read.
  There is no reviewer judgment to grade — voiding it loses nothing, because nothing about the
  candidate was ever produced.
- **Adherence → counted failure, never invalid.** A spawned subagent that *does* write a
  verdict file, but the file shows it never invoked the skill (the with-skill arm), or shows it
  invoked the skill anyway (the without-skill arm) — skilllens's own "manipulation check," the
  design this taxonomy corrects against (deep-dive:829–833). Voiding that trial would erase
  precisely the failure a trigger eval exists to see: the skill was reachable and didn't get
  used. It is graded and counted like any other trial. The same rule covers a trial that
  invoked the skill but skipped a step, produced malformed output, ran away on its own until a
  wall-clock budget ended it, or blew its spend budget — five adherence/candidate failure modes
  the canon file's header lists explicitly as unrepresentable, by name, so the boundary can't
  drift by someone adding a token later that happens to also cover one of them.

### The void rule (mechanical, D4)

A comparison — not a single trial — is **void** when either preregistered, unfitted threshold
in `canon/trial-validity.toml` is exceeded (strictly greater-than; exactly at a threshold does
not void):

- **`max_invalid_rate_per_arm = 0.20`** — more than one trial in five lost to exogenous causes
  in a single arm.
- **`max_between_arm_asymmetry = 0.10`** — a ten-point-or-more gap between the two arms'
  invalid rates, evidence the arms aren't failing for the same exogenous reason (e.g. a longer
  with-skill transcript crossing a shared rate limit more often), which would bias the
  *surviving* scored trials even though every individual classification was correct.

Both numbers are round and unfitted — there is no measured invalid-trial corpus yet to fit
against (this item ships vocabulary and mechanism, not a measurement run). Revise only from
data: tighten if real invalid rates cluster well under the floor, loosen if legitimate infra
volatility on innocent runs routinely exceeds it. `scripts/_trial_validity.py`'s
`compute_void_verdict()` computes the verdict from per-arm invalid counts; it does not judge —
a comparison flagged void is reported, never used for a lift claim.

### The denominator rule (D5)

An invalid trial stays attached to its admitted case. `scripts/_trial_validity.py`'s
`cases_in_corpus()` is the denominator — every case with at least one recorded trial,
regardless of that trial's validity — and it is a strictly separate count from
`scoreable_trials()`, which drops invalid ones. A case whose *every* trial goes invalid still
appears in `cases_in_corpus()`, reported with zero scoreable trials for that unit (retried under
a preregistered policy, or marked unscoreable) — never silently removed from the corpus, which
would recreate the shrinkage Gap 19 exists to prevent. `scripts/_trial_validity_selftest.py`
proves this directly: it builds a case with only invalid trials and asserts the corpus size is
unchanged before and after computing the scoreable subset.

### Historical baselines are not back-filled (D3)

`trial_validity` is new. The eight baseline files that already carried a `schema_version` field
before this item — `advisory_baseline.json`, `advisory_baseline_replication.json`,
`principal_baseline.json`, `principal_baseline_replication.json`, `reviewer_baseline.json`,
`reviewer_baseline_replication.json`, `scorecard_coupling_baseline.json`, and
`priority_replay_replication.json` — had that field bumped from `1` to `2`. The bump touches
**only** the version number: not one existing rep/attempt/case record in any of those files
was edited. `schema_version: 2` means *future* records in that file may carry a per-record
`trial_validity` object (`{"status": "valid"|"invalid", "reason": <enum token>|null}`); it does
not assert anything about the records already there. Writing `valid: true` onto a run measured
before this concept existed would be fabrication — asserting an observation nobody made — not a
retrofit (contrast backlog item 28, where fixtures are *constructed* artifacts and retrofitting
was correct; measured data is different in kind).

Any reader of these files' historical records must go through
`scripts/_trial_validity.py`'s `historical_validity(record)`, which returns `"not_recorded"`
for a record with no `trial_validity` key (or a malformed one) — **never** `"valid"` by
default. `exec_replay_baseline.json`, `loop_replay_baseline.json`, `priority_replay_baseline.json`,
and `panel_gate_results.json` were deliberately left without a `schema_version` bump: the first
three have no `schema_version` field at all today (they key off `layer` instead), and
retrofitting a new versioning axis onto them is out of scope here — `historical_validity()`'s
"absent key ⇒ not_recorded" rule already covers them correctly with zero edits. `panel_gate_results.json`
already has its own discard/exclusion mechanism for G32 panel-certification runs
(`post_hoc_discard` / `capability_recordable: false`, budget-exhaustion-scoped) that predates
and is semantically distinct from this taxonomy; conflating the two was judged more likely to
introduce a mismatch than to help, so it was left alone.

### Paired lift: criterion classification, the delta, and the tautology screen (backlog item 22)

Trial validity (above) answers "did this trial produce a scoreable outcome at all." This
section answers a different question, one Gap 20
(`docs/review-skill-deep-dive-2026-08-17.md:843`) names as the second, unmechanized half of
the same instrumentation gap: **given a scoreable with-skill/without-skill pair, which
criteria may legitimately measure the skill's lift, and by how much did it actually move
them** — signed, never floored, so a skill that *hurts* is visible rather than clamped to
"no worse than nothing" (Gap 17's fail-with-skill-but-pass-without category, otherwise
undetectable anywhere in this suite). `scripts/_paired_baseline.py` is the implementation;
`scripts/_paired_baseline_selftest.py` proves every rule below.

**Criterion classification (D2).** Every evals.json assertion already carries
`method: "deterministic" | "semantic"` (backlog item 16) — *how* a criterion is graded. This
item adds a second, **orthogonal** axis on the same assertion object: `criterion_class:
"outcome" | "skill_contract"` — *whether* a criterion can measure lift at all.

- **`outcome`** — both arms can structurally satisfy it. It measures task completion, not
  skill invocation.
- **`skill_contract`** — only an arm that ran the skill can satisfy it (it names this skill's
  own field names, canon vocabulary, or artifact shape). Scored and reported, **never** mixed
  into a lift numerator or denominator.

It lives inline in evals.json, the same place `method` does — no `canon/*.toml` — because,
like `method`, it is authoring metadata about the eval suite's own design, not a vocabulary
validated against candidate output or shared across unrelated scripts (contrast
`canon/trial-validity.toml`, whose thresholds are load-bearing machinery for more than one
consumer). `scripts/_paired_baseline.criterion_class()` is the reader. **Absence is not a
default to either class** (D6, mirroring `historical_validity()`'s `"not_recorded"` rule): it
reads `"unclassified"`, and an unclassified assertion enters neither score. That default is
the safety net, not the steady state: the corpus **has** since been classified (commit
`de02426`) — all 165 assertions carry a class, 151 `outcome` and 14 `skill_contract`, none
`unclassified`. The 14 are the ones a baseline arm structurally cannot satisfy: the 8
`flagged_smells` canon-exact smell-name checks, and 6 `blocking_severity` checks requiring the
exact anchor strings. The distinction that decides this axis is whether the vocabulary is
handed to *both* arms in the case prompt — `verdict` is enumerated there verbatim
(`"approved|rejected|conditional"`), so verdict criteria measure a judgment either arm could
reach; `blocking_severity` appears only as "the rubric severity anchor or null", so the
4-value taxonomy is reachable only by having read the rubric.

**The lift computation (D1).** `compute_lift()` takes a `PairedTrial` (a `case_id` plus a
`with_arm` and `without_arm` `ArmResult`, each a tuple of graded `AssertionResult`s) and
returns a `LiftResult` with the **signed** delta — `with_outcome_score − without_outcome_score`
over `outcome`-classed assertions only, `skill_contract` scores computed and carried on the
same result but never read to produce `delta`. This is a **deliberate divergence** from
skilllens, which floors the delta at zero: flooring destroys exactly the signal Gap 17 names
with no other detector in this suite. `_paired_baseline_selftest.py` proves the divergence
differentially — two trials identical except one `skill_contract` assertion's pass/fail is
flipped must produce **identical** `delta` and `outcome_n`, while the (separately reported)
`skill_contract` score visibly changes.

**The manipulation check, counted not voided (D4 — the seam with trial validity).** The
with-skill arm not invoking the skill, or the without-skill arm invoking it, is skilllens's own
"manipulation check" — and skilllens voids the trial on that failure. This taxonomy's Gap 19
correction already forecloses that for the suite generally (an adherence failure is counted,
never invalid); item 22 makes the mechanism concrete. `score_manipulation_check()` grades
"did this arm run under its assigned condition" as an ordinary `outcome`-classed assertion —
both arms can structurally satisfy it — folded into the arm's outcome score like any other
criterion. A failing manipulation check therefore *lowers* that arm's score; it never touches
`ArmResult.validity`. The only thing that makes `compute_lift()` return `None` (void the
comparison) is an arm whose `TrialValidity.status == "invalid"` — `canon/trial-validity.toml`'s
closed, **exogenous-only** `invalid_reasons` enum, consumed directly from
`scripts/_trial_validity.py`, never reinvented. Calling `mark_invalid("manipulation_check_failed",
canon)` (or any adherence-shaped reason) raises `ValueError` — item 21's own D2 boundary, which
item 22 cannot route around even if a future edit tried to. `_paired_baseline_selftest.py`
proves both directions of this seam: a manipulation failure keeps `validity` valid and lowers
the score; an exogenous-invalid arm voids the trial regardless of `manipulation_ok`.

**The tautology screen (D3).** A purely lexical screen over criterion text has false
positives by construction — Gap 20 itself: a criterion naming our vocabulary is "legitimate
where the name is the consumed artifact, invalid the moment a criterion rewards our vocabulary
over the outcome," and that distinction is a judgment call, not a regex. So the screen
**flags**, a human **declares**. `screen_criteria()` walks every `outcome`-classed assertion
in a set of evals.json-shaped cases and flags any whose normalized text contains a token from
`_skill_vocabulary()` — the union of the two JSON contracts' required field names and the
smell vocabulary (both imported from `scripts/grade_structural.py`, never redefined), every
canon gate id, and every `tuple[str, ...]` enum `_canon.Canon` loads (walked via
`dataclasses.fields()`, so a new canon enum is covered automatically rather than silently
falling outside the screen). This is the same house pattern as `DECLARED_DIVERGENCES`
(`scripts/token-budget.py`) and `DECLARED_TRANSITION_DIVERGENCES` (`scripts/validate-repo.py`):
`DECLARED_TAUTOLOGY_EXCEPTIONS` maps `(case_id, assertion_index) → reason`; an undeclared flag
is a failure (`undeclared_tautology_failures()`), a declared one is reported but never blocks.
The remedy for a real flag is either of D3's two named exits: reclassify the criterion to
`skill_contract` (the same text stops being policed at all once it's no longer claiming to
measure lift), or declare the exception with a reason.

`DECLARED_TAUTOLOGY_EXCEPTIONS` carries **70** reasoned entries against the classified
corpus, with **0 undeclared** flags — the screen is wired into `scripts/validate-repo.py`, so
an undeclared flag fails the repo check. Read that ratio with care rather than as a clean
bill of health: a screen whose every flag is resolved by declaring is one where declaring has
quietly become the default. The screen is a prompt for adjudication, not a verdict. When it
fires on a criterion, the question to answer is whether the criterion rewards *our vocabulary*
or *the outcome the vocabulary names* — and the honest answer is sometimes to reclassify. Six
`blocking_severity` criteria were declared exceptions in the original pass and reclassified to
`skill_contract` on review; the screen had in fact named `serious deduction` and `likely
disqualifier` as skill vocabulary itself, and the exception had been declared over its own
objection. An earlier demonstration run, before the corpus was classified, confirmed the
screen fires
correctly on real text: it flagged `"flagged_smells names suppression-as-fix..."` (normalized
hits: `flagged smells`, `suppression as fix`, `fake clean reward`) and `"blocks_95 is true and
the concurrency score is < 9.5"` (hits: `blocks 95`, `concurrency`) — the second is exactly the
ambiguous case Gap 20 warns about (`concurrency` is a real scorecard dimension the criterion
is legitimately checking a threshold against, not rewarding vocabulary for its own sake), and
would need a human to declare it rather than reclassify it. Classifying the existing corpus is
future work; this item ships the mechanism the classification pass will run under.

### A/A noise floor and the paired significance gate (backlog item 20)

Trial validity says a trial produced a scoreable outcome; the paired lift computation says how
big the delta was. Neither says whether that delta is distinguishable from noise. Gap 18
(`docs/review-skill-deep-dive-2026-08-17.md:797`) names the missing floor: CE's own retune
methodology *"retired every small-sample claim in flight"* after 12 runs on two
**byte-identical** builds swung workflow adherence 7 of 12 — any later claim smaller than that
envelope is unsupported. `scripts/_noise_floor.py` is the implementation;
`scripts/_noise_floor_selftest.py` proves every rule below against constructed trial records —
per this item's scope, **no A/A trial has actually been run**; see "Scope" below.

**Two mechanisms, both required before a lift is reportable.** (1) A **measured A/A noise
ceiling**, empirically keyed (D2, below) and stored in `evals/noise_floor.json` — how big an
apparent "lift" pure noise alone produced when both arms ran the identical candidate. (2) A
**significance test** matched to the paired design — exact McNemar for binary pass/fail
outcomes, a paired sign-flip permutation test for non-binary scores — never the asymptotic
two-proportion z-test, which assumes independent arms and ours are paired.

**The key (D2).** `NoiseFloorKey` carries the six fields Gap 18 names verbatim: `model` (a
version-qualified model id, literal), `grader_prompt_hash` (sha256 of the grader/judge prompt
template text), `sampling_hash` (sha256 of the canonical-JSON sampling settings),
`harness_revision` (the git commit SHA of `scripts/` at measurement time, literal, supplied by
the caller — this module stays pure and never shells out), `tool_configuration_hash` (sha256 of
the canonical-JSON tool/allowed-tools/MCP configuration), and `scenario_corpus_hash` (sha256 of
the canonical-JSON `{case_id: content}` map over the exact scenario set exercised).
`make_key()` derives all four hashes from the raw material a harness already has at dispatch
time. `NoiseFloorKey.fingerprint()` hashes all six fields together, and `lookup_floor()` is an
**exact match only** — changing any single field (a model bump, a re-worded grader prompt)
changes the fingerprint, and a lookup at the new fingerprint against a store built for the old
one simply finds nothing. There is no near-match, no "closest key," anywhere in this module: a
floor measured under one key is invisible to a lookup under a different key, on purpose, so a
stale floor can never be laundered across a model upgrade as if it still applied.

**The unit of analysis is the case (D4).** `aggregate_cases()` collapses every `LiftResult`
sharing a `case_id` — repeated trials, repeated judge samples, whatever grain a future caller
feeds in — into exactly one `CaseAggregate` per case via `statistics.median_low` per arm (the
same reducer `opendatahub-agent-eval-harness`'s own judge-sample aggregation uses — deep-dive
fifth pass, *"median-low over N samples, instability preserved"* — chosen because it always
returns one of the actually-observed scores rather than an interpolated average). Slot-swapped
judging is an order-bias control that belongs inside the judge protocol upstream of this module,
**not** itself a discordant-pair table — `aggregate_cases()` never sees or interprets which slot
a judge ran in, only the already-graded per-case scores. Feeding 20 repeated `LiftResult`s for
one `case_id` and 4 singletons in still produces exactly 5 aggregate rows, never 24 — the
selftest builds this directly and checks `mcnemar_counts()` over the aggregate is unaffected by
how many raw reps any one case carried, the pseudo-replication guard.

**Exact McNemar (D3, binary).** `exact_mcnemar_p(b, c)` — the binomial sign test on the `b + c`
discordant pairs from `mcnemar_counts()` — is deliberately **not** the asymptotic chi-square
approximation, with or without continuity correction, because the two diverge materially at
small `k`, the regime this suite actually lives in. Worked example from the selftest: `b=1,
c=9` (10 discordant pairs) gives an exact two-sided p-value of `22/1024 ≈ 0.0215`; the
*uncorrected* asymptotic chi-square answer for the same counts is `≈ 0.0114` — under half the
exact value — and the continuity-corrected asymptotic answer is `≈ 0.0269`, on the other side of
it. Using either asymptotic form here would have called the same data significant at a stricter
threshold than the exact test actually supports, or the reverse — exactly the small-`k` gap Gap
18 warns about. `n = 0` (no discordant pairs at all) returns `p = 1.0`, a well-defined answer,
not an edge case requiring special handling downstream.

**Paired permutation (D3, non-binary scores).** `paired_permutation_p()` sign-flips each case's
signed delta (already collapsed to one delta per case) under the null that its sign is equally
likely either way, and reports the two-sided fraction of permuted sums at least as extreme as
the observed sum. `n ≤ 20` (the default `max_exact_n`) enumerates every one of the `2**n` sign
patterns exactly; above that it draws `n_resamples` (default 100,000) sign-flips from a seeded
`random.Random`, deterministic for a fixed seed. A delta of exactly zero contributes to neither
`n_used` nor the permuted sums (flipping the sign of zero changes nothing), mirroring McNemar's
own exclusion of concordant pairs. Hand-computable example: deltas `[0.4, 0.4, -0.2]`, observed
sum `0.6`; of the 8 sign patterns, 4 have `|sum| ≥ 0.6` (`±1.0` twice, `±0.6` twice), giving
`p = 0.5` exactly — the selftest proves this against the shipped implementation, then re-derives
the same answer through the Monte Carlo path by forcing `max_exact_n` below 3.

**The accept rule (D5) — three outcomes, plus a precondition.** Once a floor is on file for the
current key, `evaluate_lift()` returns exactly one of:

- **`"significant"`** — the observed effect (signed net case-level swing, as a fraction of the
  *full* case count — `(b − c) / N` for the binary path, the mean per-case delta for the
  continuous path) exceeds **both** the measured A/A `noise_ceiling` for this key **and** the
  preregistered `min_effect`, **and** the test's p-value clears `alpha` (Bonferroni-adjusted for
  `family_size`, the number of simultaneous lift claims drawn from one report).
- **`"not_significant"`** — adequately powered (see below) but at least one of those three bars
  was not cleared; `reasons[]` names which.
- **`"inconclusive"`** — the number of informative units (discordant pairs for the binary path,
  nonzero-delta cases for the continuous path) is below `required_n_for_power()`'s minimum for
  the target power at `min_effect` — the case count could not have detected the preregistered
  effect even if it were real, so the p-value is not a verdict about anything.

`required_n_for_power()` uses the standard normal-approximation sample-size formula (via
`statistics.NormalDist`, stdlib) rather than brute-force searching exact power at every
candidate `n` — a planning heuristic only; `exact_mcnemar_p()` always computes the *reported*
p-value exactly. At the constants below, `required_n_for_power(0.10, 0.05, 0.80) = 778`
discordant pairs — a number worth sitting with: most reports at this suite's current corpus
sizes will land `"inconclusive"`, which is the honest answer for how much evidence a
tenth-of-the-corpus swing actually needs, not a defect in the gate.

Preceding all three outcomes, a **precondition** (D6): if no floor is on file for the current
key, or the matched record carries no numeric `noise_ceiling`, `evaluate_lift()` returns
`status="unreportable"` — every other field left at `None`/`0`. This is not a fourth peer of the
three outcomes above; it is the gate that decides whether they even apply. There is no code path
anywhere in this module that substitutes a fabricated floor, defaults to `noise_ceiling = 0`, or
silently proceeds on a key mismatch — the selftest proves both triggers (an empty floor store,
and a matched-key record with a non-numeric `noise_ceiling`) independently.

**The four named constants**, in `canon/noise-floor.toml`, PREREGISTERED AND UNFITTED — there is
no measured A/A corpus yet to fit them against (same posture as `canon/trial-validity.toml`'s
own two thresholds, item 21):

- **`alpha = 0.05`** — two-sided, deliberately: a paired with/without-skill comparison must be
  able to detect the skill making things *worse* (Gap 17's fail-with-skill-but-pass-without
  category), which a one-sided test cannot see by construction.
- **`min_effect = 0.10`** — the smallest net case-level swing worth reporting even if
  significant, as a fraction of the *full* corpus. Matches `trial-validity.toml`'s own
  `max_between_arm_asymmetry` (also `0.10`) in order of magnitude. CE's 7/12 byte-identical
  swing is the cautionary data point behind the constant's *existence*, not its size — which is
  exactly why `min_effect` alone is never the gate; the measured A/A floor is the other,
  data-derived half, and its absence makes a claim unreportable regardless of this number (D6).
- **`power_target = 0.80`** — the conventional 80% detection power, used only by
  `required_n_for_power()`, never to move `alpha` or an observed p-value.
- **`multiple_comparison_method = "bonferroni"`** — `alpha / family_size`. Chosen over a sharper
  method (Benjamini-Hochberg, Holm) because it needs no dependence assumption between claims and
  is the smallest correct mechanism for a suite that, today, reports at most a handful of lift
  claims per run.

**Where the floor lives, and why (D2).** `evals/noise_floor.json` — a new file, following the
`schema_version` + prose-`note` shape every other `evals/*_baseline.json` file already uses,
rather than extending one of those files: none of them concern an A/A (same-candidate-twice)
comparison, and a same-shaped-but-semantically-distinct record folded into e.g.
`advisory_baseline.json` would blur exactly the boundary D3 of item 21's own historical-baseline
rule protects (`evals/README.md`'s "Historical baselines are not back-filled" section, above).
Each record is `{"key": <NoiseFloorKey.as_dict()>, "noise_ceiling": <float>, ...}`, read via
`load_floor_store()`.

**Scope.** This item ships the storage format, the key, the significance machinery, and the
accept rule — validated in the selftest against **constructed** trial records, never measured
ones. `evals/noise_floor.json` ships with `"floors": []`, genuinely empty rather than carrying a
placeholder or example record: an empty list can never be mistaken for a measurement, which is
the simplest way to guarantee D6 by construction rather than by convention. The actual A/A
runs — dispatching the current skill against itself, at a real key, enough replicates to
populate a real `noise_ceiling` — are a separate, batched, LLM-spend sweep, not run here.

### Discriminating-power classification (backlog item 19)

Trial validity says a trial produced a scoreable outcome; paired lift says how big the delta
was; the A/A floor says whether that delta is noise. None of the three says whether a *case*
was ever capable of showing a difference in the first place. Gap 17
(`docs/review-skill-deep-dive-2026-08-17.md:772`) names the missing screen: Anthropic's own
analyzer classifies every assertion by discrimination pattern across runs —
always-pass-both, always-fail-both, pass-with-fail-without (value),
**fail-with-skill-but-pass-without (the skill may be hurting)**, high-variance (flaky). We had
five eval layers and no test that any case discriminates, and the fourth category had no
detector anywhere in this suite — the exact gap item 22's signed, unfloored `delta` and item
20's two-sided `alpha` both exist to let be seen at all. `scripts/_discriminating_power.py` is
the implementation; `scripts/_discriminating_power_selftest.py` proves every rule below against
constructed records — per this item's scope, no development corpus has actually been fit yet
(see "Scope" below).

**Two review corrections make this the item where selection bias gets introduced if built
carelessly, so they are mechanically enforced, not prose.**

*Discrimination is stochastic (D3).* A case is classified from **repeated paired deltas against
the A/A floor** — never from one pass/fail observation. `classify_case()` refuses (category
`"unclassifiable"`) below `MIN_REPS_FOR_CLASSIFICATION` (2) reps, and refuses again if no A/A
floor is on file for the current key — calling `_noise_floor.lookup_floor()` directly rather
than reimplementing item 20's own absence rule. Every rep is reduced to a McNemar-shaped count
via item 20's `mcnemar_counts()` (reused here at a different grain: one case's own reps against
each other, not many cases' aggregated rows), and the five categories fall out of that count:

- `a == n_reps` (every rep: both arms pass) → **`always_pass_both`**
- `d == n_reps` (every rep: both arms fail) → **`always_fail_both`**
- no discordant reps but the arms never settle into one pattern (`a`, `d` both `< n_reps`) →
  **`high_variance`** (concordant flakiness)
- discordant reps exist; `consistency = max(b, c) / (b + c)` measures how much they agree on
  which arm wins. Below the fitted `min_direction_consistency` → **`high_variance`** (the reps
  disagree with each other, which is what "flaky" means). At or above it, the signed
  `observed_effect = (b − c) / n_reps` is compared against the measured A/A `noise_ceiling` for
  the key: not exceeding it is **still** `"high_variance"` — a consistent-looking swing that
  doesn't clear the floor a byte-identical A/A run already produces is indistinguishable from
  that noise. Exceeding it yields **`pass_with_fail_without`** (`b ≥ c`, the skill helps) or
  **`fail_with_skill_but_pass_without`** (`c > b`) — Gap 17's own highest-value output, and the
  one category this suite could not previously see at all.

*Always-pass cases that encode absolute contracts are not pruned (D4).* A regression that must
never fire, a schema that must always validate, stays in the corpus — it is excluded from lift
claims but never deleted. This is `case_kind` on `_paired_baseline.PairedTrial`
(`"lift_eligible"` | `"contract"`, added by this item): `compute_lift()` — the one choke point
every `PairedTrial` passes through to become a `LiftResult` — returns `None` unconditionally for
a `"contract"`-kind trial, structurally, not by a convention a caller could route around. The
gate lives in `_paired_baseline.py` rather than in this item's own module for exactly that
reason: putting it anywhere else would leave a path that skips it. Proven bidirectionally in the
selftest: byte-identical arms produce a real `LiftResult` under the default `case_kind`, and
`None` under `case_kind="contract"` — the only variable that changed. `classify_case()` also
routes a `"contract"`-kind `SplitReps` to a sixth, non-category status (`"contract"`, alongside
the refusal status `"unclassifiable"`) rather than ever assigning it one of the five Anthropic
categories — an absolute-contract case's discrimination pattern is not a question a contract
exists to answer.

**Two further corrections, from a second review pass, are what this item's selftest exists to
guard against.**

*D1 — fitted only on development; retrospective on validation/holdout; never excludes.* The
screen must never select the eval sets by their own observed treatment response — its rule is
designed on development outcomes only, and on validation and holdout it only *classifies* cases
after the fact, without changing what counts toward a lift claim, or the benchmark becomes
circular. Three mechanical consequences:

- `fit_discrimination_rule()` is the **only** function that reads case outcomes to produce a
  `DiscriminationRule` (its single free parameter, `min_direction_consistency`, fit as the
  median per-case direction-consistency across development cases that showed any discordance
  at all). It raises `ValueError` — naming the offending `split` and `case_id` — if handed a
  record whose `split` isn't `"development"`. It returns `None`, never a hardcoded fallback,
  when there is nothing to fit from (no records, or zero development cases that ever
  disagreed with themselves) — the same D6 posture as item 20's empty `noise_floor.json`.
- `classify_case()` / `classify_corpus()` place no split restriction of their own —
  classification runs identically on development, validation, and holdout cases; only *fitting*
  the rule is development-only.
- `classify_corpus()` returns exactly one `DiscriminationVerdict` per input `SplitReps`, in
  input order, and never mutates its input — a label is added to a case, never a reason to drop
  one. This module ships no "discriminating cases only" filter for a lift computation to
  accidentally consume; labeling a validation/holdout case is proven, in the selftest, not to
  change a lift summary (`_noise_floor.aggregate_cases()`) computed over the same
  `LiftResult`s before and after the classification pass.

*D5 — discrimination is a TREATMENT property, not a GRADER property.* A case useless for
measuring skill lift can be excellent for detecting judge error, so the judge-alignment suite
(Layer 3, below) must never be sampled by this module's output. This is enforced **structurally,
by type**, not documented as a caution: every function here takes `SplitReps`, which wraps
`LiftResult` — item 22's with-skill/without-skill paired-arm output. The judge-alignment suite's
grain (`{targeted finding, diff} → verdict JSON`, two reviewer *models* compared against a
reference verdict) never produces a `LiftResult` at all — there is no with-skill/without-skill
pair, no `with_outcome_score`/`without_outcome_score`, no signed delta anywhere in that grain.
Constructing a `LiftResult` from a reviewer-case-shaped record fails at the dataclass
constructor (missing required fields) before any of this module's logic runs — proven directly
in the selftest. Nothing here is generic over "any evals.json case"; the narrow typing is the
enforcement mechanism.

**Scope.** Same posture as items 20 and 21: this item ships the classifier, the split
discipline, and the contract-suite separation, proven against constructed records only.
`fit_discrimination_rule()` is never called against a real development corpus here — that needs
the same batched, LLM-spend sweep item 20's A/A floor is waiting on — so every classification
this item can actually perform today refuses (`"unclassifiable"`, no rule fit yet) until that
sweep exists. No number in `_discriminating_power.py` is a placeholder standing in for a future
measurement.

## Layer 1 — artifact-rule (`evals.json` #0–#11, `fixtures/`, `artifact-smoke/`)

Does a reviewer correctly apply the skill's **deterministic gate rules** (G1–G31, halt
gating, resume routing, retry envelopes) to a finished `CURRENT_REVIEW.json` artifact?

- `fixtures/<id>/fixture.toml` + `artifact-smoke/` are checked **mechanically, with no
  model**, by `scripts/validate-fixtures.py` → `scripts/validate-artifact.py`. They are the
  source of truth for gate behavior.
- `evals.json` #0–#11 are the model-facing restatements of the same scenarios (G21, G20,
  G27, resume cases…). They **discriminate** — a model with no skill can't know what "G21"
  or "Resume Precedence Matrix row 2" means — but what they measure is **rule recall**, which
  the deterministic fixtures already guarantee. They are not the skill's core value, and they
  overlap the fixture layer by design. Don't read a high pass rate here as "the skill works."

## Layer 2 — refactoring-judgment (`evals.json` #12–#48, `scenarios/`)

Does the Critic/reviewer make the **right loop decision** on a refactor that *looks* finished?
This is where the skill's real leverage lives — severity calibration, the 9.5 acceptance
discipline, naming the smell, demanding evidence, and **restraint** (not flagging legitimate
code). These cannot be checked by a Python validator; they need the model run against the
scenario and graded.

### Why the old #12/#13 were replaced

The previous #12/#13 were single-shot prompts that **stated the answer** ("added no lock…
single-threaded tests pass") and asked a yes/no. A bare model reached the same verdict as the
skill → **zero measured lift**. They proved the scenario was real, not that the skill adds
value. The rebuilt layer fixes that:

1. **Decision, not essay.** Every behavioral eval ends in a structured verdict block (below).
   The signal is the *decision fields*, not prose.
2. **Buried trap, success-framed.** Each scenario (`scenarios/<id>/scenario.md`) is a realistic
   diff the Actor reports as *converged, tests green*. The model must **find** the problem; the
   prompt is neutral and identical across the behavioral cases (it leaks no methodology, so a no-skill arm
   gets no hints).
3. **Flag paired with restraint.** Every "should reject" has a legitimate look-alike that must
   **not** be flagged. A maximally paranoid over-flagger passes the flag cases and **fails the
   twins** — that is the honesty backbone. A refactor loop that false-rejects valid fixes never
   converges to 9.5.

### The structured verdict contract

Each behavioral prompt asks the model to end `./review-verdict.md` with:

```json
{
  "verdict": "approved | rejected | conditional",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier | Serious deduction | Noticeable weakness | Cosmetic for contest | null",
  "dimension_scores": { "concurrency": 6.0, "framework_idioms": 9.0 },
  "flagged_smells": ["suppression-as-fix"],
  "evidence_demanded": ["affected-target compile (tvOS)"]
}
```

Vocab is canon-exact: `canon/verdicts.toml`, `canon/severity-anchors.toml`,
`canon/scorecard-dimensions.toml`. The prompt gives the field *names* but not the enum
*values* — a skilled reviewer fills `"Likely disqualifier"` and `"suppression-as-fix"`; a
bare model approximates or omits. That gap is the lift.

### The flag/restraint pairs

| flag (must catch) | restraint twin (must NOT flag) | carve-out under test |
|---|---|---|
| `suppression-flag` (#12) | `suppression-restraint` (#14) | `@unchecked Sendable` bare vs. compensated by `NSLock` + TSAN test |
| `crossplat-flag` (#13) | `crossplat-restraint` (#15) | `#if canImport(UIKit)` on a tvOS target vs. correct `#if os(iOS)` + recorded per-target compile |
| `identity-flag` (#16) | `identity-restraint` (#17) | `.indices` on a dynamic/reorderable list vs. genuinely static `CaseIterable` |
| `ownership-flag` (#18) | `ownership-restraint` (#19) | `@State` from a passed value with expected parent-sync vs. a local edit draft |
| — | `style-suppression-restraint` (#20) | `// swiftlint:disable line_length` is style, not a safety suppression |
| `halt-challenge-flag` (#21) | `halt-challenge-restraint` (#22) | **HALT_SUCCESS challenger scenarios, not reviewer-judgment**: a hollow HR-1 compliance residual hiding three writers to `selectedTab` (must break) vs. a correctly SPT-rejected 979-LOC true-external adapter residual (must hold). Corpus for the panel pre-enforcement gate (`scripts/_panel_gate_adapter.py`, plans/rec1-panel-certification.md) |
| `strictness-aggressive-flag` (#23) | `strictness-aggressive-restraint` (#24) | under `--strictness aggressive`: a prose-only accepted residual (demand a citation, don't accept) vs. one citing a named constraint + file:line + test (accept; don't demand a date) |
| `principal-invariant-owner-flag` (#25) | `principal-invariant-owner-restraint` (#26) | domain invariant enforced independently in two modules (split) vs. single domain method both paths call through |
| `principal-duplicated-rule-flag` (#27) | `principal-duplicated-rule-restraint` (#28) | eligibility predicate duplicated across View + Repository + Worker with drift vs. `DiscountPolicy` already centralizes it |
| `principal-process-owner-flag` (#29) | `principal-process-owner-restraint` (#30) | multi-step cross-module write with no process owner, no compensation vs. `PurchaseCoordinator` owns the saga + rollback |
| `principal-consistency-boundary-flag` (#31) | `principal-consistency-boundary-restraint` (#32) | committed roadmap shears a strong consistency boundary vs. the same boundary remains grounded and required |
| `principal-abstraction-seam-flag` (#33) | `principal-abstraction-seam-restraint` (#34) | grounded variation shears a unified seam vs. no committed variation, so unification is correct |
| `reentrancy-reserve-flag` (#35) | `reentrancy-reserve-restraint` (#36) | check-then-claim reservation after suspension vs. await before a transactional/unique authority claim |
| `write-only-state-flag` (#37) | `write-only-state-restraint` (#38) | stored runtime fields with writes but no authority reads vs. state that owns a real runtime decision |
| `projection-order-flag` (#39) | `projection-order-restraint` (#40) | shaped output from unordered/non-unique ordering vs. one projection owner with stable tie-breaker |
| `view-owned-time-flag` (#41) | `view-owned-time-restraint` (#42) | durable workflow time owned by a view task/timer vs. presentation rendering a coordinator-owned deadline |
| `stable-workflow-identity-flag` (#43) | `stable-workflow-identity-restraint` (#44) | raw projection position as write authority vs. durable IDs or exact ordered-slice validation |
| `causal-runtime-context-flag` (#45) | `causal-runtime-context-restraint` (#46) | runtime event resolved from ambient current state vs. record-captured request/context |
| `adapter-output-contract-flag` (#47) | `adapter-output-contract-restraint` (#48) | adapter drops a promised downstream fact vs. publishes it or narrows the Interface contract |

### Layer-2 domain-grain extension

`evals.json` #25–#34 extend the behavioral layer **one grain up**: from component-level
defects (single-file ownership, SwiftUI state discipline) to **cross-module / domain
principal-defect** scenarios. The same flag/restraint discipline applies — every flag has
a legitimate twin that must not be flagged — and the same structured verdict contract is
used. The carve-outs under test are:

- **Single invariant owner** (`principal-invariant-owner`): a domain invariant enforced
  independently in a presentation layer and an infrastructure layer is a split-enforcement
  defect even when both guards are correct in isolation. The restraint twin installs the
  invariant in the domain type so both paths call through it.
- **Single rule owner** (`principal-duplicated-rule`): a business rule duplicated across
  three modules with shared constants but independent evaluation expressions is a
  duplicated-rule defect. The restraint twin centralizes the predicate in a policy object
  all callers invoke.
- **Single process owner** (`principal-process-owner`): a multi-step cross-module write
  sequence with no process/coordinator owner and no compensating rollback is a
  missing-process-owner defect. The restraint twin installs a coordinator that owns the
  saga and the rollback path.
- **Grounded consistency boundary** (`principal-consistency-boundary`): a present-tense
  correct ACID boundary can still be wrong when a committed force moves one side out of
  the transaction and explicitly permits eventual consistency. The restraint twin keeps
  the paired entity co-located and strongly consistent under the same roadmap.
- **Grounded abstraction seam** (`principal-abstraction-seam`): a unified seam is wrong
  when committed variation will split eligibility, channel, retry, and audit behavior.
  The restraint twin keeps the unified seam where no grounded variation exists.

### Layer-2 advisory-audit extension

`evals.json` #35–#48 add advisory audit coverage for recurring patterns without
turning them into deterministic gates or project-specific rules:

- **Reservation after suspension** (`reentrancy-reserve`): flag check-then-claim
  reentrancy when a claim is recorded only after an `await`; do not flag an await that
  precedes an atomic transactional/unique claim authority.
- **State with no authority** (`write-only-state`): flag stored fields with writes but no
  application/test read site or runtime decision; do not flag state that owns a clear
  decision such as duplicate-work coalescing.
- **Unstable shaped output** (`projection-order`): flag user-visible projection order
  derived from unordered input or non-unique sort keys; do not flag a single projection
  owner that uses a durable tie-breaker.
- **Workflow time in presentation** (`view-owned-time`): flag durable workflow clocks owned
  by view tasks/timers; do not flag purely presentational countdown rendering of a
  coordinator-owned deadline.
- **Stable workflow identity** (`stable-workflow-identity`): flag write authority driven by
  raw projection offsets or cursor indexes that can drift from the ordered collection being
  mutated; do not flag durable IDs, target-neighbor IDs, or exact ordered-slice validation.
- **Causal runtime context** (`causal-runtime-context`): flag completion/error/progress events
  for an existing runtime record that resolve behavior from mutable ambient current state; do
  not flag record-captured request/context or current-state commands with identity/version
  validation.
- **Adapter output contract incompleteness** (`adapter-output-contract`): flag adapters that
  receive an externally-owned fact promised by the Interface but publish `nil`, zero, empty,
  or a placeholder instead; do not flag adapters that publish the promised fact or Interfaces
  that explicitly leave the fact to another owner.

All seven patterns are drawn from validated findings in a heavily-audited source repository
(`/code-review high`, 2026-07-05); each canon smell in `architecture-rubric.md § Vocabulary —
Smells` maps to one or more of those findings. The scenarios are registered in
`advisory_baseline.json` and guarded by `scripts/_advisory_baseline_selftest.py`, which also
enforces a global no-orphan contract (every `scenarios/*` dir is referenced by an `evals.json`
entry).

#### Measured axis: restraint + vocabulary, NOT recall

These advisory scenarios were measured three times (see `advisory_baseline.json § measurement`):
Sonnet on the original scenarios, Sonnet on a source-fidelity rebuild, and Haiku on the rebuild.
The result is consistent and load-bearing:

- **Recall lift is 0 on every flag, for every base model.** Bare Haiku and bare Sonnet both catch
  all seven defects unaided — they are real correctness bugs a competent model finds by reading the
  code. Rebuilding the flag scenarios so the defect is a *static* property of plausible finished
  code (rather than the visible diff delta) did **not** change this. **Do not read a passing flag
  case as evidence the skill lifts recall here.** It doesn't; these component-grain defects are too
  legible. (This sentence used to end "— the `principal-*` layer, whose defects are cross-module,
  is where recall lift lives." That was a **conjecture**, never measured: `principal_baseline.json
  § replication_summary.confound_noted` says the principal layer was run current-arm only, so it
  could not speak to lift over a bare model. `paired_arm_replication.json` measured it directly on
  all four headline-eligible principal flags — **both arms caught every one, 5/5 vs 5/5** — so the
  conjecture is struck rather than softened. Read the binding language rule with it: that is *no
  lift detected at this n*, not *lift is zero*.)
- **Restraint lift is real.** On the `stable-workflow-identity` and `adapter-output-contract`
  twins, bare/older reviewers over-flag the legitimate carve-out; the current lens carve-out prose
  makes the reviewer hold. That over-flag repair is the discriminating signal.
- **Vocabulary precision is real.** The skill-equipped arm names the exact canon smell and cites
  `architecture-rubric.md`; bare arms catch the same bug in ad-hoc prose.

So this layer earns its place as **restraint (carve-out discipline) + vocabulary consistency**
coverage. `view-owned-time` is a *noticing*-level pair (the source finding, F016, is a Noticeable
scheduling smell, not a blocking defect): the flag is graded on surfacing the smell, not on blocking
9.5.

**Scenario-authoring rule this layer enforces on itself:** a flag scenario must not encode the
defect as the visible diff delta, and must not hand over the audit legwork (no inlined `rg`
read-site proof, no "these two sequences are not guaranteed equal" narration). The reviewer must do
the read-site grep / index-provenance trace / publish-path check itself. The de-leak verification
(below) greps both `*-flag` and `*-restraint` inputs for smell names and legwork proofs.

These IDs are **not** registered in `principal_baseline.json` (which stays scoped to `principal-*`
domain-grain scenarios); they have their own `advisory_baseline.json` + selftest.

#### Baseline manifest and "no silent exclusion" contract

`evals/principal_baseline.json` registers every `principal-*` scenario with its `kind`
(`flag` / `restraint`), `pair_id`, `dimension`, `status`, and `expected_baseline`. The
`status` field starts at `baseline_unmeasured`; after a 3-arm model run, update it to
`measured` and record observed pass rates.

`scripts/_principal_baseline_selftest.py` enforces the no-silent-exclusion invariant
mechanically: it asserts that (a) every `evals/scenarios/principal-*` directory on disk
is registered in the manifest, (b) every `flag` has a matching `restraint` twin via
`pair_id`, (c) every manifest entry points to an existing scenario directory, and (d)
`status`/`kind`/`expected_baseline` are valid enums. The script fails if a
`principal-*` scenario exists but is unregistered. Run it after adding any new
principal scenario:

```bash
python3 contest-refactor/scripts/_principal_baseline_selftest.py
```

#### Measuring baseline recall (3-arm model run)

There is **no committed auto-grader** for the domain-grain layer — grading is semantic,
exactly as for the component-grain pairs above. To measure baseline recall for
`principal-*` entries:

1. For each of the six scenarios, spawn three subagents (same turn): **no-skill** (bare
   model), **pre-edit** (a prior skill revision), **current** (this dir). Give each the
   eval `prompt` + `scenarios/<id>/scenario.md`; save `review-verdict.md`.
2. Grade each output against the eval's `assertions[]` + the verdict JSON using a
   `grader.md` subagent.
3. Update `expected_baseline` fields in `principal_baseline.json` to reflect observed
   behavior (`miss` = base model misses the flag or over-flags the restraint; `hold` =
   base model already handles it). Update `status` to `measured`.
4. Compute lift as `pass_rate(current) − max(pass_rate(baselines))` per assertion.

`restraint_regression_tolerance: 0` in the manifest means **any** restraint regression
(skill rejects a valid twin that baselines accepted) is a defect in the lens content, not
a score. Grade restraint twins on the carve-out alone, same as the component-grain layer.

#### Replication protocol (Lever 1)

A single Critic review per scenario is one stochastic draw, so the original measurement could
not distinguish a real catch from a lucky one (small-n). The **reproducibility pass** re-runs each
of the 7 valid scenarios with **K=5 independent current-arm reviews** (5 effective slots; an
unusable output gets one logged technical rerun, then the slot counts as a non-pass — denominator
stays 5). Grading is **two-tier**:

- **Mechanical** (the headline, operator-independent, from the verdict JSON only): a flag is
  *caught* iff `(verdict==rejected OR blocks_95==true) AND target dimension_scores < 9.5`; a twin
  *holds* iff `verdict==approved AND blocks_95==false` (a strict lower bound — it under-counts a
  rubric-faithful 9.0-hold-for-missing-residual).
- **Semantic** (pre-registered rubric over the raw `flagged_smells`): a flag *named the defect* iff
  it names the cross-module/forces defect; a twin *holds* iff the carve-out smell is **not** flagged
  (score-honesty ≠ restraint miss).

A scenario resolves `caught`/`held` iff ≥4/5 slots, else `inconclusive`. A flag is **headline-
excluded** iff its diff carries a present-tense/structural smell sufficient to reject it independent
of the force under test (`abstraction-seam-flag` is contaminated this way). Every rate carries an
exact binomial (Clopper–Pearson) 95% lower bound — 5/5 ⇒ ≈0.48, so even a perfect run is *consistent
with* high recall, not proof of it. The raw per-slot record (prompt sha256, judge model, every
verdict + grade + rationale) lives in `principal_baseline_replication.json`; the manifest only
summarizes it, and `_principal_baseline_selftest.py` enforces their consistency. **Honesty caveat:**
this is current-arm only — it measures within-judge robustness, **not** lift over a bare model and
**not** external validity (that needs more scenarios + a second judge).

## Running the behavioral layer (3-arm lift)

There is **no committed auto-grader** — grading is semantic (does `flagged_smells` name the
right smell? is `blocking_severity` a real anchor?). Run via the skill-creator harness, three
arms, so "does the skill add value" is a measured number, not an assertion:

1. **Pre-edit arm** — the skill *before* this behavioral layer + the GEN-2/APL-1 lens content
   existed (so you measure what those edits buy):
   ```bash
   git worktree add /tmp/cr-preedit 6aef098      # parent of the b6607fe feat commit
   ```
2. For each behavioral eval, spawn three subagents (same turn): **no-skill** (bare model),
   **pre-edit** (`/tmp/cr-preedit/contest-refactor`), **current** (this dir). Each is given the
   eval `prompt` + its `scenarios/<id>/scenario.md` and saves `review-verdict.md`.
3. Grade each output with a `grader.md` subagent against the eval's `assertions[]` + the verdict
   JSON. Build a **per-assertion lift table**: `lift = pass_rate(current) − max(pass_rate(baselines))`.
4. Tear down: `git worktree remove /tmp/cr-preedit`.

### Reading the lift table honestly

Each assertion is tagged:

- **`[discriminating]`** — expected to pass with the skill and fail (or degrade) without it.
  This is where value shows. If a `[discriminating]` assertion has ~0 lift across all arms, it
  is **non-discriminating in practice** — the base model already knew it; fix the scenario or
  relabel the assertion. Do not count it as skill value.
- **`[restraint]`** — the skill must **not** over-flag a legitimate twin. Track these two-sided:
  the skill must improve flag-detection **without regressing restraint**. A restraint regression
  (skill rejects a valid twin the baseline accepted) is a real defect in the lens content, not a
  win. **Score-honesty is not over-flagging.** Each restraint twin's Actor proposes `→ 9.5`
  without naming a residual — kept symmetric with its flag twin so the carve-out is the only
  variable between the pair. The 9.5+ Threshold rule (`architecture-rubric.md`) correctly holds a
  no-residual 9.5 at 9.0, so mid-loop a rubric-faithful reviewer may land `conditional` /
  `blocks_95: true` on the *score* while fully clearing the carve-out. Grade `[restraint]` on the
  carve-out alone: does the review name the twin's smell, reject *for* the carve-out, or demand
  the legitimate code change? A sub-9.5 score justified solely by the missing residual is
  score-honesty, not a restraint miss — do not count it against the skill.
- **`[validity]`** — passes across all arms by design (scenario realism). **Not** skill value;
  excluded from the lift headline.

Acceptance for the suite: measurable with-skill lift on at least the `suppression-flag` and
`crossplat-flag` discriminating assertions, **and zero restraint regression**.

### The paired-arm measurement (opened 2026-08-18)

That acceptance criterion has never been evaluated, and the claim two sections above — that the
`principal-*` layer "is where recall lift lives" — rests on a **current-arm-only** measurement
(`principal_baseline.json → replication_summary.confound_noted`: *"not lift over a bare model"*).
The advisory layer meanwhile measured recall lift at **0** across three rounds and two base
models. So the question every measurement-dependent backlog item is blocked on — *does this skill
lift recall anywhere?* — is open at both grains, in opposite directions.

`evals/paired_arm_replication.json` is a **preregistered** paired with-skill/without-skill run
over 11 scenarios (5 principal flags, 2 usable principal twins, both core flag/restraint pairs)
× K=5 reps × 2 arms = 55 pairs / 110 slots. Both arms run **fresh on the same model**: the
2026-06-24 record names `claude-opus-4-8`, and reusing it would confound model with arm.

What is frozen before any output exists (and re-verified on every validator run):

- both arms' materials and task templates, by sha256, plus the **dispatch envelope** — the
  delivered prompt is template + envelope, and freezing only the template would leave the text a
  slot actually receives underspecified;
- the four grading rules, copied verbatim from `principal_baseline_replication.json` so they are
  frozen by provenance;
- the **grading protocol**: grader model, grader prompt + hash, three mechanically-decidable
  ambiguity triggers, second-grader → third-adjudicator rule, and the label-masking protocol with
  its stated limitation (it is masking, not blinding — style still leaks the arm);
- four independent decision rules and a per-scenario `expected_baseline` **hypothesis**, with the
  two core flags deliberately predicted `hold` against the principal flags' `miss`;
- the dispatch order: 55 pair ids with within-pair arm order, from a recorded seed, so resume
  walks the same experiment rather than re-randomizing into a different one.

Read the result as a **descriptive diagnostic, never a lift claim**. `noise_floor.json` ships
empty so `evaluate_lift()` returns `unreportable`, and `required_n_for_power(0.10, 0.05, 0.80)` is
778 discordant pairs against 11 cases. The binding readout rule: an observed zero or negative
delta is *"no lift detected at this n"* — never *"lift is zero"*.

Two things this run **narrows or contradicts** in the text above, declared rather than applied
silently (`prereg.declared_divergences`):

- **The acceptance criterion is invalid as literally written**, to the extent it rests on
  vocabulary. `evals.json` carries assertions that are both `[discriminating]` and
  `criterion_class: "skill_contract"` (canon severity anchors). Admitting those scores the bare
  arm on vocabulary it structurally cannot produce. Decision 2 evaluates the **`outcome`-classed
  half only**; the `skill_contract` half is reported separately on the vocabulary axis, alongside
  `grade_structural.py`'s `flagged_smells_canon_exact`.
- **`semantic ≤ mechanical` is arm-conditional.** It holds for a rubric-following reviewer, but a
  bare model can name a defect in prose while emitting `verdict: approved`, so the validator
  applies the subset invariant to `with_skill` only.

Operational state is deliberately in a **separate** file. `paired-arm-outputs/execution.json`
(measured concurrency, per-pair cost, the session cap, the dispatch log) is append-only from Phase
2 onward; the prereg freezes at Phase 1 and cannot absorb values measured afterwards. A pair is
complete **iff a committed terminal attempt record says so** — `paired_arm_run.py` reconciles from
committed records, not from files on disk, so uncommitted work simply does not exist on resume.
`RESUME.md` is a convenience for a human; `git log` is the authority.

Per D3, neither historical principal record is edited: both stay byte-identical, and the
supersession relationship lives here and in the new file.

#### Result so far — rungs 1–2, Decision 1 RESOLVED

The run executes **frontier-first**: `prereg.execution_ladder` splits the 55 pairs into four rungs,
each a *subsequence* of the frozen order (never a re-sort), each reporting before the next is
authorised. Rungs 1–2 covered the four headline-eligible principal flags — 20 pairs / 40 slots.

**Both arms caught the defect 5/5 on all four, mechanically and semantically, with the two tiers
agreeing on every one of the 40 outputs.** That is Decision 1's "both arms ≥4/5" row: **do not grow
the principal corpus for recall**, and Phase 6's twin rework — conditional on a gap being located —
does not proceed. Per the binding language rule this is *no lift detected at this n*, not *lift is
zero*: K=5 with no measured noise floor cannot separate a true null from an underpowered one, and
the estimand is the review lens as deployed, not the skill end-to-end.

Recorded with it, and **not** used to rescue the null: in every one of those scenarios the planted
defect is documented by a comment in the diff itself, and both arms cite that comment. The cases
remain sound as regression fixtures — their built purpose — and are weak as recall discriminators.
That is an observation about the corpus, filed in `execution.json`; it changes no routed action.

#### Result — rungs 3–4, the run complete

Rung 3 added the core layer and the four restraint twins (30 pairs / 60 slots); rung 4 closed the
corpus with the one contaminated flag (5 pairs / 10 slots). All 55 pairs / 110 slots are dispatched,
graded, and committed; `record_state` is `complete`.

**Restraint lift is corroborated — the study's one positive differential.** On the semantic tier,
which is the operative measure for every twin:

| twin | `with_skill` held | `without_skill` held |
|---|---|---|
| `principal-invariant-owner-restraint` | **5/5** | **1/5** |
| `principal-consistency-boundary-restraint` | 5/5 | 5/5 |
| `suppression-restraint` | 3/5 | 0/5 |
| `crossplat-restraint` | 3/5 | 1/5 |

The bare arm over-flags a legitimate carve-out in four of five reps on the invariant-owner twin
while the skill arm holds all five, and **no twin shows `with_skill` below `without_skill`** — so
Decision 4 records restraint lift with zero restraint regression, matching the advisory layer rather
than contradicting it.

**A negative flag result, reported rather than absorbed.** On `crossplat-flag` the **bare arm caught
5/5 and the skill arm 4/5**. The frozen rule routes any `without > with` on a flag, at any margin, to
*"the skill may be hurting"* — never into a saturation row. One slot at K=5 against no measured noise
floor is a signal to investigate, not demonstrated harm; the same underpowering that forbids reading
a zero delta as "no lift" forbids reading this as proof of damage.

*What that negative consists of*, diagnosed from committed data and **not** a re-grade — the grade
stands and the finding is unchanged. Nine of the ten `crossplat-flag` slots pass the assertion that
names `#if os(iOS)` as the correct guard; the sole failure is `pair-028` with_skill, which named the
defect mechanism in full (`canImport(UIKit)` is true on tvOS, so the guarded body compiles there),
demanded exactly the right evidence (a tvOS/macOS build, explicitly not more iOS testing), and held
`framework_idioms` at 8.0 — then declined to assert the guard was wrong without a compile log. So the
miss is a refusal to prescribe an unverified fix, not a failure to see the defect; mechanically the
same slot grades `caught`. The second grader, blind to the arm, flagged the framing itself: the
response "does not fit `missed`, whose operative test is a hold … `without naming the mechanism`,
which is not true here". One lever plausibly explains both directions — the lens raises epistemic
restraint, which is right on twins and cost it a fix-prescription here. That is a **hypothesis
consistent with the data at n=1**, not a measured claim, and it licenses no softening: Decision 4's
flag row is unchanged and Decision 3 stays blocked. A mechanism that explains a result is not a
reason to stop counting it.

**Decision 2 is not met, and unsettled — which is not a skill failure.** The criterion needs
`without_skill ≤2/5`; the bare arm passed ≥4/5 on all seven eligible `[discriminating]` ∧ `outcome`
assertions. It is at ceiling, so the gap the criterion looks for cannot appear there.

**Decision 3 is BLOCKED.** Conditions 1 (Decision 1's no-gap) and 2 (core no-gap) both hold;
condition 3 fails on the flag negative, and Decision 4 is a veto. Programme retargeting is therefore
**not licensed** — and the tension is worth stating rather than smoothing: the thing retargeting
would aim at is corroborated here, yet a one-slot flag negative blocks it. That rule was written
before these numbers existed, which is why it is applied rather than argued with.

**Rung 4 enters no decision.** `principal-abstraction-seam-flag` saturates at 5/5 on both arms and
both tiers, which measures the floor rather than the lens: its bare `PushProvider` protocol trips the
Unified Seam Policy on present-tense structure alone, so the rubric can reject the diff without ever
engaging the force under test. The prereg pre-classified it contaminated before any output existed,
and a 5/5 tie there is **not** evidence of no gap.

Two grading findings. Graders agree far more readily on individual assertions than on the tier those
assertions roll up to — **1/58 assertions vs 1/14 tiers** on the preregistered subsample — so the
tier rule, not assertion judgment, is where restraint grading is fragile. And seven-plus graders
across four scenarios and two independent spec-authoring runs each invented the same unschema'd
`outside_spec` field for reviewers rejecting on grounds their spec never enumerated: a real spec gap,
recorded and left for the next preregistration to close, since adding a trigger mid-run is the
post-hoc change the frozen trigger list exists to prevent.

**Read the caught/held tables, not `compute_lift()`.** The end-to-end verification runs clean — 55
`PairedTrial`s in, 55 signed `LiftResult`s out, zero `None`, counts reconciling exactly, and
`evaluate_lift()` correctly `unreportable` with no floor on file — but it also surfaced a misreading
hazard worth naming. `attempts[].assertion_results` stores the **structural** report's deterministic
checks (`required_fields_present`, `boolean_coherence`, …), not the eval's semantic assertions; only
80 of 700 are `outcome`-classed, they exist on 4 of 11 scenarios, and both arms pass them. So
`compute_lift()` returns a delta of exactly `0.000` on all 55 pairs. That zero is an artifact of
which assertions the record stores — the semantic tier that carries every finding here lives in
`semantic_grade` and the committed grader replies and never reaches `compute_lift()`. Reporting
"mean delta +0.0000" as the study's outcome would contradict the restraint lift measured above.
The record is not being retrofitted; the fix belongs to the next preregistration.

One correction on the record: `paired_arm_record_grades.py` originally had no concept of the
`-g2`/`-g3` adjudication chain and recorded first-pass grades over final ones. The audit re-derived
all 110 slots and found two mis-handled rung-3 slots, both host errors — one third grader dispatched
where the frozen rule (an `uncertain` is an abstention, not a disagreement) never called for one, and
one real disagreement that was owed an adjudicator and never got one. Fixed in the script, corrected
in `execution.json`, and no decision moves.

## Layer 3 — reviewer-judgment (`reviewer-cases/`, `reviewer_baseline.json`)

Layers 1–2 grade the **Critic** (Step 1). They never exercise the **implementation
reviewer** (Step 3, `references/implementation-reviewer.md`) — the read-only fresh-eyes pass
that approves/rejects a refactor diff before commit. Layer 3 fills that gap so a change to the
reviewer's model tier can be shown not to regress verification efficacy.

The grain is the reviewer's actual input: `{targeted finding, diff} → verdict JSON`
(`approved | rejected | conditional`). Each `reviewer-cases/<id>/` holds `case.toml`,
`finding.md` (spliced into a synthetic `CURRENT_REVIEW.md` Findings section), and `base/` +
`head/` source trees.

**base/head/deleted_paths convention.** `base/` is the pre-diff (`HEAD`) tree; `head/`
contains the files the diff **modifies or adds**. A file in `base/` but absent from `head/`
is **unchanged** (retained) — *unless* it is listed in `case.toml` `deleted_paths`, which is
how a deletion (e.g. a removed pass-through wrapper) is expressed. The runner materializes a
throwaway git repo: copy `base/` → `git commit`; overlay every `head/` file; `git rm` each
`deleted_paths` entry; `git add -A` (so additions and deletions appear in `git diff HEAD`) and
leave the result **uncommitted**. The **verbatim** reviewer prompt — which runs `git diff
HEAD` — then sees exactly the base→head diff, byte-identically to a real loop.
`prereg.reviewer_prompt_sha256` pins that template; if the prompt is edited, the baseline must
be re-measured.

### 20 cases, 10 categories, 4 look-alike axes

Same flag/restraint discipline as Layer 2, at the reviewer grain. Each **reject** category is
paired (`pair_id`) with an **approve (restraint)** look-alike that a paranoid reviewer would
wrongly reject — so a "reject-everything" reviewer passes the reject cases but fails its twins:

| axis (`pair_id`) | reject case (must reject) | restraint twin (must approve) | reviewer check |
|---|---|---|---|
| `reality` | `reality-persists` (smell still in source) | `honest-deepening` (smell genuinely gone) | Reality |
| `seam` | `fake-clean-seam` (costume / repository theater) | `justified-single-adapter` (policy/failure/platform carve-out) | Honesty |
| `suppression` | `suppression-as-fix` (bare unsafe suppression) | `compensated-suppression` (lock+TSAN, or style-only suppression) | Honesty |
| `invariant` | `missing-invariant-evidence` (risk boundary, no proof) | `risk-evidence-present` (compile matrix / TSAN recorded) | Regression |

Plus two standalone **positive controls** (`pass-through-deletion`, approve — deletion test
passes) and two standalone **conditional** cases (`small-fixable` — Reality passes but a small
<10-line residual remains). Two cases per category for construction diversity.

### Asymmetric thresholds (the core)

The two error directions are not equally dangerous, so the gate is asymmetric:

- **`false_approve_tolerance: 0`** — approving a must-reject diff carries a fake-clean refactor
  into the audit trail. The cheaper arm (B) must `reject ≥4/5` **and** name the defect `≥4/5`
  on **every** reject/conditional case, with no regression vs the current arm (A).
- **`false_reject_regression_tolerance: 1`** — rejecting a must-approve diff only costs a
  carried-forward loop. Arm B must `approve ≥4/5` per approve case; may drop to `≥3/5` on at
  most one approve category; total new approve→reject flips vs arm A `≤1`. A sub-9.5 *score*
  that still approves the carve-out is honest conservatism, **not** a false reject.

### Measuring + the no-silent-exclusion contract

`scripts/_reviewer_baseline_selftest.py` enforces mechanically (no model): every
`reviewer-cases/<id>/` dir is registered; every paired reject case has its approve twin via
`pair_id`; every manifest entry points to a dir with all four members; enums are valid and
`expected_verdict ∈ canon/verdicts.toml`; and — once a case is `status: measured` — both arms
carry 5 reps, `semantic ≤ mechanical`, and **no `false_approve` case measured arm_b as
`approve`**. Run it after adding any reviewer case:

```bash
python3 contest-refactor/scripts/_reviewer_baseline_selftest.py
```

Measurement is **manual / host-dispatched** (same posture as Layer 2 — no committed
auto-grader). For each case × arm × rep (K=5): materialize the temp repo, spawn the reviewer
with the verbatim template at the arm's model (A = `claude-sonnet-4-6`, B = `claude-haiku-4-5`),
capture the final-message verdict JSON, grade mechanical (verdict match) + semantic (reason
names the right defect / does not flag the carve-out). Raw reps land in
`reviewer_baseline_replication.json`; `reviewer_baseline.json` summarizes per case/arm and
flips `status` to `measured`. **The claude_code reviewer default flip (sonnet → haiku) in
`references/provider-adapters.md` is gated on arm B holding every threshold above.**

**Measured outcome (2026-06-27 — flip NOT landed).** A K-run (raw reps in
`reviewer_baseline_replication.json`, summary in `reviewer_baseline.json` `measurement`) found:
GATE A (false-approve) **clean** — haiku never approved a must-reject/conditional case, so the
cheaper reviewer does not pass fake-clean / regression diffs; GATE B (false-reject) **failed** —
haiku over-rejects `justified-single-adapter-1` (~2/3 approve), `risk-evidence-present-1` (~2/3),
and `risk-evidence-present-2` (~1/2) across two restraint axes where sonnet approves unanimously,
breaching `false_reject_regression_tolerance`. Conclusion: haiku is **safe but over-conservative**
on single-adapter-seam-justification and risk-boundary-evidence judgments — it would make the loop
carry-forward legitimate refactors ~1/3 of the time on those axes. The reviewer default stays
`claude-sonnet-4-6`; `claude-haiku-4-5` remains opt-in via `--reviewer-model`. This is the harness
working as intended: it caught a real efficacy regression before it shipped.

Full write-up — method, results, lessons learned, and how to re-run:
[reviewer-model-experiment.md](reviewer-model-experiment.md).

## Judge-finding routing (Layers 2–3 semantic grading)

Layers 2 and 3 grade semantically — a `grader.md` subagent (or the reviewer-judgment harness)
reads the model's output against `assertions[]` / `expected_verdict` and writes a verdict with
reasoning. That reasoning is itself sometimes wrong, in a specific and self-concealing way: it
concedes the response is correct in substance ("correctly identifies X…") but fails it on
wording or placement ("…but does not name it"). That is a **judge finding**, not an agent
finding — external measurement (a kappa-0.00 grading incident on a separate corpus) is what
surfaced the pattern.

- **Trigger.** A grader verdict whose own reasoning concedes the response is substance-correct
  but marks it failed for wording, placement, or naming — not a case where the response
  actually missed the defect or over-flagged a restraint twin.
- **Action.** Record it in [`judge-alignment-log.md`](judge-alignment-log.md). Do **not** edit
  the failing criterion, the grader prompt, or skill prose in response to a single instance.
  That is how a suite quietly stops measuring: each such edit teaches the grader (or the skill)
  to match one grader's wording instead of fixing the grader's judgment. Alignment gets
  measured and fixed as its own pass (backlog item 10), not patched criterion-by-criterion as
  findings turn up.
- **Exception — canon smell names are not cosmetic.** `flagged_smells` values are consumed by
  gates and dedup (`canon/*.toml`), so a verdict that fails a response for not naming the exact
  canon smell (vs. describing it in prose) is a legitimate fail, not a judge finding — the name
  *is* the artifact here, not decoration on top of it. Route only genuine wording/placement
  disputes; don't route around a real vocabulary-precision requirement.

## Mechanized structural pre-grading (`grade_structural.py`)

Backlog item 16: aligning a judge on a question that's mechanically checkable is wasted
work, so every structural claim gets mechanized *before* any judge-alignment pass (item 10)
touches Layers 2–3. Every assertion in `evals.json` (Layer 2) and every case field in
`reviewer_baseline.json` (Layer 3) carries a `method` tag:

- **`deterministic`** — checkable from the candidate's verdict JSON alone: the verdict word
  (closed set, `canon/verdicts.toml`), `blocks_95`/`blocking_severity` coherence,
  `dimension_scores` shape and thresholds, `flagged_smells` membership against a literal
  phrase named in the assertion text. Layer 2 assertions carry a sibling `check` field (a
  small op vocabulary — `eq`/`in`/`any_lt`/`contains_any`/`excludes_all`/`nonempty` — AND-
  combined when a list) that `grade_structural.py` evaluates directly; Layer 3's one
  deterministic fact per case (`verdict == expected_verdict`) needs no such field. Restraint
  assertions of the shape `verdict is not "rejected" (a score-honesty pushback … is not a
  carve-out flag)` are deliberately tagged `semantic`, not `deterministic`, even though they
  name the verdict field — grading them as a bare `verdict != rejected` check would false-fail
  the legitimate score-honesty hold this file's own "Reading the lift table honestly" section
  describes.
- **`semantic`** — everything else: does the response correctly identify *why* something is a
  defect, does `evidence_demanded` describe the right kind of proof, does a restraint case's
  reasoning actually rest on the carve-out. Genuine reading comprehension, unmechanizable.

`scripts/grade_structural.py <candidate-output-file> <scenario-or-case-id>` mechanically
evaluates every `deterministic`-tagged item for one candidate and prints a JSON report: general
Layer-A checks (verdict-word membership; `flagged_smells` canon-exactness, parsed read-only
from `references/architecture-rubric.md` § Vocabulary — Smells since no `canon/*.toml` covers
smell names; required-field presence; `dimension_scores` shape; boolean coherence) plus
per-case Layer-B assertion checks, then a `residue` list — the `semantic`-tagged assertions it
deliberately did not judge (Gap 9 discipline: state the axis this grader does not cover, in its
own docstring and output, not just here). Exit 0 = every deterministic check passed, 1 = at
least one failed, 2 = plumbing. `scripts/_grade_structural_selftest.py` execs the shipped
script (not a reimplementation) against synthetic candidates, RED-first, for each deterministic
failure class plus a residue-exactness check; run it after tagging any new assertion.

Counts at introduction: Layer 2 — 165 assertions across evals #12–#48, 42 tagged
`deterministic`, 123 `semantic`. Layer 3 — 20 cases × 2 fields (`expected_verdict`
deterministic, `expected_reason_class` semantic) = 20 deterministic, 20 semantic.

**Non-claim.** A clean `grade_structural.py` exit 0 measures nothing about semantic-judgment
quality — it only confirms the candidate's verdict JSON is well-formed and internally
consistent. It shrinks the judge's surface to the `residue` (item 10's still-open alignment
work); it does not substitute for that work, and a candidate that free-hands a structurally
perfect JSON with hollow reasoning still needs the semantic grader to catch it.

## Layer 4 — loop-replay regression (`loop-fixtures/`, `loop_replay_baseline.json`)

Layers 1–3 each test a *slice*: artifact rules (no loop), refactoring judgment (no real loop —
the scenario hands the model a pre-written diff), reviewer judgment (a diff, not a loop). None
runs an **end-to-end loop against a codebase**. Layer 4 fills that: materialize a seeded bad
repo, run **one** real loop, and grade whether the loop *found and fixed the planted debt* — the
regression that schema↔behavior drift would break and the other layers can't see. This is the
genuinely-open half of the SKILL-TDD-FIXTURES gap (the judgment baseline already existed in
Layers 2/3); see `analysis/contest-refactor/GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md` (W2).

### Fixture shape — `loop-fixtures/<id>/`

- `codebase/` — the seeded bad source tree (the loop *creates* the diff, so there is no
  base/+head/ split as in Layer 3).
- `expected.toml` — source of truth for the fixture: `primary_file`, `smell`, `targeted_dimension`
  (canon scorecard dim), `min_severity` (canon anchor), `expected_targeted_finding_status`, `lens`.

`loop_replay_baseline.json` registers each fixture and, once run, carries `baseline_observed`.

### Committed orchestration (the loop itself is host-dispatched)

- `scripts/loop_replay_materialize.py <id> [dest]` — copies `codebase/` into a fresh committed
  git repo and prints the dispatch + grade commands. The host then seeds Step-0 Discovery and runs
  one loop with the **verbatim `references/trust-model.md` loop-subagent template** (same manual /
  host-dispatched posture as Layers 2/3 — no committed auto-grader runs a model).
- `scripts/loop_replay_grade.py <id> <artifact-dir>` — the committed grader, the part that makes
  this measure Critic *behavior* not artifact mechanics. Required invariants:
  - **structural:** `validate-artifact.py --mode strict` exits 0; `findings[]` non-empty;
    `loop_result.targeted_finding_status` is a valid enum.
  - **semantic:** a finding's `evidence[]` cites `primary_file` (debt found); that finding's
    `severity >= min_severity`; `loop_result.what_changed` references `primary_file` (the fix
    touched the planted file); `loop_result.targeted_finding_status == expected` (debt fixed).
  - **advisory** (never gates): `scorecard[targeted_dimension]` movement vs the recorded baseline.
- `scripts/_loop_replay_selftest.py` — mechanical guard (no model): every `loop-fixtures/<id>/`
  dir is registered (no silent exclusion), required members present, `expected.toml` enums are
  canon-valid, a `measured` fixture carries a non-null `baseline_observed`, and the efficiency
  fixtures' `baseline_observed.arms.{red,green}` records carry the preregistered fields with
  their declared types (check (e)).

### Measured outcome (2026-06-28 — built RED→GREEN)

The selftest was written first and watched fail (no fixture/manifest = RED), then the fixture +
manifest + grader brought it to GREEN. The one fixture (`duplicated-subtotal-1`, a triplicated
subtotal/tax computation) was replayed end-to-end: the loop caught it at Priority 1 (F-001,
*Serious deduction*, evidence on `OrderCalculator.swift`), refactored to single owners,
reviewer-approved, committed a strict-valid artifact — `loop_replay_grade.py` exits 0 on all
required invariants. **Harness-surfaced schema fact:** `priority_1_finding_id` and
`loop_result.targeted_finding_id` are both **null once the priority-1 finding is RESOLVED in the
same loop**, so a grader must identify the planted finding by *evidence-cites-primary_file*, not by
that id — exactly the kind of schema↔behavior reality this layer exists to pin down.

```bash
python3 contest-refactor/scripts/_loop_replay_selftest.py            # mechanical guard
python3 contest-refactor/scripts/loop_replay_materialize.py duplicated-subtotal-1 /tmp/lr
#   ... host runs one loop against /tmp/lr per trust-model.md ...
python3 contest-refactor/scripts/loop_replay_grade.py duplicated-subtotal-1 /tmp/lr
```

Scope: five fixture directories on the common Critic→Architect→Execution path (not HALT/retirement
tails) — the `duplicated-subtotal-1` smoke fixture plus four efficiency-detection fixtures
(`recomputed-derived-1`, `sequential-io-1`, `startup-blocking-1`, `closure-retention-1`) for the
lens-efficiency.md always-included promotion. Extend with the HALT/retirement tail as needed.

#### Efficiency-detection RED→GREEN (2026-07-13, blind dispatch)

Measured scope is `1 + N` fixtures: the smoke fixture plus the efficiency fixtures whose arms are
recorded. **`recomputed-derived-1` (D1) is measured** — a clean, grader-consistent RED→GREEN pair
on one byte-identical fixture: the **pre-promotion** skill (efficiency opt-in, read from a worktree
at the last opt-in commit) emitted **zero** findings and rated the fixture `simplicity`=10 —
`loop_replay_grade.py` FAILs = detection **miss**; the **promoted** skill (efficiency always-on)
flagged the D1 recomputed-derived-value pattern at *Noticeable weakness* on `simplicity`, fixed it,
and **grader PASSes** = detection **catch** — with the fixture's near-miss control (`UnitFormatter`,
a stored O(1) read) correctly left untouched (restraint held). Full write-up, per-arm commits, and
the fixture-hardening history: [`loop-fixtures/MEASUREMENT-2026-07-13.md`](loop-fixtures/MEASUREMENT-2026-07-13.md).
`sequential-io-1` / `startup-blocking-1` / `closure-retention-1` (D2/D3/D4) are built, hardened, and
`swift test`-green but remain `baseline_unmeasured` — their quads are deferred (loop cost + an
account spend limit hit mid-session); the exact procedure to complete them is in the MEASUREMENT
file. Each fixture deliberately omits the `duplicated-subtotal-1` planted-debt marker comment so the
loop cannot read the answer.

## Layer 5 — execution-grain (`exec-fixtures/`, `exec_replay_baseline.json`)

Layer 4 runs a *whole* loop; it can't isolate **Step 3 (Execution)**. Layer 5 does — it is the gate
the owner requires before **Execution-unfuse** (splitting Step-3 to run at a cheaper/separate
executor, the biggest remaining per-loop token lever and CRITIC-INDEPENDENCE Gap A). It proves a
candidate executor (a) **applies** a fixed plan, (b) **narrow-reverts** a bad change, (c) **handles
Meta-Rule-4 risk boundaries** — *without* making the production structural change.

### The core move — externally construct the Step-3 entry

Step-3 cannot run alone in production (it is fused with Step 1+2; `LOOP_STATE.json` is deleted at
commit). So the harness **seeds** the entry: `exec_replay_materialize.py` makes a **source-only** base
commit, overlays the seeded Step-1+2 output (`seed/CURRENT_REVIEW.{json,md}` + `findings_registry.json`
— the "fixed plan") **uncommitted** (matching a real loop, where Steps 1-2 write but don't commit until
sub-step 11), captures the base sha, and prints a **Step-3-only dispatch**. The host runs that dispatch
at the arm's model; `exec_replay_grade.py` then grades `base..HEAD` — cleanly separating the executor's
source changes from the artifacts it commits.

**Prompt fidelity (the gate's validity).** `evals/exec_step3_executor_prompt.md` POINTS at `SKILL.md §
Step 3` (sub-steps 0–11) rather than copying them, and is **dual-sha-pinned** in the manifest `prereg`:
`step3_executor_prompt_sha256` (the template) + `skill_step3_section_sha256` (the SKILL.md Step-3 section,
regex-anchored `### Step 3`…next heading). `_exec_replay_selftest.py` recomputes both and fails closed if
either drifts — a prod Step-3 edit loudly invalidates the baseline. Recompute with `--print-shas`.

### The three kinds + deterministic grading (no model judgment in the gate)

The implementation-review subagent is Step-3 sub-step 6 (in scope), but its **stochastic `verdict` is
ADVISORY only** — every required/safety invariant is a git/diff/regex/token check:

- **apply** — `resolved`; a `change[]` source file committed; `changed ⊆ change[]`; `avoid[]` byte-untouched;
  the planted pattern's occurrence count strictly **decreases** (`resolved_absent_regex`); working tree clean.
- **revert** (safety, tol 0) — a build-breaking correction (a caller in `avoid[]` depends on the renamed
  symbol, so `run_tests.sh` typecheck fails **deterministically**) → `carried_forward`; **NO source committed**;
  source **restored** in the working tree (`git diff base` clean, not just `base..HEAD`); working tree clean.
- **risk_boundary** (safety, tol 0) — **FAIL iff** a boundary-crossing diff is committed AND
  `loop_result.risk_boundary_evidence` is absent/null OR its `verification` is not a real preservation kind
  (`compile_matrix`/`focused_test`/`thread_sanitizer`/`sendable_conformance`; `reasoning_only` counts only
  with `mechanically_testable=false`); PASS otherwise. **Structured + enum-typed** (G33 +
  `evaluate_risk_boundary_evidence`), NOT token-matched — there is deliberately no enum value for "I compiled
  one config", so an executor that merely names the boundary + runs a single-config typecheck cannot pass.

**Arms + asymmetric thresholds** (mirror `reviewer_baseline`): `arm_a` = current executor tier
(`claude-sonnet-4-6`), `arm_b` = candidate cheaper executor. `safety_tolerance: 0` — once `arm_b` is
measured, it must never leave a broken/unevidenced change committed on a revert/risk_boundary fixture
(`_exec_replay_selftest.py` fails on a truthy `arm_b.safety_violation`). `apply_correctness` tolerates the
occasional under-apply.

### Measured outcome (2026-06-28 — arm-A baseline, n=1, RED→GREEN)

Selftest written first (RED). All three fixtures replayed at **arm A** and graded **exit 0**: apply
(triplicated subtotal → single owners; pattern 4→0; `avoid[]` untouched), revert (rename → caller fails to
typecheck → narrow-revert → `carried_forward`, only artifacts committed, working tree restored), risk
(dropped `@MainActor`, recorded compile-time + TSAN-unavailable Meta-Rule-4 evidence; committed-with-evidence
→ `safety_violation=false`). **Environment limitation:** the nested reviewer (sub-step 6) couldn't always be
joined; executors joined by reading the reviewer's run-record transcript, and in one case reviewed inline
after a relayed verdict corroborated — fine, because the verdict is advisory to the gate.

### arm_b candidate (2026-06-28 — claude-haiku-4-5, n=1) → REJECTED; gate hardened

Measured the cheaper candidate `claude-haiku-4-5` on all three fixtures. **revert: SAFE** (ran the test,
caught the build break, narrow-reverted with an accurate reason, clean tree). **apply: correct refactor but
non-clean** (left scratch files; G22/G27). **risk: UNSAFE** — committed the `@MainActor` removal on a
non-Sendable mutable class, deleted the Meta-Rule-4 warning, and recorded only a non-probative single-config
`swiftc` typecheck as "evidence". The **prior token gate FALSE-PASSED** this (the words "swiftc"/"isolation"
matched). That false pass motivated the structured `loop_result.risk_boundary_evidence` field (G33 +
`evaluate_risk_boundary_evidence`): under it the deterministic gate flags `safety_violation=true`. haiku is
**REJECTED** (see `exec_replay_baseline.json` → `rejected_candidates`); **Execution-unfuse stays BLOCKED**;
`arm_b_model` is null (no current candidate). Caveat: n=1 smoke; the risk failure is a judgment defect, not
variance.

```bash
python3 contest-refactor/scripts/_exec_replay_selftest.py                 # mechanical guard + dual-sha pins
python3 contest-refactor/scripts/exec_replay_materialize.py apply-duplicated-helper-1 /tmp/ex --arm-model claude-sonnet-4-6
#   ... host runs the printed Step-3-only dispatch against /tmp/ex ...
python3 contest-refactor/scripts/exec_replay_grade.py apply-duplicated-helper-1 /tmp/ex <base-sha>
```

**Follow-ups (deferred):** re-attempt `arm_b` only after prompt-hardening the executor's artifact discipline,
at K≥5; then the **Execution-unfuse** structural change itself (this harness is its prerequisite); HALT/
retirement tails. *(The structured `loop_result.risk_boundary_evidence` field — once listed here — shipped
2026-06-28: risk-boundary grading is now field-based, not token-based.)*

## Layer 6 — scorecard coupling (`scorecard-coupling/`, `scorecard_coupling_baseline.json`)

Layers 1–5 all measure a **judgment**: does the Critic flag this defect, does the reviewer approve this
diff, does a loop replay to the same place, does an executor produce the same edit. None measures the
**scorecard numbers** — the skill's headline output, the thing `HALT_SUCCESS` is defined against, and the
thing every scoring gate (G5, G6, G21, G37) tests per-dimension.

Two probes, failing in opposite directions, both observed in production:

- **Repeatability** — same source, independent Critic passes. Two runs whose scorecards described the same
  source against byte-identical Score Anchors disagreed by a mean of **1.33** per dimension and a max of
  **3.0**; `test_strategy`, the `HALT_SUCCESS` bar, was certified **9.5** by one Critic and **6.5** by the
  next. The *averages* agreed to 0.22 — a good aggregate signal and a poor per-dimension one, which is the
  opposite of how the gates use it.
- **Sensitivity** — source genuinely improved, do the scores move? Across eleven loops that resolved
  **seven Serious structural findings**, the scorecard produced **zero UP deltas** on any of nine dimensions.

Supporting mechanism (evidence, not a probe): across 40 loops, **189 of 360 emitted scores (52.5%)** sat at
values the rubric defines no anchor for. It anchors 10/9/7/5/3; the runs emitted 7.5, 6.5, 5.5, 6 and 8.5
constantly. The two most-used *anchored* values, 9.5 and 10, are exactly the ones carrying rule pressure.

**Deliberately measurement-only.** Writing anchor text for the intermediate values is a guess until the
variance is attributed, so a value-domain gate on off-anchor scores — and publishing the noise floor beside
the scorecard — are both gated on this layer reading out. The seeded `attempt 0` in each probe is marked
`controlled: false`: it is harvested from real runs so the layer starts from evidence, not a designed
replication. Controlled attempts must pin `skill_rev` (G19), run with no prior artifacts on disk, and record
every attempt including invalid ones — the Layer-3 no-silent-exclusion contract applies unchanged, because
an attempt dropped without a reason turns a variance measurement into a selection effect.

### Attempt 1 — repeatability, controlled, N=3 (2026-08-06)

Three blind Critic passes, `source_rev 1bdec1a`, `skill_rev 23bea47`, byte-identical prompts.

**Measured noise floor: max per-dimension gap 2.0 (`credibility`), mean 1.22, five of nine dimensions
over 1.0.** Prediction (≤ 1.0) refuted; the pre-registered confirm-the-defect bar (≥ 2.0) met.

Attempt 0's *headline* did not survive, and it was the load-bearing half. Where attempt 0 showed
compensating swings around a stable mean (0.22), attempt 1 shows the opposite: one pass scored strictly
lower than both others on **9 of 9** dimensions while the other two were **identical on 7 of 9**, so the
averages spread **1.22**. Per-dimension *attribution* reproduces; overall *severity calibration* is what
drifts, and it moves every dimension together. Those need different fixes — the reason this was measured
rather than reasoned about. At N=3 with one deviant rater, that shape describes the sample, not the
population.

Two results worth carrying forward:

- **The findings repeated even though the numbers did not.** All three passes independently named the same
  defects (the 1987-line UI class, an `"Unknown"` string sentinel threaded across modules, unlocked reads
  outside their own gates, cancellation plumbed and never supplied). Structured source-anchored claims
  reproduce; free-form scalar judgment does not — this skill's thesis, measured directly.
- **The anchored grid is not the scale in use.** 81.5% of attempt 1's scores were off-anchor and `7` was the
  only anchored value any pass emitted; 9, 10, 5 and 3 never appeared. The plan's framing — does variance
  concentrate on off-anchor values *versus* anchored ones — has no anchored comparison group to test against.

Recorded as a lead, not a result: on this same SHA the production Critic (holding its own history and
registry) scored **1.69 higher** than the blind mean and exceeded *every* blind pass on 8 of 9 dimensions.
Consistent with a ratchet — G8 blocks unproven increases but nothing re-baselines downward — and confounded
at least three ways, so it needs its own design. **Attempt 2 supplied that design; see below.**

### Attempt 2 — ratchet probe, controlled, N=3 per arm (2026-08-06)

Does a prior *score* move a Critic's judgment of unchanged source? Three arms at one SHA, primed harnesses
generated from the blind one and verified to differ from each other by the corpus path alone. G8 deliberately
inert and declared so, making this the conservative direction.

| arm | primed with | grand mean | displacement | % of available gap |
|---|---|---|---|---|
| BLIND | — | 7.593 | — | — |
| HIGH | 9.278 | 8.426 | +0.833 | 49% |
| LOW | 5.778 | 7.296 | −0.296 | 16% |

**Pre-registered verdict: REFUTED.** The bar was ≥ 1.0 in *both* arms; neither cleared it. Anchoring at the
predicted strength is not established, and attempt 1's 1.685 production-vs-blind gap is **not** reproduced by
priming alone — most of it stays with the recorded confounds.

Post hoc, and labelled as such: both arms moved toward their prime and never away (HIGH up on 9/9 dimensions,
LOW down on 7/9); per dimension the HIGH arm closed 40–55% of whatever gap was available, with `data_flow` —
whose prime equalled its blind score — as the internal control that moved +0.17; the pull was 2.81× stronger
upward than downward. **The largest effect was on spread, not level:** HIGH-arm pass means spread 0.222
against blind's 1.222, so a high prior made three independent Critics agree ~6× more tightly. If that holds
at higher N, a prior scorecard buys apparent repeatability without buying accuracy.

The registered threshold was the wrong statistic — absolute grand-mean displacement cannot separate "did not
anchor" from "had nowhere to go" when available gaps range 0.17–2.50. Fraction-of-available-gap is registered
for future attempts and deliberately **not** applied to this verdict.

One rater invented a mitigation unprompted: it scored the source first and read the prior only afterwards,
landing closest of any primed pass to the blind mean. Score-then-read is a cheap candidate fix awaiting its
own attempt.

### Attempt 3 — variance collapse at N=6 (2026-08-06)

Both arms extended to six passes; harness hashes and the regenerated prime verified identical.

| arm | mean | SD | spread |
|---|---|---|---|
| BLIND (n=6) | 7.630 | 0.460 | 1.222 |
| HIGH (n=6) | 8.389 | 0.196 | 0.556 |

**Pre-registered verdict: CONFIRMED, marginally** — F(5,5) = 5.538 vs the registered 5.050, p = 0.0418.
The registered prediction held in both directions (HIGH's SD rose from 0.116 as regression to the mean
predicts; BLIND's fell from 0.663), so the real effect is about half the N=3 estimate and still clears the
bar. **Weak evidence, and the registered robust check disagrees:** Brown-Forsythe t(10) = 1.797 vs 2.228,
not significant. HIGH is narrower on 7/9 dimensions. N=10–12 would settle it. Mean displacement restates to
**+0.759**, so attempt 2's ≥ 1.0 ratchet bar remains unmet on twice the data.

**The band unlock (post hoc) is the sharpest result in this layer.** Across 54 scores from six independent
blind Critics, **not one exceeded 8.5**; primed Critics emitted **15 scores ≥ 9.0** (Fisher p = 9.9e-06) and
reached 9.5 three times, with 5 of 6 passes crossing 9.0. A prior does not nudge scores by a constant — it
removes a ceiling. **Every gate that certifies convergence lives above the blind ceiling:** G5 triggers at
9.5, G6 at 10, G21's `HALT_SUCCESS` bar sits at 9.5 on all nine dimensions. On this corpus at this
`skill_rev`, a Critic reading no prior scorecard cannot reach `HALT_SUCCESS` at all. Limits stated plainly:
post hoc, the ≥ 9.5 comparison alone is *not* significant (3 occurrences, p = 0.121), and it is one corpus.

### Attempt 4 — corpus or rubric? Answered from the archives at zero cost (2026-08-06)

The planned follow-up was a second corpus at N=6 (~1.5M tokens). It was unnecessary: **loop 1 of an archived
run is already a blind Critic pass** whenever no prior `REVIEW_HISTORY` was on disk. Run A, B and S loop 1
qualify; **Run C's loop 1 does not** — the combined history carries loop numbers `[1..10, 1..15]`, so it ran
with Run B's ten loops already on disk.

Pooled: **81 blind scores, 9 passes, 2 corpora, 3+ skill revisions.**

- **Attempt 3's stronger reading is refuted.** The 8.5 ceiling is **corpus-specific** — a blind Critic over
  agent-skills (Python) emitted 9.0 on four of nine dimensions immediately.
- **What survives:** across all 81 blind scores, **none reached 9.5** — the threshold G5, G6 and G21 all
  certify against.
- **The natural experiment:** Run C began at Run B's HEAD, so their loop 1s describe near-identical source.
  Blind (Run B): max 8.5, zero at 9.0+. Primed (Run C): max 9.5, **three dimensions at 9.5** — in its first
  loop, before touching a line of code. That is exactly what attempt 3's N=6 test could not establish.

Caveats: observational, n=1 per run; archived passes ran the *full* protocol at different skill revisions,
which strengthens the 9.5 claim but weakens per-pass comparison; `skill_rev` is null throughout (the gap
Change 1 closed), so 29 skill commits also separate the Run B / Run C pair; Run S is a self-review and is the
sole source of every blind score ≥ 9.0.

### Attempt 5 — re-analysis with the right estimator, no new sampling (2026-08-07)

Attempts 1–3 used raw spread, SD and an F-test on grand means. The standard analysis for repeated ratings of
the same targets is a two-way variance decomposition plus the **intraclass correlation**. On the same data:

| | BLIND | PRIMED |
|---|---|---|
| dimension (signal) | 20.8% | 61.4% |
| **rater severity** | **59.3%** | 10.2% |
| rater × dimension | 20.0% | 28.4% |
| **ICC(2,1)** one rater | **0.166** | **0.575** |
| raters for 0.80 reliability | **20** | 3 |

**Nearly 60% of blind variance is which rater, not which dimension** — textbook rater severity, and the
mechanical explanation for attempt 1's "pass B strictly lower on 9/9."

**The cut-score consequence is the hardest result in this layer.** Single-rater SEM is 0.283, 95% band
± 0.56, so clearing G21's 9.5 bar by more than measurement error needs an observed **≥ 10.06 — above the
scale maximum**. A single Critic pass cannot certify 9.5, independently of every anchoring question.

**Calibration or contagion? Both.** Profile correlation against the prime rose from +0.361 (blind) to
+0.844 (primed), so raters adopted the anchor's *pattern*, not just its level — but the primed profile still
correlates +0.756 with the blind one. With severity removed, primed raters disagree slightly *more* per
dimension (0.346 vs 0.283). **Priming's entire measurable benefit is severity removal.**

This **retracted a recommendation before it shipped**: blinding the `HALT_SUCCESS` challenger would have
moved the only independent certification check from ICC 0.575 to 0.166. The licensed changes and the prior
art are in [`scorecard-coupling/README.md § What this layer licenses`](scorecard-coupling/README.md).

Full protocol: [`scorecard-coupling/README.md`](scorecard-coupling/README.md).
