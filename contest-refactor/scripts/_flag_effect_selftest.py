#!/usr/bin/env python3
"""Self-test: every CLI flag advertised in SKILL.md's `argument-hint` must have its
effect DEFINED somewhere, not merely parsed and recommended.

Backlog item 24 audit (2026-08-19): `--scope <dir>` was advertised in the
argument-hint, listed in startup.md's "Parse user flags" sentence, and actively
recommended to users by halt-handoff.md:136 ("Scope down -- re-invoke as
/contest-refactor --scope <dir>") -- while NO step ever read it. Step 0 step 2
scanned CWD unconditionally, `source_roots` was never narrowed, and nothing
recorded the narrowing. Its only downstream consumer, scripts/preflight.py, takes
`<scope-dir>` as its first positional and names "a scope dir that isn't there" as
the canonical bad input -- so the consumer expected the flag while the producer
ignored it. A user following the skill's own handoff advice got a whole-repo run
and a whole-repo scorecard.

Every other advertised flag had its effect defined at 3-40 sites. `--scope` had
zero. This test is the tripwire that makes that state impossible to re-enter.

Why this shape rather than a fixed list of files: the flag set is DISCOVERED from
SKILL.md's argument-hint, so newly advertising a flag without registering where it
acts fails here. That is the "discovery tripwire, not a longer list" closure
recommended in analysis/contest-refactor/ITEM3-HARD-RULE-PROPAGATION-2026-08-19.md
for the enumerate-only dispatch audits -- applied here first because the flag list
has a machine-readable source and the dispatch-prompt set does not.

Two sites are excluded from counting as an effect definition, because neither says
what the flag DOES:
  - SKILL.md's `argument-hint:` line       -- the advertisement
  - startup.md's "Parse user flags" bullet -- the parse list ("Record for later
    steps" is not an effect; something must later READ it)

Run: python3 scripts/_flag_effect_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

# flag -> the file(s) that define what it DOES. A flag may act in several places;
# register the ones that carry the operative instruction, not every mention.
EFFECT_SITES: dict[str, tuple[str, ...]] = {
    "--cap": ("SKILL.md",),
    "--confirm": ("SKILL.md", "references/startup.md"),
    "--dry-run": ("SKILL.md",),
    "--incidents": ("references/output-format-state-schemas.md",),
    "--purge": ("SKILL.md", "references/startup.md"),
    "--reset": ("SKILL.md", "references/startup.md"),
    "--scope": ("references/startup.md",),
    "--strictness": ("references/architecture-rubric-scoring.md",),
    "--test-filter": ("references/startup.md",),
}


def _advertised_flags(skill_md: list[str]) -> tuple[list[str], int]:
    """Flags from SKILL.md's argument-hint, plus that line's 0-based index."""
    idx = next(i for i, line in enumerate(skill_md) if line.startswith("argument-hint:"))
    return sorted(set(re.findall(r"--[a-z][a-z-]*", skill_md[idx]))), idx


def _parse_list_index(startup: list[str]) -> int:
    return next(
        i for i, line in enumerate(startup) if line.lstrip().startswith("1. **Parse user flags**")
    )


def main() -> int:
    failures: list[str] = []
    skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
    startup = (SKILL_ROOT / "references" / "startup.md").read_text(encoding="utf-8").splitlines()
    flags, hint_idx = _advertised_flags(skill_md)
    parse_idx = _parse_list_index(startup)

    for flag in flags:
        pattern = re.compile(re.escape(flag) + r"(?![a-z-])")
        sites = EFFECT_SITES.get(flag)
        if not sites:
            failures.append(
                f"{flag} is advertised in SKILL.md's argument-hint but has no EFFECT_SITES entry -- "
                f"register the file that defines what it does, or stop advertising it. A flag that "
                f"is parsed and never read is the --scope defect this test exists to prevent"
            )
            continue
        for site in sites:
            path = SKILL_ROOT / site
            if not path.is_file():
                failures.append(f"{flag}: registered effect site {site} does not exist")
                continue
            hit = False
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
                if not pattern.search(line):
                    continue
                if site == "SKILL.md" and i == hint_idx:
                    continue  # the advertisement, not an effect
                if site == "references/startup.md" and i == parse_idx:
                    continue  # the parse list, not an effect
                hit = True
                break
            if not hit:
                failures.append(
                    f"{flag}: registered effect site {site} no longer describes it outside the "
                    f"advertisement/parse list -- the operative instruction was deleted or moved"
                )

    for flag in EFFECT_SITES:
        if flag not in flags:
            failures.append(
                f"{flag} has an EFFECT_SITES entry but is no longer advertised in the "
                f"argument-hint -- drop the entry, or re-advertise the flag"
            )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: all {len(flags)} advertised flags have a defined effect at a registered site")
    return 0


if __name__ == "__main__":
    sys.exit(main())
