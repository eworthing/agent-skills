#!/usr/bin/env python3
"""Self-test for G40 — Discovery persistence across loops.

Step-0 Discovery is the durable handoff: it carries the source roots, the lens, and —
critically — the test AND build commands that every later loop re-runs as ground truth.
The schema used to say "required first loop only; null on later loops" while three
consumers were already written against the opposite assumption (rule #27's test_scope
coherence, G21's incremental->full reverify, and candidate_fingerprint.py's binding of
lens + source_roots). A 10-loop production run nulled it from loop 2 on, obeying the
schema, and nothing caught it because nothing checked.

This test pins five things against the REAL gate function in validate-artifact.py:

  1. TRIGGER    — G40 fires on a null/absent/empty discovery and on each individual
                  load-bearing field being missing, blank, or the wrong type.
  2. REGRESSION — the exact production shape (schema_version 4, loop > 1, discovery
                  null) fires. This is the case the old schema comment actively
                  instructed loops to produce, so it gets its own guard rather than
                  hiding inside the generic TRIGGER set.
  3. BYPASS     — G40 stays silent on a fully populated discovery at loop 1 AND at a
                  later loop (the carry-forward case this change exists to make legal),
                  tolerates extra/unknown discovery keys, and stays below the
                  schema_version 4 floor. The v1-v3 corpus has 13 artifacts with
                  late-loop null discovery; retroactively failing them would be a
                  regression in this gate, not a finding about them.
  4. ISOLATION  — a discovery value never changes an unrelated gate's verdict,
                  mirroring _g39_selftest.py / _metric_isolation_selftest.py.
  5. VACUITY    — at least one TRIGGER case exists, so a gate that silently stopped
                  firing cannot pass by doing nothing.

No pytest in this repo -> standalone _*.py helper.

Run: python3 scripts/_g40_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_g40", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _discovery(**overrides):
    """A fully populated Step-0 discovery object; overrides may drop or corrupt fields.

    Passing a field as `...` deletes it, so a case can test 'key absent' distinctly
    from 'key present but empty'.
    """
    base = {
        "source_roots": ["src/"],
        "test_command": "make test",
        "build_command": "make build",
        "lens": "Generic",
        "adrs": [],
        "domain_terms": [],
        "test_scope": "full",
        "test_filter": None,
        "working_tree_dirty_paths": [],
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not ...}


def _art(discovery, *, schema_version=4, loop=1):
    return {
        "schema_version": schema_version,
        "state": "CONTINUE",
        "loop": loop,
        "discovery": discovery,
        "backlog": [
            {
                "priority": 1,
                "title": "t",
                "kind": "structural",
                "why_it_matters": "w",
                "score_impact": "data_flow +0.5",
            }
        ],
        "scorecard": {d: {"score": 7.0} for d in DIMS},
    }


# (label, artifact, expect_fire)
def _cases():
    cases = [
        # --- TRIGGER: the object itself ---
        ("discovery null", _art(None), True),
        ("discovery absent", {"schema_version": 4, "state": "CONTINUE", "loop": 3}, True),
        ("discovery empty dict", _art({}), True),
        ("discovery not a dict", _art("see loop 1"), True),
        ("discovery is a list", _art([{"source_roots": ["src/"]}]), True),
        # --- TRIGGER: individual load-bearing fields ---
        ("source_roots absent", _art(_discovery(source_roots=...)), True),
        ("source_roots empty list", _art(_discovery(source_roots=[])), True),
        ("source_roots all blank", _art(_discovery(source_roots=["", "  "])), True),
        ("source_roots not a list", _art(_discovery(source_roots="src/")), True),
        ("test_command absent", _art(_discovery(test_command=...)), True),
        ("test_command blank", _art(_discovery(test_command="   ")), True),
        ("test_command not a string", _art(_discovery(test_command=["make", "test"])), True),
        ("lens absent", _art(_discovery(lens=...)), True),
        ("lens blank", _art(_discovery(lens="")), True),
        ("lens not a string", _art(_discovery(lens=0)), True),
        # --- REGRESSION: the exact production failure ---
        # schema_version 4, loop > 1, discovery null. The pre-G40 schema comment told
        # loops to emit precisely this, so it must fire loudly and unambiguously.
        ("REGRESSION: v4 later loop with null discovery", _art(None, loop=7), True),
        # --- BYPASS: the valid shape, at both loop positions ---
        ("populated at loop 1", _art(_discovery()), False),
        ("populated at a later loop (carry-forward)", _art(_discovery(), loop=7), False),
        ("populated at the loop cap", _art(_discovery(), loop=10), False),
        (
            "incremental scope still passes",
            _art(_discovery(test_scope="incremental", test_filter="ArtworkTests")),
            False,
        ),
        (
            "unknown extra discovery keys tolerated",
            _art(_discovery(churn_top20=[{"path": "a.py", "edits": 3}], prior_audit_docs=[])),
            False,
        ),
        (
            "build_command absent is NOT a G40 failure",
            # Deliberate: not every stack has a build step distinct from its test step,
            # so gating on build_command would fire on honest single-command repos.
            # rule #32 still asks the loop to carry whatever Step 0 recorded.
            _art(_discovery(build_command=...)),
            False,
        ),
    ]
    # --- BYPASS: the schema_version floor. 13 v1-v3 fixtures carry late-loop null
    # discovery because the old schema mandated it; G40 must not retroactively fail them.
    for sv in (1, 2, 3):
        cases.append(
            (
                f"null discovery below the v4 floor (schema_version {sv})",
                _art(None, schema_version=sv, loop=6),
                False,
            )
        )
    return cases


def _isolation(va):
    """A discovery value must not perturb gates that do not own it."""
    failures = []

    def verdict(art):
        out = []
        out += va.check_g21_scorecard(art)
        out += va.check_continue_backlog(art)
        return sorted(f"{i.rule}: {i.message}" for i in out)

    base = verdict(_art(_discovery()))
    for label, discovery in (
        ("null", None),
        ("empty", {}),
        ("no test_command", _discovery(test_command=...)),
        ("apple lens", _discovery(lens="Apple", source_roots=["Sources/"])),
    ):
        got = verdict(_art(discovery))
        if got != base:
            failures.append(
                f"isolation: discovery={label} changed an unrelated gate's verdict\n"
                f"  baseline: {base}\n  got:      {got}"
            )
    return failures


def main() -> int:
    va = _load_validator()
    failures = []
    triggers = 0
    saw_regression_case = False

    for label, art, expect_fire in _cases():
        if label.startswith("REGRESSION:"):
            saw_regression_case = True
        issues = va.check_g40_discovery_persistence(copy.deepcopy(art))
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
            if i.rule != "G40":
                failures.append(f"{label}: emitted rule {i.rule!r}, expected 'G40'")

    failures += _isolation(va)

    # Vacuity guards: a gate that stopped firing must not pass by doing nothing, and the
    # production regression case must not be quietly deleted from the corpus.
    if triggers == 0:
        failures.append("vacuity: no TRIGGER case present")
    if not saw_regression_case:
        failures.append(
            "vacuity: the 'REGRESSION: v4 later loop with null discovery' case is gone — "
            "that is the exact shape the pre-G40 schema produced and it must stay covered"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: G40 selftest — {len(_cases())} cases ({triggers} trigger), isolation clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
