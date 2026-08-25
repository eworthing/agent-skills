#!/usr/bin/env python3
"""Selftest for G47's repo-dependent RED cases (item 14).

Fixtures under evals/fixtures/ carry only the artifact-local conditions (shape, the
carried-forward coupling, the null-evidence restraint). Everything needing a live git
repo and a real ledger lives here: temp repos, ledgers produced by subprocessing the
SHIPPED attested_run.py under a temp CONTEST_REFACTOR_HOME, and verdicts from
subprocessing the SHIPPED validate-artifact.py with the three attestation flags — never
a reimplementation of either (the item-16 acceptance rule).

Assertions are on the G47 issue subset of the --json sidecar: a synthetic minimal
artifact legitimately fails unrelated gates (G1/G18/G19…), which is not what this test
measures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
WRAPPER = SCRIPTS / "attested_run.py"
VALIDATOR = SCRIPTS / "validate-artifact.py"

RUN_ID = "run-2026-08-21-selftest0000000000000000000000"


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def _mkrepo(td: Path, name: str) -> Path:
    repo = td / name
    (repo / "src").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "src" / "a.txt").write_text("alpha\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def _wrap(home: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["CONTEST_REFACTOR_HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(WRAPPER), *args], cwd=cwd, env=env, capture_output=True, text=True
    )


def _event_id(proc: subprocess.CompletedProcess) -> str:
    for line in proc.stdout.splitlines():
        if line.startswith("attested-run: event "):
            return line.split()[2]
    raise AssertionError(f"no event line in wrapper output: {proc.stdout!r}")


def _artifact(
    repo: Path,
    event_id: str,
    run_id: str = RUN_ID,
    status: str = "resolved",
    loop: int = 1,
    skip_reason: str | None = None,
) -> None:
    loop_result: dict = {
        "targeted_finding_status": status,
        "execution_evidence": {
            "event_id": event_id,
            "attestation_status": "consistency_check",
        },
    }
    if skip_reason is not None:
        loop_result["execution_evidence_skip_reason"] = skip_reason
    (repo / "CURRENT_REVIEW.json").write_text(
        json.dumps(
            {
                "schema_version": 4,
                "loop": loop,
                "run_id": run_id,
                "state": "CONTINUE",
                "loop_result": loop_result,
            },
            indent=2,
        )
        + "\n"
    )


def _artifact_null(
    repo: Path,
    skill_rev: str | None,
    skip_reason: str | None = None,
    status: str = "resolved",
    run_id: str = RUN_ID,
    loop: int = 1,
) -> None:
    """A CURRENT_REVIEW.json with a null execution_evidence -- for the epoch-scoped
    W8 skip-reason cases, which never need a real ledger citation."""
    body: dict = {
        "schema_version": 4,
        "loop": loop,
        "run_id": run_id,
        "state": "CONTINUE",
        "loop_result": {
            "targeted_finding_status": status,
            "execution_evidence": None,
        },
    }
    if skill_rev is not None:
        body["skill_rev"] = skill_rev
    if skip_reason is not None:
        body["loop_result"]["execution_evidence_skip_reason"] = skip_reason
    (repo / "CURRENT_REVIEW.json").write_text(json.dumps(body, indent=2) + "\n")


def _g47_issues(home: Path, repo: Path, phase: str) -> list[str]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        json_path = Path(tf.name)
    env = dict(os.environ)
    env["CONTEST_REFACTOR_HOME"] = str(home)
    subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            str(repo),
            "--mode",
            "strict",
            "--quiet",
            "--json",
            str(json_path),
            "--attestation-ledger",
            str(home / "attestation-ledger.jsonl"),
            "--attestation-trust",
            str(home / "verify-trust.json"),
            "--attestation-phase",
            phase,
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(json_path.read_text())
    finally:
        json_path.unlink(missing_ok=True)
    return [i.get("message", "") for i in payload.get("issues", []) if i.get("rule") == "G47"]


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="g47-selftest-") as td_s:
        td = Path(td_s)
        home = td / "home"
        repo = _mkrepo(td, "repo")

        r = _wrap(home, repo, "--trust", "--", "echo", "tests-green")
        if r.returncode != 0:
            failures.append(f"setup: trust pin failed: {r.stderr}")
        r = _wrap(home, repo, "--run-id", RUN_ID, "--", "echo", "tests-green")
        event = _event_id(r)

        # Pre-commit phase: uncommitted citing artifact + matching record => PASS.
        _artifact(repo, event)
        got = _g47_issues(home, repo, "pre-commit")
        if got:
            failures.append(f"pre-commit green: unexpected G47 issues: {got}")

        # Post-hoc: commit the artifact (the loop commit), source unchanged => PASS.
        _git(repo, "add", "CURRENT_REVIEW.json")
        _git(repo, "commit", "-qm", "loop 1 commit")
        got = _g47_issues(home, repo, "post-hoc")
        if got:
            failures.append(f"post-hoc green: unexpected G47 issues: {got}")

        # Replaced-artifact resolver regression (codex B2): a second loop replaces the
        # artifact; validating the CURRENT artifact must resolve exactly its own commit.
        r2 = _wrap(home, repo, "--run-id", RUN_ID, "--", "echo", "tests-green")
        event2 = _event_id(r2)
        _artifact(repo, event2)
        _git(repo, "add", "CURRENT_REVIEW.json")
        _git(repo, "commit", "-qm", "loop 2 commit")
        got = _g47_issues(home, repo, "post-hoc")
        if got:
            failures.append(f"replaced-artifact resolver: unexpected G47 issues: {got}")

        # Pre-commit FAIL: post-run worktree edit invalidates the record.
        (repo / "src" / "a.txt").write_text("alpha drifted\n")
        _artifact(repo, event2)
        got = _g47_issues(home, repo, "pre-commit")
        if not any("working tree" in m for m in got):
            failures.append(f"pre-commit drift must fail on the working-tree comparison, got {got}")
        _git(repo, "checkout", "--", "src/a.txt")
        _git(repo, "checkout", "--", "CURRENT_REVIEW.json")

        # Row 3 — replayed/stale record: source edited and committed AFTER the run; the
        # new loop commit's source no longer matches record.wtree.
        (repo / "src" / "a.txt").write_text("alpha v2\n")
        _artifact(repo, event2, loop=3)  # a NEW loop's artifact citing the OLD record
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "loop 3 commit with source drift")
        got = _g47_issues(home, repo, "post-hoc")
        if not any("replayed or stale" in m for m in got):
            failures.append(f"replay case must fail on wtree-vs-loop-commit, got {got}")

        # Row 1 — missing record.
        _artifact(repo, "deadbeef" * 4)
        got = _g47_issues(home, repo, "pre-commit")
        if not any("does not resolve" in m for m in got):
            failures.append(f"missing record must fail resolution, got {got}")

        # Row 4 — mismatched exit: cite a failing run.
        rf = _wrap(home, repo, "--run-id", RUN_ID, "--", "bash", "-c", "echo boom; exit 1")
        event_fail = _event_id(rf)
        _git(repo, "checkout", "--", "CURRENT_REVIEW.json")
        _artifact(repo, event_fail)
        got = _g47_issues(home, repo, "pre-commit")
        if not any("exit_status" in m for m in got):
            failures.append(f"failing-run citation must fail on exit_status, got {got}")

        # run-id mismatch.
        _artifact(repo, event2, run_id="run-2026-08-21-other000000000000000000000000")
        got = _g47_issues(home, repo, "pre-commit")
        if not any("run_id" in m for m in got):
            failures.append(f"run-id mismatch must fail, got {got}")

        # Duplicate event_id in the ledger.
        ledger = home / "attestation-ledger.jsonl"
        rec_line = next(
            line
            for line in ledger.read_text().splitlines()
            if json.loads(line)["event_id"] == event2
        )
        ledger.write_text(ledger.read_text() + rec_line + "\n")
        _artifact(repo, event2)
        got = _g47_issues(home, repo, "pre-commit")
        if not any("appears 2 times" in m for m in got):
            failures.append(f"duplicate event must fail, got {got}")
        # de-duplicate for later cases
        lines = ledger.read_text().splitlines()
        lines.remove(rec_line)
        ledger.write_text("\n".join(lines) + "\n")

        # Row 5 — unpinned / wrong-pin command.
        (home / "verify-trust.json").unlink()
        got = _g47_issues(home, repo, "pre-commit")
        if not any("no human-pinned command" in m for m in got):
            failures.append(f"missing pin must fail, got {got}")
        r = _wrap(home, repo, "--trust", "--", "true")  # pin a DIFFERENT (no-op) command
        got = _g47_issues(home, repo, "pre-commit")
        if not any("does not match the human-pinned command" in m for m in got):
            failures.append(f"wrapped-different-command must fail against the pin, got {got}")
        _wrap(home, repo, "--trust", "--", "echo", "tests-green")  # restore

        # Subdirectory invocation: recorded honestly, refused by the gate.
        rs = _wrap(home, repo / "src", "--run-id", RUN_ID, "--", "echo", "tests-green")
        event_sub = _event_id(rs)
        _artifact(repo, event_sub)
        got = _g47_issues(home, repo, "pre-commit")
        if not any("invoked from" in m for m in got):
            failures.append(f"subdirectory invocation must fail the directory rule, got {got}")

        # --- Item 14 / W8 -- execution_evidence_skip_reason (epoch-scoped) --------
        # `home`/`repo` already carry a trust pin (echo tests-green, restored above).
        POST_EPOCH_REV = "1609cd6"  # _ruleset_epoch.ATTESTATION_SKIP_REV
        PRE_EPOCH_REV = "7ffd502"  # _ruleset_epoch.HOTSPOT_TRIAGE_REV (an ancestor)

        # (1) post-epoch skill_rev, trust pin present, null evidence, no reason -> FAIL.
        _artifact_null(repo, POST_EPOCH_REV)
        got = _g47_issues(home, repo, "pre-commit")
        if not any("execution_evidence_skip_reason" in m for m in got):
            failures.append(f"post-epoch null evidence with no reason must fail, got {got}")

        # (2) same + non-empty reason -> PASS.
        _artifact_null(repo, POST_EPOCH_REV, skip_reason="test suite unrunnable in this env")
        got = _g47_issues(home, repo, "pre-commit")
        if got:
            failures.append(f"post-epoch null evidence with a reason must pass, got {got}")

        # (3) pre-epoch skill_rev -> PASS (run-8's already-committed artifacts stay green).
        _artifact_null(repo, PRE_EPOCH_REV)
        got = _g47_issues(home, repo, "pre-commit")
        if got:
            failures.append(f"pre-epoch skill_rev null evidence must stay green, got {got}")

        # (4) no trust entry for the repo -> PASS.
        (home / "verify-trust.json").unlink()
        _artifact_null(repo, POST_EPOCH_REV)
        got = _g47_issues(home, repo, "pre-commit")
        if got:
            failures.append(f"no trust pin must not fire the skip-reason check, got {got}")
        _wrap(home, repo, "--trust", "--", "echo", "tests-green")  # restore

        # (5) carried_forward + null + no reason -> PASS (the honest-revert exemption).
        _artifact_null(repo, POST_EPOCH_REV, status="carried_forward")
        got = _g47_issues(home, repo, "pre-commit")
        if got:
            failures.append(f"carried_forward null evidence must be exempt, got {got}")

        # (6) non-empty reason alongside non-null evidence -> FAIL (unconditional shape rule).
        r6 = _wrap(home, repo, "--run-id", RUN_ID, "--", "echo", "tests-green")
        event6 = _event_id(r6)
        _artifact(repo, event6, skip_reason="should never be set alongside real evidence")
        got = _g47_issues(home, repo, "pre-commit")
        if not any("legal only alongside a null" in m for m in got):
            failures.append(f"skip_reason alongside non-null evidence must fail, got {got}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: G47 — green both phases, and every repo-dependent RED case fails as itself")
    return 0


if __name__ == "__main__":
    sys.exit(main())
