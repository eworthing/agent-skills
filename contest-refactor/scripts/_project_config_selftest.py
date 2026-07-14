#!/usr/bin/env python3
"""Self-test: `.contest-refactor.toml` loader fails loud on any unloadable input,
and the `--json` output write reports a clean error instead of a raw traceback.

CLI contracts the plain fixture harness (validate-fixtures.py) cannot assert,
because it inspects only exit code + gate ids, not stderr:

- A present-but-unloadable `.contest-refactor.toml` — bad TOML syntax OR non-UTF-8
  encoding (UnicodeDecodeError is a ValueError, not TOMLDecodeError/OSError, so a
  narrow except misses it) — must abort as a clean operator error: exit 2,
  `error: ... malformed .contest-refactor.toml` on stderr, no `Traceback`. It
  must NOT be swallowed to None (which used to let HALT_SUCCESS / G22 / G28 skip
  their strict branch).
- `--json <unwritable-path>` must exit 2 with a clean `error:` on stderr.

Exit 2 (not 1) is deliberate: an unloadable config is a "cannot run" operator
error — the same class as `not a directory` — distinct from strict-mode's exit 1
("ran; artifact had findings"). It therefore exits 2 regardless of `--mode`.

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

# ASCII content encoded UTF-16 begins with a BOM (0xFF 0xFE) that is invalid
# UTF-8, so tomllib's strict decode raises UnicodeDecodeError deterministically.
NON_UTF8_TOML = '[x]\ny = "z"\n'.encode("utf-16")


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
        # Pin to root's OWN file (candidates[0]); "some dict" would pass even if a
        # regression bound to an ancestor config instead.
        if loaded != {"accepted_residuals": {}}:
            failures.append(f"valid config should load root's own file, got {loaded!r}")

    # Both unloadable kinds must raise (fail loud), not return.
    for label, writer in (
        ("malformed TOML", lambda p: p.write_text("this = = broken\n", encoding="utf-8")),
        ("non-UTF-8", lambda p: p.write_bytes(NON_UTF8_TOML)),
    ):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            writer(root / ".contest-refactor.toml")
            try:
                va._load_project_config(root)
                failures.append(f"{label} config should raise, returned instead")
            except SystemExit:
                pass
            except Exception as exc:
                failures.append(f"{label} config raised non-SystemExit: {exc!r}")

    # --- CLI contract: unloadable config → exit 2, pinned error, no traceback ---
    for label, content in (
        ("malformed-toml", b"nope = = nope\n"),
        ("non-utf8", NON_UTF8_TOML),
    ):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "CURRENT_REVIEW.json").write_text("{}", encoding="utf-8")
            (root / ".contest-refactor.toml").write_bytes(content)
            proc = _run(str(root))
            if proc.returncode != 2:
                failures.append(f"{label} config: exit {proc.returncode}, expected 2")
            # Pin to the specific diagnostic, not a bare 'error:' (an Issue message
            # could contain 'error:' and false-GREEN a swallow regression).
            if "malformed .contest-refactor.toml" not in proc.stderr:
                failures.append(f"{label} config: missing pinned diagnostic on stderr")
            if "Traceback" in proc.stderr:
                failures.append(f"{label} config: raw traceback leaked to stderr")

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
    print("OK: unloadable config (bad TOML or non-UTF-8) exits 2 clean; --json write guarded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
