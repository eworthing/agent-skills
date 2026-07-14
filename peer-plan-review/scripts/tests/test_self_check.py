"""self_check + platform-helper unit tests — moved verbatim from test_execution_paths.py (mechanical split)."""

import argparse
import glob
import io
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

from ._helpers import *
from ._helpers import _CREATE_NEW_PROCESS_GROUP


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

    @mock.patch("run_review.shutil.which", return_value="/fake/opencode")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_opencode_requires_auto_flag(self, mock_run, _mock_which):
        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "run", "--help"],
            0,
            stdout="--format json\n",
            stderr="",
        )

        self.assertFalse(self_check("opencode"))
        self.assertEqual(mock_run.call_args.args[0], ["opencode", "run", "--help"])

    @mock.patch("run_review.shutil.which", return_value="/fake/opencode")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_opencode_accepts_auto_flag(self, mock_run, _mock_which):
        mock_run.return_value = subprocess.CompletedProcess(
            ["opencode", "run", "--help"],
            0,
            stdout="--format json\n--auto\n",
            stderr="",
        )

        self.assertTrue(self_check("opencode"))
        self.assertEqual(mock_run.call_args.args[0], ["opencode", "run", "--help"])


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


class TestPlatformHelpers(unittest.TestCase):
    """Tests for cross-platform process helpers."""

    @mock.patch("_common.process.tree.sys")
    def test_popen_session_kwargs_posix(self, mock_sys):
        mock_sys.platform = "linux"
        result = run_review._popen_session_kwargs()
        self.assertEqual(result, {"start_new_session": True})

    @mock.patch(
        "_common.process.tree.subprocess.CREATE_NEW_PROCESS_GROUP",
        _CREATE_NEW_PROCESS_GROUP,
        create=True,
    )
    @mock.patch("_common.process.tree.sys")
    def test_popen_session_kwargs_windows(self, mock_sys):
        mock_sys.platform = "win32"
        result = run_review._popen_session_kwargs()
        self.assertIn("creationflags", result)
        self.assertEqual(result["creationflags"], _CREATE_NEW_PROCESS_GROUP)

    @mock.patch("_common.process.tree.sys")
    def test_kill_tree_windows_uses_taskkill(self, mock_sys):
        mock_sys.platform = "win32"
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        with mock.patch("_common.process.tree.subprocess.run") as mock_run:
            run_review._kill_tree(mock_proc)
            mock_run.assert_called_once_with(
                ["taskkill", "/T", "/F", "/PID", "12345"],
                capture_output=True,
            )
            mock_proc.wait.assert_called_once()

    @mock.patch("_common.process.tree.sys")
    def test_kill_tree_posix_uses_killpg(self, mock_sys):
        mock_sys.platform = "linux"
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        with (
            mock.patch("_common.process.tree.os.getpgid", return_value=12345),
            mock.patch("_common.process.tree.os.killpg"),
        ):
            run_review._kill_tree(mock_proc)
            mock_proc.wait.assert_called()
