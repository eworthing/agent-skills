"""file io validation tests — relocated verbatim from test_run_review.py (mechanical split)."""

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

from ._helpers import *
from ._helpers import _CREATE_NEW_PROCESS_GROUP


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


class TestArgContract(unittest.TestCase):
    """Guard that make_args() stays in sync with parse_args() dest names.

    Loop 1 was entirely consumed by a build failure caused by make_args()
    drifting from parse_args() when --codex-home-manifest was added.
    This test derives the ground truth from argparse itself so it cannot
    drift: any new argument added to parse_args() surfaces here immediately.
    """

    def test_make_args_keys_match_parse_args_dests(self):
        """make_args() namespace keys must equal parse_args() dest names."""
        with mock.patch("sys.argv", ["run_review.py"]):
            canonical = set(vars(run_review.parse_args()).keys())
        helper = set(vars(make_args()).keys())
        self.assertEqual(
            canonical,
            helper,
            f"make_args() is out of sync with parse_args().\n"
            f"  Missing from make_args(): {canonical - helper}\n"
            f"  Extra in make_args():     {helper - canonical}",
        )
