"""parsing reviews tests — relocated verbatim from test_run_quorum.py (mechanical split)."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ._helpers import *


class TestStructuredReviewParsing(unittest.TestCase):
    """Tests for parse_structured_review()."""

    def _write_review(self, text):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write(text)
        f.flush()
        f.close()
        return f.name

    def test_parse_structured_blocking_issues(self):
        path = self._write_review(
            "### Blocking Issues\n"
            "- [B1] No auth on admin endpoint\n"
            "- [B2] SQL injection in search query\n\n"
            "### Non-Blocking Issues\n"
            "None\n\n"
            "### Confidence\nHIGH\n\n"
            "### Scope\nsecurity, API design\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(len(result["blocking"]), 2)
        self.assertEqual(result["blocking"][0]["id"], "B1")
        self.assertIn("auth", result["blocking"][0]["text"])
        self.assertEqual(result["blocking"][1]["id"], "B2")
        self.assertTrue(result["structured"])
        os.unlink(path)

    def test_parse_structured_non_blocking(self):
        path = self._write_review(
            "### Blocking Issues\nNone\n\n"
            "### Non-Blocking Issues\n"
            "- [N1] Consider adding pagination\n"
            "- [N2] Variable naming could be clearer\n\n"
            "### Confidence\nMEDIUM\n\n"
            "VERDICT: APPROVED\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(len(result["non_blocking"]), 2)
        self.assertEqual(result["non_blocking"][0]["id"], "N1")
        self.assertEqual(result["non_blocking"][1]["id"], "N2")
        os.unlink(path)

    def test_parse_confidence_levels(self):
        for level in ["HIGH", "MEDIUM", "LOW"]:
            path = self._write_review(f"### Confidence\n{level}\n\nVERDICT: APPROVED\n")
            result = parse_structured_review(path)
            self.assertEqual(result["confidence"], level)
            os.unlink(path)

    def test_parse_confidence_case_insensitive(self):
        path = self._write_review("### Confidence\nhigh\n\nVERDICT: APPROVED\n")
        result = parse_structured_review(path)
        self.assertEqual(result["confidence"], "HIGH")
        os.unlink(path)

    def test_parse_scope(self):
        path = self._write_review(
            "### Scope\narchitecture, security, testing\n\nVERDICT: APPROVED\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(result["scope"], ["architecture", "security", "testing"])
        os.unlink(path)

    def test_parse_unstructured_fallback(self):
        path = self._write_review(
            "This is a free-form review without sections.\n"
            "I think the plan looks good overall.\n\n"
            "VERDICT: APPROVED\n"
        )
        result = parse_structured_review(path)
        self.assertFalse(result["structured"])
        self.assertEqual(result["verdict"], "APPROVED")
        self.assertEqual(len(result["blocking"]), 0)
        self.assertEqual(len(result["non_blocking"]), 0)
        self.assertIsNone(result["confidence"])
        self.assertIn("free-form", result["raw_text"])
        os.unlink(path)

    def test_parse_bold_markdown_blocking_issues(self):
        """Reviewers sometimes wrap issue tags in bold markdown: **[B1] (HIGH)**."""
        path = self._write_review(
            "### Reasoning\nAnalysis here.\n\n"
            "### Blocking Issues\n"
            "- **[B1] (HIGH)** No auth on admin endpoint\n"
            "- **[B2] (MEDIUM)** SQL injection in search query\n\n"
            "### Non-Blocking Issues\n"
            "- **[N1]** Consider adding pagination\n\n"
            "### Confidence\nHIGH\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(len(result["blocking"]), 2)
        self.assertEqual(result["blocking"][0]["id"], "B1")
        self.assertEqual(result["blocking"][0]["confidence"], "HIGH")
        self.assertEqual(result["blocking"][1]["id"], "B2")
        self.assertEqual(result["blocking"][1]["confidence"], "MEDIUM")
        self.assertEqual(len(result["non_blocking"]), 1)
        self.assertEqual(result["non_blocking"][0]["id"], "N1")
        self.assertTrue(result["structured"])
        os.unlink(path)

    def test_parse_partial_bold_markdown(self):
        """Bold on the tag but not the description."""
        path = self._write_review(
            "### Blocking Issues\n"
            "- **[B1]** No auth on admin endpoint\n"
            "- [B2] (HIGH) SQL injection in search query\n\n"
            "### Non-Blocking Issues\nNone\n\n"
            "### Confidence\nHIGH\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(len(result["blocking"]), 2)
        self.assertEqual(result["blocking"][0]["id"], "B1")
        self.assertEqual(result["blocking"][1]["id"], "B2")
        os.unlink(path)

    def test_parse_issues_without_leading_dash(self):
        """Issues without a leading dash (e.g., from Codex) must still parse."""
        path = self._write_review(
            "### Blocking Issues\n"
            "[B1] (HIGH) Missing authorization check on admin endpoint\n"
            "[B2] SQL injection in search query\n\n"
            "### Non-Blocking Issues\n"
            "[N1] Consider adding request logging\n\n"
            "### Confidence\nHIGH\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(len(result["blocking"]), 2)
        self.assertEqual(result["blocking"][0]["id"], "B1")
        self.assertIn("authorization", result["blocking"][0]["text"])
        self.assertEqual(result["blocking"][1]["id"], "B2")
        self.assertEqual(len(result["non_blocking"]), 1)
        self.assertEqual(result["non_blocking"][0]["id"], "N1")
        os.unlink(path)


class TestCrossCritiqueParsing(unittest.TestCase):
    """Tests for parse_cross_critique()."""

    def _write_review(self, text):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write(text)
        f.flush()
        f.close()
        return f.name

    def test_parse_cross_critique_agree(self):
        path = self._write_review("[AGREE BLK-001]\n[AGREE BLK-002]\n\nVERDICT: REVISE\n")
        result = parse_cross_critique(path)
        self.assertEqual(result["agrees"], ["BLK-001", "BLK-002"])
        os.unlink(path)

    def test_parse_cross_critique_disagree(self):
        path = self._write_review(
            "[DISAGREE BLK-003] This is actually handled by the middleware\n\nVERDICT: APPROVED\n"
        )
        result = parse_cross_critique(path)
        self.assertEqual(len(result["disagrees"]), 1)
        self.assertEqual(result["disagrees"][0]["id"], "BLK-003")
        self.assertIn("middleware", result["disagrees"][0]["reason"])
        os.unlink(path)

    def test_parse_cross_critique_refine(self):
        path = self._write_review(
            "[REFINE NB-001] Should also consider cursor-based pagination\n\nVERDICT: REVISE\n"
        )
        result = parse_cross_critique(path)
        self.assertEqual(len(result["refines"]), 1)
        self.assertEqual(result["refines"][0]["id"], "NB-001")
        self.assertIn("cursor-based", result["refines"][0]["text"])
        os.unlink(path)

    def test_parse_cross_critique_new_issues(self):
        path = self._write_review(
            "[B-NEW] Missing rate limiting on public endpoints\n"
            "[N-NEW] Could add OpenAPI spec generation\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_cross_critique(path)
        self.assertEqual(len(result["new_blocking"]), 1)
        self.assertIn("rate limiting", result["new_blocking"][0])
        self.assertEqual(len(result["new_non_blocking"]), 1)
        self.assertIn("OpenAPI", result["new_non_blocking"][0])
        os.unlink(path)

    def test_parse_cross_critique_mixed(self):
        """Mixed cross-critique with agrees, disagrees, refines, and new issues."""
        path = self._write_review(
            "[AGREE BLK-001]\n"
            "[DISAGREE BLK-002] Not a real issue\n"
            "[REFINE NB-001] Should be more specific\n"
            "[B-NEW] XSS vulnerability in user input\n"
            "[N-NEW] Add logging\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_cross_critique(path)
        self.assertEqual(len(result["agrees"]), 1)
        self.assertEqual(len(result["disagrees"]), 1)
        self.assertEqual(len(result["refines"]), 1)
        self.assertEqual(len(result["new_blocking"]), 1)
        self.assertEqual(len(result["new_non_blocking"]), 1)
        os.unlink(path)


class TestVerdictParsing(unittest.TestCase):
    """Tests 6-10: Verdict parsing from review files."""

    def test_approved_verdict(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Good plan.\n\nVERDICT: APPROVED\n")
            f.flush()
            self.assertEqual(parse_verdict(f.name), "APPROVED")
            os.unlink(f.name)

    def test_revise_verdict(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Needs work.\n\nVERDICT: REVISE\n")
            f.flush()
            self.assertEqual(parse_verdict(f.name), "REVISE")
            os.unlink(f.name)

    def test_no_verdict(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Some review text without a verdict line.\n")
            f.flush()
            self.assertIsNone(parse_verdict(f.name))
            os.unlink(f.name)

    def test_missing_file(self):
        self.assertIsNone(parse_verdict("/nonexistent/review.md"))

    def test_trailing_whitespace(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Review.\n\nVERDICT: APPROVED\n\n\n")
            f.flush()
            self.assertEqual(parse_verdict(f.name), "APPROVED")
            os.unlink(f.name)


class TestTallyVerdicts(unittest.TestCase):
    """Tests 11-17: Verdict tallying with different thresholds."""

    def _make_verdicts(self, verdict_list):
        return [
            (f"Reviewer {chr(65 + i)}", v, f"model-{i + 1}", "medium")
            for i, v in enumerate(verdict_list)
        ]

    def test_unanimous_all_approved(self):
        verdicts = self._make_verdicts(["APPROVED", "APPROVED", "APPROVED"])
        tally = tally_verdicts(verdicts, "unanimous")
        self.assertTrue(tally["threshold_met"])
        self.assertEqual(len(tally["approved"]), 3)

    def test_unanimous_one_revise(self):
        verdicts = self._make_verdicts(["APPROVED", "REVISE", "APPROVED"])
        tally = tally_verdicts(verdicts, "unanimous")
        self.assertFalse(tally["threshold_met"])

    def test_supermajority_one_revise(self):
        verdicts = self._make_verdicts(["APPROVED", "REVISE", "APPROVED"])
        tally = tally_verdicts(verdicts, "super")
        self.assertTrue(tally["threshold_met"])

    def test_majority_threshold(self):
        verdicts = self._make_verdicts(["APPROVED", "REVISE", "APPROVED"])
        tally = tally_verdicts(verdicts, "majority")
        self.assertTrue(tally["threshold_met"])

    def test_majority_fails_with_minority(self):
        verdicts = self._make_verdicts(["APPROVED", "REVISE", "REVISE"])
        tally = tally_verdicts(verdicts, "majority")
        self.assertFalse(tally["threshold_met"])

    def test_four_reviewers_supermajority(self):
        verdicts = self._make_verdicts(["APPROVED", "APPROVED", "APPROVED", "REVISE"])
        tally = tally_verdicts(verdicts, "super")
        self.assertTrue(tally["threshold_met"])

    def test_no_verdict_counted_as_not_approved(self):
        verdicts = self._make_verdicts(["APPROVED", None, "APPROVED"])
        tally = tally_verdicts(verdicts, "unanimous")
        self.assertFalse(tally["threshold_met"])
        self.assertEqual(len(tally["failed"]), 1)


class TestTallySummaryFormat(unittest.TestCase):
    """Test 32: Tally summary output format."""

    def test_summary_contains_key_fields(self):
        verdicts = [
            ("Reviewer A", "APPROVED", "sonnet", "high"),
            ("Reviewer B", "REVISE", "pro", "medium"),
            ("Reviewer C", "APPROVED", "o3", "medium"),
        ]
        tally = tally_verdicts(verdicts, "super")
        self.assertIn("APPROVED: 2/3", tally["summary"])
        self.assertIn("REVISE: 1/3", tally["summary"])
        self.assertIn("supermajority", tally["summary"])
        self.assertIn("advisory", tally["summary"].lower())


class TestThresholdLanguage(unittest.TestCase):
    """Tests for blocker-survival threshold semantics."""

    def test_tally_summary_uses_advisory(self):
        """Tally summary marks itself as advisory."""
        verdicts = [
            ("Reviewer A", "APPROVED", "sonnet", "high"),
            ("Reviewer B", "REVISE", "pro", "medium"),
            ("Reviewer C", "APPROVED", "o3", "medium"),
        ]
        tally = tally_verdicts(verdicts, "super")
        self.assertIn("advisory", tally["summary"].lower())
        self.assertIn("derived verdict", tally["summary"].lower())
