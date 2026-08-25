#!/usr/bin/env python3
"""Self-test: preflight.py fails fast on a knowably-bad run BEFORE any subagent spawn.

contest-refactor dispatches its Critic/Architect/Execution work into fresh subagents.
If the scope dir, discovered test command, configured base ref, or persisted hotspot
evidence is bad, the run should die in the main agent with a clear message — not three
layers deep inside a spawned agent (mattpocock-skills@2e64732). preflight.py is that gate.

No pytest in this repo (pyproject configures only ruff), so this standalone check runs
the CLI as a subprocess against throwaway tempdirs (and a throwaway git repo for the
base-ref case) and asserts on exit codes + stderr.

Cases:
  - healthy (real dir + resolvable test cmd)   -> exit 0
  - missing repo root                          -> non-zero, names the repo root
  - unresolvable test command                  -> non-zero, names the test command
  - base ref: HEAD in a real repo -> exit 0;  bogus ref -> non-zero, names the ref
  - exact raw + persisted hotspot JSON          -> exit 0
  - truncated, malformed, or missing hotspot JSON -> non-zero before dispatch
  - multi-root discovery.source_roots (avalanche plan Phase 2):
      happy path (declared == enumerated)               -> exit 0
      declared missing an enumerated root                -> non-zero, names it
      declared has an extra undeclared root               -> non-zero, names it
      trailing slash / unsorted / duplicate / absolute entries -> non-zero, normalization message
      a source-root-relative hotspot candidate path       -> non-zero, repo-root message
      --scope nonexistent                                 -> non-zero, names --scope
      declared root outside --scope                       -> non-zero
      scoped happy path (declared root under --scope)      -> exit 0

Run: python3 scripts/_preflight_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PREFLIGHT = Path(__file__).with_name("preflight.py")
AUDIT = Path(__file__).with_name("audit_hotspots.py")


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PREFLIGHT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            "init",
        ],
        cwd=root,
        check=True,
    )


def _unknown_provider_warning() -> list[str]:
    """Pin the `--provider unknown` warning.

    It exists because of a documented production incident: an inline self-vet
    reached HALT_SUCCESS off a stale detection rule with no subagent spawn. The
    warning was the fix, and it had zero test coverage -- deleting it outright
    passed this suite. A guard installed after a real incident is exactly the one
    that must not be able to vanish quietly.
    """
    import subprocess
    import sys as _sys

    p = subprocess.run(
        [_sys.executable, str(PREFLIGHT), str(PREFLIGHT.parent), "--provider", "unknown"],
        capture_output=True,
        text=True,
    )
    blob = (p.stdout + p.stderr).lower()
    if "unknown" not in blob:
        return ["--provider unknown: no warning emitted; the post-incident guard is silent"]
    if "halt_success" not in blob:
        return ["--provider unknown: warning does not name the HALT_SUCCESS risk it exists for"]
    return []


def main() -> int:
    if not PREFLIGHT.is_file():
        print(f"FAIL: preflight script missing: {PREFLIGHT}")
        return 1

    failures: list[str] = []
    failures.extend(_unknown_provider_warning())
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        scope = base / "src"
        scope.mkdir()

        # 1) healthy: existing dir + a test command whose binary resolves.
        p = _run([str(scope), "--test-cmd", f"{sys.executable} -m pytest"])
        if p.returncode != 0:
            failures.append(f"healthy: expected exit 0, got {p.returncode}\n{p.stderr.rstrip()}")

        # 2) missing repo root.
        p = _run([str(base / "nope")])
        if p.returncode == 0:
            failures.append("missing-dir: expected non-zero exit, got 0")
        elif "repo root" not in p.stderr.lower():
            failures.append(f"missing-dir: message should name the repo root\n{p.stderr.rstrip()}")

        # 3) unresolvable test command.
        p = _run([str(scope), "--test-cmd", "definitely-not-a-real-binary-xyz run"])
        if p.returncode == 0:
            failures.append("bad-test-cmd: expected non-zero exit, got 0")
        elif "test command" not in p.stderr.lower():
            failures.append(
                f"bad-test-cmd: message should name the test command\n{p.stderr.rstrip()}"
            )

        # 4) base ref resolution (real temp git repo).
        if shutil.which("git"):
            repo = base / "repo"
            repo.mkdir()
            _init_repo(repo)
            p = _run([str(repo), "--base-ref", "HEAD"], cwd=repo)
            if p.returncode != 0:
                failures.append(
                    f"good-ref: HEAD should resolve, got {p.returncode}\n{p.stderr.rstrip()}"
                )
            p = _run([str(repo), "--base-ref", "no-such-ref-zzz"], cwd=repo)
            if p.returncode == 0:
                failures.append("bad-ref: expected non-zero exit, got 0")
            elif "ref" not in p.stderr.lower():
                failures.append(f"bad-ref: message should name the ref\n{p.stderr.rstrip()}")
        else:
            print("note: git not found — skipping base-ref cases")

        # 5) The scanner output and the persisted discovery object are both valid and equal.
        hotspot_scope = base / "hotspot-src"
        hotspot_scope.mkdir()
        (hotspot_scope / "flow.py").write_text(
            "def route(a, b, c):\n"
            "    if a and b:\n"
            "        if c:\n"
            "            return 1\n"
            "    elif a or b:\n"
            "        return 2\n"
            "    return 0\n",
            encoding="utf-8",
        )
        hotspot_json = base / "hotspot.json"
        scan = subprocess.run(
            [sys.executable, str(AUDIT), str(hotspot_scope), "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        hotspot_json.write_text(scan.stdout, encoding="utf-8")
        hotspot_record = json.loads(scan.stdout)
        current_review = base / "CURRENT_REVIEW.json"
        current_review.write_text(
            json.dumps({"discovery": {"hotspot_scan": hotspot_record}}),
            encoding="utf-8",
        )
        hotspot_args = [
            str(hotspot_scope),
            "--hotspot-json",
            str(hotspot_json),
            "--current-review",
            str(current_review),
        ]
        p = _run(hotspot_args)
        if p.returncode != 0:
            failures.append(
                f"hotspot-match: valid identical records should pass, got {p.returncode}\n"
                f"{p.stderr.rstrip()}"
            )

        # 6) Reproduce the live BenchHype failure: raw output is valid, but manual
        # reconstruction drops Python coverage and candidate evidence before persistence.
        truncated = copy.deepcopy(hotspot_record)
        truncated["coverage"].pop("python")
        if truncated["candidates"]:
            truncated["candidates"][0].pop("signals")
        current_review.write_text(
            json.dumps({"discovery": {"hotspot_scan": truncated}}),
            encoding="utf-8",
        )
        p = _run(hotspot_args)
        if p.returncode == 0:
            failures.append("hotspot-truncated: expected pre-dispatch failure, got 0")
        elif "hotspot" not in p.stderr.lower():
            failures.append(
                f"hotspot-truncated: failure should name hotspot evidence\n{p.stderr.rstrip()}"
            )

        # 7) Malformed or missing scanner evidence fails at the same boundary.
        hotspot_json.write_text("{not json", encoding="utf-8")
        p = _run(hotspot_args)
        if p.returncode == 0:
            failures.append("hotspot-invalid-json: expected pre-dispatch failure, got 0")
        hotspot_json.unlink()
        p = _run(hotspot_args)
        if p.returncode == 0:
            failures.append("hotspot-missing-json: expected pre-dispatch failure, got 0")

        # 8) A missing/unreadable --current-review (the live Step-0 circular-dependency
        # incident: preflight invoked before CURRENT_REVIEW.json existed) must name the
        # required scanner -> persist -> preflight order, not just "cannot be read".
        hotspot_json.write_text(scan.stdout, encoding="utf-8")
        missing_review = base / "NOPE_REVIEW.json"
        p = _run(
            [
                str(hotspot_scope),
                "--hotspot-json",
                str(hotspot_json),
                "--current-review",
                str(missing_review),
            ]
        )
        if p.returncode == 0:
            failures.append("missing-current-review: expected pre-dispatch failure, got 0")
        elif "audit_hotspots.py" not in p.stderr:
            failures.append(
                f"missing-current-review: failure should name the required Step-0 order\n"
                f"{p.stderr.rstrip()}"
            )

        # 9) Multi-root discovery.source_roots checks (avalanche plan Phase 2). A
        # two-root scratch repo (src/, tools/) so "declared narrows the repo" is
        # observable. --current-review alone (no --hotspot-json) drives these --
        # the equality check in case 5-8 above is a separate, independently-gated path.
        multiroot = base / "multiroot"
        (multiroot / "src").mkdir(parents=True)
        (multiroot / "tools").mkdir()
        (multiroot / "src" / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
        (multiroot / "tools" / "b.py").write_text("def g():\n    pass\n", encoding="utf-8")
        review = multiroot / "CURRENT_REVIEW.json"

        def _write_review(source_roots: list[str] | None, candidate_path: str) -> None:
            discovery: dict = {"hotspot_scan": {"candidates": [{"path": candidate_path}]}}
            if source_roots is not None:
                discovery["source_roots"] = source_roots
            review.write_text(json.dumps({"discovery": discovery}), encoding="utf-8")

        def _run_review(extra: list[str] | None = None):
            args = [str(multiroot), "--current-review", str(review)]
            if extra:
                args.extend(extra)
            return _run(args)

        # Happy path: declared set matches the repo's enumerated universe exactly.
        _write_review(["src", "tools"], "src/a.py")
        p = _run_review()
        if p.returncode != 0:
            failures.append(
                f"multiroot-happy: expected exit 0, got {p.returncode}\n{p.stderr.rstrip()}"
            )

        # Declared list missing an enumerated root -> FAIL naming it.
        _write_review(["src"], "src/a.py")
        p = _run_review()
        if p.returncode == 0:
            failures.append("multiroot-missing-root: expected non-zero exit, got 0")
        elif "tools" not in p.stderr:
            failures.append(
                f"multiroot-missing-root: message should name the missing root\n{p.stderr.rstrip()}"
            )

        # Extra undeclared root in the list -> FAIL naming it.
        _write_review(["src", "tools", "extra"], "src/a.py")
        p = _run_review()
        if p.returncode == 0:
            failures.append("multiroot-extra-root: expected non-zero exit, got 0")
        elif "extra" not in p.stderr:
            failures.append(
                f"multiroot-extra-root: message should name the extra root\n{p.stderr.rstrip()}"
            )

        # Trailing slash / unsorted / duplicate / absolute entries -> FAIL, each with
        # the normalization message.
        for label, bad_roots in (
            ("trailing-slash", ["src/", "tools"]),
            ("unsorted", ["tools", "src"]),
            ("duplicate", ["src", "src", "tools"]),
            ("absolute", ["/etc", "tools"]),
        ):
            _write_review(bad_roots, "src/a.py")
            p = _run_review()
            msg = p.stderr.lower()
            if p.returncode == 0:
                failures.append(f"multiroot-{label}: expected non-zero exit, got 0")
            elif "source_roots" not in p.stderr or not ("normaliz" in msg or "malformed" in msg):
                failures.append(
                    f"multiroot-{label}: message should name the normalization problem\n"
                    f"{p.stderr.rstrip()}"
                )

        # Coordinate tripwire: a source-root-relative candidate path -> FAIL with the
        # repo-root message.
        _write_review(["src", "tools"], "a.py")
        p = _run_review()
        if p.returncode == 0:
            failures.append("multiroot-coordinate: expected non-zero exit, got 0")
        elif "repo root" not in p.stderr.lower():
            failures.append(
                f"multiroot-coordinate: message should name the repo-root requirement\n"
                f"{p.stderr.rstrip()}"
            )

        # --scope pointing at a nonexistent directory -> FAIL naming --scope.
        p = _run_review(["--scope", str(multiroot / "nope")])
        if p.returncode == 0:
            failures.append("multiroot-scope-missing: expected non-zero exit, got 0")
        elif "scope" not in p.stderr.lower():
            failures.append(
                f"multiroot-scope-missing: message should name --scope\n{p.stderr.rstrip()}"
            )

        # Declared root outside --scope -> FAIL (equality check is skipped when scoped).
        _write_review(["tools"], "tools/b.py")
        p = _run_review(["--scope", str(multiroot / "src")])
        if p.returncode == 0:
            failures.append("multiroot-scope-outside: expected non-zero exit, got 0")
        elif "scope" not in p.stderr.lower():
            failures.append(
                f"multiroot-scope-outside: message should name --scope\n{p.stderr.rstrip()}"
            )

        # Scoped happy path: declared root falls under --scope.
        _write_review(["src"], "src/a.py")
        p = _run_review(["--scope", str(multiroot / "src")])
        if p.returncode != 0:
            failures.append(
                f"multiroot-scope-happy: expected exit 0, got {p.returncode}\n{p.stderr.rstrip()}"
            )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: preflight — healthy inputs pass; missing repo root, unresolvable test "
        "command, bogus base ref, malformed hotspot persistence, and multi-root "
        "source_roots narrowing/normalization/coordinate defects fail fast"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
