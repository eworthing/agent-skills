#!/usr/bin/env python3
"""Self-test: audit_boundaries.py flags real first-party import cycles and stays
silent on the false-positive classes a line-regex parser would trip on.

No pytest in this repo (pyproject configures only ruff), so this standalone check
builds throwaway fixture repos in a tempdir, runs the audit CLI as a subprocess, and
asserts on its stdout. "circular" appearing in stdout == a candidate finding emitted.

FLAG fixtures (must emit a cycle):
  - 2-package cycle a <-> b
  - 3-package cycle a -> b -> c -> a (exercises SCC, not just a direct pair)

RESTRAINT fixtures (must stay silent — these are exactly what a naive
`grep -E "^(from|import)"` cross-reference would mis-flag):
  - one-way multi-line import
  - one-way aliased import
  - back-edge that lives only in a test file (excluded tree)
  - back-edge in a generated file (_pb2.py / @generated)
  - "import a" appearing only in a comment / string literal
  - first-party pkg importing the stdlib (no first-party cycle)

Run: python3 scripts/_audit_boundaries_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT = Path(__file__).with_name("audit_boundaries.py")


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


def _run(root: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(AUDIT), str(root)],
        capture_output=True,
        text=True,
    )
    return proc.stdout


# name -> (files, expect_cycle)
FIXTURES: dict[str, tuple[dict[str, str], bool]] = {
    "flag-2-cycle": (
        {
            "a/__init__.py": "",
            "a/mod.py": "from b import helper\n",
            "b/__init__.py": "",
            "b/mod.py": "import a.mod\n",
        },
        True,
    ),
    "flag-3-cycle": (
        {
            "a/__init__.py": "from b import x\n",
            "b/__init__.py": "from c import y\n",
            "c/__init__.py": "from a import z\n",
        },
        True,
    ),
    "restraint-oneway-multiline": (
        {
            "a/__init__.py": "",
            "a/mod.py": "from b import (\n    one,\n    two,\n    three,\n)\n",
            "b/__init__.py": "",
            "b/mod.py": "VALUE = 1\n",  # b does NOT import a
        },
        False,
    ),
    "restraint-oneway-aliased": (
        {
            "a/__init__.py": "",
            "a/mod.py": "import b.deep.thing as t\nfrom b import x as y\n",
            "b/__init__.py": "",
            "b/deep/__init__.py": "",
            "b/deep/thing.py": "x = 1\n",
        },
        False,
    ),
    "restraint-test-only-backedge": (
        {
            "a/__init__.py": "from b import x\n",  # prod edge a -> b
            "b/__init__.py": "y = 1\n",
            "b/tests/test_b.py": "import a\n",  # back-edge ONLY in a test file
        },
        False,
    ),
    "restraint-generated-backedge": (
        {
            "a/__init__.py": "from b import x\n",  # prod edge a -> b
            "b/__init__.py": "y = 1\n",
            "b/wire_pb2.py": "import a  # generated\n",  # back-edge in generated file
        },
        False,
    ),
    "restraint-comment-and-string": (
        {
            "a/__init__.py": "from b import x\n",  # prod edge a -> b
            "b/__init__.py": (
                "# import a  (mentioned in a comment, not a real import)\n"
                'DOC = "from a import nothing"\n'  # mention in a string literal
            ),
        },
        False,
    ),
    "restraint-stdlib-only": (
        {
            "a/__init__.py": "import os\nimport sys\nfrom b import x\n",
            "b/__init__.py": "import json\n",  # only stdlib; no edge back to a
        },
        False,
    ),
}


def _filters_independently() -> list[str]:
    """Pin `_is_test_file` and `IGNORE_DIRS` SEPARATELY.

    They mask each other through the combined walk: a test file usually also sits
    under a `tests/` directory, so disabling `_is_test_file` entirely still passed
    (IGNORE_DIRS caught the files), and emptying IGNORE_DIRS also passed (the
    filename check caught them back). Each filter was therefore unproven while the
    pair looked covered. These assertions call each filter directly, so neither can
    hide behind the other. `repo_map.py` and `audit_suppressions.py` both import
    these as a single source of truth, so a hole here is a hole in three tools.
    """
    import audit_boundaries as ab

    out: list[str] = []
    for name, expected in (
        ("test_thing.py", True),
        ("thing_test.py", True),
        ("thing.py", False),
        ("contest_helper.py", False),  # substring 'test' must not match
        ("latest_test.py", True),
    ):
        if ab._is_test_file(name) is not expected:
            out.append(f"_is_test_file({name!r}) != {expected}")
    for d in ("__pycache__", ".git", "node_modules", ".venv"):
        if d not in ab.IGNORE_DIRS:
            out.append(f"IGNORE_DIRS lost {d!r}")
    if not ab.IGNORE_DIRS:
        out.append("IGNORE_DIRS is empty -- the directory filter excludes nothing")
    return out


def main() -> int:
    if not AUDIT.is_file():
        print(f"FAIL: audit script missing: {AUDIT}")
        return 1

    failures: list[str] = []
    failures.extend(_filters_independently())
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for name, (files, expect_cycle) in FIXTURES.items():
            root = base / name
            _write(root, files)
            out = _run(root)
            flagged = "circular" in out
            if flagged != expect_cycle:
                verb = "expected a cycle, got none" if expect_cycle else "false-positive cycle"
                failures.append(f"{name}: {verb}\n--- stdout ---\n{out.rstrip()}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    flags = sum(1 for _, exp in FIXTURES.values() if exp)
    restraints = len(FIXTURES) - flags
    print(
        f"OK: audit_boundaries — {flags} flag fixture(s) emit cycles, "
        f"{restraints} restraint fixture(s) stay silent"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
