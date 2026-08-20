#!/usr/bin/env python3
"""Self-test for G43 -- convergence-pass coverage; a repeated clean must propose anew.

Two passes re-test a stalled dimension each loop: the Stalled-Dimension Sweep (sub-9.5,
delta SAME for 3+ loops) and the Adversarial Pass on Accepted Residuals (9.5-accepted,
every loop). Both were prose obligations with no gate. Across 55 production loops their
outcomes tracked their contracts exactly -- the Adversarial Pass demands a newly proposed
smallest fix plus the SPT question that rejected it and produced three structurally
distinct candidates; the Sweep permits "a named candidate OR an explicit clean" and
decayed to a bare "explicit clean." while the same file stayed the named blocker for 40 of
40 loops with no movement.

Both runs that had the Sweep were fully COMPLIANT with it. That is why this gate keys on
repetition, not presence -- and why REWORDED_NOTE below is the load-bearing case: an
earlier design of this gate hashed the free-form proposal text, which a production finding
("Free-form residual wording defeats candidate recurrence") had already shown to be
defeatable by rewording. Novelty is judged on (fix_kind, target_path, target_symbol).

Run: python3 scripts/_g43_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import sys

import _canon
from _selftest_lib import load_validator as _load_validator

CANON = _canon.load_canon()


def _dim(score, delta="SAME", disposition=None):
    return {"score": score, "delta": delta, "residual_disposition": disposition}


def _fix(kind="extract", path="src/Widget.cs", symbol="PopulatePanelAsync", note="prose"):
    return {"fix_kind": kind, "target_path": path, "target_symbol": symbol, "note": note}


def _clean(dim, fix=None, rationale="needs the view model split first", pass_name="stalled_sweep"):
    record = {
        "dimension": dim,
        "pass": pass_name,
        "outcome": "clean",
        "surface_walked": "Widget.cs (2092 lines) + Services/ (11 files)",
        "finding_stable_id": None,
        "clean_rationale": rationale,
    }
    if fix is not None:
        record["proposed_fix"] = fix
        record["spt_question_failed"] = "Q5"
    return record


def _candidate(dim, stable_id="F-014"):
    return {
        "dimension": dim,
        "pass": "stalled_sweep",
        "outcome": "candidate",
        "surface_walked": "Widget.cs",
        "finding_stable_id": stable_id,
        "clean_rationale": None,
    }


def _art(
    loop=6,
    state="CONTINUE",
    scorecard=None,
    records=None,
    backlog=None,
    findings=None,
    schema_version=4,
):
    return {
        "schema_version": schema_version,
        "skill_rev": "9346822",
        "loop": loop,
        "state": state,
        "scorecard": scorecard if scorecard is not None else {"architecture_quality": _dim(7.5)},
        "convergence_pass": records if records is not None else [],
        "backlog": backlog if backlog is not None else [],
        "findings": findings if findings is not None else [],
    }


def _history(loops):
    return {"loops": loops}


def _prior(loop, scorecard=None, records=None):
    return {
        "loop": loop,
        "scorecard": scorecard if scorecard is not None else {"architecture_quality": _dim(7.5)},
        "convergence_pass": records if records is not None else [],
    }


# Two prior loops whose architecture_quality was a clean, so the current loop is the third.
def _streak_history(prior_fix=None):
    return _history(
        [
            _prior(4, records=[_clean("architecture_quality", fix=prior_fix)]),
            _prior(5, records=[_clean("architecture_quality", fix=prior_fix)]),
        ]
    )


# THE load-bearing regression: same target tuple, freshly reworded prose.
REWORDED_NOTE = (
    _art(
        records=[_clean("architecture_quality", fix=_fix(note="a completely different sentence"))]
    ),
    _streak_history(prior_fix=_fix(note="the original sentence")),
    True,
)


def _cases():
    """(label, artifact, history, expect_fire)"""
    two_priors = _history([_prior(4), _prior(5)])
    cases = [
        # --- TRIGGER ---
        (
            "3-loop clean streak with NO proposed_fix (the production shape)",
            _art(records=[_clean("architecture_quality")]),
            _streak_history(),
            True,
        ),
        ("reworded note over an unchanged target tuple", *REWORDED_NOTE[:2], REWORDED_NOTE[2]),
        (
            "stalled sub-9.5 dimension with no convergence_pass record at all",
            _art(records=[]),
            two_priors,
            True,
        ),
        (
            "9.5-accepted dimension with no record (a silently skipped Adversarial Pass)",
            _art(
                scorecard={"domain_modeling": _dim(9.5, disposition="accepted")},
                records=[],
            ),
            _history([_prior(4), _prior(5)]),
            True,
        ),
        (
            "streak proposal present but no spt_question_failed",
            _art(
                records=[
                    {
                        **_clean("architecture_quality", fix=_fix(symbol="OtherMethod")),
                        "spt_question_failed": None,
                    }
                ]
            ),
            _streak_history(prior_fix=_fix()),
            True,
        ),
        # --- BYPASS ---
        (
            "streak of 2 -- an honest ceiling may answer clean twice before owing a target",
            _art(records=[_clean("architecture_quality")]),
            _history([_prior(4), _prior(5, records=[])]),
            False,
        ),
        (
            "genuinely different target tuple on the streak",
            _art(records=[_clean("architecture_quality", fix=_fix(symbol="DifferentMethod"))]),
            _streak_history(prior_fix=_fix(symbol="OriginalMethod")),
            False,
        ),
        (
            "candidate whose finding_stable_id resolves in findings[]",
            _art(
                records=[_candidate("architecture_quality")],
                findings=[{"stable_id": "F-014"}],
            ),
            _streak_history(),
            False,
        ),
        (
            "dimension named by a backlog item's score_impact (it was filed)",
            _art(
                records=[],
                backlog=[{"stable_id": "F-022", "score_impact": "architecture_quality +0.5"}],
            ),
            two_priors,
            False,
        ),
        (
            "an UP inside the 3-loop window breaks the stall",
            _art(scorecard={"architecture_quality": _dim(7.5, delta="UP")}, records=[]),
            two_priors,
            False,
        ),
        (
            "loop 3 is below the floor (loop 1's SAME is definitional)",
            _art(loop=3, records=[]),
            _history([_prior(1), _prior(2)]),
            False,
        ),
        (
            "schema_version 3 is below the floor",
            _art(records=[], schema_version=3),
            two_priors,
            False,
        ),
        (
            "only one prior loop -- too little history to judge a stall",
            _art(records=[]),
            _history([_prior(5)]),
            False,
        ),
        ("no history at all", _art(records=[]), None, False),
        (
            "HALT_SUCCESS is G21's territory",
            _art(state="HALT_SUCCESS", records=[]),
            two_priors,
            False,
        ),
        (
            "HALT_DRY_RUN halts before the evidence exists",
            _art(state="HALT_DRY_RUN", records=[]),
            two_priors,
            False,
        ),
        (
            "9.5 WITHOUT an accepted disposition owes no adversarial pass",
            _art(scorecard={"domain_modeling": _dim(9.5)}, records=[]),
            two_priors,
            False,
        ),
        # --- SHAPE (checked independently of whether the dimension was owed a record) ---
        (
            "candidate whose finding_stable_id is absent from findings[]",
            _art(records=[_candidate("architecture_quality", stable_id="F-999")], findings=[]),
            two_priors,
            True,
        ),
        (
            "clean with an empty clean_rationale ('nothing found' is fake-clean)",
            _art(records=[_clean("architecture_quality", rationale="   ")]),
            two_priors,
            True,
        ),
        (
            "record with an empty surface_walked",
            _art(records=[{**_clean("architecture_quality"), "surface_walked": ""}]),
            two_priors,
            True,
        ),
        (
            "record naming a dimension not in this scorecard",
            _art(records=[_clean("not_a_dimension")]),
            two_priors,
            True,
        ),
        (
            "unknown outcome",
            _art(records=[{**_clean("architecture_quality"), "outcome": "maybe"}]),
            two_priors,
            True,
        ),
        (
            "unknown pass name",
            _art(records=[{**_clean("architecture_quality"), "pass": "vibes"}]),
            two_priors,
            True,
        ),
        (
            "fix_kind outside canon/fix-kinds.toml",
            _art(records=[_clean("architecture_quality", fix=_fix(kind="refactor"))]),
            _streak_history(prior_fix=_fix(symbol="Other")),
            True,
        ),
    ]
    return cases


def _isolation(va) -> list[str]:
    """convergence_pass[] must never perturb G37 / G39 / G42."""
    failures: list[str] = []
    base = {
        "schema_version": 4,
        "loop": 6,
        "state": "HALT_LOOP_CAP",
        "halt_subtype": None,
        "backlog": [{"stable_id": "F-001", "score_impact": "data_flow +0.5"}],
        "scorecard": {"data_flow": _dim(7.5), "simplicity": _dim(8.0)},
        "findings": [],
    }

    def verdict(art):
        return sorted(
            f"{i.rule}: {i.message}"
            for i in (
                va.check_g37_terminal_residual_accounting(art)
                + va.check_g39_backlog_score_impact(art, CANON)
                + va.check_g42_backlog_stable_id(art)
            )
        )

    without = verdict(copy.deepcopy(base))
    with_records = copy.deepcopy(base)
    with_records["convergence_pass"] = [_clean("simplicity", fix=_fix())]
    if verdict(with_records) != without:
        failures.append(
            "convergence_pass[] changed a G37/G39/G42 verdict; the gates must be disjoint"
        )
    return failures


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    for label, art, history, expect_fire in _cases():
        issues = va.check_g43_convergence_pass(copy.deepcopy(art), copy.deepcopy(history), CANON)
        fired = bool(issues)
        if fired != expect_fire:
            failures.append(
                f"{label}: expected {'FIRE' if expect_fire else 'BYPASS'}, "
                f"got {'FIRE' if fired else 'BYPASS'}"
                + (f"\n  {issues[0].message}" if issues else "")
            )

    # The reworded-note regression must fire for the RIGHT reason, not incidentally.
    art, history, _ = REWORDED_NOTE
    messages = " ".join(
        i.message
        for i in va.check_g43_convergence_pass(copy.deepcopy(art), copy.deepcopy(history), CANON)
    )
    if "SAME proposed_fix target" not in messages:
        failures.append(
            "reworded-note case fired, but not on target-tuple repetition -- the F-007 lesson is "
            f"not what caught it. Messages: {messages}"
        )

    failures.extend(_isolation(va))

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: G43 holds across {len(_cases())} cases -- a repeated clean owes a NEW "
        f"(fix_kind, target_path, target_symbol), rewording does not satisfy it, records are "
        f"shape-checked, and convergence_pass[] stays disjoint from G37/G39/G42"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
