#!/usr/bin/env python3
"""Self-test: the advisory-audit scenario manifest + the global evals.json no-orphan contract.

Two guards in one script:

1. **Advisory-manifest contract** (mirror of _principal_baseline_selftest.py) for the
   Layer-2 advisory-audit extension (evals.json #35-#48): every advisory-family scenario
   directory on disk is registered in evals/advisory_baseline.json, every flag has a
   matching restraint twin via pair_id, every manifest entry points to an existing dir,
   status/kind/expected_baseline are valid enums, flags pre-register `miss` and restraints
   pre-register `hold`, and the dormant replication block is shape-checked once recorded.

2. **Global no-orphan contract**: every evals/scenarios/* directory is referenced by at
   least one evals.json entry's files[], and every files[] path exists on disk. This closes
   the gap where no script validated evals.json at all, and makes "cutting" a degenerate
   scenario safe — a half-removed scenario (dir gone from evals.json but manifest still lists
   it, or vice-versa) fails here.

RED-first: run before creating the manifest/selftest to confirm it fails, then build and
confirm GREEN.

Run: python3 scripts/_advisory_baseline_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = SKILL_ROOT / "evals"
SCENARIOS_DIR = EVALS_DIR / "scenarios"
MANIFEST_PATH = EVALS_DIR / "advisory_baseline.json"
REPLICATION_PATH = EVALS_DIR / "advisory_baseline_replication.json"
EVALS_JSON_PATH = EVALS_DIR / "evals.json"

VALID_KINDS = {"flag", "restraint"}
VALID_STATUSES = {"baseline_unmeasured", "measured"}
VALID_EXPECTED_BASELINES = {"miss", "hold"}
VALID_DECISIONS = {"caught", "held", "inconclusive"}
VALID_ARMS = {"no_skill", "pre_edit", "current"}


def _load_json(path: Path, label: str) -> dict:
    if not path.exists():
        print(f"FAIL: {label} not found: {path.relative_to(SKILL_ROOT)}")
        sys.exit(1)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _collect_family_dirs(families: list[str]) -> list[str]:
    """Scenario dirs whose name starts with a declared advisory family prefix."""
    if not SCENARIOS_DIR.exists():
        return []
    out = []
    for p in SCENARIOS_DIR.iterdir():
        if not p.is_dir():
            continue
        if any(
            p.name == fam or p.name.startswith(fam + "-") or p.name.startswith(fam)
            for fam in families
        ) and (p.name.endswith("-flag") or p.name.endswith("-restraint")):
            out.append(p.name)
    return sorted(out)


def _evals_entries() -> list[dict]:
    data = _load_json(EVALS_JSON_PATH, "evals.json")
    ev = data["evals"] if isinstance(data, dict) else data
    return [e for e in ev if isinstance(e, dict)]


def _check_global_no_orphan(failures: list[str]) -> None:
    """Every scenarios/* dir referenced by evals.json; every files[] path exists."""
    entries = _evals_entries()
    referenced: set[str] = set()
    for e in entries:
        for f in e.get("files", []):
            fpath = EVALS_DIR / f
            if not fpath.exists():
                failures.append(f"evals.json id={e.get('id')!r} references missing file: {f}")
            parts = Path(f).parts
            if len(parts) >= 2 and parts[0] == "scenarios":
                referenced.add(parts[1])

    if not SCENARIOS_DIR.exists():
        return
    for p in sorted(SCENARIOS_DIR.iterdir()):
        if p.is_dir() and p.name not in referenced:
            failures.append(
                f"scenario dir '{p.name}' exists on disk but is referenced by NO "
                f"evals.json entry (orphaned scenario)"
            )


def _check_replication(entries: list, failures: list[str]) -> None:
    """Validate `replication` blocks + artifacts consistency; dormant until recorded."""
    repl_entries = [e for e in entries if isinstance(e, dict) and "replication" in e]
    if not repl_entries:
        return

    artifacts_attempts: dict[str, list[dict]] = {}
    if REPLICATION_PATH.exists():
        with REPLICATION_PATH.open(encoding="utf-8") as fh:
            art = json.load(fh)
        for a in art.get("attempts", []):
            artifacts_attempts.setdefault(a.get("scenario_id", "?"), []).append(a)
    else:
        failures.append(
            f"replication recorded in manifest but artifacts file missing: {REPLICATION_PATH.name}"
        )

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
            failures.append(
                f"replication '{sid}': decision={rep.get('decision')!r} not in {sorted(VALID_DECISIONS)}"
            )
        mech, sem = rep.get("mechanical", {}), rep.get("semantic", {})
        inv = rep.get("invalid_slots", 0)
        m, s = mech.get(field), sem.get(field)
        if not isinstance(m, int) or not isinstance(s, int):
            failures.append(f"replication '{sid}': mechanical/semantic missing int '{field}'")
            continue
        if m + inv > 5:
            failures.append(
                f"replication '{sid}': mechanical.{field}({m}) + invalid_slots({inv}) > 5"
            )
        if kind == "flag" and s > m:
            failures.append(
                f"replication '{sid}': flag semantic.caught({s}) must be <= mechanical.caught({m})"
            )
        if kind == "restraint" and m > s:
            failures.append(
                f"replication '{sid}': twin mechanical.held({m}) must be <= semantic.held({s})"
            )

        atts = artifacts_attempts.get(sid)
        if atts is None:
            failures.append(f"replication '{sid}': no attempts in artifacts file")
            continue
        for a in atts:
            if a.get("arm") not in VALID_ARMS:
                failures.append(
                    f"replication '{sid}': attempt arm={a.get('arm')!r} not in {sorted(VALID_ARMS)}"
                )
        # terminal slot per (arm, slot_index) for the `current` arm drives the decision
        current = [a for a in atts if a.get("arm") == "current"]
        terminal: dict = {}
        for a in current:
            si = a.get("slot_index")
            if si not in terminal or a.get("attempt_index", 1) > terminal[si].get(
                "attempt_index", 1
            ):
                terminal[si] = a
        if len(terminal) != 5:
            failures.append(
                f"replication '{sid}': current arm has {len(terminal)} terminal slots, expected 5"
            )
        n_inv = sum(1 for a in terminal.values() if a.get("status") != "valid")
        if n_inv != inv:
            failures.append(
                f"replication '{sid}': invalid_slots={inv} but current arm shows {n_inv} invalid"
            )
        for a in terminal.values():
            if a.get("status") == "valid":
                if a.get("verdict_json") is None or a.get("host_grade") is None:
                    failures.append(
                        f"replication '{sid}': valid slot {a.get('slot_index')} missing verdict_json/host_grade"
                    )
            elif not a.get("invalid_reason"):
                failures.append(
                    f"replication '{sid}': invalid slot {a.get('slot_index')} missing invalid_reason"
                )


def main() -> int:
    failures: list[str] = []

    manifest = _load_json(MANIFEST_PATH, "manifest")
    families = manifest.get("families", [])
    if not families:
        failures.append("manifest has no 'families' list (needed for no-silent-exclusion)")
    entries = manifest.get("scenarios", [])
    registered_ids = {e["id"] for e in entries if isinstance(e, dict) and "id" in e}

    # (a) every on-disk advisory-family dir is registered.
    for dirname in _collect_family_dirs(families):
        if dirname not in registered_ids:
            failures.append(
                f"scenario dir '{dirname}' matches an advisory family but is NOT registered "
                f"in {MANIFEST_PATH.name} (silent exclusion)"
            )

    # (c) every manifest entry points to an existing scenario dir.
    for entry in entries:
        if not isinstance(entry, dict):
            failures.append(f"manifest entry is not a dict: {entry!r}")
            continue
        entry_id = entry.get("id", "<missing id>")
        if not (SCENARIOS_DIR / entry_id).is_dir():
            failures.append(f"manifest entry '{entry_id}' points to a missing scenario dir")

    # (d) enums + pre-registration direction (flag=miss, restraint=hold).
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id", "<missing id>")
        kind = entry.get("kind")
        if kind not in VALID_KINDS:
            failures.append(f"entry '{entry_id}': kind={kind!r} not in {sorted(VALID_KINDS)}")
        if entry.get("status") not in VALID_STATUSES:
            failures.append(
                f"entry '{entry_id}': status={entry.get('status')!r} not in {sorted(VALID_STATUSES)}"
            )
        eb = entry.get("expected_baseline")
        if eb not in VALID_EXPECTED_BASELINES:
            failures.append(
                f"entry '{entry_id}': expected_baseline={eb!r} not in {sorted(VALID_EXPECTED_BASELINES)}"
            )
        elif kind == "flag" and eb != "miss":
            failures.append(
                f"entry '{entry_id}': flag must pre-register expected_baseline='miss', got {eb!r}"
            )
        elif kind == "restraint" and eb != "hold":
            failures.append(
                f"entry '{entry_id}': restraint must pre-register expected_baseline='hold', got {eb!r}"
            )

    # (b) twin pairing via pair_id.
    pair_map: dict[str, set] = {}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("pair_id"):
            pair_map.setdefault(entry["pair_id"], set()).add(entry.get("kind"))
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id", "<missing id>")
        pair_id = entry.get("pair_id")
        if pair_id is None:
            failures.append(f"entry '{entry_id}' has no pair_id")
            continue
        kinds = pair_map.get(pair_id, set())
        want = "restraint" if entry.get("kind") == "flag" else "flag"
        if want not in kinds:
            failures.append(f"entry '{entry_id}' (pair_id={pair_id!r}) has no matching {want} twin")

    # (e) dormant replication shape check.
    _check_replication(entries, failures)

    # global no-orphan contract.
    _check_global_no_orphan(failures)

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        f"OK: advisory_baseline.json accounts for {len(entries)} scenario(s) across "
        f"{len(families)} families; every scenarios/* dir referenced by evals.json; "
        "all pair_id/kind/status/expected_baseline valid"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
