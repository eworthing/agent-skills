#!/usr/bin/env python3
"""Write committed grades back into the paired-arm record's attempt entries.

Every value is RECOMPUTED from committed, immutable inputs -- the candidate outputs in
evals/paired-arm-outputs/study/ and the grader replies in <rung>-grades/ -- so this script is
idempotent and auditable. It never invents a grade and never edits a non-null field to a
different value; a conflict is a hard error, not a silent overwrite.

Exit codes: 0 ok / 1 conflict with an existing recorded grade / 2 plumbing.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RECORD = ROOT / "evals" / "paired_arm_replication.json"
OUTPUTS = ROOT / "evals" / "paired-arm-outputs"


def load_reply(path: Path) -> dict:
    text = path.read_text()
    m = re.search(r"```json\s*\n(.*?)```", text, re.S)
    return json.loads(m.group(1) if m else text)


def mechanical(scenario: str, candidate: str) -> str | None:
    r = subprocess.run(
        [
            "python3",
            str(HERE / "paired_arm_grade.py"),
            "mechanical",
            "--scenario",
            scenario,
            "--candidate",
            candidate,
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if r.returncode not in (0, 1):
        print(f"mechanical failed for {candidate}: {r.stderr[-300:]}", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(r.stdout).get("mechanical_grade")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--rung",
        type=int,
        action="append",
        required=True,
        help="repeatable; each needs rung<N>-blind-map.json and rung<N>-grades/",
    )
    args = ap.parse_args()

    record = json.loads(RECORD.read_text())
    prereg = record["prereg"]
    grading = prereg["grading"]
    by_key = {(a["pair_id"], a["arm"]): a for a in record["attempts"]}

    written = conflicts = 0
    for rung in args.rung:
        bm_path = OUTPUTS / f"rung{rung}-blind-map.json"
        grades_dir = OUTPUTS / f"rung{rung}-grades"
        if not bm_path.is_file() or not grades_dir.is_dir():
            print(f"rung {rung}: missing blind map or grades dir", file=sys.stderr)
            return 2
        bm = json.loads(bm_path.read_text())
        entries = bm.get("map", bm)
        for oid, v in entries.items():
            attempt = by_key.get((v["pair"], v["arm"]))
            if attempt is None:
                print(f"no attempt for {v['pair']}/{v['arm']}", file=sys.stderr)
                return 2
            # Rung 1 ran a haiku->sonnet cascade: where an escalation happened, the
            # `-sonnet` reply is the TERMINAL grade and the base reply is the superseded
            # haiku one (3 of which are unparseable JSON, which is why it escalated).
            escalated = grades_dir / f"{oid}-sonnet.reply.md"
            reply_path = escalated if escalated.is_file() else grades_dir / f"{oid}.reply.md"
            if not reply_path.is_file():
                print(f"missing reply for {oid}", file=sys.stderr)
                return 2
            reply = load_reply(reply_path)
            new = {
                "grade_status": "graded",
                "mechanical_grade": mechanical(attempt["scenario_id"], v["candidate"]),
                "semantic_grade": reply["semantic_grade"],
                "grader_id": oid,
                "grader_reply": str(reply_path.relative_to(ROOT)),
                "grader_model": grading["grader_model"],
                "grader_prompt_sha256": grading["grader_prompt_sha256"],
            }
            for k, val in new.items():
                cur = attempt.get(k)
                if cur is not None and cur != val:
                    print(
                        f"CONFLICT {oid} {k}: recorded {cur!r} != recomputed {val!r}",
                        file=sys.stderr,
                    )
                    conflicts += 1
                attempt[k] = val
            written += 1

    if conflicts:
        return 1
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(
        json.dumps(
            {"attempts_graded": written, "attempts_total": len(record["attempts"])}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
