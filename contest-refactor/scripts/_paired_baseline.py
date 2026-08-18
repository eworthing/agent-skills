"""Paired with/without-skill lift harness (backlog item 22, Gap 20:
docs/review-skill-deep-dive-2026-08-17.md:843; backlog row :1150).

Anthropic's skill-creator makes the baseline structural -- spawn a with-skill and a
without-skill arm on the same case, score the delta. Two failure modes make that unsafe on
its own, and both are load-bearing here:

  1. A criterion the baseline arm structurally cannot satisfy (it names our vocabulary, our
     field names, our artifact shape) rewards running the skill, not completing the task --
     "an invalid evaluation item" (skilllens, quoted in Gap 20). D2/D3 below.
  2. Flooring the delta at zero (skilllens's own choice) erases the case Gap 17 names with no
     detector anywhere in this suite: fail-with-skill-but-pass-without, the skill actively
     hurting. D1 below is a DELIBERATE divergence from skilllens on this one point.

This module ships the classification, the lift computation, and the tautology screen. It does
NOT dispatch, run, or score a live trial (D5 of the item-22 brief) -- every trial here is a
constructed record, either a real graded output plumbed in by a future consumer or a fixture
built for `_paired_baseline_selftest.py`.

D2 -- the classification axis, and where it lives: every evals.json assertion already carries
`method: "deterministic" | "semantic"` (backlog item 16) -- HOW a criterion is graded. This
item adds a second, ORTHOGONAL axis -- `criterion_class: "outcome" | "skill_contract"` --
WHETHER a criterion can measure lift at all. It lives on the exact same assertion object,
inline, the same way `method` does: no canon/*.toml, because (like `method`) it is authoring
metadata about the eval suite's own design, not a vocabulary validated against candidate
output or shared machinery read by multiple unrelated scripts (contrast canon/trial-validity.toml,
whose thresholds are consumed by both this suite and, eventually, exec_replay_grade.py).
`criterion_class()` below is the reader; absence is `"unclassified"`, never a default to
either class (D6 -- see the module docstring note on the existing corpus, and
`evals/README.md`'s "Criterion classification" section for why the 165 assertions already in
evals.json are, today, all unclassified rather than retroactively guessed at).

D4 -- the seam with item 21: a manipulation-check failure (the with-skill arm never invoked
the skill, or the without-skill arm did) is graded as an ordinary counted, FAILING outcome
assertion (`score_manipulation_check()`) -- it never touches `canon/trial-validity.toml`'s
closed `invalid_reasons` enum, and `_trial_validity.mark_invalid()` raises ValueError if
something tries to spend a manipulation-shaped reason there (proven in the selftest). The only
thing that can make `compute_lift()` return None for a trial is an arm whose
`TrialValidity.status == "invalid"` -- an EXOGENOUS failure (item 21's vocabulary, consumed
directly here, never reinvented).

Cross-references: evals/README.md ("Trial validity" section, "Criterion classification" /
"Paired lift" / "Tautology screen" subsections), scripts/_trial_validity.py (TrialValidity,
mark_invalid, mark_valid -- imported, not reimplemented), scripts/grade_structural.py
(LAYER2_REQUIRED_FIELDS / LAYER3_REQUIRED_FIELDS / _smell_vocabulary / _normalize -- imported
for the D3 screen's vocabulary, not reimplemented), scripts/_paired_baseline_selftest.py.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields

from _canon import Canon
from _trial_validity import TrialValidity, mark_valid
from grade_structural import (
    LAYER2_REQUIRED_FIELDS,
    LAYER3_REQUIRED_FIELDS,
    _normalize,
    _smell_vocabulary,
)

# No sys.path handling here, by convention (see _trial_validity.py): this is a pure library
# module, imported after the caller has already put scripts/ on sys.path -- the selftest does
# this, matching the house pattern, rather than every importee re-inserting its own directory.

CRITERION_CLASSES = ("outcome", "skill_contract")

# Added by backlog item 19 (Gap 17's D4, docs/review-skill-deep-dive-2026-08-17.md:772 --
# scripts/_discriminating_power.py carries the full rationale). An always-pass case that
# encodes an absolute contract (a regression that must never fire, a schema that must always
# validate) is never pruned, but must be structurally unable to enter a lift computation -- not
# just declared out via a convention a caller could ignore. `compute_lift()` below is the ONE
# choke point every PairedTrial passes through to become a LiftResult, so the gate lives here,
# not in item 19's own module: putting it anywhere else would leave a path around it.
CASE_KINDS = ("lift_eligible", "contract")


def criterion_class(assertion: Mapping) -> str:
    """Read an evals.json-shaped assertion's `criterion_class` (D2).

    Absence is NOT a default to either class (D6) -- it reads as `"unclassified"`, mirroring
    `_trial_validity.historical_validity()`'s `"not_recorded"` rule for a record predating its
    own taxonomy. An unclassified criterion participates in neither the outcome score nor the
    skill_contract score (see `_score()`) until someone classifies it.
    """
    value = assertion.get("criterion_class")
    if value is None:
        return "unclassified"
    if value not in CRITERION_CLASSES:
        raise ValueError(
            f"{value!r} is not a criterion_class ({'|'.join(CRITERION_CLASSES)}): {assertion!r}"
        )
    return value


@dataclass(frozen=True)
class AssertionResult:
    """One graded criterion inside one arm of a paired trial."""

    text: str
    criterion_class: str  # "outcome" | "skill_contract" | "unclassified"
    passed: bool


@dataclass(frozen=True)
class ArmResult:
    """One arm (with_skill | without_skill) of one paired trial.

    `validity` is item 21's vocabulary, unchanged: `mark_valid()` unless the arm's non-outcome
    was exogenous (rate limit, auth failure, harness timeout, lost artifact). `manipulation_ok`
    is a SEPARATE field -- True iff this arm ran under its assigned skill condition (the
    with-skill arm invoked the skill; the without-skill arm did not). A manipulation failure
    never touches `validity` (D4): it stays `mark_valid()` and is instead graded through
    `score_manipulation_check()` below, as a counted failing assertion.
    """

    arm: str  # "with_skill" | "without_skill"
    validity: TrialValidity
    manipulation_ok: bool
    assertions: tuple[AssertionResult, ...]


@dataclass(frozen=True)
class PairedTrial:
    case_id: str
    with_arm: ArmResult
    without_arm: ArmResult
    # D4 of item 19: defaults to "lift_eligible" so every existing call site (this file's own
    # selftest included) is unaffected. Explicit "contract" is the only way to route a case out
    # of the lift computation, and compute_lift() below enforces it unconditionally.
    case_kind: str = "lift_eligible"

    def __post_init__(self) -> None:
        if self.case_kind not in CASE_KINDS:
            raise ValueError(
                f"{self.case_kind!r} is not a case_kind ({'|'.join(CASE_KINDS)}): "
                f"case {self.case_id!r}"
            )


def score_manipulation_check(arm: ArmResult) -> AssertionResult:
    """The manipulation check, graded as an ordinary outcome criterion (D4).

    Both arms can structurally satisfy "ran under its assigned condition" -- the with-skill
    arm by invoking the skill, the without-skill arm by not -- so it is legitimately classed
    `outcome`, not `skill_contract`. This is the deliberate divergence from skilllens named in
    the module docstring: skilllens VOIDS the trial on this failure; here it COUNTS, folded
    into the arm's outcome score like any other criterion.
    """
    return AssertionResult(
        text="arm ran under its assigned with-skill/without-skill condition",
        criterion_class="outcome",
        passed=arm.manipulation_ok,
    )


def _all_assertions(arm: ArmResult) -> tuple[AssertionResult, ...]:
    return (*arm.assertions, score_manipulation_check(arm))


def _score(assertions: Iterable[AssertionResult], cls: str) -> tuple[float | None, int]:
    """Fraction passed among assertions classed `cls`, and how many there were.

    Returns `(None, 0)` for an empty subset -- never `0.0`, which would read as "scored zero"
    rather than "nothing to score". `criterion_class == "unclassified"` assertions never enter
    this: they are filtered out by the `cls` equality check like any other non-matching class.
    """
    subset = [a for a in assertions if a.criterion_class == cls]
    if not subset:
        return None, 0
    return sum(1 for a in subset if a.passed) / len(subset), len(subset)


@dataclass(frozen=True)
class LiftResult:
    case_id: str
    with_outcome_score: float
    without_outcome_score: float
    delta: float  # SIGNED, never floored at zero (D1) -- with_outcome_score - without_outcome_score
    outcome_n: int
    with_skill_contract_score: float | None
    without_skill_contract_score: float | None
    skill_contract_n_with: int
    skill_contract_n_without: int


def compute_lift(trial: PairedTrial) -> LiftResult | None:
    """The paired-lift computation (D1/D2).

    Returns None when either arm's item-21 `TrialValidity` is invalid -- an exogenous failure
    produced no scoreable outcome on that arm, so there is nothing to compute a delta from
    (item 21's `scoreable_trials()` boundary, consumed directly rather than reimplemented).
    This is NOT the manipulation-check path: `manipulation_ok=False` never makes `validity`
    invalid (D4), so a manipulation failure always reaches the scoring below, counted.

    `delta` is signed and never floored -- a negative delta (the skill made the outcome score
    WORSE) is a real, reportable result, not clamped to zero (D1; Gap 17's
    fail-with-skill-but-pass-without category has no detector anywhere else in this suite).

    `skill_contract` scores are computed and returned, but never read by this function to
    produce `delta` -- they cannot enter the lift numerator or denominator (D2; proven
    differentially in the selftest).

    Also returns None when `trial.case_kind == "contract"` (item 19, D4) -- a THIRD, distinct
    reason from the two below: both arms may be perfectly valid, there is simply no lift claim
    an absolute-contract case is allowed to contribute to. The case itself is never dropped
    from the corpus; it is scored through a separate contract-suite path
    (scripts/_discriminating_power.py), never mixed into a lift numerator or denominator.
    """
    if trial.case_kind == "contract":
        return None
    if (
        trial.with_arm.validity.status == "invalid"
        or trial.without_arm.validity.status == "invalid"
    ):
        return None

    with_all = _all_assertions(trial.with_arm)
    without_all = _all_assertions(trial.without_arm)

    with_outcome, with_n = _score(with_all, "outcome")
    without_outcome, without_n = _score(without_all, "outcome")
    # score_manipulation_check() always contributes one outcome-classed assertion to every
    # arm, so with_n/without_n are never 0 here -- an all-unclassified trial still yields a
    # well-defined (if minimal) delta from the manipulation check alone.
    assert with_n and without_n, "outcome_n must be >=1: score_manipulation_check() guarantees it"

    with_sc, with_sc_n = _score(with_all, "skill_contract")
    without_sc, without_sc_n = _score(without_all, "skill_contract")

    return LiftResult(
        case_id=trial.case_id,
        with_outcome_score=with_outcome,
        without_outcome_score=without_outcome,
        delta=with_outcome - without_outcome,
        outcome_n=with_n,
        with_skill_contract_score=with_sc,
        without_skill_contract_score=without_sc,
        skill_contract_n_with=with_sc_n,
        skill_contract_n_without=without_sc_n,
    )


# ---- D3: the tautology screen ------------------------------------------------------------
#
# Flags any `outcome`-classed criterion whose text references skill-internal vocabulary. A
# purely lexical screen has false positives by design (Gap 20 itself: "legitimate where the
# name is the consumed artifact, invalid the moment a criterion rewards our vocabulary over
# the outcome" is a judgment a regex cannot make) -- so the screen FLAGS, a human DECLARES.
# House pattern for exactly this: DECLARED_DIVERGENCES (scripts/token-budget.py) and
# DECLARED_TRANSITION_DIVERGENCES (scripts/validate-repo.py). An undeclared flag fails; a
# declared one passes and stays visible in the findings list.

# (case_id, assertion_index): reason. Populated by the item-22 corpus-classification pass
# (evals/README.md "Criterion classification"): every evals.json assertion now carries
# criterion_class, and every resulting outcome-classed lexical hit below is adjudicated here
# rather than reclassified -- each one names a real severity/dimension/verdict judgment on a
# required output-contract field (or a coincidental generic-English collision), never a
# criterion whose ONLY substance is reproducing our own coined vocabulary (those -- the
# flagged_smells exact-canon-name checks -- were reclassified to skill_contract instead, the
# other exit D3 names).
DECLARED_TAUTOLOGY_EXCEPTIONS: dict[tuple[str, int], str] = {
    ("suppression-flag", 1): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token; thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("suppression-flag", 2): (
        "evidence_demanded is a required field name; the evidence-sufficiency judgment is generic review diligence, not our vocabulary"
    ),
    ("suppression-flag", 3): (
        "coincidental collision with a canon fix-kind token; here it names the real Swift `Sendable` protocol under review in this scenario's source, not our taxonomy"
    ),
    ("suppression-flag", 5): (
        "verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("crossplat-flag", 2): (
        "evidence_demanded is a required field name; the evidence-sufficiency judgment is generic review diligence, not our vocabulary"
    ),
    ("suppression-restraint", 1): (
        "verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours; coincidental collision with a canon fix-kind token; here it names the real Swift `Sendable` protocol under review in this scenario's source, not our taxonomy"
    ),
    ("suppression-restraint", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field; coincidental collision with a canon fix-kind token; here it names the real Swift `Sendable` protocol under review in this scenario's source, not our taxonomy"
    ),
    ("crossplat-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("crossplat-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("identity-flag", 1): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("identity-flag", 3): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("identity-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("identity-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("ownership-flag", 0): (
        "coincidental collision with an unrelated canon workflow-state token; ordinary English"
    ),
    ("ownership-flag", 1): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("ownership-flag", 3): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("ownership-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("ownership-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("style-suppression-restraint", 1): (
        "names the smell category descriptively for the grading judge's benefit in a restraint check whose behavioral bar is avoiding a false-positive finding -- not a token the candidate must reproduce"
    ),
    ("style-suppression-restraint", 2): (
        "verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("style-suppression-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("halt-challenge-flag", 0): (
        "HALT_SUCCESS is this scenario's own subject matter (the case prompt itself frames the task as challenging a HALT_SUCCESS claim), not a smell/review-vocabulary reward; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("halt-challenge-flag", 1): (
        "flagged_smells referenced generically as the field the finding belongs in, not a specific canon smell token"
    ),
    ("halt-challenge-flag", 2): (
        "names the smell category descriptively for the grading judge's benefit in a restraint check whose behavioral bar is avoiding a false-positive finding -- not a token the candidate must reproduce"
    ),
    ("halt-challenge-restraint", 0): (
        "verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("strictness-aggressive-flag", 1): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token; thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("strictness-aggressive-flag", 2): (
        "evidence_demanded is a required field name; the evidence-sufficiency judgment is generic review diligence, not our vocabulary"
    ),
    ("strictness-aggressive-restraint", 0): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name"
    ),
    ("strictness-aggressive-restraint", 3): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("principal-invariant-owner-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("principal-invariant-owner-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("principal-invariant-owner-restraint", 1): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("principal-invariant-owner-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("principal-duplicated-rule-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("principal-duplicated-rule-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("principal-duplicated-rule-restraint", 1): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("principal-duplicated-rule-restraint", 2): (
        "verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("principal-process-owner-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("principal-process-owner-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("principal-process-owner-restraint", 1): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("principal-process-owner-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("principal-consistency-boundary-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field; generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name"
    ),
    ("principal-abstraction-seam-flag", 1): (
        "coincidental collision with an unrelated canon finding-status token; ordinary English"
    ),
    ("principal-abstraction-seam-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("reentrancy-reserve-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("reentrancy-reserve-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("reentrancy-reserve-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("reentrancy-reserve-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("write-only-state-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("write-only-state-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("write-only-state-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours; names the smell category descriptively for the grading judge's benefit in a restraint check whose behavioral bar is avoiding a false-positive finding -- not a token the candidate must reproduce"
    ),
    ("write-only-state-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("projection-order-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("projection-order-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("projection-order-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("projection-order-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("view-owned-time-flag", 3): (
        "flagged_smells referenced generically as the field the finding belongs in, not a specific canon smell token"
    ),
    ("view-owned-time-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("stable-workflow-identity-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("stable-workflow-identity-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("stable-workflow-identity-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("stable-workflow-identity-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("causal-runtime-context-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("causal-runtime-context-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("causal-runtime-context-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("causal-runtime-context-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("adapter-output-contract-flag", 2): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
    ("adapter-output-contract-flag", 4): (
        "blocks_95 is a required contract field naming whether a finding blocks the touched dimension's 9.5 bar, not a smell vocabulary token"
    ),
    ("adapter-output-contract-restraint", 2): (
        "generic English 'reason(s)' coincidentally matches the Layer-3 `reason` field name; verdict's 3-value enum is spelled out verbatim in every case's own prompt (\"approved|rejected|conditional\"); ordinary review vocabulary, not ours"
    ),
    ("adapter-output-contract-restraint", 3): (
        "thresholds a real scorecard dimension's severity (Gap 20's own worked ambiguous example, docs/review-skill-deep-dive-2026-08-17.md:843) -- the judgment is generalizable, the dimension key is the contract's own field"
    ),
}


@dataclass(frozen=True)
class TautologyFinding:
    case_id: str
    assertion_index: int
    text: str
    hits: tuple[str, ...]
    declared: bool
    reason: str | None


def _skill_vocabulary(canon: Canon) -> frozenset[str]:
    """Every closed vocabulary token our own artifacts define: the two JSON contracts'
    required field names (grade_structural.py, imported), the smell names
    (grade_structural._smell_vocabulary(), imported), every canon gate id, and every
    tuple[str, ...] enum canon.py loads -- walked via dataclasses.fields() rather than
    hand-listing canon's ~15 enum field names, so a new canon/*.toml enum is covered
    automatically instead of silently falling outside the screen.
    """
    tokens: set[str] = set()
    tokens.update(LAYER2_REQUIRED_FIELDS)
    tokens.update(LAYER3_REQUIRED_FIELDS)
    tokens.update(_smell_vocabulary())
    tokens.update(canon.validation_gates.keys())
    for f in fields(Canon):
        value = getattr(canon, f.name)
        if isinstance(value, tuple) and value and isinstance(value[0], str):
            tokens.update(value)
    return frozenset(_normalize(t) for t in tokens if t)


def screen_criteria(cases: Iterable[Mapping], canon: Canon) -> list[TautologyFinding]:
    """Run the D3 screen over evals.json-shaped case records (each with an `assertions[]`
    list). Every `outcome`-classed assertion whose normalized text contains a skill-vocabulary
    token is reported -- declared exceptions included, so the findings list stays a complete,
    auditable record even where nothing failed.
    """
    vocab = _skill_vocabulary(canon)
    findings: list[TautologyFinding] = []
    for case in cases:
        case_id = str(case.get("name") or case.get("id"))
        for idx, assertion in enumerate(case.get("assertions", [])):
            if criterion_class(assertion) != "outcome":
                continue
            text = str(assertion.get("text", ""))
            normalized = _normalize(text)
            hits = tuple(sorted(tok for tok in vocab if tok and tok in normalized))
            if not hits:
                continue
            reason = DECLARED_TAUTOLOGY_EXCEPTIONS.get((case_id, idx))
            findings.append(TautologyFinding(case_id, idx, text, hits, reason is not None, reason))
    return findings


def undeclared_tautology_failures(findings: Iterable[TautologyFinding]) -> list[TautologyFinding]:
    """The subset of screen_criteria()'s findings that fail the check -- flagged and not
    declared. A non-empty result here is what a CI/selftest gate should fail on; a declared
    finding is reported but never blocks."""
    return [f for f in findings if not f.declared]


__all__ = [
    "CASE_KINDS",
    "CRITERION_CLASSES",
    "DECLARED_TAUTOLOGY_EXCEPTIONS",
    "ArmResult",
    "AssertionResult",
    "LiftResult",
    "PairedTrial",
    "TautologyFinding",
    "compute_lift",
    "criterion_class",
    "mark_valid",
    "score_manipulation_check",
    "screen_criteria",
    "undeclared_tautology_failures",
]
