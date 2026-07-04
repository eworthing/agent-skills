"""Tests for common.log.events."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from common.log import EventLogger


class TestNoopWhenNoPath:
    def test_logger_with_none_path_does_not_create_file(self, tmp_path):
        log = EventLogger(log_path=None, review_id="r1")
        log.log("started", provider="claude")
        # No file because log_path was None.
        assert list(tmp_path.iterdir()) == []


class TestAppendOnly:
    def test_writes_jsonl_entry(self, tmp_path):
        p = tmp_path / "events.jsonl"
        log = EventLogger(log_path=str(p), review_id="r-42")
        log.log("started", provider="claude", round_num=1)
        log.log("done", provider="claude", round_num=1)
        lines = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 2
        for entry in lines:
            assert entry["review_id"] == "r-42"
            assert entry["provider"] == "claude"
            assert entry["round"] == 1
            # ISO-8601 timestamp is parseable.
            datetime.fromisoformat(entry["ts"])
        assert lines[0]["event"] == "started"
        assert lines[1]["event"] == "done"

    def test_logging_failure_is_swallowed(self, tmp_path):
        # log_path is a directory, not a file — open('a') will fail.
        # The logger must not propagate the OSError.
        log = EventLogger(log_path=str(tmp_path), review_id="r")
        log.log("anything")  # must not raise


class TestOptionalFields:
    def test_minimal_entry(self, tmp_path):
        p = tmp_path / "events.jsonl"
        log = EventLogger(log_path=str(p), review_id="r")
        log.log("event_only")
        line = p.read_text(encoding="utf-8").strip()
        entry = json.loads(line)
        assert entry["event"] == "event_only"
        # Optional fields must NOT appear when their kwarg is None.
        assert "provider" not in entry
        assert "round" not in entry
        assert "error" not in entry
        assert "ctx" not in entry

    def test_error_coerces_to_string(self, tmp_path):
        p = tmp_path / "events.jsonl"
        log = EventLogger(log_path=str(p), review_id="r")
        log.log("failed", error=ValueError("boom"))
        entry = json.loads(p.read_text(encoding="utf-8").strip())
        assert entry["error"] == "boom"
