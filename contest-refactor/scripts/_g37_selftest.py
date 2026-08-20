#!/usr/bin/env python3
"""Self-test for G37 — no terminal scorecard may strand a sub-9.5 dimension.

G37 mechanizes the Residual Accounting Pass (method-critic.md) / G23 at HALT. Every
dimension below 9.5 at a terminal must be accounted for by exactly one of:
  (a) a backlog[] item whose score_impact names it, or
  (c) residual_blocker_kind == "structural_anchor_unmet".
Account (b) -- residual_disposition == "accepted" -- is NOT accepted here: an "accepted"
disposition below 9.5 is itself the violation, owned by G5's converse.

The trigger was widened from a closed set (HALT_STAGNATION/no_backlog, or HALT_LOOP_CAP
with an empty backlog) to every HALT_LOOP_CAP / HALT_STAGNATION, any subtype, any backlog.
The old set assumed a non-empty backlog explains the sub-9.5 gaps -- true only for the
dimensions the backlog actually names. REGRESSION_CASE below is the production artifact
that exposed it: a cap terminal whose two backlog items named other dimensions while
data_flow sat at 7.5 with every residual field null. It validated clean.

This test pins four things against the REAL gate function in validate-artifact.py:

  1. TRIGGER  -- fires on every terminal with an unaccounted sub-9.5 dimension.
  2. BYPASS   -- silent when either account is present, and on the non-terminal states
                (CONTINUE, HALT_DRY_RUN) and the success states G21 already owns.
  3. REGRESSION -- the production shape, pinned by identity so a future narrowing of the
                trigger cannot quietly restore it.
  4. ISOLATION -- a residual_blocker_kind value never changes an unrelated gate's verdict
                (check_g21_scorecard / check_halt_success_gating).

No pytest in this repo -> standalone _*.py helper.

Run: python3 scripts/_g37_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import sys

from _selftest_lib import load_validator as _load_validator

FW = "framework_constrained"
STRUCT = "structural_anchor_unmet"


def _dim(score, blocker_kind=None, disposition=None):
    return {
        "score": score,
        "residual_disposition": disposition,
        "residual_blocker_kind": blocker_kind,
    }


def _art(state, scorecard, halt_subtype=None, backlog=None, schema_version=4):
    return {
        "schema_version": schema_version,
        "state": state,
        "halt_subtype": halt_subtype,
        "backlog": backlog if backlog is not None else [],
        "scorecard": scorecard,
    }


# The production artifact, reduced to the shape that matters. HALT_LOOP_CAP with a NON-empty
# backlog naming architecture_quality and concurrency; data_flow stranded at 7.5.
REGRESSION_CASE = _art(
    "HALT_LOOP_CAP",
    {
        "architecture_quality": _dim(9.0),
        "data_flow": _dim(7.5),
        "test_strategy": _dim(8.5, None, "accepted"),
        "simplicity": _dim(10.0),
    },
    backlog=[
        {"stable_id": "F-022", "score_impact": "architecture_quality +0.5"},
        {"stable_id": "F-011", "score_impact": "concurrency +0.5"},
    ],
)


def _cases():
    """(label, artifact, expect_fire)"""
    cases = []

    # --- TRIGGER: an unaccounted sub-9.5 dimension at any terminal ---
    cases.append(
        (
            "cap empty-backlog, sub-9.5 promotion-trigger kind",
            _art("HALT_LOOP_CAP", {"framework_idioms": _dim(7.0, FW)}),
            True,
        )
    )
    cases.append(
        (
            "cap empty-backlog, sub-9.5 MISSING kind",
            _art("HALT_LOOP_CAP", {"domain_modeling": _dim(6.5, None)}),
            True,
        )
    )
    cases.append(
        (
            "no_backlog, sub-9.5 promotion-trigger kind",
            _art(
                "HALT_STAGNATION",
                {"domain_modeling": _dim(6.5, "ceremony")},
                halt_subtype="no_backlog",
            ),
            True,
        )
    )
    # --- The five rows the widening flipped from BYPASS to TRIGGER. ---
    cases.append(
        (
            "WIDENED: cap NON-empty backlog that does not name the stranded dim",
            _art(
                "HALT_LOOP_CAP",
                {"framework_idioms": _dim(7.0)},
                backlog=[{"stable_id": "F-001", "score_impact": "simplicity +0.5"}],
            ),
            True,
        )
    )
    cases.append(
        (
            "WIDENED: cap NON-empty backlog item carrying NO score_impact at all",
            _art("HALT_LOOP_CAP", {"framework_idioms": _dim(7.0)}, backlog=[{"id": "F1"}]),
            True,
        )
    )
    for st in ("user_decision", "oscillation", "no_progress", "verification_blocked"):
        cases.append(
            (
                f"WIDENED: HALT_STAGNATION/{st} with an unaccounted sub-9.5 dim",
                _art("HALT_STAGNATION", {"framework_idioms": _dim(7.0, FW)}, halt_subtype=st),
                True,
            )
        )

    # --- BYPASS: account (c), a named structural ceiling ---
    cases.append(
        (
            "cap empty-backlog, sub-9.5 structural_anchor_unmet (honest)",
            _art(
                "HALT_LOOP_CAP",
                {
                    "domain_modeling": _dim(6.5, STRUCT),
                    "framework_idioms": _dim(9.5, None, "accepted"),
                },
            ),
            False,
        )
    )
    for st in ("user_decision", "oscillation", "no_progress", "verification_blocked"):
        cases.append(
            (
                f"HALT_STAGNATION/{st} with structural_anchor_unmet (honest)",
                _art("HALT_STAGNATION", {"framework_idioms": _dim(7.0, STRUCT)}, halt_subtype=st),
                False,
            )
        )

    # --- BYPASS: account (a), the backlog names the dimension ---
    cases.append(
        (
            "cap, backlog score_impact names the sub-9.5 dim",
            _art(
                "HALT_LOOP_CAP",
                {"framework_idioms": _dim(7.0)},
                backlog=[{"stable_id": "F-001", "score_impact": "framework_idioms +0.5"}],
            ),
            False,
        )
    )
    cases.append(
        (
            "cap, dim named in a multi-entry ';'-joined score_impact",
            _art(
                "HALT_LOOP_CAP",
                {"framework_idioms": _dim(7.0)},
                backlog=[{"score_impact": "simplicity +0.5; framework_idioms +1.0"}],
            ),
            False,
        )
    )
    cases.append(
        (
            "cap, permissive attribution tolerates a G39-malformed score_impact",
            # `data_flow +0.5 once verified` is a G39 shape failure; G39 owns that. G37 must
            # still attribute it so only one gate speaks about the same defect.
            _art(
                "HALT_LOOP_CAP",
                {"data_flow": _dim(7.5)},
                backlog=[{"score_impact": "data_flow +0.5 once verified"}],
            ),
            False,
        )
    )

    # --- BYPASS: nothing sub-9.5 to strand ---
    cases.append(
        (
            "cap, all dims >= 9.5",
            _art("HALT_LOOP_CAP", {"architecture_quality": _dim(9.5, None, "accepted")}),
            False,
        )
    )

    # --- BYPASS: non-terminals and the states G21 already owns ---
    cases.append(("HALT_SUCCESS", _art("HALT_SUCCESS", {"framework_idioms": _dim(7.0, FW)}), False))
    cases.append(
        (
            "HALT_SUCCESS_candidate",
            _art("HALT_SUCCESS_candidate", {"framework_idioms": _dim(7.0, FW)}),
            False,
        )
    )
    cases.append(("HALT_DRY_RUN", _art("HALT_DRY_RUN", {"framework_idioms": _dim(7.0, FW)}), False))
    cases.append(
        (
            "CONTINUE",
            _art("CONTINUE", {"framework_idioms": _dim(7.0, FW)}, backlog=[{"id": "F1"}]),
            False,
        )
    )

    # --- BYPASS: version floor — field is additive on v4; pre-v4 never fires ---
    cases.append(
        (
            "schema_version 3, cap incoherent (pre-field, must NOT fire)",
            _art("HALT_LOOP_CAP", {"framework_idioms": _dim(7.0, FW)}, schema_version=3),
            False,
        )
    )

    return cases


def _isolation(va) -> list[str]:
    """A residual_blocker_kind value must never change check_g21_scorecard /
    check_halt_success_gating -- those gates read score + residual_disposition only."""
    failures: list[str] = []

    def art(kind):
        return {
            "state": "HALT_SUCCESS",
            "scorecard": {
                "architecture_quality": {
                    "score": 9.5,
                    "residual_disposition": "accepted",
                    "residual_blocker_kind": kind,
                }
            },
            "findings": [],
        }

    def verdict(a):
        issues = va.check_g21_scorecard(a) + va.check_halt_success_gating(a, None)
        return sorted(f"{i.rule}: {i.message}" for i in issues)

    baseline = verdict(art(None))
    for kind in (STRUCT, FW, "ceremony", "cosmetic"):
        v = verdict(art(kind))
        if v != baseline:
            failures.append(
                f"residual_blocker_kind={kind!r} changed an unrelated gate verdict\n"
                f"  baseline: {baseline}\n  {kind}: {v}"
            )
    return failures


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    for label, art, expect_fire in _cases():
        issues = va.check_g37_terminal_residual_accounting(copy.deepcopy(art))
        fired = bool(issues)
        if fired != expect_fire:
            failures.append(
                f"{label}: expected {'FIRE' if expect_fire else 'BYPASS'}, "
                f"got {'FIRE' if fired else 'BYPASS'}"
                + (f"\n  {issues[0].message}" if issues else "")
            )

    # REGRESSION: the production artifact, pinned by the identity of what fires.
    reg = va.check_g37_terminal_residual_accounting(copy.deepcopy(REGRESSION_CASE))
    stranded = sorted(
        m.split("dimension ")[1].split(" ")[0].strip("'") for m in (i.message for i in reg)
    )
    # data_flow (nothing names it) and test_strategy (8.5 "accepted" is G5's violation, not an
    # account here). architecture_quality is backlog-named; simplicity is 10.
    if stranded != ["data_flow", "test_strategy"]:
        failures.append(
            f"REGRESSION_CASE: expected data_flow + test_strategy stranded, got {stranded}"
        )

    failures.extend(_isolation(va))

    if not any(e for _, _, e in _cases()):
        failures.append("vacuous: no TRIGGER case present")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    n = len(_cases())
    print(
        f"OK: G37 accounts every sub-9.5 dimension across {n} terminal cases "
        f"(backlog attribution + structural_anchor_unmet); production regression pinned; "
        f"residual_blocker_kind isolated from G21 / halt_success_gating"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
