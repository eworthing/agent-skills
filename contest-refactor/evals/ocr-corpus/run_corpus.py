#!/usr/bin/env python3
"""run_corpus.py — OCR-corpus runner for the `invariant` and `dead_surface`
detectors (contest-refactor OCR-GAP-REMEDIATION-PLAN-2026-09-03, wave W0).

Checks out a manifest's target revision of an external repo into a throwaway
git worktree, runs the requested detector adapter against it, and reports
whether the detector's candidates match the manifest's frozen targets.

Coverage validity comes first: a run is `invalid_coverage` whenever the
detector's own scan wasn't clean (non-zero exit, bad JSON, `status != "ok"`,
or the detector isn't wired up yet -- unknown flag or missing script). Only a
run with valid coverage can be `passed` or `failed`.

Usage:
  run_corpus.py --detector {invariant,dead_surface} --manifest PATH
                --rev {pre,post,pinned} [--assert] [--json PATH]

Exit codes (only meaningful with --assert; otherwise always 0):
  0 = passed, skipped_missing_root, or skipped_missing_revision
  1 = failed or invalid_coverage
  2 = usage error (bad manifest / bad --rev for this manifest's shape)
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
AGENT_SKILLS_ROOT = Path(__file__).resolve().parents[3]

# --rev {pre,post,pinned} selects which manifest field carries the git revision.
_REV_FIELD = {"pre": "pre_fix_rev", "post": "post_fix_rev", "pinned": "rev"}


def _detector_version() -> str:
    proc = subprocess.run(
        ["git", "-C", str(AGENT_SKILLS_ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _norm_path(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix()


def _normalize_symbol(symbol: str) -> str:
    """Strip generic clauses (`<...>`) and parameter labels (`(...)` onward)."""
    symbol = re.sub(r"<[^>]*>", "", symbol)
    paren = symbol.find("(")
    if paren != -1:
        symbol = symbol[:paren]
    return symbol.strip()


def _candidate_id(posix_path: str, symbol: str, start: int, end: int) -> str:
    raw = f"{posix_path}|{symbol}|{start}|{end}".encode()
    return hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:12]


def _match_invariant(row: dict, candidates: list[dict]) -> dict | None:
    row_path = _norm_path(row["path"])
    row_symbol = _normalize_symbol(row["symbol"])
    row_start = row.get("line_start") or 0
    row_end = row.get("line_end") or 0
    for cand in candidates:
        if _norm_path(cand.get("path", "")) != row_path:
            continue
        if _normalize_symbol(cand.get("symbol", "")) != row_symbol:
            continue
        if row_start and row_end:
            line_range = cand.get("line_range", {})
            c_start = cand.get("start_line", line_range.get("start", 0))
            c_end = cand.get("end_line", line_range.get("end", 0))
            if c_end < row_start or c_start > row_end:
                continue
        return cand
    return None


def _match_dead_surface(row: dict, candidates: list[dict]) -> dict | None:
    for cand in candidates:
        if (
            cand.get("kind") == row.get("kind")
            and _norm_path(cand.get("path", "")) == _norm_path(row["path"])
            and cand.get("type_name") == row.get("type_name")
            and cand.get("name") == row.get("name")
        ):
            return cand
    return None


def _invariant_candidate_id(cand: dict) -> str:
    line_range = cand.get("line_range", {})
    start = cand.get("start_line", line_range.get("start", 0))
    end = cand.get("end_line", line_range.get("end", 0))
    return _candidate_id(_norm_path(cand.get("path", "")), cand.get("symbol", ""), start, end)


def _dead_surface_candidate_id(cand: dict) -> str:
    symbol = f"{cand.get('kind')}:{cand.get('type_name')}.{cand.get('name')}"
    line = cand.get("line", 0)
    return _candidate_id(_norm_path(cand.get("path", "")), symbol, line, line)


def _cleanup_worktree(repo_root: Path, worktree: Path) -> None:
    if worktree.exists():
        subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "remove", "--force", str(worktree)],
            capture_output=True,
            text=True,
        )
    subprocess.run(
        ["git", "-C", str(repo_root), "worktree", "prune"], capture_output=True, text=True
    )


def _result(status: str, **fields) -> dict:
    base = {
        "status": status,
        "detector": None,
        "detector_version": None,
        "command": None,
        "rev": None,
        "hits": [],
        "misses": [],
        "flagged_silent": [],
        "candidate_total": 0,
        "files_scanned": 0,
        "target_candidate_ids": {},
    }
    base.update(fields)
    return base


def run(args: argparse.Namespace, manifest: dict) -> dict:
    detector_version = _detector_version()
    common = {"detector": args.detector, "detector_version": detector_version}

    rev_field = _REV_FIELD[args.rev]
    if rev_field not in manifest:
        sys.stderr.write(
            f"error: manifest has no '{rev_field}' field, required for --rev {args.rev}\n"
        )
        raise SystemExit(2)
    rev = manifest[rev_field]

    repo_env = manifest["repo_env"]
    repo_root_str = os.environ.get(repo_env)
    if not repo_root_str or not Path(repo_root_str).is_dir():
        sys.stderr.write(f"skip: {repo_env} is not set to an existing directory\n")
        return _result("skipped_missing_root", rev=rev, **common)
    repo_root = Path(repo_root_str).resolve()

    verify = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if verify.returncode != 0:
        sys.stderr.write(f"skip: revision '{rev}' not found in {repo_root}\n")
        return _result("skipped_missing_revision", rev=rev, **common)

    scope = manifest.get("scope", ".")
    worktree = Path(tempfile.mkdtemp(prefix="ocr-corpus-"))
    invariant_json_fd, invariant_json_name = tempfile.mkstemp(
        suffix=".json", prefix="ocr-corpus-invariant-"
    )
    os.close(invariant_json_fd)
    invariant_json_path = Path(invariant_json_name)

    def _cleanup() -> None:
        _cleanup_worktree(repo_root, worktree)
        invariant_json_path.unlink(missing_ok=True)

    atexit.register(_cleanup)
    try:
        add = subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "add", "--detach", str(worktree), rev],
            capture_output=True,
            text=True,
        )
        if add.returncode != 0:
            return _result(
                "invalid_coverage",
                rev=rev,
                command=[],
                **common,
                _reason=f"worktree add failed: {add.stderr.strip()[:300]}",
            )

        if args.detector == "invariant":
            script_path = SCRIPTS_DIR / "audit_hotspots.py"
            command = [
                sys.executable,
                str(script_path),
                str(worktree),
                "--json",
                "--scope",
                scope,
                "--experimental-invariant-queue",
                "--invariant-json",
                str(invariant_json_path),
            ]
        else:
            script_path = SCRIPTS_DIR / "audit_dead_surface.py"
            command = [
                sys.executable,
                str(script_path),
                str(worktree),
                "--json",
                "--scope",
                scope,
            ]

        if not script_path.exists():
            return _result(
                "invalid_coverage",
                rev=rev,
                command=command,
                **common,
                _reason=f"detector script missing: {script_path}",
            )

        proc = subprocess.run(command, capture_output=True, text=True)
        if proc.returncode != 0:
            return _result(
                "invalid_coverage",
                rev=rev,
                command=command,
                **common,
                _reason=f"adapter exited {proc.returncode}: {proc.stderr.strip()[:300]}",
            )
        try:
            doc = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return _result(
                "invalid_coverage",
                rev=rev,
                command=command,
                **common,
                _reason="adapter stdout is not decodable JSON",
            )
        if doc.get("status") != "ok":
            return _result(
                "invalid_coverage",
                rev=rev,
                command=command,
                **common,
                _reason=f"adapter status={doc.get('status')!r}, not 'ok'",
            )

        if args.detector == "invariant":
            # ponytail: candidate shape is a forward guess at the v3 document W3
            # defines (candidates carrying `candidate_queues`); unexercised until
            # W1a ships --experimental-invariant-queue. Adjust here when it lands.
            try:
                side_doc = json.loads(invariant_json_path.read_text())
            except (OSError, json.JSONDecodeError):
                return _result(
                    "invalid_coverage",
                    rev=rev,
                    command=command,
                    **common,
                    _reason="--invariant-json side file missing or not decodable",
                )
            candidates = [
                c
                for c in side_doc.get("candidates", [])
                if "invariant" in c.get("candidate_queues", [])
            ]
            files_scanned = sum(
                v.get("scanned", 0) for v in doc.get("coverage", {}).values() if isinstance(v, dict)
            )
            match_fn = _match_invariant
            id_fn = _invariant_candidate_id
        else:
            candidates = [r for r in doc.get("rows", []) if r.get("status") == "dead"]
            files_scanned = doc.get("coverage", {}).get("files_scanned", 0)
            match_fn = _match_dead_surface
            id_fn = _dead_surface_candidate_id

        targets = [t for t in manifest.get("targets", []) if t.get("detector") == args.detector]
        silents = [
            s for s in manifest.get("must_stay_silent", []) if s.get("detector") == args.detector
        ]

        hits: list[int] = []
        misses: list[int] = []
        target_candidate_ids: dict[str, str] = {}
        for target in targets:
            match = match_fn(target, candidates)
            if match is None:
                misses.append(target["fid"])
            else:
                hits.append(target["fid"])
                target_candidate_ids[str(target["fid"])] = id_fn(match)

        flagged_silent = [s["fid"] for s in silents if match_fn(s, candidates) is not None]

        # A restraint violation (a must-stay-silent row got flagged) is an
        # unambiguous failure regardless of wave-specific recall/budget bars,
        # which are owner-set thresholds applied by later measurement tooling,
        # not by this runner. ponytail: no other pass/fail criterion is defined
        # at W0 -- recall floors land with W1a/W2.
        status = "failed" if flagged_silent else "passed"

        return _result(
            status,
            rev=rev,
            command=command,
            hits=hits,
            misses=misses,
            flagged_silent=flagged_silent,
            candidate_total=len(candidates),
            files_scanned=files_scanned,
            target_candidate_ids=target_candidate_ids,
            **common,
        )
    finally:
        _cleanup()
        atexit.unregister(_cleanup)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detector", required=True, choices=["invariant", "dead_surface"])
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--rev", required=True, choices=["pre", "post", "pinned"])
    parser.add_argument("--assert", dest="assert_", action="store_true")
    parser.add_argument("--json", dest="json_path", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.manifest.is_file():
        sys.stderr.write(f"error: manifest not found: {args.manifest}\n")
        return 2
    manifest = json.loads(args.manifest.read_text())

    result = run(args, manifest)
    reason = result.pop("_reason", None)
    if reason:
        sys.stderr.write(f"{result['status']}: {reason}\n")

    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.json_path:
        args.json_path.write_text(payload + "\n")
    else:
        print(payload)

    if not args.assert_:
        return 0
    return 1 if result["status"] in ("failed", "invalid_coverage") else 0


if __name__ == "__main__":
    sys.exit(main())
