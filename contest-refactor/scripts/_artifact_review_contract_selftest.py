#!/usr/bin/env python3
"""Self-test: _artifact_review_contract.py (backlog item [I1] items 3 and 4).

Pins:
  - rounds: missing/None, True, False, 0, 3, "1" all fail at CURRENT epoch;
    1 and 2 pass; every case is tolerated at LEGACY epoch; an absent
    implementation_review is exempt entirely (no requirement to check).
  - G29: v1/v2/v3, missing, null, non-int, and bool all fail at CURRENT
    epoch; v4 passes (the live, zero-entry-manifest value); a declared v5
    fails naming the empty-manifest reason; LEGACY tolerates every value.

Run: python3 scripts/_artifact_review_contract_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import _artifact_review_contract as rc

_CURRENT = {"skill_rev": "2b81c10"}
_LEGACY = {}


def _art(review=None, schema_version=4, epoch=_CURRENT, **over):
    base = {
        "schema_version": schema_version,
        "provider": "claude_code",
        "loop_model": "claude-sonnet-5",
    }
    base.update(epoch)
    if review is not None:
        base["implementation_review"] = review
    base.update(over)
    return base


def main() -> int:
    failures: list[str] = []

    # --- rounds: absent implementation_review is exempt ----------------------
    if rc.check_rounds_membership(_art(review=None)):
        failures.append("no implementation_review at all must never owe rounds")

    # --- rounds: CURRENT epoch, invalid shapes must fail ----------------------
    for label, rounds in (
        ("missing key", {}),
        ("explicit null", {"rounds": None}),
        ("bool True", {"rounds": True}),
        ("bool False", {"rounds": False}),
        ("zero", {"rounds": 0}),
        ("three", {"rounds": 3}),
        ("string '1'", {"rounds": "1"}),
    ):
        issues = rc.check_rounds_membership(_art(review=rounds))
        if not any(i.rule == "rounds-membership" for i in issues):
            failures.append(f"rounds {label}: expected rounds-membership failure, got {issues}")

    # --- rounds: CURRENT epoch, valid values pass -----------------------------
    for valid in (1, 2):
        issues = rc.check_rounds_membership(_art(review={"rounds": valid}))
        if issues:
            failures.append(f"rounds={valid} is legal and must pass; got {issues}")

    # --- rounds: LEGACY epoch tolerates everything, including bool/missing ---
    for rounds in ({}, {"rounds": None}, {"rounds": True}, {"rounds": "1"}, {"rounds": 3}):
        issues = rc.check_rounds_membership(_art(review=rounds, epoch=_LEGACY))
        if issues:
            failures.append(f"LEGACY epoch must tolerate rounds={rounds!r}; got {issues}")

    # --- G29: CURRENT epoch, v4 (the live capability-derived value) passes ---
    issues = rc.check_g29_schema_version(_art(schema_version=4))
    if issues:
        failures.append(f"schema_version=4 is the live value and must pass; got {issues}")

    # --- G29: CURRENT epoch, every stale/malformed declaration fails ---------
    for label, declared in (
        ("v1", 1),
        ("v2", 2),
        ("v3", 3),
        ("missing", None),
        ("non-int string", "4"),
        ("bool True", True),
    ):
        art = _art(schema_version=4)
        art["schema_version"] = declared
        issues = rc.check_g29_schema_version(art)
        if not any(i.rule == "G29-version-equality" for i in issues):
            failures.append(f"schema_version {label} ({declared!r}) must fail G29; got {issues}")

    # --- G29: CURRENT epoch, v5 fails while the manifest has zero entries ----
    issues = rc.check_g29_schema_version(_art(schema_version=5))
    if not any(i.rule == "G29-version-equality" for i in issues):
        failures.append("schema_version=5 with an unauthorized (empty) manifest must fail")
    elif not any("no_entry" in i.message for i in issues):
        failures.append(
            f"the v5 failure must name the manifest's own reason code (no_entry); "
            f"got {[i.message for i in issues]}"
        )

    # --- G29: LEGACY epoch tolerates every value ------------------------------
    for declared in (1, 2, 3, None, "4", True, 5):
        issues = rc.check_g29_schema_version(_art(schema_version=declared, epoch=_LEGACY))
        if issues:
            failures.append(f"LEGACY epoch must tolerate schema_version={declared!r}; got {issues}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: rounds-membership rejects non-{1,2} shapes (bool included) at CURRENT epoch and "
        "tolerates them at LEGACY; G29-version-equality requires the capability-derived version "
        "exactly, v5 fails against the zero-entry manifest, LEGACY tolerates any declared version"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
