#!/usr/bin/env python3
"""Self-test: no NEW gate may retroactively invalidate already-committed artifacts.

Backlog item 30 (found 2026-08-19). A required field or record introduced at an
*existing* `schema_version` makes every artifact already written at that version
fail rules that did not exist when it was emitted. `schema_version` cannot
separate "v4 before the field existed" from "v4 after", and `skill_rev` (G19),
the field that exists to record which ruleset produced an artifact, is null on
the only real artifact we have.

references/output-format-migrations.md states the three legal ways to add a
required field (bump + default-fill, scope by `skill_rev`, or
optional-with-shape-gating) and records G43 + G46 as the outstanding violation.

This test is the tripwire that keeps that list honest. It runs the shipped
validator against the repo's own committed dogfood artifact and asserts the set
of gates that fail is a SUBSET of the documented violations. Adding a fourth
required field at an existing version grows that set, and this fails naming the
new gate -- so the violation cannot be introduced silently.

It deliberately asserts a subset, not equality: FIXING G43 or G46 (the point of
item 30) must not fail this test. Only a NEW violation does.

Skips cleanly when the dogfood artifact is absent -- it is a real committed
review, not a fixture, and not every checkout will carry one.

Run: python3 scripts/_schema_compat_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_ROOT.parent
MIGRATIONS = SKILL_ROOT / "references" / "output-format-migrations.md"

# Gates recorded in output-format-migrations.md as the known outstanding violation.
DOCUMENTED_VIOLATIONS = {"G43", "G46"}


def main() -> int:
    failures: list[str] = []

    text = MIGRATIONS.read_text(encoding="utf-8")
    if "## Adding a required field" not in text:
        failures.append(
            "output-format-migrations.md lost its 'Adding a required field' policy section -- "
            "the rule that a required field at an existing schema_version retroactively "
            "invalidates committed history, and the three legal alternatives"
        )
    for option in ("Bump the schema version", "Scope the gate", "Make the field optional"):
        if option not in text:
            failures.append(f"migrations policy no longer names the legal option {option!r}")

    # Option 3 must keep pointing at the shipped precedent rather than describing it in
    # the abstract. G19 is deliberately type-only and its docstring carries this exact
    # reasoning -- an implementer who is shown the working example copies it; one who is
    # given a principle re-derives it, which is how G43/G46 went wrong in the first place.
    # Pin the file:line pointer, not the bare gate id -- "G19" also appears in option 2
    # ("scope by skill_rev (G19)"), so a bare-id check would pass with option 3's citation
    # deleted. Verified by mutation: the bare-id version did not trip.
    if "_artifact_history.py:307" not in text:
        failures.append(
            "migrations policy no longer cites G19 as the shipped precedent for "
            "optional-with-shape-gating (_artifact_history.py:307) -- the concrete example "
            "is the part an implementer copies"
        )

    artifact = REPO_ROOT / "CURRENT_REVIEW.json"
    if not artifact.is_file():
        if failures:
            for f in failures:
                print(f"FAIL: {f}")
            return 1
        print("OK: migrations policy intact (dogfood artifact absent; retroactive check skipped)")
        return 0

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "issues.json"
        subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "validate-artifact.py"),
                str(REPO_ROOT),
                "--mode",
                "advisory",
                "--quiet",
                "--json",
                str(out),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {"issues": []}

    failing: set[str] = set()
    for issue in payload.get("issues", []):
        for gate in re.findall(r"\bG\d+\b", f"{issue.get('rule', '')} {issue.get('message', '')}"):
            failing.add(gate)

    new = failing - DOCUMENTED_VIOLATIONS
    if new:
        failures.append(
            f"gate(s) {sorted(new)} now fail the committed dogfood artifact "
            f"({artifact.name}, written before they existed) and are NOT recorded as a known "
            f"retroactive violation. A required field was added at an existing schema_version. "
            f"Fix per references/output-format-migrations.md § Adding a required field, or record "
            f"it there and in DOCUMENTED_VIOLATIONS with the reason"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    fixed = DOCUMENTED_VIOLATIONS - failing
    note = f" ({sorted(fixed)} now fixed)" if fixed else ""
    print(f"OK: no undocumented retroactive gate invalidation; policy section intact{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
