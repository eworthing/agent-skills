#!/usr/bin/env python3
"""Grade a completed loop-replay run against its fixture's expected.toml (Layer 4).

Given the artifact directory a host-dispatched loop emitted into (CURRENT_REVIEW.json +
REVIEW_HISTORY + registry), this checks the structural and semantic invariants registered
in evals/loop_replay_baseline.json. This is the committed grader — it is what makes the
harness measure Critic *behavior* (did the loop catch and fix the planted debt), not just
artifact mechanics. It runs no model.

Usage:
  loop_replay_grade.py <fixture-id> <artifact-dir>
  loop_replay_grade.py <fixture-id> <artifact-dir-or-findings-file> --detection-only
  loop_replay_grade.py <fixture-id> <artifact-dir-or-findings-file> --priority-only

  <artifact-dir>    directory holding the emitted CURRENT_REVIEW.json (the materialized
                    repo root, unless the loop writes artifacts elsewhere).
  --detection-only  Tier-1/2 probe grading (evals/loop-fixtures/DETECTION-PROBE.md):
                    detection verdict only, from a bare findings JSON file or a
                    CURRENT_REVIEW.json / artifact dir.
  --priority-only   Tier-1P probe grading (evals/priority-fixtures/): RANK verdict,
                    reading `backlog[]` rather than `findings[]`. Detection asks "was
                    it found?"; this asks "of several valid candidates, which was
                    ranked first?" Fixtures resolve from evals/priority-fixtures/.
  --strict-exit     accepted for back-compat; strict is the only exit mode.

Exit codes: full mode — 0 = all required invariants hold, 1 = a required invariant
failed or inputs missing. --detection-only — 0 = DETECTED, 3 = NOT DETECTED,
1 = input error. --priority-only — 0 = correctly prioritized, 3 = misprioritized,
1 = input error. Advisory checks never affect exit status; they print as INFO.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = SKILL_ROOT / "evals" / "loop-fixtures"
PRIORITY_FIXTURES_DIR = SKILL_ROOT / "evals" / "priority-fixtures"
CANON_DIR = SKILL_ROOT / "canon"
VALIDATE_ARTIFACT = SKILL_ROOT / "scripts" / "validate-artifact.py"

# G39's shape: `<canon_dim_id> <signed delta>`, ';'-joined. Attribution by dimension
# is what makes rank gradable without parsing English.
_SCORE_IMPACT_ENTRY = re.compile(r"^([a-z_]+)\s+[+-]\d+(?:\.\d+)?$")


def _severity_rank() -> dict[str, int]:
    data = tomllib.loads((CANON_DIR / "severity-anchors.toml").read_text())
    return {label: i for i, label in enumerate(data["severity_anchors"])}


def _load_expected(fixture_id: str, base: Path | None = None) -> dict:
    p = (base or FIXTURES_DIR) / fixture_id / "expected.toml"
    if not p.exists():
        sys.exit(f"FAIL: fixture '{fixture_id}' has no expected.toml ({p})")
    return tomllib.loads(p.read_text())


def _load_artifact(artifact_dir: Path) -> dict:
    p = artifact_dir / "CURRENT_REVIEW.json"
    if not p.exists():
        sys.exit(f"FAIL: no CURRENT_REVIEW.json in {artifact_dir}")
    return json.loads(p.read_text())


def _cites(finding: dict, primary: str) -> bool:
    """One citation rule for BOTH grading modes — a drift here would let Tier-1
    probe grading and full Layer-4 grading disagree on what counts as a hit."""
    return any(primary in str(e) for e in (finding.get("evidence") or []))


def _finding_label(finding: dict) -> str:
    """v2+ artifacts may omit the legacy `id` alias; fall back to the required IDs."""
    return str(finding.get("id") or finding.get("loop_local_id") or finding.get("stable_id") or "?")


def _load_probe_payload(findings_path: Path) -> dict:
    """Load untrusted probe output: tolerate a markdown code fence and a bare
    top-level array; fail loudly (clean FAIL, exit 1) on anything else.

    Returns the whole object so callers can read `findings` (detection) or
    `backlog` (prioritization) without two copies of the tolerant parsing —
    same single-source rationale as `_cites`.
    """
    if not findings_path.exists():
        sys.exit(f"FAIL: no findings file at {findings_path}")
    try:
        text = findings_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        sys.exit(f"FAIL: could not read findings file {findings_path}: {exc}")
    stripped = text.strip()
    if stripped.startswith("```"):
        first_nl = stripped.find("\n")
        stripped = stripped[first_nl + 1 :] if first_nl != -1 else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        sys.exit(f"FAIL: findings file is not valid JSON: {exc}")
    if isinstance(data, list):
        data = {"findings": data}
    if not isinstance(data, dict):
        sys.exit(f"FAIL: findings JSON must be an object or array, got {type(data).__name__}")
    return data


def _load_probe_findings(findings_path: Path) -> list[dict]:
    return [
        f for f in _load_probe_payload(findings_path).get("findings", []) if isinstance(f, dict)
    ]


def _detection_only(fixture_id: str, findings_path: Path) -> int:
    """Tier-1/Tier-2 detection probe grading (evals/loop-fixtures/DETECTION-PROBE.md).

    Reads a bare findings file ({"findings": [...]} or a CURRENT_REVIEW.json) and
    reports ONLY the detection verdict: does a >= min_severity finding cite the
    planted primary_file? Empty findings are a valid miss, not an error. Every
    finding is printed so the operator reads restraint manually (near-miss control
    judgments stay human, per the microtest doctrine). Exit 0 = DETECTED,
    3 = NOT DETECTED, 1 = input error.
    """
    expected = _load_expected(fixture_id)
    findings = _load_probe_findings(findings_path)
    sev_rank = _severity_rank()
    primary = expected["primary_file"]
    floor = expected["min_severity"]
    if floor not in sev_rank:
        sys.exit(f"FAIL: fixture min_severity {floor!r} is not a canon severity anchor")

    hit_flags = [
        _cites(f, primary) and sev_rank.get(f.get("severity"), -1) >= sev_rank[floor]
        for f in findings
    ]
    print(
        f"loop_replay_grade --detection-only: fixture '{fixture_id}' ({len(findings)} finding(s))"
    )
    for f, hit in zip(findings, hit_flags, strict=True):
        ev = str((f.get("evidence") or ["-"])[0])[:80]
        print(
            f"  [{'HIT ' if hit else '    '}] {_finding_label(f)} | {f.get('severity')} | "
            f"{str(f.get('title', ''))[:70]} | ev: {ev}"
        )
    if any(hit_flags):
        print(f"DETECTED (planted primary_file cited at >= {floor!r})")
        return 0
    print(f"NOT DETECTED (no >= {floor!r} finding cites {primary!r})")
    return 3


def _item_dimensions(item: dict) -> set[str]:
    """Dimensions a backlog item claims to move, from its G39-shaped score_impact.

    Returns an empty set for prose. That is not treated as an error here — the
    grader reports it as unattributable and the operator sees it — because G39
    already fails prose at emit; a second, softer copy of that rule would just
    disagree with the first one eventually.
    """
    raw = item.get("score_impact")
    if not isinstance(raw, str):
        return set()
    dims: set[str] = set()
    for part in raw.split(";"):
        m = _SCORE_IMPACT_ENTRY.match(part.strip())
        if m:
            dims.add(m.group(1))
    return dims


def _priority_only(fixture_id: str, path: Path) -> int:
    """Tier-1P prioritization probe grading.

    `--detection-only` answers "was the planted defect found?" — set membership.
    This answers "given several simultaneously valid candidates, which one did the
    Critic rank first?" A competent Critic finds all of them; the measurement is
    what it does with them.

    Verdict (all three required): the Priority-1 item moves the target dimension,
    the decoy is absent or ranked below 1, and the restraint control is ranked
    nowhere. The blocked item is printed, never gated — whether its blocker was
    named honestly is prose, and prose stays an operator read for the same reason
    restraint does. Exit 0 = correctly prioritized, 3 = misprioritized, 1 = input
    error.
    """
    expected = _load_expected(fixture_id, PRIORITY_FIXTURES_DIR)
    payload = _load_probe_payload(path)
    backlog = [b for b in payload.get("backlog", []) if isinstance(b, dict)]

    target = expected["expected_priority_1_dimension"]
    decoy = expected["decoy_dimension"]
    restraint = expected["restraint_dimension"]
    blocked = expected.get("blocked_dimension")

    print(
        f"loop_replay_grade --priority-only: fixture '{fixture_id}' ({len(backlog)} backlog item(s))"
    )
    if not backlog:
        print("MISPRIORITIZED (empty backlog — nothing to rank)")
        return 3

    def _is_restraint(item: dict) -> bool:
        """The restraint control is a PURE framework_idioms change — consolidating the
        two decoding idioms moves nothing else. An item that claims the dimension
        alongside another is doing different work and happens to help here too, which
        is a real and common shape: the production finding this fixture is modelled on
        carried `"concurrency +0.5; framework_idioms +0.5"` for fifteen loops. Failing
        that would fail a faithful arm for being accurate about its own side effects.
        """
        return _item_dimensions(item) == {restraint}

    ranked = sorted(backlog, key=lambda b: b.get("priority", 10**6))
    for item in ranked:
        dims = _item_dimensions(item)
        tags = []
        if target in dims:
            tags.append("TARGET")
        if decoy in dims:
            tags.append("decoy")
        if _is_restraint(item):
            tags.append("RESTRAINT")
        elif restraint in dims:
            tags.append("restraint-secondary")
        if blocked and blocked in dims:
            tags.append("blocked")
        label = ",".join(tags) if tags else ("unattributed" if not dims else "-")
        print(
            f"  P{item.get('priority')} [{label}] {sorted(dims) or '?'} | "
            f"{str(item.get('title', ''))[:64]}"
        )

    p1_dims = _item_dimensions(ranked[0])
    decoy_at_1 = decoy in p1_dims
    restraint_ranked = [b for b in backlog if _is_restraint(b)]
    target_at_1 = target in p1_dims

    failures = []
    if not target_at_1:
        failures.append(f"Priority 1 does not move the target dimension {target!r}")
    if decoy_at_1:
        failures.append(f"Priority 1 is the decoy dimension {decoy!r}")
    if restraint_ranked:
        at = [b.get("priority") for b in restraint_ranked]
        failures.append(
            f"restraint control {restraint!r} ranked at priority {at} "
            "(SPT-rejected candidate — a stall signal is not a licence to manufacture work)"
        )
    secondary = [
        b.get("priority")
        for b in backlog
        if restraint in _item_dimensions(b) and not _is_restraint(b)
    ]
    if secondary:
        print(
            f"  [INFO] {restraint!r} claimed as a secondary effect at priority {secondary} — "
            "not a restraint failure; confirm the item is not the decoding consolidation "
            "wearing a second dimension"
        )

    if blocked:
        where = [b.get("priority") for b in backlog if blocked in _item_dimensions(b)]
        print(
            f"  [INFO] blocked dimension {blocked!r} at priority {where or 'absent'} — "
            "read the Priority-1 accounting: naming the blocker is correct, "
            "halting on it and silently omitting it are both wrong"
        )

    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        print("MISPRIORITIZED")
        return 3
    print("CORRECTLY PRIORITIZED (target first, decoy not first, restraint unranked)")
    return 0


KNOWN_FLAGS = {"--strict-exit", "--detection-only", "--priority-only"}


def main(argv: list[str]) -> int:
    unknown = {a for a in argv if a.startswith("--")} - KNOWN_FLAGS
    if unknown:
        sys.exit(
            f"FAIL: unrecognized flag(s): {', '.join(sorted(unknown))}"
            f" (known: {', '.join(sorted(KNOWN_FLAGS))})"
        )
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(
            "usage: loop_replay_grade.py <fixture-id> <artifact-dir-or-findings-file>"
            " [--detection-only]"
        )
    if "--detection-only" in argv and "--priority-only" in argv:
        sys.exit("FAIL: --detection-only and --priority-only are mutually exclusive")
    if "--detection-only" in argv:
        p = Path(args[1]).resolve()
        return _detection_only(args[0], p / "CURRENT_REVIEW.json" if p.is_dir() else p)
    if "--priority-only" in argv:
        p = Path(args[1]).resolve()
        return _priority_only(args[0], p / "CURRENT_REVIEW.json" if p.is_dir() else p)
    fixture_id, artifact_dir = args[0], Path(args[1]).resolve()

    expected = _load_expected(fixture_id)
    artifact = _load_artifact(artifact_dir)
    sev_rank = _severity_rank()

    required: list[tuple[str, bool, str]] = []  # (label, passed, detail)
    advisory: list[tuple[str, str]] = []

    # ---- STRUCTURAL ----
    proc = subprocess.run(
        [sys.executable, str(VALIDATE_ARTIFACT), str(artifact_dir), "--mode", "strict"],
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

    findings_list = [f for f in artifact.get("findings", []) if isinstance(f, dict)]
    required.append(
        (
            "structural: findings[] is non-empty",
            bool(findings_list),
            f"count={len(findings_list)}",
        )
    )

    loop_result = artifact.get("loop_result") or {}
    tfs = loop_result.get("targeted_finding_status")
    required.append(
        (
            "structural: loop_result.targeted_finding_status valid enum",
            tfs in {"resolved", "carried_forward"},
            f"status={tfs!r}",
        )
    )

    # ---- SEMANTIC ----
    # Identify the planted finding. priority_1_finding_id / loop_result.targeted_finding_id are
    # both null once the priority-1 finding is RESOLVED this loop (a real schema fact this harness
    # surfaced), so we don't depend on them: prefer an explicit targeted id if present, else fall
    # back to the highest-severity finding whose evidence cites the planted primary_file.
    primary = expected["primary_file"]

    targeted_id = loop_result.get("targeted_finding_id") or artifact.get("priority_1_finding_id")
    by_id = {f.get("id"): f for f in findings_list}
    planted = by_id.get(targeted_id) if targeted_id else None
    if planted is None or not _cites(planted, primary):
        citing = sorted(
            (f for f in findings_list if _cites(f, primary)),
            key=lambda f: sev_rank.get(f.get("severity"), -1),
            reverse=True,
        )
        planted = citing[0] if citing else None

    # False-GREEN guard: the fallback cannot tell the planted defect from a
    # competing finding in the same file (both 2026-07-13 false-GREENs looked
    # all-PASS). Surface the ambiguity on the advisory channel so an operator
    # reads the findings before recording the arm; exit status is unaffected.
    floor_rank = sev_rank.get(expected["min_severity"], len(sev_rank))
    contenders = [
        f
        for f in findings_list
        if _cites(f, primary) and sev_rank.get(f.get("severity"), -1) >= floor_rank
    ]
    if len(contenders) > 1:
        advisory.append(
            (
                f"advisory: {len(contenders)} findings at/above min_severity cite "
                f"primary_file ({', '.join(_finding_label(f) for f in contenders)}) — "
                f"fallback cannot distinguish planted vs competing; read them before "
                f"recording this arm",
                "",
            )
        )

    required.append(
        (
            "semantic: a finding cites the planted primary_file (debt was found)",
            planted is not None,
            f"primary_file={primary!r}",
        )
    )
    if planted is not None:
        sev = planted.get("severity")
        floor = expected["min_severity"]
        required.append(
            (
                "semantic: that finding's severity >= min_severity",
                sev in sev_rank and sev_rank[sev] >= sev_rank[floor],
                f"severity={sev!r} floor={floor!r} id={planted.get('id')!r}",
            )
        )

    what_changed = str(loop_result.get("what_changed") or "")
    required.append(
        (
            "semantic: loop_result.what_changed references primary_file (fix touched planted file)",
            primary in what_changed,
            f"primary_file={primary!r} present={primary in what_changed}",
        )
    )

    exp_status = expected["expected_targeted_finding_status"]
    required.append(
        (
            "semantic: loop_result.targeted_finding_status == expected (planted debt fixed)",
            tfs == exp_status,
            f"got={tfs!r} expected={exp_status!r}",
        )
    )

    # ---- ADVISORY (never affects exit) ----
    dim = expected["targeted_dimension"]
    scorecard = artifact.get("scorecard") or {}
    dim_entry = scorecard.get(dim)
    score = dim_entry.get("score") if isinstance(dim_entry, dict) else dim_entry
    advisory.append(
        (
            f"advisory: scorecard[{dim}] present (movement vs baseline once measured)",
            f"score={score!r}",
        )
    )

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
