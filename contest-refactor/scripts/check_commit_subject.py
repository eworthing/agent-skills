#!/usr/bin/env python3
"""Pre-commit G22 subject check: validate a drafted commit subject before `git commit`.

Reuses the exact G22 regexes from _artifact_core.py (never duplicated) so a
malformed subject fails BEFORE it lands, instead of being diagnosed after the
fact from git log. Production motivation: two BenchHype commits landed with a
fabricated `stable_id F-NEW` because nothing checked the drafted subject
pre-commit (register "Instrumented run #7", additional defect #5).

Usage:
    python3 scripts/check_commit_subject.py --subject '<drafted subject>'

Exit 0: subject matches the G22 pattern (finding-bearing or no-finding form).
Exit 1: subject does not match -- fix the draft; do not `git commit` it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _artifact_core import (
    _G22_COMMIT_SUBJECT_NO_FINDING_RE,
    _G22_COMMIT_SUBJECT_RE,
)

_ERROR = (
    "commit subject does not match the G22 pattern: "
    "`loop <N>: <verb-phrase>; finding F<n> (stable_id F-<NNN>) <status> "
    "[registry: +<n> findings(, ~<n> occurrences)?]` or the no-finding form "
    "`loop <N>: <verb-phrase>; no findings [registry: +0 findings]`"
)


def check(subject: str) -> str | None:
    """Return None if `subject` matches G22, else an error message."""
    if _G22_COMMIT_SUBJECT_RE.match(subject) or _G22_COMMIT_SUBJECT_NO_FINDING_RE.match(subject):
        return None
    return _ERROR


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True, help="the drafted commit subject to check")
    args = parser.parse_args()
    error = check(args.subject)
    if error:
        print(f"FAIL: {error}", file=sys.stderr)
        print(f"  got: {args.subject!r}", file=sys.stderr)
        return 1
    print("OK: commit subject matches G22")
    return 0


if __name__ == "__main__":
    sys.exit(main())
