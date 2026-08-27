#!/usr/bin/env python3
"""Join run-2 blind scores against the arm key and apply the pre-registered rule.

The scorer never sees the key; this script is what unblinds, and it is written
before any score exists so the arithmetic cannot be tuned to the outcome. Run:

    python3 join_run2.py <scores.json> <key.json>

`scores.json` is the blind scorer's output: {"r01": {"A": ..., "B": ...}, ...}
`key.json` maps each id to [arm, order].
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# Pre-registered thresholds (PREREG_RUN2.md). Do not edit to fit a result.
PANDAS_MIN_DROP = 2  # of 5; below this the arm is noise at n=5
CONFIG_MIN_RECALL = 4  # of 5, in the arm
RUN1_CONTROL_PANDAS_OVER_MERGE = 5  # of 5, from CONTROL_SCORED.md


def main() -> int:
    scores = json.loads(Path(sys.argv[1]).read_text())
    key = json.loads(Path(sys.argv[2]).read_text())

    missing = sorted(set(key) - set(scores))
    if missing:
        print(f"FAIL: scorer did not label {missing}")
        return 1

    arms: dict[str, list[str]] = {"control": [], "arm": []}
    for rid, (arm, _order) in sorted(key.items()):
        arms[arm].append(rid)

    tally = {}
    for arm, ids in arms.items():
        a = Counter(scores[i]["A"] for i in ids)
        b = Counter(scores[i]["B"] for i in ids)
        tally[arm] = {"n": len(ids), "A": a, "B": b}

    print("=== Case A — pandas (OVER_MERGE is the failure) ===")
    for arm in ("control", "arm"):
        t = tally[arm]
        print(
            f"  {arm:8} n={t['n']}  OVER_MERGE={t['A']['OVER_MERGE']}  NO_MERGE={t['A']['NO_MERGE']}"
        )
    print("=== Case B — config (CONSOLIDATED is the correct answer) ===")
    for arm in ("control", "arm"):
        t = tally[arm]
        print(
            f"  {arm:8} n={t['n']}  CONSOLIDATED={t['B']['CONSOLIDATED']}  "
            f"LOCAL_REPAIR={t['B']['LOCAL_REPAIR']}  MISSED={t['B']['MISSED']}"
        )

    c_over = tally["control"]["A"]["OVER_MERGE"]
    a_over = tally["arm"]["A"]["OVER_MERGE"]
    c_cons = tally["control"]["B"]["CONSOLIDATED"]
    a_cons = tally["arm"]["B"]["CONSOLIDATED"]
    drop = c_over - a_over

    print("\n=== Pre-registered decision ===")
    print(f"  pandas over-merge: control {c_over}/5 -> arm {a_over}/5 (drop {drop})")
    print(f"  config recall:     control {c_cons}/5 -> arm {a_cons}/5")
    print(f"  (run-1 control pandas baseline was {RUN1_CONTROL_PANDAS_OVER_MERGE}/5)")

    reasons = []
    if a_cons < c_cons:
        reasons.append(
            f"VETO: config consolidation recall fell ({c_cons} -> {a_cons}). "
            "Over-suppression outweighs any pandas gain."
        )
    if a_cons < CONFIG_MIN_RECALL:
        reasons.append(f"config recall {a_cons}/5 is below the required {CONFIG_MIN_RECALL}/5")
    if drop < PANDAS_MIN_DROP:
        reasons.append(f"pandas drop {drop} is below the {PANDAS_MIN_DROP}-of-5 noise floor")

    if reasons:
        print("\n  DO NOT SHIP:")
        for r in reasons:
            print(f"    - {r}")
    else:
        print("\n  SHIP: both pre-registered conditions met.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
