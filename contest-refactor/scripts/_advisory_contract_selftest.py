#!/usr/bin/env python3
"""Self-test: the advisory-mode contract the Step-3 mechanical sweep depends on.

references/validation.md instructs the loop to run, once all five artifacts are on
disk and before the commit:

    scripts/validate-artifact.py <dir> --mode advisory

That instruction rests on a behavioural promise -- **advisory never blocks** -- and
the promise is load-bearing in a way a prose check cannot cover. If the default
flipped, or advisory started returning non-zero on findings, every loop would begin
dying at commit time on an artifact that is merely imperfect. The sweep exists to
inform the emit, never to stop it.

So this pins the contract, not the wording:

  1. advisory on a KNOWN-FAILING fixture exits 0 and still prints WARN lines
     (informative and non-blocking are both required -- silence would be useless,
     and a non-zero exit would be dangerous).
  2. strict on the SAME fixture exits 1, so the two modes are provably different
     and (1) is not passing vacuously on an artifact that simply has no issues.
  3. a missing directory exits 2 -- plumbing stays distinguishable from measured
     failure, the discipline applied to exec_replay_grade.py.
  4. validation.md still carries the instruction, naming the script and the flag.

Fixture choice: g37-cap-open-backlog-stranded is declared `expected_result = "fail"`
and carries the full sibling set (CURRENT_REVIEW.{md,json}, REVIEW_HISTORY.{md,json},
findings_registry.json), so its failures are real gate findings rather than
missing-artifact noise -- which is the same ordering hazard the sweep instruction
itself guards against by requiring all five files on disk first.

Run: python3 scripts/_advisory_contract_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = SKILL_ROOT / "scripts" / "validate-artifact.py"
FIXTURE = SKILL_ROOT / "evals" / "fixtures" / "g37-cap-open-backlog-stranded"
VALIDATION_MD = SKILL_ROOT / "references" / "validation.md"


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

    # 4. the instruction is still there
    text = VALIDATION_MD.read_text(encoding="utf-8")
    if "--json" not in text.split("**Mechanical sweep**")[-1].split("\n")[0]:
        failures.append(
            "the Step-3 sweep no longer writes --json: advisory WARNs would live only in the loop "
            "subagent's stderr and die with it, leaving nothing to analyse after a run"
        )
    if "validate-artifact.py" not in text or "--mode advisory" not in text:
        failures.append(
            "validation.md no longer instructs the Step-3 mechanical sweep "
            "(`validate-artifact.py <dir> --mode advisory`) -- the validator is wired to nothing "
            "again, which is the state this change existed to fix"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: advisory contract holds — non-blocking, informative, mode-distinct, wired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
