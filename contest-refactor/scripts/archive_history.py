#!/usr/bin/env python3
"""Owns the REVIEW_HISTORY.json append-vs-replace-last rule so nothing hand-edits it.

Per references/output-format-state-schemas.md:192,326-341: each loop's complete
CURRENT_REVIEW.json is appended to the top-level `loops[]` array, except a
same-run same-loop replay or HALT_SUCCESS_candidate promotion replaces only the
last entry -- matched on (run_id, loop, schema_version); when run_id is
unavailable on a legacy artifact, only the last entry may match on
(loop, schema_version) (tuple equality already restricts matching to the last
entry, in both cases -- see append_or_replace()).

Register "Instrumented run #7" P1 #6: a production run invented a
`runs[].loops[]` top-level shape by hand, added `archived_at`, and wrote an
order-unstable dedup script. This helper never produces any shape but
top-level `loops[]`, and refuses to write when the existing file already has
a different one, rather than trying to migrate or merge it.

CLI:
  python3 scripts/archive_history.py write <current-review.json> <history.json>
      # append-or-replace-last, atomic write (Path.replace)
  python3 scripts/archive_history.py verify <current-review.json> <history.json>
      # exit 0 iff history.loops[-1] parses equal to current-review
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _key(entry: dict) -> tuple[Any, Any, Any]:
    return entry.get("run_id"), entry.get("loop"), entry.get("schema_version")


def append_or_replace(history: dict, current_review: dict) -> dict:
    """Return `history` with `current_review` appended, or replacing the last
    entry when it shares (run_id, loop, schema_version) with current_review.

    Never searches or overwrites any entry but the last one.
    """
    loops = history.get("loops")
    if not isinstance(loops, list):
        raise ValueError(
            "REVIEW_HISTORY.json must have a top-level 'loops' list; refusing to write any "
            "other shape (e.g. a hand-invented runs[].loops[])"
        )
    new_loops = list(loops)
    if (
        new_loops
        and isinstance(new_loops[-1], dict)
        and _key(new_loops[-1]) == _key(current_review)
    ):
        new_loops[-1] = current_review
    else:
        new_loops.append(current_review)
    return {**history, "loops": new_loops}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_history(path: Path, schema_version: int) -> dict:
    if not path.exists():
        return {"schema_version": schema_version, "loops": []}
    history = _load(path)
    if not isinstance(history, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return history


def _cmd_write(current_review_path: Path, history_path: Path) -> int:
    current_review = _load(current_review_path)
    history = _load_history(history_path, current_review.get("schema_version", 1))
    updated = append_or_replace(history, current_review)

    tmp_path = history_path.parent / f"{history_path.name}.tmp"
    tmp_path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(history_path)
    print(f"wrote {len(updated['loops'])} loops[] entries to {history_path}")
    return 0


def _cmd_verify(current_review_path: Path, history_path: Path) -> int:
    current_review = _load(current_review_path)
    history = _load(history_path)
    loops = history.get("loops") if isinstance(history, dict) else None
    if not isinstance(loops, list) or not loops:
        sys.stderr.write("MISMATCH: REVIEW_HISTORY.json has no loops[] entries\n")
        return 1
    if loops[-1] != current_review:
        sys.stderr.write("MISMATCH: loops[-1] does not equal CURRENT_REVIEW.json verbatim\n")
        return 1
    print("OK: REVIEW_HISTORY.json loops[-1] matches CURRENT_REVIEW.json")
    return 0


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="REVIEW_HISTORY.json archive helper")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn, help_text in (
        ("write", _cmd_write, "append-or-replace-last, then atomic write"),
        ("verify", _cmd_verify, "exit 0 iff loops[-1] equals CURRENT_REVIEW.json"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("current_review", type=Path, help="path to CURRENT_REVIEW.json")
        p.add_argument("history", type=Path, help="path to REVIEW_HISTORY.json")
        p.set_defaults(func=fn)
    args = parser.parse_args(argv)
    try:
        return args.func(args.current_review, args.history)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
