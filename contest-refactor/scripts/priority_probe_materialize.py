#!/usr/bin/env python3
"""Materialize a Tier-1P prioritization-probe run and print its dispatch block.

Copies ONLY `codebase/` and `seed/` into a throwaway directory — `expected.toml`
stays behind. That separation is the point: the spec names the target, the decoy,
the restraint control and the blocked item, and a probe that can read it is
measuring nothing. Same blind-dispatch discipline the loop-replay measurement
session had to learn the hard way (a materializer that printed the planted smell
to stdout had to be redirected away from the prompt).

Runs no model. Prints the dest path, the resolved dispatch prompt, and the grade
command.

Usage:
  priority_probe_materialize.py <fixture-id> [dest-dir]

Exit codes: 0 = materialized; 2 = usage / missing inputs / dest exists.
"""

from __future__ import annotations

import shutil
import sys
import tomllib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = SKILL_ROOT / "evals" / "priority-fixtures"
PROMPT = SKILL_ROOT / "evals" / "priority_probe_prompt.md"


def _die(msg: str) -> int:
    print(f"priority_probe_materialize: {msg}", file=sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    if len(argv) < 2:
        return _die("usage: priority_probe_materialize.py <fixture-id> [dest-dir]")
    fixture_id = argv[1]
    src = FIXTURES / fixture_id
    if not src.is_dir():
        return _die(f"no such fixture: {src}")
    spec_path = src / "expected.toml"
    if not spec_path.is_file():
        return _die(f"fixture has no expected.toml: {spec_path}")
    if not PROMPT.is_file():
        return _die(f"missing dispatch template: {PROMPT}")

    spec = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    dest = Path(argv[2]).resolve() if len(argv) > 2 else Path.cwd() / f"probe-{fixture_id}"
    if dest.exists():
        return _die(f"dest already exists, refusing to overwrite: {dest}")

    shutil.copytree(src / "codebase", dest / "repo")
    shutil.copytree(src / "seed", dest / "seed")

    template = PROMPT.read_text(encoding="utf-8")
    # Drop the authoring comment — it documents the placeholder set and the blind
    # dispatch rule, and must not reach the probe.
    if template.lstrip().startswith("<!--"):
        end = template.index("-->") + 3
        template = template[end:].lstrip("\n")

    rendered = (
        template.replace("{{REPO}}", str(dest / "repo"))
        .replace("{{SKILL_DIR}}", str(SKILL_ROOT))
        .replace("{{HISTORY}}", str(dest / "seed" / "REVIEW_HISTORY.json"))
        .replace("{{LENS}}", str(spec.get("lens", "lens-generic.md")))
        .replace("{{TEST_COMMAND}}", str(spec.get("test_command", "")))
    )
    (dest / "PROMPT.md").write_text(rendered, encoding="utf-8")

    print(f"materialized: {dest}")
    print(f"prompt:       {dest / 'PROMPT.md'}")
    print()
    print("--- DISPATCH (send verbatim; save the JSON reply to <dest>/findings.json) ---")
    print(rendered)
    print("--- GRADE ---")
    print(
        f"python3 scripts/loop_replay_grade.py {fixture_id} "
        f"{dest / 'findings.json'} --priority-only"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
