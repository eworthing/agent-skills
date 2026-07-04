"""models validation tests — relocated verbatim from test_run_review.py (mechanical split)."""

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


def run_script_isolated(*extra_args):
    """Like run_script, but with PATH replaced by an empty temp dir.

    --list-models (with no --reviewer) loops every provider, and opencode/agy
    each carry a list_models_cmd that shells out to the real CLI with its own
    15s subprocess timeout. If both happen to be installed-but-slow, the two
    15s waits stack past this suite's outer 30s run_script timeout and
    TimeoutExpired escapes. Emptying PATH makes those lookups fail instantly
    with FileNotFoundError — which run_review.py already catches and turns
    into its fallback line — so the test never depends on, or waits on, real
    third-party CLIs. sys.executable is invoked by absolute path, so running
    python itself doesn't need PATH.
    """
    cmd = [sys.executable, SCRIPT, *list(extra_args)]
    with tempfile.TemporaryDirectory(prefix="ppr-empty-path-") as empty_dir:
        env = os.environ.copy()
        env["PATH"] = empty_dir
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=env,
        )
    return result.returncode, result.stdout, result.stderr


class TestListModels(unittest.TestCase):
    """Tests 1-2: --list-models output."""

    def test_list_models_all_providers(self):
        """Test 1: --list-models prints all providers with correct aliases."""
        rc, stdout, stderr = run_script_isolated("--list-models")
        self.assertEqual(rc, 0, f"stderr: {stderr}")
        for provider in ("claude", "gemini", "codex", "copilot", "opencode"):
            self.assertIn(
                provider, stdout, f"Provider {provider} missing from --list-models output"
            )
        # Claude should have fable, sonnet, opus, haiku
        self.assertIn("fable", stdout)
        self.assertIn("sonnet", stdout)
        self.assertIn("opus", stdout)
        self.assertIn("haiku", stdout)
        # Gemini should have auto, pro, flash, flash-lite
        self.assertIn("flash", stdout)
        self.assertIn("pro", stdout)
        # Codex/copilot have empty model_aliases and no list_models_cmd, so
        # run_review.py prints either the doc-sourced known_models list (if
        # that registry field has been wired into --list-models) or the
        # "raw model IDs only" fallback. Tolerate either wording — assert
        # only on the stable fact that each provider produced *some* line.
        for provider in ("codex", "copilot"):
            line = next((l for l in stdout.splitlines() if l.startswith(f"{provider}:")), "")
            self.assertTrue(line, f"{provider} line missing from --list-models output")
            self.assertTrue(
                "raw model IDs" in line or "gpt-5" in line.lower(),
                f"{provider} line unexpected: {line!r}",
            )

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
