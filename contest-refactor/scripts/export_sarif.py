#!/usr/bin/env python3
"""Export the findings that SURVIVE a contest-refactor run as a SARIF 2.1.0 log.

A refactor loop fixes most of what it finds, but some findings outlive it: an entry
retired as `unresolvable` (Step 1.6), and — when a scorecard is supplied — a
dimension that reached 9.5 on an *accepted* residual carve-out. Those are the durable,
triage-worthy items an IDE or CI surface cares about. Same-run-fixed findings
(`resolved` / `fixed_by_user`) are not durable and are deliberately omitted.

This is a read-only export. It never mutates the registry and has no effect on loop
behaviour, scoring, or gating; it just reshapes already-decided records into the
SARIF interchange format. Stdlib-only, Python 3.11+.

Usage:
    export_sarif.py <findings_registry.json> [--review CURRENT_REVIEW.json] [-o OUT.sarif]

    <findings_registry.json>   registry whose terminally-`unresolvable` entries are exported
    --review CURRENT_REVIEW    also export `accepted` scorecard residuals as note-level results
    -o / --output              write here instead of stdout

Exit codes: 0 = wrote a (possibly empty-results) SARIF log; 2 = usage / unreadable input.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
TOOL_NAME = "contest-refactor"
TOOL_URI = "https://github.com/eworthing/agent-skills/tree/main/contest-refactor"

# Canonical severity anchors (canon/severity-anchors.toml) -> SARIF result levels.
# SARIF levels: "none" | "note" | "warning" | "error".
_SEVERITY_TO_LEVEL = {
    "Likely disqualifier": "error",
    "Serious deduction": "error",
    "Noticeable weakness": "warning",
    "Cosmetic for contest": "note",
}
_DEFAULT_LEVEL = "warning"  # unknown/missing severity errs toward visible, not silent


def _die(msg: str) -> int:
    print(f"export_sarif: {msg}", file=sys.stderr)
    return 2


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _terminal_occurrence(entry: dict) -> dict | None:
    """The occurrence at the highest loop number — the entry's current state."""
    occs = entry.get("occurrences") or []
    if not occs:
        return None
    return max(occs, key=lambda o: o.get("loop", -1))


def _result_for_entry(entry: dict) -> dict:
    """Map one terminally-unresolvable registry entry to a SARIF result."""
    stable_id = entry.get("stable_id", "UNKNOWN")
    severity = entry.get("severity", "")
    level = _SEVERITY_TO_LEVEL.get(severity, _DEFAULT_LEVEL)

    terminal = _terminal_occurrence(entry) or {}
    rationale = (terminal.get("retirement") or {}).get("rationale", "")
    text = entry.get("title", stable_id)
    if rationale:
        text = f"{text} — {rationale}"

    result: dict = {
        "ruleId": stable_id,
        "level": level,
        "message": {"text": text},
    }

    primary_file = entry.get("primary_file")
    if primary_file:
        lines = entry.get("primary_evidence_lines") or []
        region: dict = {}
        if len(lines) >= 1 and isinstance(lines[0], int):
            region["startLine"] = lines[0]
        if len(lines) >= 2 and isinstance(lines[1], int):
            region["endLine"] = lines[1]
        physical: dict = {"artifactLocation": {"uri": primary_file}}
        if region:
            physical["region"] = region
        result["locations"] = [{"physicalLocation": physical}]

    return result


def _rule_for_entry(entry: dict) -> dict:
    return {
        "id": entry.get("stable_id", "UNKNOWN"),
        "name": entry.get("stable_id", "UNKNOWN"),
        "shortDescription": {"text": entry.get("title", "")},
        "defaultConfiguration": {
            "level": _SEVERITY_TO_LEVEL.get(entry.get("severity", ""), _DEFAULT_LEVEL)
        },
    }


def _residual_result(dim: str, cell: dict) -> dict:
    blocker = cell.get("residual_blocking_10") or "accepted residual"
    rationale = cell.get("residual_rationale_or_backlog_ref") or ""
    text = f"Accepted residual on `{dim}`: {blocker}"
    if rationale:
        text = f"{text} — {rationale}"
    return {
        "ruleId": f"residual/{dim}",
        "level": "note",  # accepted carve-out, not a defect to fix
        "message": {"text": text},
    }


def build_sarif(registry: dict, review: dict | None) -> dict:
    rules: list[dict] = []
    results: list[dict] = []

    for entry in registry.get("entries", []):
        terminal = _terminal_occurrence(entry)
        if not terminal or terminal.get("status") != "unresolvable":
            continue
        rules.append(_rule_for_entry(entry))
        results.append(_result_for_entry(entry))

    if review is not None:
        scorecard = review.get("scorecard") or {}
        for dim, cell in scorecard.items():
            if isinstance(cell, dict) and cell.get("residual_disposition") == "accepted":
                rule_id = f"residual/{dim}"
                rules.append(
                    {"id": rule_id, "name": rule_id,
                     "shortDescription": {"text": f"Accepted residual on {dim}"},
                     "defaultConfiguration": {"level": "note"}}
                )
                results.append(_residual_result(dim, cell))

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "informationUri": TOOL_URI,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export surviving contest-refactor findings as SARIF 2.1.0."
    )
    parser.add_argument("registry", help="path to findings_registry.json")
    parser.add_argument("--review", help="path to CURRENT_REVIEW.json (adds accepted residuals)")
    parser.add_argument("-o", "--output", help="write SARIF here instead of stdout")
    args = parser.parse_args(argv)

    registry_path = Path(args.registry)
    if not registry_path.is_file():
        return _die(f"registry not found: {registry_path}")
    try:
        registry = _load_json(registry_path)
    except (json.JSONDecodeError, OSError) as exc:
        return _die(f"cannot read registry {registry_path}: {exc}")

    review: dict | None = None
    if args.review:
        review_path = Path(args.review)
        if not review_path.is_file():
            return _die(f"review not found: {review_path}")
        try:
            review = _load_json(review_path)
        except (json.JSONDecodeError, OSError) as exc:
            return _die(f"cannot read review {review_path}: {exc}")

    sarif = build_sarif(registry, review)
    text = json.dumps(sarif, indent=2) + "\n"

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
