#!/usr/bin/env python3
"""Fail-fast precondition gate, run BEFORE the first subagent is dispatched.

contest-refactor runs its Critic/Architect/Execution work in fresh subagents. A bad
input — a missing repo root or scope dir, unresolved test command or base ref, or
hotspot evidence that changed while being persisted — should abort here, in the main
agent, with one clear message, instead of failing opaquely two layers deep inside a
spawned agent (mattpocock-skills@2e64732: "A bad ref or empty diff should fail here —
not inside two parallel sub-agents.").

This is prevention only. It does NOT touch the post-spawn idle-recovery path
(trust-model.md HALT routing, added in 4c3e98e); that cure is unchanged. Stdlib-only,
Python 3.11+.

Usage:
    preflight.py <repo-root> [--scope DIR] [--test-cmd "CMD ..."] [--base-ref REF]
        [--hotspot-json PATH --current-review PATH]

    <repo-root>        repo root that must exist before review starts
    --scope DIR        optional subdirectory this run narrows to; must exist under
                        <repo-root>. Relaxes the unscoped source_roots check below
                        from "matches the repo's enumerated roots exactly" to
                        "every declared root is under DIR".
    --test-cmd "CMD"   discovered test/build command; its leading binary must resolve
    --base-ref REF     optional base ref; must `git rev-parse --verify` in the CWD
    --hotspot-json     raw audit_hotspots.py --json output
    --current-review   artifact checked against <repo-root>: discovery.source_roots
                        must be normalized and (unscoped) match the repo's enumerated
                        first-party roots, or (scoped) fall under --scope; every
                        discovery.hotspot_scan candidate path must resolve as a file
                        under <repo-root>. Also required (with --hotspot-json) to equal
                        the raw scanner output.

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
from _fs_filters import normalize_roots
from coverage_ledger import source_roots as _enumerate_source_roots


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
    """Raw-vs-persisted equality check. --hotspot-json has nothing to compare
    against without --current-review and is rejected alone; --current-review alone
    is valid (it drives _discovery_failures below without needing a fresh scan)."""
    if not hotspot_json:
        return []
    if not current_review:
        return ["--hotspot-json requires --current-review"]

    order_hint = (
        "required order: run audit_hotspots.py --json first, persist its object unchanged as "
        "discovery.hotspot_scan when writing CURRENT_REVIEW.json, then run preflight"
    )

    raw, error = _read_json(hotspot_json, "hotspot scanner output")
    if error:
        return [error, order_hint]
    artifact, error = _read_json(current_review, "current review")
    if error:
        return [error, order_hint]

    discovery = artifact.get("discovery") if isinstance(artifact, dict) else None
    persisted = discovery.get("hotspot_scan") if isinstance(discovery, dict) else None
    failures = [f"hotspot scanner output: {msg}" for msg in validate_hotspot_scan(raw)]
    failures.extend(f"persisted hotspot_scan: {msg}" for msg in validate_hotspot_scan(persisted))
    if raw != persisted:
        failures.append("persisted hotspot_scan does not match the hotspot scanner output")
    if failures:
        failures.append(order_hint)
    return failures


_ROOTS_FINGERPRINT_HINT = (
    "the candidate fingerprint hashes discovery.source_roots verbatim -- order, "
    "duplicates, or slash noise changes the fingerprint and breaks recurrence detection"
)


def _normalize_failures(declared: list[str]) -> list[str]:
    """Structural + sort/dedupe checks. Independent of --scope."""
    bad = [
        r
        for r in declared
        if not r or r.endswith("/") or Path(r).is_absolute() or ".." in Path(r).parts
    ]
    if bad:
        return [
            f"discovery.source_roots has malformed entries {bad}: entries must be non-empty, "
            f"repo-relative, no trailing slash, no '..' ({_ROOTS_FINGERPRINT_HINT})"
        ]
    normalized = normalize_roots(declared)
    if declared != normalized:
        return [
            f"discovery.source_roots is not normalized (expected {normalized}): "
            f"{_ROOTS_FINGERPRINT_HINT}"
        ]
    return []


def _narrowing_failures(repo_root: Path, declared: list[str], scope_rel: str | None) -> list[str]:
    """Unscoped: declared roots must equal the repo's enumerated universe (catches
    silent narrowing). Scoped: declared roots need only fall under --scope; the
    equality check is skipped (v1 minimal, per the plan's Settled-during-execution note).
    """
    if scope_rel is not None:
        outside = [r for r in declared if r != scope_rel and not r.startswith(scope_rel + "/")]
        if outside:
            return [f"discovery.source_roots entries fall outside --scope {scope_rel}: {outside}"]
        return []

    enumerated = set(_enumerate_source_roots(repo_root))
    declared_set = set(declared)
    if declared_set == enumerated:
        return []
    missing = sorted(enumerated - declared_set)
    extra = sorted(declared_set - enumerated)
    detail = "; ".join(
        part
        for part in (f"missing: {missing}" if missing else "", f"extra: {extra}" if extra else "")
        if part
    )
    return [
        f"discovery.source_roots silently narrows the repository ({detail}) -- an unscoped run "
        "must declare every first-party root the repo enumerates; pass --scope to narrow on purpose"
    ]


def _coordinate_failures(repo_root: Path, hotspot_scan: object) -> list[str]:
    """Every candidate path must resolve as a file under repo_root. Catches a scan
    run at a source root instead of the repo root -- a different coordinate base
    than the citation ledger uses, silently, at any N."""
    if not isinstance(hotspot_scan, dict):
        return []
    candidates = hotspot_scan.get("candidates")
    if not isinstance(candidates, list):
        return []
    bad = [
        c["path"]
        for c in candidates
        if isinstance(c, dict)
        and isinstance(c.get("path"), str)
        and not (repo_root / c["path"]).is_file()
    ]
    if not bad:
        return []
    return [
        f"hotspot_scan candidate path(s) do not resolve from the repo root: {bad} -- "
        "run audit_hotspots.py at the repo root, not a source root, so candidate paths "
        "stay repo-relative"
    ]


def _discovery_failures(
    repo_root: Path, current_review: str | None, scope: Path | None
) -> list[str]:
    """Normalization + silent-narrowing + coordinate tripwire. Runs whenever
    --current-review is given, independent of --hotspot-json (unlike
    _hotspot_failures' raw-vs-persisted equality check)."""
    if not current_review:
        return []
    artifact, error = _read_json(current_review, "current review")
    if error:
        return [error]
    discovery = artifact.get("discovery") if isinstance(artifact, dict) else None
    if not isinstance(discovery, dict):
        return []

    failures: list[str] = []
    declared = discovery.get("source_roots")
    if declared is not None:
        if not isinstance(declared, list) or not all(isinstance(r, str) for r in declared):
            failures.append("discovery.source_roots must be a list of strings")
        else:
            failures.extend(_normalize_failures(declared))
            # Compare a best-effort normalized view even when the raw list is
            # malformed (e.g. a trailing slash): a normalization defect should not
            # mask a missing/extra root -- both are worth surfacing in one pass
            # rather than a fix-one-rerun-discover-the-next cycle.
            scope_rel = scope.relative_to(repo_root).as_posix() if scope else None
            failures.extend(_narrowing_failures(repo_root, normalize_roots(declared), scope_rel))

    failures.extend(_coordinate_failures(repo_root, discovery.get("hotspot_scan")))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-fast precondition gate before subagent dispatch."
    )
    parser.add_argument("repo_root", help="repo root that must exist before review starts")
    parser.add_argument(
        "--scope", help="optional subdirectory of repo_root this run narrows to; must exist"
    )
    parser.add_argument("--test-cmd", help="discovered test/build command to sanity-check")
    parser.add_argument("--base-ref", help="optional base ref to verify with git rev-parse")
    parser.add_argument("--provider", help="detected provider; warns (never fails) when 'unknown'")
    parser.add_argument("--hotspot-json", help="raw audit_hotspots.py --json output")
    parser.add_argument("--current-review", help="CURRENT_REVIEW.json containing hotspot_scan")
    args = parser.parse_args(argv)

    failures: list[str] = []
    repo_root = Path(args.repo_root)

    if not repo_root.is_dir():
        failures.append(f"repo root does not exist: {args.repo_root}")

    scope_path: Path | None = None
    if args.scope:
        candidate = Path(args.scope)
        if not candidate.is_dir():
            failures.append(f"--scope directory does not exist: {args.scope}")
        elif repo_root.is_dir() and not candidate.resolve().is_relative_to(repo_root.resolve()):
            failures.append(f"--scope must be a subdirectory of repo root: {args.scope}")
        else:
            scope_path = candidate.resolve()

    if args.test_cmd:
        ok, msg = _test_command_resolves(args.test_cmd)
        if not ok:
            failures.append(msg)

    if args.base_ref:
        ok, msg = _base_ref_resolves(args.base_ref)
        if not ok:
            failures.append(msg)

    failures.extend(_hotspot_failures(args.hotspot_json, args.current_review))
    if repo_root.is_dir():
        failures.extend(_discovery_failures(repo_root.resolve(), args.current_review, scope_path))

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
