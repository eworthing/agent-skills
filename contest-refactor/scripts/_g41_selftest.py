#!/usr/bin/env python3
"""Self-test for G41 — the cap loop executes its budgeted work. (Why: validation.md.)

Pinned against the REAL gate function in validate-artifact.py. The gate is a chain of
exemptions ending in one failure, so the table walks each exemption plus the failure:

  1. TRIGGER    — fires when state is HALT_LOOP_CAP, loop == loop_cap, the backlog is
                  non-empty, and loop_result is missing/null/empty.
  2. REGRESSION — the exact production shape (loop 10 of cap 10, three backlog items,
                  no loop_result) fires. That artifact passes strict validation with
                  zero issues today, which is the whole reason this gate exists, so it
                  is pinned by identity (REGRESSION_CASE) and guarded against deletion.
  3. BYPASS     — silent on each legitimate no-work terminal: loop > loop_cap (Step-1
                  emit), an empty backlog (Steps 2-3 skipped; that terminal is G37's),
                  loop < loop_cap (deliberately unpoliced — 13 v1-v3 fixtures carry
                  loop=1/cap=10 while testing unrelated things), non-cap states, the
                  schema_version 4 floor, missing/non-int loop or loop_cap, and — the
                  semantic case worth stating — a reviewer-REJECTED cap loop, which
                  did its work and had it declined and so still writes a loop_result.
  4. ISOLATION  — loop_result / loop_cap values never change an unrelated gate's verdict.
  5. VACUITY    — a gate that silently stopped firing cannot pass by doing nothing.

No pytest in this repo -> standalone _*.py helper.

Run: python3 scripts/_g41_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _canon import load_canon


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_g41", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DIMS = tuple(load_canon(HERE.parent).scorecard_dimensions)

# A loop_result from a loop that ran Steps 2-3 and had the reviewer approve.
EXECUTED = {
    "what_changed": "collapsed the duplicated panel animation into a shared helper",
    "targeted_finding_status": "resolved",
    "changed_paths": ["src/Widget.cs"],
}
# A loop that ran Steps 2-3 and had the reviewer REJECT: the narrow-revert path still
# writes a loop_result. Doing the work and having it declined is not skipping the work.
REJECTED = {
    "what_changed": "attempt reverted after implementation review",
    "targeted_finding_status": "carried_forward",
    "unintended_regression": "reviewer rejected: seam not justified",
}


def _backlog(n=1):
    return [
        {
            "priority": i + 1,
            "title": f"item {i + 1}",
            "kind": "structural",
            "why_it_matters": "w",
            "score_impact": "data_flow +0.5",
        }
        for i in range(n)
    ]


def _art(
    *, loop=10, cap=10, state="HALT_LOOP_CAP", backlog=None, loop_result=..., schema_version=4
):
    art = {
        "schema_version": schema_version,
        "state": state,
        "loop": loop,
        "loop_cap": cap,
        "backlog": _backlog() if backlog is None else backlog,
        "scorecard": {d: {"score": 7.0} for d in DIMS},
        "unresolved_reason": "loop counter reached cap",
    }
    if loop_result is not ...:
        art["loop_result"] = loop_result
    return art


# The shape the production run emitted: cap loop, real backlog, no execution.
REGRESSION_CASE = (
    "REGRESSION: cap loop ran Critic-only with a 3-item backlog",
    _art(loop=10, cap=10, backlog=_backlog(3)),
    True,
)


# (label, artifact, expect_fire)
def _cases():
    return [
        # --- TRIGGER: every way "no loop_result" can be spelled ---
        REGRESSION_CASE,
        ("loop_result absent", _art(), True),
        ("loop_result null", _art(loop_result=None), True),
        ("loop_result empty dict", _art(loop_result={}), True),
        ("cap of 1 — the smallest run", _art(loop=1, cap=1), True),
        # --- BYPASS: the loop did its work ---
        ("loop_result present (approved)", _art(loop_result=EXECUTED), False),
        ("loop_result present (reviewer REJECTED)", _art(loop_result=REJECTED), False),
        # --- BYPASS: legitimate no-work terminals ---
        ("empty backlog — converged terminal, G37's case", _art(backlog=[]), False),
        ("loop > loop_cap — Step-1 emit, nothing to run", _art(loop=11, cap=10), False),
        ("loop < loop_cap — deliberately unpoliced", _art(loop=1, cap=10), False),
        # --- BYPASS: not a cap terminal at all ---
        ("state CONTINUE", _art(state="CONTINUE"), False),
        ("state HALT_STAGNATION", _art(state="HALT_STAGNATION"), False),
        ("state HALT_SUCCESS", _art(state="HALT_SUCCESS"), False),
        # --- BYPASS: unusable loop/cap values ---
        ("loop_cap absent", _art(cap=None), False),
        ("loop absent", _art(loop=None), False),
        ("loop_cap not an int", _art(cap="10"), False),
        # bool is an int subclass; True must not be read as loop 1 == cap 1.
        ("loop is a bool", _art(loop=True, cap=True), False),
        # --- BYPASS: the schema_version floor ---
        ("below the v4 floor (schema_version 3)", _art(schema_version=3), False),
        ("below the v4 floor (schema_version 2)", _art(schema_version=2), False),
    ]


def _isolation(va):
    """loop_result / loop_cap values must not perturb gates that do not own them."""
    failures = []

    def verdict(art):
        out = []
        out += va.check_g21_scorecard(art)
        out += va.check_g40_discovery_persistence(art)
        return sorted(f"{i.rule}: {i.message}" for i in out)

    base = verdict(_art(loop_result=EXECUTED))
    for label, art in (
        ("no loop_result", _art()),
        ("rejected loop_result", _art(loop_result=REJECTED)),
        ("loop past cap", _art(loop=11, cap=10)),
        ("empty backlog", _art(backlog=[])),
    ):
        got = verdict(art)
        if got != base:
            failures.append(
                f"isolation: {label} changed an unrelated gate's verdict\n"
                f"  baseline: {base}\n  got:      {got}"
            )
    return failures


def main() -> int:
    va = _load_validator()
    failures = []
    triggers = 0
    cases = _cases()

    for label, art, expect_fire in cases:
        issues = va.check_g41_cap_loop_executed(copy.deepcopy(art))
        fired = bool(issues)
        if expect_fire:
            triggers += 1
        if fired != expect_fire:
            failures.append(
                f"{label}: expected {'FIRE' if expect_fire else 'silence'}, "
                f"got {'FIRE' if fired else 'silence'}"
                + (f" ({issues[0].message[:90]})" if issues else "")
            )
        for i in issues:
            if i.rule != "G41":
                failures.append(f"{label}: emitted rule {i.rule!r}, expected 'G41'")

    failures += _isolation(va)

    if triggers == 0:
        failures.append("vacuity: no TRIGGER case present")
    if REGRESSION_CASE not in cases:
        failures.append(
            "vacuity: REGRESSION_CASE is no longer in the case table — that is the shape "
            "the production run emitted and it must stay covered"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: G41 selftest — {len(cases)} cases ({triggers} trigger), isolation clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
