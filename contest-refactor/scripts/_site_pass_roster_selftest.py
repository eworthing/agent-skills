#!/usr/bin/env python3
"""Selftest for scripts/site_pass_roster.py (SITE-PASS plan W1). Run directly; exit 0 = pass.
Guards: the roster is the ledger's enumeration under --scope only (tests, vendor and
out-of-scope files excluded); byte-order sort; the documented digest encoding; exit 2 without
--scope, for a missing scope, and for a scope outside the repo root.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "site_pass_roster.py"
sys.path.insert(0, str(HERE))
import site_pass_roster as R


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=cwd
    )


def _repo() -> Path:
    root = Path(tempfile.mkdtemp())
    for rel in (
        "Kit/Sources/Feature/B.swift",
        "Kit/Sources/Feature/a.swift",
        "Kit/Sources/Feature/Sub/Z.swift",
        "Kit/Sources/Feature/FeatureTests.swift",
        "Kit/Sources/Feature/node_modules/x.swift",
        "Kit/Sources/Other/O.swift",
        "Kit/Tests/FeatureTests/T.swift",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("struct X {}\n")
    return root


def test_roster_contents_and_digest() -> None:
    root = _repo()
    r = R.build_roster(root, "Kit/Sources/Feature")
    assert r["scope"] == "Kit/Sources/Feature"
    assert r["paths"] == [
        "Kit/Sources/Feature/B.swift",
        "Kit/Sources/Feature/Sub/Z.swift",
        "Kit/Sources/Feature/a.swift",
    ], r["paths"]  # byte order: uppercase before lowercase; tests/vendor/out-of-scope excluded
    assert r["digest"] == hashlib.sha256("\n".join(r["paths"]).encode("utf-8")).hexdigest()
    assert R.roster_digest(r["paths"]) == r["digest"]


def test_cli_json_and_exit_codes() -> None:
    root = _repo()
    p = _run([".", "--scope", "Kit/Sources/Feature", "--json"], root)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out == R.build_roster(root, "Kit/Sources/Feature"), out
    assert _run([".", "--json"], root).returncode == 2, "no --scope must exit 2"
    assert _run([".", "--scope", "Kit/Sources/Nope", "--json"], root).returncode == 2
    assert _run([".", "--scope", "/", "--json"], root).returncode == 2, "scope outside root"
    assert _run(["/nonexistent-root", "--scope", "x", "--json"], root).returncode == 2


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print(f"PASS {_name}")
    print("site_pass_roster selftest: OK")
