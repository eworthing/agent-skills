#!/usr/bin/env python3
"""Self-test for G39 — backlog score_impact dimension attribution.

`score_impact` was a required field that no rule read, so it drifted into prose that
nothing could act on. G39 pins it to `<canon_dim_id> <signed delta>`, semicolon-joined,
so the Backlog Prioritization Pass and the priority probe grader can attribute a backlog
item to a dimension without parsing English. This test pins four things against the REAL
gate function in validate-artifact.py:

  1. TRIGGER   — G39 fires on prose, display labels, unknown ids, a dimension absent from
                 this loop's scorecard, and a missing/blank/non-string score_impact.
  2. BYPASS    — G39 stays silent on the valid shape (single and semicolon-joined,
                 negative deltas, integer deltas), on an EMPTY backlog, and below the
                 schema_version 4 floor. A regression that broadened the predicate — or
                 that started firing on the v1-v3 corpus — would flip one of these.
  3. ISOLATION — a score_impact value never changes an unrelated gate's verdict
                 (check_g21_scorecard / check_continue_backlog), mirroring
                 _metric_isolation_selftest.py.
  4. VACUITY   — at least one TRIGGER case exists, so a gate that silently stopped
                 firing cannot pass by doing nothing.

No pytest in this repo -> standalone _*.py helper.

Run: python3 scripts/_g39_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _canon import load_canon
from _selftest_lib import load_validator as _load_validator

DIMS = (
    "architecture_quality",
    "state_management",
    "concurrency",
    "test_strategy",
    "credibility",
    "domain_modeling",
    "data_flow",
    "framework_idioms",
    "simplicity",
)


def _scorecard(*, drop=()):
    return {d: {"score": 7.0} for d in DIMS if d not in drop}


def _art(impact, *, schema_version=4, backlog=None, scorecard=None):
    """A minimal artifact carrying one backlog item with the given score_impact."""
    if backlog is None:
        item = {"priority": 1, "title": "t", "kind": "structural", "why_it_matters": "w"}
        if impact is not ...:
            item["score_impact"] = impact
        backlog = [item]
    return {
        "schema_version": schema_version,
        "state": "CONTINUE",
        "backlog": backlog,
        "scorecard": _scorecard() if scorecard is None else scorecard,
    }


# (label, artifact, expect_fire)
def _cases():
    cases = [
        # --- TRIGGER ---
        (
            "legacy prose with display labels",
            _art("Architecture quality + State management each +1.0"),
            True,
        ),
        ("display label, right shape otherwise", _art("Data flow +0.5"), True),
        ("prose suffix after a valid entry", _art("data_flow +0.5 once verified"), True),
        ("unknown dimension id", _art("velocity +0.5"), True),
        (
            "known id absent from THIS loop's scorecard",
            _art("data_flow +0.5", scorecard=_scorecard(drop=("data_flow",))),
            True,
        ),
        ("delta missing entirely", _art("data_flow"), True),
        ("unsigned delta", _art("data_flow 0.5"), True),
        ("score_impact absent", _art(...), True),
        ("score_impact blank", _art("   "), True),
        ("score_impact not a string", _art(0.5), True),
        ("one good entry, one prose entry", _art("data_flow +0.5; and some tests"), True),
        # --- BYPASS: the valid shape ---
        ("single dimension", _art("data_flow +0.5"), False),
        ("semicolon-joined pair", _art("data_flow +0.5; framework_idioms +0.5"), False),
        ("underscore id", _art("architecture_quality +1.0"), False),
        ("negative delta", _art("simplicity -0.5"), False),
        ("integer delta", _art("credibility +1"), False),
        ("extra whitespace around the join", _art("  data_flow +0.5 ;  simplicity +0.5  "), False),
        # --- BYPASS: out of scope ---
        ("empty backlog", _art("irrelevant", backlog=[]), False),
        (
            "absent backlog key",
            {"schema_version": 4, "state": "CONTINUE", "scorecard": _scorecard()},
            False,
        ),
    ]
    # --- BYPASS: the schema_version floor. The v1-v3 fixture corpus carries prose
    # score_impact; G39 must not retroactively fail it.
    for sv in (1, 2, 3):
        cases.append(
            (
                f"prose below the v4 floor (schema_version {sv})",
                _art("Architecture quality + State management each +1.0", schema_version=sv),
                False,
            )
        )
    return cases


def _isolation(va, canon):
    """A score_impact value must not perturb gates that do not own it."""
    failures = []
    baseline_art = _art("data_flow +0.5")

    def verdict(art):
        out = []
        out += va.check_g21_scorecard(art)
        out += va.check_continue_backlog(art)
        return sorted(f"{i.rule}: {i.message}" for i in out)

    base = verdict(copy.deepcopy(baseline_art))
    for impact in (
        "Architecture quality + State management each +1.0",
        "simplicity -0.5",
        "data_flow +0.5; framework_idioms +0.5",
        "velocity +9.9",
    ):
        got = verdict(_art(impact))
        if got != base:
            failures.append(
                f"isolation: score_impact={impact!r} changed an unrelated gate's verdict\n"
                f"  baseline: {base}\n  got:      {got}"
            )
    return failures


def main() -> int:
    va = _load_validator()
    canon = load_canon(HERE.parent)
    failures = []
    triggers = 0

    for label, art, expect_fire in _cases():
        issues = va.check_g39_backlog_score_impact(copy.deepcopy(art), canon)
        fired = bool(issues)
        if expect_fire:
            triggers += 1
        if fired != expect_fire:
            failures.append(
                f"{label}: expected {'FIRE' if expect_fire else 'silence'}, "
                f"got {'FIRE' if fired else 'silence'}"
                + (f" ({issues[0].message})" if issues else "")
            )
        for i in issues:
            if i.rule != "G39":
                failures.append(f"{label}: emitted rule {i.rule!r}, expected 'G39'")

    failures += _isolation(va, canon)

    # Vacuity guard: a gate that stopped firing must not pass by doing nothing.
    if triggers == 0:
        failures.append("vacuity: no TRIGGER case present")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: G39 selftest — {len(_cases())} cases ({triggers} trigger), isolation clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
