"""Pytest config — adds scripts/ to sys.path so `from quorum.parsing import …` resolves."""

import os
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def parse_failures_log(tmp_path, monkeypatch):
    """Redirect QUORUM_PARSE_FAILURES_LOG to a fresh per-test file.

    Prevents cross-test contamination of the parse-failures log, so each
    test asserts ONLY on the rows its own parser calls produced. Returns
    the path the parser will write to.
    """
    log_path = tmp_path / "parse-failures.jsonl"
    monkeypatch.setenv("QUORUM_PARSE_FAILURES_LOG", str(log_path))
    return log_path


def _read_failures(path):
    """Load JSONL parse-failures rows. Returns [] if the file doesn't exist."""
    import json
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


@pytest.fixture
def read_failures():
    """Helper to read JSONL rows from a parse-failures log path."""
    return _read_failures
