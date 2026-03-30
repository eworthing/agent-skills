#!/usr/bin/env python3
"""
test_run_review.py — Deterministic test suite for run_review.py.

Tier 1: Local tests that exercise pure script logic (no external CLIs).
Tier 2: Optional self-checks for installed provider CLIs.

Run:  python3 scripts/test_run_review.py
"""

import argparse
import json
import os
import signal
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
import run_review  # noqa: E402
from run_review import extract_metadata, extract_text_from_output, self_check  # noqa: E402


def run_script(*extra_args):
    """Run run_review.py as subprocess, return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT, *list(extra_args)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def make_args(**overrides):
    """Create a Namespace matching run_review.py argument names."""
    data = {
        "reviewer": "claude",
        "plan_file": None,
        "prompt_file": None,
        "output_file": None,
        "session_file": None,
        "events_file": None,
        "model": None,
        "effort": None,
        "resume": False,
        "timeout": 600,
        "self_check": False,
        "list_models": False,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


class TestListModels(unittest.TestCase):
    """Tests 1-2: --list-models output."""

    def test_list_models_all_providers(self):
        """Test 1: --list-models prints all 4 providers with correct aliases."""
        rc, stdout, stderr = run_script("--list-models")
        self.assertEqual(rc, 0, f"stderr: {stderr}")
        for provider in ("claude", "gemini", "codex", "copilot"):
            self.assertIn(
                provider, stdout, f"Provider {provider} missing from --list-models output"
            )
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
            "--reviewer",
            "claude",
            "--model",
            "OPUS",
            "--prompt-file",
            os.devnull,
            "--list-models",
        )
        # --list-models exits 0; model validation runs before it.
        # No warning should be emitted since OPUS normalizes to opus.
        self.assertEqual(rc, 0)
        self.assertNotIn("Warning", stderr)

    def test_model_prefix_suggestion(self):
        """Test 4: --model fla --reviewer gemini suggests flash/flash-lite."""
        rc, _stdout, stderr = run_script(
            "--reviewer",
            "gemini",
            "--model",
            "fla",
            "--list-models",
        )
        self.assertEqual(rc, 0)
        self.assertIn("Warning", stderr)
        self.assertIn("flash", stderr)

    def test_unknown_model_warning(self):
        """Test 5: --model flahs --reviewer gemini warns on stderr."""
        rc, _stdout, stderr = run_script(
            "--reviewer",
            "gemini",
            "--model",
            "flahs",
            "--list-models",
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
            "--reviewer",
            "claude",
            "--plan-file",
            "/nonexistent/plan.md",
            "--prompt-file",
            os.devnull,
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("--plan-file", stderr)
        self.assertIn("not found", stderr)

    def test_missing_prompt_file(self):
        """Test 7: --prompt-file /nonexistent exits non-zero with clear error."""
        rc, _stdout, stderr = run_script(
            "--reviewer",
            "claude",
            "--prompt-file",
            "/nonexistent/prompt.md",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("--prompt-file", stderr)
        self.assertIn("not found", stderr)

    def test_bare_filename_output(self):
        """Test 10: --output-file review.json (bare filename) validates cwd."""
        # This should pass the directory validation (cwd exists and is writable)
        # but will fail later at binary check — that's fine, we're testing validation.
        _rc, _stdout, stderr = run_script(
            "--reviewer",
            "claude",
            "--prompt-file",
            os.devnull,
            "--output-file",
            "review.json",
        )
        # Should NOT fail with "directory does not exist" error
        self.assertNotIn("directory for --output-file does not exist", stderr)

    @unittest.skipIf(
        sys.platform == "win32", "POSIX directory permissions not supported on Windows"
    )
    def test_nonwritable_output_dir(self):
        """Test 11: Non-writable output directory exits non-zero."""
        tmpdir = tempfile.mkdtemp(prefix="ppr-test-")
        readonly_dir = Path(tmpdir) / "readonly"
        readonly_dir.mkdir(parents=True)
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # r-x
        try:
            rc, _stdout, stderr = run_script(
                "--reviewer",
                "claude",
                "--prompt-file",
                os.devnull,
                "--output-file",
                str(readonly_dir / "out.json"),
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


class TestCommandBuilders(unittest.TestCase):
    """Direct unit coverage for provider-specific command construction."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-builder-")
        self.prompt_file = Path(self.tmpdir.name) / "prompt.md"
        self.prompt_file.write_text("Review this plan carefully.\n", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_build_codex_cmd_fresh_exec_maps_effort_and_sandbox(self):
        args = make_args(
            reviewer="codex",
            prompt_file=str(self.prompt_file),
            output_file="/tmp/review.md",
            model="gpt-5.4",
            effort="high",
        )

        cmd = run_review.build_codex_cmd(args)

        self.assertEqual(cmd[:5], ["codex", "exec", "--sandbox", "read-only", "-c"])
        self.assertIn("approval_mode=never", cmd)
        self.assertIn("--json", cmd)
        self.assertIn("--output-last-message", cmd)
        self.assertIn("/tmp/review.md", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("gpt-5.4", cmd)
        self.assertIn("model_reasoning_effort=high", cmd)
        self.assertEqual(cmd[-1], "-")
        self.assertNotIn("--resume", cmd)

    def test_build_codex_cmd_resume_uses_resume_subcommand(self):
        args = make_args(
            reviewer="codex",
            prompt_file=str(self.prompt_file),
            output_file="/tmp/review.md",
            resume=True,
        )

        cmd = run_review.build_codex_cmd(args, session_id="codex-session")

        self.assertEqual(cmd[:4], ["codex", "exec", "resume", "codex-session"])
        self.assertIn("approval_mode=never", cmd)
        self.assertIn("--json", cmd)
        self.assertNotIn("--sandbox", cmd)
        self.assertEqual(cmd[-1], "-")

    def test_build_gemini_cmd_resume_uses_prompt_flag(self):
        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            model="flash",
            resume=True,
        )

        cmd = run_review.build_gemini_cmd(args, session_id="sess-123")

        self.assertEqual(cmd[:3], ["gemini", "--resume", "sess-123"])
        self.assertIn("--sandbox", cmd)
        self.assertIn("--approval-mode", cmd)
        self.assertIn("yolo", cmd)
        self.assertIn("--output-format", cmd)
        self.assertIn("json", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("flash", cmd)
        self.assertIn("-p", cmd)
        self.assertIn("Review this plan carefully.\n", cmd)

    def test_build_gemini_cmd_keeps_headless_flag_with_missing_prompt_text(self):
        args = make_args(
            reviewer="gemini",
            prompt_file=str(Path(self.tmpdir.name) / "missing-prompt.md"),
        )

        cmd = run_review.build_gemini_cmd(args)

        self.assertIn("-p", cmd)
        self.assertEqual(cmd[-1], "")

    def test_build_claude_cmd_sets_reviewer_system_prompt_and_effort(self):
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            model="opus",
            effort="xhigh",
        )

        cmd = run_review.build_claude_cmd(args)

        self.assertEqual(cmd[:3], ["claude", "-p", "Review this plan carefully.\n"])
        self.assertIn("--no-session-persistence", cmd)
        self.assertIn("--permission-mode", cmd)
        self.assertIn("plan", cmd)
        self.assertIn("--tools", cmd)
        self.assertIn("--allowedTools", cmd)
        self.assertIn("--output-format", cmd)
        self.assertIn("--max-turns", cmd)
        self.assertIn("--append-system-prompt", cmd)
        self.assertIn(
            "You are a code reviewer. Analyze the plan and provide feedback. "
            "End with VERDICT: APPROVED or VERDICT: REVISE on the last line.",
            cmd,
        )
        self.assertIn("--model", cmd)
        self.assertIn("opus", cmd)
        self.assertIn("--effort", cmd)
        self.assertIn("max", cmd)

    def test_build_copilot_cmd_sets_headless_review_flags(self):
        args = make_args(
            reviewer="copilot",
            prompt_file=str(self.prompt_file),
            model="gpt-5.4",
            effort="medium",
            resume=True,
        )

        cmd = run_review.build_copilot_cmd(args, session_id="copilot-session")

        self.assertEqual(cmd[:4], ["copilot", "-p", "Review this plan carefully.\n", "-s"])
        self.assertIn("--resume=copilot-session", cmd)
        self.assertIn("--no-ask-user", cmd)
        self.assertIn("--yolo", cmd)
        self.assertIn("--deny-tool=write,shell,memory", cmd)
        self.assertIn("--no-custom-instructions", cmd)
        self.assertIn("--no-auto-update", cmd)
        self.assertIn("--output-format", cmd)
        self.assertIn("json", cmd)
        self.assertIn("--model", cmd)
        self.assertIn("gpt-5.4", cmd)
        self.assertIn("--reasoning-effort", cmd)
        self.assertIn("medium", cmd)


class TestSelfCheckUnit(unittest.TestCase):
    """Pure unit tests for self_check edge cases."""

    @mock.patch("run_review.shutil.which", return_value="/fake/gemini")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_gemini_timeout_is_inconclusive_success(self, mock_run, _mock_which):
        """Gemini help timeout under automation should not fail install check."""
        mock_run.side_effect = subprocess.TimeoutExpired(["gemini", "--help"], 15)

        self.assertTrue(self_check("gemini"))

    @mock.patch("run_review.shutil.which", return_value="/fake/copilot")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_copilot_keychain_error_is_inconclusive_success(self, mock_run, _mock_which):
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


_CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows constant sentinel for testing


class TestPlatformHelpers(unittest.TestCase):
    """Tests for cross-platform process helpers."""

    @mock.patch("run_review.sys")
    def test_popen_session_kwargs_posix(self, mock_sys):
        mock_sys.platform = "linux"
        result = run_review._popen_session_kwargs()
        self.assertEqual(result, {"start_new_session": True})

    @mock.patch(
        "run_review.subprocess.CREATE_NEW_PROCESS_GROUP", _CREATE_NEW_PROCESS_GROUP, create=True
    )
    @mock.patch("run_review.sys")
    def test_popen_session_kwargs_windows(self, mock_sys):
        mock_sys.platform = "win32"
        result = run_review._popen_session_kwargs()
        self.assertIn("creationflags", result)
        self.assertEqual(result["creationflags"], _CREATE_NEW_PROCESS_GROUP)

    @mock.patch("run_review.sys")
    def test_kill_tree_windows_uses_taskkill(self, mock_sys):
        mock_sys.platform = "win32"
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        with mock.patch("run_review.subprocess.run") as mock_run:
            run_review._kill_tree(mock_proc)
            mock_run.assert_called_once_with(
                ["taskkill", "/T", "/F", "/PID", "12345"],
                capture_output=True,
            )
            mock_proc.wait.assert_called_once()

    @mock.patch("run_review.sys")
    def test_kill_tree_posix_uses_killpg(self, mock_sys):
        mock_sys.platform = "linux"
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        with (
            mock.patch("run_review.os.getpgid", return_value=12345),
            mock.patch("run_review.os.killpg"),
        ):
            run_review._kill_tree(mock_proc)
            mock_proc.wait.assert_called()


class TestRunReviewExecution(unittest.TestCase):
    """Execution-path unit tests that stub subprocess behavior."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-run-review-")
        self.prompt_file = Path(self.tmpdir.name) / "prompt.md"
        self.prompt_file.write_text("Review this plan carefully.\n", encoding="utf-8")
        self.output_file = Path(self.tmpdir.name) / "review.json"
        self.session_file = Path(self.tmpdir.name) / "session.json"
        self.events_file = Path(self.tmpdir.name) / "events.jsonl"

    def tearDown(self):
        self.tmpdir.cleanup()

    @staticmethod
    def _proc(returncode, stdout="", stderr=""):
        proc = mock.MagicMock()
        proc.communicate.return_value = (stdout, stderr)
        proc.returncode = returncode
        proc.poll.return_value = returncode
        return proc

    def test_run_review_gemini_effort_overlay_preserves_existing_settings(self):
        source_dir = Path(self.tmpdir.name) / "source-config"
        source_dir.mkdir()
        (source_dir / "settings.json").write_text(
            json.dumps({"theme": "dark", "thinkingConfig": {"thinkingBudget": 1}}),
            encoding="utf-8",
        )
        overlay_dir = Path(self.tmpdir.name) / "overlay-config"
        overlay_dir.mkdir()

        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            effort="high",
        )

        proc = self._proc(0, stdout='{"response":"ok"}')
        with (
            mock.patch.dict(os.environ, {"GEMINI_CONFIG_DIR": str(source_dir)}, clear=False),
            mock.patch("run_review.tempfile.mkdtemp", return_value=str(overlay_dir)),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="gemini-session"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
            mock.patch("run_review.shutil.rmtree"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        settings = json.loads((overlay_dir / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["theme"], "dark")
        self.assertEqual(settings["thinkingConfig"]["thinkingBudget"], 16384)
        popen_env = mock_popen.call_args.kwargs["env"]
        self.assertEqual(popen_env["GEMINI_CONFIG_DIR"], str(overlay_dir))

    def test_run_review_resume_failure_retries_once_without_resume(self):
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=True,
        )

        first_proc = self._proc(2, stdout="", stderr="resume failed")
        second_proc = self._proc(1, stdout="", stderr="fresh exec failed")

        with (
            mock.patch(
                "run_review.load_session",
                return_value={"session_id": "resume-session", "round": 1, "model": "prior-model"},
            ),
            mock.patch("run_review.subprocess.Popen", side_effect=[first_proc, second_proc]) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 1)
        self.assertFalse(args.resume)
        self.assertEqual(mock_popen.call_count, 2)
        first_cmd = mock_popen.call_args_list[0].args[0]
        second_cmd = mock_popen.call_args_list[1].args[0]
        self.assertIn("--resume", first_cmd)
        self.assertNotIn("--resume", second_cmd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
