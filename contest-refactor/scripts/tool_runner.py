#!/usr/bin/env python3
"""tool_runner.py — bounded deterministic-tool runner for Step 0 (main agent).

Backlog item 25, Half A. Design note:
analysis/contest-refactor/ITEM25-TOOL-SUBSTRATE-2026-08-19.md

WHY STEP 0 AND NOT THE LOOP. Analyzer output is attacker-influenceable
repository-derived text. Running the ladder in the main agent means that text is
never in a dispatched subagent's context at all -- only the sanitized summary
crosses the boundary. That is a structural control, stronger than any prose rule
about handling raw tool output, and it is also why this costs zero per-loop
tokens: startup.md is main-agent-only and outside the per-loop reload.

WHAT PERSISTS. Structured `(file, code)` pairs, counts, and a sha256 digest of
the raw output. Never the raw output, and never a tool's free-text message --
that is where both secrets and injected instructions live. This generalises the
existing redaction rule ("record file:line plus the credential's TYPE only --
never the value") from findings to analyzer output, and matches what tech-audit
derived independently: "reference the location only -- never quote the secret
value into the report ... (reports get committed/shared)".

SIX TYPED OUTCOMES, NONE SILENT. A tool that quietly did not run reads as a
clean result, so every way of not-running has its own name:

    ok                        ran; exit in findings_exit_codes
    absent                    binary not on PATH
    version_incompatible      present but below the pinned floor
    timed_out                 exceeded its ceiling; partial output DISCARDED
    partial                   parseable output + undocumented exit code
    skipped_no_redacted_mode  fails closed (item 25's inherited boundary)

Two of those carry the item and are separately selftested:

  * `absent` is NOT `clean`. It reports no findings count at all, because
    "not installed" summarised as "found nothing" is the survivor-metric hazard.
  * `timed_out` DISCARDS partial output -- no counts, no digest. A truncated
    stream is an unknown fraction of a result, not a smaller one, and a count
    taken from it reads as complete.

The runner REPORTS; it never gates. Exit 0 always, including when every tool is
absent. Exit 2 is plumbing (bad repo root). Exit 1 is deliberately unused --
there is no "measured failure" for a reporter, and reserving it keeps the 0/1/2
discipline consistent with exec_replay_grade.py.

Tool output is candidate evidence under `promotion_allowed: false`, like every
existing audit script: the Critic re-derives any judgment (method.md Meta-Rule 1).

Usage:
    tool_runner.py <repo-root> [--json PATH] [--quiet]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Reuse G44's credential shapes rather than growing a second implementation.
# _scan_line returns (pattern_name, transform) pairs and never the matched value,
# which is exactly the fail-closed primitive this needs.
from _artifact_credentials import _scan_line  # noqa: E402

# `path:line:col: CODE message` -- the shape ruff, mypy, swiftlint and most
# linters share. Only `file` and `code` are kept; `message` is dropped whole.
_HIT_RE = re.compile(r"^(?P<file>[^\s:]+):\d+:\d+:\s+(?P<code>[A-Za-z]+\d+)\b")

# Instruction-shaped text in analyzer output is payload under G14, never a
# command. Counted so the coverage line can disclose it; never reproduced.
_INJECTION_RE = re.compile(
    r"(?i)\b(?:ignore\s+(?:all\s+)?(?:previous|prior)|disregard\s+(?:all\s+)?prior"
    r"|score\s+this|you\s+are\s+now|new\s+instructions?|system\s+prompt)\b"
)

_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    argv: tuple[str, ...]
    findings_exit_codes: tuple[int, ...] = (0,)
    version_argv: tuple[str, ...] | None = None
    min_version: tuple[int, ...] | None = None
    timeout_s: int = 60
    has_redacted_mode: bool = True


@dataclass
class ToolResult:
    name: str
    outcome: str
    detail: str | None = None
    counts: dict[str, int] = field(default_factory=dict)
    digest: str | None = None
    hits: list[dict[str, str]] = field(default_factory=list)
    redactions: list[dict[str, str]] = field(default_factory=list)
    injection_markers: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "outcome": self.outcome,
            "detail": self.detail,
            "counts": self.counts,
            "digest": self.digest,
            "hits": self.hits,
            "redactions": self.redactions,
            "injection_markers": self.injection_markers,
        }


def _parse_version(text: str) -> tuple[int, ...] | None:
    m = _VERSION_RE.search(text or "")
    if not m:
        return None
    return tuple(int(g) for g in m.groups() if g is not None)


def _sanitize(raw: str) -> tuple[list[dict[str, str]], list[dict[str, str]], int]:
    """(hits, redactions, injection_markers) -- raw text is never returned."""
    hits: list[dict[str, str]] = []
    redactions: list[dict[str, str]] = []
    injections = 0
    for line in raw.splitlines():
        for name, transform in _scan_line(line):
            redactions.append({"pattern": name, "transform": transform})
        if _INJECTION_RE.search(line):
            injections += 1
        m = _HIT_RE.match(line)
        if m:
            hits.append({"file": m.group("file"), "code": m.group("code")})
    return hits, redactions, injections


def run_tool(spec: ToolSpec, cwd: Path) -> ToolResult:
    # Fail closed BEFORE running anything: a tool that cannot produce redactable
    # output is skipped and disclosed, never run and cleaned up afterwards.
    if not spec.has_redacted_mode:
        return ToolResult(spec.name, "skipped_no_redacted_mode", "no redacted output mode")

    if shutil.which(spec.argv[0]) is None and not Path(spec.argv[0]).is_file():
        return ToolResult(spec.name, "absent", f"{spec.argv[0]} not on PATH")

    if spec.version_argv and spec.min_version:
        try:
            probe = subprocess.run(
                list(spec.version_argv), capture_output=True, text=True, timeout=15, cwd=cwd
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return ToolResult(spec.name, "version_incompatible", f"version probe failed: {exc}")
        observed = _parse_version(probe.stdout + probe.stderr)
        if observed is None:
            return ToolResult(
                spec.name, "version_incompatible", "version probe returned no version"
            )
        if observed < spec.min_version:
            got = ".".join(str(n) for n in observed)
            want = ".".join(str(n) for n in spec.min_version)
            return ToolResult(
                spec.name, "version_incompatible", f"observed {got}, requires >= {want}"
            )

    try:
        proc = subprocess.run(
            list(spec.argv), capture_output=True, text=True, timeout=spec.timeout_s, cwd=cwd
        )
    except subprocess.TimeoutExpired:
        # Discard everything. A truncated stream is an unknown fraction of a
        # result; a count taken from it would read as complete.
        return ToolResult(spec.name, "timed_out", f"exceeded {spec.timeout_s}s ceiling")
    except OSError as exc:
        return ToolResult(spec.name, "absent", f"could not execute: {exc}")

    raw = proc.stdout or ""
    hits, redactions, injections = _sanitize(raw)
    outcome = "ok" if proc.returncode in spec.findings_exit_codes else "partial"
    detail = None if outcome == "ok" else f"undocumented exit {proc.returncode}"
    return ToolResult(
        name=spec.name,
        outcome=outcome,
        detail=detail,
        counts={"findings": len(hits)},
        digest="sha256:" + hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest(),
        hits=hits,
        redactions=redactions,
        injection_markers=injections,
    )


# Wired tools (item 25 slice A3). Deliberately small: every entry is a tool this
# repo already depends on or can prove absent cleanly. `absent` is a first-class,
# disclosed outcome, so an unlisted or uninstalled tool costs nothing.
DEFAULT_REGISTRY: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="ruff",
        argv=("ruff", "check", "--output-format", "concise", "."),
        findings_exit_codes=(0, 1),
        version_argv=("ruff", "--version"),
        min_version=(0, 15, 0),
        timeout_s=120,
    ),
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Step-0 bounded tool runner (reports; never gates)")
    ap.add_argument("repo_root", type=Path)
    ap.add_argument("--json", type=Path, default=None, help="write the sanitized summary here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if not args.repo_root.is_dir():
        sys.stderr.write(f"error: not a directory: {args.repo_root}\n")
        return 2

    results = [run_tool(spec, args.repo_root) for spec in DEFAULT_REGISTRY]
    payload = {
        "repo_root": str(args.repo_root),
        "promotion_allowed": False,
        "tools": [r.to_dict() for r in results],
    }
    if args.json is not None:
        try:
            args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"error: could not write --json output: {exc}\n")
            return 2
    if not args.quiet:
        for r in results:
            extra = f" findings={r.counts['findings']}" if "findings" in r.counts else ""
            flags = ""
            if r.redactions:
                flags += f" redacted={len(r.redactions)}"
            if r.injection_markers:
                flags += f" injection_markers={r.injection_markers}"
            print(
                f"[tool {r.name}] {r.outcome}{extra}{flags}{'' if not r.detail else ' — ' + r.detail}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
