#!/usr/bin/env python3
"""
test_run_quorum.py — Deterministic test suite for run_quorum.py.

Tier 1: Local tests that exercise orchestrator logic (no external CLIs).

Run:  python3 scripts/test_run_quorum.py
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

# Resolve paths relative to this test file
SCRIPT_DIR = str(Path(__file__).resolve().parent)
SCRIPT = str(Path(SCRIPT_DIR) / "run_quorum.py")

# Import functions for direct unit tests
sys.path.insert(0, SCRIPT_DIR)
import run_quorum  # noqa: E402
from run_quorum import (  # noqa: E402
    compile_deliberation,
    parse_reviewer_spec,
    parse_verdict,
    tally_verdicts,
    validate_panel,
    write_deliberation_prompt,
    write_initial_prompt,
)


def run_script(*extra_args):
    """Run run_quorum.py as subprocess, return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT, *list(extra_args)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


class TestReviewerSpecParsing(unittest.TestCase):
    """Tests 1-3: Reviewer spec parsing."""

    def test_parse_provider_and_model(self):
        """Test 1: 'claude:sonnet' parses to ('claude', 'sonnet')."""
        self.assertEqual(parse_reviewer_spec("claude:sonnet"), ("claude", "sonnet"))

    def test_parse_provider_only(self):
        """Test 2: 'codex' parses to ('codex', None)."""
        self.assertEqual(parse_reviewer_spec("codex"), ("codex", None))

    def test_parse_case_insensitive(self):
        """Test 3: 'Claude:Opus' normalizes provider to lowercase."""
        provider, model = parse_reviewer_spec("Claude:Opus")
        self.assertEqual(provider, "claude")
        self.assertEqual(model, "Opus")


class TestPanelValidation(unittest.TestCase):
    """Tests 4-5: Panel validation."""

    def test_minimum_reviewers(self):
        """Test 4: Panel with < 3 reviewers exits with error."""
        with self.assertRaises(SystemExit):
            validate_panel(["claude:sonnet", "gemini:pro"])

    def test_invalid_provider(self):
        """Test 5: Unknown provider exits with error."""
        with self.assertRaises(SystemExit):
            validate_panel(["claude:sonnet", "gemini:pro", "unknown:foo"])


class TestVerdictParsing(unittest.TestCase):
    """Tests 6-9: Verdict parsing from review files."""

    def test_approved_verdict(self):
        """Test 6: Parse VERDICT: APPROVED from review output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Good plan.\n\nVERDICT: APPROVED\n")
            f.flush()
            self.assertEqual(parse_verdict(f.name), "APPROVED")
            os.unlink(f.name)

    def test_revise_verdict(self):
        """Test 7: Parse VERDICT: REVISE from review output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Needs work.\n\nVERDICT: REVISE\n")
            f.flush()
            self.assertEqual(parse_verdict(f.name), "REVISE")
            os.unlink(f.name)

    def test_no_verdict(self):
        """Test 8: Review without verdict returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Some review text without a verdict line.\n")
            f.flush()
            self.assertIsNone(parse_verdict(f.name))
            os.unlink(f.name)

    def test_missing_file(self):
        """Test 9: Missing review file returns None."""
        self.assertIsNone(parse_verdict("/nonexistent/review.md"))

    def test_trailing_whitespace(self):
        """Test 10: Verdict with trailing empty lines still parses."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Review.\n\nVERDICT: APPROVED\n\n\n")
            f.flush()
            self.assertEqual(parse_verdict(f.name), "APPROVED")
            os.unlink(f.name)


class TestTallyVerdicts(unittest.TestCase):
    """Tests 11-14: Verdict tallying with different thresholds."""

    def _make_verdicts(self, verdict_list):
        """Helper: create verdict tuples from a list of verdict strings."""
        return [
            (f"Reviewer {i+1}", v, f"model-{i+1}", "medium")
            for i, v in enumerate(verdict_list)
        ]

    def test_unanimous_all_approved(self):
        """Test 11: Unanimous threshold with all approved."""
        verdicts = self._make_verdicts(["APPROVED", "APPROVED", "APPROVED"])
        tally = tally_verdicts(verdicts, "unanimous")
        self.assertTrue(tally["threshold_met"])
        self.assertEqual(len(tally["approved"]), 3)

    def test_unanimous_one_revise(self):
        """Test 12: Unanimous threshold fails with one REVISE."""
        verdicts = self._make_verdicts(["APPROVED", "REVISE", "APPROVED"])
        tally = tally_verdicts(verdicts, "unanimous")
        self.assertFalse(tally["threshold_met"])

    def test_supermajority_one_revise(self):
        """Test 13: Supermajority threshold passes with one REVISE out of 3."""
        verdicts = self._make_verdicts(["APPROVED", "REVISE", "APPROVED"])
        tally = tally_verdicts(verdicts, "super")
        self.assertTrue(tally["threshold_met"])

    def test_majority_threshold(self):
        """Test 14: Majority threshold with 2/3 approved."""
        verdicts = self._make_verdicts(["APPROVED", "REVISE", "APPROVED"])
        tally = tally_verdicts(verdicts, "majority")
        self.assertTrue(tally["threshold_met"])

    def test_majority_fails_with_minority(self):
        """Test 15: Majority threshold fails with 1/3 approved."""
        verdicts = self._make_verdicts(["APPROVED", "REVISE", "REVISE"])
        tally = tally_verdicts(verdicts, "majority")
        self.assertFalse(tally["threshold_met"])

    def test_four_reviewers_supermajority(self):
        """Test 16: 4-reviewer panel, supermajority requires 3/4."""
        verdicts = self._make_verdicts(["APPROVED", "APPROVED", "APPROVED", "REVISE"])
        tally = tally_verdicts(verdicts, "super")
        self.assertTrue(tally["threshold_met"])

    def test_no_verdict_counted_as_not_approved(self):
        """Test 17: None verdicts are not counted as approvals."""
        verdicts = self._make_verdicts(["APPROVED", None, "APPROVED"])
        tally = tally_verdicts(verdicts, "unanimous")
        self.assertFalse(tally["threshold_met"])
        self.assertEqual(len(tally["failed"]), 1)


class TestPromptGeneration(unittest.TestCase):
    """Tests 18-19: Prompt file generation."""

    def test_initial_prompt_contains_plan(self):
        """Test 18: Round 1 prompt includes plan text and panel context."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_initial_prompt(
                f.name, 1, 3, "## Review Contract\nTest contract.", "# My Plan\nDo stuff."
            )
            content = Path(f.name).read_text()
            self.assertIn("# My Plan", content)
            self.assertIn("reviewer 1 of 3", content)
            self.assertIn("Review Contract", content)
            os.unlink(f.name)

    def test_deliberation_prompt_contains_prior_reviews(self):
        """Test 19: Round 2+ prompt includes deliberation context."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_deliberation_prompt(
                f.name,
                2,
                3,
                2,
                "## Review Contract\nTest.",
                "--- Reviewer 1 --- VERDICT: REVISE ---\nFix X.\n--- Reviewer 2 ---",
                "- Fixed X per Reviewer 1",
                "# Updated Plan\nFixed stuff.",
            )
            content = Path(f.name).read_text()
            self.assertIn("Reviewer 1", content)
            self.assertIn("Fix X", content)
            self.assertIn("Fixed X per Reviewer 1", content)
            self.assertIn("# Updated Plan", content)
            self.assertIn("round 2", content)
            os.unlink(f.name)


class TestDeliberationCompilation(unittest.TestCase):
    """Tests 20-21: Deliberation context compilation."""

    def test_compile_reviews(self):
        """Test 20: compile_deliberation assembles labeled reviews."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "test1234"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            # Write mock review files
            for idx, (prov, model) in enumerate(panel, 1):
                review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
                review_file.write_text(f"Review from {prov}.\n\nVERDICT: APPROVED\n")

                session_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json"
                session_file.write_text(json.dumps({
                    "model": model or "default-model",
                    "effort": "medium",
                }))

            delib_text, verdicts = compile_deliberation(panel, quorum_id, tmpdir, 1)

            self.assertIn("Reviewer 1 (claude:sonnet)", delib_text)
            self.assertIn("Reviewer 2 (gemini:pro)", delib_text)
            self.assertIn("Review from claude", delib_text)
            self.assertEqual(len(verdicts), 3)
            self.assertTrue(all(v[1] == "APPROVED" for v in verdicts))

    def test_compile_missing_review(self):
        """Test 21: Missing review file produces empty text and None verdict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "test5678"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
            # Don't create any files
            delib_text, verdicts = compile_deliberation(panel, quorum_id, tmpdir, 1)
            self.assertEqual(len(verdicts), 3)
            self.assertTrue(all(v[1] is None for v in verdicts))


class TestCLIValidation(unittest.TestCase):
    """Tests 22-23: CLI argument validation."""

    def test_too_few_reviewers(self):
        """Test 22: Script exits non-zero with < 3 reviewers."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as plan:
            plan.write(b"test plan")
            plan.flush()
            rc, stdout, stderr = run_script(
                "--reviewers", "claude:sonnet,gemini:pro",
                "--plan-file", plan.name,
                "--quorum-id", "abc",
                "--round", "1",
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("at least 3", stderr)
            os.unlink(plan.name)

    def test_invalid_provider_cli(self):
        """Test 23: Script exits non-zero with invalid provider."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as plan:
            plan.write(b"test plan")
            plan.flush()
            rc, stdout, stderr = run_script(
                "--reviewers", "claude:sonnet,gemini:pro,bogus:foo",
                "--plan-file", plan.name,
                "--quorum-id", "abc",
                "--round", "1",
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("unknown provider", stderr)
            os.unlink(plan.name)


class TestTallySummaryFormat(unittest.TestCase):
    """Test 24: Tally summary output format."""

    def test_summary_contains_key_fields(self):
        """Test 24: Tally summary includes all expected sections."""
        verdicts = [
            ("Reviewer 1 (claude:sonnet)", "APPROVED", "sonnet", "high"),
            ("Reviewer 2 (gemini:pro)", "REVISE", "pro", "medium"),
            ("Reviewer 3 (codex)", "APPROVED", "o3", "medium"),
        ]
        tally = tally_verdicts(verdicts, "super")
        self.assertIn("APPROVED: 2/3", tally["summary"])
        self.assertIn("REVISE: 1/3", tally["summary"])
        self.assertIn("supermajority", tally["summary"])
        self.assertIn("CONSENSUS REACHED", tally["summary"])


if __name__ == "__main__":
    unittest.main()
