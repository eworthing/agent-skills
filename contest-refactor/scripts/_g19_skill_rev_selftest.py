#!/usr/bin/env python3
"""Self-test: G19's `skill_rev` sub-check (schema_version >= 4).

`skill_rev` is the only field identifying WHICH RULESET produced an artifact.
`schema_version` is the artifact format and `source_rev` is the target repo;
neither pins the rules the loop obeyed. Production motivation: 29 commits landed
on this skill between two runs against the same target repo, and three
conclusions drawn from comparing those runs were wrong until the commit
timestamps were hand-correlated against the loop timestamps.

The check is deliberately TYPE-only, not presence: a validator reading an
artifact cannot distinguish "the emitting version omitted it" from "this run
predates the field", so presence is a Step -1 emit obligation (startup.md).
These cases pin that asymmetry so a later reader does not "tighten" it into a
presence check and break every pre-existing v4 artifact.

Run: python3 scripts/_g19_skill_rev_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_g19_skill_rev", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base(**overrides) -> dict:
    """A v4 artifact that is otherwise G19-clean, so only skill_rev can fire."""
    artifact = {
        "schema_version": 4,
        "provider": "claude_code",
        "loop_model": "claude-sonnet-5",
        "loop_model_source": "default",
        "reviewer_model": "claude-sonnet-5",
        "reviewer_model_source": "default",
        "spawn_isolation": "subagent",
    }
    artifact.update(overrides)
    return artifact


def _skill_rev_issues(va, artifact: dict) -> list[str]:
    return [
        i.message for i in va.check_g19_provider_model(artifact) if "skill_rev" in i.message
    ]


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    # --- BYPASS: the field is absent entirely (every pre-existing v4 artifact). ---
    if _skill_rev_issues(va, _base()):
        failures.append("absent skill_rev fired G19 — presence must NOT be enforced on read")

    # --- BYPASS: a real short SHA. ---
    if _skill_rev_issues(va, _base(skill_rev="2b81c10")):
        failures.append("valid short SHA '2b81c10' rejected")

    # --- BYPASS: explicit null (skill is not a git checkout). ---
    if _skill_rev_issues(va, _base(skill_rev=None)):
        failures.append("explicit null rejected — null is the documented not-a-checkout value")

    # --- BYPASS: below the v4 floor, the field is not validated at all. ---
    if _skill_rev_issues(va, _base(schema_version=3, skill_rev=12345)):
        failures.append("schema_version 3 validated skill_rev — the floor is v4")

    # --- TRIGGER: empty string is not a SHA. Distinct from null, which is legal. ---
    if not _skill_rev_issues(va, _base(skill_rev="")):
        failures.append("empty-string skill_rev accepted; only null may mean 'no checkout'")

    # --- TRIGGER: wrong type. Guards against writing the whole rev-parse result object. ---
    if not _skill_rev_issues(va, _base(skill_rev=12345)):
        failures.append("non-string skill_rev accepted")
    if not _skill_rev_issues(va, _base(skill_rev={"sha": "2b81c10"})):
        failures.append("dict skill_rev accepted")

    # --- ISOLATION: skill_rev never perturbs the provider/model verdict. ---
    # Same artifact, three skill_rev values; the non-skill_rev issues must be identical.
    broken = {"provider": "unknown", "spawn_isolation": "subagent"}  # a real G19 violation
    baselines = set()
    for rev in (None, "2b81c10", ""):
        others = tuple(
            sorted(
                i.message
                for i in va.check_g19_provider_model(_base(skill_rev=rev, **broken))
                if "skill_rev" not in i.message
            )
        )
        baselines.add(others)
    if len(baselines) != 1:
        failures.append("skill_rev changed the provider/model verdict; the checks must be disjoint")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: G19 type-checks skill_rev at v4+ (absent/null/SHA pass; empty/non-string fire), "
        "below v4 it is unvalidated, and it never perturbs the provider/model verdict"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
