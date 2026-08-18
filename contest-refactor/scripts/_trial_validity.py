"""Trial-validity taxonomy for the paired skill-lift harness (backlog item 21, Gap 19:
docs/review-skill-deep-dive-2026-08-17.md:822).

A "trial" is one arm/rep execution inside a paired with-skill / without-skill comparison
(reviewer_baseline's case x arm x K reps, exec_replay's arm x K reps, advisory/principal's
no_skill/pre_edit/current arms, ...). This module answers three questions mechanically:

  1. Was a trial's non-outcome EXOGENOUS to the candidate (rate limit, auth failure, harness
     timeout, lost artifact -- canon/trial-validity.toml `invalid_reasons`), or was it an
     adherence/candidate failure the suite must still count? `mark_invalid()` makes the second
     case unrepresentable by raising on any reason outside the closed enum (D2).
  2. Does an admitted case ever leave the corpus because one of its trials went invalid?
     `cases_in_corpus()` says no -- the denominator invariant (D5).
  3. Given per-arm invalid rates, is the comparison itself void? `compute_void_verdict()` -- the
     mechanical rule (D4), thresholds read from canon, never fitted from data that doesn't exist
     yet.

D3 (never back-fill validity onto historical measured baselines): `historical_validity()` reads
a raw JSON record and returns "not_recorded" when it predates this taxonomy -- never "valid".
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class TrialValidity:
    status: str  # "valid" | "invalid"
    reason: str | None  # canon.invalid_reasons token; set iff status == "invalid"


def mark_valid() -> TrialValidity:
    return TrialValidity(status="valid", reason=None)


def mark_invalid(reason: str, canon) -> TrialValidity:
    """Construct an invalid-trial record. Raises ValueError if `reason` is not one of the
    closed exogenous-only tokens in canon/trial-validity.toml. This is the D2 boundary as code:
    an adherence-shaped reason (didn't trigger, wasn't followed, malformed output, a candidate's
    own runaway timeout, blown spend budget) has no token to spend here, so it cannot be voided
    -- it falls through to the suite's ordinary grading path as a counted failure instead."""
    if reason not in canon.invalid_reasons:
        raise ValueError(
            f"{reason!r} is not an exogenous invalid_reason (canon/trial-validity.toml); "
            "adherence and candidate failures are COUNTED failures, never invalid trials"
        )
    return TrialValidity(status="invalid", reason=reason)


@dataclass(frozen=True)
class TrialRecord:
    case_id: str
    arm: str
    validity: TrialValidity


def cases_in_corpus(trials: Iterable[TrialRecord]) -> frozenset[str]:
    """The denominator (D5): every case_id with at least one recorded trial, regardless of that
    trial's validity. An invalid trial marks the TRIAL unscoreable; it never removes the CASE --
    a case whose every trial went invalid still appears here, reported as zero scoreable trials
    for that unit rather than silently dropped (deep-dive:462-465)."""
    return frozenset(t.case_id for t in trials)


def scoreable_trials(trials: Iterable[TrialRecord]) -> list[TrialRecord]:
    """Trials usable for a lift comparison. Narrowing THIS list must never be read as narrowing
    cases_in_corpus() -- that conflation is exactly the denominator shrinkage Gap 19 exists to
    prevent."""
    return [t for t in trials if t.validity.status != "invalid"]


@dataclass(frozen=True)
class ArmStats:
    total: int
    invalid: int

    @property
    def rate(self) -> float:
        return self.invalid / self.total if self.total else 0.0


def per_arm_stats(trials: Iterable[TrialRecord]) -> dict[str, ArmStats]:
    """Invalid counts/rates per arm, machine-readable (the brief's "invalid counts are reported
    per arm with machine-readable reasons")."""
    totals: dict[str, int] = {}
    invalids: dict[str, int] = {}
    for t in trials:
        totals[t.arm] = totals.get(t.arm, 0) + 1
        if t.validity.status == "invalid":
            invalids[t.arm] = invalids.get(t.arm, 0) + 1
    return {arm: ArmStats(total=n, invalid=invalids.get(arm, 0)) for arm, n in totals.items()}


@dataclass(frozen=True)
class VoidVerdict:
    void: bool
    reasons: tuple[str, ...]
    per_arm_rates: Mapping[str, float]


def compute_void_verdict(trials: Iterable[TrialRecord], canon) -> VoidVerdict:
    """D4: void — mechanically, not by judgment — when EITHER threshold in
    canon/trial-validity.toml is exceeded. Strictly greater-than: a rate or asymmetry exactly AT
    a threshold does not void (the threshold is the declared maximum tolerable value, not a
    floor)."""
    max_rate = canon.extra["trial_validity_max_invalid_rate_per_arm"]
    max_asymmetry = canon.extra["trial_validity_max_between_arm_asymmetry"]
    stats = per_arm_stats(trials)
    rates = {arm: s.rate for arm, s in stats.items()}
    reasons: list[str] = []
    for arm, r in sorted(rates.items()):
        if r > max_rate:
            reasons.append(
                f"arm {arm!r} invalid rate {r:.4f} exceeds max_invalid_rate_per_arm {max_rate}"
            )
    if len(rates) >= 2:
        asymmetry = max(rates.values()) - min(rates.values())
        if asymmetry > max_asymmetry:
            reasons.append(
                f"between-arm asymmetry {asymmetry:.4f} exceeds max_between_arm_asymmetry {max_asymmetry}"
            )
    return VoidVerdict(void=bool(reasons), reasons=tuple(reasons), per_arm_rates=rates)


def historical_validity(record: Mapping) -> str:
    """Read a raw JSON trial/rep/attempt record's validity without assuming presence. Returns
    'not_recorded' when the record predates this taxonomy (no `trial_validity` key, or a
    malformed one) -- NEVER 'valid'. D3: a `schema_version` bump on a baseline file marks that
    FUTURE records in it may carry `trial_validity`; it does not retrofit meaning onto records
    that already exist there. Every reader of historical baseline JSON must route through this
    function rather than `record.get("trial_validity", {}).get("status", "valid")`-shaped code,
    which would silently promote absence to validity."""
    tv = record.get("trial_validity") if isinstance(record, Mapping) else None
    if not isinstance(tv, Mapping):
        return "not_recorded"
    status = tv.get("status")
    if status not in ("valid", "invalid"):
        return "not_recorded"
    return status
