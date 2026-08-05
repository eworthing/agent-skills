#!/usr/bin/env python3
"""Self-test for G42 — backlog item identity. (Why G42 exists: validation.md.)

Pinned against the REAL gate function in validate-artifact.py:

  1. TRIGGER    — fires on a missing/blank/non-string stable_id, on a malformed id, on
                  a non-object backlog item, and on an id absent from this loop's
                  findings[] when findings[] is non-empty.
  2. REGRESSION — the pre-G42 shape: a well-formed backlog item whose only trace of
                  identity is "(Finding F-002)" inside the title. Every field a rule
                  could read is present and correct; the identity is prose. Pinned by
                  identity (REGRESSION_CASE) so it cannot be quietly dropped.
  3. BYPASS     — silent on a well-formed id, on the conditional findings link when
                  findings[] is empty (minimal single-gate fixtures legitimately carry
                  none), on an empty/absent backlog, and below the schema_version 4
                  floor.
  4. ISOLATION  — a stable_id value never changes an unrelated gate's verdict.
  5. VACUITY    — a gate that silently stopped firing cannot pass by doing nothing.

No pytest in this repo -> standalone _*.py helper.

Run: python3 scripts/_g42_selftest.py   (exit 0 = pass, 1 = fail)
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
    spec = importlib.util.spec_from_file_location("_va_g42", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DIMS = tuple(load_canon(HERE.parent).scorecard_dimensions)


def _item(stable_id=..., title="Collapse the duplicated dialog ceremony"):
    it = {
        "priority": 1,
        "rank": "needed for winning",
        "title": title,
        "kind": "structural",
        "why_it_matters": "three near-identical bodies drift apart",
        "score_impact": "simplicity +0.5",
    }
    if stable_id is not ...:
        it["stable_id"] = stable_id
    return it


def _art(backlog=None, *, findings=("F-002", "F-003"), schema_version=4):
    return {
        "schema_version": schema_version,
        "state": "CONTINUE",
        "loop": 3,
        "backlog": [_item("F-002")] if backlog is None else backlog,
        "findings": [{"stable_id": f, "title": f"finding {f}"} for f in findings],
        "scorecard": {d: {"score": 7.0} for d in DIMS},
    }


# The pre-G42 shape: every machine-readable field correct, identity only in the prose.
REGRESSION_CASE = (
    "REGRESSION: identity only inside the title prose",
    _art([_item(title="Collapse the duplicated dialog ceremony (Finding F-002)")]),
    True,
)


# (label, artifact, expect_fire)
def _cases():
    return [
        # --- TRIGGER: no usable identity ---
        REGRESSION_CASE,
        ("stable_id absent", _art([_item()]), True),
        ("stable_id blank", _art([_item("   ")]), True),
        ("stable_id not a string", _art([_item(2)]), True),
        ("backlog item not an object", _art(["F-002"]), True),
        # --- TRIGGER: malformed id ---
        ("bare number", _art([_item("2")]), True),
        ("too few digits", _art([_item("F-2")]), True),
        ("lowercase prefix", _art([_item("f-002")]), True),
        ("prose appended to a valid id", _art([_item("F-002 (dialog ceremony)")]), True),
        # --- TRIGGER: well-formed but points at nothing ---
        ("id absent from this loop's findings", _art([_item("F-999")]), True),
        (
            "one good item, one dangling",
            _art([_item("F-002"), _item("F-404")]),
            True,
        ),
        # --- BYPASS: well formed and linked ---
        ("valid id present in findings", _art([_item("F-002")]), False),
        ("second valid id", _art([_item("F-003")]), False),
        ("four-digit id", _art([_item("F-1024")], findings=("F-1024",)), False),
        (
            "multiple items, all linked",
            _art([_item("F-002"), _item("F-003")]),
            False,
        ),
        # --- BYPASS: the conditional findings link ---
        # Minimal single-gate fixtures carry no findings; the link cannot be checked and
        # the shape check still applies, so a well-formed id passes.
        ("findings[] empty — link not checked", _art([_item("F-999")], findings=()), False),
        # --- BYPASS: out of scope ---
        ("empty backlog", _art([]), False),
        (
            "absent backlog key",
            {"schema_version": 4, "state": "CONTINUE", "findings": [], "scorecard": {}},
            False,
        ),
        # --- BYPASS: the schema_version floor. The v1-v3 corpus has no stable_id on
        # backlog items at all; retroactively failing it would be a bug in this gate.
        ("below the v4 floor (schema_version 3)", _art([_item()], schema_version=3), False),
        ("below the v4 floor (schema_version 2)", _art([_item()], schema_version=2), False),
        ("below the v4 floor (schema_version 1)", _art([_item()], schema_version=1), False),
    ]


def _isolation(va):
    """A stable_id value must not perturb gates that do not own it."""
    failures = []

    def verdict(art):
        out = []
        out += va.check_g21_scorecard(art)
        out += va.check_g39_backlog_score_impact(art, load_canon(HERE.parent))
        return sorted(f"{i.rule}: {i.message}" for i in out)

    base = verdict(_art([_item("F-002")]))
    for label, art in (
        ("absent", _art([_item()])),
        ("malformed", _art([_item("f-002")])),
        ("dangling", _art([_item("F-999")])),
        ("four-digit", _art([_item("F-1024")])),
    ):
        got = verdict(art)
        if got != base:
            failures.append(
                f"isolation: stable_id={label} changed an unrelated gate's verdict\n"
                f"  baseline: {base}\n  got:      {got}"
            )
    return failures


def main() -> int:
    va = _load_validator()
    failures = []
    triggers = 0
    cases = _cases()

    for label, art, expect_fire in cases:
        issues = va.check_g42_backlog_stable_id(copy.deepcopy(art))
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
            if i.rule != "G42":
                failures.append(f"{label}: emitted rule {i.rule!r}, expected 'G42'")

    failures += _isolation(va)

    if triggers == 0:
        failures.append("vacuity: no TRIGGER case present")
    if REGRESSION_CASE not in cases:
        failures.append(
            "vacuity: REGRESSION_CASE is no longer in the case table — an item whose "
            "identity exists only in the title prose is the shape G42 was written for"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: G42 selftest — {len(cases)} cases ({triggers} trigger), isolation clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
