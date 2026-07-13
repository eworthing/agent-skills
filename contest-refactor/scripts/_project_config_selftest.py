#!/usr/bin/env python3
"""Self-test: `.contest-refactor.toml` loader fails loud on malformed input, and
the `--json` output write reports a clean error instead of a raw traceback.

Two CLI contracts the plain fixture harness (validate-fixtures.py) cannot assert,
because it inspects only exit code + gate ids, not stderr:

- A present-but-malformed `.contest-refactor.toml` must abort loudly (non-zero
  exit, `error:` on stderr, no `Traceback`) instead of being swallowed to None —
  which used to let HALT_SUCCESS / G22 / G28 skip their strict branch.
- `--json <unwritable-path>` must exit 2 with a clean `error:` on stderr, not a
  raw `FileNotFoundError` traceback.

Isolated: every fixture lives under a fresh TemporaryDirectory (below $TMPDIR,
outside this git repo), so `_load_project_config`'s ancestor walk cannot bind to
the enclosing repository's own config.

Run: python3 scripts/_project_config_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

VALIDATOR = Path(__file__).with_name("validate-artifact.py")


def _load_validator():
    spec = importlib.util.spec_from_file_location("_va_cfg", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    # --- direct loader unit tests ---
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        if va._load_project_config(root) is not None:
            failures.append("absent config should load as None")
        (root / ".contest-refactor.toml").write_text("[accepted_residuals]\n", encoding="utf-8")
        loaded = va._load_project_config(root)
        if not isinstance(loaded, dict):
            failures.append(f"valid config should load as dict, got {type(loaded)}")

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / ".contest-refactor.toml").write_text("this = = broken\n", encoding="utf-8")
        try:
            va._load_project_config(root)
            failures.append("malformed config should raise, returned instead")
        except SystemExit:
            pass  # expected: fail loud
        except Exception as exc:
            failures.append(f"malformed config raised non-SystemExit: {exc!r}")

    # --- CLI contract: malformed config → loud, no traceback ---
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "CURRENT_REVIEW.json").write_text("{}", encoding="utf-8")
        (root / ".contest-refactor.toml").write_text("nope = = nope\n", encoding="utf-8")
        proc = _run(str(root))
        if proc.returncode == 0:
            failures.append("malformed config: CLI exited 0 (should be non-zero)")
        if "error:" not in proc.stderr:
            failures.append("malformed config: no 'error:' diagnostic on stderr")
        if "Traceback" in proc.stderr:
            failures.append("malformed config: raw traceback leaked to stderr")

    # --- CLI contract: unwritable --json path → exit 2, no traceback ---
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "CURRENT_REVIEW.json").write_text("{}", encoding="utf-8")
        missing = root / "nope" / "out.json"  # parent 'nope' does not exist
        proc = _run(str(root), "--json", str(missing))
        if proc.returncode != 2:
            failures.append(f"--json unwritable: exit {proc.returncode}, expected 2")
        if "error:" not in proc.stderr:
            failures.append("--json unwritable: no 'error:' diagnostic on stderr")
        if "Traceback" in proc.stderr:
            failures.append("--json unwritable: raw traceback leaked to stderr")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: malformed config fails loud (no traceback); --json write guarded (exit 2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
