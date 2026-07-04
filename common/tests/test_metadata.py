"""Tests for common.metadata.extractors."""

import json
import subprocess
from unittest import mock

import pytest
from common.metadata import (
    compute_plan_metadata,
    extract_metadata,
    extract_session_id_agy,
    extract_session_id_copilot,
    extract_session_id_json,
    extract_session_id_opencode,
)
from common.metadata.extractors import _extract_opencode_metadata_via_export


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
            "not json\n" + json.dumps({"type": "result", "sessionId": "cop-9"}) + "\n",
            encoding="utf-8",
        )
        assert extract_session_id_copilot(str(p)) == "cop-9"


class TestSessionIdOpencode:
    def test_first_line_sessionid(self, tmp_path):
        p = tmp_path / "events.jsonl"
        p.write_text(
            json.dumps({"sessionID": "oc-1", "other": True}) + "\nignored\n",
            encoding="utf-8",
        )
        assert extract_session_id_opencode(str(p)) == "oc-1"


class TestSessionIdAgy:
    def test_extracts_print_mode_conversation(self, tmp_path):
        log = tmp_path / "agy.log"
        log.write_text(
            "I0614 10:58:18 printmode.go:85] Print mode: starting\n"
            "I0614 10:58:19 printmode.go:155] Print mode: conversation="
            "0a6d2ba7-222f-469a-b49d-2c7d8f10fbff, sending message\n",
            encoding="utf-8",
        )
        assert extract_session_id_agy(str(log)) == "0a6d2ba7-222f-469a-b49d-2c7d8f10fbff"

    def test_extracts_created_conversation(self, tmp_path):
        log = tmp_path / "agy.log"
        log.write_text(
            "I0614 server.go:753] Created conversation f014e69c-55a3-40a1-a89e-1df03b6ba6e9\n",
            encoding="utf-8",
        )
        assert extract_session_id_agy(str(log)) == "f014e69c-55a3-40a1-a89e-1df03b6ba6e9"

    def test_no_conversation_returns_none(self, tmp_path):
        log = tmp_path / "agy.log"
        log.write_text("just some unrelated log noise\n", encoding="utf-8")
        assert extract_session_id_agy(str(log)) is None

    def test_missing_file_returns_none(self, tmp_path):
        assert extract_session_id_agy(str(tmp_path / "nope.log")) is None


class TestExtractMetadata:
    def test_claude_model(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text(json.dumps({"model": "claude-opus-4-7", "result": "ok"}), encoding="utf-8")
        meta = extract_metadata(str(p), events_file=None, reviewer="claude")
        assert meta["model"] == "claude-opus-4-7"

    def test_gemini_stats_models(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text(
            json.dumps(
                {
                    "stats": {
                        "models": {
                            "gemini-3-pro-preview": {
                                "tokens": {"thoughts": 4096},
                            }
                        }
                    }
                }
            ),
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
            json.dumps(
                {
                    "type": "turn_context",
                    "payload": {"model": "gpt-5.4", "effort": "high"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        meta = extract_metadata(output_file=None, events_file=str(p), reviewer="codex")
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


class TestOpencodeMetadataExport:
    """`opencode export` reshaped model fields across versions: the nested
    info.model dict survives on the user message, while assistant messages
    flatten providerID/modelID/variant onto info. Detection must handle both."""

    def _run(self, payload):
        return subprocess.CompletedProcess(
            ["opencode", "export", "ses_1"],
            0,
            stdout=json.dumps(payload),
            stderr="",
        )

    def test_nested_shape(self):
        payload = {
            "messages": [
                {
                    "info": {
                        "model": {
                            "providerID": "opencode-go",
                            "modelID": "deepseek-v4-pro",
                            "variant": "max",
                        }
                    }
                },
            ]
        }
        with mock.patch.object(subprocess, "run", return_value=self._run(payload)):
            meta = _extract_opencode_metadata_via_export("ses_1")
        assert meta == {"model": "opencode-go/deepseek-v4-pro", "effort": "xhigh"}

    def test_flattened_shape(self):
        # info.model is empty/absent; fields hoisted onto info (v1.17+ assistant).
        payload = {
            "messages": [
                {
                    "info": {
                        "role": "assistant",
                        "model": {},
                        "providerID": "opencode-go",
                        "modelID": "deepseek-v4-flash",
                        "variant": "high",
                    }
                },
            ]
        }
        with mock.patch.object(subprocess, "run", return_value=self._run(payload)):
            meta = _extract_opencode_metadata_via_export("ses_1")
        assert meta == {"model": "opencode-go/deepseek-v4-flash", "effort": "high"}

    def test_real_mixed_export_uses_first_resolvable_message(self):
        # Mirrors a real v1.17.11 export: nested user message first, then
        # flattened assistant messages. The user message resolves first.
        payload = {
            "messages": [
                {
                    "info": {
                        "role": "user",
                        "model": {
                            "providerID": "opencode-go",
                            "modelID": "deepseek-v4-flash",
                            "variant": "high",
                        },
                    }
                },
                {
                    "info": {
                        "role": "assistant",
                        "model": {},
                        "providerID": "opencode-go",
                        "modelID": "deepseek-v4-flash",
                        "variant": "high",
                    }
                },
            ]
        }
        with mock.patch.object(subprocess, "run", return_value=self._run(payload)):
            meta = _extract_opencode_metadata_via_export("ses_1")
        assert meta == {"model": "opencode-go/deepseek-v4-flash", "effort": "high"}

    def test_model_without_variant_omits_effort(self):
        payload = {
            "messages": [
                {"info": {"providerID": "opencode-go", "modelID": "qwen3.6-plus"}},
            ]
        }
        with mock.patch.object(subprocess, "run", return_value=self._run(payload)):
            meta = _extract_opencode_metadata_via_export("ses_1")
        assert meta == {"model": "opencode-go/qwen3.6-plus"}
