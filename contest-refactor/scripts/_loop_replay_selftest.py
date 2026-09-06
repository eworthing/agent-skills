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
      fixtures), each arm is named red/green and carries the preregistered fields with
      their declared types; a measured fixture with arms must carry both arms (legacy
      single-arm shape stays valid), and a measured efficiency fixture (expected.toml
      notes.red_baseline) must use the arms shape
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
# Preregistered per-arm fields WITH the types arm_schema declares (loop_replay_baseline.json
# § prereg.arm_schema) — presence alone would let a hand-recorded planted_finding_detected
# of "no" (truthy string) silently score as a detection in the RED-vs-GREEN comparison.
ARM_KEY_TYPES = {
    "skill_commit": str,
    "run_commit": str,
    "observed_at": str,
    "model": str,
    "grader_exit": int,
    "failed_invariants": list,
    "planted_finding_detected": bool,
    "other_efficiency_findings": int,
    "note": str,
}


_CANON_LOAD_ERRORS = (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError)


def _load_canon_dimensions() -> set[str]:
    try:
        data = tomllib.loads((CANON_DIR / "scorecard-dimensions.toml").read_text(encoding="utf-8"))
        return {d["id"] for d in data["scorecard_dimensions"]}
    except _CANON_LOAD_ERRORS as exc:
        print(f"FAIL: cannot load canon scorecard-dimensions.toml: {exc}")
        sys.exit(1)


def _load_canon_severities() -> set[str]:
    try:
        data = tomllib.loads((CANON_DIR / "severity-anchors.toml").read_text(encoding="utf-8"))
        return set(data["severity_anchors"])
    except _CANON_LOAD_ERRORS as exc:
        print(f"FAIL: cannot load canon severity-anchors.toml: {exc}")
        sys.exit(1)


def _collect_fixture_dirs() -> list[str]:
    if not FIXTURES_DIR.exists():
        return []
    return sorted(p.name for p in FIXTURES_DIR.iterdir() if p.is_dir())


def _check_arms(fid: str, status: object, arms: object) -> list[str]:
    """Check (e): arms named red/green, each carrying the preregistered fields with the
    declared types (bool fields reject truthy strings; int fields reject bools)."""
    if not isinstance(arms, dict) or not arms:
        return [f"fixture '{fid}': baseline_observed.arms must be a non-empty object"]
    failures: list[str] = []
    for arm_name, arm in arms.items():
        if arm_name not in VALID_ARM_NAMES:
            failures.append(f"fixture '{fid}': arm '{arm_name}' not in {sorted(VALID_ARM_NAMES)}")
            continue
        if not isinstance(arm, dict):
            failures.append(f"fixture '{fid}': arm '{arm_name}' is not an object")
            continue
        for key, want in ARM_KEY_TYPES.items():
            if key not in arm:
                failures.append(f"fixture '{fid}': arm '{arm_name}' missing key '{key}'")
                continue
            value = arm[key]
            if not isinstance(value, want) or (want is int and isinstance(value, bool)):
                failures.append(
                    f"fixture '{fid}': arm '{arm_name}' key '{key}' must be "
                    f"{want.__name__}, got {type(value).__name__}"
                )
    if status == "measured" and not set(arms) >= VALID_ARM_NAMES:
        failures.append(f"fixture '{fid}': status=measured with arms requires both red and green")
    return failures


def _check_deferral_missing_primary_file_fails_loud(failures: list[str]) -> None:
    """A `--deferral-only` fixture whose expected.toml is missing
    expected_escalated_primary_file must FAIL loud (OCR-1013-1033), not default
    the target file to "" -- which matches every finding's evidence string and
    silently turns ABSENT into ESCALATED-by-dropping.

    Note: `_deferral_only` lives in loop_replay_grade.py but reads from
    evals/priority-fixtures/ (PRIORITY_FIXTURES_DIR), a different fixture family
    than this file's own evals/loop-fixtures/ well-formedness checks -- this case
    is added here because the finding's own `simplify.test` field names this
    file; scripts/_priority_replay_selftest.py is the module-correct home.
    """
    import tempfile

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import loop_replay_grade as L

    with tempfile.TemporaryDirectory() as td:
        priority_dir = Path(td) / "priority-fixtures"
        fixdir = priority_dir / "missing-primary-file-1"
        fixdir.mkdir(parents=True)
        (fixdir / "expected.toml").write_text(
            'id = "missing-primary-file-1"\n'
            'kind = "deferral"\n'
            'expected_escalated_stable_id = "F-1"\n'
            'expected_escalated_dimension = "credibility"\n'
            'decoy_dimension = "architecture_quality"\n'
            'restraint_dimension = "framework_idioms"\n'
            # expected_escalated_primary_file deliberately absent
        )
        payload_path = Path(td) / "probe.json"
        payload_path.write_text(
            json.dumps(
                {
                    "backlog": [],
                    "findings": [
                        {"id": "F-2", "evidence": ["Sources/Unrelated.swift:1 unrelated"]}
                    ],
                }
            )
        )
        orig = L.PRIORITY_FIXTURES_DIR
        L.PRIORITY_FIXTURES_DIR = priority_dir
        try:
            L._deferral_only("missing-primary-file-1", payload_path)
        except SystemExit as exc:
            msg = str(exc.code)
        else:
            msg = None
        finally:
            L.PRIORITY_FIXTURES_DIR = orig
    if msg is None or "FAIL" not in msg:
        failures.append(
            f"deferral fixture missing expected_escalated_primary_file must FAIL loud, got {msg!r}"
        )


def main() -> int:
    failures: list[str] = []

    if not MANIFEST_PATH.exists():
        print(f"FAIL: manifest not found: {MANIFEST_PATH.relative_to(SKILL_ROOT)}")
        return 1
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"FAIL: manifest is not valid JSON: {exc}")
        return 1

    canon_dims = _load_canon_dimensions()
    canon_sevs = _load_canon_severities()

    fixture_dirs = _collect_fixture_dirs()
    if not isinstance(manifest, dict):
        print(f"FAIL: manifest root must be an object, got {type(manifest).__name__}")
        return 1
    entries = manifest.get("fixtures", [])
    if not isinstance(entries, list):
        print(f"FAIL: manifest 'fixtures' must be a list, got {type(entries).__name__}")
        return 1
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
        baseline = entry.get("baseline_observed")
        if status == "measured" and not baseline:
            failures.append(f"fixture '{fid}': status=measured but baseline_observed is empty")
        if baseline is not None and not isinstance(baseline, dict):
            failures.append(
                f"fixture '{fid}': baseline_observed must be an object, "
                f"got {type(baseline).__name__}"
            )
            baseline = None

        # (e) two-arm schema (efficiency RED->GREEN fixtures; legacy single-arm shape valid)
        arms = (baseline or {}).get("arms")
        if arms is not None:
            failures.extend(_check_arms(fid, status, arms))

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
        # Efficiency fixtures (notes.red_baseline marks the RED->GREEN protocol) must record
        # measurements in the two-arm shape — a flat legacy baseline_observed would silently
        # drop the RED arm the fixture exists to capture.
        if (
            status == "measured"
            and "red_baseline" in exp.get("notes", {})
            and not isinstance(arms, dict)
        ):
            failures.append(
                f"fixture '{fid}': efficiency fixture (notes.red_baseline present) is "
                f"measured without baseline_observed.arms — RED/GREEN arms required"
            )

    _check_deferral_missing_primary_file_fails_loud(failures)

    if failures:
        print(f"_loop_replay_selftest: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"_loop_replay_selftest: OK ({len(entries)} fixture(s) registered, all well-formed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
