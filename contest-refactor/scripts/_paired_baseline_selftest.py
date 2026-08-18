#!/usr/bin/env python3
"""Self-test for the paired with/without-skill lift harness (backlog item 22, Gap 20).

Imports and calls the shipped `_paired_baseline.py` implementation directly -- never a
reimplementation of the logic under test (house rule). Covers: D1 (a genuinely negative,
unfloored delta); D2 (a skill_contract criterion cannot enter the lift numerator or
denominator, proven differentially); D3 (the tautology screen flags an undeclared hit,
passes a declared one, and never flags a skill_contract-classed criterion at all); D4 (the
seam with item 21 -- a manipulation-check failure is counted, never voids, and item 21's own
`mark_invalid()` refuses a manipulation-shaped reason); D6 (an unclassified assertion enters
neither score, and absence of the field reads as "unclassified", never a default class).

Run: python3 scripts/_paired_baseline_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _canon import load_canon
from _paired_baseline import (
    CRITERION_CLASSES,
    DECLARED_TAUTOLOGY_EXCEPTIONS,
    ArmResult,
    AssertionResult,
    PairedTrial,
    compute_lift,
    criterion_class,
    mark_valid,
    screen_criteria,
    undeclared_tautology_failures,
)
from _trial_validity import mark_invalid

SKILL_ROOT = HERE.parent
canon = load_canon(SKILL_ROOT)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


# ---- criterion_class(): closed set, D6 default, invalid value rejected -------------------
check(
    CRITERION_CLASSES == ("outcome", "skill_contract"),
    f"CRITERION_CLASSES drifted: {CRITERION_CLASSES}",
)
check(
    criterion_class({}) == "unclassified",
    "an assertion with no criterion_class key must read as 'unclassified'",
)
check(
    criterion_class({"criterion_class": None}) == "unclassified",
    "an explicit-null criterion_class must read as 'unclassified', not crash",
)
check(
    criterion_class({"criterion_class": "outcome"}) == "outcome",
    "an explicit 'outcome' must round-trip",
)
check(
    criterion_class({"criterion_class": "skill_contract"}) == "skill_contract",
    "an explicit 'skill_contract' must round-trip",
)
try:
    criterion_class({"criterion_class": "bogus"})
    failures.append("criterion_class('bogus') should have raised ValueError (closed set)")
except ValueError as exc:
    check("bogus" in str(exc), f"ValueError for 'bogus' did not name the rejected value: {exc}")


# ---- helpers for building fixture trials --------------------------------------------------


def _arm(arm: str, manipulation_ok: bool, assertions: tuple[AssertionResult, ...]) -> ArmResult:
    return ArmResult(
        arm=arm, validity=mark_valid(), manipulation_ok=manipulation_ok, assertions=assertions
    )


# ---- D1: a genuinely negative delta, never floored at zero --------------------------------
# with-skill arm fails its one outcome criterion; without-skill arm passes it -- the skill is
# actively HURTING (Gap 17's fail-with-skill-but-pass-without category).
trial_hurts = PairedTrial(
    case_id="case-hurts",
    with_arm=_arm("with_skill", True, (AssertionResult("x", "outcome", False),)),
    without_arm=_arm("without_skill", True, (AssertionResult("x", "outcome", True),)),
)
lift_hurts = compute_lift(trial_hurts)
check(lift_hurts is not None, "a clean paired trial must produce a LiftResult")
check(
    lift_hurts.delta == -0.5,
    f"expected delta -0.5 (with=0.5, without=1.0 over 2 outcome assertions incl. manipulation "
    f"check), got {lift_hurts.delta}",
)
check(lift_hurts.delta < 0, "a negative delta must survive unfloored -- this is D1's whole point")


# ---- D2: a skill_contract criterion cannot enter the lift numerator or denominator --------
# Two trials, identical except one skill_contract assertion's pass/fail is flipped. If the
# lift computation is honoring D2, delta and outcome_n must be IDENTICAL between them; only
# the (separately reported) skill_contract score may differ.
def _trial_d2(skill_contract_passed: bool) -> PairedTrial:
    return PairedTrial(
        case_id="case-d2",
        with_arm=_arm(
            "with_skill",
            True,
            (
                AssertionResult("o1", "outcome", True),
                AssertionResult("sc1", "skill_contract", skill_contract_passed),
            ),
        ),
        without_arm=_arm("without_skill", True, (AssertionResult("o1", "outcome", False),)),
    )


lift_sc_pass = compute_lift(_trial_d2(True))
lift_sc_fail = compute_lift(_trial_d2(False))
check(
    lift_sc_pass.delta == lift_sc_fail.delta,
    f"flipping a skill_contract assertion's pass/fail must not move delta at all: "
    f"{lift_sc_pass.delta} vs {lift_sc_fail.delta}",
)
check(
    lift_sc_pass.outcome_n == lift_sc_fail.outcome_n,
    "flipping a skill_contract assertion must not move outcome_n (the lift denominator) either",
)
check(
    lift_sc_pass.with_skill_contract_score == 1.0 and lift_sc_fail.with_skill_contract_score == 0.0,
    f"the skill_contract score itself MUST move (it is reported, just never mixed into lift): "
    f"{lift_sc_pass.with_skill_contract_score} vs {lift_sc_fail.with_skill_contract_score}",
)
check(
    lift_sc_pass.without_skill_contract_score is None,
    "the without-skill arm has zero skill_contract assertions here -- must read None, not 0.0 "
    "(0.0 would misreport 'scored zero' rather than 'nothing to score')",
)

# ---- D6: an unclassified assertion enters NEITHER score ------------------------------------
trial_no_unclassified = PairedTrial(
    case_id="case-d6",
    with_arm=_arm("with_skill", True, (AssertionResult("o1", "outcome", True),)),
    without_arm=_arm("without_skill", True, (AssertionResult("o1", "outcome", False),)),
)
trial_with_unclassified = PairedTrial(
    case_id="case-d6",
    with_arm=_arm(
        "with_skill",
        True,
        (AssertionResult("o1", "outcome", True), AssertionResult("u1", "unclassified", False)),
    ),
    without_arm=_arm("without_skill", True, (AssertionResult("o1", "outcome", False),)),
)
lift_no_u = compute_lift(trial_no_unclassified)
lift_with_u = compute_lift(trial_with_unclassified)
check(
    lift_no_u.delta == lift_with_u.delta and lift_no_u.outcome_n == lift_with_u.outcome_n,
    "adding an 'unclassified' assertion must change nothing about the lift -- it enters "
    f"neither score (delta {lift_no_u.delta} vs {lift_with_u.delta}, "
    f"outcome_n {lift_no_u.outcome_n} vs {lift_with_u.outcome_n})",
)
check(
    lift_with_u.skill_contract_n_with == 0,
    "an 'unclassified' assertion must not leak into the skill_contract count either",
)


# ---- D4: the seam with item 21 --------------------------------------------------------------
# (a) a manipulation-check failure is COUNTED (lowers the with-arm's outcome score) and never
#     voids the trial -- compute_lift must still return a LiftResult.
without_ok = _arm("without_skill", True, ())
with_manip_ok = _arm("with_skill", True, ())
with_manip_fail = _arm("with_skill", False, ())

lift_manip_ok = compute_lift(PairedTrial("case-mc", with_manip_ok, without_ok))
lift_manip_fail = compute_lift(PairedTrial("case-mc", with_manip_fail, without_ok))
check(
    lift_manip_fail is not None,
    "a manipulation-check failure must NEVER void the trial (D4) -- compute_lift must still "
    "return a LiftResult, not None",
)
if lift_manip_fail is not None:  # guard: don't crash the rest of the suite on a D4 violation
    check(
        lift_manip_fail.with_outcome_score < lift_manip_ok.with_outcome_score,
        f"a manipulation-check failure must be COUNTED as a failing outcome assertion "
        f"(got {lift_manip_fail.with_outcome_score} vs a clean {lift_manip_ok.with_outcome_score})",
    )

# (b) item 21's own boundary refuses to let this failure be spent as an invalid_reason -- the
#     seam is enforced by mark_invalid()'s closed enum, not by anything item 22 adds.
for manipulation_shaped_reason in (
    "manipulation_check_failed",
    "skill_not_triggered",
    "skill_not_followed",
):
    try:
        mark_invalid(manipulation_shaped_reason, canon)
        failures.append(
            f"mark_invalid({manipulation_shaped_reason!r}) should have raised ValueError -- "
            "item 22 must not be able to route a manipulation/adherence failure through item "
            "21's exogenous-only invalid_reasons enum"
        )
    except ValueError:
        pass

# (c) contrast case: an EXOGENOUS invalid arm (item 21's actual void path) makes compute_lift
#     return None -- this is the only thing that voids, and it is unrelated to manipulation_ok.
with_exogenous_invalid = ArmResult(
    arm="with_skill",
    validity=mark_invalid("rate_limited", canon),
    manipulation_ok=True,
    assertions=(),
)
lift_exogenous = compute_lift(PairedTrial("case-exo", with_exogenous_invalid, without_ok))
check(
    lift_exogenous is None,
    "an exogenous-invalid arm (item 21's TrialValidity) must make compute_lift return None -- "
    "the only voiding path, and distinct from a manipulation-check failure which never voids",
)


# ---- D3: the tautology screen ---------------------------------------------------------------
CASE_HIT = {
    "name": "case-tautology-hit",
    "assertions": [
        {
            "text": "flagged_smells names suppression-as-fix",
            "criterion_class": "outcome",
        }
    ],
}
CASE_CLEAN = {
    "name": "case-tautology-clean",
    "assertions": [
        {
            "text": "the refactor preserves existing external behavior under load",
            "criterion_class": "outcome",
        }
    ],
}
CASE_SAME_TEXT_BUT_SKILL_CONTRACT = {
    "name": "case-tautology-reclassified",
    "assertions": [
        {
            "text": "flagged_smells names suppression-as-fix",
            "criterion_class": "skill_contract",
        }
    ],
}

findings_hit = screen_criteria([CASE_HIT], canon)
check(
    len(findings_hit) == 1 and not findings_hit[0].declared,
    f"an 'outcome'-classed criterion naming skill vocabulary must be flagged, undeclared: {findings_hit}",
)
check(
    len(undeclared_tautology_failures(findings_hit)) == 1,
    "the undeclared hit must appear in undeclared_tautology_failures() -- this is what a gate fails on",
)

findings_clean = screen_criteria([CASE_CLEAN], canon)
check(
    findings_clean == [],
    f"a criterion with no skill-vocabulary text must not be flagged: {findings_clean}",
)

findings_reclassified = screen_criteria([CASE_SAME_TEXT_BUT_SKILL_CONTRACT], canon)
check(
    findings_reclassified == [],
    "the screen must ONLY ever police 'outcome'-classed criteria -- reclassifying the exact "
    f"same text to 'skill_contract' must exit the tautology boundary entirely, got {findings_reclassified}",
)

# declared exception: house pattern from _token_budget_selftest.py (mutate the module dict,
# save/restore) rather than adding a bespoke parameter to screen_criteria().
_saved_exceptions = dict(DECLARED_TAUTOLOGY_EXCEPTIONS)
try:
    DECLARED_TAUTOLOGY_EXCEPTIONS[("case-tautology-hit", 0)] = (
        "selftest-declared: proof of the D3 exception path"
    )
    findings_declared = screen_criteria([CASE_HIT], canon)
    check(
        len(findings_declared) == 1
        and findings_declared[0].declared
        and findings_declared[0].reason,
        f"a declared exception must still be REPORTED (stays visible) but marked declared=True: {findings_declared}",
    )
    check(
        undeclared_tautology_failures(findings_declared) == [],
        "a declared exception must never appear in undeclared_tautology_failures()",
    )
finally:
    DECLARED_TAUTOLOGY_EXCEPTIONS.clear()
    DECLARED_TAUTOLOGY_EXCEPTIONS.update(_saved_exceptions)

# restore sanity: after restoring, the same case is undeclared again (proves the finally-block
# restore actually worked, not just that the dict was ever populated)
findings_after_restore = screen_criteria([CASE_HIT], canon)
check(
    len(findings_after_restore) == 1 and not findings_after_restore[0].declared,
    "DECLARED_TAUTOLOGY_EXCEPTIONS must be restored to its shipped (empty-for-this-key) state "
    f"after the test: {findings_after_restore}",
)


if failures:
    print(f"_paired_baseline_selftest: FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("_paired_baseline_selftest: OK")
sys.exit(0)
