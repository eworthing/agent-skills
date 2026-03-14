#!/usr/bin/env python3
"""
test_run_review.py — Deterministic test suite for run_review.py.

Tier 1: 11 local tests that exercise pure script logic (no external CLIs).
Tier 2: Optional self-checks for installed provider CLIs.

Run:  python3 scripts/test_run_review.py
"""

import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Resolve paths relative to this test file
SCRIPT_DIR = str(Path(__file__).resolve().parent)
SCRIPT = str(Path(SCRIPT_DIR) / "run_review.py")
FIXTURES_DIR = str(Path(SCRIPT_DIR).parent / "evals" / "fixtures")

# Import functions from run_review for direct unit tests
sys.path.insert(0, SCRIPT_DIR)
from run_review import extract_metadata, extract_text_from_output, self_check  # noqa: E402


def run_script(*extra_args):
    """Run run_review.py as subprocess, return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT, *list(extra_args)]
    result = subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace",
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


class TestListModels(unittest.TestCase):
    """Tests 1-2: --list-models output."""

    def test_list_models_all_providers(self):
        """Test 1: --list-models prints all 4 providers with correct aliases."""
        rc, stdout, stderr = run_script("--list-models")
        self.assertEqual(rc, 0, f"stderr: {stderr}")
        for provider in ("claude", "gemini", "codex", "copilot"):
            self.assertIn(provider, stdout,
                          f"Provider {provider} missing from --list-models output")
        # Claude should have sonnet, opus, haiku
        self.assertIn("sonnet", stdout)
        self.assertIn("opus", stdout)
        self.assertIn("haiku", stdout)
        # Gemini should have auto, pro, flash, flash-lite
        self.assertIn("flash", stdout)
        self.assertIn("pro", stdout)
        # Codex/copilot should indicate raw IDs
        self.assertIn("raw model IDs", stdout)

    def test_list_models_single_provider(self):
        """Test 2: --list-models --reviewer gemini shows only gemini."""
        rc, stdout, stderr = run_script("--list-models", "--reviewer", "gemini")
        self.assertEqual(rc, 0, f"stderr: {stderr}")
        self.assertIn("gemini", stdout)
        self.assertIn("flash", stdout)
        # Other providers should not appear
        self.assertNotIn("codex:", stdout)
        self.assertNotIn("copilot:", stdout)


class TestModelValidation(unittest.TestCase):
    """Tests 3-5: Model alias normalization and warnings."""

    def test_model_case_normalization(self):
        """Test 3: --model OPUS --reviewer claude normalizes to opus (lowercase)."""
        # --list-models exits before binary check, but model validation runs first
        # We need to trigger model validation with a real invocation that will fail
        # at binary check. Use a nonexistent prompt to trigger early exit after validation.
        rc, _stdout, stderr = run_script(
            "--reviewer", "claude", "--model", "OPUS",
            "--prompt-file", "/dev/null", "--list-models",
        )
        # --list-models exits 0; model validation runs before it.
        # No warning should be emitted since OPUS normalizes to opus.
        self.assertEqual(rc, 0)
        self.assertNotIn("Warning", stderr)

    def test_model_prefix_suggestion(self):
        """Test 4: --model fla --reviewer gemini suggests flash/flash-lite."""
        rc, _stdout, stderr = run_script(
            "--reviewer", "gemini", "--model", "fla", "--list-models",
        )
        self.assertEqual(rc, 0)
        self.assertIn("Warning", stderr)
        self.assertIn("flash", stderr)

    def test_unknown_model_warning(self):
        """Test 5: --model flahs --reviewer gemini warns on stderr."""
        rc, _stdout, stderr = run_script(
            "--reviewer", "gemini", "--model", "flahs", "--list-models",
        )
        self.assertEqual(rc, 0)
        self.assertIn("Warning", stderr)
        self.assertIn("flahs", stderr)
        self.assertIn("not a recognized shorthand", stderr)


class TestFileValidation(unittest.TestCase):
    """Tests 6-7, 10-11: File argument validation (Phase 2a)."""

    def test_missing_plan_file(self):
        """Test 6: --plan-file /nonexistent exits non-zero with clear error."""
        rc, _stdout, stderr = run_script(
            "--reviewer", "claude",
            "--plan-file", "/nonexistent/plan.md",
            "--prompt-file", "/dev/null",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("--plan-file", stderr)
        self.assertIn("not found", stderr)

    def test_missing_prompt_file(self):
        """Test 7: --prompt-file /nonexistent exits non-zero with clear error."""
        rc, _stdout, stderr = run_script(
            "--reviewer", "claude",
            "--prompt-file", "/nonexistent/prompt.md",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("--prompt-file", stderr)
        self.assertIn("not found", stderr)

    def test_bare_filename_output(self):
        """Test 10: --output-file review.json (bare filename) validates cwd."""
        # This should pass the directory validation (cwd exists and is writable)
        # but will fail later at binary check — that's fine, we're testing validation.
        _rc, _stdout, stderr = run_script(
            "--reviewer", "claude",
            "--prompt-file", "/dev/null",
            "--output-file", "review.json",
        )
        # Should NOT fail with "directory does not exist" error
        self.assertNotIn("directory for --output-file does not exist", stderr)

    def test_nonwritable_output_dir(self):
        """Test 11: Non-writable output directory exits non-zero."""
        tmpdir = tempfile.mkdtemp(prefix="ppr-test-")
        readonly_dir = Path(tmpdir) / "readonly"
        readonly_dir.mkdir(parents=True)
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # r-x
        try:
            rc, _stdout, stderr = run_script(
                "--reviewer", "claude",
                "--prompt-file", "/dev/null",
                "--output-file", str(readonly_dir / "out.json"),
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("not writable", stderr)
        finally:
            readonly_dir.chmod(stat.S_IRWXU)
            shutil.rmtree(tmpdir)


class TestOutputParsing(unittest.TestCase):
    """Tests 8-9: Output extraction from fixtures (direct import, no subprocess)."""

    def test_extract_text_claude(self):
        """Test 8a: Claude JSON fixture extracts review text correctly."""
        # Copy fixture to temp file (extraction rewrites the file)
        fixture = Path(FIXTURES_DIR) / "claude_output.json"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False) as tmp:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False) as tmp:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl",
                                          delete=False) as tmp:
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

    def test_malformed_output_warning(self):
        """Test 9: Malformed JSON emits warning, file left as-is."""
        fixture = Path(FIXTURES_DIR) / "malformed.json"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False) as tmp:
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


class TestSelfCheckUnit(unittest.TestCase):
    """Pure unit tests for self_check edge cases."""

    @mock.patch("run_review.shutil.which", return_value="/fake/gemini")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_gemini_timeout_is_inconclusive_success(
        self, mock_run, _mock_which
    ):
        """Gemini help timeout under automation should not fail install check."""
        mock_run.side_effect = subprocess.TimeoutExpired(["gemini", "--help"], 15)

        self.assertTrue(self_check("gemini"))

    @mock.patch("run_review.shutil.which", return_value="/fake/copilot")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_copilot_keychain_error_is_inconclusive_success(
        self, mock_run, _mock_which
    ):
        """Copilot keychain startup errors under automation should not fail install check."""
        mock_run.return_value = subprocess.CompletedProcess(
            ["copilot", "--help"],
            1,
            stdout="",
            stderr="ERROR: SecItemCopyMatching failed -50\n",
        )

        self.assertTrue(self_check("copilot"))

    @mock.patch("run_review.shutil.which", return_value="/fake/claude")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_generic_timeout_still_fails(self, mock_run, _mock_which):
        """Timeouts remain failures for providers without a known automation exception."""
        mock_run.side_effect = subprocess.TimeoutExpired(["claude", "--help"], 15)

        self.assertFalse(self_check("claude"))


class TestSelfCheck(unittest.TestCase):
    """Tier 2: Optional self-checks for installed provider CLIs."""

    @unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
    def test_self_check_claude(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "claude")
        self.assertEqual(rc, 0, f"stderr: {stderr}")

    @unittest.skipUnless(shutil.which("gemini"), "gemini CLI not installed")
    def test_self_check_gemini(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "gemini")
        self.assertEqual(rc, 0, f"stderr: {stderr}")

    @unittest.skipUnless(shutil.which("codex"), "codex CLI not installed")
    def test_self_check_codex(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "codex")
        self.assertEqual(rc, 0, f"stderr: {stderr}")

    @unittest.skipUnless(shutil.which("copilot"), "copilot CLI not installed")
    def test_self_check_copilot(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "copilot")
        self.assertEqual(rc, 0, f"stderr: {stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
