#!/usr/bin/env python3
"""Self-test for both halves of G5 -- residual fields belong exactly to [9.5, 10).

Rule #12 has two halves. The CONVERSE half (`check_g5_sub95_residual_fields`) rejects
residual fields OUTSIDE [9.5, 10) -- a score below 9.5, or exactly 10, carries no residual
fields -- and had zero violations across the 65-artifact corpus when it landed, so it
rejects only genuinely incoherent artifacts. The FORWARD half
(`check_g5_forward_residual_fields`) rejects their ABSENCE INSIDE [9.5, 10): every score in
that range must name the residual blocking 10. Both halves are tested here, against their
respective functions, so together they pin the range exactly.

REGRESSION_ACCEPTED_BELOW_95 is the production shape the converse exists for:
`test_strategy: 8.5` carrying `residual_disposition: "accepted"`. The rubric puts an
accepted residual at 9.5, so a score below that is not accepting a residual -- it is
deferring one -- and no gate said so.

The forward half is loaded directly from `_artifact_residual.py` rather than through
`validate-artifact.py` (as the converse cases are) because at the time this test was
written, `validate-artifact.py` had not yet been wired to call the forward check --
`_load_residual_module()` exercises the gate function itself, independent of that wiring.

Run: python3 scripts/_g5_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_g5", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_residual_module():
    """Load _artifact_residual.py directly -- the forward-half cases test the gate
    function itself, not its wiring into validate-artifact.py's run_checks()."""
    path = Path(__file__).with_name("_artifact_residual.py")
    spec = importlib.util.spec_from_file_location("_ar_g5", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dim(score, blocking=None, disposition=None, rationale=None):
    return {
        "score": score,
        "residual_blocking_10": blocking,
        "residual_disposition": disposition,
        "residual_rationale_or_backlog_ref": rationale,
    }


def _art(scorecard, schema_version=4):
    return {"schema_version": schema_version, "state": "CONTINUE", "scorecard": scorecard}


REGRESSION_ACCEPTED_BELOW_95 = _art(
    {
        "test_strategy": _dim(
            8.5,
            blocking="Session IDs have no direct test file",
            disposition="accepted",
            rationale="platform constraint",
        )
    }
)


def _cases():
    """(label, artifact, expect_fire)"""
    return [
        # --- TRIGGER: sub-9.5 carrying residual fields ---
        ("sub-9.5 with disposition='accepted'", REGRESSION_ACCEPTED_BELOW_95, True),
        (
            "sub-9.5 with disposition='queued'",
            _art({"data_flow": _dim(7.5, disposition="queued")}),
            True,
        ),
        (
            "sub-9.5 with only residual_blocking_10 populated",
            _art({"concurrency": _dim(6.5, blocking="unlocked caches")}),
            True,
        ),
        (
            "sub-9.5 with only the rationale populated",
            _art({"simplicity": _dim(8.0, rationale="see F-013")}),
            True,
        ),
        # --- TRIGGER: a 10 cannot also name a residual (G6 says a 10 has none) ---
        ("score 10 with residual_blocking_10", _art({"credibility": _dim(10, blocking="x")}), True),
        (
            "score 10 with disposition='accepted'",
            _art({"credibility": _dim(10, disposition="accepted")}),
            True,
        ),
        # --- BYPASS: the honest shapes ---
        ("sub-9.5 with every residual field null", _art({"data_flow": _dim(7.5)}), False),
        ("score 10 with every residual field null", _art({"simplicity": _dim(10)}), False),
        (
            "9.5 accepted with a named residual (the forward half's territory)",
            _art(
                {"domain_modeling": _dim(9.5, blocking="parallel fields", disposition="accepted")}
            ),
            False,
        ),
        (
            "9.5 with NO residual named -- converse doesn't apply, forward half's territory",
            # Not a converse case either way: the converse only ever fires on scores
            # outside [9.5, 10). check_g5_forward_residual_fields tests the fire case
            # for this exact shape below, in _forward_cases().
            _art({"domain_modeling": _dim(9.5)}),
            False,
        ),
        (
            "9.75 accepted -- inside [9.5, 10), same territory as 9.5",
            _art({"framework_idioms": _dim(9.75, blocking="x", disposition="accepted")}),
            False,
        ),
        # --- BYPASS: shapes the gate must not crash on ---
        (
            "non-numeric score",
            _art({"data_flow": {"score": "n/a", "residual_disposition": "x"}}),
            False,
        ),
        ("scorecard is not a dict", {"schema_version": 4, "scorecard": []}, False),
        ("scorecard absent entirely", {"schema_version": 4}, False),
    ]


def _forward_cases():
    """(label, artifact, expect_fire) against check_g5_forward_residual_fields."""
    return [
        # --- TRIGGER: [9.5, 10) missing one or both forward-required fields ---
        (
            "9.5 with NO residual named -- forward half now mechanized",
            _art({"domain_modeling": _dim(9.5)}),
            True,
        ),
        (
            "9.5 with only residual_blocking_10 populated -- rationale still missing",
            _art({"domain_modeling": _dim(9.5, blocking="parallel fields")}),
            True,
        ),
        (
            "9.5 with only the rationale populated -- blocking_10 still missing",
            _art({"simplicity": _dim(9.5, rationale="see F-013")}),
            True,
        ),
        (
            "9.75 with both fields missing -- same [9.5, 10) territory as 9.5",
            _art({"framework_idioms": _dim(9.75)}),
            True,
        ),
        # --- BYPASS: restraint -- both required fields present ---
        (
            "9.5 with both fields populated -- restraint",
            _art(
                {
                    "domain_modeling": _dim(
                        9.5,
                        blocking="parallel fields",
                        disposition="accepted",
                        rationale="see F-013",
                    )
                }
            ),
            False,
        ),
        (
            "9.5 with both fields populated, disposition null -- disposition not required here",
            _art({"data_flow": _dim(9.5, blocking="x", rationale="y")}),
            False,
        ),
        # --- BOUNDARY: forward half doesn't apply outside [9.5, 10) ---
        (
            "score below 9.5 with nulls -- forward half doesn't apply",
            _art({"data_flow": _dim(7.5)}),
            False,
        ),
        (
            "score exactly 10 with nulls -- forward half doesn't apply",
            _art({"simplicity": _dim(10)}),
            False,
        ),
        # --- BYPASS: shapes the gate must not crash on ---
        (
            "non-numeric score",
            _art({"data_flow": {"score": "n/a", "residual_blocking_10": None}}),
            False,
        ),
        ("scorecard is not a dict", {"schema_version": 4, "scorecard": []}, False),
        ("scorecard absent entirely", {"schema_version": 4}, False),
    ]


def _version_independence(va) -> list[str]:
    """Rule #12 predates every schema version, so the converse is not schema-floored.
    A v1 artifact with the incoherent shape must fire exactly as a v4 one does."""
    failures: list[str] = []
    for version in (1, 2, 3, 4):
        art = copy.deepcopy(REGRESSION_ACCEPTED_BELOW_95)
        art["schema_version"] = version
        if not va.check_g5_sub95_residual_fields(art):
            failures.append(f"schema_version {version}: converse did not fire (it is not floored)")
    return failures


def _isolation(va) -> list[str]:
    """Residual fields on a sub-9.5 dimension must not change G37's verdict -- G5 owns the
    incoherence, G37 owns the accounting, and both must be able to speak independently."""
    failures: list[str] = []
    base = {
        "schema_version": 4,
        "state": "HALT_LOOP_CAP",
        "halt_subtype": None,
        "backlog": [],
        "scorecard": {"data_flow": _dim(7.5)},
    }
    without = sorted(
        i.message for i in va.check_g37_terminal_residual_accounting(copy.deepcopy(base))
    )
    art = copy.deepcopy(base)
    art["scorecard"]["data_flow"]["residual_disposition"] = "accepted"
    with_disp = sorted(i.message for i in va.check_g37_terminal_residual_accounting(art))
    if without != with_disp:
        failures.append(
            "adding residual_disposition='accepted' changed G37's verdict; account (b) must stay "
            "unimplemented in G37 or it licenses the exact shape G5 rejects"
        )
    return failures


def main() -> int:
    va = _load_validator()
    ar = _load_residual_module()
    failures: list[str] = []

    for label, art, expect_fire in _cases():
        issues = va.check_g5_sub95_residual_fields(copy.deepcopy(art))
        fired = bool(issues)
        if fired != expect_fire:
            failures.append(
                f"{label}: expected {'FIRE' if expect_fire else 'BYPASS'}, "
                f"got {'FIRE' if fired else 'BYPASS'}"
                + (f"\n  {issues[0].message}" if issues else "")
            )

    for label, art, expect_fire in _forward_cases():
        issues = ar.check_g5_forward_residual_fields(copy.deepcopy(art))
        fired = bool(issues)
        if fired != expect_fire:
            failures.append(
                f"[forward] {label}: expected {'FIRE' if expect_fire else 'BYPASS'}, "
                f"got {'FIRE' if fired else 'BYPASS'}"
                + (f"\n  {issues[0].message}" if issues else "")
            )

    failures.extend(_version_independence(va))
    failures.extend(_isolation(va))

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: G5 converse fires on residual fields below 9.5 and at 10 across {len(_cases())} "
        f"cases, forward half fires on missing residual fields inside [9.5, 10) across "
        f"{len(_forward_cases())} cases, is version-independent, and stays disjoint from G37"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
