#!/usr/bin/env python3
"""Self-test: the principal-defect scenario manifest accounts for every scenario.

Guards the "no silent exclusion" contract for the Layer-2 domain-grain extension:
every evals/scenarios/principal-* directory must be registered in
evals/principal_baseline.json, every flag scenario must have a matching
restraint twin via pair_id, every manifest entry must point to an existing
scenario directory, and all status/kind/expected_baseline values must be valid
enums.

RED-first: run this before creating scenarios or the manifest to confirm it fails.
Then build those artifacts and confirm it passes.

Run: python3 scripts/_principal_baseline_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = SKILL_ROOT / "evals"
SCENARIOS_DIR = EVALS_DIR / "scenarios"
MANIFEST_PATH = EVALS_DIR / "principal_baseline.json"

VALID_KINDS = {"flag", "restraint"}
VALID_STATUSES = {"baseline_unmeasured", "measured"}
VALID_EXPECTED_BASELINES = {"miss", "hold"}
VALID_DECISIONS = {"caught", "held", "inconclusive"}
REPLICATION_PATH = EVALS_DIR / "principal_baseline_replication.json"


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        print(f"FAIL: manifest not found: {MANIFEST_PATH.relative_to(SKILL_ROOT)}")
        sys.exit(1)
    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _collect_principal_dirs() -> list[str]:
    """Return sorted list of principal-* scenario directory names."""
    if not SCENARIOS_DIR.exists():
        return []
    return sorted(p.name for p in SCENARIOS_DIR.iterdir() if p.is_dir() and p.name.startswith("principal-"))


def _check_replication(entries: list, failures: list[str]) -> None:
    """Validate the Phase-1 `replication` blocks + artifacts↔manifest consistency.

    Only runs when at least one entry carries a `replication` block (so the
    contract is dormant until Lever 1 has been recorded). Checks block shape,
    the kind-specific floor ordering (flags: semantic.caught <= mechanical.caught;
    twins: mechanical.held <= semantic.held), and that the raw artifacts file has
    exactly 5 terminal slots per re-run scenario with consistent invalid counts.
    """
    repl_entries = [e for e in entries if isinstance(e, dict) and "replication" in e]
    if not repl_entries:
        return

    # Load raw artifacts; group attempts by scenario.
    artifacts_attempts: dict[str, list[dict]] = {}
    if REPLICATION_PATH.exists():
        with REPLICATION_PATH.open(encoding="utf-8") as fh:
            art = json.load(fh)
        for a in art.get("attempts", []):
            artifacts_attempts.setdefault(a.get("scenario_id", "?"), []).append(a)
    else:
        failures.append(f"replication recorded in manifest but artifacts file missing: {REPLICATION_PATH.name}")

    for e in repl_entries:
        sid = e.get("id", "<missing id>")
        kind = e.get("kind")
        rep = e["replication"]
        if rep.get("excluded"):
            if not rep.get("reason"):
                failures.append(f"replication '{sid}': excluded block needs a 'reason'")
            continue

        field = "caught" if kind == "flag" else "held"
        for key in ("runs", "invalid_slots", "decision", "mechanical", "semantic"):
            if key not in rep:
                failures.append(f"replication '{sid}': missing key '{key}'")
        if rep.get("runs") != 5:
            failures.append(f"replication '{sid}': runs={rep.get('runs')!r} must be 5")
        if rep.get("decision") not in VALID_DECISIONS:
            failures.append(f"replication '{sid}': decision={rep.get('decision')!r} not in {sorted(VALID_DECISIONS)}")
        mech, sem = rep.get("mechanical", {}), rep.get("semantic", {})
        inv = rep.get("invalid_slots", 0)
        m, s = mech.get(field), sem.get(field)
        if not isinstance(m, int) or not isinstance(s, int):
            failures.append(f"replication '{sid}': mechanical/semantic missing int '{field}'")
            continue
        if m + inv > 5:
            failures.append(f"replication '{sid}': mechanical.{field}({m}) + invalid_slots({inv}) > 5")
        # kind-specific floor ordering
        if kind == "flag" and s > m:
            failures.append(f"replication '{sid}': flag semantic.caught({s}) must be <= mechanical.caught({m}) (named-the-defect is a subset)")
        if kind == "restraint" and m > s:
            failures.append(f"replication '{sid}': twin mechanical.held({m}) must be <= semantic.held({s}) (mechanical is the strict floor)")
        if rep.get("headline_excluded") and not rep.get("contaminated"):
            failures.append(f"replication '{sid}': headline_excluded implies contaminated")

        # artifacts↔manifest consistency
        atts = artifacts_attempts.get(sid)
        if atts is None:
            failures.append(f"replication '{sid}': no attempts in artifacts file")
            continue
        terminal: dict = {}
        for a in atts:
            si = a.get("slot_index")
            if si not in terminal or a.get("attempt_index", 1) > terminal[si].get("attempt_index", 1):
                terminal[si] = a
        if len(terminal) != 5:
            failures.append(f"replication '{sid}': artifacts have {len(terminal)} terminal slots, expected 5")
        # no attempt 2 after a valid attempt 1
        first = {a.get("slot_index"): a for a in atts if a.get("attempt_index") == 1}
        for a in atts:
            si = a.get("slot_index")
            if a.get("attempt_index", 1) >= 2 and first.get(si, {}).get("status") == "valid":
                failures.append(f"replication '{sid}': slot {si} has a retry attempt after a valid attempt 1")
        n_inv = sum(1 for a in terminal.values() if a.get("status") != "valid")
        if n_inv != inv:
            failures.append(f"replication '{sid}': invalid_slots={inv} but artifacts show {n_inv} terminal-invalid slots")
        for a in terminal.values():
            if a.get("status") == "valid":
                if a.get("verdict_json") is None or a.get("host_grade") is None:
                    failures.append(f"replication '{sid}': valid slot {a.get('slot_index')} missing verdict_json/host_grade")
            elif not a.get("invalid_reason"):
                failures.append(f"replication '{sid}': invalid slot {a.get('slot_index')} missing invalid_reason")


def main() -> int:
    failures: list[str] = []

    # (a) Discover all principal-* scenario dirs on disk.
    principal_dirs = _collect_principal_dirs()

    # (b) Load manifest; fail fast if missing.
    manifest = _load_manifest()
    entries = manifest.get("scenarios", [])
    registered_ids = {e["id"] for e in entries if isinstance(e, dict) and "id" in e}

    # Check (a): every on-disk principal-* dir is registered in the manifest.
    for dirname in principal_dirs:
        if dirname not in registered_ids:
            failures.append(
                f"scenario dir '{dirname}' exists on disk but is NOT registered "
                f"in {MANIFEST_PATH.name} (silent exclusion)"
            )

    # Check (c): every manifest entry points to an existing scenario dir.
    for entry in entries:
        if not isinstance(entry, dict):
            failures.append(f"manifest entry is not a dict: {entry!r}")
            continue
        entry_id = entry.get("id", "<missing id>")
        scenario_path = SCENARIOS_DIR / entry_id
        if not scenario_path.is_dir():
            failures.append(
                f"manifest entry '{entry_id}' points to a missing scenario dir: "
                f"{scenario_path.relative_to(SKILL_ROOT)}"
            )

    # Check (d): status / kind / expected_baseline are valid enums.
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id", "<missing id>")
        kind = entry.get("kind")
        if kind not in VALID_KINDS:
            failures.append(
                f"entry '{entry_id}': kind={kind!r} is not one of {sorted(VALID_KINDS)}"
            )
        status = entry.get("status")
        if status not in VALID_STATUSES:
            failures.append(
                f"entry '{entry_id}': status={status!r} is not one of {sorted(VALID_STATUSES)}"
            )
        expected_baseline = entry.get("expected_baseline")
        if expected_baseline not in VALID_EXPECTED_BASELINES:
            failures.append(
                f"entry '{entry_id}': expected_baseline={expected_baseline!r} "
                f"is not one of {sorted(VALID_EXPECTED_BASELINES)}"
            )

    # Check (b): every flag entry has a matching restraint twin via pair_id.
    pair_id_to_entries: dict[str, list[dict]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        pair_id = entry.get("pair_id")
        if pair_id is not None:
            pair_id_to_entries.setdefault(pair_id, []).append(entry)

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id", "<missing id>")
        kind = entry.get("kind")
        pair_id = entry.get("pair_id")
        if kind == "flag":
            if pair_id is None:
                failures.append(
                    f"flag entry '{entry_id}' has no pair_id (every flag must have a restraint twin)"
                )
                continue
            siblings = pair_id_to_entries.get(pair_id, [])
            sibling_kinds = {e.get("kind") for e in siblings}
            if "restraint" not in sibling_kinds:
                failures.append(
                    f"flag entry '{entry_id}' (pair_id={pair_id!r}) has no matching "
                    f"restraint twin in the manifest"
                )
        elif kind == "restraint":
            if pair_id is None:
                failures.append(
                    f"restraint entry '{entry_id}' has no pair_id (every restraint must reference a flag)"
                )
                continue
            siblings = pair_id_to_entries.get(pair_id, [])
            sibling_kinds = {e.get("kind") for e in siblings}
            if "flag" not in sibling_kinds:
                failures.append(
                    f"restraint entry '{entry_id}' (pair_id={pair_id!r}) has no matching "
                    f"flag entry in the manifest"
                )

    # Check (e): Phase-1 replication blocks + artifacts consistency (dormant until recorded).
    _check_replication(entries, failures)

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    n = len(entries)
    print(
        f"OK: principal_baseline.json accounts for {n} scenario(s); "
        f"{len(principal_dirs)} on-disk dirs registered; "
        "all pair_id/kind/status/expected_baseline valid"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
