#!/usr/bin/env python3
"""Self-test: the credential-redaction rule must be forwarded verbatim into every
dispatch prompt that independently reads raw payload (source/diffs) and writes
free-text evidence into a persisted artifact.

Backlog item 1 (security class): a finding whose evidence quotes a hardcoded
credential writes the value into CURRENT_REVIEW.md -> CURRENT_REVIEW.json ->
REVIEW_HISTORY archive -- committed. Layer 1 (this test) is the preventive prose
rule; Layer 2 (G44, scripts/_g44_selftest.py) is the mechanical quarantine gate
that catches a rule violation after the fact.

Canonical home: method.md's "Reading discipline" list (§ Method, 10 steps), right
next to "Cite as you read" -- the exact instruction whose literal text ("record
file:line plus the quoted span") is what creates the risk. The loop subagent
reads method.md whole and mandatory at Step 1 (SKILL.md's Reference Load Matrix),
so that boundary needs no forwarded copy -- unlike G14's validation.md home,
which Step 1 does NOT read until emit time.

Two further dispatch sites read raw payload (diffs, source) independently and
write their own free-text verdict fields (`reason`, `regressions[]`,
`attempts[].what_tried/why_failed`) that get appended into CURRENT_REVIEW.md /
CURRENT_REVIEW.json, and do NOT reliably load method.md's Evidence Chain section
(implementation-reviewer.md's read-first list scopes method.md to "Simplify
Pressure Test" only; halt-verifier.md never instructs loading method.md at all)
-- the same "fragile chain" failure mode G14 fixed. Fixed sites:

  1. Implementation reviewer (implementation-reviewer.md) -- whole job is reading
     `git diff HEAD` (raw payload); reject reason + regressions[] persist into
     CURRENT_REVIEW.md's "## Loop N Implementation Review" section.
  2. HALT_SUCCESS challenger (halt-verifier.md) -- reads source independently
     while trying to break the verdict; its `attempts[]`/`reason` persist into
     CURRENT_REVIEW.json's halt_success_challenge object (G32).

This test pins the canonical rule text as a constant and asserts it appears
byte-identical at all three sites (method.md, and both forwarded copies). A copy
drifting out of sync with the canonical text is exactly the failure mode this
guards against.

Run: python3 scripts/_redaction_dispatch_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

# Verbatim canonical text (method.md § Reading discipline, "Credential redaction"
# bullet -- minus the bold lead-in, which is method.md-only list formatting, not
# part of the reusable rule). Every dispatch site below must carry this exact
# string.
REDACTION_RULE = (
    "When evidence cites a hardcoded credential (API key, token, password, "
    "private key), record `file:line` plus the credential's TYPE only — never "
    "the value. The value itself must never appear in anything you write. "
    "Recommend rotation, not display, as the remedy."
)

METHOD = SKILL_ROOT / "references" / "method.md"
IMPLEMENTATION_REVIEWER = SKILL_ROOT / "references" / "implementation-reviewer.md"
HALT_VERIFIER = SKILL_ROOT / "references" / "halt-verifier.md"


def main() -> int:
    failures: list[str] = []

    if REDACTION_RULE not in METHOD.read_text(encoding="utf-8"):
        failures.append(
            "method.md: credential-redaction rule text missing from the Reading "
            "discipline list -- this is the canonical home, adjacent to 'Cite as "
            "you read'"
        )

    if REDACTION_RULE not in IMPLEMENTATION_REVIEWER.read_text(encoding="utf-8"):
        failures.append(
            "implementation-reviewer.md: credential-redaction rule text missing "
            "from the reviewer prompt template -- the reviewer's whole job is "
            "reading git diff HEAD (raw payload) and its reject reason persists "
            "into CURRENT_REVIEW.md; the copy must stay in sync with method.md's "
            "canonical text"
        )

    if REDACTION_RULE not in HALT_VERIFIER.read_text(encoding="utf-8"):
        failures.append(
            "halt-verifier.md: credential-redaction rule text missing from the "
            "challenger prompt source -- the challenger reads source "
            "independently and its attempts[]/reason persist into "
            "CURRENT_REVIEW.json's halt_success_challenge object; the copy must "
            "stay in sync with method.md's canonical text"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: credential-redaction rule present verbatim at all 3 dispatch sites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
