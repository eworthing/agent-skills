#!/usr/bin/env python3
"""Self-test: provider-adapters.md model IDs are current (no known-stale strings).

There is no pytest harness in this repo (pyproject configures only ruff), so this
standalone check guards the model catalog in references/provider-adapters.md against
drift. Model IDs are mutable facts, so this is the "dated source" record for T1.1:
the STALE / REQUIRED sets below were verified on 2026-06-24 against the session model
catalog (Claude Code: claude-opus-4-8 current top Opus, claude-fable-5 the Fable 5
tier above Opus) and the Codex CLI model list (gpt-5.5 current flagship).

Per-provider DEFAULTS are deliberately NOT bumped (sonnet-4-6 / gpt-5.4-mini /
deepseek-v4-flash stay the tuned defaults); only the "When to upgrade the model"
examples move, plus the new fable top tier. DEFAULTS_PRESENT guards against an
accidental default change.

Run: python3 scripts/_model_catalog_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Verified 2026-06-24. Strings that must NOT appear (superseded upgrade targets).
STALE = ("claude-opus-4-7",)
# Strings that MUST appear after the refresh (current upgrade targets + fable tier).
REQUIRED = ("claude-opus-4-8", "gpt-5.5", "claude-fable-5")
# Tuned per-provider defaults that must stay put (no accidental default bump).
DEFAULTS_PRESENT = ("claude-sonnet-4-6", "gpt-5.4-mini", "deepseek-v4-flash")


def main() -> int:
    doc = Path(__file__).resolve().parent.parent / "references" / "provider-adapters.md"
    text = doc.read_text(encoding="utf-8")
    failures: list[str] = []

    for s in STALE:
        if s in text:
            failures.append(f"stale model id still present: {s!r}")
    for s in REQUIRED:
        if s not in text:
            failures.append(f"required model id missing: {s!r}")
    for s in DEFAULTS_PRESENT:
        if s not in text:
            failures.append(f"tuned default unexpectedly removed: {s!r}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: model catalog current — {len(REQUIRED)} refreshed ids present, "
        f"{len(STALE)} stale id(s) absent, defaults intact"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
