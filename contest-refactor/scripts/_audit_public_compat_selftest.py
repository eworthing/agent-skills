#!/usr/bin/env python3
"""Selftest for audit-public-surface.sh --since (DD-07). Run directly; exit 0 = pass.

Guards the three properties the back-compat mode rests on: a vanished public
declaration reads `removed`, an edited one reads `changed` (its name comes back
on an added line), and an untouched one is silent. The last is the restraint
case -- a contract auditor that fires on every unchanged export is unusable.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "audit-public-surface.sh"
BEFORE = (
    'public struct Widget { public func render() -> String { "x" } }\n'
    "public func legacyHelper() {}\n"
    "public var knob: Int = 1\n"
)
AFTER = (
    'public struct Widget { public func render(scale: Int) -> String { "x" } }\n'
    "public var knob: Int = 1\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _run(repo: Path, rev: str) -> tuple[int, str]:
    p = subprocess.run(
        ["bash", str(SCRIPT), "--since", rev, str(repo)],
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout


def _fixture() -> Path:
    repo = Path(tempfile.mkdtemp(prefix="pubcompat-"))
    src = repo / "Sources" / "M"
    src.mkdir(parents=True)
    (src / "A.swift").write_text(BEFORE, encoding="utf-8")
    _git(repo, "init", "-q", ".")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    (src / "A.swift").write_text(AFTER, encoding="utf-8")
    return repo


def test_removed_changed_and_silent() -> None:
    code, out = _run(_fixture(), "HEAD")
    assert code == 0, f"audit helper must never gate: exit {code}"
    assert "| removed | `legacyHelper` |" in out, out
    assert "| changed | `Widget` |" in out, out
    # Restraint: `knob` is public and untouched. Any mention is a false positive.
    assert "knob" not in out, f"untouched public decl reported: {out}"


def test_unknown_revision_is_named_not_guessed() -> None:
    p = subprocess.run(
        ["bash", str(SCRIPT), "--since", "no-such-rev", str(_fixture())],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 2, p.returncode
    assert "unknown revision" in p.stderr, p.stderr


def test_enumeration_mode_still_runs() -> None:
    # The --since parsing must not have broken the original positional call.
    p = subprocess.run(["bash", str(SCRIPT), str(_fixture())], capture_output=True, text=True)
    assert p.returncode == 0, (p.returncode, p.stderr)


def test_deleted_file_attribution() -> None:
    repo = Path(tempfile.mkdtemp(prefix="pubcompat-del-"))
    src = repo / "Sources" / "M"
    src.mkdir(parents=True)
    (src / "A.swift").write_text("public func stillHere() {}\n", encoding="utf-8")
    (src / "B.swift").write_text("public func deletedFunc() {}\n", encoding="utf-8")
    _git(repo, "init", "-q", ".")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    (src / "B.swift").unlink()
    code, out = _run(repo, "HEAD")
    assert code == 0, f"audit helper must never gate: exit {code}"
    # A deleted file (+++ /dev/null) must not inherit the previous file's path.
    assert "| removed | `deletedFunc` | Sources/M/B.swift |" in out, out


def test_enumeration_widened_modifiers() -> None:
    repo = Path(tempfile.mkdtemp(prefix="pubcompat-enum-"))
    src = repo / "Sources" / "M"
    src.mkdir(parents=True)
    (src / "Foo.swift").write_text(
        "open class BarThing {}\n"
        "public final class FinalThing {}\n"
        "@objc public func annotatedFn() {}\n",
        encoding="utf-8",
    )
    p = subprocess.run(["bash", str(SCRIPT), str(repo)], capture_output=True, text=True)
    assert p.returncode == 0, (p.returncode, p.stderr)
    assert "| BarThing |" in p.stdout, p.stdout
    assert "| FinalThing |" in p.stdout, p.stdout
    assert "| annotatedFn |" in p.stdout, p.stdout


def test_enumeration_symbol_extraction() -> None:
    repo = Path(tempfile.mkdtemp(prefix="pubcompat-sym-"))
    src = repo / "Sources" / "M"
    src.mkdir(parents=True)
    (src / "Foo.swift").write_text("public static func foo() {}\n", encoding="utf-8")
    p = subprocess.run(["bash", str(SCRIPT), str(repo)], capture_output=True, text=True)
    assert p.returncode == 0, (p.returncode, p.stderr)
    # A multi-keyword decl must extract the real symbol, not the kind keyword.
    assert "| foo |" in p.stdout, p.stdout
    assert "| func |" not in p.stdout, p.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("audit-public-surface --since selftest: OK")
