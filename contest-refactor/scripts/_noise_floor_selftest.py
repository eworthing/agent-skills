#!/usr/bin/env python3
"""Self-test for the A/A noise floor + paired significance gate (backlog item 20, Gap 18).

Imports and calls the shipped `_noise_floor.py` implementation directly -- never a
reimplementation of the logic under test (house rule). Covers: exact McNemar against
hand-computed values, including a small-k case where the exact and (independently, locally
computed here for comparison only) asymptotic chi-square answers diverge materially; the
sign-flip permutation test's exact-enumeration path against a hand-computed value, and its
Monte Carlo fallback; D2 (a floor computed under a different key is invisible to lookup_floor,
never fuzzy-matched); D4 (repeated trials for one case_id collapse to one aggregate row, so
they cannot inflate the test's n -- the pseudo-replication guard); D5 (all three outcomes --
significant, not_significant, inconclusive); D6 (no floor on file, or a floor with no numeric
noise_ceiling, makes a claim "unreportable", never a fabricated 0.0).

Run: python3 scripts/_noise_floor_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _canon import load_canon
from _noise_floor import (
    NoiseFloorKey,
    aggregate_cases,
    bonferroni_alpha,
    evaluate_lift,
    exact_mcnemar_p,
    load_floor_store,
    lookup_floor,
    make_key,
    mcnemar_counts,
    paired_permutation_p,
    required_n_for_power,
)
from _paired_baseline import LiftResult

SKILL_ROOT = HERE.parent
canon = load_canon(SKILL_ROOT)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


def lr(case_id: str, with_score: float, without_score: float) -> LiftResult:
    """Minimal LiftResult builder -- only the two fields _noise_floor.py reads matter here;
    everything else is item-22 bookkeeping this module never touches."""
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


# ---- exact McNemar: hand-computed values ------------------------------------------------------
# b=1, c=9 (n=10, m=1): p = 2 * (C(10,0) + C(10,1)) / 2**10 = 2*11/1024 = 22/1024 = 0.021484375
check(
    math.isclose(exact_mcnemar_p(1, 9), 22 / 1024, rel_tol=1e-12),
    f"exact_mcnemar_p(1, 9) = {exact_mcnemar_p(1, 9)}, expected 22/1024 = {22 / 1024}",
)
check(exact_mcnemar_p(1, 9) == exact_mcnemar_p(9, 1), "exact_mcnemar_p must be symmetric in b, c")
check(exact_mcnemar_p(0, 0) == 1.0, "n=0 (no discordant pairs) must be well-defined p=1.0")
# b=0, c=5 (n=5, m=0): p = 2 * C(5,0) / 2**5 = 2/32 = 0.0625
check(
    math.isclose(exact_mcnemar_p(0, 5), 2 / 32, rel_tol=1e-12),
    f"exact_mcnemar_p(0, 5) = {exact_mcnemar_p(0, 5)}, expected 2/32 = {2 / 32}",
)

# ---- exact vs. asymptotic: material divergence at small k -------------------------------------
# Independent, classical formula computed locally (not the module under test) purely to
# demonstrate the gap the module's docstring claims: the asymptotic chi-square approximation
# (uncorrected) at b=1, c=9 materially understates the exact p-value.
_chi2_uncorrected = (1 - 9) ** 2 / 10
_asymptotic_uncorrected_p = math.erfc(math.sqrt(_chi2_uncorrected / 2))
_exact_p = exact_mcnemar_p(1, 9)
check(
    _exact_p / _asymptotic_uncorrected_p > 1.5,
    f"expected exact ({_exact_p:.6f}) to exceed the uncorrected asymptotic answer "
    f"({_asymptotic_uncorrected_p:.6f}) by >1.5x at b=1,c=9 (small-k divergence); "
    f"ratio was {_exact_p / _asymptotic_uncorrected_p:.4f}",
)

# ---- paired permutation: hand-computed value, exact-enumeration path --------------------------
# deltas [0.4, 0.4, -0.2]: 8 sign patterns, observed sum = 0.6.
# |permuted sum| >= 0.6 for 4 of the 8 patterns (+++/--- give +-1.0, ++-/--+ give +-0.6) -> p=0.5.
perm = paired_permutation_p([0.4, 0.4, -0.2])
check(perm.exact is True, "n=3 <= default max_exact_n=20 must take the exact-enumeration path")
check(perm.n_used == 3, f"n_used must be 3 (no zero deltas), got {perm.n_used}")
check(
    math.isclose(perm.p_value, 0.5, rel_tol=1e-9),
    f"hand-computed paired_permutation_p([0.4,0.4,-0.2]) = {perm.p_value}, expected 0.5",
)
check(
    math.isclose(perm.observed_statistic, 0.6, rel_tol=1e-9),
    f"observed_statistic must be sum(deltas) = 0.6, got {perm.observed_statistic}",
)

# a delta of exactly 0 contributes nothing (n_used excludes it) and does not change the p-value.
perm_with_tie = paired_permutation_p([0.4, 0.4, -0.2, 0.0])
check(
    perm_with_tie.n_used == 3 and math.isclose(perm_with_tie.p_value, 0.5, rel_tol=1e-9),
    f"a zero delta must not enter n_used or change p_value: {perm_with_tie}",
)

# ---- paired permutation: Monte Carlo fallback path ---------------------------------------------
# Force the same 3-delta case through the Monte Carlo branch by lowering max_exact_n below 3;
# the seeded resample should land close to the hand-computed exact answer (0.5).
perm_mc = paired_permutation_p([0.4, 0.4, -0.2], max_exact_n=2, n_resamples=50_000, seed=7)
check(perm_mc.exact is False, "n=3 > max_exact_n=2 must take the Monte Carlo path")
check(perm_mc.n_used == 3, f"Monte Carlo path must still report n_used=3, got {perm_mc.n_used}")
check(
    abs(perm_mc.p_value - 0.5) < 0.02,
    f"Monte Carlo p_value ({perm_mc.p_value}) should land within 0.02 of the exact answer (0.5) "
    "at 50,000 resamples",
)
# same seed -> same result (deterministic, reproducible)
perm_mc_again = paired_permutation_p([0.4, 0.4, -0.2], max_exact_n=2, n_resamples=50_000, seed=7)
check(
    perm_mc.p_value == perm_mc_again.p_value,
    "a fixed seed must reproduce the identical Monte Carlo p_value",
)

# ---- D4: pseudo-replication -- repeated trials for one case_id never inflate n ----------------
dup_heavy = [lr("dup", 1.0, 0.0)] * 20 + [
    lr("a", 1.0, 1.0),
    lr("b", 0.0, 0.0),
    lr("c", 1.0, 0.0),
    lr("d", 0.0, 1.0),
]
agg = aggregate_cases(dup_heavy)
check(
    len(agg) == 5,
    f"24 LiftResults over 5 distinct case_ids must aggregate to 5 rows, got {len(agg)}",
)
dup_row = next(x for x in agg if x.case_id == "dup")
check(
    dup_row.n_reps == 20 and dup_row.with_pass and not dup_row.without_pass,
    f"the dup case's 20 reps must collapse to ONE aggregate row: {dup_row}",
)
a, b, c, d = mcnemar_counts(agg)
check(
    (a, b, c, d) == (1, 2, 1, 1),
    f"mcnemar_counts over the 5 aggregated rows must be (1,2,1,1) -- NOT scaled by the dup "
    f"case's 20 raw reps -- got {(a, b, c, d)}",
)
check(
    b + c == 3,
    f"n_informative (discordant pairs) must be 3, the same whether dup contributed 1 or 20 raw "
    f"records -- got {b + c}",
)

# ---- D2: key mismatch fails loudly (no fuzzy match) --------------------------------------------
key_a = make_key(
    model="claude-sonnet-5-20260115",
    grader_prompt_text="grade the transcript for X",
    sampling={"temperature": 0, "top_p": 1},
    harness_revision="abc1234",
    tool_configuration={"allowed_tools": ["Read", "Bash"]},
    scenario_corpus={"case-1": "prompt text 1", "case-2": "prompt text 2"},
)
# key_b differs from key_a in exactly one field: model bumped to a new version.
key_b = make_key(
    model="claude-sonnet-5-20260601",
    grader_prompt_text="grade the transcript for X",
    sampling={"temperature": 0, "top_p": 1},
    harness_revision="abc1234",
    tool_configuration={"allowed_tools": ["Read", "Bash"]},
    scenario_corpus={"case-1": "prompt text 1", "case-2": "prompt text 2"},
)
check(key_a.fingerprint() != key_b.fingerprint(), "a model bump must change the fingerprint")
floor_store_a_only = [{"key": key_a.as_dict(), "noise_ceiling": 0.03, "n_cases": 200}]
check(
    lookup_floor(key_a, floor_store_a_only) is not None,
    "an exact key match must find the stored floor",
)
check(
    lookup_floor(key_b, floor_store_a_only) is None,
    "a floor stored under key_a must NOT match key_b (one field differs -- model version) -- "
    "silently reusing it would launder a stale floor across a model upgrade",
)

# ---- D6: absent floor / malformed floor -> "unreportable", never a fabricated 0.0 -------------
sig_trials = [lr(f"case-{i}", 1.0, 0.0) for i in range(450)] + [
    lr(f"case-{450 + i}", 0.0, 1.0) for i in range(350)
]

verdict_no_floor = evaluate_lift(sig_trials, key_a, [], canon)
check(
    verdict_no_floor.status == "unreportable",
    f"no floor on file for key_a must yield status=unreportable, got {verdict_no_floor.status}",
)
check(
    verdict_no_floor.observed_effect is None and verdict_no_floor.p_value is None,
    "an unreportable verdict must not carry a computed effect or p-value at all",
)

floor_malformed = [{"key": key_a.as_dict(), "noise_ceiling": "measured later"}]
verdict_malformed = evaluate_lift(sig_trials, key_a, floor_malformed, canon)
check(
    verdict_malformed.status == "unreportable",
    f"a matched floor with a non-numeric noise_ceiling must yield status=unreportable, got "
    f"{verdict_malformed.status}",
)

# ---- D5: all three outcomes ---------------------------------------------------------------------
floor_a = [{"key": key_a.as_dict(), "noise_ceiling": 0.03, "n_cases": 200}]

# "significant": n_informative=800 clears required_n (778 at the canon defaults), observed
# effect = (450-350)/800 = 0.125 clears both min_effect (0.10) and the floor (0.03), and the
# exact McNemar p-value is far below alpha.
verdict_sig = evaluate_lift(sig_trials, key_a, floor_a, canon)
check(
    verdict_sig.status == "significant",
    f"expected status=significant, got {verdict_sig.status} (reasons={verdict_sig.reasons})",
)
check(verdict_sig.direction == "positive", f"with-arm won more discordant pairs: {verdict_sig}")
check(
    verdict_sig.n_informative == 800 and verdict_sig.case_n == 800,
    f"expected n_informative=case_n=800, got {verdict_sig}",
)

# "not_significant": same case_n / n_informative (well past required_n), but the swing is only
# (410-390)/800 = 0.025 -- below both min_effect (0.10) and the floor (0.03) -- so the run is
# adequately powered and the test still says no.
not_sig_trials = [lr(f"case-{i}", 1.0, 0.0) for i in range(410)] + [
    lr(f"case-{410 + i}", 0.0, 1.0) for i in range(390)
]
verdict_not_sig = evaluate_lift(not_sig_trials, key_a, floor_a, canon)
check(
    verdict_not_sig.status == "not_significant",
    f"expected status=not_significant, got {verdict_not_sig.status} "
    f"(reasons={verdict_not_sig.reasons})",
)
check(len(verdict_not_sig.reasons) >= 1, "not_significant must name at least one failed bar")

# "inconclusive": only 12 discordant pairs total, far under required_n (778) -- underpowered
# regardless of how large the apparent swing looks in this tiny sample.
small_trials = [lr(f"case-{i}", 1.0, 0.0) for i in range(10)] + [
    lr(f"case-{10 + i}", 0.0, 1.0) for i in range(2)
]
verdict_inconclusive = evaluate_lift(small_trials, key_a, floor_a, canon)
check(
    verdict_inconclusive.status == "inconclusive",
    f"expected status=inconclusive, got {verdict_inconclusive.status} "
    f"(n_informative={verdict_inconclusive.n_informative}, required_n="
    f"{verdict_inconclusive.required_n})",
)
check(
    verdict_inconclusive.required_n
    == required_n_for_power(
        canon.extra["noise_floor_min_effect"],
        canon.extra["noise_floor_alpha"],
        canon.extra["noise_floor_power_target"],
    ),
    "evaluate_lift's required_n must come from required_n_for_power() at the canon constants, "
    "not a hardcoded number",
)

# ---- continuous-mode path (non-binary scores) wired through the same accept rule --------------
continuous_trials = [
    lr("c1", 0.9, 0.4),
    lr("c2", 0.8, 0.5),
    lr("c3", 0.7, 0.6),
    lr("c4", 0.95, 0.3),
    lr("c5", 1.0, 0.2),
]
verdict_continuous = evaluate_lift(continuous_trials, key_a, floor_a, canon, mode="continuous")
check(
    verdict_continuous.status == "inconclusive",
    f"5 cases is far under required_n; continuous mode must still gate on power, got "
    f"{verdict_continuous.status}",
)
check(
    verdict_continuous.p_value is not None and verdict_continuous.direction == "positive",
    f"continuous mode must still compute a permutation p-value and a direction: "
    f"{verdict_continuous}",
)

# ---- bonferroni_alpha / required_n_for_power argument guards ----------------------------------
check(bonferroni_alpha(0.05, 5) == 0.01, "bonferroni_alpha(0.05, 5) must be 0.01")
check(bonferroni_alpha(0.05, 1) == 0.05, "family_size=1 must leave alpha unchanged")
try:
    bonferroni_alpha(0.05, 0)
    failures.append("bonferroni_alpha(alpha, 0) should have raised ValueError")
except ValueError:
    pass
try:
    required_n_for_power(0.0, 0.05, 0.80)
    failures.append("required_n_for_power(min_effect=0.0, ...) should have raised ValueError")
except ValueError:
    pass
try:
    evaluate_lift(sig_trials, key_a, floor_a, canon, mode="bogus")
    failures.append("evaluate_lift(mode='bogus') should have raised ValueError")
except ValueError:
    pass

# ---- the shipped store loads and is genuinely empty (D1: no A/A arm run by this item) ---------
store_path = SKILL_ROOT / "evals" / "noise_floor.json"
check(store_path.exists(), f"evals/noise_floor.json must exist: {store_path}")
loaded = load_floor_store(store_path)
check(
    loaded == [],
    f"evals/noise_floor.json must ship with an empty floors[] -- nothing measured yet -- got "
    f"{loaded!r}",
)

if failures:
    print(f"_noise_floor_selftest: FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("_noise_floor_selftest: OK")
sys.exit(0)
