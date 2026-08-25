#!/usr/bin/env python3
"""Self-test for archive_history.py (register "Instrumented run #7" P1 #6).

Covers: append, same-key replace, legacy (no run_id) match-last-only, tail-
equality verify, and refusal to write over a non-loops[] top-level shape (the
hand-invented runs[].loops[] the real run produced).

Run: python3 scripts/_archive_history_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import archive_history as ah

SCRIPT = Path(__file__).with_name("archive_history.py")


def _review(*, run_id, loop, schema_version=4, **extra) -> dict:
    review = {"run_id": run_id, "loop": loop, "schema_version": schema_version, "state": "CONTINUE"}
    review.update(extra)
    return review


def main() -> int:
    failures: list[str] = []

    # --- append_or_replace(): unit-level ---------------------------------

    loop1 = _review(run_id="run-A", loop=1)
    history = {"schema_version": 4, "loops": [loop1]}

    loop2 = _review(run_id="run-A", loop=2)
    appended = ah.append_or_replace(history, loop2)
    if [e["loop"] for e in appended["loops"]] != [1, 2]:
        failures.append(
            f"append: expected loops [1, 2], got {[e['loop'] for e in appended['loops']]}"
        )
    if history["loops"] != [loop1]:
        failures.append("append: mutated the input history in place")

    replay = _review(run_id="run-A", loop=2, narrative="replayed")
    replaced = ah.append_or_replace(appended, replay)
    if len(replaced["loops"]) != 2 or replaced["loops"][-1] != replay:
        failures.append("same-key replace: expected loops[-1] replaced in place, count unchanged")

    promotion = _review(run_id="run-A", loop=2, state="HALT_SUCCESS")
    promoted = ah.append_or_replace(replaced, promotion)
    if len(promoted["loops"]) != 2 or promoted["loops"][-1] != promotion:
        failures.append(
            "promotion replace: HALT_SUCCESS_candidate->HALT_SUCCESS must replace, not append"
        )

    legacy_last = _review(run_id=None, loop=1, schema_version=1)
    legacy_history = {"schema_version": 1, "loops": [legacy_last]}
    legacy_replay = _review(run_id=None, loop=1, schema_version=1, narrative="legacy replay")
    legacy_result = ah.append_or_replace(legacy_history, legacy_replay)
    if len(legacy_result["loops"]) != 1 or legacy_result["loops"][-1] != legacy_replay:
        failures.append(
            "legacy match: no-run_id artifacts must still replace on (loop, schema_version)"
        )

    legacy_new_loop = _review(run_id=None, loop=2, schema_version=1)
    legacy_appended = ah.append_or_replace(legacy_result, legacy_new_loop)
    if [e["loop"] for e in legacy_appended["loops"]] != [1, 2]:
        failures.append("legacy append: a genuinely new loop must append, not overwrite loop 1")

    try:
        ah.append_or_replace({"runs": [{"loops": [loop1]}]}, loop2)
        failures.append("refusal: a runs[].loops[] shaped history must raise, not silently adapt")
    except ValueError as exc:
        if "loops" not in str(exc):
            failures.append(f"refusal message should name 'loops': {exc}")

    try:
        ah.append_or_replace({"schema_version": 4, "loops": "not-a-list"}, loop2)
        failures.append("refusal: loops must be a list, not any other type")
    except ValueError:
        pass

    # --- CLI: write + verify, against real files --------------------------

    with tempfile.TemporaryDirectory(prefix="contest-archive-") as tmp:
        base = Path(tmp)
        current_review = base / "CURRENT_REVIEW.json"
        review_history = base / "REVIEW_HISTORY.json"

        review = _review(run_id="run-X", loop=1)
        current_review.write_text(json.dumps(review), encoding="utf-8")

        p = subprocess.run(
            [sys.executable, str(SCRIPT), "write", str(current_review), str(review_history)],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            failures.append(f"CLI write (fresh history): exit {p.returncode}\n{p.stderr}")
        written = json.loads(review_history.read_text(encoding="utf-8"))
        if written.get("loops") != [review]:
            failures.append(f"CLI write (fresh history): expected loops == [review], got {written}")

        p = subprocess.run(
            [sys.executable, str(SCRIPT), "verify", str(current_review), str(review_history)],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            failures.append(f"CLI verify (should match): exit {p.returncode}\n{p.stderr}")

        # A same-run same-loop rewrite must replace, not double-append.
        review["narrative"] = "revised"
        current_review.write_text(json.dumps(review), encoding="utf-8")
        p = subprocess.run(
            [sys.executable, str(SCRIPT), "write", str(current_review), str(review_history)],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            failures.append(f"CLI write (replace): exit {p.returncode}\n{p.stderr}")
        written = json.loads(review_history.read_text(encoding="utf-8"))
        if written.get("loops") != [review]:
            failures.append(f"CLI write (replace): expected a single replaced entry, got {written}")

        p = subprocess.run(
            [sys.executable, str(SCRIPT), "verify", str(current_review), str(review_history)],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            failures.append(f"CLI verify (post-replace): exit {p.returncode}\n{p.stderr}")

        # Tail mismatch must be caught.
        stale_review = base / "STALE_REVIEW.json"
        stale_review.write_text(
            json.dumps(_review(run_id="run-X", loop=1, narrative="stale")), encoding="utf-8"
        )
        p = subprocess.run(
            [sys.executable, str(SCRIPT), "verify", str(stale_review), str(review_history)],
            capture_output=True,
            text=True,
        )
        if p.returncode == 0:
            failures.append("CLI verify: a stale current-review must fail verify, got exit 0")

        # A hand-invented runs[].loops[] shape must be refused, never written over.
        review_history.write_text(json.dumps({"runs": [{"loops": [review]}]}), encoding="utf-8")
        p = subprocess.run(
            [sys.executable, str(SCRIPT), "write", str(current_review), str(review_history)],
            capture_output=True,
            text=True,
        )
        if p.returncode == 0:
            failures.append(
                "CLI write: a runs[].loops[] shaped history must be refused, got exit 0"
            )
        untouched = json.loads(review_history.read_text(encoding="utf-8"))
        if "runs" not in untouched:
            failures.append("CLI write: refusal must leave the bad file untouched")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("OK: archive_history — append, same-key/legacy replace, verify, and refusal all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
