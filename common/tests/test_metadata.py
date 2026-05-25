"""Tests for common.metadata.extractors."""

import json

import pytest

from common.metadata import (
    compute_plan_metadata,
    extract_metadata,
    extract_session_id_copilot,
    extract_session_id_json,
    extract_session_id_opencode,
)


class TestSessionIdJson:
    def test_present(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text(json.dumps({"session_id": "sess-1"}), encoding="utf-8")
        assert extract_session_id_json(str(p)) == "sess-1"

    def test_missing_field_returns_none(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text(json.dumps({"other": "x"}), encoding="utf-8")
        assert extract_session_id_json(str(p)) is None

    def test_missing_file_returns_none(self, tmp_path):
        assert extract_session_id_json(str(tmp_path / "nope.json")) is None

    def test_malformed_json_returns_none(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text("{not json", encoding="utf-8")
        assert extract_session_id_json(str(p)) is None


class TestSessionIdCopilot:
    def test_finds_result_event(self, tmp_path):
        p = tmp_path / "events.jsonl"
        lines = [
            json.dumps({"type": "assistant.message", "data": {"content": "..."}}),
            json.dumps({"type": "result", "sessionId": "cop-7"}),
        ]
        p.write_text("\n".join(lines), encoding="utf-8")
        assert extract_session_id_copilot(str(p)) == "cop-7"

    def test_no_result_event(self, tmp_path):
        p = tmp_path / "events.jsonl"
        p.write_text(json.dumps({"type": "assistant.message"}), encoding="utf-8")
        assert extract_session_id_copilot(str(p)) is None

    def test_skips_malformed_lines(self, tmp_path):
        p = tmp_path / "events.jsonl"
        p.write_text(
            "not json\n"
            + json.dumps({"type": "result", "sessionId": "cop-9"})
            + "\n",
            encoding="utf-8",
        )
        assert extract_session_id_copilot(str(p)) == "cop-9"


class TestSessionIdOpencode:
    def test_first_line_sessionid(self, tmp_path):
        p = tmp_path / "events.jsonl"
        p.write_text(
            json.dumps({"sessionID": "oc-1", "other": True}) + "\n"
            "ignored\n",
            encoding="utf-8",
        )
        assert extract_session_id_opencode(str(p)) == "oc-1"


class TestExtractMetadata:
    def test_claude_model(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text(json.dumps({"model": "claude-opus-4-7", "result": "ok"}), encoding="utf-8")
        meta = extract_metadata(str(p), events_file=None, reviewer="claude")
        assert meta["model"] == "claude-opus-4-7"

    def test_gemini_stats_models(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text(
            json.dumps({
                "stats": {
                    "models": {
                        "gemini-3-pro-preview": {
                            "tokens": {"thoughts": 4096},
                        }
                    }
                }
            }),
            encoding="utf-8",
        )
        meta = extract_metadata(str(p), events_file=None, reviewer="gemini")
        assert meta["model"] == "gemini-3-pro-preview"
        assert meta["thinking_tokens"] == 4096

    def test_copilot_jsonl_model(self, tmp_path):
        p = tmp_path / "out.jsonl"
        p.write_text(
            json.dumps({"type": "assistant.message", "data": {"model": "gpt-5.4"}}) + "\n",
            encoding="utf-8",
        )
        meta = extract_metadata(str(p), events_file=None, reviewer="copilot")
        assert meta["model"] == "gpt-5.4"

    def test_codex_turn_context(self, tmp_path):
        p = tmp_path / "events.jsonl"
        p.write_text(
            json.dumps({
                "type": "turn_context",
                "payload": {"model": "gpt-5.4", "effort": "high"},
            }) + "\n",
            encoding="utf-8",
        )
        meta = extract_metadata(
            output_file=None, events_file=str(p), reviewer="codex"
        )
        assert meta["model"] == "gpt-5.4"
        assert meta["effort"] == "high"

    def test_missing_file_returns_empty(self):
        assert extract_metadata("/nope", None, "claude") == {}


class TestComputePlanMetadata:
    def test_basic(self, tmp_path):
        p = tmp_path / "plan.md"
        p.write_text("# Hello\n", encoding="utf-8")
        meta = compute_plan_metadata(str(p))
        assert meta["plan_name"] == "plan.md"
        assert meta["plan_bytes"] == 8  # "# Hello\n" is 8 bytes
        assert len(meta["plan_sha256"]) == 64
        assert "T" in meta["plan_mtime"]  # ISO 8601 has T separator

    def test_missing_file(self):
        assert compute_plan_metadata("/nope") == {}

    def test_none(self):
        assert compute_plan_metadata(None) == {}
