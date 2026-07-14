#!/usr/bin/env python3
"""Self-test: G16 mechanical duplicate-`stable_id` detection in findings_registry.json.

Before this check existed, two `entries[]` sharing a `stable_id` passed validation
silently: `_occurrences_for()` returns the first match and G30's disposition map
(a dict keyed on `stable_id`) keeps the last, so per-finding retirement and
oscillation ran on incomplete occurrence history with no validator complaint.
G16 ("Registry consistency") was a manual checklist only; this gives it its first
mechanical enforcement.

Run: python3 scripts/_g16_uniqueness_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_g16", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    # None registry (schema_version 1) → no issue, no crash.
    if va.check_g16_registry_uniqueness(None):
        failures.append("None registry should yield no G16 issue")

    # Unique stable_ids → clean.
    clean = {"entries": [{"stable_id": "F-001"}, {"stable_id": "F-002"}]}
    if va.check_g16_registry_uniqueness(clean):
        failures.append("unique stable_ids flagged as duplicate")

    # Duplicate stable_id → G16 fires.
    dup = {"entries": [{"stable_id": "F-007"}, {"stable_id": "F-007"}]}
    dup_rules = [i.rule for i in va.check_g16_registry_uniqueness(dup)]
    if "G16" not in dup_rules:
        failures.append("duplicate stable_id 'F-007' did not fire G16")

    # TWO entries missing stable_id must NOT collide — this proves the
    # `if sid is None: continue` skip guard. With one id-less entry a lone None
    # can't self-collide, so the test would pass even if the guard were deleted;
    # two id-less entries would both map to None and false-fire G16 without it.
    two_missing = {"entries": [{"title": "a"}, {"title": "b"}]}
    try:
        if va.check_g16_registry_uniqueness(two_missing):
            failures.append("two id-less entries false-fired G16 (None-skip guard missing?)")
    except Exception as exc:
        failures.append(f"id-less entries crashed: {exc!r}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: G16 fires on duplicate stable_id, clean on unique, id-less entries skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
