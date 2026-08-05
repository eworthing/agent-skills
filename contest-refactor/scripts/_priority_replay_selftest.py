#!/usr/bin/env python3
"""Self-test for the Tier-1P prioritization harness (evals/priority-fixtures/).

Mechanical guard, no model. Pins the manifest/fixture contract and the grader's
discrimination, because a probe that silently stops discriminating reports a clean
GREEN and nobody notices:

  1. NO SILENT EXCLUSION — every evals/priority-fixtures/<id>/ dir is registered in
     evals/priority_replay_baseline.json, and every registered id exists on disk.
  2. REQUIRED MEMBERS   — codebase/, seed/REVIEW_HISTORY.json, expected.toml.
  3. SPEC VALIDITY      — the four role dimensions are DISTINCT canon scorecard ids.
     A fixture whose candidates share a dimension cannot discriminate at all, and
     the grader keys on dimension.
  4. STALL SIGNATURE    — the recorded stall_signature matches what the seeded
     REVIEW_HISTORY.json actually implies. A drifting seed would quietly change
     which dimension is "most overdue" and invert the expected answer.
  5. GRADER BEHAVIOUR   — RED-shaped input misprioritizes (exit 3), GREEN-shaped
     passes (exit 0), a pure restraint claim fails, and a restraint claimed as a
     SECONDARY effect does not (the production finding this models carried
     `concurrency +0.5; framework_idioms +0.5` for fifteen loops).
  6. MEASURED-MODE      — status=measured requires both arms recorded.

No pytest in this repo -> standalone _*.py helper.

Run: python3 scripts/_priority_replay_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _canon import load_canon

FIXTURES = SKILL_ROOT / "evals" / "priority-fixtures"
MANIFEST = SKILL_ROOT / "evals" / "priority_replay_baseline.json"
REPLICATION = SKILL_ROOT / "evals" / "priority_replay_replication.json"
GRADER = HERE / "loop_replay_grade.py"

FIXTURE_KINDS = {"rank", "residual_disposition"}

ROLE_KEYS = (
    "expected_priority_1_dimension",
    "decoy_dimension",
    "restraint_dimension",
    "blocked_dimension",
)

RESIDUAL_KEYS = (
    "off_path_dimension",
    "off_path_file",
    "legitimate_dimension",
)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


def _grade(payload: dict) -> int:
    """Exercise the grader as a subprocess, not an import: the exit code IS the
    contract the probe operator reads, so testing the function return value would
    pass while a broken main() routing shipped."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
        json.dump(payload, tf)
        path = Path(tf.name)
    try:
        proc = subprocess.run(
            [sys.executable, str(GRADER), "stalled-domain-1", str(path), "--priority-only"],
            capture_output=True,
            text=True,
        )
        return proc.returncode
    finally:
        path.unlink(missing_ok=True)


def _implied_stalls(history: dict) -> dict[str, int]:
    """loops_since_up per dimension entering the next loop, from the seeded history."""
    loops = sorted(history.get("loops", []), key=lambda e: e.get("loop", 0))
    stall: dict[str, int] = {}
    for entry in loops:
        for dim, cell in (entry.get("scorecard") or {}).items():
            stall[dim] = 0 if cell.get("delta") == "UP" else stall.get(dim, 0) + 1
    return stall


def main() -> int:
    canon = load_canon(SKILL_ROOT)
    known_dims = set(canon.scorecard_dimensions)

    check(MANIFEST.is_file(), f"missing manifest {MANIFEST}")
    if not MANIFEST.is_file():
        print("FAIL: " + failures[0])
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registered = {f["id"]: f for f in manifest.get("fixtures", [])}

    on_disk = {p.name for p in FIXTURES.iterdir() if p.is_dir()} if FIXTURES.is_dir() else set()

    # 1) no silent exclusion, both directions
    for name in sorted(on_disk - set(registered)):
        failures.append(
            f"fixture {name!r} on disk but not registered in priority_replay_baseline.json"
        )
    for name in sorted(set(registered) - on_disk):
        failures.append(f"fixture {name!r} registered but absent from {FIXTURES}")

    for name in sorted(on_disk & set(registered)):
        d = FIXTURES / name
        entry = registered[name]

        # 2) required members
        check((d / "codebase").is_dir(), f"{name}: missing codebase/")
        check(
            (d / "seed" / "REVIEW_HISTORY.json").is_file(),
            f"{name}: missing seed/REVIEW_HISTORY.json",
        )
        spec_path = d / "expected.toml"
        check(spec_path.is_file(), f"{name}: missing expected.toml")
        if not spec_path.is_file():
            continue
        spec = tomllib.loads(spec_path.read_text(encoding="utf-8"))

        check(
            spec.get("id") == name, f"{name}: expected.toml id {spec.get('id')!r} != directory name"
        )

        # 3) spec validity, per kind. `rank` fixtures ask which of several candidates
        # goes first; `residual_disposition` fixtures ask where a single off-path gap
        # lands. They need different keys, so validating one shape against the other
        # would reject a legitimate fixture.
        kind = spec.get("kind", "rank")
        check(
            kind in FIXTURE_KINDS,
            f"{name}: kind={kind!r} not in {sorted(FIXTURE_KINDS)}",
        )
        required = ROLE_KEYS if kind == "rank" else RESIDUAL_KEYS
        roles = {}
        for key in required:
            val = spec.get(key)
            check(bool(val), f"{name}: kind={kind} expected.toml missing {key}")
            if val and key.endswith("dimension"):
                check(val in known_dims, f"{name}: {key}={val!r} is not a canon scorecard id")
                roles[key] = val
        dim_keys = [k for k in required if k.endswith("dimension")]
        if len(roles) == len(dim_keys):
            check(
                len(set(roles.values())) == len(dim_keys),
                f"{name}: role dimensions must be distinct, got {roles} — "
                "a fixture whose candidates share a dimension cannot discriminate",
            )

        # 4) stall signature matches the seeded history
        hist_path = d / "seed" / "REVIEW_HISTORY.json"
        if hist_path.is_file():
            implied = _implied_stalls(json.loads(hist_path.read_text(encoding="utf-8")))
            for dim, want in (spec.get("stall_signature") or {}).items():
                got = implied.get(dim)
                check(
                    got == want,
                    f"{name}: stall_signature[{dim}]={want} but seed/REVIEW_HISTORY.json implies {got} "
                    "— the seed drifted and the expected answer may have inverted",
                )
            for dim in spec.get("stalled_dimensions", []):
                check(
                    implied.get(dim, 0) >= 3,
                    f"{name}: {dim!r} listed in stalled_dimensions but seed implies "
                    f"loops_since_up={implied.get(dim)}",
                )

        # 4b) blind dispatch — codebase/ is copied into the probe, so it must not
        # name the roles or state the verdict. An earlier draft of this fixture
        # carried `/// TARGET (domain_modeling)` and `RESTRAINT CONTROL ... fails
        # SPT at Q1/Q2` as Swift doc comments, handing the probe both the answer
        # and the reasoning. Role docs belong in expected.toml, which is not copied.
        tells = (
            "TARGET",
            "DECOY",
            "RESTRAINT CONTROL",
            "BLOCKED (",
            "planted",
            "fixture",
            "restraint failure",
            "Simplify Pressure Test",
            "SPT",
        )
        for src in sorted((d / "codebase").rglob("*")):
            if not src.is_file():
                continue
            body = src.read_text(encoding="utf-8", errors="replace")
            for tell in tells:
                check(
                    tell not in body,
                    f"{name}: {src.relative_to(d)} contains {tell!r} — codebase/ is "
                    "copied into the probe and must not telegraph the answer",
                )

        # 4c) the seeded scorecard must be re-derivable from codebase/. A Critic
        # following Method Step 1's anchor-to-source rule ignores the prior
        # scorecard and re-derives from source; if the two disagree, the fixture
        # measures that discipline instead of prioritization. This cost one whole
        # 5-rep RED arm: the fixture shipped no tests, three reps correctly scored
        # test_strategy at its 3-anchor, and the decoy became the honest answer.
        hist_path2 = d / "seed" / "REVIEW_HISTORY.json"
        if hist_path2.is_file() and (d / "codebase").is_dir():
            hist = json.loads(hist_path2.read_text(encoding="utf-8"))
            loops = sorted(hist.get("loops", []), key=lambda e: e.get("loop", 0))
            if loops:
                final = (loops[-1].get("scorecard") or {}).get("test_strategy") or {}
                seeded = final.get("score")
                # Match on path components RELATIVE to codebase/, not the absolute
                # path: the skill lives under `contest-refactor`, and "contest"
                # contains "test", so an absolute-substring check silently reports
                # tests everywhere and never fires.
                has_tests = any(
                    any("test" in part.lower() for part in p.relative_to(d / "codebase").parts)
                    for p in (d / "codebase").rglob("*")
                    if p.is_file()
                )
                check(
                    not (isinstance(seeded, (int, float)) and seeded >= 9 and not has_tests),
                    f"{name}: seed scores test_strategy at {seeded} but codebase/ ships no "
                    "tests — a Critic re-deriving from source will score it far lower and "
                    "the fixture will measure anchor-to-source instead of rank",
                )

        # 6) measured mode
        status = entry.get("status")
        check(
            status in {"baseline_unmeasured", "measured"},
            f"{name}: status {status!r} not in {{baseline_unmeasured, measured}}",
        )
        if status == "measured":
            obs = entry.get("baseline_observed")
            check(isinstance(obs, dict), f"{name}: status=measured requires baseline_observed")
            if isinstance(obs, dict):
                for arm in ("red", "green"):
                    # Presence is not enough — a null arm is an unrun arm. Keying on
                    # `arm in obs` would let a half-measured fixture claim `measured`,
                    # which is the shape a partial result actually arrives in.
                    check(
                        isinstance(obs.get(arm), dict),
                        f"{name}: status=measured but the {arm!r} arm is null/absent — "
                        "a half-measured fixture stays baseline_unmeasured",
                    )

    # 7) the replication file must agree with the summary it backs. A recorded arm
    # whose raw reps say something else is worse than no raw reps at all, and these
    # arms are NEGATIVE results — the only way to disagree with the reading is to
    # re-grade the reps, so the counts have to be checkable.
    if REPLICATION.is_file():
        rep = json.loads(REPLICATION.read_text(encoding="utf-8"))
        attempts = rep.get("attempts", [])
        for name, entry in registered.items():
            obs = (entry.get("baseline_observed") or {}).get("red")
            if not isinstance(obs, dict) or "reps" not in obs:
                continue
            got = sum(1 for a in attempts if a.get("fixture_id") == name and a.get("arm") == "red")
            check(
                got == obs["reps"],
                f"{name}: baseline_observed.red records {obs['reps']} reps but "
                f"priority_replay_replication.json holds {got} for arm 'red'",
            )
    else:
        for name, entry in registered.items():
            if isinstance((entry.get("baseline_observed") or {}).get("red"), dict):
                failures.append(
                    f"{name}: an arm is recorded but priority_replay_replication.json is "
                    "missing — a measured arm keeps its raw reps"
                )

    # 5) grader discrimination (only meaningful once the reference fixture exists)
    if "stalled-domain-1" in on_disk:
        target = {"priority": 1, "title": "t", "score_impact": "domain_modeling +1.0"}
        decoy = {"priority": 1, "title": "d", "score_impact": "test_strategy +0.5"}
        blocked = {"priority": 2, "title": "b", "score_impact": "concurrency +0.5"}
        blocked_pair = {
            "priority": 2,
            "title": "b2",
            "score_impact": "concurrency +0.5; framework_idioms +0.5",
        }
        restraint = {"priority": 2, "title": "r", "score_impact": "framework_idioms +0.5"}

        cases = [
            ("RED: decoy first", {"backlog": [decoy, dict(target, priority=2)]}, 3),
            ("GREEN: target first", {"backlog": [target, blocked]}, 0),
            ("GREEN: restraint as a secondary effect", {"backlog": [target, blocked_pair]}, 0),
            ("restraint ranked (pure claim)", {"backlog": [target, restraint]}, 3),
            ("empty backlog", {"backlog": []}, 3),
            ("unattributed prose", {"backlog": [{"priority": 1, "score_impact": "big win"}]}, 3),
        ]
        for label, payload, want in cases:
            got = _grade(payload)
            check(got == want, f"grader {label}: expected exit {want}, got {got}")

        # the mutually-exclusive flag guard
        proc = subprocess.run(
            [sys.executable, str(GRADER), "x", "y", "--priority-only", "--detection-only"],
            capture_output=True,
            text=True,
        )
        check(proc.returncode != 0, "grader: --priority-only + --detection-only must be rejected")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: priority-replay selftest — {len(on_disk)} fixture(s), "
        "manifest/spec/stall-signature consistent, grader discriminates"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
