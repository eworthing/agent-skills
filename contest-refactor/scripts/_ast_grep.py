#!/usr/bin/env python3
"""_ast_grep.py — shared ast-grep subprocess invocation helper.

Extracted from audit_hotspots.py (OCR-GAP-REMEDIATION-PLAN-2026-09-03, W1a) so
audit_hotspots.py and the new invariant-queue wiring share one launcher instead
of two copies drifting apart. audit_boundaries.py and repo_map.py keep their
own independent copies deliberately -- not touched here.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

#: (reason, path) for genuine ast-grep failures, drained to a bounded stderr
#: diagnostic at the end of a run. Not part of the persisted JSON document.
_AST_GREP_FAILURES: list[tuple[str, str]] = []


def _ast_grep_matches(
    ast_grep_bin: str, path: Path, lang: str, selector: str
) -> tuple[list[dict], bool]:
    # ast-grep exits 1 (not 0) with valid JSON "[]" when a file has no matches for
    # the given kind — that is a successful scan, not a failure. Only a launch
    # error, timeout, or stdout that isn't decodable JSON is a genuine failure.
    cmd = [
        ast_grep_bin,
        "run",
        "--lang",
        lang,
        "--kind",
        selector,
        "--json=compact",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        _AST_GREP_FAILURES.append(("timeout", str(path)))
        return [], False
    except OSError:
        _AST_GREP_FAILURES.append(("launch-error", str(path)))
        return [], False
    stdout = proc.stdout.strip()
    if not stdout:
        if proc.returncode == 0:
            return [], True
        _AST_GREP_FAILURES.append(("undecodable-output", str(path)))
        return [], False
    try:
        matches = json.loads(stdout)
    except json.JSONDecodeError:
        _AST_GREP_FAILURES.append(("undecodable-output", str(path)))
        return [], False
    if not isinstance(matches, list):
        _AST_GREP_FAILURES.append(("undecodable-output", str(path)))
        return [], False
    return matches, True
