#!/usr/bin/env python3
"""
paths.py — Canonical temp-path helper (also runnable as a CLI).

Ported from peer-plan-review/scripts/ppr_paths.py. Given a review id,
emits the standard temp file locations used by a session. Keeps host-side
shell snippets from reimplementing path construction.

CLI usage (skill scripts can `eval "$(... --format shell)"` to export
all six path env vars at once):

    python3 -m common.session.paths --review-id <id> --format shell
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
    # Not required at the argparse layer: --cleanup accepts --id-prefix instead
    # of a review id. main() validates the right combination per mode.
    source = parser.add_mutually_exclusive_group(required=False)
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
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Reclaim this review's per-run Codex homes (manifest + session files) and exit",
    )
    parser.add_argument(
        "--id-prefix",
        default=None,
        help="With --cleanup: the literal review prefix (e.g. 'qr-<quorum_id>'). "
        "Defaults to 'ppr-<review-id>' when --review-id is given instead.",
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
        "codex_home_manifest": str(base / f"{prefix}-codex-homes.list"),
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
        "CODEX_HOME_MANIFEST": paths["codex_home_manifest"],
    }
    return "\n".join(
        f"export {name}={shlex.quote(value)}" for name, value in env_map.items()
    )


def main():
    args = parse_args()

    if args.cleanup:
        # Relative import: this module is always imported as part of the package
        # (_common.session.paths in skills, common.session.paths in tests), so a
        # sibling import resolves; it is never run as a bare script.
        from .codex_home import cleanup_review_homes

        if args.id_prefix:
            prefix = args.id_prefix
        else:
            try:
                prefix = f"ppr-{load_review_id(args)}"
            except ValueError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                sys.exit(1)
        tmpdir = args.tmpdir or tempfile.gettempdir()
        remaining = cleanup_review_homes(tmpdir, prefix)
        if remaining:
            print(f"Warning: {remaining} Codex home(s) could not be removed", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    if not (args.review_id or args.review_id_file):
        print("Error: one of --review-id or --review-id-file is required", file=sys.stderr)
        sys.exit(1)
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
