"""Discriminating-power classifier for the paired skill-lift harness (backlog item 19, Gap 17:
docs/review-skill-deep-dive-2026-08-17.md:772).

Item 21 (`_trial_validity.py`) answers "did this trial produce a scoreable outcome." Item 22
(`_paired_baseline.py`) answers "given a scoreable pair, what is the signed lift." Item 20
(`_noise_floor.py`) answers "is a lift distinguishable from noise." This item answers a
question upstream of a lift *summary*, about the *cases* feeding it: **does this case
discriminate at all** -- Anthropic's own analyzer classifies every assertion by discrimination
pattern across runs: always-pass-both, always-fail-both, pass-with-fail-without (value),
**fail-with-skill-but-pass-without (the skill may be hurting)**, high-variance (flaky). A case
that lands in either "always" bucket contributes nothing to a lift claim and dilutes its
sensitivity; a case that lands in the fourth bucket is currently invisible everywhere in this
suite -- item 22's signed, unfloored `delta` and item 20's two-sided `alpha` both exist to let
that bucket be seen at all, and this item is what actually names it.

Two corrections from review, both load-bearing here, not cosmetic:

  1. **Discrimination is stochastic, never read from one observation.** A case is classified
     from repeated paired deltas *against the A/A floor* (item 20) -- never from a single
     pass/fail. `classify_case()` refuses (category `"unclassifiable"`) on fewer than
     `MIN_REPS_FOR_CLASSIFICATION` reps, and refuses again if no floor is on file for the
     current key -- inheriting item 20's own D6 posture (`evals/noise_floor.json` ships empty;
     an absent floor makes a claim unreportable, never a fabricated 0.0) rather than
     reimplementing it: `classify_case()` calls `_noise_floor.lookup_floor()` directly.
  2. **Always-pass cases that encode absolute contracts are not pruned.** A regression that
     must never fire, a schema that must always validate, stays in the corpus -- it moves to a
     separately reported contract suite, excluded from lift claims but never deleted. That
     separation is `case_kind` on `_paired_baseline.PairedTrial` (added by this item, D4): a
     `"contract"`-kind trial makes `compute_lift()` return `None` unconditionally, the single
     choke point every trial passes through to become a `LiftResult` -- see that module for the
     enforcement and this module's own docstring note below for why the gate lives there.

Two more corrections, from a second review pass, are the actual hazard this item exists to
guard against -- building this carelessly is exactly how selection bias gets introduced into a
benchmark that is supposed to measure lift honestly:

  - **D1 -- fitted only on development, retrospective on validation/holdout, never
    excludes.** The screen must never select the eval sets by their own observed treatment
    response: its rule is designed on development outcomes only, and on validation and holdout
    it only *classifies* cases after the fact, without changing what counts toward a lift
    claim -- or the benchmark becomes circular. Three mechanical consequences, each proven in
    `_discriminating_power_selftest.py`, not asserted in prose:
      * `fit_discrimination_rule()` is the ONLY function in this module that reads case
        outcomes to produce a `DiscriminationRule`. It raises `ValueError` if handed a record
        whose `split` is not `"development"` -- a rule fit on validation or holdout data would
        make the benchmark circular by construction, so this fails loudly rather than silently
        producing a rule that happens to fit those splits too.
      * `classify_case()` / `classify_corpus()` never filter, reorder, or mutate their input.
        `classify_corpus()` returns exactly one `DiscriminationVerdict` per input `SplitReps`,
        in input order -- a label is added to a case, never a reason to drop one. A case
        classified `"high_variance"` or `"always_pass_both"` is reported that way; it is not
        removed from whatever denominator a caller computes downstream, and this module ships
        no function that could remove it (there is no "discriminating cases only" filter here
        for a lift computation to accidentally consume).
      * Labeling a validation- or holdout-split case never touches the `LiftResult` objects
        underneath it -- `classify_case()` reads `SplitReps.reps` and returns a new,
        independent `DiscriminationVerdict`; nothing downstream of a lift computation
        (`_noise_floor.aggregate_cases()`, `evaluate_lift()`) reads anything this module
        produces. Any lift summary computed before or after a classification pass over the same
        `LiftResult`s is bit-for-bit identical, because the two computations share input data
        and nothing else.

  - **D5 -- discrimination is a TREATMENT property, not a GRADER property.** A case useless
    for measuring skill lift can be excellent for detecting judge error -- the judge-alignment
    suite (Layer 3, `evals/reviewer-cases/` + `reviewer_baseline.json`) must never be sampled by
    this module's output. This is enforced **structurally, by type, not by convention**: every
    function here takes `SplitReps`, which wraps `LiftResult` tuples -- item 22's
    with-skill/without-skill paired-arm output. The judge-alignment suite's grain is entirely
    different (`{targeted finding, diff} -> verdict JSON`, two REVIEWER MODELS compared against
    a reference verdict, `evals/README.md`'s Layer 3 section) and is graded through
    `scripts/_reviewer_baseline_selftest.py`'s own mechanical checks -- it never produces a
    `LiftResult` (no `with_outcome_score` / `without_outcome_score` / signed `delta` over a
    with-skill/without-skill pair exists anywhere in that grain). There is therefore no value of
    any type this module accepts that a reviewer-case record could be coerced into: constructing
    a `LiftResult` from a reviewer-case verdict fails at the dataclass constructor (missing
    required fields), before this module's logic ever runs. Nothing here is generic over "any
    evals.json case" -- narrowly typing every entry point to `SplitReps`/`LiftResult` is the
    enforcement mechanism, not a comment asking a future caller to be careful.

Scope (matches item 20's and item 21's own posture, D6 of the item-19 brief): this item ships
the classification mechanism, the split discipline, and the contract-suite separation, proven
against **constructed** records. It fits nothing and runs nothing -- `fit_discrimination_rule()`
returns `None` on empty input, never a hardcoded default, and `classify_case()` refuses to
classify without a fitted `DiscriminationRule` exactly as it refuses without a noise floor. No
number in this module is a placeholder standing in for a future measurement; the refusal path
*is* the shipped behavior until a real development corpus exists.

Cross-references: evals/README.md ("Discriminating-power classification" section),
scripts/_paired_baseline.py (LiftResult, PairedTrial.case_kind, compute_lift -- imported/relied
on, not reimplemented), scripts/_noise_floor.py (CaseAggregate, mcnemar_counts, lookup_floor,
NoiseFloorKey -- imported, not reimplemented), scripts/_discriminating_power_selftest.py.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from _noise_floor import CaseAggregate, NoiseFloorKey, lookup_floor, mcnemar_counts
from _paired_baseline import CASE_KINDS, LiftResult

# No sys.path handling here, by house convention (see _trial_validity.py / _paired_baseline.py /
# _noise_floor.py): a pure library module, imported after the caller has already put scripts/ on
# sys.path.

CASE_SPLITS = ("development", "validation", "holdout")

# The five categories from Anthropic's analyzer (Gap 17), plus two outcomes that are not one of
# the five: "contract" (routed here by case_kind, never classified into the five -- see D4 in
# the module docstring) and "unclassifiable" (a refusal: too few reps, no fitted rule, or no A/A
# floor on file -- D3/D6). Kept as a separate tuple from DISCRIMINATION_CATEGORIES so a caller
# who wants "only the five Anthropic categories" (e.g. for a summary table) has a vocabulary
# that does not also include the two refusal/routing states.
DISCRIMINATION_CATEGORIES = (
    "always_pass_both",
    "always_fail_both",
    "pass_with_fail_without",
    "fail_with_skill_but_pass_without",
    "high_variance",
)
NON_CATEGORY_STATUSES = ("contract", "unclassifiable")
ALL_CLASSIFICATION_STATUSES = DISCRIMINATION_CATEGORIES + NON_CATEGORY_STATUSES

# D3: a single pass/fail observation is refused, not guessed from -- this is a definitional
# floor on what "stochastic" can mean (you cannot observe a *pattern* across one data point),
# not a tuned statistic, so it is a plain module constant rather than something
# fit_discrimination_rule() derives (contrast DiscriminationRule.min_direction_consistency
# below, which genuinely is fit from data).
MIN_REPS_FOR_CLASSIFICATION = 2


@dataclass(frozen=True)
class SplitReps:
    """One case's repeated paired trials (item 22 `LiftResult`s), tagged with which split the
    case belongs to (D1: explicit per-record, never inferred) and which suite it belongs to
    (`case_kind`, mirroring `_paired_baseline.PairedTrial.case_kind`).

    `case_kind` here is defense-in-depth, not the primary enforcement: a `"contract"`-kind
    `PairedTrial` already cannot produce a `LiftResult` at all (`compute_lift()` returns `None`
    unconditionally for one), so in the intended flow a `SplitReps.reps` tuple for a contract
    case is simply empty -- there is nothing to wrap. The field is carried anyway so a
    hand-constructed `SplitReps` (as every one in this item's selftest is, per its own scope)
    still routes correctly through `classify_case()` without requiring a live dispatch.
    """

    case_id: str
    split: str
    reps: tuple[LiftResult, ...]
    case_kind: str = "lift_eligible"

    def __post_init__(self) -> None:
        if self.split not in CASE_SPLITS:
            raise ValueError(
                f"{self.split!r} is not a case split ({'|'.join(CASE_SPLITS)}): "
                f"case {self.case_id!r}"
            )
        if self.case_kind not in CASE_KINDS:
            raise ValueError(
                f"{self.case_kind!r} is not a case_kind ({'|'.join(CASE_KINDS)}): "
                f"case {self.case_id!r}"
            )
        for r in self.reps:
            if r.case_id != self.case_id:
                raise ValueError(
                    f"LiftResult.case_id {r.case_id!r} does not match "
                    f"SplitReps.case_id {self.case_id!r}"
                )


@dataclass(frozen=True)
class DiscriminationRule:
    """The single free parameter this item's classifier uses, fit exclusively from
    development-split outcomes (D1): `min_direction_consistency` -- the minimum fraction of a
    case's discordant reps that must agree on direction before the swing is even treated as a
    directional candidate signal, rather than mixed-direction ("high_variance") noise. Produced
    only by `fit_discrimination_rule()`; nothing else in this module may construct one.
    """

    min_direction_consistency: float
    fitted_from_n_cases: int


def fit_discrimination_rule(
    records: Iterable[SplitReps], *, pass_threshold: float = 1.0
) -> DiscriminationRule | None:
    """D1: the ONLY function permitted to produce a `DiscriminationRule`, and the only one that
    may read case outcomes to set its free parameter. Raises `ValueError` -- loudly, not
    silently -- if handed a record whose `split` is not `"development"`: a rule fit on
    validation or holdout data would let the benchmark select itself, exactly the circularity
    Gap 17's second-review correction forbids.

    Returns `None` -- never a hardcoded fallback -- when there is nothing to fit from: no
    records, or no development case whose reps ever disagreed with each other (zero discordance
    carries no information about what a noise-driven disagreement rate looks like for this
    corpus). This mirrors item 20's own D6 posture (`evals/noise_floor.json` ships empty; an
    absent floor makes a claim `unreportable`, never `floor=0`) -- and per this item's own scope
    (D6), nothing calls this function with a non-empty development corpus yet: it ships the
    refusal path, not a fitted value.
    """
    dev_records = list(records)
    for r in dev_records:
        if r.split != "development":
            raise ValueError(
                f"fit_discrimination_rule() was handed a {r.split!r}-split case "
                f"({r.case_id!r}); a discrimination rule may only be fit from "
                "'development'-split outcomes (D1) -- fitting on validation or holdout data "
                "would make the benchmark circular"
            )

    consistencies: list[float] = []
    for r in dev_records:
        if r.case_kind == "contract" or len(r.reps) < MIN_REPS_FOR_CLASSIFICATION:
            continue
        _a, b, c, _d = mcnemar_counts(_per_rep_aggregates(r.case_id, r.reps, pass_threshold))
        if b + c > 0:
            consistencies.append(max(b, c) / (b + c))

    if not consistencies:
        return None
    return DiscriminationRule(
        min_direction_consistency=statistics.median(consistencies),
        fitted_from_n_cases=len(consistencies),
    )


def _per_rep_aggregates(
    case_id: str, reps: Sequence[LiftResult], pass_threshold: float
) -> list[CaseAggregate]:
    """One `CaseAggregate` per rep (item 20's dataclass, reused rather than reimplemented) so
    `mcnemar_counts()` can be called directly on a single case's repeated trials -- a different
    use of that function than item 20's own (which counts across many *cases*' single
    aggregated rows); here every "case" `mcnemar_counts()` sees is really one rep of the SAME
    case, `n_reps=1` each, which is exactly what lets the (a, b, c, d) counts describe how that
    one case's own reps disagreed with each other."""
    return [
        CaseAggregate(
            case_id=case_id,
            with_score=r.with_outcome_score,
            without_score=r.without_outcome_score,
            with_pass=r.with_outcome_score >= pass_threshold,
            without_pass=r.without_outcome_score >= pass_threshold,
            delta=r.delta,
            n_reps=1,
        )
        for r in reps
    ]


@dataclass(frozen=True)
class DiscriminationVerdict:
    case_id: str
    split: str
    category: str  # one of ALL_CLASSIFICATION_STATUSES
    n_reps: int
    counts: tuple[int, int, int, int] | None  # (a, b, c, d); None when refused before counting
    observed_effect: float | None  # (b - c) / n_reps; None when refused/not computed
    noise_ceiling: float | None
    reasons: tuple[str, ...]


def _refuse(record: SplitReps, category: str, reason: str) -> DiscriminationVerdict:
    return DiscriminationVerdict(
        case_id=record.case_id,
        split=record.split,
        category=category,
        n_reps=len(record.reps),
        counts=None,
        observed_effect=None,
        noise_ceiling=None,
        reasons=(reason,),
    )


def classify_case(
    record: SplitReps,
    key: NoiseFloorKey,
    floors: Iterable[Mapping[str, Any]],
    rule: DiscriminationRule | None,
    *,
    pass_threshold: float = 1.0,
) -> DiscriminationVerdict:
    """Classify one case's repeated paired trials into one of `ALL_CLASSIFICATION_STATUSES`.

    Read-only end to end: takes a `SplitReps` and returns a fresh `DiscriminationVerdict`, never
    mutating `record` or anything reachable from it (D1's "retrospective, never alters
    contribution" rule -- proven in the selftest by recomputing a lift summary from the same
    `LiftResult`s before and after calling this function and asserting bit-for-bit equality).

    Refusal order, each returning `"unclassifiable"` or `"contract"` before any counting:
      1. `case_kind == "contract"` -- routed to the contract suite (D4), never classified as one
         of the five Anthropic categories; a contract case's discrimination pattern is not the
         question a contract exists to answer.
      2. Fewer than `MIN_REPS_FOR_CLASSIFICATION` reps -- discrimination is a stochastic
         property; a single observation is refused, not guessed from (D3).
      3. `rule is None` -- no `DiscriminationRule` has been fit yet (D6); an unfitted classifier
         refuses rather than falling back to a default consistency threshold.
      4. No A/A noise floor on file for `key`, or a matched record with no numeric
         `noise_ceiling` -- inherited directly from item 20's D6 via `lookup_floor()`, not
         reimplemented.

    Once past all four, every rep is scored pass/fail per arm (`pass_threshold`) and reduced to
    McNemar counts `(a, b, c, d)` via item 20's own `mcnemar_counts()`:

      - `a == n_reps` (every rep: both arms passed)  -> `"always_pass_both"`
      - `d == n_reps` (every rep: both arms failed)  -> `"always_fail_both"`
      - no discordant reps (`b == c == 0`) but `a`/`d` are both < n_reps -- the arms move
        together across reps but not to a single stable pass/fail pattern -> `"high_variance"`
        (concordant flakiness)
      - discordant reps exist (`b + c > 0`); `consistency = max(b, c) / (b + c)` measures how
        much they agree on which arm wins:
          - `consistency < rule.min_direction_consistency` -> `"high_variance"` (the reps
            disagree with each other about which arm is better -- this is what "flaky" means)
          - otherwise, `observed_effect = (b - c) / n_reps` is compared against the measured A/A
            `noise_ceiling` for this key (D3's own correction: classified *against the floor*,
            never in isolation):
              - `abs(observed_effect) > noise_ceiling` and `b >= c` -> `"pass_with_fail_without"`
              - `abs(observed_effect) > noise_ceiling` and `c > b`  ->
                `"fail_with_skill_but_pass_without"` -- the skill may be hurting; Gap 17's own
                highest-value output, otherwise undetectable anywhere in this suite
              - otherwise (consistent direction, but the swing does not clear the measured A/A
                floor) -> `"high_variance"` -- indistinguishable from the noise a byte-identical
                A/A comparison already produces
    """
    if record.case_kind == "contract":
        return _refuse(
            record,
            "contract",
            "case_kind='contract' -- an absolute-contract case, excluded from discrimination "
            "classification and from every lift claim (D4); reported in the contract suite, "
            "never pruned",
        )

    n = len(record.reps)
    if n < MIN_REPS_FOR_CLASSIFICATION:
        return _refuse(
            record,
            "unclassifiable",
            f"{n} rep(s) recorded; discrimination is a stochastic property and cannot be read "
            f"from a single observation (D3) -- need >= {MIN_REPS_FOR_CLASSIFICATION}",
        )

    if rule is None:
        return _refuse(
            record,
            "unclassifiable",
            "no DiscriminationRule fit yet -- fit_discrimination_rule() must run against "
            "development-split outcomes first (D6); an unfitted classifier refuses rather than "
            "guessing a default consistency threshold",
        )

    floor = lookup_floor(key, list(floors))
    if floor is None:
        return _refuse(
            record,
            "unclassifiable",
            f"no A/A noise floor recorded for key fingerprint {key.fingerprint()[:12]}... "
            "(inherited from item 20's D6: an unmeasured key makes classification impossible, "
            "never defaulted to noise_ceiling=0)",
        )
    noise_ceiling = floor.get("noise_ceiling")
    if not isinstance(noise_ceiling, int | float):
        return _refuse(
            record,
            "unclassifiable",
            f"floor record matched key fingerprint {key.fingerprint()[:12]}... but carries no "
            "numeric noise_ceiling -- refusing to fabricate one (item 20's D6)",
        )

    a, b, c, d = mcnemar_counts(_per_rep_aggregates(record.case_id, record.reps, pass_threshold))
    counts = (a, b, c, d)

    if a == n:
        return DiscriminationVerdict(
            case_id=record.case_id,
            split=record.split,
            category="always_pass_both",
            n_reps=n,
            counts=counts,
            observed_effect=0.0,
            noise_ceiling=float(noise_ceiling),
            reasons=(f"all {n} rep(s) show both arms passing (a={a})",),
        )
    if d == n:
        return DiscriminationVerdict(
            case_id=record.case_id,
            split=record.split,
            category="always_fail_both",
            n_reps=n,
            counts=counts,
            observed_effect=0.0,
            noise_ceiling=float(noise_ceiling),
            reasons=(f"all {n} rep(s) show both arms failing (d={d})",),
        )
    if b == 0 and c == 0:
        return DiscriminationVerdict(
            case_id=record.case_id,
            split=record.split,
            category="high_variance",
            n_reps=n,
            counts=counts,
            observed_effect=0.0,
            noise_ceiling=float(noise_ceiling),
            reasons=(
                f"no discordant reps (b=c=0) but arms do not settle into a single pass/fail "
                f"pattern across reps (a={a}, d={d}) -- concordant flakiness",
            ),
        )

    consistency = max(b, c) / (b + c)
    observed_effect = (b - c) / n
    if consistency < rule.min_direction_consistency:
        return DiscriminationVerdict(
            case_id=record.case_id,
            split=record.split,
            category="high_variance",
            n_reps=n,
            counts=counts,
            observed_effect=observed_effect,
            noise_ceiling=float(noise_ceiling),
            reasons=(
                f"discordant reps split {b} favor-with / {c} favor-without (consistency "
                f"{consistency:.3f} < rule threshold {rule.min_direction_consistency:.3f}) -- "
                "reps disagree with each other about which arm wins",
            ),
        )

    if abs(observed_effect) > noise_ceiling:
        category = "pass_with_fail_without" if b >= c else "fail_with_skill_but_pass_without"
        return DiscriminationVerdict(
            case_id=record.case_id,
            split=record.split,
            category=category,
            n_reps=n,
            counts=counts,
            observed_effect=observed_effect,
            noise_ceiling=float(noise_ceiling),
            reasons=(
                f"observed_effect={observed_effect:.3f} exceeds noise_ceiling="
                f"{noise_ceiling:.3f} for this key, direction consistent "
                f"(consistency={consistency:.3f} >= {rule.min_direction_consistency:.3f})",
            ),
        )

    return DiscriminationVerdict(
        case_id=record.case_id,
        split=record.split,
        category="high_variance",
        n_reps=n,
        counts=counts,
        observed_effect=observed_effect,
        noise_ceiling=float(noise_ceiling),
        reasons=(
            f"direction consistent (consistency={consistency:.3f}) but observed_effect="
            f"{observed_effect:.3f} does not exceed the measured A/A noise_ceiling="
            f"{noise_ceiling:.3f} -- indistinguishable from noise under this key",
        ),
    )


def classify_corpus(
    records: Iterable[SplitReps],
    key: NoiseFloorKey,
    floors: Iterable[Mapping[str, Any]],
    rule: DiscriminationRule | None,
    *,
    pass_threshold: float = 1.0,
) -> list[DiscriminationVerdict]:
    """Label every record. Never filters, reorders, or drops one (D1) -- returns exactly one
    `DiscriminationVerdict` per input `SplitReps`, in input order, so a caller can never end up
    with fewer labeled cases than it started with. This is the ONLY corpus-level entry point
    this module ships; there is no companion "discriminating cases only" filter for a lift
    computation to reach for, on purpose."""
    floors_list = list(floors)
    return [
        classify_case(r, key, floors_list, rule, pass_threshold=pass_threshold) for r in records
    ]


__all__ = [
    "ALL_CLASSIFICATION_STATUSES",
    "CASE_SPLITS",
    "DISCRIMINATION_CATEGORIES",
    "MIN_REPS_FOR_CLASSIFICATION",
    "NON_CATEGORY_STATUSES",
    "DiscriminationRule",
    "DiscriminationVerdict",
    "SplitReps",
    "classify_case",
    "classify_corpus",
    "fit_discrimination_rule",
]
