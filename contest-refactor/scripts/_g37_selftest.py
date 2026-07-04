#!/usr/bin/env python3
"""Self-test for G37 — residual-blocker-kind coherence at converged empty-backlog terminals.

G37 mechanizes the Residual Accounting Pass (method-critic.md) / G23 at HALT: at a converged
empty-backlog terminal a sub-9.5 dimension may keep its score ONLY with
residual_blocker_kind == "structural_anchor_unmet"; a promotion-trigger kind (or a missing kind)
is the incoherence. This test pins three things against the REAL gate function in
validate-artifact.py:

  1. TRIGGER  — G37 fires on { HALT_STAGNATION/no_backlog, HALT_LOOP_CAP+empty-backlog+sub-9.5 }.
  2. BYPASS   — G37 stays silent on every OTHER terminal (the closed-set guarantee): the other
                HALT_STAGNATION subtypes, HALT_SUCCESS(_candidate), HALT_DRY_RUN, CONTINUE, and
                HALT_LOOP_CAP with a NON-empty backlog. A regression that broadened the predicate
                would flip one of these.
  3. ISOLATION — a residual_blocker_kind value never changes an unrelated gate's verdict
                (check_g21_scorecard / check_halt_success_gating), mirroring
                _metric_isolation_selftest.py.

No pytest in this repo -> standalone _*.py helper.

Run: python3 scripts/_g37_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_g37", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


# (label, artifact, expect_fire)
def _cases():
    FW = "framework_constrained"
    STRUCT = "structural_anchor_unmet"
    cases = []

    # --- TRIGGER: G37 must fire ---
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
    cases.append(
        (
            "no_backlog, sub-9.5 MISSING kind",
            _art(
                "HALT_STAGNATION", {"state_management": _dim(7.5, None)}, halt_subtype="no_backlog"
            ),
            True,
        )
    )

    # --- BYPASS: honest resolution at a trigger terminal ---
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
    cases.append(
        (
            "no_backlog, sub-9.5 structural_anchor_unmet (honest)",
            _art(
                "HALT_STAGNATION", {"domain_modeling": _dim(6.5, STRUCT)}, halt_subtype="no_backlog"
            ),
            False,
        )
    )
    cases.append(
        (
            "cap empty-backlog, all dims >= 9.5 (no sub-9.5 -> not our case)",
            _art("HALT_LOOP_CAP", {"architecture_quality": _dim(9.5, None, "accepted")}),
            False,
        )
    )

    # --- BYPASS: the closed-set guarantee — every OTHER terminal, even with an incoherent dim ---
    cases.append(
        (
            "cap NON-empty backlog (queued items legitimate)",
            _art("HALT_LOOP_CAP", {"framework_idioms": _dim(7.0, FW)}, backlog=[{"id": "F1"}]),
            False,
        )
    )
    for st in ("user_decision", "oscillation", "no_progress", "verification_blocked"):
        cases.append(
            (
                f"HALT_STAGNATION/{st} (not a residual-accounting terminal)",
                _art("HALT_STAGNATION", {"framework_idioms": _dim(7.0, FW)}, halt_subtype=st),
                False,
            )
        )
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

    # --- BYPASS: version gate — field is additive on v4; pre-v4 never fires ---
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
    check_halt_success_gating — those gates read score + residual_disposition only."""
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
    for kind in ("structural_anchor_unmet", "framework_constrained", "ceremony", "cosmetic"):
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
        issues = va.check_g37_residual_blocker_coherence(copy.deepcopy(art))
        fired = bool(issues)
        if fired != expect_fire:
            failures.append(
                f"{label}: expected {'FIRE' if expect_fire else 'BYPASS'}, "
                f"got {'FIRE' if fired else 'BYPASS'}"
                + (f"\n  {issues[0].message}" if issues else "")
            )

    failures.extend(_isolation(va))

    # Sanity: the matrix isn't vacuous — at least one fire and one bypass exercised.
    if not any(e for _, _, e in _cases()):
        failures.append("vacuous: no TRIGGER case present")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    n = len(_cases())
    print(
        f"OK: G37 closed-set predicate holds across {n} state/subtype cases; "
        f"residual_blocker_kind is isolated from G21 / halt_success_gating"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
