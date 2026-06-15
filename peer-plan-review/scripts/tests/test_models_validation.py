"""models validation tests — relocated verbatim from test_run_review.py (mechanical split)."""
import argparse, json, os, shutil, signal, stat, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from unittest import mock  # noqa: F401
from ._helpers import *  # noqa: F401,F403
from ._helpers import _CREATE_NEW_PROCESS_GROUP  # noqa: F401


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
        # Claude should have fable, sonnet, opus, haiku
        self.assertIn("fable", stdout)
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
