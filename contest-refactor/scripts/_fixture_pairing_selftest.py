#!/usr/bin/env python3
"""Self-test for validate-fixtures.py's flag/restraint pairing discipline.

evals/README.md documents a flag/restraint discipline for the model-graded
Layer 2/3 corpora (evals/scenarios/, evals/reviewer-cases/), each already
enforced by its own selftest. This one covers the analogous discipline added
to the mechanical Layer 1 corpus (evals/fixtures/), which validate-fixtures.py
checks: every fixture.toml declares either (pair_id + pair_role) linking it to
exactly one look-alike counterpart, or an explicit pair_exception reason.
Silence (neither field) is an error.

Unlike the Layer 2/3 corpora -- where nearly every scenario has a genuine 1:1
look-alike twin -- most of evals/fixtures/ is independent single-branch gate
coverage (e.g. G32's ~28 fixtures each probe a distinct structural invariant)
or single-field mutations of a shared clean baseline. Only 4 fixture pairs in
the corpus have a textually-documented "pairs with" / "negative twin of"
look-alike relationship; the other 72 fixtures carry a pair_exception. See the
inventory in the commit/report, not repeated here.

Run: python3 scripts/_fixture_pairing_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_validate_fixtures():
    path = Path(__file__).with_name("validate-fixtures.py")
    spec = importlib.util.spec_from_file_location("_vf_pairing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pair_field_cases(vf):
    """(label, data, expect_violation_rule_or_None, expect_entry)"""
    return [
        ("GREEN: valid flag", {"pair_id": "x", "pair_role": "flag"}, None, ("x", "flag")),
        (
            "GREEN: valid restraint",
            {"pair_id": "x", "pair_role": "restraint"},
            None,
            ("x", "restraint"),
        ),
        ("GREEN: valid exception", {"pair_exception": "some reason"}, None, None),
        ("RED: undeclared (neither field)", {}, "pair-schema", None),
        (
            "RED: both pair_id and pair_exception declared",
            {"pair_id": "x", "pair_role": "flag", "pair_exception": "why"},
            "pair-schema",
            None,
        ),
        ("RED: empty pair_exception string", {"pair_exception": "  "}, "pair-schema", None),
        (
            "RED: pair_role outside closed set",
            {"pair_id": "x", "pair_role": "bogus"},
            "pair-schema",
            None,
        ),
        ("RED: pair_id present, pair_role missing", {"pair_id": "x"}, "pair-schema", None),
        (
            "RED: empty pair_id string",
            {"pair_id": "  ", "pair_role": "flag"},
            "pair-schema",
            None,
        ),
    ]


def _check_pair_fields(vf) -> list[str]:
    failures: list[str] = []
    for label, data, expect_rule, expect_entry in _pair_field_cases(vf):
        violations, entry = vf._validate_pair_fields(
            Path("dummy"), data, Path("dummy/fixture.toml")
        )
        fired_rules = {v.rule for v in violations}
        if expect_rule is None:
            if violations:
                failures.append(
                    f"{label}: expected no violations, got {[v.render() for v in violations]}"
                )
        elif expect_rule not in fired_rules:
            failures.append(f"{label}: expected rule {expect_rule!r} to fire, got {fired_rules}")
        if entry != expect_entry:
            failures.append(f"{label}: expected pair_entry {expect_entry!r}, got {entry!r}")
    return failures


def _check_pairing_cardinality(vf) -> list[str]:
    failures: list[str] = []

    # GREEN: exactly one flag + one restraint.
    entries = [("p1", "flag", Path("a")), ("p1", "restraint", Path("b"))]
    violations = vf._validate_pairing(entries)
    if violations:
        failures.append(
            f"GREEN pair: expected no violations, got {[v.render() for v in violations]}"
        )

    # RED: missing twin -- flag with no restraint.
    entries = [("p2", "flag", Path("a"))]
    violations = vf._validate_pairing(entries)
    if not any(v.rule == "pair-cardinality" and "0 restraint" in v.message for v in violations):
        failures.append(
            f"RED missing-twin (flag only): did not fire clearly, got {[v.render() for v in violations]}"
        )

    # RED: dangling pair reference -- restraint with no flag.
    entries = [("p3", "restraint", Path("c"))]
    violations = vf._validate_pairing(entries)
    if not any(v.rule == "pair-cardinality" and "0 flag" in v.message for v in violations):
        failures.append(
            f"RED dangling-ref (restraint only): did not fire clearly, got {[v.render() for v in violations]}"
        )

    # RED: duplicate pair id -- two flags sharing one pair_id.
    entries = [("p4", "flag", Path("d")), ("p4", "flag", Path("e")), ("p4", "restraint", Path("f"))]
    violations = vf._validate_pairing(entries)
    if not any(
        v.rule == "pair-cardinality" and "2 flag(s) and 1 restraint(s)" in v.message
        for v in violations
    ):
        failures.append(
            f"RED duplicate pair id: did not fire clearly, got {[v.render() for v in violations]}"
        )

    return failures


def _check_real_corpus(vf) -> list[str]:
    """No-silent-exclusion: every real evals/fixtures/<id>/fixture.toml is
    paired or an exception, and every pair_id in the live corpus is a clean
    1-flag/1-restraint bijection."""
    failures: list[str] = []
    fixtures_dir = vf.SKILL_ROOT / "evals" / "fixtures"
    canon = vf._canon.load_canon(vf.SKILL_ROOT)
    kinds = vf._fixture_rule_kinds(canon)
    subdirs = sorted(p for p in fixtures_dir.iterdir() if p.is_dir())
    if not subdirs:
        return [f"no fixture subdirectories found under {fixtures_dir}"]

    pair_entries: list[tuple[str, str, Path]] = []
    for fixture_dir in subdirs:
        violations, entry = vf._validate_one_fixture(fixture_dir, canon, kinds)
        pair_violations = [v for v in violations if v.rule.startswith("pair-")]
        if pair_violations:
            failures.append(
                f"{fixture_dir.name}: unexpected pairing violation(s): "
                f"{[v.render() for v in pair_violations]}"
            )
        if entry is not None:
            pair_entries.append(entry)

    cardinality_violations = vf._validate_pairing(pair_entries)
    if cardinality_violations:
        failures.append(
            "real corpus has pair_id cardinality violation(s): "
            f"{[v.render() for v in cardinality_violations]}"
        )
    return failures


def main() -> int:
    vf = _load_validate_fixtures()
    failures: list[str] = []
    failures.extend(_check_pair_fields(vf))
    failures.extend(_check_pairing_cardinality(vf))
    failures.extend(_check_real_corpus(vf))

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: pair-field schema (RED: undeclared/both-declared/empty/bad-role/missing-role, "
        "GREEN: flag/restraint/exception) and pair-cardinality (RED: missing twin, dangling "
        "reference, duplicate pair id, GREEN: clean 1:1) all fire correctly; real "
        "evals/fixtures/ corpus is fully paired-or-excepted with no cardinality violations"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
