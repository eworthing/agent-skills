#!/usr/bin/env python3
"""Self-test for the Layer-4 loop-replay regression harness (evals/loop-fixtures/).

Guards fixture well-formedness so a loop-replay measurement is defensible — mirrors
`_reviewer_baseline_selftest.py` / `_principal_baseline_selftest.py`. Mechanical only;
runs no model. Exit 0 = pass, 1 = fail (every failure is printed first).

Checks:
  (a) no silent exclusion — every evals/loop-fixtures/<id>/ dir is registered in the manifest
  (b) every manifest fixture points to an existing dir with the required members
      (codebase/ tree + expected.toml)
  (c) each expected.toml parses, carries the required keys, and uses canon-valid enums
      (targeted_dimension ∈ canon scorecard dims; min_severity ∈ canon severity anchors;
       expected_targeted_finding_status ∈ {resolved, carried_forward})
  (d) manifest consistency — status ∈ {baseline_unmeasured, measured}; a measured fixture
      must carry a non-null baseline_observed
  (e) two-arm schema — when baseline_observed.arms is present (the efficiency RED->GREEN
      fixtures), each arm is named red/green and carries the preregistered fields; a
      measured fixture with arms must carry both arms (legacy single-arm shape stays valid)
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = SKILL_ROOT / "evals"
FIXTURES_DIR = EVALS_DIR / "loop-fixtures"
MANIFEST_PATH = EVALS_DIR / "loop_replay_baseline.json"
CANON_DIR = SKILL_ROOT / "canon"

REQUIRED_MEMBERS = ("codebase", "expected.toml")
REQUIRED_EXPECTED_KEYS = (
    "id",
    "primary_file",
    "smell",
    "targeted_dimension",
    "min_severity",
    "expected_targeted_finding_status",
    "lens",
)
VALID_STATUS = {"baseline_unmeasured", "measured"}
VALID_FINDING_STATUS = {"resolved", "carried_forward"}
VALID_ARM_NAMES = {"red", "green"}
REQUIRED_ARM_KEYS = (
    "skill_commit",
    "run_commit",
    "observed_at",
    "model",
    "grader_exit",
    "failed_invariants",
    "planted_finding_detected",
    "other_efficiency_findings",
    "note",
)


def _load_canon_dimensions() -> set[str]:
    data = tomllib.loads((CANON_DIR / "scorecard-dimensions.toml").read_text())
    return {d["id"] for d in data["scorecard_dimensions"]}


def _load_canon_severities() -> set[str]:
    data = tomllib.loads((CANON_DIR / "severity-anchors.toml").read_text())
    return set(data["severity_anchors"])


def _collect_fixture_dirs() -> list[str]:
    if not FIXTURES_DIR.exists():
        return []
    return sorted(p.name for p in FIXTURES_DIR.iterdir() if p.is_dir())


def main() -> int:
    failures: list[str] = []

    if not MANIFEST_PATH.exists():
        print(f"FAIL: manifest not found: {MANIFEST_PATH.relative_to(SKILL_ROOT)}")
        return 1
    try:
        manifest = json.loads(MANIFEST_PATH.read_text())
    except json.JSONDecodeError as exc:
        print(f"FAIL: manifest is not valid JSON: {exc}")
        return 1

    canon_dims = _load_canon_dimensions()
    canon_sevs = _load_canon_severities()

    fixture_dirs = _collect_fixture_dirs()
    entries = manifest.get("fixtures", [])
    registered_ids = {e["id"] for e in entries if isinstance(e, dict) and "id" in e}

    # (a) no silent exclusion
    for dirname in fixture_dirs:
        if dirname not in registered_ids:
            failures.append(f"fixture dir '{dirname}' is not registered in the manifest")

    if not fixture_dirs:
        failures.append("no fixture dirs found under evals/loop-fixtures/ (need >= 1)")
    if not entries:
        failures.append("manifest registers no fixtures (need >= 1)")

    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry:
            failures.append(f"manifest fixture entry malformed (no id): {entry!r}")
            continue
        fid = entry["id"]
        fdir = FIXTURES_DIR / fid

        # (b) required members
        if not fdir.is_dir():
            failures.append(f"fixture '{fid}': dir does not exist")
            continue
        for member in REQUIRED_MEMBERS:
            if not (fdir / member).exists():
                failures.append(f"fixture '{fid}': missing required member '{member}'")

        # (d) manifest consistency
        status = entry.get("status")
        if status not in VALID_STATUS:
            failures.append(f"fixture '{fid}': status '{status}' not in {sorted(VALID_STATUS)}")
        if status == "measured" and not entry.get("baseline_observed"):
            failures.append(f"fixture '{fid}': status=measured but baseline_observed is empty")

        # (e) two-arm schema (efficiency RED->GREEN fixtures; legacy single-arm shape valid)
        arms = (entry.get("baseline_observed") or {}).get("arms")
        if arms is not None:
            if not isinstance(arms, dict) or not arms:
                failures.append(
                    f"fixture '{fid}': baseline_observed.arms must be a non-empty object"
                )
            else:
                for arm_name, arm in arms.items():
                    if arm_name not in VALID_ARM_NAMES:
                        failures.append(
                            f"fixture '{fid}': arm '{arm_name}' not in {sorted(VALID_ARM_NAMES)}"
                        )
                        continue
                    if not isinstance(arm, dict):
                        failures.append(f"fixture '{fid}': arm '{arm_name}' is not an object")
                        continue
                    for key in REQUIRED_ARM_KEYS:
                        if key not in arm:
                            failures.append(
                                f"fixture '{fid}': arm '{arm_name}' missing key '{key}'"
                            )
                if status == "measured" and not set(arms) >= VALID_ARM_NAMES:
                    failures.append(
                        f"fixture '{fid}': status=measured with arms requires both red and green"
                    )

        # (c) expected.toml
        exp_path = fdir / "expected.toml"
        if not exp_path.exists():
            continue
        try:
            exp = tomllib.loads(exp_path.read_text())
        except tomllib.TOMLDecodeError as exc:
            failures.append(f"fixture '{fid}': expected.toml does not parse: {exc}")
            continue
        for key in REQUIRED_EXPECTED_KEYS:
            if key not in exp:
                failures.append(f"fixture '{fid}': expected.toml missing key '{key}'")
        if exp.get("id") != fid:
            failures.append(f"fixture '{fid}': expected.toml id '{exp.get('id')}' != dir name")
        if exp.get("targeted_dimension") not in canon_dims:
            failures.append(
                f"fixture '{fid}': targeted_dimension '{exp.get('targeted_dimension')}' "
                f"not a canon scorecard dimension"
            )
        if exp.get("min_severity") not in canon_sevs:
            failures.append(
                f"fixture '{fid}': min_severity '{exp.get('min_severity')}' not a canon severity anchor"
            )
        if exp.get("expected_targeted_finding_status") not in VALID_FINDING_STATUS:
            failures.append(
                f"fixture '{fid}': expected_targeted_finding_status "
                f"'{exp.get('expected_targeted_finding_status')}' not in {sorted(VALID_FINDING_STATUS)}"
            )

    if failures:
        print(f"_loop_replay_selftest: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"_loop_replay_selftest: OK ({len(entries)} fixture(s) registered, all well-formed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
