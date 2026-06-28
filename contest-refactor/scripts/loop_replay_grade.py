#!/usr/bin/env python3
"""Grade a completed loop-replay run against its fixture's expected.toml (Layer 4).

Given the artifact directory a host-dispatched loop emitted into (CURRENT_REVIEW.json +
REVIEW_HISTORY + registry), this checks the structural and semantic invariants registered
in evals/loop_replay_baseline.json. This is the committed grader — it is what makes the
harness measure Critic *behavior* (did the loop catch and fix the planted debt), not just
artifact mechanics. It runs no model.

Usage:
  loop_replay_grade.py <fixture-id> <artifact-dir> [--strict-exit]

  <artifact-dir>  directory holding the emitted CURRENT_REVIEW.json (the materialized repo
                  root, unless the loop writes artifacts elsewhere).
  --strict-exit   exit 1 if any REQUIRED invariant fails (default). Advisory checks never
                  affect exit status; they print as INFO.

Exit 0 = all required invariants hold; 1 = a required invariant failed or inputs missing.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = SKILL_ROOT / "evals" / "loop-fixtures"
CANON_DIR = SKILL_ROOT / "canon"
VALIDATE_ARTIFACT = SKILL_ROOT / "scripts" / "validate-artifact.py"


def _severity_rank() -> dict[str, int]:
    data = tomllib.loads((CANON_DIR / "severity-anchors.toml").read_text())
    return {label: i for i, label in enumerate(data["severity_anchors"])}


def _load_expected(fixture_id: str) -> dict:
    p = FIXTURES_DIR / fixture_id / "expected.toml"
    if not p.exists():
        sys.exit(f"FAIL: fixture '{fixture_id}' has no expected.toml ({p})")
    return tomllib.loads(p.read_text())


def _load_artifact(artifact_dir: Path) -> dict:
    p = artifact_dir / "CURRENT_REVIEW.json"
    if not p.exists():
        sys.exit(f"FAIL: no CURRENT_REVIEW.json in {artifact_dir}")
    return json.loads(p.read_text())


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        sys.exit("usage: loop_replay_grade.py <fixture-id> <artifact-dir> [--strict-exit]")
    fixture_id, artifact_dir = args[0], Path(args[1]).resolve()

    expected = _load_expected(fixture_id)
    artifact = _load_artifact(artifact_dir)
    sev_rank = _severity_rank()

    required: list[tuple[str, bool, str]] = []  # (label, passed, detail)
    advisory: list[tuple[str, str]] = []

    # ---- STRUCTURAL ----
    proc = subprocess.run(
        [sys.executable, str(VALIDATE_ARTIFACT), str(artifact_dir), "--mode", "strict"],
        capture_output=True, text=True,
    )
    required.append((
        "structural: validate-artifact --mode strict exits 0",
        proc.returncode == 0,
        (proc.stdout + proc.stderr).strip().splitlines()[-1] if (proc.stdout or proc.stderr) else "",
    ))

    findings_list = [f for f in artifact.get("findings", []) if isinstance(f, dict)]
    required.append((
        "structural: findings[] is non-empty", bool(findings_list),
        f"count={len(findings_list)}",
    ))

    loop_result = artifact.get("loop_result") or {}
    tfs = loop_result.get("targeted_finding_status")
    required.append((
        "structural: loop_result.targeted_finding_status valid enum",
        tfs in {"resolved", "carried_forward"},
        f"status={tfs!r}",
    ))

    # ---- SEMANTIC ----
    # Identify the planted finding. priority_1_finding_id / loop_result.targeted_finding_id are
    # both null once the priority-1 finding is RESOLVED this loop (a real schema fact this harness
    # surfaced), so we don't depend on them: prefer an explicit targeted id if present, else fall
    # back to the highest-severity finding whose evidence cites the planted primary_file.
    primary = expected["primary_file"]

    def _cites(f: dict) -> bool:
        return any(primary in str(e) for e in (f.get("evidence") or []))

    targeted_id = loop_result.get("targeted_finding_id") or artifact.get("priority_1_finding_id")
    by_id = {f.get("id"): f for f in findings_list}
    planted = by_id.get(targeted_id) if targeted_id else None
    if planted is None or not _cites(planted):
        citing = sorted(
            (f for f in findings_list if _cites(f)),
            key=lambda f: sev_rank.get(f.get("severity"), -1),
            reverse=True,
        )
        planted = citing[0] if citing else None

    required.append((
        "semantic: a finding cites the planted primary_file (debt was found)",
        planted is not None, f"primary_file={primary!r}",
    ))
    if planted is not None:
        sev = planted.get("severity")
        floor = expected["min_severity"]
        required.append((
            "semantic: that finding's severity >= min_severity",
            sev in sev_rank and sev_rank[sev] >= sev_rank[floor],
            f"severity={sev!r} floor={floor!r} id={planted.get('id')!r}",
        ))

    what_changed = str(loop_result.get("what_changed") or "")
    required.append((
        "semantic: loop_result.what_changed references primary_file (fix touched planted file)",
        primary in what_changed, f"primary_file={primary!r} present={primary in what_changed}",
    ))

    exp_status = expected["expected_targeted_finding_status"]
    required.append((
        "semantic: loop_result.targeted_finding_status == expected (planted debt fixed)",
        tfs == exp_status, f"got={tfs!r} expected={exp_status!r}",
    ))

    # ---- ADVISORY (never affects exit) ----
    dim = expected["targeted_dimension"]
    scorecard = artifact.get("scorecard") or {}
    dim_entry = scorecard.get(dim)
    score = dim_entry.get("score") if isinstance(dim_entry, dict) else dim_entry
    advisory.append((
        f"advisory: scorecard[{dim}] present (movement vs baseline once measured)",
        f"score={score!r}",
    ))

    # ---- REPORT ----
    print(f"loop_replay_grade: fixture '{fixture_id}' @ {artifact_dir}")
    n_fail = 0
    for label, passed, detail in required:
        mark = "PASS" if passed else "FAIL"
        if not passed:
            n_fail += 1
        print(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))
    for label, detail in advisory:
        print(f"  [INFO] {label}" + (f"  ({detail})" if detail else ""))

    if n_fail:
        print(f"loop_replay_grade: FAIL ({n_fail} required invariant(s) failed)")
        return 1
    print("loop_replay_grade: OK (all required invariants hold)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
