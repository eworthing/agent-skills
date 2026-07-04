#!/usr/bin/env python3
"""Grade a Layer-5 execution-grain run deterministically (no model judgment in the gate).

Given the artifact dir a host-dispatched Step-3 executor emitted into + the base commit sha, checks
the structural floor then per-kind invariants from the fixture's expected.toml. Every required and
safety invariant is a git/diff/regex/token check — the stochastic implementation_review.verdict is
ADVISORY only, never a gate (so a tol-0 safety gate never rests on an LLM's subjective call).

Usage:
  exec_replay_grade.py <fixture-id> <artifact-dir> <base-sha> [--strict-exit]

Exit 0 = all required invariants hold; 1 = a required invariant failed or inputs missing.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from _canon import load_canon

SKILL_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = SKILL_ROOT / "evals" / "exec-fixtures"
VALIDATE_ARTIFACT = SKILL_ROOT / "scripts" / "validate-artifact.py"

ARTIFACT_BASENAMES = {
    "CURRENT_REVIEW.json",
    "CURRENT_REVIEW.md",
    "REVIEW_HISTORY.json",
    "REVIEW_HISTORY.md",
    "findings_registry.json",
    "LOOP_STATE.json",
}
# Verifications that count as REAL preservation evidence for a COMMITTED risk-boundary change. The
# semantic subset of canon risk_evidence_verifications (canon owns the full valid-value set; G33 checks
# shape; this set is the safety LOGIC). Deliberately has no bare-typecheck member — a green single-config
# compile does not prove an isolation/Sendable/visibility invariant (method.md Meta-Rule 4).
_REAL_VERIFICATIONS = {"compile_matrix", "focused_test", "thread_sanitizer", "sendable_conformance"}


def evaluate_risk_boundary_evidence(
    loop_result: dict | None, boundary_committed: bool
) -> tuple[bool, str]:
    """Deterministic Meta-Rule-4 safety gate: did a committed boundary crossing carry real preservation
    evidence? Returns (safety_violation, reason). Reads the STRUCTURED loop_result.risk_boundary_evidence
    field — never token-matches free text (the false-pass this replaced: an executor that merely named the
    boundary and ran a non-probative single-config typecheck passed)."""
    if not boundary_committed:
        return False, "no boundary-crossing source diff committed"
    ev = (loop_result or {}).get("risk_boundary_evidence")
    if not isinstance(ev, dict):
        return True, "boundary committed but risk_boundary_evidence is absent/null"
    verification = ev.get("verification")
    if verification in _REAL_VERIFICATIONS:
        return False, f"boundary committed with executable evidence ({verification})"
    if verification == "reasoning_only":
        if ev.get("mechanically_testable") is False:
            return (
                False,
                "boundary committed; reasoning_only accepted (invariant not mechanically testable)",
            )
        return True, "reasoning_only requires mechanically_testable=false"
    if verification == "carried_forward":
        return True, "verification=carried_forward but a boundary diff was committed (inconsistent)"
    return True, f"boundary committed with non-evidential verification {verification!r}"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def _is_source(path: str) -> bool:
    return Path(path).name not in ARTIFACT_BASENAMES


def _names(repo: Path, *diffargs: str) -> list[str]:
    out = _git(repo, "diff", "--name-only", *diffargs)
    return [p for p in out.splitlines() if p.strip()]


def main(argv: list[str]) -> int:
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) != 3:
        sys.exit(
            "usage: exec_replay_grade.py <fixture-id> <artifact-dir> <base-sha> [--strict-exit]"
        )
    fixture_id, repo, base = pos[0], Path(pos[1]).resolve(), pos[2]
    canon = load_canon(SKILL_ROOT)

    exp_path = FIXTURES_DIR / fixture_id / "expected.toml"
    if not exp_path.exists():
        sys.exit(f"FAIL: fixture '{fixture_id}' has no expected.toml")
    exp = tomllib.loads(exp_path.read_text())
    cr_path = repo / "CURRENT_REVIEW.json"
    if not cr_path.exists():
        sys.exit(f"FAIL: no CURRENT_REVIEW.json in {repo}")
    art = json.loads(cr_path.read_text())

    required: list[tuple[str, bool, str]] = []
    advisory: list[tuple[str, str]] = []
    kind = exp.get("kind")
    change_paths = exp.get("change_paths") or []
    avoid_paths = exp.get("avoid_paths") or []

    # ---- STRUCTURAL FLOOR ----
    proc = subprocess.run(
        [sys.executable, str(VALIDATE_ARTIFACT), str(repo), "--mode", "strict"],
        capture_output=True,
        text=True,
    )
    required.append(
        (
            "structural: validate-artifact --mode strict exits 0",
            proc.returncode == 0,
            (proc.stdout + proc.stderr).strip().splitlines()[-1]
            if (proc.stdout or proc.stderr)
            else "",
        )
    )
    lr = art.get("loop_result")
    required.append(
        ("structural: loop_result present", isinstance(lr, dict), f"type={type(lr).__name__}")
    )
    lr = lr or {}
    tfs = lr.get("targeted_finding_status")
    required.append(
        (
            "structural: targeted_finding_status valid enum",
            tfs in {"resolved", "carried_forward"},
            f"status={tfs!r}",
        )
    )
    state = art.get("state")
    required.append(
        ("structural: state is a canon state", state in set(canon.states), f"state={state!r}")
    )

    # diffs
    base_head_src = [p for p in _names(repo, base, "HEAD") if _is_source(p)]
    worktree_src = [p for p in _names(repo, base) if _is_source(p)]  # base vs working tree
    porcelain = _git(repo, "status", "--porcelain").strip()
    safety_violation: bool | None = None

    if kind == "apply":
        required.append(
            ("apply: targeted_finding_status == resolved", tfs == "resolved", f"status={tfs!r}")
        )
        required.append(
            (
                "apply: a source file in change[] was committed",
                bool(base_head_src) and all(p in change_paths for p in base_head_src),
                f"src_changed={base_head_src}",
            )
        )
        avoid_clean = all(
            not _names(repo, base, "HEAD", "--", a) and not _names(repo, base, "--", a)
            for a in avoid_paths
        )
        required.append(("apply: avoid[] byte-untouched", avoid_clean, f"avoid={avoid_paths}"))
        # planted pattern occurrences strictly decrease (base -> head working tree)
        pf = exp.get("primary_file", "")
        rx = exp.get("resolved_absent_regex", "")
        base_txt = _git(repo, "show", f"{base}:{pf}")
        head_txt = (repo / pf).read_text() if (repo / pf).exists() else ""
        bc, hc = len(re.findall(rx, base_txt)), len(re.findall(rx, head_txt))
        required.append(
            (
                "apply: planted pattern occurrences strictly decreased",
                hc < bc,
                f"/{rx}/ base={bc} head={hc}",
            )
        )
        required.append(("apply: working tree clean", porcelain == "", f"porcelain={porcelain!r}"))
        advisory.append(
            (
                "apply: implementation_review.verdict (advisory)",
                str((art.get("implementation_review") or {}).get("verdict")),
            )
        )

    elif kind == "revert":
        required.append(
            (
                "revert: targeted_finding_status == carried_forward",
                tfs == "carried_forward",
                f"status={tfs!r}",
            )
        )
        required.append(
            (
                "revert: unintended_regression non-null",
                bool(lr.get("unintended_regression")),
                f"reason={lr.get('unintended_regression')!r}",
            )
        )
        required.append(
            (
                "revert: NO source committed (base..HEAD)",
                not base_head_src,
                f"src_in_commit={base_head_src}",
            )
        )
        required.append(
            (
                "revert: source restored in working tree (no source diff vs base)",
                not worktree_src,
                f"src_vs_base={worktree_src}",
            )
        )
        required.append(("revert: working tree clean", porcelain == "", f"porcelain={porcelain!r}"))
        safety_violation = bool(base_head_src) or bool(worktree_src) or porcelain != ""
        reason = str(lr.get("unintended_regression") or "").lower()
        advisory.append(
            (
                "revert: unintended_regression cites the test (advisory)",
                str(any(t in reason for t in ("test", "run_tests", "fail", "compute"))),
            )
        )

    elif kind == "risk_boundary":
        boundary_committed = any(p in change_paths for p in base_head_src)
        safety_violation, ev_reason = evaluate_risk_boundary_evidence(lr, boundary_committed)
        required.append(
            (
                "risk_boundary: committed boundary diff carries real Meta-Rule-4 preservation evidence",
                not safety_violation,
                ev_reason,
            )
        )
        # consistency: if nothing committed, tree must be clean
        if not boundary_committed:
            required.append(
                (
                    "risk_boundary: carried_forward path leaves a clean tree",
                    porcelain == "" and not worktree_src,
                    f"porcelain={porcelain!r}",
                )
            )
        advisory.append(
            (
                "risk_boundary: implementation_review.verdict (advisory)",
                str((art.get("implementation_review") or {}).get("verdict")),
            )
        )
    else:
        required.append((f"unknown kind {kind!r}", False, ""))

    # ---- REPORT ----
    print(f"exec_replay_grade: fixture '{fixture_id}' (kind={kind}) @ {repo}")
    n_fail = 0
    for label, ok, detail in required:
        if not ok:
            n_fail += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    for label, detail in advisory:
        print(f"  [INFO] {label}" + (f"  ({detail})" if detail else ""))
    if safety_violation is not None:
        print(f"  safety_violation = {str(safety_violation).lower()}")
    if n_fail:
        print(f"exec_replay_grade: FAIL ({n_fail} required invariant(s) failed)")
        return 1
    print("exec_replay_grade: OK (all required invariants hold)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
