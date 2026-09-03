#!/usr/bin/env python3
"""Self-test for G52 site-pass ledger completeness (report-only; SITE-PASS plan W1).
Run: python3 scripts/_g52_selftest.py   (exit 0 = pass, 1 = fail)
Guards every diagnostic the checker can raise, that it never returns an Issue, that an
unscoped run is silent with site_pass null and diagnosed with site_pass present, and that a
pre-epoch artifact (skill_rev before the site_pass boundary) is silent.
"""

from __future__ import annotations

import copy
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _artifact_site_pass as G52

PATHS = ["Kit/Sources/F/A.swift", "Kit/Sources/F/B.swift"]


def _answers(**over: dict) -> dict:
    qs = {f"Q{i}": {"status": "clean"} for i in range(1, 9)}
    qs.update(over)
    return qs


def _artifact(*, scoped: bool = True, skill_rev: str = "1b4ddd5") -> dict:
    discovery = {"source_roots": ["Kit/Sources/F"], "lens": "Apple"}
    art: dict = {
        "schema_version": 4,
        "skill_rev": skill_rev,
        "loop": 1,
        "state": "CONTINUE",
        "discovery": discovery,
        "findings": [{"id": "F1", "evidence": ["Kit/Sources/F/A.swift:10"]}],
        "site_pass": None,
    }
    if scoped:
        discovery["scope"] = "Kit/Sources/F"
        discovery["site_pass_roster"] = {
            "scope": "Kit/Sources/F",
            "paths": list(PATHS),
            "digest": G52.roster_digest(PATHS),
        }
        art["site_pass"] = {
            "files": [
                {
                    "path": PATHS[0],
                    "reads": "full",
                    "questions": _answers(Q2={"status": "finding", "finding_ids": ["F1"]}),
                },
                {
                    "path": PATHS[1],
                    "reads": "partial:1-40",
                    "questions": _answers(Q3={"status": "not_applicable", "reason": "no controls"}),
                },
            ]
        }
    else:
        discovery["scope"] = None
        discovery["site_pass_roster"] = None
    return art


def _run(art: dict) -> tuple[list, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        issues = G52.check_g52_site_pass(art)
    return issues, buf.getvalue()


def check(cond: bool, msg: str, failures: list[str]) -> None:
    if not cond:
        failures.append(msg)


def main() -> int:
    f: list[str] = []
    issues, out = _run(_artifact())
    check(issues == [] and out == "", f"valid scoped ledger must be silent; got {out!r}", f)
    issues, out = _run(_artifact(scoped=False))
    check(
        issues == [] and out == "", f"unscoped with null site_pass must be silent; got {out!r}", f
    )

    a = _artifact(scoped=False)
    a["site_pass"] = {"files": []}
    issues, out = _run(a)
    check(issues == [] and "must be null on an unscoped run" in out, f"unscoped+ledger: {out!r}", f)

    a = _artifact(skill_rev="000c7d8")  # md_state_parity epoch, before site_pass
    a["site_pass"]["files"].pop()
    issues, out = _run(a)
    check(out == "", f"pre-epoch artifact must be silent; got {out!r}", f)

    cases = {
        "missing file": (lambda a: a["site_pass"]["files"].pop(), "missing 1"),
        "extra path": (
            lambda a: a["site_pass"]["files"].append(
                {"path": "Kit/Sources/F/Z.swift", "reads": "full", "questions": _answers()}
            ),
            "outside the roster",
        ),
        "duplicate path": (
            lambda a: a["site_pass"]["files"].append(copy.deepcopy(a["site_pass"]["files"][0])),
            "more than once",
        ),
        "site_pass null": (lambda a: a.__setitem__("site_pass", None), "site_pass must be {files"),
        "roster missing": (
            lambda a: a["discovery"].__setitem__("site_pass_roster", None),
            "site_pass_roster must be",
        ),
        "digest mismatch": (
            lambda a: a["discovery"]["site_pass_roster"].__setitem__("digest", "00"),
            "does not re-derive",
        ),
        "questions keys": (
            lambda a: a["site_pass"]["files"][0]["questions"].pop("Q8"),
            "exactly Q1..Q8",
        ),
        "bad status": (
            lambda a: a["site_pass"]["files"][0]["questions"].__setitem__(
                "Q1", {"status": "maybe"}
            ),
            "status must be",
        ),
        "finding no ids": (
            lambda a: a["site_pass"]["files"][0]["questions"].__setitem__(
                "Q2", {"status": "finding", "finding_ids": []}
            ),
            "non-empty finding_ids",
        ),
        "unknown finding id": (
            lambda a: a["site_pass"]["files"][0]["questions"].__setitem__(
                "Q2", {"status": "finding", "finding_ids": ["F9"]}
            ),
            "not present in findings",
        ),
        "n/a no reason": (
            lambda a: a["site_pass"]["files"][1]["questions"].__setitem__(
                "Q3", {"status": "not_applicable", "reason": " "}
            ),
            "non-empty reason",
        ),
        "clean with ids": (
            lambda a: a["site_pass"]["files"][0]["questions"].__setitem__(
                "Q1", {"status": "clean", "finding_ids": ["F1"]}
            ),
            "clean must not carry",
        ),
        "bad reads": (
            lambda a: a["site_pass"]["files"][0].__setitem__("reads", "skim"),
            "reads must be",
        ),
    }
    for name, (mutate, needle) in cases.items():
        a = _artifact()
        mutate(a)
        issues, out = _run(a)
        check(issues == [], f"{name}: report-only must never return an Issue", f)
        check(needle in out, f"{name}: expected diagnostic containing {needle!r}; got {out!r}", f)
        check("[g52-site-pass loop=1 " in out, f"{name}: diagnostic prefix missing; got {out!r}", f)

    if f:
        for m in f:
            print(f"FAIL: {m}")
        return 1
    print(
        f"OK: G52 selftest — valid/unscoped/pre-epoch silent; {len(cases)} diagnostics fire, never an Issue"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
