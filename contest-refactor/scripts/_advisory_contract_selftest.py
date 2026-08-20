#!/usr/bin/env python3
"""Self-test: validate-artifact.py's mode contract.

The validator is an operator/audit tool. Nothing in the runtime protocol invokes
it: the Step-3 sweep instruction that used to was removed on 2026-08-20 after
firing 0/6 times across two production runs (sweep #4, probe P2). Its value is
realised when a human or a reviewing agent runs it against an artifact -- which
on 2026-08-19/20 surfaced 15 WARNs mid-run, a shipped G19 table drift, and a real
G17 violation at a terminal HALT_SUCCESS.

That makes the mode contract MORE load-bearing, not less, because an auditor
needs to trust what an exit code means:

  1. advisory on a KNOWN-FAILING fixture exits 0 and still prints WARN lines --
     informative and non-blocking (auditing must never be a gate).
  2. strict on the SAME fixture exits 1, so the two modes are provably different
     and (1) is not vacuous.
  3. a missing directory exits 2 -- plumbing stays distinguishable from measured
     failure, so "could not run" can never read as "found nothing".

Run: python3 scripts/_advisory_contract_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = SKILL_ROOT / "scripts" / "validate-artifact.py"
FIXTURE = SKILL_ROOT / "evals" / "fixtures" / "g37-cap-open-backlog-stranded"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args], capture_output=True, text=True, check=False
    )


def main() -> int:
    failures: list[str] = []

    if not FIXTURE.is_dir():
        print(f"FAIL: fixture missing: {FIXTURE}")
        return 1

    # 1. advisory: informative AND non-blocking
    adv = _run(str(FIXTURE), "--mode", "advisory")
    if adv.returncode != 0:
        failures.append(
            f"advisory exited {adv.returncode} on a known-failing fixture; it must exit 0. "
            f"The Step-3 sweep runs immediately before the commit -- a non-zero advisory would "
            f"turn an imperfect artifact into a dead loop"
        )
    if "WARN" not in adv.stderr:
        failures.append(
            "advisory printed no WARN lines on a known-failing fixture -- a silent sweep tells "
            "the loop nothing, which is the other half of the contract"
        )

    # 2. strict differs, so (1) is not vacuous
    strict = _run(str(FIXTURE), "--mode", "strict")
    if strict.returncode != 1:
        failures.append(
            f"strict exited {strict.returncode} on a known-failing fixture; expected 1. If strict "
            f"and advisory agree, the advisory pass in (1) proves nothing about mode handling"
        )

    # 3. plumbing stays distinguishable from measured failure
    missing = _run(str(SKILL_ROOT / "no-such-artifact-dir"), "--mode", "advisory")
    if missing.returncode != 2:
        failures.append(
            f"a missing artifact dir exited {missing.returncode}; expected 2 (cannot measure). "
            f"Folding it into 0 would let the sweep silently not run"
        )

    # (4) previously asserted that validation.md still instructed the Step-3 sweep.
    # Removed 2026-08-20 with the instruction itself: it fired 0/6 times across two
    # production runs, so the repo was paying 64 per-loop tokens to advertise a step
    # that never executed. Assertions 1-3 are unchanged and now matter MORE, not less
    # -- they are the contract an operator or auditor relies on when running the
    # validator by hand, which is where it demonstrably produces value.

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: advisory contract holds — non-blocking, informative, mode-distinct")
    return 0


if __name__ == "__main__":
    sys.exit(main())
