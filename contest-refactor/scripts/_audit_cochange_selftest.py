#!/usr/bin/env python3
"""Self-test: audit_cochange.py mines git history for change-coupled, distant file pairs.

No pytest in this repo (pyproject configures only ruff), so this standalone check
creates throwaway temp git repos via subprocess + tempfile.TemporaryDirectory, runs the
audit CLI, and asserts on the JSON output.

Cases:
  1. co-changing distant pair  — src/orders/checkout.ts + src/billing/discount.ts edited
     together ≥3 times, far apart → must appear as a candidate pair
  2. restraint: same-module pair / single co-change / generated-file churn → NOT flagged
  3. Swift fixture: A/Foo.swift + B/Bar.swift co-changing → pair present,
     static_dependency == "unavailable"
  4. shallow clone OR no-.git dir → empty candidate list, exit 0, no crash

Run: python3 scripts/_audit_cochange_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT = Path(__file__).with_name("audit_cochange.py")

_GIT_ENV = {**os.environ,
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

# Inline identity flags passed to every git commit, following the
# _preflight_selftest.py pattern — avoids reliance on global git config.
_GIT_ID = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *_GIT_ID, *args], cwd=cwd, check=True,
                   capture_output=True, env=_GIT_ENV)


def _init(root: Path) -> None:
    subprocess.run(["git", *_GIT_ID, "init", "-q", str(root)],
                   check=True, capture_output=True, env=_GIT_ENV)


def _write_and_commit(root: Path, files: dict[str, str], msg: str) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    _git(["add", "-A"], cwd=root)
    _git(["commit", "-m", msg], cwd=root)


def _run(repo: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(AUDIT), str(repo), "--format", "json"]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True)


def _pairs_by_files(result: dict) -> dict[tuple[str, str], dict]:
    """Build a lookup keyed by (lhs, rhs) normalised as a sorted tuple."""
    out: dict[tuple[str, str], dict] = {}
    for p in result.get("pairs", []):
        key = tuple(sorted([p.get("lhs", ""), p.get("rhs", "")]))
        out[key] = p
    return out  # type: ignore[return-value]


def main() -> int:
    if not AUDIT.is_file():
        print(f"FAIL: audit_cochange.py missing: {AUDIT}")
        return 1

    failures: list[str] = []

    # ------------------------------------------------------------------ #
    # Case 1: co-changing distant pair flagged as a candidate             #
    # ------------------------------------------------------------------ #
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo1"
        root.mkdir()
        _init(root)

        # initial state
        _write_and_commit(root, {
            "src/orders/checkout.ts": "// checkout v0\n",
            "src/billing/discount.ts": "// discount v0\n",
            "src/orders/cart.ts": "// cart\n",
        }, "init")

        # 3 co-change commits for the distant pair
        for i in range(1, 4):
            _write_and_commit(root, {
                "src/orders/checkout.ts": f"// checkout v{i}\n",
                "src/billing/discount.ts": f"// discount v{i}\n",
            }, f"feat: sync checkout+discount v{i}")

        proc = _run(root)
        if proc.returncode != 0:
            failures.append(
                f"case1: expected exit 0, got {proc.returncode}\n{proc.stderr.rstrip()}"
            )
        else:
            try:
                result = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                failures.append(f"case1: invalid JSON output: {e}\n{proc.stdout[:300]}")
                result = {}
            pairs = _pairs_by_files(result)
            key = ("src/billing/discount.ts", "src/orders/checkout.ts")
            if key not in pairs:
                failures.append(
                    f"case1: expected pair {key} in candidates; got pairs: "
                    f"{list(pairs.keys())}\nfull output: {proc.stdout[:800]}"
                )

    # ------------------------------------------------------------------ #
    # Case 2: restraint — same-module / single co-change / lockfile churn #
    # ------------------------------------------------------------------ #
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo2"
        root.mkdir()
        _init(root)

        _write_and_commit(root, {
            "src/orders/checkout.ts": "// checkout\n",
            "src/orders/cart.ts": "// cart\n",
            "package-lock.json": '{"lockfileVersion": 1}\n',
        }, "init")

        # same-module pair: checkout + cart (same dir) — should NOT be flagged
        _write_and_commit(root, {
            "src/orders/checkout.ts": "// checkout v2\n",
            "src/orders/cart.ts": "// cart v2\n",
        }, "refactor: local renames in orders")

        # lockfile-only churn across 4 commits — should be ignored
        for i in range(1, 5):
            _write_and_commit(root, {
                "package-lock.json": f'{{"lockfileVersion": {i + 1}}}\n',
            }, "chore: update lockfile")

        # single co-change of a distant pair — below threshold → NOT flagged
        _write_and_commit(root, {
            "src/orders/checkout.ts": "// checkout v3\n",
            "src/billing/invoice.ts": "// invoice v1\n",
        }, "feat: add invoice once")

        proc = _run(root)
        if proc.returncode != 0:
            failures.append(
                f"case2: expected exit 0, got {proc.returncode}\n{proc.stderr.rstrip()}"
            )
        else:
            try:
                result = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                failures.append(f"case2: invalid JSON output: {e}\n{proc.stdout[:300]}")
                result = {}
            pairs = _pairs_by_files(result)
            # same-dir pair should not appear
            same_dir_key = ("src/orders/cart.ts", "src/orders/checkout.ts")
            if same_dir_key in pairs:
                failures.append(
                    f"case2: same-module pair {same_dir_key} should NOT be flagged; "
                    f"directory_distance must be > 0 for a candidate"
                )
            # single co-change should not appear
            single_key = ("src/billing/invoice.ts", "src/orders/checkout.ts")
            if single_key in pairs:
                failures.append(
                    f"case2: single-co-change pair {single_key} should NOT be flagged"
                )

    # ------------------------------------------------------------------ #
    # Case 3: Swift fixture → static_dependency == "unavailable"          #
    # ------------------------------------------------------------------ #
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo3"
        root.mkdir()
        _init(root)

        _write_and_commit(root, {
            "A/Foo.swift": "// Foo\n",
            "B/Bar.swift": "// Bar\n",
        }, "init")

        for i in range(1, 4):
            _write_and_commit(root, {
                "A/Foo.swift": f"// Foo v{i}\n",
                "B/Bar.swift": f"// Bar v{i}\n",
            }, f"feat: update Foo+Bar v{i}")

        proc = _run(root)
        if proc.returncode != 0:
            failures.append(
                f"case3: expected exit 0, got {proc.returncode}\n{proc.stderr.rstrip()}"
            )
        else:
            try:
                result = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                failures.append(f"case3: invalid JSON output: {e}\n{proc.stdout[:300]}")
                result = {}
            pairs = _pairs_by_files(result)
            key = ("A/Foo.swift", "B/Bar.swift")
            if key not in pairs:
                failures.append(
                    f"case3: Swift pair {key} should appear; got: {list(pairs.keys())}"
                )
            else:
                dep = pairs[key].get("static_dependency")
                if dep != "unavailable":
                    failures.append(
                        f"case3: static_dependency should be 'unavailable' for Swift, "
                        f"got {dep!r}"
                    )

    # ------------------------------------------------------------------ #
    # Case 4a: no .git dir → empty candidates, exit 0                     #
    # ------------------------------------------------------------------ #
    with tempfile.TemporaryDirectory() as td:
        nodir = Path(td) / "no_git"
        nodir.mkdir()
        (nodir / "some_file.py").write_text("x = 1\n", encoding="utf-8")

        proc = _run(nodir)
        if proc.returncode != 0:
            failures.append(
                f"case4a (no .git): expected exit 0, got {proc.returncode}\n"
                f"{proc.stderr.rstrip()}"
            )
        else:
            try:
                result = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                failures.append(f"case4a: invalid JSON output: {e}\n{proc.stdout[:300]}")
                result = {}
            if result.get("pairs"):
                failures.append(
                    f"case4a: no-.git dir should yield empty pairs, got: "
                    f"{result.get('pairs')}"
                )

    # ------------------------------------------------------------------ #
    # Case 4b: shallow clone → empty candidates, exit 0                   #
    # ------------------------------------------------------------------ #
    with tempfile.TemporaryDirectory() as td:
        origin = Path(td) / "origin"
        origin.mkdir()
        _init(origin)
        _write_and_commit(origin, {"hello.py": "x = 0\n"}, "init")
        for i in range(1, 4):
            _write_and_commit(origin, {"hello.py": f"x = {i}\n"}, f"update {i}")

        shallow = Path(td) / "shallow"
        subprocess.run(
            ["git", *_GIT_ID, "clone", "--depth=1", str(origin), str(shallow)],
            check=True, capture_output=True, env=_GIT_ENV,
        )

        proc = _run(shallow)
        if proc.returncode != 0:
            failures.append(
                f"case4b (shallow): expected exit 0, got {proc.returncode}\n"
                f"{proc.stderr.rstrip()}"
            )
        else:
            try:
                result = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                failures.append(f"case4b: invalid JSON output: {e}\n{proc.stdout[:300]}")
                result = {}
            if result.get("pairs"):
                failures.append(
                    f"case4b: shallow clone should yield empty pairs, got: "
                    f"{result.get('pairs')}"
                )

    # ------------------------------------------------------------------ #
    # Report                                                               #
    # ------------------------------------------------------------------ #
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "OK: audit_cochange — distant co-changing pair flagged; same-module/single-shot/"
        "lockfile NOT flagged; Swift pair has static_dependency=unavailable; "
        "shallow+no-.git yield empty candidates at exit 0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
