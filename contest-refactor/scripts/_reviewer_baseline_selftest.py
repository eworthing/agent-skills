#!/usr/bin/env python3
"""Self-test: the reviewer-judgment baseline manifest accounts for every case.

Guards the "no silent exclusion" contract for the reviewer-judgment regression
harness (evals/reviewer-cases/). The harness measures the implementation
reviewer (references/implementation-reviewer.md) at its own input grain —
{targeted finding, diff} -> verdict JSON — so a reviewer model-tier change can
be shown not to regress verification efficacy. The flag/restraint scenario
harness (principal_baseline.json) grades only the Critic, never the reviewer, so
this is a separate, net-new baseline.

Contract enforced here (mechanical, no model):
  (a) every evals/reviewer-cases/<id>/ directory is registered in
      evals/reviewer_baseline.json cases[]  (silent-exclusion guard);
  (b) every paired case has its twin: a reject case in a pair has an approve
      (restraint) twin via pair_id and vice versa — the honesty backbone that
      catches a reject-everything reviewer;
  (c) every manifest entry points to an existing case dir holding the four
      required members (case.toml, finding.md, base/, head/);
  (d) verdict_class / check_under_test / status / danger_class are valid enums
      and expected_verdict is one of canon/verdicts.toml;
  (e) measured-mode consistency (dormant until a case is status="measured"):
      both arms present with runs==5, semantic <= mechanical (named-defect /
      over-flag-free is a subset of the mechanical verdict), and the asymmetric
      false_approve_tolerance — NO measured must-reject case (danger_class ==
      "false_approve") may have arm_b.decision == "approve"; plus the raw
      replication file carries exactly 5 terminal slots per case per arm.

RED-first: run this before creating the cases or the manifest to confirm it
fails. Then build those artifacts and confirm it passes.

Run: python3 scripts/_reviewer_baseline_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _canon import load_canon

SKILL_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = SKILL_ROOT / "evals"
CASES_DIR = EVALS_DIR / "reviewer-cases"
MANIFEST_PATH = EVALS_DIR / "reviewer_baseline.json"
REPLICATION_PATH = EVALS_DIR / "reviewer_baseline_replication.json"

VALID_VERDICT_CLASSES = {"reject", "approve", "conditional"}
VALID_CHECKS = {"reality", "honesty", "regression"}
VALID_STATUSES = {"baseline_unmeasured", "measured"}
VALID_DANGER = {"false_approve", "false_reject", "none"}
VALID_DECISIONS = {"reject", "approve", "conditional", "inconclusive"}
REQUIRED_CASE_MEMBERS = ("case.toml", "finding.md", "base", "head")


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        print(f"FAIL: manifest not found: {MANIFEST_PATH.relative_to(SKILL_ROOT)}")
        sys.exit(1)
    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _collect_case_dirs() -> list[str]:
    """Return sorted list of reviewer-case directory names."""
    if not CASES_DIR.exists():
        return []
    return sorted(p.name for p in CASES_DIR.iterdir() if p.is_dir())


def _check_arm(case_id: str, arm_name: str, arm: dict, failures: list[str]) -> None:
    """Validate one arm block of a measured case."""
    for key in ("model", "runs", "invalid_slots", "decision", "mechanical", "semantic"):
        if key not in arm:
            failures.append(f"case '{case_id}' {arm_name}: missing key '{key}'")
    if arm.get("runs") != 5:
        failures.append(f"case '{case_id}' {arm_name}: runs={arm.get('runs')!r} must be 5")
    if arm.get("decision") not in VALID_DECISIONS:
        failures.append(
            f"case '{case_id}' {arm_name}: decision={arm.get('decision')!r} "
            f"not in {sorted(VALID_DECISIONS)}"
        )
    mech, sem = arm.get("mechanical", {}), arm.get("semantic", {})
    inv = arm.get("invalid_slots", 0)
    m, s = mech.get("hits"), sem.get("hits")
    if not isinstance(m, int) or not isinstance(s, int):
        failures.append(f"case '{case_id}' {arm_name}: mechanical/semantic missing int 'hits'")
        return
    if not isinstance(inv, int) or m + inv > 5:
        failures.append(
            f"case '{case_id}' {arm_name}: mechanical.hits({m}) + invalid_slots({inv}) > 5"
        )
    # semantic (named-the-defect / carve-out-not-flagged) is a subset of the
    # mechanical verdict — you cannot name the defect on a run you did not reject.
    if s > m:
        failures.append(
            f"case '{case_id}' {arm_name}: semantic.hits({s}) must be <= mechanical.hits({m}) "
            "(semantic is a subset of the mechanical verdict)"
        )


def _check_replication_raw(measured_ids: set[str], failures: list[str]) -> None:
    """Each measured case has exactly 5 terminal slots per arm in the raw file."""
    if not measured_ids:
        return
    if not REPLICATION_PATH.exists():
        failures.append(
            f"cases marked measured but raw replication file missing: {REPLICATION_PATH.name}"
        )
        return
    with REPLICATION_PATH.open(encoding="utf-8") as fh:
        art = json.load(fh)
    # group attempts by (case_id, arm)
    attempts: dict[tuple[str, str], list[dict]] = {}
    for a in art.get("attempts", []):
        attempts.setdefault((a.get("case_id", "?"), a.get("arm", "?")), []).append(a)
    for cid in sorted(measured_ids):
        for arm in ("arm_a", "arm_b"):
            atts = attempts.get((cid, arm))
            if not atts:
                failures.append(f"case '{cid}' {arm}: no attempts in {REPLICATION_PATH.name}")
                continue
            terminal: dict = {}
            for a in atts:
                si = a.get("slot_index")
                if si not in terminal or a.get("attempt_index", 1) > terminal[si].get(
                    "attempt_index", 1
                ):
                    terminal[si] = a
            if len(terminal) != 5:
                failures.append(
                    f"case '{cid}' {arm}: raw file has {len(terminal)} terminal slots, expected 5"
                )


def main() -> int:
    failures: list[str] = []
    canon = load_canon(SKILL_ROOT)
    valid_verdicts = set(canon.verdicts)

    # (a) discover all reviewer-case dirs on disk.
    case_dirs = _collect_case_dirs()

    # load manifest; fail fast if missing.
    manifest = _load_manifest()
    entries = manifest.get("cases", [])
    registered_ids = {e["id"] for e in entries if isinstance(e, dict) and "id" in e}

    # (a) every on-disk case dir is registered.
    for dirname in case_dirs:
        if dirname not in registered_ids:
            failures.append(
                f"case dir '{dirname}' exists on disk but is NOT registered in "
                f"{MANIFEST_PATH.name} (silent exclusion)"
            )

    # (c) every manifest entry points to an existing dir with the required members.
    for entry in entries:
        if not isinstance(entry, dict):
            failures.append(f"manifest entry is not a dict: {entry!r}")
            continue
        entry_id = entry.get("id", "<missing id>")
        case_path = CASES_DIR / entry_id
        if not case_path.is_dir():
            failures.append(
                f"manifest entry '{entry_id}' points to a missing case dir: "
                f"{case_path.relative_to(SKILL_ROOT)}"
            )
            continue
        for member in REQUIRED_CASE_MEMBERS:
            if not (case_path / member).exists():
                failures.append(f"case '{entry_id}' is missing required member '{member}'")

    # (d) enum validity.
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id", "<missing id>")
        vc = entry.get("verdict_class")
        if vc not in VALID_VERDICT_CLASSES:
            failures.append(
                f"entry '{entry_id}': verdict_class={vc!r} not in {sorted(VALID_VERDICT_CLASSES)}"
            )
        cut = entry.get("check_under_test")
        if cut not in VALID_CHECKS:
            failures.append(
                f"entry '{entry_id}': check_under_test={cut!r} not in {sorted(VALID_CHECKS)}"
            )
        status = entry.get("status")
        if status not in VALID_STATUSES:
            failures.append(
                f"entry '{entry_id}': status={status!r} not in {sorted(VALID_STATUSES)}"
            )
        danger = entry.get("danger_class")
        if danger not in VALID_DANGER:
            failures.append(
                f"entry '{entry_id}': danger_class={danger!r} not in {sorted(VALID_DANGER)}"
            )
        expected = entry.get("expected_verdict")
        if expected not in valid_verdicts:
            failures.append(
                f"entry '{entry_id}': expected_verdict={expected!r} not in canon verdicts {sorted(valid_verdicts)}"
            )

    # (b) twin pairing: a paired reject case needs an approve twin and vice versa.
    pair_to_classes: dict[str, set[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        pid = entry.get("pair_id")
        if pid is not None:
            pair_to_classes.setdefault(pid, set()).add(entry.get("verdict_class"))
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id", "<missing id>")
        vc = entry.get("verdict_class")
        pid = entry.get("pair_id")
        if pid is None:
            continue  # standalone positive control / conditional — exempt
        classes = pair_to_classes.get(pid, set())
        if vc == "reject" and "approve" not in classes:
            failures.append(
                f"reject case '{entry_id}' (pair_id={pid!r}) has no approve (restraint) twin in the manifest"
            )
        if vc == "approve" and "reject" not in classes:
            failures.append(
                f"approve case '{entry_id}' (pair_id={pid!r}) has no reject twin in the manifest"
            )

    # (e) measured-mode consistency (dormant until any case is measured).
    measured_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") != "measured":
            continue
        entry_id = entry.get("id", "<missing id>")
        measured_ids.add(entry_id)
        arms = entry.get("arms")
        if not isinstance(arms, dict) or "arm_a" not in arms or "arm_b" not in arms:
            failures.append(f"measured case '{entry_id}': arms.arm_a and arms.arm_b required")
            continue
        _check_arm(entry_id, "arm_a", arms["arm_a"], failures)
        _check_arm(entry_id, "arm_b", arms["arm_b"], failures)
        # the asymmetric gate: a must-reject case may never measure arm_b as approve.
        if (
            entry.get("danger_class") == "false_approve"
            and arms["arm_b"].get("decision") == "approve"
        ):
            failures.append(
                f"measured case '{entry_id}': arm_b.decision='approve' on a false_approve case "
                "violates false_approve_tolerance=0 (cheaper reviewer must not rubber-stamp a must-reject diff)"
            )
    _check_replication_raw(measured_ids, failures)

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    n = len(entries)
    print(
        f"OK: reviewer_baseline.json accounts for {n} case(s); "
        f"{len(case_dirs)} on-disk dir(s) registered; "
        f"{len(measured_ids)} measured; all enums/twins valid"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
