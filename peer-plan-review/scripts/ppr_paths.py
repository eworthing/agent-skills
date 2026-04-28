#!/usr/bin/env python3
"""
ppr_paths.py — Canonical temp-path helper for peer-plan-review sessions.

Given a review id, emit the standard temp file locations used by the skill.
This keeps host-side shell snippets from reimplementing path construction.
"""

import argparse
import json
import re
import shlex
import sys
import tempfile
from pathlib import Path


_REVIEW_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def parse_args():
    parser = argparse.ArgumentParser(description="Emit canonical peer-plan-review temp paths")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--review-id", help="Review id to build temp paths for")
    source.add_argument(
        "--review-id-file",
        help="File containing a review id from a prior round or resumed session",
    )
    parser.add_argument(
        "--tmpdir",
        default=None,
        help="Override temp directory (defaults to Python tempfile.gettempdir())",
    )
    parser.add_argument(
        "--format",
        choices=("json", "shell"),
        default="json",
        help="Output format: JSON object or shell export statements",
    )
    return parser.parse_args()


def load_review_id(args):
    if args.review_id:
        review_id = args.review_id.strip()
    else:
        path = Path(args.review_id_file)
        try:
            review_id = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ValueError(f"could not read review id file: {path}: {exc}") from exc
        if not review_id:
            raise ValueError(f"review id file is empty: {path}")

    if not _REVIEW_ID_RE.match(review_id):
        raise ValueError(
            "review id must contain only letters, digits, dot, underscore, or hyphen"
        )
    return review_id


def build_paths(review_id, tmpdir=None):
    base = Path(tmpdir or tempfile.gettempdir())
    prefix = f"ppr-{review_id}"
    return {
        "review_id": review_id,
        "tmpdir": str(base),
        "plan_file": str(base / f"{prefix}-plan.md"),
        "prompt_file": str(base / f"{prefix}-prompt.md"),
        "output_file": str(base / f"{prefix}-review.md"),
        "session_file": str(base / f"{prefix}-session.json"),
        "events_file": str(base / f"{prefix}-events.jsonl"),
        "error_log": str(base / f"{prefix}-errors.jsonl"),
    }


def render_shell(paths):
    env_map = {
        "REVIEW_ID": paths["review_id"],
        "TMPDIR": paths["tmpdir"],
        "PLAN_FILE": paths["plan_file"],
        "PROMPT_FILE": paths["prompt_file"],
        "OUTPUT_FILE": paths["output_file"],
        "SESSION_FILE": paths["session_file"],
        "EVENTS_FILE": paths["events_file"],
        "ERROR_LOG": paths["error_log"],
    }
    return "\n".join(
        f"export {name}={shlex.quote(value)}" for name, value in env_map.items()
    )


def main():
    args = parse_args()
    try:
        paths = build_paths(load_review_id(args), tmpdir=args.tmpdir)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.format == "shell":
        print(render_shell(paths))
    else:
        json.dump(paths, sys.stdout, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
