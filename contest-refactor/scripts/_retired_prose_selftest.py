#!/usr/bin/env python3
"""Self-test: prose deliberately deleted from the skill's own files must not creep back in.

Each entry below names a rule or prose block that was retired on purpose, with the commit
that removed it. Nothing in this repo prevents a future edit from reintroducing the same
text — by a revert, a merge, or a well-meaning contributor re-deriving the old rule from
first principles — so this is the standing regression test for that class of drift.

Inventory (contest-refactor/, checked against the full commit history):

- 1abea0c deleted the Check 3 "sub-severity note" rule from implementation-reviewer.md.
  It told the reviewer to record a below-severity regression in `regressions[]` without
  rejecting for it, but an `approved` verdict must carry an empty `regressions[]` (the
  JSON contract in the same prompt, and output-format-json.md rule), so the instruction
  described an unrepresentable output shape. Confirmed absent from the current tree.

Considered and excluded (deletions that don't fit "retired prose that must not return"):

- 9919880 ("delete dormant fixture files contract") removed a code block from
  scripts/validate-fixtures.py, not prose from SKILL.md/references/. Out of scope for
  this check, and that file is owned by another workstream.
- aabfde3 ("remove duplicate format helper...") deleted Swift fixture source under
  evals/, not skill prose.
- 14470d8 ("kill the Meta-Rule-4 token-gate false-pass") replaced free-text evidence
  recording with a structured field, but the SKILL.md diff is a rewrite/expansion, not a
  clean deletion — the underlying concept (a reasoning-only exception) survives in the
  new text, so there is no "must never return" substring to pin.

Run: python3 scripts/_retired_prose_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

# Sentinel for an entry retired repo-wide rather than from one named file: check every
# SKILL.md + references/*.md file instead of an explicit path list.
REPO_WIDE = "__repo_wide__"

# (target files relative to SKILL_ROOT, or REPO_WIDE; forbidden substring; reason; source commit)
ENTRIES: list[tuple[tuple[str, ...] | str, str, str, str]] = [
    (
        ("references/implementation-reviewer.md",),
        "A regression at lower severity is acceptable",
        "Check 3's sub-severity note rule was unrepresentable -- an approved verdict "
        "cannot carry a non-empty regressions[]",
        "1abea0c",
    ),
]


def _repo_wide_files() -> list[Path]:
    return [SKILL_ROOT / "SKILL.md", *sorted((SKILL_ROOT / "references").glob("*.md"))]


def main() -> int:
    failures: list[str] = []

    for target, substring, reason, sha in ENTRIES:
        paths = _repo_wide_files() if target == REPO_WIDE else [SKILL_ROOT / rel for rel in target]

        for path in paths:
            if not path.exists():
                failures.append(
                    f"{sha}: target file missing at {path.relative_to(SKILL_ROOT)} -- a rename "
                    f"would silently blind this check; update the entry's path [{reason}]"
                )
                continue
            text = path.read_text(encoding="utf-8")
            if substring in text:
                failures.append(
                    f"{sha}: retired prose reappeared in {path.relative_to(SKILL_ROOT)}: "
                    f"{substring!r} -- {reason}"
                )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: {len(ENTRIES)} retired-prose entries stay retired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
