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
    ci = over.pop("challenger_isolation", None)
    base.update(over)
    if ci is not None:
        base["halt_success_challenge"] = dict(
            base["halt_success_challenge"], challenger_isolation=ci
        )
    return base


def main() -> int:
    failures: list[str] = []

    issues, out = _run(_artifact())
    if "challenge-independence" not in out:
        failures.append("inline + HALT_SUCCESS must emit a diagnostic; got nothing")
    # Intent unchanged, literal moved: the diagnostic must say WHICH field drove the
    # verdict, now that two can (challenger_isolation, or the loop-level fallback).
    if "source=spawn_isolation" not in out:
        failures.append(
            f"the diagnostic must name the field it relied on -- these are the typed fields "
            f"G32 ignores and the whole reason the check exists. Got: {out!r}"
        )
    if issues:
        failures.append(
            f"report-only must return no Issue (it would fail --mode strict on a legal "
            f"artifact); got {len(issues)}"
        )

    # CHANGED 2026-08-20, deliberately. This case previously asserted SILENCE, and
    # that assertion is what let the defect through: `spawn_isolation` describes the
    # LOOP spawn, and a loop running as a subagent proves nothing about the challenge
    # it then ran. BenchHype run 2 was exactly this shape -- subagent loop, inline
    # challenger, because an opencode subagent cannot nest-spawn -- and reached a
    # user-visible HALT_SUCCESS in silence.
    _, out = _run(_artifact(spawn_isolation="subagent", provider="opencode"))
    if "challenge-independence-unverified" not in out:
        failures.append(
            f"a subagent LOOP does not establish an independent CHALLENGE; with no "
            f"challenger_isolation recorded the result is unverified, not silent. Got: {out!r}"
        )

    # The challenger's own record is what settles it, in both directions.
    _, out = _run(
        _artifact(spawn_isolation="subagent", provider="opencode", challenger_isolation="subagent")
    )
    if out.strip():
        failures.append(
            f"a recorded independent challenge is the normal case and must stay silent; got: {out!r}"
        )

    _, out = _run(
        _artifact(spawn_isolation="subagent", provider="opencode", challenger_isolation="inline")
    )
    if "[challenge-independence " not in out:
        failures.append(
            f"challenger_isolation=inline under a SUBAGENT loop is the run-2 defect and must "
            f"fire; got: {out!r}"
        )
    if "unverified" in out:
        failures.append(
            f"a recorded inline challenge is verified-not-independent, not unverified; got: {out!r}"
        )

    # challenger_isolation outranks the loop-level fallback when both are present.
    _, out = _run(_artifact(spawn_isolation="inline", challenger_isolation="subagent"))
    if out.strip():
        failures.append(
            f"an explicitly recorded independent challenge outranks the loop-level fallback "
            f"signal; got: {out!r}"
        )

    # A garbage value must not be read as independence.
    _, out = _run(_artifact(spawn_isolation="subagent", challenger_isolation="probably?"))
    if "unverified" not in out:
        failures.append(
            f"an unrecognised challenger_isolation must be unverified, not silent; got: {out!r}"
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

    # --- the reviewer is the other verification a terminal rests on ----------
    a = _artifact(spawn_isolation="subagent", challenger_isolation="subagent")
    a["implementation_review"] = {"reviewer_isolation": "inline"}
    _, out = _run(a)
    if "reviewer-independence" not in out:
        failures.append(
            f"an inline implementation review at a terminal must be disclosed; got: {out!r}"
        )

    a["implementation_review"] = {"reviewer_isolation": "subagent"}
    _, out = _run(a)
    if out.strip():
        failures.append(f"an independently-spawned reviewer is the normal case; got: {out!r}")

    a["implementation_review"] = {}
    _, out = _run(a)
    if "reviewer-independence" in out:
        failures.append(
            f"an ABSENT reviewer_isolation is an optional v4 field (item 30): it must not be "
            f"read as inline. Got: {out!r}"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: challenge-independence — fires on inline terminals, silent otherwise, report-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
