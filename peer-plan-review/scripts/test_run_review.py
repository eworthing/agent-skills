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
import shutil
import signal
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
PATHS_SCRIPT = str(Path(SCRIPT_DIR) / "ppr_paths.py")
FIXTURES_DIR = str(Path(SCRIPT_DIR) / "fixtures")

# Import functions from run_review for direct unit tests
sys.path.insert(0, SCRIPT_DIR)
import run_review  # noqa: E402
from ppr_io import parse_structured_review  # noqa: E402
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


def run_paths_script(*extra_args, env=None):
    """Run ppr_paths.py as subprocess, return (returncode, stdout, stderr)."""
    cmd = [sys.executable, PATHS_SCRIPT, *list(extra_args)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=env,
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
        "error_log": None,
        "review_id": None,
        "summary_file": None,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


class TestListModels(unittest.TestCase):
    """Tests 1-2: --list-models output."""

    def test_list_models_all_providers(self):
        """Test 1: --list-models prints all 5 providers with correct aliases."""
        rc, stdout, stderr = run_script("--list-models")
        self.assertEqual(rc, 0, f"stderr: {stderr}")
        for provider in ("claude", "gemini", "codex", "copilot", "opencode"):
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
        # Codex/copilot/opencode should indicate raw IDs
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
        # Create a valid prompt file so validation passes prompt checks
        prompt_file = Path(tmpdir) / "prompt.md"
        prompt_file.write_text("Review this plan.\n", encoding="utf-8")
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # r-x
        try:
            rc, _stdout, stderr = run_script(
                "--reviewer",
                "claude",
                "--prompt-file",
                str(prompt_file),
                "--output-file",
                str(readonly_dir / "out.json"),
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("not writable", stderr)
        finally:
            readonly_dir.chmod(stat.S_IRWXU)
            shutil.rmtree(tmpdir)


class TestPathHelper(unittest.TestCase):
    """Canonical temp-path helper must not depend on ad hoc env vars."""

    def test_shell_output_without_prompt_file_env(self):
        env = os.environ.copy()
        env.pop("PROMPT_FILE", None)
        rc, stdout, stderr = run_paths_script(
            "--review-id",
            "abc123def456",
            "--tmpdir",
            "/tmp",
            "--format",
            "shell",
            env=env,
        )
        self.assertEqual(rc, 0, f"stderr: {stderr}")
        self.assertIn("export PROMPT_FILE=/tmp/ppr-abc123def456-prompt.md", stdout)
        self.assertIn("export PLAN_FILE=/tmp/ppr-abc123def456-plan.md", stdout)
        self.assertEqual(stderr, "")

    def test_json_output_from_review_id_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("resume-round-2\n")
            review_id_file = f.name
        try:
            rc, stdout, stderr = run_paths_script(
                "--review-id-file",
                review_id_file,
                "--tmpdir",
                "/tmp",
            )
            self.assertEqual(rc, 0, f"stderr: {stderr}")
            data = json.loads(stdout)
            self.assertEqual(data["review_id"], "resume-round-2")
            self.assertEqual(data["prompt_file"], "/tmp/ppr-resume-round-2-prompt.md")
            self.assertEqual(data["session_file"], "/tmp/ppr-resume-round-2-session.json")
        finally:
            Path(review_id_file).unlink()

    def test_invalid_review_id_exits_nonzero(self):
        rc, _stdout, stderr = run_paths_script("--review-id", "../bad")
        self.assertNotEqual(rc, 0)
        self.assertIn("review id must contain only", stderr)


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

    def test_extract_session_id_opencode(self):
        """Test 8f: opencode session ID extracted from first JSONL line."""
        from ppr_metadata import extract_session_id_opencode
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

    def test_build_codex_cmd_no_model_no_effort(self):
        args = make_args(
            reviewer="codex",
            prompt_file=str(self.prompt_file),
            output_file="/tmp/review.md",
        )

        cmd = run_review.build_codex_cmd(args)

        self.assertNotIn("-m", cmd)
        self.assertNotIn("model_reasoning_effort", cmd)

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

    def test_build_codex_cmd_resume_true_but_no_session_id_is_fresh_exec(self):
        args = make_args(
            reviewer="codex",
            prompt_file=str(self.prompt_file),
            output_file="/tmp/review.md",
            resume=True,
        )

        cmd = run_review.build_codex_cmd(args, session_id=None)

        self.assertNotIn("resume", cmd)
        self.assertIn("--sandbox", cmd)
        self.assertIn("read-only", cmd)

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
        self.assertEqual(cmd[-1], "")

    def test_build_gemini_cmd_fresh_exec_maps_effort(self):
        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            model="pro",
            effort="high",
        )

        cmd = run_review.build_gemini_cmd(args)

        self.assertIn("-p", cmd)
        self.assertEqual(cmd[-1], "")
        self.assertIn("--sandbox", cmd)
        self.assertIn("--approval-mode", cmd)
        self.assertIn("yolo", cmd)
        self.assertIn("--output-format", cmd)
        self.assertIn("json", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("pro", cmd)
        extensions_index = cmd.index("--extensions")
        self.assertEqual(cmd[extensions_index + 1], "")
        self.assertNotIn("--resume", cmd)

    def test_build_gemini_cmd_resume_true_but_no_session_id_is_fresh_exec(self):
        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            model="flash",
            resume=True,
        )

        cmd = run_review.build_gemini_cmd(args, session_id=None)

        self.assertNotIn("--resume", cmd)
        self.assertIn("-p", cmd)

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

        self.assertEqual(cmd[:3], ["claude", "-p", ""])
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
        self.assertNotIn("--resume", cmd)

    def test_build_claude_cmd_fresh_does_not_disable_session_persistence(self):
        """Round 1 fresh exec must NOT include --no-session-persistence,
        otherwise round 2 --resume will fail because the session was never saved."""
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
        )

        cmd = run_review.build_claude_cmd(args)

        self.assertNotIn("--no-session-persistence", cmd)

    def test_build_claude_cmd_resume_adds_resume_flag(self):
        """When resume=True and session_id is provided, --resume <id> must be added."""
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            resume=True,
        )

        cmd = run_review.build_claude_cmd(args, session_id="claude-sess-123")

        self.assertIn("--resume", cmd)
        self.assertIn("claude-sess-123", cmd)
        self.assertNotIn("--no-session-persistence", cmd)

    def test_build_claude_cmd_resume_true_but_no_session_id_is_fresh_exec(self):
        """If resume=True but session_id is None, command should be a fresh exec
        (no --resume flag, no --no-session-persistence)."""
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            resume=True,
        )

        cmd = run_review.build_claude_cmd(args, session_id=None)

        self.assertNotIn("--resume", cmd)
        self.assertNotIn("--no-session-persistence", cmd)

    def test_build_copilot_cmd_sets_headless_review_flags(self):
        args = make_args(
            reviewer="copilot",
            prompt_file=str(self.prompt_file),
            model="gpt-5.4",
            effort="medium",
            resume=True,
        )

        cmd = run_review.build_copilot_cmd(args, session_id="copilot-session")

        self.assertEqual(cmd[:4], ["copilot", "-p", "", "-s"])
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

    def test_build_copilot_cmd_fresh_exec_no_resume(self):
        args = make_args(
            reviewer="copilot",
            prompt_file=str(self.prompt_file),
            model="gpt-5.4",
            effort="medium",
        )

        cmd = run_review.build_copilot_cmd(args)

        self.assertEqual(cmd[:4], ["copilot", "-p", "", "-s"])
        self.assertNotIn("--resume", cmd)
        self.assertIn("--no-ask-user", cmd)
        self.assertIn("--yolo", cmd)

    def test_build_copilot_cmd_resume_true_but_no_session_id_is_fresh_exec(self):
        args = make_args(
            reviewer="copilot",
            prompt_file=str(self.prompt_file),
            resume=True,
        )

        cmd = run_review.build_copilot_cmd(args, session_id=None)

        self.assertNotIn("--resume", cmd)
        self.assertIn("--no-ask-user", cmd)

    def test_build_opencode_cmd_fresh_exec_maps_effort_and_safety(self):
        args = make_args(
            reviewer="opencode",
            prompt_file=str(self.prompt_file),
            output_file="/tmp/review.jsonl",
            model="opencode-go/deepseek-v4-pro",
            effort="xhigh",
        )

        cmd = run_review.build_opencode_cmd(args)

        self.assertEqual(cmd[:3], ["opencode", "run", ""])
        self.assertIn("--format", cmd)
        self.assertIn("json", cmd)
        self.assertIn("--dangerously-skip-permissions", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("opencode-go/deepseek-v4-pro", cmd)
        self.assertIn("--variant", cmd)
        self.assertIn("max", cmd)
        self.assertNotIn("-s", cmd)

    def test_build_opencode_cmd_resume_uses_session_flag(self):
        args = make_args(
            reviewer="opencode",
            prompt_file=str(self.prompt_file),
            output_file="/tmp/review.jsonl",
            resume=True,
        )

        cmd = run_review.build_opencode_cmd(args, session_id="open-session-42")

        self.assertEqual(cmd[:3], ["opencode", "run", ""])
        self.assertIn("--format", cmd)
        self.assertIn("json", cmd)
        self.assertIn("-s", cmd)
        self.assertIn("open-session-42", cmd)

    def test_build_opencode_cmd_no_model_no_effort(self):
        args = make_args(
            reviewer="opencode",
            prompt_file=str(self.prompt_file),
        )

        cmd = run_review.build_opencode_cmd(args)

        self.assertEqual(cmd[:3], ["opencode", "run", ""])
        self.assertIn("--format", cmd)
        self.assertIn("json", cmd)
        self.assertIn("--dangerously-skip-permissions", cmd)
        self.assertNotIn("-m", cmd)
        self.assertNotIn("--variant", cmd)

    def test_build_opencode_cmd_resume_true_but_no_session_id_is_fresh_exec(self):
        args = make_args(
            reviewer="opencode",
            prompt_file=str(self.prompt_file),
            resume=True,
        )

        cmd = run_review.build_opencode_cmd(args, session_id=None)

        self.assertNotIn("-s", cmd)
        self.assertIn("--dangerously-skip-permissions", cmd)


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

    @unittest.skipUnless(shutil.which("opencode"), "opencode CLI not installed")
    def test_self_check_opencode(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "opencode")
        self.assertEqual(rc, 0, f"stderr: {stderr}")


_CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows constant sentinel for testing


class TestPlatformHelpers(unittest.TestCase):
    """Tests for cross-platform process helpers."""

    @mock.patch("ppr_process.sys")
    def test_popen_session_kwargs_posix(self, mock_sys):
        mock_sys.platform = "linux"
        result = run_review._popen_session_kwargs()
        self.assertEqual(result, {"start_new_session": True})

    @mock.patch(
        "ppr_process.subprocess.CREATE_NEW_PROCESS_GROUP", _CREATE_NEW_PROCESS_GROUP, create=True
    )
    @mock.patch("ppr_process.sys")
    def test_popen_session_kwargs_windows(self, mock_sys):
        mock_sys.platform = "win32"
        result = run_review._popen_session_kwargs()
        self.assertIn("creationflags", result)
        self.assertEqual(result["creationflags"], _CREATE_NEW_PROCESS_GROUP)

    @mock.patch("ppr_process.sys")
    def test_kill_tree_windows_uses_taskkill(self, mock_sys):
        mock_sys.platform = "win32"
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        with mock.patch("ppr_process.subprocess.run") as mock_run:
            run_review._kill_tree(mock_proc)
            mock_run.assert_called_once_with(
                ["taskkill", "/T", "/F", "/PID", "12345"],
                capture_output=True,
            )
            mock_proc.wait.assert_called_once()

    @mock.patch("ppr_process.sys")
    def test_kill_tree_posix_uses_killpg(self, mock_sys):
        mock_sys.platform = "linux"
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        with (
            mock.patch("ppr_process.os.getpgid", return_value=12345),
            mock.patch("ppr_process.os.killpg"),
        ):
            run_review._kill_tree(mock_proc)
            mock_proc.wait.assert_called()


class TestOpencodeMetadataExport(unittest.TestCase):
    """Tests for _extract_opencode_metadata_via_export (Finding #3)."""

    @mock.patch("ppr_metadata.subprocess.run")
    def test_extracts_model_and_effort_from_export(self, mock_run):
        """Valid export JSON returns model (providerID/modelID) and effort (max→xhigh)."""
        from ppr_metadata import _extract_opencode_metadata_via_export

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

    @mock.patch("ppr_metadata.subprocess.run")
    def test_nonzero_returncode_returns_empty(self, mock_run):
        """Non-zero exit code from opencode export returns empty dict."""
        from ppr_metadata import _extract_opencode_metadata_via_export

        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "export", "ses_1"], 1, stdout="", stderr="not found"
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta, {})

    @mock.patch("ppr_metadata.subprocess.run")
    def test_timeout_returns_empty(self, mock_run):
        """TimeoutExpired returns empty dict."""
        from ppr_metadata import _extract_opencode_metadata_via_export

        mock_run.side_effect = subprocess.TimeoutExpired(
            ["opencode", "export", "ses_1"], 15
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta, {})

    @mock.patch("ppr_metadata.subprocess.run")
    def test_malformed_export_json_returns_empty(self, mock_run):
        """Malformed JSON in export stdout returns empty dict."""
        from ppr_metadata import _extract_opencode_metadata_via_export

        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "export", "ses_1"], 0, stdout="{not json", stderr=""
        )
        meta = _extract_opencode_metadata_via_export("ses_1")
        self.assertEqual(meta, {})

    @mock.patch("ppr_metadata.subprocess.run")
    def test_variant_fallback_passthrough(self, mock_run):
        """Unrecognized variant is passed through unchanged."""
        from ppr_metadata import _extract_opencode_metadata_via_export

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

    def test_run_review_gemini_effort_overlay_excludes_auto_saved_policies(self):
        source_dir = Path(self.tmpdir.name) / "source-config"
        policies_dir = source_dir / "policies"
        policies_dir.mkdir(parents=True)
        (source_dir / "settings.json").write_text("{}", encoding="utf-8")
        (policies_dir / "auto-saved.toml").write_text(
            '[allow]\ncommand = "python3 -c \\"very large stale prompt\\""\n',
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
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="gemini-session"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
            mock.patch("run_review.shutil.rmtree"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        self.assertFalse((overlay_dir / "policies" / "auto-saved.toml").exists())

    def test_run_review_gemini_without_effort_uses_isolated_config_overlay(self):
        source_dir = Path(self.tmpdir.name) / "source-config"
        policies_dir = source_dir / "policies"
        policies_dir.mkdir(parents=True)
        (source_dir / "settings.json").write_text('{"theme":"dark"}', encoding="utf-8")
        (policies_dir / "auto-saved.toml").write_text(
            '[allow]\ncommand = "python3 -c \\"very large stale prompt\\""\n',
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
            effort=None,
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
        self.assertFalse((overlay_dir / "policies" / "auto-saved.toml").exists())
        popen_env = mock_popen.call_args.kwargs["env"]
        self.assertEqual(popen_env["GEMINI_CONFIG_DIR"], str(overlay_dir))

    def test_run_review_gemini_pipes_prompt_via_stdin(self):
        source_dir = Path(self.tmpdir.name) / "source-config"
        source_dir.mkdir()
        overlay_dir = Path(self.tmpdir.name) / "overlay-config"
        overlay_dir.mkdir()
        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
        )

        proc = self._proc(0, stdout='{"response":"ok"}')
        with (
            mock.patch.dict(os.environ, {"GEMINI_CONFIG_DIR": str(source_dir)}, clear=False),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.tempfile.mkdtemp", return_value=str(overlay_dir)),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="gemini-session"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
            mock.patch("run_review.shutil.rmtree"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        self.assertEqual(mock_popen.call_args.kwargs["stdin"], subprocess.PIPE)
        proc.communicate.assert_called_once_with(
            input="Review this plan carefully.\n",
            timeout=args.timeout,
        )

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
        # args.resume is NOT mutated — resume state is tracked via locals
        self.assertTrue(args.resume)
        self.assertEqual(mock_popen.call_count, 2)
        first_cmd = mock_popen.call_args_list[0].args[0]
        second_cmd = mock_popen.call_args_list[1].args[0]
        self.assertIn("--resume", first_cmd)
        self.assertNotIn("--resume", second_cmd)

    def test_run_review_claude_round1_to_round2_session_persistence(self):
        """Round 1 fresh exec must produce a command without --no-session-persistence,
        so that round 2 resume can find the session."""
        # Round 1: fresh exec
        args_round1 = make_args(
            reviewer="claude", prompt_file=str(self.prompt_file),
            output_file=str(self.output_file), session_file=str(self.session_file),
            events_file=str(self.events_file), resume=False,
        )
        proc1 = self._proc(0, stdout='{"result":"ok","session_id":"round1-sess"}')
        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc1) as mock_popen1,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="round1-sess"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args_round1)

        round1_cmd = mock_popen1.call_args_list[0].args[0]
        self.assertNotIn("--no-session-persistence", round1_cmd)
        self.assertNotIn("--resume", round1_cmd)

        # Round 2: resume=True with session_id from round 1
        args_round2 = make_args(
            reviewer="claude", prompt_file=str(self.prompt_file),
            output_file=str(self.output_file), session_file=str(self.session_file),
            events_file=str(self.events_file), resume=True,
        )
        proc2 = self._proc(0, stdout='{"result":"ok","session_id":"round2-sess"}')
        with (
            mock.patch("run_review.load_session", return_value={"session_id": "round1-sess", "round": 1}),
            mock.patch("run_review.subprocess.Popen", return_value=proc2) as mock_popen2,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="round2-sess"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args_round2)

        round2_cmd = mock_popen2.call_args_list[0].args[0]
        self.assertIn("--resume", round2_cmd)
        self.assertIn("round1-sess", round2_cmd)
        self.assertNotIn("--no-session-persistence", round2_cmd)


# ---------------------------------------------------------------------------
# Phase 1b+ new test classes
# ---------------------------------------------------------------------------

from ppr_io import probe_writable, validate_prompt_file  # noqa: E402
from ppr_log import EventLogger  # noqa: E402
from ppr_metadata import compute_plan_metadata  # noqa: E402
from ppr_providers import PROVIDERS  # noqa: E402


class TestEventLogger(unittest.TestCase):
    """Tests for the EventLogger JSONL logger."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-logger-")
        self.log_path = Path(self.tmpdir.name) / "events.jsonl"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_writes_valid_jsonl_line(self):
        logger = EventLogger(str(self.log_path), review_id="test123")
        logger.log("execution_start", provider="claude")
        lines = self.log_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["event"], "execution_start")
        self.assertEqual(data["provider"], "claude")
        self.assertEqual(data["review_id"], "test123")

    def test_appends_across_calls(self):
        logger = EventLogger(str(self.log_path), review_id="test")
        logger.log("event_a")
        logger.log("event_b")
        lines = self.log_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)

    def test_noop_when_no_path(self):
        logger = EventLogger(None)
        logger.log("should_not_crash")  # no exception

    def test_includes_all_fields(self):
        logger = EventLogger(str(self.log_path), review_id="r1")
        logger.log("test_event", provider="codex", round_num=3, error="boom", context={"k": "v"})
        data = json.loads(self.log_path.read_text().strip())
        self.assertIn("ts", data)
        self.assertEqual(data["review_id"], "r1")
        self.assertEqual(data["event"], "test_event")
        self.assertEqual(data["provider"], "codex")
        self.assertEqual(data["round"], 3)
        self.assertEqual(data["error"], "boom")
        self.assertEqual(data["ctx"], {"k": "v"})

    def test_handles_unwritable_log_path(self):
        logger = EventLogger("/nonexistent/dir/events.jsonl", review_id="r1")
        logger.log("should_not_crash")  # no exception

    def test_handles_missing_parent_directory(self):
        logger = EventLogger("/tmp/ppr-missing-dir-xyz/events.jsonl", review_id="r1")
        logger.log("should_not_crash")  # no exception

    def test_handles_non_serializable_context(self):
        logger = EventLogger(str(self.log_path), review_id="r1")
        logger.log("test", context={"path": Path("/tmp/test")})
        data = json.loads(self.log_path.read_text().strip())
        self.assertIn("/tmp/test", data["ctx"]["path"])

    def test_timestamp_format(self):
        logger = EventLogger(str(self.log_path), review_id="r1")
        logger.log("test")
        data = json.loads(self.log_path.read_text().strip())
        self.assertIn("+00:00", data["ts"])


class TestPromptValidation(unittest.TestCase):
    """Tests for validate_prompt_file."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-prompt-")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_empty_prompt_rejected(self):
        f = Path(self.tmpdir.name) / "empty.md"
        f.write_text("", encoding="utf-8")
        ok, err = validate_prompt_file(str(f))
        self.assertFalse(ok)
        self.assertIn("empty", err)

    def test_whitespace_only_prompt_rejected(self):
        f = Path(self.tmpdir.name) / "whitespace.md"
        f.write_text("   \n\t  \n", encoding="utf-8")
        ok, err = validate_prompt_file(str(f))
        self.assertFalse(ok)
        self.assertIn("empty", err)

    def test_binary_prompt_rejected(self):
        f = Path(self.tmpdir.name) / "binary.md"
        f.write_bytes(bytes([0x80, 0x81, 0x82, 0x83]))
        ok, err = validate_prompt_file(str(f))
        self.assertFalse(ok)
        self.assertIn("UTF-8", err)

    def test_valid_prompt_accepted(self):
        f = Path(self.tmpdir.name) / "valid.md"
        f.write_text("Review this plan.\n", encoding="utf-8")
        ok, err = validate_prompt_file(str(f))
        self.assertTrue(ok)
        self.assertIsNone(err)

    @unittest.skipIf(
        sys.platform == "win32", "POSIX file permissions not supported on Windows"
    )
    def test_unreadable_prompt_rejected(self):
        f = Path(self.tmpdir.name) / "unreadable.md"
        f.write_text("content", encoding="utf-8")
        f.chmod(0o000)
        try:
            ok, err = validate_prompt_file(str(f))
            self.assertFalse(ok)
            self.assertIn("not readable", err)
        finally:
            f.chmod(stat.S_IRWXU)


class TestWriteProbes(unittest.TestCase):
    """Tests for probe_writable."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-probe-")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_existing_writable_file(self):
        f = Path(self.tmpdir.name) / "writable.json"
        f.write_text("{}", encoding="utf-8")
        ok, err = probe_writable(str(f))
        self.assertTrue(ok)
        self.assertIsNone(err)

    @unittest.skipIf(
        sys.platform == "win32", "POSIX file permissions not supported on Windows"
    )
    def test_existing_readonly_file(self):
        f = Path(self.tmpdir.name) / "readonly.json"
        f.write_text("{}", encoding="utf-8")
        f.chmod(stat.S_IRUSR)
        try:
            ok, err = probe_writable(str(f))
            self.assertFalse(ok)
            self.assertIn("not writable", err)
        finally:
            f.chmod(stat.S_IRWXU)

    def test_new_file_in_writable_dir(self):
        ok, err = probe_writable(str(Path(self.tmpdir.name) / "new.json"))
        self.assertTrue(ok)
        self.assertIsNone(err)

    @unittest.skipIf(
        sys.platform == "win32", "POSIX directory permissions not supported on Windows"
    )
    def test_new_file_in_readonly_dir(self):
        readonly = Path(self.tmpdir.name) / "readonly"
        readonly.mkdir()
        readonly.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            ok, err = probe_writable(str(readonly / "new.json"))
            self.assertFalse(ok)
            self.assertIn("not writable", err)
        finally:
            readonly.chmod(stat.S_IRWXU)

    def test_path_is_directory(self):
        d = Path(self.tmpdir.name) / "subdir"
        d.mkdir()
        ok, err = probe_writable(str(d))
        self.assertFalse(ok)
        self.assertIn("not a regular file", err)

    @unittest.skipIf(
        sys.platform == "win32", "Symlink creation requires elevated privileges on Windows"
    )
    def test_path_is_symlink_to_directory(self):
        d = Path(self.tmpdir.name) / "target_dir"
        d.mkdir()
        link = Path(self.tmpdir.name) / "link_to_dir"
        link.symlink_to(d)
        ok, err = probe_writable(str(link))
        self.assertFalse(ok)
        self.assertIn("not a regular file", err)

    @unittest.skipIf(
        sys.platform == "win32", "FIFOs require POSIX"
    )
    def test_path_is_fifo(self):
        fifo = Path(self.tmpdir.name) / "test.fifo"
        os.mkfifo(str(fifo))
        ok, err = probe_writable(str(fifo))
        self.assertFalse(ok)
        self.assertIn("not a regular file", err)


class TestProviderCapabilityTable(unittest.TestCase):
    """Tests for the caps field on every PROVIDERS entry."""

    def test_all_providers_have_caps(self):
        for name, p in PROVIDERS.items():
            self.assertIn("caps", p, f"Missing caps on PROVIDERS[{name}]")

    def test_caps_fields_present(self):
        required = {"binary", "prompt_mode", "output_mode", "model_flag",
                     "effort_flag", "resume_flag_style", "resume_supported", "safety_flags"}
        for name, p in PROVIDERS.items():
            caps = p["caps"]
            for field in required:
                self.assertIn(field, caps, f"Missing {field} in PROVIDERS[{name}].caps")


class TestResumeMetadata(unittest.TestCase):
    """Tests for resume metadata in session data."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-resume-meta-")
        self.prompt_file = Path(self.tmpdir.name) / "prompt.md"
        self.prompt_file.write_text("Review.\n", encoding="utf-8")
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

    def test_session_records_resume_requested_false(self):
        args = make_args(
            reviewer="claude", prompt_file=str(self.prompt_file),
            output_file=str(self.output_file), session_file=str(self.session_file),
            events_file=str(self.events_file), resume=False,
        )
        proc = self._proc(0, stdout='{"result":"ok"}')
        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)
        session = json.loads(self.session_file.read_text())
        self.assertFalse(session["resume_requested"])
        self.assertFalse(session["resume_fallback_used"])
        self.assertEqual(session["resume_reason"], "fresh_exec")

    def test_session_records_resume_requested_true(self):
        args = make_args(
            reviewer="claude", prompt_file=str(self.prompt_file),
            output_file=str(self.output_file), session_file=str(self.session_file),
            events_file=str(self.events_file), resume=True,
        )
        proc = self._proc(0, stdout='{"result":"ok"}')
        with (
            mock.patch("run_review.load_session", return_value={"session_id": "s1", "round": 1}),
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)
        session = json.loads(self.session_file.read_text())
        self.assertTrue(session["resume_requested"])
        self.assertTrue(session["resume_attempted"])
        self.assertEqual(session["resume_reason"], "session_found")

    def test_session_records_fallback(self):
        args = make_args(
            reviewer="claude", prompt_file=str(self.prompt_file),
            output_file=str(self.output_file), session_file=str(self.session_file),
            events_file=str(self.events_file), resume=True,
        )
        first_proc = self._proc(2, stdout="", stderr="resume failed")
        second_proc = self._proc(0, stdout='{"result":"ok"}')
        with (
            mock.patch("run_review.load_session", return_value={"session_id": "s1", "round": 1}),
            mock.patch("run_review.subprocess.Popen", side_effect=[first_proc, second_proc]),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s2"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)
        session = json.loads(self.session_file.read_text())
        self.assertTrue(session["resume_requested"])
        self.assertTrue(session["resume_fallback_used"])
        self.assertEqual(session["resume_reason"], "fallback_to_fresh")


class TestPlanMetadata(unittest.TestCase):
    """Tests for compute_plan_metadata."""

    def test_computes_correctly(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Plan\nStep 1\n")
            f.flush()
            meta = compute_plan_metadata(f.name)
        try:
            self.assertEqual(meta["plan_name"], Path(f.name).name)
            self.assertEqual(meta["plan_bytes"], Path(f.name).stat().st_size)
            self.assertEqual(len(meta["plan_sha256"]), 64)
            self.assertIn("+00:00", meta["plan_mtime"])
        finally:
            Path(f.name).unlink()

    def test_plan_name_is_filename_only(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("content")
            f.flush()
            meta = compute_plan_metadata(f.name)
        try:
            self.assertNotIn("/", meta["plan_name"])
        finally:
            Path(f.name).unlink()

    def test_missing_file_returns_empty(self):
        meta = compute_plan_metadata("/nonexistent/plan.md")
        self.assertEqual(meta, {})

    def test_none_returns_empty(self):
        meta = compute_plan_metadata(None)
        self.assertEqual(meta, {})


class TestCorruption(unittest.TestCase):
    """Tests for edge cases with corrupt/unexpected files."""

    def test_zero_byte_output_no_crash(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            tmp_path = f.name
        try:
            from ppr_io import extract_text_from_output
            extract_text_from_output(tmp_path, "claude")  # should not raise
            self.assertEqual(Path(tmp_path).read_text(), "")
        finally:
            Path(tmp_path).unlink()

    def test_corrupt_session_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{corrupt json")
            tmp_path = f.name
        try:
            from ppr_io import load_session
            result = load_session(tmp_path)
            self.assertEqual(result, {})
        finally:
            Path(tmp_path).unlink()

    def test_resume_with_no_session_id(self):
        """Resume=True but session file has no session_id — should not crash."""
        tmpdir = tempfile.mkdtemp(prefix="ppr-corrupt-")
        prompt = Path(tmpdir) / "prompt.md"
        prompt.write_text("Review.\n", encoding="utf-8")
        session = Path(tmpdir) / "session.json"
        session.write_text("{}", encoding="utf-8")

        args = make_args(
            reviewer="claude", prompt_file=str(prompt),
            output_file=str(Path(tmpdir) / "out.json"),
            session_file=str(session),
            events_file=str(Path(tmpdir) / "events.jsonl"),
            resume=True,
        )

        proc = mock.MagicMock()
        proc.communicate.return_value = ('{"result":"ok"}', "")
        proc.returncode = 0
        proc.poll.return_value = 0

        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value=None),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)
        self.assertEqual(rc, 0)
        shutil.rmtree(tmpdir)

    def test_nonzero_exit_with_output_still_extracts(self):
        """Non-zero exit but output present — should extract and not retry."""
        tmpdir = tempfile.mkdtemp(prefix="ppr-extract-")
        prompt = Path(tmpdir) / "prompt.md"
        prompt.write_text("Review.\n", encoding="utf-8")
        output = Path(tmpdir) / "review.json"
        output.write_text('{"result":"Review text here"}', encoding="utf-8")

        args = make_args(
            reviewer="claude", prompt_file=str(prompt),
            output_file=str(output),
            session_file=str(Path(tmpdir) / "session.json"),
            events_file=str(Path(tmpdir) / "events.jsonl"),
            resume=False,
        )

        proc = mock.MagicMock()
        proc.communicate.return_value = ('{"result":"Review text here"}', "warning")
        proc.returncode = 1
        proc.poll.return_value = 1

        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)
        self.assertEqual(rc, 1)  # returns the error code, doesn't retry
        shutil.rmtree(tmpdir)

    def test_resume_with_output_does_not_retry(self):
        """Resume failure WITH output — should NOT fallback to fresh exec."""
        tmpdir = tempfile.mkdtemp(prefix="ppr-no-retry-")
        prompt = Path(tmpdir) / "prompt.md"
        prompt.write_text("Review.\n", encoding="utf-8")
        output = Path(tmpdir) / "review.json"

        args = make_args(
            reviewer="claude", prompt_file=str(prompt),
            output_file=str(output),
            session_file=str(Path(tmpdir) / "session.json"),
            events_file=str(Path(tmpdir) / "events.jsonl"),
            resume=True,
        )

        proc = mock.MagicMock()
        # Non-zero exit but produces output
        proc.communicate.return_value = ('{"result":"partial review"}', "error")
        proc.returncode = 1
        proc.poll.return_value = 1

        with (
            mock.patch("run_review.load_session", return_value={"session_id": "s1", "round": 1}),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)
        self.assertEqual(rc, 1)
        # Only one Popen call — no retry
        self.assertEqual(mock_popen.call_count, 1)
        shutil.rmtree(tmpdir)


class TestMockPathCompatibility(unittest.TestCase):
    """Verify re-export mock paths intercept calls from run_review.run_review()."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-compat-")
        self.prompt_file = Path(self.tmpdir.name) / "prompt.md"
        self.prompt_file.write_text("Review.\n", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    @staticmethod
    def _proc(returncode=0, stdout='{"result":"ok"}', stderr=""):
        proc = mock.MagicMock()
        proc.communicate.return_value = (stdout, stderr)
        proc.returncode = returncode
        proc.poll.return_value = returncode
        return proc

    def _run_and_check(self):
        """Run run_review with standard mocks, return mock objects for assertions."""
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(Path(self.tmpdir.name) / "out.json"),
            session_file=str(Path(self.tmpdir.name) / "session.json"),
            events_file=str(Path(self.tmpdir.name) / "events.jsonl"),
        )
        with (
            mock.patch("run_review.subprocess.Popen", return_value=self._proc()) as m_popen,
            mock.patch("run_review.extract_metadata", return_value={}) as m_meta,
            mock.patch("run_review.extract_text_from_output") as m_text,
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)
            return {"popen": m_popen, "meta": m_meta, "text": m_text}

    def test_extract_metadata_intercepted(self):
        mocks = self._run_and_check()
        mocks["meta"].assert_called()

    def test_extract_text_intercepted(self):
        mocks = self._run_and_check()
        mocks["text"].assert_called()

    def test_build_cmd_intercepted(self):
        sentinel_cmd = ["echo", "test"]
        mock_build = mock.Mock(return_value=sentinel_cmd)
        from ppr_providers import PROVIDERS as _PROVIDERS
        with (
            mock.patch.dict(_PROVIDERS["claude"], {"build_cmd": mock_build}),
            mock.patch("run_review.subprocess.Popen", return_value=self._proc()),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            args = make_args(
                reviewer="claude",
                prompt_file=str(self.prompt_file),
                output_file=str(Path(self.tmpdir.name) / "out.json"),
                session_file=str(Path(self.tmpdir.name) / "session.json"),
                events_file=str(Path(self.tmpdir.name) / "events.jsonl"),
            )
            run_review.run_review(args)
            mock_build.assert_called_once()


class TestStructuredReviewParsing(unittest.TestCase):
    """Tests for parse_structured_review() — section-scoped finding extraction."""

    def test_finding_with_confidence_section_recommendation(self):
        text = """\
### Reasoning
Some analysis here with [B1] mentioned in passing.

### Blocking Issues
- [B1] (HIGH) Race condition in migration step
  Section: Step 3 — Database migration (lines 42-55)
  Recommendation: Add dependency gate between steps 2 and 3

### Non-Blocking Issues
- [N1] Monitoring gap
  Section: Step 7 — Post-deploy (line 95)
  Recommendation: Add health checks

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 2)
        b1 = findings[0]
        self.assertEqual(b1["id"], "B1")
        self.assertEqual(b1["severity"], "blocking")
        self.assertEqual(b1["confidence"], "HIGH")
        self.assertIn("Race condition", b1["description"])
        self.assertEqual(b1["section"], "Step 3 — Database migration")
        self.assertEqual(b1["lines"], "42-55")
        self.assertEqual(b1["recommendation"], "Add dependency gate between steps 2 and 3")
        n1 = findings[1]
        self.assertEqual(n1["id"], "N1")
        self.assertEqual(n1["severity"], "non_blocking")

    def test_finding_without_confidence(self):
        text = """\
### Blocking Issues
- [B1] Missing rollback strategy

### Non-Blocking Issues
None

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "B1")
        self.assertIsNone(findings[0]["confidence"])

    def test_non_blocking_severity(self):
        text = """\
### Blocking Issues
None

### Non-Blocking Issues
- [N1] Consider adding smoke test
  Recommendation: Add post-deploy verification

VERDICT: APPROVED
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "non_blocking")
        self.assertEqual(findings[0]["recommendation"], "Add post-deploy verification")

    def test_plain_text_returns_empty(self):
        text = "This is just plain text review.\n\nVERDICT: REVISE\n"
        findings = parse_structured_review(text)
        self.assertEqual(findings, [])

    def test_markdown_bold_tags(self):
        text = """\
### Blocking Issues
- **[B1]** (MEDIUM) Bold-tagged finding
  Section: Step 1 (lines 1-5)

### Non-Blocking Issues
None

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "B1")
        self.assertEqual(findings[0]["confidence"], "MEDIUM")

    def test_multi_finding_across_sections(self):
        text = """\
### Reasoning
Analysis...

### Blocking Issues
- [B1] (HIGH) First blocker
  Section: Step 1 (lines 1-10)
- [B2] (MEDIUM) Second blocker
  Section: Step 2 (lines 20-30)

### Non-Blocking Issues
- [N1] First suggestion
- [N2] Second suggestion

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 4)
        ids = [f["id"] for f in findings]
        self.assertEqual(ids, ["B1", "B2", "N1", "N2"])

    def test_reasoning_section_contamination(self):
        """[B1] in ### Reasoning must NOT produce a false positive."""
        text = """\
### Reasoning
The plan mentions [B1] rollback but I disagree with the approach.

### Blocking Issues
None

### Non-Blocking Issues
None

VERDICT: APPROVED
"""
        findings = parse_structured_review(text)
        self.assertEqual(findings, [])

    def test_multiline_spacing(self):
        """Findings separated by blank lines with varying indent."""
        text = """\
### Blocking Issues
- [B1] (HIGH) First issue
  Section: Step 1 (lines 1-5)
  Recommendation: Fix it

- [B2] (LOW) Second issue
  Section: Step 2 (lines 10-15)
  Recommendation: Also fix

### Non-Blocking Issues
None

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["recommendation"], "Fix it")
        self.assertEqual(findings[1]["recommendation"], "Also fix")

    def test_section_heading_trailing_whitespace(self):
        """Section heading with trailing spaces should still match."""
        text = "### Blocking Issues   \n- [B1] (HIGH) Found an issue\n\n### Non-Blocking Issues\nNone\n\nVERDICT: REVISE\n"
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "B1")


class TestProviderRegistry(unittest.TestCase):
    """PROVIDERS is the single source of truth for all provider plumbing."""

    def test_get_provider_returns_entry(self):
        from ppr_providers import get_provider
        codex = get_provider("codex")
        self.assertEqual(codex["binary"], "codex")
        self.assertTrue(codex["resume_supported"])
        with self.assertRaises(KeyError):
            get_provider("nonexistent")

    def test_all_providers_have_required_keys(self):
        from ppr_providers import PROVIDERS
        required = {
            "binary", "effort_map", "effort_default", "model_aliases",
            "resume_supported", "build_cmd", "caps",
        }
        for name, p in PROVIDERS.items():
            self.assertTrue(required.issubset(p.keys()), f"{name} missing keys")
            self.assertTrue(callable(p["build_cmd"]))


class TestSessionDurability(unittest.TestCase):
    """save_session must be atomic — partial writes must not clobber the target."""

    def test_save_session_atomic_rename(self):
        from ppr_io import save_session
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "session.json"
            target.write_text(json.dumps({"round": 1, "session_id": "abc"}))
            save_session(str(target), {"round": 2, "session_id": "def"})
            self.assertEqual(json.loads(target.read_text())["round"], 2)
            self.assertFalse((Path(tmpdir) / "session.json.tmp").exists())

    def test_save_session_failure_preserves_target(self):
        from ppr_io import save_session
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "session.json"
            target.write_text(json.dumps({"round": 1}))
            with mock.patch("ppr_io.json.dump", side_effect=OSError("disk full")):
                save_session(str(target), {"round": 2})
            self.assertEqual(json.loads(target.read_text())["round"], 1)
            self.assertFalse((Path(tmpdir) / "session.json.tmp").exists())


class TestSummaryFile(unittest.TestCase):
    """write_summary emits machine-readable per-round summary JSON."""

    def test_summary_with_findings(self):
        from ppr_io import write_summary
        with tempfile.TemporaryDirectory() as tmpdir:
            review = Path(tmpdir) / "review.md"
            review.write_text(
                "### Blocking Issues\n"
                "- [B1] (HIGH) problem one\n"
                "- [B2] (MEDIUM) problem two\n\n"
                "### Non-Blocking Issues\n"
                "- [N1] nit\n\n"
                "VERDICT: REVISE\n"
            )
            summary = Path(tmpdir) / "summary.json"
            write_summary(
                str(summary),
                str(review),
                {"reviewer": "codex", "model": "gpt-5.4", "effort": "medium", "round": 2},
            )
            data = json.loads(summary.read_text())
            self.assertEqual(data["verdict"], "REVISE")
            self.assertEqual(data["reviewer"], "codex")
            self.assertEqual(data["finding_count"], 3)
            self.assertEqual(data["blocking_count"], 2)

    def test_summary_missing_output_file(self):
        from ppr_io import write_summary
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.json"
            write_summary(str(summary), str(Path(tmpdir) / "nope.md"), {"reviewer": "claude"})
            data = json.loads(summary.read_text())
            self.assertIsNone(data["verdict"])
            self.assertEqual(data["finding_count"], 0)

    def test_summary_none_path_is_noop(self):
        from ppr_io import write_summary
        write_summary(None, None, {})  # must not raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
