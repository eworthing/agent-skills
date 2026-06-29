"""output extraction tests — relocated verbatim from test_run_review.py (mechanical split)."""
import argparse, json, os, shutil, signal, stat, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from unittest import mock  # noqa: F401
from ._helpers import *  # noqa: F401,F403
from ._helpers import _CREATE_NEW_PROCESS_GROUP  # noqa: F401


class TestOutputParsing(unittest.TestCase):
    """Tests 8-9: Output extraction from fixtures (direct import, no subprocess)."""

    def test_extract_text_claude(self):
        """Test 8a: Claude JSON fixture extracts review text correctly."""
        # Copy fixture to temp file (extraction rewrites the file)
        fixture = Path(FIXTURES_DIR) / "claude_output.json"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            with fixture.open() as f:
                tmp.write(f.read())
            tmp_path = tmp.name
        try:
            # Extract metadata first (must happen before text extraction)
            meta = extract_metadata(tmp_path, None, "claude")
            self.assertEqual(meta.get("model"), "test-claude-model")

            # Extract text (rewrites file)
            extract_text_from_output(tmp_path, "claude")
            with Path(tmp_path).open() as f:
                text = f.read()
            self.assertIn("VERDICT: REVISE", text)
            self.assertIn("error handling", text)
            # Should be plain text, not JSON
            self.assertNotIn('"result"', text)
        finally:
            Path(tmp_path).unlink()

    def test_extract_text_gemini(self):
        """Test 8b: Gemini JSON fixture extracts review text and metadata."""
        fixture = Path(FIXTURES_DIR) / "gemini_output.json"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            with fixture.open() as f:
                tmp.write(f.read())
            tmp_path = tmp.name
        try:
            meta = extract_metadata(tmp_path, None, "gemini")
            self.assertEqual(meta.get("model"), "test-gemini-model")
            self.assertEqual(meta.get("thinking_tokens"), 4096)

            extract_text_from_output(tmp_path, "gemini")
            with Path(tmp_path).open() as f:
                text = f.read()
            self.assertIn("VERDICT: APPROVED", text)
        finally:
            Path(tmp_path).unlink()

    def test_extract_text_copilot(self):
        """Test 8c: Copilot JSONL fixture extracts review text and metadata."""
        fixture = Path(FIXTURES_DIR) / "copilot_output.jsonl"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            with fixture.open() as f:
                tmp.write(f.read())
            tmp_path = tmp.name
        try:
            meta = extract_metadata(tmp_path, None, "copilot")
            self.assertEqual(meta.get("model"), "test-copilot-model")

            extract_text_from_output(tmp_path, "copilot")
            with Path(tmp_path).open() as f:
                text = f.read()
            self.assertIn("VERDICT: REVISE", text)
        finally:
            Path(tmp_path).unlink()

    def test_extract_metadata_codex(self):
        """Test 8d: Codex JSONL events fixture extracts model and effort."""
        fixture = str(Path(FIXTURES_DIR) / "codex_events.jsonl")
        meta = extract_metadata(None, fixture, "codex")
        self.assertEqual(meta.get("model"), "test-codex-model")
        self.assertEqual(meta.get("effort"), "high")

    def test_extract_text_opencode(self):
        """Test 8e: opencode JSONL fixture extracts review text correctly."""
        fixture = Path(FIXTURES_DIR) / "opencode_output.jsonl"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            with fixture.open() as f:
                tmp.write(f.read())
            tmp_path = tmp.name
        try:
            extract_text_from_output(tmp_path, "opencode")
            with Path(tmp_path).open() as f:
                text = f.read()
            self.assertIn("VERDICT: REVISE", text)
            self.assertIn("Blocking Issues", text)
            self.assertIn("No rollback strategy", text)
            # Should be plain text, not JSONL
            self.assertNotIn('"type":"text"', text)
        finally:
            Path(tmp_path).unlink()

    def test_extract_text_opencode_drops_tool_narration(self):
        """Test 8e2: pre-answer tool-narration (in a tool-calls step) is dropped;
        only the final stop-step review text survives."""
        fixture = Path(FIXTURES_DIR) / "opencode_with_narration.jsonl"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            with fixture.open() as f:
                tmp.write(f.read())
            tmp_path = tmp.name
        try:
            extract_text_from_output(tmp_path, "opencode")
            text = Path(tmp_path).read_text()
            self.assertIn("VERDICT: REVISE", text)
            self.assertIn("No gating strategy", text)
            # The tool-call narration must not leak into the review prose.
            self.assertNotIn("I need to check how the deploy script", text)
        finally:
            Path(tmp_path).unlink()

    def test_extract_session_id_opencode(self):
        """Test 8f: opencode session ID extracted from first JSONL line."""
        from _common.metadata.extractors import extract_session_id_opencode
        fixture = Path(FIXTURES_DIR) / "opencode_output.jsonl"
        sid = extract_session_id_opencode(str(fixture))
        self.assertEqual(sid, "ses_fixture12345abcdef")

    def test_malformed_output_warning(self):
        """Test 9: Malformed JSON emits warning, file left as-is."""
        fixture = Path(FIXTURES_DIR) / "malformed.json"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            with fixture.open() as f:
                original = f.read()
                tmp.write(original)
            tmp_path = tmp.name
        try:
            # Capture stderr
            import io
            from contextlib import redirect_stderr

            stderr_buf = io.StringIO()
            with redirect_stderr(stderr_buf):
                extract_text_from_output(tmp_path, "claude")
            warning = stderr_buf.getvalue()
            self.assertIn("Warning", warning)
            self.assertIn("could not extract", warning)

            # File should be unchanged
            with Path(tmp_path).open() as f:
                content = f.read()
            self.assertEqual(content, original)
        finally:
            Path(tmp_path).unlink()


class TestOpencodeMetadataExport(unittest.TestCase):
    """Tests for _extract_opencode_metadata_via_export (Finding #3)."""

    @mock.patch("_common.metadata.extractors.subprocess.run")
    def test_extracts_model_and_effort_from_export(self, mock_run):
        """Valid export JSON returns model (providerID/modelID) and effort (max→xhigh)."""
        from _common.metadata.extractors import _extract_opencode_metadata_via_export

        export_json = json.dumps({
            "messages": [
                {
                    "info": {
                        "model": {
                            "providerID": "opencode-go",
                            "modelID": "deepseek-v4-pro",
                            "variant": "max",
                        }
                    }
                }
            ]
        })
        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "export", "ses_1"], 0, stdout=export_json, stderr=""
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta["model"], "opencode-go/deepseek-v4-pro")
        self.assertEqual(meta["effort"], "xhigh")

    @mock.patch("_common.metadata.extractors.subprocess.run")
    def test_extracts_from_flattened_assistant_shape(self, mock_run):
        """v1.17+ flattens providerID/modelID/variant onto info (info.model empty)."""
        from _common.metadata.extractors import _extract_opencode_metadata_via_export

        export_json = json.dumps({
            "messages": [
                {
                    "info": {
                        "role": "assistant",
                        "model": {},
                        "providerID": "opencode-go",
                        "modelID": "deepseek-v4-flash",
                        "variant": "high",
                    }
                }
            ]
        })
        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "export", "ses_1"], 0, stdout=export_json, stderr=""
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta["model"], "opencode-go/deepseek-v4-flash")
        self.assertEqual(meta["effort"], "high")

    @mock.patch("_common.metadata.extractors.subprocess.run")
    def test_nonzero_returncode_returns_empty(self, mock_run):
        """Non-zero exit code from opencode export returns empty dict."""
        from _common.metadata.extractors import _extract_opencode_metadata_via_export

        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "export", "ses_1"], 1, stdout="", stderr="not found"
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta, {})

    @mock.patch("_common.metadata.extractors.subprocess.run")
    def test_timeout_returns_empty(self, mock_run):
        """TimeoutExpired returns empty dict."""
        from _common.metadata.extractors import _extract_opencode_metadata_via_export

        mock_run.side_effect = subprocess.TimeoutExpired(
            ["opencode", "export", "ses_1"], 15
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta, {})

    @mock.patch("_common.metadata.extractors.subprocess.run")
    def test_malformed_export_json_returns_empty(self, mock_run):
        """Malformed JSON in export stdout returns empty dict."""
        from _common.metadata.extractors import _extract_opencode_metadata_via_export

        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "export", "ses_1"], 0, stdout="{not json", stderr=""
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta, {})

    @mock.patch("_common.metadata.extractors.subprocess.run")
    def test_variant_fallback_passthrough(self, mock_run):
        """Unrecognized variant is passed through unchanged."""
        from _common.metadata.extractors import _extract_opencode_metadata_via_export

        export_json = json.dumps({
            "messages": [
                {
                    "info": {
                        "model": {
                            "providerID": "opencode-go",
                            "modelID": "deepseek-v4-pro",
                            "variant": "unknown-effort",
                        }
                    }
                }
            ]
        })
        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "export", "ses_1"], 0, stdout=export_json, stderr=""
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta["effort"], "unknown-effort")
