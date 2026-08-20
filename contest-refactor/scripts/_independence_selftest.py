#!/usr/bin/env python3
"""Self-test: the challenge-independence report-only check.

Found live on a real run (BenchHype, 2026-08-19): HALT_SUCCESS at loop 1 promoted by
an inline self-vet, all 46 gates clean. G32 only requires challenger_model to be a
non-empty string, while `spawn_isolation` -- a typed enum already in the artifact --
records the distinction G32 cannot see.

Pinned here:
  1. inline + terminal success  -> fires, and names spawn_isolation in the diagnostic
  2. subagent + terminal success -> silent (independence is the normal case, not noise)
  3. inline + non-terminal state -> silent (only a TERMINAL success overclaims)
  4. report-only: returns no Issue, so it can never fail validate-artifact --mode strict

Run: python3 scripts/_independence_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import _artifact_independence as ind


def _run(artifact: dict) -> tuple[list, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        issues = ind.check_challenge_independence_report_only(artifact)
    return issues, buf.getvalue()


def _artifact(**over) -> dict:
    base = {
        "schema_version": 4,
        "state": "HALT_SUCCESS",
        "spawn_isolation": "inline",
        "provider": "unknown",
        "halt_success_challenge": {"challenger_model": "inline-vetting", "outcome": "held"},
    }
    base.update(over)
    return base


def main() -> int:
    failures: list[str] = []

    issues, out = _run(_artifact())
    if "challenge-independence" not in out:
        failures.append("inline + HALT_SUCCESS must emit a diagnostic; got nothing")
    if "spawn_isolation=inline" not in out:
        failures.append(
            f"the diagnostic must name spawn_isolation -- it is the typed field G32 ignores "
            f"and the whole reason the check exists. Got: {out!r}"
        )
    if issues:
        failures.append(
            f"report-only must return no Issue (it would fail --mode strict on a legal "
            f"artifact); got {len(issues)}"
        )

    _, out = _run(_artifact(spawn_isolation="subagent", provider="opencode"))
    if out.strip():
        failures.append(
            f"an independently-spawned challenger is the normal case and must stay silent; "
            f"got: {out!r}"
        )

    _, out = _run(_artifact(state="CONTINUE"))
    if out.strip():
        failures.append(f"only a TERMINAL success overclaims independence; got: {out!r}")

    _, out = _run(_artifact(state="HALT_SUCCESS_candidate"))
    if "challenge-independence" not in out:
        failures.append("a HALT_SUCCESS_candidate is promotable and must also be flagged")

    _, out = _run(_artifact(schema_version=3))
    if out.strip():
        failures.append(
            f"spawn_isolation is a v4 field; a v3 artifact must not be judged by it (item 30's "
            f"retroactive-invalidation rule). Got: {out!r}"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: challenge-independence — fires on inline terminals, silent otherwise, report-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
