#!/usr/bin/env python3
"""Self-test for the trial-validity taxonomy (backlog item 21, Gap 19).

Imports and calls the shipped `_trial_validity.py` implementation directly -- never a
reimplementation of the logic under test (house rule). Covers: closed-enum membership; the D2
boundary (an adherence-shaped reason cannot be represented as `invalid`); the D4 void rule at,
just under, and just over each canon threshold; D5 denominator preservation (a case survives
even when every one of its trials is invalid); and D3 (a historical record with no
`trial_validity` key reads as "not_recorded", never "valid").

Run: python3 scripts/_trial_validity_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _canon import load_canon
from _trial_validity import (
    ArmStats,
    TrialRecord,
    cases_in_corpus,
    compute_void_verdict,
    historical_validity,
    mark_invalid,
    mark_valid,
    per_arm_stats,
    scoreable_trials,
)

SKILL_ROOT = HERE.parent
canon = load_canon(SKILL_ROOT)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


# ---- enum membership: the closed set is exactly what canon/trial-validity.toml documents ----
EXPECTED_REASONS = {"rate_limited", "auth_failure", "infra_timeout", "artifact_lost"}
check(
    set(canon.invalid_reasons) == EXPECTED_REASONS,
    f"canon.invalid_reasons drifted from the documented closed set: {sorted(canon.invalid_reasons)}",
)
for reason in EXPECTED_REASONS:
    tv = mark_invalid(reason, canon)
    check(
        tv.status == "invalid" and tv.reason == reason,
        f"mark_invalid({reason!r}) did not construct a matching invalid TrialValidity",
    )
check(
    mark_valid() == mark_valid(), "mark_valid() must be a stable value (status=valid, reason=None)"
)
check(mark_valid().status == "valid" and mark_valid().reason is None, "mark_valid() shape wrong")

# ---- D2 boundary: adherence/candidate failure reasons are UNREPRESENTABLE as invalid ----
ADHERENCE_SHAPED_REASONS = [
    "skill_not_triggered",
    "manipulation_check_failed",
    "skill_not_followed",
    "malformed_output",
    "candidate_timeout",
    "runaway_spend",
]
for reason in ADHERENCE_SHAPED_REASONS:
    try:
        mark_invalid(reason, canon)
        failures.append(
            f"mark_invalid({reason!r}) should have raised ValueError (D2 boundary) but did not"
        )
    except ValueError as exc:
        check(
            reason in str(exc), f"ValueError for {reason!r} did not name the rejected reason: {exc}"
        )

# ---- D5: denominator preservation. A case whose EVERY trial is invalid still appears in the
# corpus; only the scoreable-trial count shrinks. ----
trials_d5 = [
    TrialRecord("case-A", "with_skill", mark_valid()),
    TrialRecord("case-A", "without_skill", mark_valid()),
    TrialRecord("case-B", "with_skill", mark_invalid("rate_limited", canon)),
    TrialRecord("case-B", "without_skill", mark_invalid("auth_failure", canon)),
]
corpus_before = cases_in_corpus(trials_d5)
check(
    corpus_before == frozenset({"case-A", "case-B"}),
    f"corpus must be both cases, got {corpus_before}",
)
scoreable = scoreable_trials(trials_d5)
check(
    {t.case_id for t in scoreable} == {"case-A"},
    "scoreable_trials must drop case-B's trials (both invalid) while cases_in_corpus keeps case-B",
)
corpus_after = cases_in_corpus(trials_d5)
check(
    corpus_after == corpus_before,
    "the denominator must not shrink after computing scoreable_trials (Gap 19's shrinkage bug)",
)
check(
    "case-B" in cases_in_corpus(trials_d5),
    "case-B (zero scoreable trials) must remain in the corpus, not be silently dropped",
)

# ---- per_arm_stats sanity ----
stats = per_arm_stats(trials_d5)
check(
    stats["with_skill"] == ArmStats(total=2, invalid=1)
    and stats["without_skill"] == ArmStats(total=2, invalid=1),
    f"per_arm_stats miscounted: {stats}",
)

# ---- D4: mechanical void rule, at / just-under / just-over EACH threshold ----
MAX_RATE = canon.extra["trial_validity_max_invalid_rate_per_arm"]
MAX_ASYMMETRY = canon.extra["trial_validity_max_between_arm_asymmetry"]
check(
    MAX_RATE == 0.20,
    f"expected max_invalid_rate_per_arm 0.20 (see canon rationale), got {MAX_RATE}",
)
check(
    MAX_ASYMMETRY == 0.10,
    f"expected max_between_arm_asymmetry 0.10 (see canon rationale), got {MAX_ASYMMETRY}",
)


def _trials(arm: str, total: int, invalid: int) -> list[TrialRecord]:
    out = [TrialRecord(f"{arm}-case-{i}", arm, mark_valid()) for i in range(total - invalid)]
    out += [
        TrialRecord(f"{arm}-case-{i}", arm, mark_invalid("infra_timeout", canon))
        for i in range(total - invalid, total)
    ]
    return out


# per-arm rate boundary, symmetric between the two arms so asymmetry never trips instead.
for label, invalid_count, expect_void in (
    ("just under", 19, False),
    ("exactly at", 20, False),
    ("just over", 21, True),
):
    trials = _trials("with_skill", 100, invalid_count) + _trials(
        "without_skill", 100, invalid_count
    )
    verdict = compute_void_verdict(trials, canon)
    check(
        verdict.void is expect_void,
        f"per-arm-rate boundary ({label}, invalid={invalid_count}/100): expected void={expect_void}, "
        f"got {verdict.void} (reasons={verdict.reasons})",
    )

# between-arm asymmetry boundary, each arm individually under max_invalid_rate_per_arm (0.20) so
# only the asymmetry check can trip.
for label, arm_b_invalid, expect_void in (
    ("just under", 15, False),  # |0.20 - 0.15| = 0.05 < 0.10
    ("exactly at", 10, False),  # |0.20 - 0.10| = 0.10, not > 0.10
    ("just over", 4, True),  # |0.20 - 0.04| = 0.16 > 0.10
):
    trials = _trials("with_skill", 100, 20) + _trials("without_skill", 100, arm_b_invalid)
    verdict = compute_void_verdict(trials, canon)
    check(
        verdict.void is expect_void,
        f"asymmetry boundary ({label}, without_skill invalid={arm_b_invalid}/100): expected "
        f"void={expect_void}, got {verdict.void} (reasons={verdict.reasons})",
    )

# a single-arm comparison (no second arm to be asymmetric against) is judged on rate alone.
single_arm = _trials("with_skill", 100, 21)
verdict = compute_void_verdict(single_arm, canon)
check(
    verdict.void is True, "single-arm over-rate must still void (asymmetry check requires >=2 arms)"
)

# ---- D3: a historical record with no trial_validity key is legible as "not_recorded", never
# silently treated as "valid" ----
historical_record = {
    "case_id": "reality-persists-1",
    "arm": "arm_a",
    "rep": "k1",
    "verdict": "rejected",
}
check(
    historical_validity(historical_record) == "not_recorded",
    "a pre-item-21 record with no trial_validity key must read as 'not_recorded'",
)
check(
    historical_validity(historical_record) != "valid",
    "a pre-item-21 record must NEVER read as 'valid' by default",
)
recorded_valid = {**historical_record, "trial_validity": {"status": "valid", "reason": None}}
check(
    historical_validity(recorded_valid) == "valid", "an explicit valid record must read as 'valid'"
)
recorded_invalid = {
    **historical_record,
    "trial_validity": {"status": "invalid", "reason": "rate_limited"},
}
check(
    historical_validity(recorded_invalid) == "invalid",
    "an explicit invalid record must read as 'invalid'",
)
malformed = {**historical_record, "trial_validity": {"status": "sort-of"}}
check(
    historical_validity(malformed) == "not_recorded",
    "a malformed trial_validity.status must fall back to 'not_recorded', not crash or default valid",
)
check(
    historical_validity({}) == "not_recorded"
    and historical_validity({"trial_validity": None}) == "not_recorded",
    "empty record and explicit-null trial_validity must both read as 'not_recorded'",
)

if failures:
    print(f"_trial_validity_selftest: FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("_trial_validity_selftest: OK")
sys.exit(0)
