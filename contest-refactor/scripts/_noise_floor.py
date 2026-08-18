"""A/A noise floor + paired significance gate (backlog item 20, Gap 18:
docs/review-skill-deep-dive-2026-08-17.md:797).

Item 21 (`_trial_validity.py`) answers "did this trial produce a scoreable outcome." Item 22
(`_paired_baseline.py`) answers "given a scoreable pair, what is the signed lift." This item
answers the question in front of both: **is that lift distinguishable from noise** -- CE's own
retune methodology found workflow adherence swinging 7/12 across two BYTE-IDENTICAL builds, so
any later claim smaller than that envelope is unsupported. Two mechanisms, both required before
a lift is reportable:

  1. **The measured A/A floor** (D2) -- an empirical noise ceiling, KEYED to model/version,
     grader prompt, sampling settings, harness revision, tool configuration, and scenario
     corpus (verbatim from the gap). Stored in `evals/noise_floor.json`, read here, never
     computed here -- this module ships zero A/A measurements (see that file's header). A
     lookup that does not exactly match every key field returns no floor -- silently
     substituting a near-miss floor is worse than refusing, so there is no fuzzy match anywhere
     in `lookup_floor()`.
  2. **The significance test** (D3) -- exact McNemar on paired binary outcomes (the accept
     rule's default), or a paired sign-flip permutation test for non-binary scores. Both are
     computed only after the unit of analysis is fixed (D4): `aggregate_cases()` collapses
     every repeated trial/judge sample for one `case_id` into ONE row via
     `statistics.median_low` before either test ever sees it, so re-running a case K times
     never inflates the test's n -- the classic pseudo-replication error, and the easiest way
     to manufacture significance from nothing.

D5 -- the accept rule (`evaluate_lift()`) has exactly three outcomes once a floor exists for the
key: `"significant"` (the effect clears both the measured floor and the preregistered
min_effect, and the test's p-value clears alpha), `"not_significant"` (adequately powered but
one of those bars was not cleared), or `"inconclusive"` (the case count could not have detected
`min_effect` at the target power regardless of what the p-value says). `alpha`, `min_effect`,
`power_target`, and `multiple_comparison_method` are named constants in
`canon/noise-floor.toml`, preregistered and UNFITTED -- there is no measured A/A corpus yet to
fit them against (this item ships mechanism, not measurement; see that file's header for the
full rationale, matching `canon/trial-validity.toml`'s posture on its own two thresholds).

D6 -- absence of a floor for the exact current key, or a floor record with no numeric
`noise_ceiling`, makes `evaluate_lift()` return `status="unreportable"` -- never a fabricated
floor, never a silent `floor=0`. This is the same rule `historical_validity()` applies to
records that predate a taxonomy: absence reads as absence, never as permission.

Cross-references: canon/noise-floor.toml (the four named constants), evals/noise_floor.json
(the floor store, empty -- D1: this item does not run the A/A arm), evals/README.md ("A/A noise
floor" section), scripts/_paired_baseline.py (LiftResult, consumed directly, not reimplemented),
scripts/_trial_validity.py (the sibling taxonomy this gate sits downstream of),
scripts/_noise_floor_selftest.py.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _canon import Canon
from _paired_baseline import LiftResult

# No sys.path handling here, by house convention (see _trial_validity.py / _paired_baseline.py):
# a pure library module, imported after the caller has already put scripts/ on sys.path.

# ---- D2: the noise-floor key ---------------------------------------------------------------


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NoiseFloorKey:
    """The six fields Gap 18 names verbatim ("model/version, grader prompt, sampling settings,
    harness revision, tool configuration, and scenario corpus"). Two are literals the caller
    already knows; four are content hashes so the key changes the instant the thing it names
    changes, without this module needing to understand that thing's internal shape.

      model                     literal -- a fully version-qualified model id (the "model" and
                                 "version" halves of the gap's phrase collapse into one field:
                                 a version-qualified id already names both).
      grader_prompt_hash        derived -- sha256 of the grader/judge prompt template text.
      sampling_hash             derived -- sha256 of the canonical-JSON sampling settings
                                 (temperature, top_p, max_tokens, ...).
      harness_revision          literal -- the git commit SHA of scripts/ at measurement time
                                 (the caller derives this via `git rev-parse HEAD`; this module
                                 stays pure and does not shell out).
      tool_configuration_hash   derived -- sha256 of the canonical-JSON tool/allowed-tools/MCP
                                 configuration.
      scenario_corpus_hash      derived -- sha256 of the canonical-JSON {case_id: content} map
                                 over the exact scenario set exercised.

    `fingerprint()` is the single value `lookup_floor()` matches on: it hashes ALL SIX fields
    together, so changing any one of them -- even one -- changes the fingerprint and a stored
    floor keyed to the old fingerprint no longer matches. That is the loud-failure property D2
    asks for: there is no partial-match path anywhere in this module.
    """

    model: str
    grader_prompt_hash: str
    sampling_hash: str
    harness_revision: str
    tool_configuration_hash: str
    scenario_corpus_hash: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    def fingerprint(self) -> str:
        return _sha256(_canonical_json(self.as_dict()))


def make_key(
    *,
    model: str,
    grader_prompt_text: str,
    sampling: Mapping[str, Any],
    harness_revision: str,
    tool_configuration: Mapping[str, Any],
    scenario_corpus: Mapping[str, str],
) -> NoiseFloorKey:
    """Derive a NoiseFloorKey from the raw material the harness already has on hand at
    dispatch time -- the actual prompt text, the actual settings dicts, the actual case-id ->
    content map -- rather than asking the caller to pre-hash anything itself."""
    return NoiseFloorKey(
        model=model,
        grader_prompt_hash=_sha256(grader_prompt_text),
        sampling_hash=_sha256(_canonical_json(dict(sampling))),
        harness_revision=harness_revision,
        tool_configuration_hash=_sha256(_canonical_json(dict(tool_configuration))),
        scenario_corpus_hash=_sha256(_canonical_json(dict(scenario_corpus))),
    )


def load_floor_store(path: Path) -> list[Mapping[str, Any]]:
    """Read evals/noise_floor.json's `floors` list. No validation beyond shape -- a malformed
    or missing `noise_ceiling` on an individual record is caught by `evaluate_lift()` (D6), not
    here, so a store with one good record and one placeholder record still loads."""
    data = json.loads(path.read_text())
    floors = data.get("floors", [])
    if not isinstance(floors, list):
        raise ValueError(f"{path}: 'floors' must be a list, got {type(floors).__name__}")
    return floors


def lookup_floor(
    key: NoiseFloorKey, floors: Iterable[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    """Exact match only (D2). Returns None -- never a nearest-neighbor guess -- the instant no
    stored record's key fingerprints identically to `key`."""
    fp = key.fingerprint()
    for record in floors:
        rec_key = record.get("key")
        if not isinstance(rec_key, Mapping):
            continue
        if _sha256(_canonical_json(dict(rec_key))) == fp:
            return record
    return None


# ---- D4: the unit of analysis is the case ---------------------------------------------------


@dataclass(frozen=True)
class CaseAggregate:
    case_id: str
    with_score: float
    without_score: float
    with_pass: bool
    without_pass: bool
    delta: float  # signed, with_score - without_score (mirrors LiftResult.delta, D1 of item 22)
    n_reps: int


def aggregate_cases(
    lift_results: Iterable[LiftResult], *, pass_threshold: float = 1.0
) -> list[CaseAggregate]:
    """Collapse every LiftResult sharing a case_id -- repeated trials, repeated judge samples,
    whatever grain the caller fed in -- into exactly ONE CaseAggregate per case_id (D4). Uses
    `statistics.median_low` per arm: the same reducer opendatahub's judge-sample aggregation
    uses (deep-dive fifth pass, "median-low over N samples, instability preserved"), chosen
    because it always returns one of the actually-observed scores rather than an interpolated
    average -- a case that flip-flops stays visibly a flip-flop rather than being smoothed into
    a fabricated midpoint.

    Feeding this function 1 case_id with 50 LiftResults and 4 case_ids with 1 LiftResult each
    returns a list of length 5, not 54 -- the pseudo-replication guard the selftest proves
    directly.
    """
    by_case: dict[str, list[LiftResult]] = {}
    for lr in lift_results:
        by_case.setdefault(lr.case_id, []).append(lr)
    out: list[CaseAggregate] = []
    for case_id in sorted(by_case):
        reps = by_case[case_id]
        with_score = statistics.median_low(r.with_outcome_score for r in reps)
        without_score = statistics.median_low(r.without_outcome_score for r in reps)
        out.append(
            CaseAggregate(
                case_id=case_id,
                with_score=with_score,
                without_score=without_score,
                with_pass=with_score >= pass_threshold,
                without_pass=without_score >= pass_threshold,
                delta=with_score - without_score,
                n_reps=len(reps),
            )
        )
    return out


def mcnemar_counts(aggregates: Sequence[CaseAggregate]) -> tuple[int, int, int, int]:
    """(a, b, c, d): both-pass, with-only, without-only, both-fail. Only b and c (the
    discordant pairs) enter `exact_mcnemar_p()` -- a and d carry no directional information
    under McNemar's own logic and are returned only for transparency in the verdict."""
    a = sum(1 for x in aggregates if x.with_pass and x.without_pass)
    b = sum(1 for x in aggregates if x.with_pass and not x.without_pass)
    c = sum(1 for x in aggregates if not x.with_pass and x.without_pass)
    d = sum(1 for x in aggregates if not x.with_pass and not x.without_pass)
    return a, b, c, d


# ---- D3: exact McNemar (binary) --------------------------------------------------------------


def exact_mcnemar_p(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value: the binomial sign test on the b+c discordant pairs
    under H0 (each discordant pair is equally likely to favor either arm). n=0 (no discordant
    pairs at all) returns 1.0 -- no evidence of any difference is well-defined, not undefined.

    p = min(1, 2 * P(X <= min(b,c))), X ~ Binomial(n=b+c, p=0.5). Computed with exact Python
    ints throughout (math.comb, arbitrary precision) and a single final int/int division to
    float -- the only rounding step, and it is IEEE-754 correctly-rounded division, not an
    accumulated approximation. This is deliberately NOT the asymptotic chi-square
    approximation (with or without continuity correction): the two diverge materially at small
    k, which is the regime this suite actually lives in (see the selftest's worked b=1,c=9
    example, ~2x apart from the uncorrected asymptotic answer).
    """
    n = b + c
    if n == 0:
        return 1.0
    m = min(b, c)
    tail = sum(math.comb(n, i) for i in range(m + 1))
    return min(1.0, 2 * tail / (2**n))


# ---- D3: paired permutation (non-binary scores) ----------------------------------------------


@dataclass(frozen=True)
class PermutationResult:
    p_value: float
    exact: bool  # True: every sign pattern enumerated. False: Monte Carlo (n exceeded max_exact_n).
    n_used: int  # count of NONZERO deltas actually permuted -- zero-deltas carry no directional
    # information under sign-flipping (flipping the sign of 0 does not change the statistic),
    # exactly mirroring McNemar's exclusion of concordant (a, d) pairs above.
    observed_statistic: float


def paired_permutation_p(
    deltas: Sequence[float],
    *,
    max_exact_n: int = 20,
    n_resamples: int = 100_000,
    seed: int = 0,
) -> PermutationResult:
    """Two-sided paired sign-flip permutation test on per-case signed deltas (already collapsed
    to one delta per case by `aggregate_cases()` -- D4 applies here exactly as it does to the
    binary path). H0: each case's delta is equally likely to have either sign (symmetric around
    zero). The observed statistic is the sum of deltas (equivalently the mean, up to the same
    constant divisor for every permutation, so the p-value is identical either way).

    n_used <= max_exact_n (default 20, 2**20 ~= 1e6 sign patterns): every sign pattern is
    enumerated exactly via itertools.product. Above that, `n_resamples` (default 100,000)
    sign-flips are drawn from a seeded `random.Random` -- deterministic for a fixed `seed`, so
    the same input always reproduces the same p-value.
    """
    nonzero = [d for d in deltas if d != 0]
    n = len(nonzero)
    observed = sum(deltas)
    if n == 0:
        return PermutationResult(p_value=1.0, exact=True, n_used=0, observed_statistic=observed)
    abs_observed = abs(observed)
    if n <= max_exact_n:
        extreme = 0
        total = 0
        for signs in itertools.product((1, -1), repeat=n):
            total += 1
            stat = sum(s * v for s, v in zip(signs, nonzero, strict=True))
            if abs(stat) >= abs_observed - 1e-12:
                extreme += 1
        return PermutationResult(
            p_value=extreme / total, exact=True, n_used=n, observed_statistic=observed
        )
    rng = random.Random(seed)
    extreme = 0
    for _ in range(n_resamples):
        stat = sum(v if rng.random() < 0.5 else -v for v in nonzero)
        if abs(stat) >= abs_observed - 1e-12:
            extreme += 1
    return PermutationResult(
        p_value=extreme / n_resamples, exact=False, n_used=n, observed_statistic=observed
    )


# ---- D5: the accept rule ----------------------------------------------------------------------


def bonferroni_alpha(alpha: float, family_size: int) -> float:
    """canon.extra['noise_floor_multiple_comparison_method'] == 'bonferroni': alpha divided by
    the number of simultaneous lift claims in one report. family_size=1 (the default caller
    shape -- one claim at a time) leaves alpha unchanged."""
    if family_size < 1:
        raise ValueError(f"family_size must be >= 1, got {family_size}")
    return alpha / family_size


def required_n_for_power(min_effect: float, alpha: float, power: float) -> int:
    """Minimum discordant-pair count for ~`power` probability of detecting a true discordant
    win-rate of 0.5 + min_effect/2 at two-sided significance `alpha` -- the standard
    normal-approximation sample-size formula for a one-sample proportion test against 0.5. This
    is a PLANNING heuristic only: `exact_mcnemar_p()` always computes the reported p-value
    exactly, never this approximation. The closed form (via `statistics.NormalDist`, stdlib)
    is used here instead of brute-force searching exact power at every candidate n because the
    effect sizes this suite preregisters are small enough that the honest answer is in the
    hundreds of pairs -- exhaustively evaluating exact_mcnemar_p() at every k for every
    candidate n up to that range would be tens of millions of calls for one planning number.
    """
    if not 0 < min_effect < 1:
        raise ValueError(f"min_effect must be in (0, 1), got {min_effect}")
    distance = min_effect / 2
    p_alt = 0.5 + distance
    z_alpha = statistics.NormalDist().inv_cdf(1 - alpha / 2)
    z_power = statistics.NormalDist().inv_cdf(power)
    n = ((z_alpha + z_power) ** 2) * p_alt * (1 - p_alt) / (distance**2)
    return math.ceil(n)


@dataclass(frozen=True)
class NoiseFloorVerdict:
    status: str  # "unreportable" | "inconclusive" | "significant" | "not_significant"
    case_n: int
    n_informative: int
    required_n: int | None
    observed_effect: float | None
    direction: str | None  # "positive" | "negative" | None (exactly-zero effect)
    p_value: float | None
    alpha_used: float | None
    floor_noise_ceiling: float | None
    reasons: tuple[str, ...]


def evaluate_lift(
    lift_results: Sequence[LiftResult],
    key: NoiseFloorKey,
    floors: Sequence[Mapping[str, Any]],
    canon: Canon,
    *,
    mode: str = "binary",
    pass_threshold: float = 1.0,
    family_size: int = 1,
) -> NoiseFloorVerdict:
    """The accept rule (D5). Three outcomes once a floor is on file for `key`:

      "significant"      the observed effect exceeds BOTH the measured A/A noise ceiling and
                          the preregistered min_effect, AND the significance test's p-value
                          clears alpha (Bonferroni-adjusted for family_size).
      "not_significant"  adequately powered (n_informative >= required_n) but one of the three
                          bars above was not cleared -- reasons[] says which.
      "inconclusive"      n_informative < required_n: the case count could not have detected
                          min_effect at the target power, so the p-value is not a verdict.

    A precondition gate sits in front of all three (D6): if no floor is on file for `key`, or
    the matched record has no numeric noise_ceiling, this returns "unreportable" with case_n
    and everything downstream left at 0/None -- never a fabricated floor, never a silent 0.0.
    """
    if mode not in ("binary", "continuous"):
        raise ValueError(f"mode must be 'binary' or 'continuous', got {mode!r}")

    aggregates = aggregate_cases(lift_results, pass_threshold=pass_threshold)
    case_n = len(aggregates)

    floor = lookup_floor(key, floors)
    if floor is None:
        return NoiseFloorVerdict(
            status="unreportable",
            case_n=case_n,
            n_informative=0,
            required_n=None,
            observed_effect=None,
            direction=None,
            p_value=None,
            alpha_used=None,
            floor_noise_ceiling=None,
            reasons=(
                f"no A/A noise floor recorded for key fingerprint {key.fingerprint()[:12]}... "
                "(D6: an unmeasured key makes a lift claim unreportable, never defaulted to "
                "floor=0)",
            ),
        )
    noise_ceiling = floor.get("noise_ceiling")
    if not isinstance(noise_ceiling, int | float):
        return NoiseFloorVerdict(
            status="unreportable",
            case_n=case_n,
            n_informative=0,
            required_n=None,
            observed_effect=None,
            direction=None,
            p_value=None,
            alpha_used=None,
            floor_noise_ceiling=None,
            reasons=(
                f"floor record matched key fingerprint {key.fingerprint()[:12]}... but carries "
                "no numeric noise_ceiling -- refusing to fabricate one (D6)",
            ),
        )

    alpha = canon.extra["noise_floor_alpha"]
    min_effect = canon.extra["noise_floor_min_effect"]
    power_target = canon.extra["noise_floor_power_target"]
    alpha_used = bonferroni_alpha(alpha, family_size)
    required_n = required_n_for_power(min_effect, alpha_used, power_target)

    if mode == "binary":
        _a, b, c, _d = mcnemar_counts(aggregates)
        n_informative = b + c
        p_value = exact_mcnemar_p(b, c)
        observed_effect = (b - c) / case_n if case_n else 0.0
    else:
        deltas = [x.delta for x in aggregates]
        perm = paired_permutation_p(deltas)
        n_informative = perm.n_used
        p_value = perm.p_value
        observed_effect = statistics.mean(deltas) if deltas else 0.0

    direction = "positive" if observed_effect > 0 else "negative" if observed_effect < 0 else None

    if n_informative < required_n:
        return NoiseFloorVerdict(
            status="inconclusive",
            case_n=case_n,
            n_informative=n_informative,
            required_n=required_n,
            observed_effect=observed_effect,
            direction=direction,
            p_value=p_value,
            alpha_used=alpha_used,
            floor_noise_ceiling=noise_ceiling,
            reasons=(
                f"n_informative={n_informative} < required_n={required_n} for "
                f"min_effect={min_effect}, alpha={alpha_used:.4g}, power={power_target} -- "
                "underpowered to detect the preregistered effect; the p-value is not a verdict",
            ),
        )

    reasons: list[str] = []
    clears_floor = abs(observed_effect) > noise_ceiling
    clears_min_effect = abs(observed_effect) >= min_effect
    clears_test = p_value < alpha_used
    if not clears_floor:
        reasons.append(
            f"|observed_effect|={abs(observed_effect):.4g} does not exceed the measured A/A "
            f"noise ceiling {noise_ceiling:.4g} for this key"
        )
    if not clears_min_effect:
        reasons.append(
            f"|observed_effect|={abs(observed_effect):.4g} < preregistered min_effect {min_effect}"
        )
    if not clears_test:
        reasons.append(f"p={p_value:.4g} >= alpha_used={alpha_used:.4g}")
    status = (
        "significant" if (clears_floor and clears_min_effect and clears_test) else "not_significant"
    )

    return NoiseFloorVerdict(
        status=status,
        case_n=case_n,
        n_informative=n_informative,
        required_n=required_n,
        observed_effect=observed_effect,
        direction=direction,
        p_value=p_value,
        alpha_used=alpha_used,
        floor_noise_ceiling=noise_ceiling,
        reasons=tuple(reasons),
    )


__all__ = [
    "CaseAggregate",
    "NoiseFloorKey",
    "NoiseFloorVerdict",
    "PermutationResult",
    "aggregate_cases",
    "bonferroni_alpha",
    "evaluate_lift",
    "exact_mcnemar_p",
    "load_floor_store",
    "lookup_floor",
    "make_key",
    "mcnemar_counts",
    "paired_permutation_p",
    "required_n_for_power",
]
