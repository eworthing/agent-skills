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
  python3 scripts/archive_history.py write <current-review.json> <history.json> \
      --md <history.md> --md-divider loop --md-body <path-or-'-'>
      # ...also appends the REVIEW_HISTORY.md divider block, so both artifacts
      # move in lockstep (retro #3/#4). --md-divider promotion writes the
      # canonical `--- HALT_SUCCESS <verb> (UTC ...) ---` form instead (see
      # promotion_divider()). append-if-absent: a retry with an identical
      # divider+body block is a no-op, never a duplicate.
  python3 scripts/archive_history.py verify <current-review.json> <history.json>
      # exit 0 iff history.loops[-1] parses equal to current-review
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
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


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def loop_divider(loop: int, ts: str) -> str:
    """`--- Loop <N> (UTC <ts>) ---` per output-format-markdown-archive.md."""
    return f"--- Loop {loop} (UTC {ts}) ---"


def promotion_divider(verb: str, ts: str) -> str:
    """`--- HALT_SUCCESS <verb> (UTC <ts>) ---` -- the canonical promotion form
    (retro #3). Also used, with a different verb, by the reset handoff.
    """
    return f"--- HALT_SUCCESS {verb} (UTC {ts}) ---"


def append_divider_block(md_path: Path, divider: str, body: str) -> bool:
    """Append `divider` + `body` to `md_path`, atomically, unless that exact
    block is already the file's tail.

    Append-if-absent: a caller retrying the identical write (same divider,
    same body -- e.g. after a crash before the promotion commit) gets a no-op
    instead of a duplicate block. This is the smallest contract that removes
    hand-formatting of the divider itself; it does not attempt the JSON side's
    richer append-or-replace-last merge.

    Returns True if it wrote, False if the block was already present.
    """
    block = f"{divider}\n{body}"
    if not block.endswith("\n"):
        block += "\n"
    existing = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    if existing.endswith(block):
        return False
    if existing and not existing.endswith("\n"):
        existing += "\n"
    tmp_path = md_path.parent / f"{md_path.name}.tmp"
    tmp_path.write_text(existing + block, encoding="utf-8")
    tmp_path.replace(md_path)
    return True


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_history(path: Path, schema_version: int) -> dict:
    if not path.exists():
        return {"schema_version": schema_version, "loops": []}
    history = _load(path)
    if not isinstance(history, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return history


def _cmd_write(args: argparse.Namespace) -> int:
    current_review = _load(args.current_review)
    history = _load_history(args.history, current_review.get("schema_version", 1))
    updated = append_or_replace(history, current_review)

    tmp_path = args.history.parent / f"{args.history.name}.tmp"
    tmp_path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(args.history)
    print(f"wrote {len(updated['loops'])} loops[] entries to {args.history}")

    if args.md is not None:
        if not args.md_body:
            raise ValueError("--md requires --md-body <path-or-'-'>")
        ts = args.md_ts or _utc_now_iso()
        if args.md_divider == "promotion":
            divider = promotion_divider(args.md_verb, ts)
        else:
            loop_n = current_review.get("loop")
            if not isinstance(loop_n, int):
                raise ValueError("--md-divider loop requires an integer 'loop' field")
            divider = loop_divider(loop_n, ts)
        body = (
            sys.stdin.read()
            if args.md_body == "-"
            else Path(args.md_body).read_text(encoding="utf-8")
        )
        wrote = append_divider_block(args.md, divider, body)
        print(f"{'wrote' if wrote else 'no-op (already present)'} divider block to {args.md}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    current_review = _load(args.current_review)
    history = _load(args.history)
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
    parser = argparse.ArgumentParser(description="REVIEW_HISTORY archive helper")
    sub = parser.add_subparsers(dest="command", required=True)
    write_p = None
    for name, fn, help_text in (
        ("write", _cmd_write, "append-or-replace-last, then atomic write"),
        ("verify", _cmd_verify, "exit 0 iff loops[-1] equals CURRENT_REVIEW.json"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("current_review", type=Path, help="path to CURRENT_REVIEW.json")
        p.add_argument("history", type=Path, help="path to REVIEW_HISTORY.json")
        p.set_defaults(func=fn)
        if name == "write":
            write_p = p
    write_p.add_argument(
        "--md", type=Path, default=None, help="REVIEW_HISTORY.md path; also append a divider block"
    )
    write_p.add_argument(
        "--md-divider",
        choices=("loop", "promotion"),
        default="loop",
        help="divider form (with --md)",
    )
    write_p.add_argument(
        "--md-verb", default="promotion", help="verb phrase for --md-divider promotion"
    )
    write_p.add_argument("--md-ts", default=None, help="UTC ISO-8601 timestamp; default now")
    write_p.add_argument(
        "--md-body", default=None, help="path to body text, or '-' for stdin (required with --md)"
    )
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
