#!/usr/bin/env python3
"""G47 — execution-evidence linkage (item 14, Tier 1).

Opt-in and strict: fires only when ``loop_result.execution_evidence`` is non-null — a
field no committed artifact has, so there is no retroactive-invalidation class and no
epoch-matrix entry (a field-triggered check self-scopes). When it fires, the citation is
checked against the wrapper's ledger record fail-closed.

Normative check order (peer-reviewed): artifact-local checks first — shape, the
carried-forward coupling, non-null run_id — so no environment access happens unless the
artifact itself is coherent; then the environment-dependent checks — ledger resolution,
repo binding, trust pin, run-id equality, invocation directory, record status, exit
status, and phase-aware freshness.

BLIND (``[g47-check-blind reason=… loop=…]``, no Issue) is reserved for genuine
environmental inability only: ``git`` missing, the artifact dir not inside a git work
tree, the ledger unreadable for permission reasons. Everything else about a CLAIMED
record FAILS: absent ledger file, unresolved event_id, duplicate event_id, unresolvable
or ambiguous loop commit, hash mismatch, missing trust pin, wrong invocation directory.

What this gate cannot conclude (design §3): that the pinned command is semantically the
right test suite, or that the record was not hand-forged by a same-privilege model —
Tier-1 records are ``consistency_check``, never ``attested``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from _artifact_core import Issue
from _wtree import source_tree_fingerprint, source_tree_fingerprint_at
from attested_run import command_sha256 as _command_sha256
from attested_run import ledger_path as _default_ledger_path
from attested_run import trust_path as _default_trust_path

PHASES = ("pre-commit", "post-hoc")


def _blind(reason: str, loop) -> None:
    print(f"[g47-check-blind reason={reason} loop={loop}]")


def _g47(msg: str) -> Issue:
    return Issue("G47", msg)


def _toplevel(path: Path) -> Path | None:
    out = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        return None
    return Path(out.stdout.strip()).resolve()


def _resolve_loop_commit(toplevel: Path, artifact_file: Path) -> tuple[str | None, str]:
    """Return (commit, diagnostic). The loop commit is the one whose committed
    CURRENT_REVIEW.json blob equals the on-disk artifact's blob — enumerate commits
    touching the path, filter by blob equality (``--find-object`` is wrong here: it
    matches occurrence-count changes, so it returns the removing commit too once a later
    loop replaces the artifact)."""
    rel = artifact_file.resolve().relative_to(toplevel)
    blob = subprocess.run(
        ["git", "-C", str(toplevel), "hash-object", f"--path={rel}", str(artifact_file)],
        capture_output=True,
        text=True,
    )
    if blob.returncode != 0:
        return None, f"hash-object failed: {blob.stderr.strip()}"
    want = blob.stdout.strip()
    log = subprocess.run(
        ["git", "-C", str(toplevel), "log", "--format=%H", "--", str(rel)],
        capture_output=True,
        text=True,
    )
    if log.returncode != 0:
        return None, f"git log failed: {log.stderr.strip()}"
    # ponytail: one rev-parse per artifact-touching commit; batch via
    # `git cat-file --batch-check` if this ever measures slow on a long-lived loop repo.
    matches = []
    for commit in log.stdout.split():
        rp = subprocess.run(
            ["git", "-C", str(toplevel), "rev-parse", f"{commit}:{rel}"],
            capture_output=True,
            text=True,
        )
        if rp.returncode == 0 and rp.stdout.strip() == want:
            matches.append(commit)
    if len(matches) != 1:
        return None, f"{len(matches)} commits match the artifact blob (need exactly 1)"
    return matches[0], ""


def check_g47_execution_evidence(
    current_review: dict,
    canon,
    artifact_dir: Path,
    ledger_path: Path | None = None,
    trust_path: Path | None = None,
    phase: str = "post-hoc",
) -> list[Issue]:
    issues: list[Issue] = []
    loop = current_review.get("loop")
    loop_result = current_review.get("loop_result")
    if not isinstance(loop_result, dict):
        return issues
    evidence = loop_result.get("execution_evidence")
    if evidence is None:
        return issues

    # --- (a) artifact-local checks: no environment access needed -------------------
    if not isinstance(evidence, dict):
        return [
            _g47(f"execution_evidence must be an object or null, got {type(evidence).__name__}")
        ]
    event_id = evidence.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        issues.append(_g47("execution_evidence.event_id must be a non-empty string"))
    status = evidence.get("attestation_status")
    if status not in canon.attestation_statuses:
        issues.append(
            _g47(
                f"execution_evidence.attestation_status={status!r} not in "
                f"{list(canon.attestation_statuses)}"
            )
        )
    if status != "consistency_check":
        issues.append(
            _g47(
                f"a citation may only ever claim 'consistency_check' "
                f"(got {status!r}); 'unavailable' records are uncitable"
            )
        )
    if loop_result.get("targeted_finding_status") == "carried_forward":
        issues.append(
            _g47(
                "carried_forward with non-null execution_evidence: a reverted loop has "
                "no surviving tested change to cite"
            )
        )
    run_id = current_review.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        issues.append(_g47("citing evidence requires a non-null top-level run_id"))
    if issues:
        return issues

    # --- (b) environment-dependent checks ------------------------------------------
    if phase not in PHASES:
        return [_g47(f"unknown attestation phase {phase!r} (valid: {PHASES})")]
    try:
        toplevel = _toplevel(Path(artifact_dir))
    except FileNotFoundError:
        _blind("git-missing", loop)
        return issues
    if toplevel is None:
        _blind("not-a-git-work-tree", loop)
        return issues

    lpath = Path(ledger_path) if ledger_path else _default_ledger_path()
    tpath = Path(trust_path) if trust_path else _default_trust_path()

    if not lpath.is_file():
        return [_g47(f"ledger absent at {lpath} but the artifact claims event {event_id}")]
    try:
        lines = lpath.read_text(encoding="utf-8").splitlines()
    except PermissionError:
        _blind("ledger-unreadable-permission", loop)
        return issues

    records = []
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # unmatchable; a claimed-but-malformed record fails as unresolved
        if rec.get("event_id") == event_id:
            records.append(rec)
    if not records:
        return [_g47(f"event {event_id} does not resolve in the ledger")]
    if len(records) > 1:
        return [_g47(f"event {event_id} appears {len(records)} times in the ledger")]
    record = records[0]

    if Path(record.get("repo_root", "")).resolve() != toplevel:
        issues.append(
            _g47(
                f"record.repo_root={record.get('repo_root')!r} does not match this "
                f"artifact's repo ({toplevel})"
            )
        )
    if record.get("run_id") != run_id:
        issues.append(_g47(f"record.run_id={record.get('run_id')!r} != artifact run_id={run_id!r}"))
    if record.get("invoked_from") != record.get("repo_root"):
        issues.append(
            _g47(
                f"record was invoked from {record.get('invoked_from')!r}, not the repo "
                f"root — the same pinned command can mean something else from a subdirectory"
            )
        )
    if record.get("attestation_status") != "consistency_check":
        issues.append(
            _g47(
                f"resolved record's own attestation_status is "
                f"{record.get('attestation_status')!r} — a degraded record is uncitable"
            )
        )
    if record.get("exit_status") != 0:
        issues.append(
            _g47(
                f"record.exit_status={record.get('exit_status')!r} cited as evidence — "
                f"a failing run proves nothing passed"
            )
        )

    # Trust pin.
    pin = None
    if tpath.is_file():
        try:
            pin = json.loads(tpath.read_text(encoding="utf-8")).get(str(toplevel))
        except (json.JSONDecodeError, PermissionError):
            pin = None
    if pin is None:
        issues.append(_g47(f"no human-pinned command for {toplevel} in the trust store"))
    elif record.get("command_sha256") != pin.get("command_sha256") or record.get(
        "command_sha256"
    ) != _command_sha256(str(record.get("command", ""))):
        issues.append(
            _g47(
                "record.command_sha256 does not match the human-pinned command "
                "(a wrapped different/no-op command authenticates nothing)"
            )
        )

    # Phase-aware freshness.
    try:
        if phase == "pre-commit":
            current_fp = source_tree_fingerprint(toplevel)
            if record.get("wtree") != current_fp:
                issues.append(
                    _g47(
                        "record.wtree does not match the current working tree "
                        "(pre-commit phase): the record is not evidence for this diff"
                    )
                )
        else:
            commit, diag = _resolve_loop_commit(
                toplevel, Path(artifact_dir) / "CURRENT_REVIEW.json"
            )
            if commit is None:
                issues.append(_g47(f"loop-commit resolver failed: {diag}"))
            elif record.get("wtree") != source_tree_fingerprint_at(toplevel, commit):
                issues.append(
                    _g47(
                        f"record.wtree does not match the source tree of the loop commit "
                        f"{commit[:12]} (replayed or stale record)"
                    )
                )
    except FileNotFoundError:
        _blind("git-missing", loop)
        return issues

    return issues
