#!/usr/bin/env python3
"""Fail-fast precondition gate, run BEFORE the first subagent is dispatched.

contest-refactor runs its Critic/Architect/Execution work in fresh subagents. A bad
input — a missing scope dir, unresolved test command or base ref, or hotspot evidence
that changed while being persisted — should abort here, in the main agent, with one
clear message, instead of failing opaquely two layers deep inside a spawned agent
(mattpocock-skills@2e64732: "A bad ref or empty diff should fail here — not inside two
parallel sub-agents.").

This is prevention only. It does NOT touch the post-spawn idle-recovery path
(trust-model.md HALT routing, added in 4c3e98e); that cure is unchanged. Stdlib-only,
Python 3.11+.

Usage:
    preflight.py <scope-dir> [--test-cmd "CMD ..."] [--base-ref REF]
        [--hotspot-json PATH --current-review PATH]

    <scope-dir>        source/scope directory that must exist before review starts
    --test-cmd "CMD"   discovered test/build command; its leading binary must resolve
    --base-ref REF     optional base ref; must `git rev-parse --verify` in the CWD
    --hotspot-json     raw audit_hotspots.py --json output
    --current-review   artifact whose discovery.hotspot_scan must equal that output

Exit codes: 0 = every precondition passed; 1 = one or more failed (each printed to
stderr); 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from _artifact_discovery import validate_hotspot_scan


def _test_command_resolves(test_cmd: str) -> tuple[bool, str]:
    """The leading token of the test command must be a binary on PATH or an
    existing executable file. We check only the launcher, not the whole pipeline —
    this is a sanity gate, not a shell."""
    # posix=False on Windows: POSIX mode treats `\` as an escape, so a quoted
    # `"C:\Program Files\...\MSBuild.exe"` collapses to `C:Program Files...`. Non-POSIX
    # mode keeps the separators but leaves the surrounding quotes on the token, so
    # strip them back off.
    posix = os.name != "nt"
    try:
        tokens = shlex.split(test_cmd, posix=posix)
    except ValueError as exc:
        return False, f"test command is not parseable: {exc}"
    if not tokens:
        return False, "test command is empty"
    launcher = tokens[0]
    if not posix and len(launcher) >= 2 and launcher[0] == launcher[-1] and launcher[0] in "\"'":
        launcher = launcher[1:-1]
    if "/" in launcher or "\\" in launcher:
        if Path(launcher).is_file():
            return True, ""
        # An unquoted launcher path containing spaces — `C:\Program Files\Python311\
        # python.exe -m pytest` — splits across several tokens, so tokens[0] is a
        # prefix that never resolves. Rejoin greedily until a real file appears.
        joined = launcher
        for extra in tokens[1:]:
            joined = f"{joined} {extra}"
            if Path(joined).is_file():
                return True, ""
        return False, f"test command launcher not found: {launcher}"
    if shutil.which(launcher):
        return True, ""
    return False, f"test command launcher not on PATH: {launcher}"


def _base_ref_resolves(base_ref: str) -> tuple[bool, str]:
    if shutil.which("git") is None:
        return False, "base ref given but `git` is not available"
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, ""
    return False, f"base ref does not resolve: {base_ref}"


def _provider_warning(provider: str | None) -> str | None:
    """Non-fatal warning when the run will have no independent challenger.

    provider == "unknown" is not a bad input -- the skill deliberately runs anywhere --
    but it has a consequence the user only discovers at halt today: no subagent spawn,
    so the HALT_SUCCESS challenge is administered by the same agent that produced the
    scorecard, and G32 (challenger_model non-empty) cannot tell the difference.

    Found live 2026-08-19 on a real opencode run that reached HALT_SUCCESS at loop 1
    under an inline self-vet. Root cause was a stale detection rule, not a real
    capability limit -- which is exactly why this belongs here, before dispatch: a
    detection bug and a genuinely spawn-less host look identical from inside the loop,
    and both silently weaken the terminal verdict.
    """
    if provider != "unknown":
        return None
    return (
        "provider resolved to 'unknown': no subagent spawn, so any HALT_SUCCESS this run "
        "reaches will rest on a challenge administered by the Critic itself. If your host "
        "does support spawn, detection failed -- pass --provider <name> explicitly. "
        "Otherwise treat a terminal success as provisional."
    )


def _read_json(path: str, label: str) -> tuple[object | None, str | None]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, f"{label} cannot be read: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"{label} is not valid JSON: {exc}"


def _hotspot_failures(hotspot_json: str | None, current_review: str | None) -> list[str]:
    if bool(hotspot_json) != bool(current_review):
        return ["--hotspot-json and --current-review must be supplied together"]
    if not hotspot_json or not current_review:
        return []

    raw, error = _read_json(hotspot_json, "hotspot scanner output")
    if error:
        return [error]
    artifact, error = _read_json(current_review, "current review")
    if error:
        return [error]

    discovery = artifact.get("discovery") if isinstance(artifact, dict) else None
    persisted = discovery.get("hotspot_scan") if isinstance(discovery, dict) else None
    failures = [f"hotspot scanner output: {msg}" for msg in validate_hotspot_scan(raw)]
    failures.extend(f"persisted hotspot_scan: {msg}" for msg in validate_hotspot_scan(persisted))
    if raw != persisted:
        failures.append("persisted hotspot_scan does not match the hotspot scanner output")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-fast precondition gate before subagent dispatch."
    )
    parser.add_argument("scope_dir", help="source/scope directory that must exist")
    parser.add_argument("--test-cmd", help="discovered test/build command to sanity-check")
    parser.add_argument("--base-ref", help="optional base ref to verify with git rev-parse")
    parser.add_argument("--provider", help="detected provider; warns (never fails) when 'unknown'")
    parser.add_argument("--hotspot-json", help="raw audit_hotspots.py --json output")
    parser.add_argument("--current-review", help="CURRENT_REVIEW.json containing hotspot_scan")
    args = parser.parse_args(argv)

    failures: list[str] = []

    if not Path(args.scope_dir).is_dir():
        failures.append(f"scope directory does not exist: {args.scope_dir}")

    if args.test_cmd:
        ok, msg = _test_command_resolves(args.test_cmd)
        if not ok:
            failures.append(msg)

    if args.base_ref:
        ok, msg = _base_ref_resolves(args.base_ref)
        if not ok:
            failures.append(msg)

    failures.extend(_hotspot_failures(args.hotspot_json, args.current_review))

    if failures:
        for f in failures:
            print(f"preflight: FAIL: {f}", file=sys.stderr)
        print(
            "preflight: aborting before any subagent dispatch — fix the above and re-run.",
            file=sys.stderr,
        )
        return 1

    warning = _provider_warning(args.provider)
    if warning:
        print(f"preflight: WARNING: {warning}", file=sys.stderr)
    print("preflight: OK — inputs are consistent and resolvable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
