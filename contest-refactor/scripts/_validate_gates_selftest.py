#!/usr/bin/env python3
"""Self-test for the `--gates` selector on validate-artifact.py.

--gates runs the full check battery unchanged, then post-filters the issues
to a requested set of canonical gate ids (see canon/validation-gates.toml).
It exists so the skill-prose-mandated targeted runs (G1+G2 at sub-step 5,
G28 at checkpoint init/resume) are actually executable mid-loop, where the
full battery structurally fails gates like G18 that only apply post-commit.

Subprocesses the SHIPPED validate-artifact.py against a real fixture
directory -- never a reimplementation -- same rule as _g47_selftest.py and
_project_config_selftest.py.

Fixture: a copy of evals/fixtures/v3-clean-loop, which already fails G18 as
shipped (REVIEW_HISTORY.json.loops == [] while current_review.loop == 1),
mutated to also break REVIEW_HISTORY.md's archive divider so G22 fires too.
Confirmed by hand: both fire, nothing else does.

Run: python3 scripts/_validate_gates_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VALIDATOR = SCRIPTS / "validate-artifact.py"
FIXTURE_SRC = SCRIPTS.parent / "evals" / "fixtures" / "v3-clean-loop"

_GOOD_DIVIDER = "--- Loop 1 (UTC 2026-05-25T14:00:00Z) ---"
_BAD_DIVIDER = "--- Loop 1 (UTC not-a-timestamp) ---"


def _make_fixture(root: Path) -> Path:
    """Copy v3-clean-loop and break its archive divider so G18 (as-shipped)
    and G22 (mutated here) both fire with no other gate in the way.
    """
    fixture = root / "fixture"
    shutil.copytree(FIXTURE_SRC, fixture)
    md_path = fixture / "REVIEW_HISTORY.md"
    text = md_path.read_text(encoding="utf-8")
    if _GOOD_DIVIDER not in text:
        raise AssertionError(f"fixture source drifted: divider line not found in {md_path}")
    md_path.write_text(text.replace(_GOOD_DIVIDER, _BAD_DIVIDER), encoding="utf-8")
    return fixture


def _run(fixture: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(fixture), "--mode", "strict", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="validate-gates-selftest-") as td:
        fixture = _make_fixture(Path(td))

        # Case 1: --gates G22 -> exit 1, mentions G22, not G18.
        r = _run(fixture, "--gates", "G22")
        if r.returncode != 1:
            failures.append(f"case1: expected exit 1, got {r.returncode}: {r.stderr}")
        if "[G22]" not in r.stderr:
            failures.append(f"case1: expected G22 in output: {r.stderr}")
        if "[G18]" in r.stderr:
            failures.append(f"case1: G18 leaked through the G22 filter: {r.stderr}")

        # Case 2: --gates G28 -> exit 0 (the mid-loop use case: G18's
        # structural failure is filtered out; this fixture never fires G28).
        r = _run(fixture, "--gates", "G28")
        if r.returncode != 0:
            failures.append(f"case2: expected exit 0, got {r.returncode}: {r.stderr}")

        # Case 3: unknown gate id -> exit 2 usage error naming the bad token.
        r = _run(fixture, "--gates", "NOT_A_GATE")
        if r.returncode != 2:
            failures.append(f"case3: expected exit 2, got {r.returncode}: {r.stderr}")
        if "NOT_A_GATE" not in r.stderr:
            failures.append(f"case3: bad token not named in stderr: {r.stderr}")

        # Case 3b: empty --gates value -> exit 2 (distinct branch from an
        # unknown-id token; regression guard for the empty-token check).
        r = _run(fixture, "--gates", "")
        if r.returncode != 2:
            failures.append(
                f"case3b: empty --gates expected exit 2, got {r.returncode}: {r.stderr}"
            )

        # Case 4: no --gates flag -> both G18 and G22 reported, non-zero exit
        # (regression guard: unfiltered behavior stays byte-identical).
        r = _run(fixture)
        if r.returncode == 0:
            failures.append(f"case4: expected non-zero exit with no filter, got 0: {r.stdout}")
        if "[G18]" not in r.stderr or "[G22]" not in r.stderr:
            failures.append(f"case4: expected both G18 and G22 unfiltered: {r.stderr}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: --gates filters to requested gate ids; unfiltered behavior unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
