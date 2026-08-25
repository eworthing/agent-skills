#!/usr/bin/env python3
"""Self-test: _fs_filters.py — the shared first-party path/test/generated filters.

Pins the RED cases from the BenchHype coverage-ledger leak (contest-refactor
avalanche plan, Phase 0): hidden build/tooling trees excluded, the migrations
exact-case carve-out preserved in both directions, and a test-directory hit
that a filename-suffix check alone would miss.

Run: python3 scripts/_fs_filters_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _fs_filters as ff


def _parts(p: str) -> tuple[str, ...]:
    return PurePosixPath(p).parts


def main() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    check(
        ff.is_ignored_path(_parts(".artifacts/DerivedData/x/GeneratedAssetSymbols.swift")),
        "hidden .artifacts/ tree must be ignored",
    )
    check(ff.is_ignored_path(_parts(".swiftpm/x.swift")), "hidden .swiftpm/ tree must be ignored")
    check(
        not ff.is_ignored_path(_parts("Sources/App/Migrations/SchemaV1.swift")),
        "capitalized Migrations/ is hand-written source and must be discovered",
    )
    check(
        ff.is_ignored_path(_parts("migrations/0001_initial.py")),
        "lowercase migrations/ (Django-style generated) must be ignored",
    )

    tests_dir_path = _parts("Tests/Foo/StarterSoundFixtures.swift")
    check(
        ff.is_ignored_path(tests_dir_path),
        "the Tests/ directory component must exclude this path",
    )
    check(
        not ff.is_test_file(tests_dir_path[-1]),
        "StarterSoundFixtures.swift must NOT match the filename-suffix test filter -- "
        "exclusion above comes from the Tests/ directory check, not this one",
    )

    got = ff.normalize_roots(["b/", "a", "a"])
    check(
        got == ["a", "b"],
        f"normalize_roots must sort+dedupe+strip trailing slash, got {got}",
    )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: _fs_filters — hidden-dir rule, migrations carve-out, root normalization")
    return 0


if __name__ == "__main__":
    sys.exit(main())
