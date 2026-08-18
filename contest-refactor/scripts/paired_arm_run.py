#!/usr/bin/env python3
"""Dispatch-loop runner for the paired-arm measurement (plan Phases 2-3).

The plan's execution model in one sentence: **a pair is resolved iff a committed terminal attempt
record says so** -- not by the presence of output files, not by a sidecar, not by in-memory state.
Git supplies atomicity, content hashing, append-only history, and crash safety; this script does
the reconcile/guard/commit bookkeeping around it and nothing else.

Two commits per pair. A `started` record lands in execution.json BEFORE dispatch, so a session
that dies mid-flight leaves a durable, counted trace instead of silently re-dispatching and
quietly conditioning the corpus on "survived long enough to commit". The terminal record lands
after both outputs verify.

Dispatch itself is NOT done here -- a script cannot spawn the host's subagents. `start` prepares
and commits, then prints the two prompt files for the host to dispatch; `finish` takes it from the
written outputs.

Subcommands
  next      reconcile committed state against the frozen order; print the next pair to run
  start     guard the tree, materialize both arms' scratch bundles, commit the `started` record
  finish    verify both outputs, structurally grade them, commit the terminal attempt records
  status    print the reconciled state and rewrite nothing

Exit codes: 0 ok, 1 measured failure (guard tripped, output missing, record rejected), 2 plumbing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _canon  # type: ignore[import-not-found]  # noqa: E402
import grade_structural  # type: ignore[import-not-found]  # noqa: E402
from _paired_arm_prereg import SKILL_ROOT, load_record  # noqa: E402
from _paired_arm_validate import validate_attempt  # noqa: E402

REPO_ROOT = SKILL_ROOT.parent
OUT_DIR = SKILL_ROOT / "evals" / "paired-arm-outputs"
EXEC_PATH = OUT_DIR / "execution.json"
RESUME_PATH = OUT_DIR / "RESUME.md"
STUDY_RECORD = SKILL_ROOT / "evals" / "paired_arm_replication.json"

ARMS = ("with_skill", "without_skill")

# The pilot runs on two of the three excluded twin_defective scenarios: comparable material,
# formally outside the corpus, so no study output is inspected before the study is registered.
PILOT_SCENARIOS = {
    "principal-duplicated-rule-restraint": "restraint",
    "principal-process-owner-restraint": "restraint",
}

# grade_structural.py's general checks are the only per-output results that exist before semantic
# grading (5 of the 11 study scenarios have zero deterministic assertions). Only the canon-exact
# smell check is a skill_contract criterion -- it is the vocabulary axis the plan reports
# separately and keeps OUT of outcome scoring. The rest are output-contract adherence: real
# results, but not lift criteria in either direction, so `unclassified` is the honest label.
GENERAL_CHECK_CRITERION_CLASS = {"flagged_smells_canon_exact": "skill_contract"}


class Plumbing(Exception):
    """Cannot even attempt the operation -- exit 2."""


class Guard(Exception):
    """A measured refusal: the tree, the order, or an output is not in the required state."""


# ---- git -----------------------------------------------------------------------------------


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise Plumbing(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def head_sha() -> str:
    return git("rev-parse", "HEAD")


def porcelain() -> list[str]:
    out = git("status", "--porcelain")
    return [line for line in out.splitlines() if line.strip()]


def require_clean_tree() -> None:
    dirty = porcelain()
    if dirty:
        raise Guard(
            "working tree is not clean -- refusing to start a pair.\n"
            "  A second session sharing this worktree shares the index, so unrelated staged or\n"
            "  modified paths can be folded into this pair's commit silently.\n  "
            + "\n  ".join(dirty)
        )


def commit_allowlist(paths: list[Path], message: str) -> str:
    """Stage ONLY these paths, verify nothing else rode along, then commit."""
    rel = sorted({str(p.relative_to(REPO_ROOT)) for p in paths})
    git("add", "--", *rel)
    staged = set(git("diff", "--cached", "--name-only").splitlines())
    extra = {s for s in staged if not any(s == r or s.startswith(r + "/") for r in rel)}
    if extra:
        git("reset", "--quiet", "HEAD", "--", *sorted(extra))
        raise Guard(f"paths outside this pair's allowlist were staged: {sorted(extra)}")
    if not staged:
        raise Guard("nothing to commit -- expected this pair's records to have changed")
    git("commit", "--quiet", "-m", message)
    return head_sha()


# ---- state ---------------------------------------------------------------------------------


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise Plumbing(f"{path} does not exist -- run `init` first") from exc
    except json.JSONDecodeError as exc:
        raise Plumbing(f"{path} is not valid JSON: {exc}") from exc


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_mode(mode: str) -> tuple[list[dict], list[dict], dict[str, str]]:
    """-> (frozen order, terminal attempts, scenario set) for this mode."""
    execution = read_json(EXEC_PATH)
    if mode == "study":
        record = load_record(STUDY_RECORD)
        scenarios = {
            s: ("restraint" if s.endswith("-restraint") else "flag")
            for s in record["prereg"]["study_scenarios"]
        }
        return record["prereg"]["frozen_order"], record["attempts"], scenarios
    return execution["pilot"]["order"], execution["pilot"]["attempts"], dict(PILOT_SCENARIOS)


def pair_states(mode: str) -> list[dict]:
    order, attempts, _ = load_mode(mode)
    log = read_json(EXEC_PATH)["dispatch_log"]
    states = []
    for pair in order:
        pid = pair["pair_id"]
        starts = [e for e in log if e["mode"] == mode and e["pair_id"] == pid]
        terminal_arms = {
            a["arm"]
            for a in attempts
            if a.get("pair_id") == pid and a.get("grade_status_reason") != "superseded"
        }
        states.append(
            {
                **pair,
                "attempts_spent": len(starts),
                "terminal_arms": sorted(terminal_arms),
                "resolved": set(terminal_arms) == set(ARMS),
                "interrupted": bool(starts) and set(terminal_arms) != set(ARMS),
            }
        )
    return states


def next_pair(mode: str) -> dict | None:
    for st in pair_states(mode):
        if st["resolved"] or st["attempts_spent"] >= 2:
            continue
        return st
    return None


# ---- materialization -----------------------------------------------------------------------


def scratch_dir(root: Path, mode: str, pair_id: str, attempt: int) -> Path:
    return root / mode / pair_id / f"attempt{attempt}"


def materialize(mode: str, st: dict, attempt: int, root: Path) -> dict:
    """Copy each arm's assigned materials OUT of the repo and render its prompt there.

    The copies are what make the sandbox a fact rather than only an instruction: an arm handed an
    in-repo path knows exactly where evals.json -- the answer key -- lives.
    """
    record = load_record(STUDY_RECORD)
    prereg = record["prereg"]
    envelope = (SKILL_ROOT / prereg["dispatch_envelope"]["file"]).read_text()
    base = scratch_dir(root, mode, st["pair_id"], attempt)
    if base.exists():
        shutil.rmtree(base)
    manifest: dict[str, Any] = {}

    for arm in ARMS:
        arm_dir = base / arm
        (arm_dir / "materials").mkdir(parents=True)
        rels = [f"evals/scenarios/{st['scenario_id']}/scenario.md"]
        rels += prereg["arms"][arm]["materials"]
        copied = []
        for rel in rels:
            src = SKILL_ROOT / rel
            if not src.is_file():
                raise Plumbing(f"material does not exist: {src}")
            dst = arm_dir / "materials" / Path(rel).name
            shutil.copy(src, dst)
            digest = sha256_file(dst)
            frozen = prereg["material_hashes"].get(rel)
            if frozen is not None and frozen != digest:
                raise Guard(f"{rel} does not match its frozen material hash -- refusing dispatch")
            copied.append(
                {"material": rel, "copied_to": str(dst), "sha256": digest, "frozen": frozen}
            )
        template_rel = prereg["arms"][arm]["task_template"]
        template = (SKILL_ROOT / template_rel).read_text()
        prompt = (
            template.rstrip()
            + "\n\n"
            + envelope.replace(
                "{{MATERIAL_PATHS}}", "\n".join(f"- `{c['copied_to']}`" for c in copied)
            ).replace("{{WORK_DIR}}", str(arm_dir))
        )
        (arm_dir / "prompt.md").write_text(prompt)
        manifest[arm] = {
            "task_template": template_rel,
            "task_template_sha256": prereg["material_hashes"][template_rel],
            "materials": copied,
            "prompt_path": str(arm_dir / "prompt.md"),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "expected_output": str(arm_dir / "review-verdict.md"),
            "work_dir": str(arm_dir),
        }
    return manifest


# ---- attempt records -----------------------------------------------------------------------


def build_assertion_results(report: dict) -> list[dict]:
    results = []
    for i, g in enumerate(report["general_checks"]):
        results.append(
            {
                "source": "general_check",
                "assertion_index": i,
                "assertion_text": g["name"],
                "criterion_class": GENERAL_CHECK_CRITERION_CLASS.get(g["name"], "unclassified"),
                "passed": bool(g["pass"]),
                "rationale": g.get("detail", ""),
            }
        )
    for a in report["assertions"]:
        results.append(
            {
                "source": "evals_assertion",
                "assertion_index": _assertion_index(report["id"], a["text"]),
                "assertion_text": a["text"],
                "criterion_class": _criterion_class(report["id"], a["text"]),
                "passed": bool(a["pass"]),
                "rationale": a.get("detail", ""),
            }
        )
    return results


def _eval_entry(scenario_id: str) -> dict:
    evals = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text())["evals"]
    for e in evals:
        if e.get("name") == scenario_id:
            return e
    raise Plumbing(f"no evals.json entry named {scenario_id!r}")


def _assertion_index(scenario_id: str, text: str) -> int:
    """Positional 0-based index in evals.json's assertions[], recorded ALONGSIDE the verbatim
    text so a later reorder cannot silently repoint a stored result."""
    for i, a in enumerate(_eval_entry(scenario_id)["assertions"]):
        if a["text"] == text:
            return i
    raise Plumbing(f"assertion not found in {scenario_id}: {text!r}")


def _criterion_class(scenario_id: str, text: str) -> str:
    for a in _eval_entry(scenario_id)["assertions"]:
        if a["text"] == text:
            return a.get("criterion_class", "unclassified")
    raise Plumbing(f"assertion not found in {scenario_id}: {text!r}")


def build_attempt(
    st: dict, arm: str, attempt: int, out_path: Path | None, invalid_reason: str | None
) -> dict:
    base = {
        "pair_id": st["pair_id"],
        "scenario_id": st["scenario_id"],
        "arm": arm,
        "slot_index": st["rep"],
        "attempt_index": attempt,
    }
    if invalid_reason:
        return {
            **base,
            "trial_validity": {"status": "invalid", "reason": invalid_reason},
            "candidate_output_status": None,
            "verdict_json": None,
            "structural_report": None,
            "assertion_results": None,
            "raw_output_path": None,
            "grade_status": "not_applicable",
            "grade_status_reason": "exogenous_invalid",
        }
    assert out_path is not None
    rel_out = str(out_path.relative_to(SKILL_ROOT))
    try:
        report = grade_structural.grade(out_path, st["scenario_id"])
        verdict = grade_structural._load_candidate(out_path)
    except Exception as exc:
        entry = _eval_entry(st["scenario_id"])
        return {
            **base,
            "trial_validity": {"status": "valid", "reason": None},
            "candidate_output_status": "malformed",
            "malformed_detail": str(exc),
            "verdict_json": None,
            "structural_report": None,
            "assertion_results": [
                {
                    "source": "evals_assertion",
                    "assertion_index": i,
                    "assertion_text": a["text"],
                    "criterion_class": a.get("criterion_class", "unclassified"),
                    "passed": False,
                    "rationale": f"candidate output unparseable: {exc}",
                }
                for i, a in enumerate(entry["assertions"])
            ],
            "raw_output_path": rel_out,
        }
    return {
        **base,
        "trial_validity": {"status": "valid", "reason": None},
        "candidate_output_status": "ok",
        "verdict_json": verdict,
        "structural_report": report,
        "assertion_results": build_assertion_results(report),
        "raw_output_path": rel_out,
    }


# ---- RESUME --------------------------------------------------------------------------------


def write_resume(mode: str) -> None:
    execution = read_json(EXEC_PATH)
    lines = [
        "# Paired-arm run — handoff note",
        "",
        "**This note is a convenience. The commits are the authority.** A resuming session reads",
        "this, then verifies it against `git log`. Uncommitted work does not exist.",
        "",
    ]
    for m in ("pilot", "study"):
        try:
            states = pair_states(m)
        except (Plumbing, KeyError):
            continue
        done = [s for s in states if s["resolved"]]
        interrupted = [s for s in states if s["interrupted"]]
        exhausted = [s for s in states if not s["resolved"] and s["attempts_spent"] >= 2]
        nxt = next_pair(m)
        lines += [
            f"## {m}",
            "",
            f"- pairs complete: **{len(done)} / {len(states)}**",
            f"- next in frozen order: **{nxt['pair_id'] + ' (' + nxt['scenario_id'] + ' rep ' + str(nxt['rep']) + ', attempt ' + str(nxt['attempts_spent'] + 1) + ')' if nxt else 'none — mode complete'}**",
            f"- interrupted (started, no terminal record — attempt index spent): {[s['pair_id'] for s in interrupted] or 'none'}",
            f"- exhausted (2 attempts spent, unresolved): {[s['pair_id'] for s in exhausted] or 'none'}",
            "",
        ]
    cap = execution.get("pairs_per_session_cap")
    spend = execution.get("measured", {})
    lines += [
        "## Operational",
        "",
        f"- measured host concurrency: {execution.get('host_concurrency', 'not yet measured')}",
        f"- pairs-per-session cap: {cap if cap is not None else 'not yet derived'}",
        f"- measured spend to date: {spend.get('total_tokens', 'not yet recorded')}",
        "",
        "## Next action",
        "",
        "```bash",
        "cd contest-refactor",
        f"python3 scripts/paired_arm_run.py next --mode {mode}",
        "```",
    ]
    RESUME_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESUME_PATH.write_text("\n".join(lines) + "\n")


# ---- commands ------------------------------------------------------------------------------


def cmd_next(args: argparse.Namespace) -> int:
    st = next_pair(args.mode)
    if st is None:
        print(f"{args.mode}: DONE — every pair in the frozen order has a terminal record")
        return 0
    execution = read_json(EXEC_PATH)
    cap = execution.get("pairs_per_session_cap")
    if cap is not None and args.session_id:
        used = sum(
            1
            for e in execution["dispatch_log"]
            if e.get("session_id") == args.session_id and e["mode"] == args.mode
        )
        if used >= cap:
            print(f"session cap reached: {used}/{cap} pairs dispatched this session — stop here")
            return 1
    print(
        json.dumps(
            {
                "pair_id": st["pair_id"],
                "scenario_id": st["scenario_id"],
                "rep": st["rep"],
                "arm_order": st["arm_order"],
                "attempt_index": st["attempts_spent"] + 1,
                "interrupted_previously": st["interrupted"],
            },
            indent=2,
        )
    )
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    st = next_pair(args.mode)
    if st is None:
        print(f"{args.mode}: nothing to start")
        return 0
    if args.pair and st["pair_id"] != args.pair:
        raise Guard(f"next pair in frozen order is {st['pair_id']}, not {args.pair}")
    attempt = st["attempts_spent"] + 1
    require_clean_tree()
    pre_head = head_sha()
    manifest = materialize(args.mode, st, attempt, Path(args.scratch_root))

    execution = read_json(EXEC_PATH)
    execution["dispatch_log"].append(
        {
            "mode": args.mode,
            "pair_id": st["pair_id"],
            "scenario_id": st["scenario_id"],
            "rep": st["rep"],
            "attempt_index": attempt,
            "arm_order": st["arm_order"],
            "session_id": args.session_id,
            "state": "started",
            "pre_dispatch_head": pre_head,
            "arms": manifest,
        }
    )
    write_json(EXEC_PATH, execution)
    write_resume(args.mode)
    sha = commit_allowlist(
        [EXEC_PATH, RESUME_PATH],
        f"chore(contest-refactor): paired-arm {args.mode} {st['pair_id']} attempt {attempt} started",
    )
    base = scratch_dir(Path(args.scratch_root), args.mode, st["pair_id"], attempt)
    (base / "start_commit.txt").write_text(sha + "\n")
    print(
        json.dumps(
            {
                "pair_id": st["pair_id"],
                "attempt_index": attempt,
                "start_commit": sha,
                "dispatch_in_this_order": st["arm_order"],
                "prompts": {a: manifest[a]["prompt_path"] for a in ARMS},
                "expected_outputs": {a: manifest[a]["expected_output"] for a in ARMS},
            },
            indent=2,
        )
    )
    return 0


def cmd_finish(args: argparse.Namespace) -> int:
    states = {s["pair_id"]: s for s in pair_states(args.mode)}
    st = states.get(args.pair)
    if st is None:
        raise Guard(f"{args.pair} is not in the {args.mode} frozen order")
    attempt = st["attempts_spent"]
    base = scratch_dir(Path(args.scratch_root), args.mode, args.pair, attempt)
    start_commit = (base / "start_commit.txt").read_text().strip()
    if head_sha() != start_commit:
        raise Guard(
            f"HEAD moved since this pair started ({start_commit[:8]} -> {head_sha()[:8]}).\n"
            "  Another session committed into this worktree. Refusing to commit on top of it."
        )

    invalid = dict(kv.split("=", 1) for kv in args.invalid or [])
    canon = _canon.load_canon(SKILL_ROOT)
    attempts_new, committed_paths = [], [EXEC_PATH, RESUME_PATH]
    for arm in ARMS:
        reason = invalid.get(arm)
        out_path = None
        if not reason:
            src = base / arm / "review-verdict.md"
            if not src.is_file() or not src.read_text().strip():
                # Absent/empty output is an ADHERENCE failure, never an exogenous void: an
                # exogenous classification takes evidence and an explicit --invalid flag.
                src.parent.mkdir(parents=True, exist_ok=True)
                src.write_text("")
            dest = OUT_DIR / args.mode / args.pair / f"attempt{attempt}" / arm / "review-verdict.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dest)
            committed_paths.append(dest)
            out_path = dest
        attempts_new.append(build_attempt(st, arm, attempt, out_path, reason))

    scenarios = load_mode(args.mode)[2]
    for i, a in enumerate(attempts_new):
        issues = validate_attempt(a, i, canon, require_grade_status=False, scenarios=scenarios)
        if issues:
            raise Guard("attempt record rejected before commit:\n  " + "\n  ".join(issues))

    execution = read_json(EXEC_PATH)
    for entry in execution["dispatch_log"]:
        if (
            entry["mode"] == args.mode
            and entry["pair_id"] == args.pair
            and entry["attempt_index"] == attempt
        ):
            entry["state"] = "finished"
            entry["usage"] = json.loads(Path(args.usage).read_text()) if args.usage else None
    if args.mode == "pilot":
        execution["pilot"]["attempts"] += attempts_new
        write_json(EXEC_PATH, execution)
    else:
        write_json(EXEC_PATH, execution)
        record = load_record(STUDY_RECORD)
        record["record_state"] = "in_progress"
        record["attempts"] += attempts_new
        write_json(STUDY_RECORD, record)
        committed_paths.append(STUDY_RECORD)
    write_resume(args.mode)
    sha = commit_allowlist(
        committed_paths,
        f"chore(contest-refactor): paired-arm {args.mode} {args.pair} attempt {attempt} complete",
    )
    print(
        json.dumps(
            {
                "pair_id": args.pair,
                "attempt_index": attempt,
                "commit": sha,
                "arms": {
                    a["arm"]: {
                        "trial_validity": a["trial_validity"]["status"],
                        "candidate_output_status": a["candidate_output_status"],
                    }
                    for a in attempts_new
                },
            },
            indent=2,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    for st in pair_states(args.mode):
        flag = (
            "resolved"
            if st["resolved"]
            else ("interrupted" if st["interrupted"] else f"pending ({st['attempts_spent']} spent)")
        )
        print(f"{st['pair_id']:12} {st['scenario_id']:42} rep {st['rep']}  {flag}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (
        ("next", cmd_next),
        ("start", cmd_start),
        ("finish", cmd_finish),
        ("status", cmd_status),
    ):
        sp = sub.add_parser(name)
        sp.add_argument("--mode", choices=("study", "pilot"), required=True)
        sp.add_argument("--scratch-root", default="/tmp/paired-arm")
        sp.add_argument("--session-id", default=None)
        sp.add_argument("--pair", default=None)
        sp.add_argument("--usage", default=None, help="path to a JSON file of measured usage")
        sp.add_argument(
            "--invalid",
            action="append",
            metavar="ARM=REASON",
            help="mark an arm exogenously invalid (canon reason). Never inferred -- an exogenous "
            "classification takes evidence, per the candidate_output_rule.",
        )
        sp.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except Guard as exc:
        print(f"paired_arm_run: REFUSED: {exc}", file=sys.stderr)
        return 1
    except Plumbing as exc:
        print(f"paired_arm_run: PLUMBING: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
