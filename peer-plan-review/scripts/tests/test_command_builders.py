"""command builders tests — relocated verbatim from test_run_review.py (mechanical split)."""
import argparse, json, os, shutil, signal, stat, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from unittest import mock  # noqa: F401
from ._helpers import *  # noqa: F401,F403
from ._helpers import _CREATE_NEW_PROCESS_GROUP  # noqa: F401


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
            "You are a code reviewer. Read the files the plan references before "
            "judging it — do not rely on the plan text alone. Assess the plan for "
            "correctness, completeness, missing edge cases, and risks. "
            "End with VERDICT: APPROVED or VERDICT: REVISE on the last non-empty line.",
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
