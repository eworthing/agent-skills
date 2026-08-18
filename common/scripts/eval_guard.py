#!/usr/bin/env python3
"""
eval_guard.py — repo-wide "eval-guard" gate.

Rule: a substantive change to a skill's SKILL.md or references/*.md must
either (a) touch that skill's evals/ or tests/ directory, or add/modify a
scripts/_*selftest*.py (or scripts/*_selftest.py) file — this repo's
convention for deterministic prose guards, see CLAUDE.md — in the same
change, or (b) carry an `Eval-waiver: <reason>` commit trailer.

"Substantive" is mechanical, not semantic: the diff reaches beyond the
YAML frontmatter block and beyond whitespace-only edits. Frontmatter
tweaks (bumping a field, editing allowed-tools) and pure reformatting
don't count — see is_substantive_change(). Additions and deletions fall
out of the same rule for free: an addition's old side is empty, a
deletion's new side is empty, and neither can equal a non-trivial body
after stripping frontmatter/whitespace, so a real prose deletion is
always flagged without any special-casing.

Three-part contract (this repo commits straight to main; there is no PR
gate to lean on, so the checker runs at three points):

  1. pre-commit (--staged)          — catches the common path early.
     Advisory ONLY, always exits 0: git invokes pre-commit *before*
     obtaining the commit message, so this mode structurally cannot see
     an `Eval-waiver:` trailer and must never block on its absence.
  2. commit-msg (--commit-msg FILE) — the real local gate. By now both
     the staged diff and the drafted message (with any trailer) exist,
     so REPORT_ONLY / --enforce takes effect here.
  3. CI (--range A..B)              — catches anything that bypassed
     1/2 (--no-verify, hooksPath never configured, ...) after it has
     landed. Same REPORT_ONLY / --enforce flip, checked against the
     landed diff and the landed commits' trailers.

Containment step on a red CI check: revert the offending commit, or land
an immediate follow-up commit (an empty commit is fine) that either adds
the missing eval/test coverage or adds a properly formatted
`Eval-waiver: <reason>` trailer. See docs in common/README.md.

Report-only (this change): every failure path prints a loud warning and
exits 0 — it never blocks. Flip REPORT_ONLY to False below (or pass
--enforce) to make --commit-msg / --range actually block. --staged is
exempt from the flip for the structural reason above.

Exit codes (before the report-only downgrade):
    0 — pass.
    1 — fail: a substantive change with no eval/test touch and no valid
        waiver.
    2 — plumbing error (bad args, git command failed, missing file, ...).

Usage:
    eval_guard.py --staged [--repo PATH]
    eval_guard.py --commit-msg <path-to-drafted-message> [--repo PATH]
    eval_guard.py --range <a>..<b> [--repo PATH]
    (append --enforce to flip out of report-only for --commit-msg/--range)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ── The flip switch ─────────────────────────────────────────────────────
# Change to False (or pass --enforce) to make --commit-msg / --range
# blocking. This is the ONE place that decision is made; hooks and CI in
# this change call the script without --enforce, so they inherit this
# constant automatically.
REPORT_ONLY = True

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_PLUMBING_ERROR = 2

PROSE_RE = re.compile(r"^(?P<skill>[^/]+)/(?:SKILL\.md|references/.+\.md)$")
FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n?", re.DOTALL)
# scripts/_*selftest*.py or scripts/*_selftest.py — this repo's convention for a
# deterministic guard that isn't an evals/ or tests/ dir (see CLAUDE.md).
SELFTEST_RE = re.compile(
    r"^(?P<skill>[^/]+)/scripts/(?:_[^/]*selftest[^/]*\.py|[^/]*_selftest\.py)$"
)
WAIVER_KEY = "Eval-waiver"
WAIVER_TRAILER_RE = re.compile(r"^([A-Za-z][\w-]*):\s?(.*)$")


class GitError(RuntimeError):
    """A git subprocess call failed outright (plumbing error, exit 2)."""


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, errors="replace"
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _git_show(ref_and_path: str, cwd: Path) -> str:
    """Content at <ref>:<path> (or `:<path>` for the staged index). "" if absent."""
    result = subprocess.run(
        ["git", "show", ref_and_path], cwd=cwd, capture_output=True, text=True, errors="replace"
    )
    return result.stdout if result.returncode == 0 else ""


def _content_at(ref: str | None, path: str, cwd: Path) -> str:
    spec = f":{path}" if ref is None else f"{ref}:{path}"
    return _git_show(spec, cwd)


def _parse_name_status_z(output: str) -> list[tuple[str, str, str | None]]:
    """Parse `git diff --name-status -M -z` into (status, path, old_path) tuples.

    old_path is set only for renames (status starts with R).
    """
    parts = output.split("\0")
    if parts and parts[-1] == "":
        parts.pop()
    entries: list[tuple[str, str, str | None]] = []
    i = 0
    while i < len(parts):
        status = parts[i]
        i += 1
        if status[:1] in ("R", "C"):
            old_path, i = parts[i], i + 1
            new_path, i = parts[i], i + 1
            entries.append((status, new_path, old_path))
        else:
            path, i = parts[i], i + 1
            entries.append((status, path, None))
    return entries


def _strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub("", text, count=1)


def _normalized(text: str) -> str:
    """Collapse all whitespace so pure reformatting compares equal."""
    return "".join(text.split())


def is_substantive_change(old_text: str, new_text: str) -> bool:
    """True if the diff reaches beyond YAML frontmatter and whitespace-only edits."""
    return _normalized(_strip_frontmatter(old_text)) != _normalized(_strip_frontmatter(new_text))


@dataclass
class ProseChange:
    skill: str
    path: str
    old_path: str | None
    status: str
    substantive: bool


@dataclass
class SkillFinding:
    skill: str
    changes: list[ProseChange]
    eval_touched: bool

    @property
    def substantive_changes(self) -> list[ProseChange]:
        return [c for c in self.changes if c.substantive]

    @property
    def needs_eval_or_waiver(self) -> bool:
        return bool(self.substantive_changes) and not self.eval_touched


def _selftest_touches_skill(all_entries: list[tuple[str, str, str | None]], skill: str) -> bool:
    """True if `skill` has an added-or-modified scripts/_*selftest*.py in this diff.

    A pure deletion doesn't count — removing the guarding test isn't coverage.
    """
    for status, path, _ in all_entries:
        if status.startswith("D"):
            continue
        m = SELFTEST_RE.match(path)
        if m and m.group("skill") == skill:
            return True
    return False


def collect_findings(
    prose_entries: list[tuple[str, str, str | None]],
    all_changed_paths: set[str],
    all_entries: list[tuple[str, str, str | None]],
    old_ref: str,
    new_ref: str | None,
    cwd: Path,
) -> list[SkillFinding]:
    """Classify every skill-prose diff entry and pair it with its skill's eval-touch status.

    new_ref=None means "the staged index" (--staged / --commit-msg modes).
    """
    by_skill: dict[str, list[ProseChange]] = {}
    for status, path, old_path in prose_entries:
        m = PROSE_RE.match(path)
        if not m:
            continue
        skill = m.group("skill")
        src_path = old_path or path
        old_text = "" if status.startswith("A") else _content_at(old_ref, src_path, cwd)
        new_text = "" if status.startswith("D") else _content_at(new_ref, path, cwd)
        by_skill.setdefault(skill, []).append(
            ProseChange(
                skill=skill,
                path=path,
                old_path=old_path,
                status=status,
                substantive=is_substantive_change(old_text, new_text),
            )
        )

    findings = []
    for skill, changes in sorted(by_skill.items()):
        touched = any(
            p == f"{skill}/evals"
            or p == f"{skill}/tests"
            or p.startswith((f"{skill}/evals/", f"{skill}/tests/"))
            for p in all_changed_paths
        ) or _selftest_touches_skill(all_entries, skill)
        findings.append(SkillFinding(skill=skill, changes=changes, eval_touched=touched))
    return findings


def parse_waiver(message: str) -> tuple[str | None, str | None]:
    """Return (reason, error) from a commit message's trailing trailer block.

    reason is set only for an exact, non-empty `Eval-waiver: <reason>` line.
    error is set for a near-miss (wrong key case, empty reason) so callers
    can say *why* a waiver didn't count instead of silently ignoring it.
    """
    lines = message.rstrip().splitlines()
    trailer_lines: list[str] = []
    for line in reversed(lines):
        if not line.strip():
            break
        if WAIVER_TRAILER_RE.match(line):
            trailer_lines.insert(0, line)
        else:
            break

    for line in trailer_lines:
        m = WAIVER_TRAILER_RE.match(line)
        assert m is not None  # guaranteed by the filter above
        key, val = m.group(1), m.group(2).strip()
        if key == WAIVER_KEY:
            if not val:
                return None, f"malformed waiver trailer (empty reason): {line!r}"
            return val, None
        if key.lower() == WAIVER_KEY.lower():
            return (
                None,
                f"malformed waiver trailer (expected {WAIVER_KEY!r}, got {key!r}): {line!r}",
            )
    return None, None


def render_findings(findings: list[SkillFinding], waiver_reason: str | None) -> str:
    lines = []
    for f in findings:
        subst = f.substantive_changes
        if not subst:
            continue
        if f.eval_touched:
            verdict = "OK (eval/test touched)"
        elif waiver_reason:
            verdict = f"OK (waived: {waiver_reason})"
        else:
            verdict = "MISSING eval/test touch"
        lines.append(f"skill '{f.skill}': {verdict}")
        for c in subst:
            arrow = f"{c.old_path} -> {c.path}" if c.old_path else c.path
            lines.append(f"    {c.status:<5} {arrow}")
    return "\n".join(lines)


def blocking_findings(findings: list[SkillFinding], waived: bool) -> list[SkillFinding]:
    if waived:
        return []
    return [f for f in findings if f.needs_eval_or_waiver]


def _banner(msg: str) -> None:
    rule = "=" * 70
    print(rule, file=sys.stderr)
    print(msg, file=sys.stderr)
    print(rule, file=sys.stderr)


_DiffResult = tuple[list[tuple[str, str, str | None]], set[str], list[tuple[str, str, str | None]]]


def _staged_diff(cwd: Path) -> _DiffResult:
    prose_out = _git(
        ["diff", "--cached", "--name-status", "-M", "-z", "--diff-filter=ACMRD", "--", "*.md"],
        cwd,
    )
    all_out = _git(["diff", "--cached", "--name-status", "-M", "-z"], cwd)
    all_entries = _parse_name_status_z(all_out)
    return _parse_name_status_z(prose_out), {p for _, p, _ in all_entries}, all_entries


def _range_diff(old_ref: str, new_ref: str, cwd: Path) -> _DiffResult:
    prose_out = _git(
        [
            "diff",
            "--name-status",
            "-M",
            "-z",
            "--diff-filter=ACMRD",
            old_ref,
            new_ref,
            "--",
            "*.md",
        ],
        cwd,
    )
    all_out = _git(["diff", "--name-status", "-M", "-z", old_ref, new_ref], cwd)
    all_entries = _parse_name_status_z(all_out)
    return _parse_name_status_z(prose_out), {p for _, p, _ in all_entries}, all_entries


def _verdict(
    findings: list[SkillFinding],
    flagged: list[SkillFinding],
    reason: str | None,
    waiver_error: str | None,
    enforce: bool,
    scope: str,
) -> int:
    if reason:
        print(f"eval-guard: waiver recorded — {WAIVER_KEY}: {reason}")

    if not flagged:
        if any(f.substantive_changes for f in findings):
            print(f"eval-guard: OK —\n{render_findings(findings, reason)}")
        else:
            print("eval-guard: OK — no substantive skill-prose changes.")
        return EXIT_PASS

    report = render_findings(findings, reason)
    msg = (
        f"eval-guard: substantive skill-prose change(s) with no eval/test touch "
        f"and no valid waiver ({scope} check).\n\n{report}\n\n"
        f"Fix: touch the skill's evals/ or tests/ directory (or add/modify a "
        f"scripts/_*selftest*.py), or add a commit trailer `{WAIVER_KEY}: <reason>`."
    )
    if waiver_error:
        msg += f"\n\nNote: found a near-miss waiver trailer that didn't count: {waiver_error}"

    if REPORT_ONLY and not enforce:
        _banner(f"eval-guard: REPORT-ONLY — would fail.\n\n{msg}")
        return EXIT_PASS
    _banner(msg)
    return EXIT_FAIL


def run_staged(cwd: Path) -> int:
    prose_entries, all_paths, all_entries = _staged_diff(cwd)
    findings = collect_findings(prose_entries, all_paths, all_entries, "HEAD", None, cwd)
    flagged = blocking_findings(findings, waived=False)
    if flagged:
        report = render_findings(findings, waiver_reason=None)
        _banner(
            "eval-guard: substantive skill-prose change(s) with no eval/test touch.\n"
            "pre-commit runs before your commit message exists, so it cannot check\n"
            "for an `Eval-waiver: <reason>` trailer — that happens at commit-msg\n"
            "time. Add eval/test coverage now, or plan to add the trailer.\n\n"
            f"{report}"
        )
    # --staged is always advisory: see module docstring. Never blocks.
    return EXIT_PASS


def run_commit_msg(message_path: Path, cwd: Path, enforce: bool) -> int:
    if not message_path.is_file():
        print(f"eval-guard: commit message file not found: {message_path}", file=sys.stderr)
        return EXIT_PLUMBING_ERROR
    message = message_path.read_text(encoding="utf-8", errors="replace")
    reason, waiver_error = parse_waiver(message)

    prose_entries, all_paths, all_entries = _staged_diff(cwd)
    findings = collect_findings(prose_entries, all_paths, all_entries, "HEAD", None, cwd)
    flagged = blocking_findings(findings, waived=reason is not None)
    return _verdict(findings, flagged, reason, waiver_error, enforce, scope="commit")


def run_range(range_spec: str, cwd: Path, enforce: bool) -> int:
    if ".." not in range_spec:
        print(f"eval-guard: --range expects <a>..<b>, got {range_spec!r}", file=sys.stderr)
        return EXIT_PLUMBING_ERROR
    old_ref, new_ref = range_spec.split("..", 1)
    if not old_ref or not new_ref:
        print(f"eval-guard: --range expects <a>..<b>, got {range_spec!r}", file=sys.stderr)
        return EXIT_PLUMBING_ERROR

    prose_entries, all_paths, all_entries = _range_diff(old_ref, new_ref, cwd)
    findings = collect_findings(prose_entries, all_paths, all_entries, old_ref, new_ref, cwd)

    log_out = _git(["log", "--format=%B%x00", f"{old_ref}..{new_ref}"], cwd)
    messages = [m for m in log_out.split("\0") if m.strip()]
    reason: str | None = None
    waiver_error: str | None = None
    for message in messages:
        r, e = parse_waiver(message)
        if r:
            reason = r
            waiver_error = None
            break
        if e and waiver_error is None:
            waiver_error = e

    flagged = blocking_findings(findings, waived=reason is not None)
    return _verdict(findings, flagged, reason, waiver_error, enforce, scope="range")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--staged",
        action="store_true",
        help="pre-commit mode: check the staged diff (advisory only).",
    )
    mode.add_argument(
        "--commit-msg",
        metavar="FILE",
        help="commit-msg mode: validate the drafted message's waiver trailer against the staged diff.",
    )
    mode.add_argument("--range", metavar="A..B", help="CI mode: check a landed commit range.")
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Flip out of report-only mode (exit 1 on a real violation). No effect on --staged.",
    )
    parser.add_argument("--repo", default=".", help="Path to the git repo (default: cwd).")
    args = parser.parse_args(argv)

    cwd = Path(args.repo).resolve()
    try:
        if args.staged:
            return run_staged(cwd)
        if args.commit_msg:
            return run_commit_msg(Path(args.commit_msg), cwd, enforce=args.enforce)
        return run_range(args.range, cwd, enforce=args.enforce)
    except GitError as e:
        print(f"eval-guard: git error: {e}", file=sys.stderr)
        return EXIT_PLUMBING_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
