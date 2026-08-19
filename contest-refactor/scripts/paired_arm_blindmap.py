#!/usr/bin/env python3
"""Generate the frozen blind map + grading order for one rung of the paired-arm study.

The plan requires the grading order to be frozen and committed for the same reason the
dispatch order is: multi-session grading in natural order could align arm style with
grader or service drift. Both outputs of a pair stay temporally adjacent.

Rung 1's map was built ad hoc and is NOT reproducible from this script; that discrepancy
is recorded in execution.json rather than corrected, since its grades are already committed.

Exit codes: 0 ok / 2 plumbing.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent / "evals"
RECORD = EVALS / "paired_arm_replication.json"
ARMS = ("with_skill", "without_skill")


def subsample_pairs(prereg: dict) -> list[str]:
    """The preregistered 20% double-graded subsample.

    The prereg freezes the seed, fraction, and size but NOT the derivation -- a real gap,
    named in execution.json. This is the canonical reading: random.Random(seed).sample over
    the pair ids in ascending order. It is invariant to whether the population is the frozen
    order or a sort of it, because pair ids were assigned ascending along the frozen order.
    """
    ids = sorted(e["pair_id"] for e in prereg["frozen_order"])
    return sorted(
        random.Random(prereg["grading_subsample_seed"]).sample(
            ids, prereg["grading_subsample_size_pairs"]
        )
    )


def terminal_outputs(record: dict) -> dict[tuple[str, str], str]:
    """(pair_id, arm) -> the TERMINAL attempt's committed raw_output_path.

    Never construct `.../attempt1/...` by hand. Attempt 1 is not always terminal: pair-015's is
    attempt 4 (three attempts burned dispatching zero arms, see execution.json attempt_grants), and
    a superseded attempt must never be graded in place of the one that resolved the pair. The
    record already names the right file per attempt, so read it rather than rebuilding it.
    """
    out: dict[tuple[str, str], str] = {}
    for a in record["attempts"]:
        if a.get("grade_status_reason") == "superseded" or not a.get("raw_output_path"):
            continue
        out[(a["pair_id"], a["arm"])] = a["raw_output_path"]
    return out


def build(prereg: dict, rung: int, pairs: list[str], outputs_root: Path, record: dict) -> dict:
    terminal = terminal_outputs(record)
    rng = random.Random(f"{prereg['grading_subsample_seed']}:rung{rung}:blindmap")
    subsample = set(subsample_pairs(prereg))

    entries: dict[str, dict] = {}
    per_pair: dict[str, list[str]] = {}
    for pair in sorted(pairs):
        arms = list(ARMS)
        rng.shuffle(arms)
        per_pair[pair] = []
        for arm in arms:
            oid = f"OUT-{rng.getrandbits(48):012x}"
            rel = terminal.get((pair, arm))
            if rel is None:
                print(f"no terminal attempt recorded for {pair}/{arm}", file=sys.stderr)
                raise SystemExit(2)
            candidate = EVALS.parent / rel
            if not candidate.is_file():
                print(f"missing candidate: {candidate}", file=sys.stderr)
                raise SystemExit(2)
            entries[oid] = {
                "pair": pair,
                "arm": arm,
                "candidate": str(candidate.relative_to(EVALS.parent)),
                "in_subsample": pair in subsample,
                "prompt": f"/tmp/paired-arm/grading/{oid}.prompt.md",
            }
            per_pair[pair].append(oid)

    pair_order = sorted(pairs)
    rng.shuffle(pair_order)
    grading_order = [oid for pair in pair_order for oid in per_pair[pair]]
    return {"map": entries, "grading_order": grading_order}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rung", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    record = json.loads(RECORD.read_text())
    prereg = record["prereg"]
    rung = prereg["execution_ladder"].get(f"rung_{args.rung}")
    if rung is None:
        print(f"no such rung: {args.rung}", file=sys.stderr)
        return 2
    wanted = set(rung.get("scenarios") or [rung["scenario"]])
    pairs = [e["pair_id"] for e in prereg["frozen_order"] if e["scenario_id"] in wanted]

    built = build(prereg, args.rung, pairs, EVALS / "paired-arm-outputs" / "study", record)
    Path(args.out).write_text(json.dumps(built, indent=2) + "\n")
    print(
        json.dumps(
            {
                "rung": args.rung,
                "outputs": len(built["map"]),
                "double_graded": sum(1 for v in built["map"].values() if v["in_subsample"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
