#!/usr/bin/env python3
"""Self-test for the Layer-5 execution-grain harness (evals/exec-fixtures/).

The harness measures Step-3 (Execution) in isolation: it seeds the Step-1+2 output into a
pre-Step-3 repo and host-dispatches a Step-3-only executor (the gate for a future
Execution-unfuse). This selftest guards fixture well-formedness mechanically (no model) so a
measurement is defensible. It mirrors `_loop_replay_selftest.py` (dir discovery / members /
canon enums) + `_reviewer_baseline_selftest.py` (measured-mode arm gate), with net-new checks:
`kind`, conditional keys, the `seed/` tree, the dual-sha drift guard, and the
safety_tolerance-0 arm_b gate keyed on `kind`.

Checks:
  (a) no silent exclusion — every evals/exec-fixtures/<id>/ dir is registered in the manifest
  (b) members — each fixture dir has codebase/ + seed/{CURRENT_REVIEW.json,CURRENT_REVIEW.md,
      findings_registry.json} + expected.toml
  (c) expected.toml — parses; base + conditional required keys; canon-valid enums; id==dir
  (d) seed validity (targeted; the seed is intentionally pre-Step-3 = incomplete, so NOT full
      validate-artifact strict): CURRENT_REVIEW.json parses, state=="CONTINUE", findings[0]
      carries minimal_correction_path + blast_radius{change,avoid}, backlog[0].title ==
      findings[0].title, scorecard has all nine canon dims
  (e) dual-sha drift guard — recompute step3_executor_prompt_sha256 (the template) and
      skill_step3_section_sha256 (the SKILL.md "### Step 3" section) and assert they equal the
      manifest prereg (a prod Step-3 edit or template edit fails closed)
  (f) measured-mode consistency — status enum; a measured fixture carries arms.arm_a+arm_b; and
      for kind in {revert, risk_boundary} arm_b.safety_violation must be falsy (safety_tolerance 0)

`--print-shas` prints the two computed shas (use it to fill the manifest prereg — same code path
as the guard, so no awk/Python byte mismatch).

RED-first: run before creating the manifest/fixtures/template to confirm it fails.
Run: python3 scripts/_exec_replay_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

from _canon import load_canon

SKILL_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = SKILL_ROOT / "evals"
FIXTURES_DIR = EVALS_DIR / "exec-fixtures"
MANIFEST_PATH = EVALS_DIR / "exec_replay_baseline.json"
TEMPLATE_PATH = EVALS_DIR / "exec_step3_executor_prompt.md"
SKILL_MD = SKILL_ROOT / "SKILL.md"

VALID_KINDS = {"apply", "revert", "risk_boundary"}
VALID_STATUS = {"baseline_unmeasured", "measured"}
VALID_FINDING_STATUS = {"resolved", "carried_forward"}
BASE_EXPECTED_KEYS = (
    "id",
    "kind",
    "primary_file",
    "smell",
    "targeted_dimension",
    "min_severity",
    "expected_targeted_finding_status",
    "lens",
    "change_paths",
    "avoid_paths",
)
SEED_MEMBERS = ("CURRENT_REVIEW.json", "CURRENT_REVIEW.md", "findings_registry.json")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _skill_step3_section() -> str | None:
    """The SKILL.md section from the '### Step 3' heading up to the next '### '/'## ' heading.

    Regex-anchored (not a line range) so it invalidates only when Step-3 content changes, not
    when text shifts above it.
    """
    if not SKILL_MD.exists():
        return None
    lines = SKILL_MD.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if re.match(r"^### Step 3\b", ln)), None)
    if start is None:
        return None
    end = next(
        (j for j in range(start + 1, len(lines)) if re.match(r"^(### |## )", lines[j])),
        len(lines),
    )
    return "".join(lines[start:end])


def _computed_shas() -> tuple[str | None, str | None]:
    tmpl = (
        _sha256_text(TEMPLATE_PATH.read_text(encoding="utf-8")) if TEMPLATE_PATH.exists() else None
    )
    section = _skill_step3_section()
    return tmpl, (_sha256_text(section) if section is not None else None)


def _collect_fixture_dirs() -> list[str]:
    if not FIXTURES_DIR.exists():
        return []
    return sorted(p.name for p in FIXTURES_DIR.iterdir() if p.is_dir())


def _check_expected(fid: str, exp: dict, canon, failures: list[str]) -> str | None:
    for key in BASE_EXPECTED_KEYS:
        if key not in exp:
            failures.append(f"fixture '{fid}': expected.toml missing key '{key}'")
    if exp.get("id") != fid:
        failures.append(f"fixture '{fid}': expected.toml id '{exp.get('id')}' != dir name")
    kind = exp.get("kind")
    if kind not in VALID_KINDS:
        failures.append(f"fixture '{fid}': kind '{kind}' not in {sorted(VALID_KINDS)}")
    if exp.get("targeted_dimension") not in set(canon.scorecard_dimensions):
        failures.append(
            f"fixture '{fid}': targeted_dimension '{exp.get('targeted_dimension')}' not a canon dim"
        )
    if exp.get("min_severity") not in set(canon.severity_anchors):
        failures.append(
            f"fixture '{fid}': min_severity '{exp.get('min_severity')}' not a canon severity anchor"
        )
    if exp.get("expected_targeted_finding_status") not in VALID_FINDING_STATUS:
        failures.append(
            f"fixture '{fid}': expected_targeted_finding_status "
            f"'{exp.get('expected_targeted_finding_status')}' not in {sorted(VALID_FINDING_STATUS)}"
        )
    for key in ("change_paths", "avoid_paths"):
        if not isinstance(exp.get(key), list):
            failures.append(f"fixture '{fid}': expected.toml '{key}' must be a list")
    # conditional required keys
    if kind == "apply" and not exp.get("resolved_absent_regex"):
        failures.append(
            f"fixture '{fid}': kind=apply requires 'resolved_absent_regex' (deterministic pattern-gone check)"
        )
    if kind == "revert" and not exp.get("test_command"):
        failures.append(f"fixture '{fid}': kind=revert requires a non-empty 'test_command'")
    if kind == "risk_boundary":
        for key in ("risk_boundary_kind", "required_evidence_kind"):
            if not exp.get(key):
                failures.append(f"fixture '{fid}': kind=risk_boundary requires '{key}'")
    return kind


def _check_seed(fid: str, seed_dir: Path, canon, failures: list[str]) -> None:
    cr = seed_dir / "CURRENT_REVIEW.json"
    if not cr.exists():
        return  # member check already flagged it
    try:
        art = json.loads(cr.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"fixture '{fid}': seed/CURRENT_REVIEW.json does not parse: {exc}")
        return
    if art.get("state") != "CONTINUE":
        failures.append(
            f"fixture '{fid}': seed state '{art.get('state')}' must be 'CONTINUE' (pre-Step-3)"
        )
    findings = art.get("findings") or []
    if not findings:
        failures.append(f"fixture '{fid}': seed has no findings[]")
    else:
        f0 = findings[0]
        if not f0.get("minimal_correction_path"):
            failures.append(
                f"fixture '{fid}': seed findings[0] missing minimal_correction_path (the plan Step-3 applies)"
            )
        br = f0.get("blast_radius") or {}
        if not isinstance(br.get("change"), list) or not isinstance(br.get("avoid"), list):
            failures.append(
                f"fixture '{fid}': seed findings[0].blast_radius must have list change[] + avoid[]"
            )
        backlog = art.get("backlog") or []
        if not backlog or backlog[0].get("title") != f0.get("title"):
            failures.append(
                f"fixture '{fid}': seed backlog[0].title must match findings[0].title (Step-3 selection)"
            )
    scorecard = art.get("scorecard") or {}
    missing = [d for d in canon.scorecard_dimensions if d not in scorecard]
    if missing:
        failures.append(f"fixture '{fid}': seed scorecard missing canon dims: {missing}")


def main(argv: list[str]) -> int:
    canon = load_canon(SKILL_ROOT)

    if "--print-shas" in argv:
        tmpl, section = _computed_shas()
        print(f"step3_executor_prompt_sha256 = {tmpl}")
        print(f"skill_step3_section_sha256   = {section}")
        return 0

    failures: list[str] = []

    if not MANIFEST_PATH.exists():
        print(f"FAIL: manifest not found: {MANIFEST_PATH.relative_to(SKILL_ROOT)}")
        return 1
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: manifest is not valid JSON: {exc}")
        return 1

    fixture_dirs = _collect_fixture_dirs()
    entries = manifest.get("fixtures", [])
    registered = {e["id"] for e in entries if isinstance(e, dict) and "id" in e}

    # (a) no silent exclusion
    for d in fixture_dirs:
        if d not in registered:
            failures.append(
                f"fixture dir '{d}' exists on disk but is NOT registered in the manifest"
            )
    if not fixture_dirs:
        failures.append("no fixture dirs under evals/exec-fixtures/ (need >= 1)")
    if not entries:
        failures.append("manifest registers no fixtures (need >= 1)")

    # (e) dual-sha drift guard
    prereg = manifest.get("prereg") or {}
    tmpl_sha, section_sha = _computed_shas()
    if not TEMPLATE_PATH.exists():
        failures.append(f"executor template not found: {TEMPLATE_PATH.relative_to(SKILL_ROOT)}")
    elif prereg.get("step3_executor_prompt_sha256") != tmpl_sha:
        failures.append(
            "step3_executor_prompt_sha256 drift: template changed vs manifest prereg "
            "(re-run --print-shas and re-measure the baseline)"
        )
    if section_sha is None:
        failures.append("could not extract the SKILL.md '### Step 3' section for the drift pin")
    elif prereg.get("skill_step3_section_sha256") != section_sha:
        failures.append(
            "skill_step3_section_sha256 drift: SKILL.md Step-3 section changed vs manifest prereg "
            "(re-run --print-shas and re-measure the baseline)"
        )

    # per-fixture members + expected + seed
    exp_by_id: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry:
            failures.append(f"manifest fixture entry malformed (no id): {entry!r}")
            continue
        fid = entry["id"]
        fdir = FIXTURES_DIR / fid
        if not fdir.is_dir():
            failures.append(f"fixture '{fid}': dir does not exist")
            continue
        # (b) members
        if not (fdir / "codebase").is_dir():
            failures.append(f"fixture '{fid}': missing codebase/ dir")
        seed_dir = fdir / "seed"
        if not seed_dir.is_dir():
            failures.append(f"fixture '{fid}': missing seed/ dir")
        else:
            for m in SEED_MEMBERS:
                if not (seed_dir / m).exists():
                    failures.append(f"fixture '{fid}': missing seed/{m}")
        exp_path = fdir / "expected.toml"
        if not exp_path.exists():
            failures.append(f"fixture '{fid}': missing expected.toml")
            continue
        # (c) expected.toml
        try:
            exp = tomllib.loads(exp_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            failures.append(f"fixture '{fid}': expected.toml does not parse: {exc}")
            continue
        exp_by_id[fid] = exp
        _check_expected(fid, exp, canon, failures)
        # (d) seed validity (targeted)
        if seed_dir.is_dir():
            _check_seed(fid, seed_dir, canon, failures)

    # (f) measured-mode consistency
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        fid = entry.get("id", "<missing id>")
        status = entry.get("status")
        if status not in VALID_STATUS:
            failures.append(f"fixture '{fid}': status '{status}' not in {sorted(VALID_STATUS)}")
        if status != "measured":
            continue
        if not entry.get("baseline_observed"):
            failures.append(f"fixture '{fid}': status=measured but baseline_observed is empty")
        arms = entry.get("arms")
        if not isinstance(arms, dict) or "arm_a" not in arms:
            failures.append(f"measured fixture '{fid}': arms.arm_a required (the baseline arm)")
            continue
        kind = (exp_by_id.get(fid) or {}).get("kind")
        # safety_tolerance 0: once arm_b (the candidate cheaper executor) is measured, it must never
        # leave a broken/unevidenced change committed on a revert/risk_boundary fixture. arm_b is the
        # deferred follow-up; the gate is dormant until it is recorded.
        arm_b = arms.get("arm_b")
        if arm_b and kind in {"revert", "risk_boundary"} and arm_b.get("safety_violation"):
            failures.append(
                f"measured fixture '{fid}' (kind={kind}): arm_b.safety_violation is truthy "
                "— violates safety_tolerance=0 (cheaper executor left a bad change committed)"
            )

    if failures:
        print(f"_exec_replay_selftest: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"_exec_replay_selftest: OK ({len(entries)} fixture(s) registered, all well-formed)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
