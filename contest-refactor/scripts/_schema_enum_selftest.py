#!/usr/bin/env python3
"""Self-test: check_schema_enums per-element guard on findings[].

Before this guard, a single non-object entry in `findings[]` (string/number/None) raised
AttributeError from `finding.get(...)` and aborted validation instead of reporting a
schema-enum Issue, mirroring the G42 per-element idiom used elsewhere in this file.

Run: python3 scripts/_schema_enum_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _canon import load_canon
from _selftest_lib import load_validator as _load_validator


def main() -> int:
    va = _load_validator()
    canon = load_canon(HERE.parent)
    failures: list[str] = []

    art = {"schema_version": 4, "state": "CONTINUE", "findings": ["x"]}
    try:
        issues = va.check_schema_enums(art, canon)
    except Exception as exc:
        failures.append(f"non-object findings entry crashed: {exc!r}")
    else:
        if not any(i.rule == "schema-enum" for i in issues):
            failures.append(
                f"non-object findings entry did not fire a schema-enum Issue, got {issues}"
            )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: check_schema_enums per-element guard on findings[] holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
