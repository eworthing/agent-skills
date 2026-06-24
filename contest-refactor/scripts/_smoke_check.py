#!/usr/bin/env python3
"""Full artifact-smoke pass: run validate-artifact.py over every smoke fixture
and assert each result matches its expected pass/fail.

PR1 development helper; not part of the loop runtime. The expected map below is
the executable form of the table in evals/artifact-smoke/README.md — keep them in
sync. A fixture directory with no expected entry fails the run (drift guard), so
adding a fixture without documenting its expected result is caught here.

Run: python3 scripts/_smoke_check.py        (exit 0 = all match, 1 = mismatch)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# fixture id -> expected validator result ("pass" = exit 0, "fail" = non-zero).
# Source of truth: evals/artifact-smoke/README.md table.
EXPECTED = {
    "halt-success-clean": "pass",
    "halt-success-with-unresolved-serious": "fail",
    "halt-success-sub-95-score": "fail",
    "halt-stagnation-eligible-remains": "fail",
    "halt-stagnation-fully-retired": "pass",
    "unresolvable-insufficient-attempts": "fail",
    "expired-residual": "fail",
    "branch-b-fake-resolve-not-a-validator-error": "pass",
}


def main() -> int:
    skill_dir = Path(__file__).resolve().parent.parent
    smoke_dir = skill_dir / "evals" / "artifact-smoke"
    validator = skill_dir / "scripts" / "validate-artifact.py"

    fixtures = sorted(p.name for p in smoke_dir.iterdir() if (p / "CURRENT_REVIEW.json").is_file())
    undocumented = [f for f in fixtures if f not in EXPECTED]
    if undocumented:
        for f in undocumented:
            print(f"FAIL: fixture {f!r} has no expected entry (update EXPECTED + README)")
        return 1

    failures = 0
    for fixture in fixtures:
        proc = subprocess.run(
            [sys.executable, str(validator), str(smoke_dir / fixture), "--mode", "strict"],
            capture_output=True,
            text=True,
        )
        got = "pass" if proc.returncode == 0 else "fail"
        want = EXPECTED[fixture]
        if got == want:
            print(f"OK    {fixture} ({got})")
        else:
            failures += 1
            print(f"WRONG {fixture}: expected={want} got={got}")
            if proc.stdout.strip():
                print(f"      {proc.stdout.strip().splitlines()[0]}")

    print("---")
    if failures:
        print(f"smoke: {failures} fixture(s) did not match expected result")
        return 1
    print(f"smoke: OK ({len(fixtures)} fixtures matched expected result)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
