#!/usr/bin/env python3
"""Self-test for the discriminating-power classifier (backlog item 19, Gap 17).

Imports and calls the shipped `_discriminating_power.py` implementation directly -- never a
reimplementation of the logic under test (house rule). Covers: D1 (a lift denominator is
identical before and after classification; `fit_discrimination_rule()` raises on any
non-development record; validation/holdout cases are classified retrospectively without
altering their contribution to a lift summary); D3 (a single observation is refused, never
guessed from); D4 (a `case_kind="contract"` trial is structurally unable to produce a
`LiftResult`, proven in both directions, via `_paired_baseline.compute_lift()`); D6 (no fitted
rule, or no A/A floor on file, makes classification refuse rather than fabricate); and all five
Anthropic discrimination categories, including `fail_with_skill_but_pass_without` -- the one
this item exists to give a detector to.

Run: python3 scripts/_discriminating_power_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _discriminating_power import (
    ALL_CLASSIFICATION_STATUSES,
    CASE_SPLITS,
    DISCRIMINATION_CATEGORIES,
    MIN_REPS_FOR_CLASSIFICATION,
    DiscriminationRule,
    SplitReps,
    classify_case,
    classify_corpus,
    fit_discrimination_rule,
)
from _noise_floor import aggregate_cases, make_key
from _paired_baseline import (
    ArmResult,
    AssertionResult,
    LiftResult,
    PairedTrial,
    compute_lift,
    mark_valid,
)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


# ---- constants sanity -------------------------------------------------------------------------
check(
    CASE_SPLITS == ("development", "validation", "holdout"), f"CASE_SPLITS drifted: {CASE_SPLITS}"
)
check(
    DISCRIMINATION_CATEGORIES
    == (
        "always_pass_both",
        "always_fail_both",
        "pass_with_fail_without",
        "fail_with_skill_but_pass_without",
        "high_variance",
    ),
    f"DISCRIMINATION_CATEGORIES drifted: {DISCRIMINATION_CATEGORIES}",
)
check(
    set(ALL_CLASSIFICATION_STATUSES)
    == set(DISCRIMINATION_CATEGORIES) | {"contract", "unclassifiable"},
    f"ALL_CLASSIFICATION_STATUSES must be the five categories plus contract/unclassifiable: "
    f"{ALL_CLASSIFICATION_STATUSES}",
)
check(MIN_REPS_FOR_CLASSIFICATION == 2, "MIN_REPS_FOR_CLASSIFICATION must be 2 (D3 floor)")


# ---- helpers ------------------------------------------------------------------------------


def lr(case_id: str, with_score: float, without_score: float) -> LiftResult:
    """Minimal LiftResult builder, matching _noise_floor_selftest.py's own helper."""
    return LiftResult(
        case_id=case_id,
        with_outcome_score=with_score,
        without_outcome_score=without_score,
        delta=with_score - without_score,
        outcome_n=1,
        with_skill_contract_score=None,
        without_skill_contract_score=None,
        skill_contract_n_with=0,
        skill_contract_n_without=0,
    )


def reps(case_id: str, pattern: list[tuple[float, float]]) -> tuple[LiftResult, ...]:
    return tuple(lr(case_id, w, wo) for w, wo in pattern)


KEY = make_key(
    model="claude-fixture-1",
    grader_prompt_text="grade the fixture",
    sampling={"temperature": 0},
    harness_revision="deadbeef",
    tool_configuration={},
    scenario_corpus={"fixture": "v1"},
)
OTHER_KEY = make_key(
    model="claude-fixture-2",  # a different model -- must produce a different fingerprint (D2/item20)
    grader_prompt_text="grade the fixture",
    sampling={"temperature": 0},
    harness_revision="deadbeef",
    tool_configuration={},
    scenario_corpus={"fixture": "v1"},
)
FLOORS = [{"key": KEY.as_dict(), "noise_ceiling": 0.20}]
RULE = DiscriminationRule(min_direction_consistency=0.75, fitted_from_n_cases=42)  # test fixture


# ---- SplitReps validation -----------------------------------------------------------------
try:
    SplitReps(case_id="x", split="bogus", reps=())
    failures.append("SplitReps(split='bogus') should have raised ValueError")
except ValueError as exc:
    check("bogus" in str(exc), f"ValueError must name the rejected split: {exc}")
try:
    SplitReps(case_id="x", split="development", reps=(), case_kind="bogus")
    failures.append("SplitReps(case_kind='bogus') should have raised ValueError")
except ValueError as exc:
    check("bogus" in str(exc), f"ValueError must name the rejected case_kind: {exc}")
try:
    SplitReps(case_id="x", split="development", reps=(lr("y", 1.0, 0.0),))
    failures.append("SplitReps with a mismatched rep case_id should have raised ValueError")
except ValueError as exc:
    check("x" in str(exc) and "y" in str(exc), f"ValueError must name both case_ids: {exc}")


# ==== the five categories, hand-worked =========================================================
# All fixtures use RULE (min_direction_consistency=0.75) and FLOORS (noise_ceiling=0.20) above.

case_always_pass = SplitReps(
    "case-always-pass", "validation", reps("case-always-pass", [(1.0, 1.0)] * 10)
)
v = classify_case(case_always_pass, KEY, FLOORS, RULE)
check(v.category == "always_pass_both", f"expected always_pass_both, got {v.category}: {v.reasons}")
check(v.counts == (10, 0, 0, 0), f"expected counts (a=10,b=0,c=0,d=0), got {v.counts}")

case_always_fail = SplitReps(
    "case-always-fail", "validation", reps("case-always-fail", [(0.0, 0.0)] * 10)
)
v = classify_case(case_always_fail, KEY, FLOORS, RULE)
check(v.category == "always_fail_both", f"expected always_fail_both, got {v.category}: {v.reasons}")
check(v.counts == (0, 0, 0, 10), f"expected counts (a=0,b=0,c=0,d=10), got {v.counts}")

# pass_with_fail_without (value): with passes, without fails, every rep -- b=10, effect=1.0 > 0.20
case_value = SplitReps("case-value", "development", reps("case-value", [(1.0, 0.0)] * 10))
v = classify_case(case_value, KEY, FLOORS, RULE)
check(
    v.category == "pass_with_fail_without",
    f"expected pass_with_fail_without, got {v.category}: {v.reasons}",
)
check(v.observed_effect == 1.0, f"expected observed_effect 1.0, got {v.observed_effect}")

# fail_with_skill_but_pass_without (the skill may be hurting -- Gap 17's own headline case):
# with fails, without passes, every rep -- c=10, effect=-1.0, |effect| > 0.20.
case_harm = SplitReps("case-harm", "development", reps("case-harm", [(0.0, 1.0)] * 10))
v = classify_case(case_harm, KEY, FLOORS, RULE)
check(
    v.category == "fail_with_skill_but_pass_without",
    f"expected fail_with_skill_but_pass_without, got {v.category}: {v.reasons}",
)
check(v.observed_effect == -1.0, f"expected observed_effect -1.0, got {v.observed_effect}")
check(
    case_value.reps != case_harm.reps and v.category != "pass_with_fail_without",
    "fail_with_skill_but_pass_without must be distinguishable from its mirror category",
)

# high_variance, concordant flakiness: 5 reps both-pass, 5 reps both-fail, zero discordance.
case_concordant_flaky = SplitReps(
    "case-concordant-flaky",
    "validation",
    reps("case-concordant-flaky", [(1.0, 1.0)] * 5 + [(0.0, 0.0)] * 5),
)
v = classify_case(case_concordant_flaky, KEY, FLOORS, RULE)
check(
    v.category == "high_variance" and "concordant" in v.reasons[0],
    f"expected concordant-flakiness high_variance, got {v.category}: {v.reasons}",
)

# high_variance, mixed direction: b=6, c=4 -- consistency 0.6 < RULE's 0.75.
case_mixed = SplitReps(
    "case-mixed-direction",
    "holdout",
    reps("case-mixed-direction", [(1.0, 0.0)] * 6 + [(0.0, 1.0)] * 4),
)
v = classify_case(case_mixed, KEY, FLOORS, RULE)
check(
    v.category == "high_variance" and "disagree" in v.reasons[0],
    f"expected mixed-direction high_variance, got {v.category}: {v.reasons}",
)

# high_variance, consistent direction but under the A/A floor: a=9 (both pass), b=1 -- fully
# consistent (consistency=1.0 >= 0.75) but observed_effect = 1/10 = 0.1, which does not exceed
# noise_ceiling=0.20.
case_noisy = SplitReps(
    "case-consistent-but-noisy",
    "holdout",
    reps("case-consistent-but-noisy", [(1.0, 1.0)] * 9 + [(1.0, 0.0)]),
)
v = classify_case(case_noisy, KEY, FLOORS, RULE)
check(
    v.category == "high_variance" and "does not exceed" in v.reasons[0],
    f"expected floor-bounded high_variance, got {v.category}: {v.reasons}",
)
check(
    v.observed_effect is not None and abs(v.observed_effect - 0.1) < 1e-9,
    f"expected effect 0.1: {v}",
)


# ==== D3: a single observation is refused, never guessed from ==================================
case_one_rep = SplitReps("case-one-rep", "development", reps("case-one-rep", [(1.0, 0.0)]))
v = classify_case(case_one_rep, KEY, FLOORS, RULE)
check(
    v.category == "unclassifiable" and "single observation" in v.reasons[0],
    f"a 1-rep case must be unclassifiable, got {v.category}: {v.reasons}",
)
case_zero_reps = SplitReps("case-zero-reps", "development", ())
v = classify_case(case_zero_reps, KEY, FLOORS, RULE)
check(v.category == "unclassifiable", f"a 0-rep case must be unclassifiable, got {v.category}")


# ==== D6: no fitted rule -> refuse, never a hardcoded default ===================================
v = classify_case(case_value, KEY, FLOORS, None)
check(
    v.category == "unclassifiable" and "no DiscriminationRule fit yet" in v.reasons[0],
    f"rule=None must refuse, got {v.category}: {v.reasons}",
)


# ==== D6 (inherited from item 20): no A/A floor -> refuse, never floor=0 =======================
v = classify_case(case_value, OTHER_KEY, FLOORS, RULE)  # FLOORS is keyed to KEY, not OTHER_KEY
check(
    v.category == "unclassifiable" and "no A/A noise floor" in v.reasons[0],
    f"an unmatched key must refuse, got {v.category}: {v.reasons}",
)
bad_floors = [{"key": KEY.as_dict(), "noise_ceiling": "not-a-number"}]
v = classify_case(case_value, KEY, bad_floors, RULE)
check(
    v.category == "unclassifiable" and "no numeric noise_ceiling" in v.reasons[0],
    f"a non-numeric noise_ceiling must refuse, got {v.category}: {v.reasons}",
)


# ==== D4: case_kind="contract" is routed out of the five categories, not classified ============
case_contract = SplitReps("case-contract", "development", (), case_kind="contract")
v = classify_case(case_contract, KEY, FLOORS, RULE)
check(v.category == "contract", f"a contract case must classify as 'contract', got {v.category}")
check(
    v.category not in DISCRIMINATION_CATEGORIES, "contract must never be one of the five categories"
)


# ==== D4: bidirectional proof that a contract case cannot enter a lift computation ==============
# Byte-identical arms; the ONLY difference between the two trials is case_kind.
def _arm(passed: bool) -> ArmResult:
    return ArmResult(
        arm="with_skill",
        validity=mark_valid(),
        manipulation_ok=True,
        assertions=(AssertionResult("x", "outcome", passed),),
    )


with_a = _arm(True)
without_a = ArmResult(
    arm="without_skill",
    validity=mark_valid(),
    manipulation_ok=True,
    assertions=(AssertionResult("x", "outcome", False),),
)
eligible_trial = PairedTrial("case-gate", with_a, without_a)  # default case_kind="lift_eligible"
contract_trial = PairedTrial("case-gate", with_a, without_a, case_kind="contract")
check(
    compute_lift(eligible_trial) is not None,
    "direction 1: a lift_eligible trial (byte-identical arms) must produce a LiftResult",
)
check(
    compute_lift(contract_trial) is None,
    "direction 2: the SAME arms with case_kind='contract' must NOT produce a LiftResult",
)


# ==== fit_discrimination_rule(): raises on non-development, refuses on nothing to fit ===========
try:
    fit_discrimination_rule([SplitReps("v1", "validation", reps("v1", [(1.0, 0.0)] * 5))])
    failures.append("fit_discrimination_rule() on a validation-split record should have raised")
except ValueError as exc:
    check(
        "validation" in str(exc) and "v1" in str(exc),
        f"ValueError must name the offending split and case_id: {exc}",
    )
try:
    fit_discrimination_rule([SplitReps("h1", "holdout", reps("h1", [(1.0, 0.0)] * 5))])
    failures.append("fit_discrimination_rule() on a holdout-split record should have raised")
except ValueError:
    pass

check(
    fit_discrimination_rule([]) is None,
    "fit_discrimination_rule([]) must return None, not a default",
)
check(
    fit_discrimination_rule(
        [SplitReps("d1", "development", reps("d1", [(1.0, 1.0)] * 5))]  # zero discordance
    )
    is None,
    "a development corpus with zero discordant reps has nothing to fit a consistency rule from",
)

# Hand-worked fit: three dev cases, discordance patterns b=3,c=2 / b=4,c=1 / b=5,c=0 -> per-case
# consistency 0.6, 0.8, 1.0 -> median = 0.8.
dev_a = SplitReps("dev-a", "development", reps("dev-a", [(1.0, 0.0)] * 3 + [(0.0, 1.0)] * 2))
dev_b = SplitReps("dev-b", "development", reps("dev-b", [(1.0, 0.0)] * 4 + [(0.0, 1.0)] * 1))
dev_c = SplitReps("dev-c", "development", reps("dev-c", [(1.0, 0.0)] * 5))
fitted = fit_discrimination_rule([dev_a, dev_b, dev_c])
check(fitted is not None, "a dev corpus with discordance must fit a rule")
check(
    fitted is not None and abs(fitted.min_direction_consistency - 0.8) < 1e-9,
    f"expected median consistency 0.8, got {fitted.min_direction_consistency if fitted else None}",
)
check(
    fitted is not None and fitted.fitted_from_n_cases == 3,
    f"expected fitted_from_n_cases=3, got {fitted.fitted_from_n_cases if fitted else None}",
)


# ==== D1: classify_corpus never filters, reorders, or drops a record ===========================
mixed_corpus = [
    case_always_pass,
    case_value,
    case_harm,
    case_concordant_flaky,
    case_mixed,
    case_noisy,
    case_one_rep,
    case_contract,
    dev_a,
    dev_b,
    dev_c,
]
before_len = len(mixed_corpus)
verdicts = classify_corpus(mixed_corpus, KEY, FLOORS, RULE)
check(
    len(verdicts) == before_len,
    f"classify_corpus must return exactly one verdict per input record: "
    f"{len(verdicts)} verdicts for {before_len} records",
)
check(
    [v.case_id for v in verdicts] == [r.case_id for r in mixed_corpus],
    "classify_corpus must preserve input order and never drop a case_id",
)
check(
    len(mixed_corpus) == before_len, "classify_corpus must never mutate the input list it is given"
)


# ==== D1: labeling validation/holdout cases never alters their contribution to a lift summary ===
# "Contribution to a lift claim" computed via item 20's own aggregate_cases() -- the actual
# machinery a lift report would use -- over the underlying LiftResults, before and after this
# module's classifier runs over the SAME records.
val_hold_records = [
    case_concordant_flaky,
    case_mixed,
    case_noisy,
]  # validation + holdout, from above
flat_lifts = [r for rec in val_hold_records for r in rec.reps]
before_aggregates = aggregate_cases(flat_lifts)
before_summary = sorted(
    (a.case_id, a.delta, a.with_pass, a.without_pass) for a in before_aggregates
)
_ = classify_corpus(val_hold_records, KEY, FLOORS, RULE)  # label them; must be a no-op on the above
after_aggregates = aggregate_cases(flat_lifts)
after_summary = sorted((a.case_id, a.delta, a.with_pass, a.without_pass) for a in after_aggregates)
check(
    before_summary == after_summary,
    f"a lift summary over validation/holdout cases must be identical before and after "
    f"classification:\n  before={before_summary}\n  after={after_summary}",
)


# ==== D5: the judge-alignment suite cannot be coerced into this module's input type =============
# reviewer-cases' own grain (evals/README.md Layer 3): {targeted finding, diff} -> verdict JSON,
# scored mechanical+semantic against a reference verdict. It has no with_outcome_score /
# without_outcome_score / signed delta over a with-skill/without-skill pair -- the fields a
# LiftResult requires. Constructing one from a reviewer-case-shaped record fails at the
# dataclass constructor, before this module's classification logic ever runs.
reviewer_case_shaped = {
    "case_id": "reality-persists",
    "arm": "arm_b",
    "verdict": "reject",
    "reason": "smell still present in source",
}
try:
    LiftResult(**reviewer_case_shaped)  # type: ignore[arg-type]
    failures.append(
        "a reviewer-case-shaped record must NOT satisfy LiftResult's constructor -- if it did, "
        "the judge-alignment suite could be coerced into this module's input type"
    )
except TypeError:
    pass


if failures:
    print(f"_discriminating_power_selftest: FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("_discriminating_power_selftest: OK")
sys.exit(0)
