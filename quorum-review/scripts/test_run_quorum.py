#!/usr/bin/env python3
"""
test_run_quorum.py — Deterministic test suite for run_quorum.py (v3).

Tier 1: Local tests that exercise orchestrator logic (no external CLIs).

Run:  python3 scripts/test_run_quorum.py
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Resolve paths relative to this test file
SCRIPT_DIR = str(Path(__file__).resolve().parent)
SCRIPT = str(Path(SCRIPT_DIR) / "run_quorum.py")

# Import functions for direct unit tests
sys.path.insert(0, SCRIPT_DIR)
import run_quorum  # noqa: E402
import run_review  # noqa: E402
from run_quorum import (  # noqa: E402
    _make_issue,
    _role_for_mode,
    CROSS_CRITIQUE_INSTRUCTIONS,
    EXIT_APPROVED,
    EXIT_INDETERMINATE,
    EXIT_REVISE,
    MAX_ROUNDS_LIMIT,
    MIN_QUORUM_SIZE,
    REVIEW_CONTRACT_V2,
    apply_merge_pipeline,
    classify_merge_candidate,
    generate_merge_candidates,
    _extract_section,
    _is_unanimous,
    build_issue_ledger,
    compile_compressed_context,
    compile_deliberation,
    derive_verdict,
    format_issue_consensus,
    format_ledger_summary,
    generate_verification_prompts,
    load_ledger,
    load_review_md,
    parse_args,
    parse_cross_critique,
    parse_reviewer_spec,
    parse_structured_review,
    parse_verdict,
    parse_verification_response,
    save_ledger,
    should_exit_early,
    tally_verdicts,
    validate_panel,
    write_cross_critique_prompt,
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


def make_issue(
    issue_id,
    summary,
    *,
    severity="blocking",
    status="open",
    support_count=1,
    dispute_count=0,
    verification_status="pending",
    anchor=None,
):
    """Build a v3-style issue record for tests."""
    issue = run_quorum._make_issue(
        issue_id,
        severity,
        1,
        1,
        issue_id,
        summary,
        anchor=anchor,
    )
    issue["status"] = status
    issue["adjudication"]["status"] = status
    issue["adjudication"]["proposed_by"] = [1]
    issue["adjudication"]["endorsed_by"] = list(range(2, support_count + 1))
    issue["adjudication"]["refined_by"] = []
    issue["adjudication"]["disputed_by"] = list(range(100, 100 + dispute_count))
    if status == "invalidated_by_verifier" and verification_status == "pending":
        verification_status = "invalidated"
    issue["verification"]["status"] = verification_status
    if verification_status == "invalidated":
        issue["status"] = "invalidated_by_verifier"
        issue["adjudication"]["status"] = "invalidated_by_verifier"
    return run_quorum._sync_issue_aliases(issue)


# ===========================================================================
# Original v1 tests (updated for v2 interface changes)
# ===========================================================================


class TestReviewerSpecParsing(unittest.TestCase):
    """Tests 1-3: Reviewer spec parsing."""

    def test_parse_provider_and_model(self):
        self.assertEqual(parse_reviewer_spec("claude:sonnet"), ("claude", "sonnet"))

    def test_parse_provider_only(self):
        self.assertEqual(parse_reviewer_spec("codex"), ("codex", None))

    def test_parse_case_insensitive(self):
        provider, model = parse_reviewer_spec("Claude:Opus")
        self.assertEqual(provider, "claude")
        self.assertEqual(model, "Opus")


class TestPanelValidation(unittest.TestCase):
    """Tests 4-5: Panel validation."""

    def test_minimum_reviewers(self):
        with self.assertRaises(SystemExit):
            validate_panel(["claude:sonnet", "gemini:pro"])

    def test_invalid_provider(self):
        with self.assertRaises(SystemExit):
            validate_panel(["claude:sonnet", "gemini:pro", "unknown:foo"])


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
            (f"Reviewer {chr(65 + i)}", v, f"model-{i+1}", "medium")
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
        verdicts = self._make_verdicts(
            ["APPROVED", "APPROVED", "APPROVED", "REVISE"]
        )
        tally = tally_verdicts(verdicts, "super")
        self.assertTrue(tally["threshold_met"])

    def test_no_verdict_counted_as_not_approved(self):
        verdicts = self._make_verdicts(["APPROVED", None, "APPROVED"])
        tally = tally_verdicts(verdicts, "unanimous")
        self.assertFalse(tally["threshold_met"])
        self.assertEqual(len(tally["failed"]), 1)


class TestPromptGeneration(unittest.TestCase):
    """Tests 18-19: Prompt file generation."""

    def test_initial_prompt_contains_plan(self):
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_deliberation_prompt(
                f.name,
                2,
                3,
                2,
                "## Review Contract\nTest.",
                "--- Reviewer A --- VERDICT: REVISE ---\nFix X.\n--- Reviewer B ---",
                "- Fixed X per Reviewer A",
                "# Updated Plan\nFixed stuff.",
            )
            content = Path(f.name).read_text()
            self.assertIn("Reviewer A", content)
            self.assertIn("Fix X", content)
            self.assertIn("Fixed X per Reviewer A", content)
            self.assertIn("# Updated Plan", content)
            self.assertIn("round 2", content)
            os.unlink(f.name)


class TestDeliberationCompilation(unittest.TestCase):
    """Tests 20-21: Deliberation context compilation (now anonymous)."""

    def test_compile_reviews_are_anonymous(self):
        """compile_deliberation produces anonymous labels (Reviewer A/B/C)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "test1234"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            for idx, (prov, model) in enumerate(panel, 1):
                review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
                review_file.write_text(f"Review from {prov}.\n\nVERDICT: APPROVED\n")

                session_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json"
                session_file.write_text(json.dumps({
                    "model": model or "default-model",
                    "effort": "medium",
                }))

            delib_text, verdicts, reviewer_map = compile_deliberation(
                panel, quorum_id, tmpdir, 1
            )

            # Verify anonymous labels
            self.assertIn("Reviewer A", delib_text)
            self.assertIn("Reviewer B", delib_text)
            self.assertIn("Reviewer C", delib_text)

            # Verify NO provider/model info in deliberation text
            self.assertNotIn("claude:sonnet", delib_text)
            self.assertNotIn("gemini:pro", delib_text)
            self.assertNotIn("model:", delib_text)
            self.assertNotIn("effort:", delib_text)

            # Verify reviewer_map has true identities
            self.assertEqual(reviewer_map["Reviewer A"]["provider"], "claude")
            self.assertEqual(reviewer_map["Reviewer B"]["provider"], "gemini")
            self.assertEqual(reviewer_map["Reviewer C"]["provider"], "codex")

            self.assertEqual(len(verdicts), 3)
            self.assertTrue(all(v[1] == "APPROVED" for v in verdicts))

    def test_compile_missing_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "test5678"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
            _delib_text, verdicts, _reviewer_map = compile_deliberation(
                panel, quorum_id, tmpdir, 1
            )
            self.assertEqual(len(verdicts), 3)
            self.assertTrue(all(v[1] is None for v in verdicts))


class TestCLIValidation(unittest.TestCase):
    """Tests 22-23: CLI argument validation."""

    def test_too_few_reviewers(self):
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


class TestSameProviderDifferentModels(unittest.TestCase):
    """Tests 25-26: Same provider with different models."""

    def test_same_provider_three_models(self):
        panel = validate_panel(["claude:sonnet", "claude:opus", "claude:haiku"])
        self.assertEqual(len(panel), 3)
        self.assertTrue(all(p[0] == "claude" for p in panel))
        self.assertEqual([p[1] for p in panel], ["sonnet", "opus", "haiku"])

    def test_mixed_same_and_different_providers(self):
        panel = validate_panel(["claude:sonnet", "claude:opus", "gemini:pro"])
        self.assertEqual(len(panel), 3)


class TestPlanFileValidation(unittest.TestCase):
    """Tests 27-28: Plan file validation via CLI."""

    def test_missing_plan_file_cli(self):
        rc, stdout, stderr = run_script(
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/nonexistent/plan.md",
            "--quorum-id", "abc",
            "--round", "1",
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("--plan-file", stderr)

    def test_invalid_effort_cli(self):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as plan:
            plan.write(b"test plan")
            plan.flush()
            rc, stdout, stderr = run_script(
                "--reviewers", "claude:sonnet,gemini:pro,codex",
                "--plan-file", plan.name,
                "--quorum-id", "abc",
                "--round", "1",
                "--effort", "extreme",
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("invalid choice", stderr)
            os.unlink(plan.name)


class TestPromptFormatting(unittest.TestCase):
    """Tests 29-30: Prompt output has correct markdown formatting."""

    def test_initial_prompt_no_indentation(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_initial_prompt(
                f.name, 1, 3, "## Review Contract\nTest.", "# My Plan\nStuff."
            )
            content = Path(f.name).read_text()
            for line in content.splitlines():
                if line.startswith("##"):
                    self.assertFalse(line.startswith("    "),
                                     f"Header is indented: {line!r}")
            os.unlink(f.name)

    def test_deliberation_prompt_no_indentation(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_deliberation_prompt(
                f.name, 1, 3, 2,
                "## Review Contract\nTest.",
                "--- R1 ---\nFeedback.",
                "- Fixed things",
                "# Plan\nUpdated.",
            )
            content = Path(f.name).read_text()
            for line in content.splitlines():
                if line.startswith("##"):
                    self.assertFalse(line.startswith("    "),
                                     f"Header is indented: {line!r}")
            os.unlink(f.name)


class TestPathResolution(unittest.TestCase):
    """Test 31: run_review.py path resolution."""

    def test_resolve_finds_local_run_review(self):
        from run_quorum import _resolve_run_review
        path = _resolve_run_review()
        self.assertTrue(Path(path).exists(), f"Resolved path does not exist: {path}")
        self.assertTrue(path.endswith("run_review.py"))
        # Must resolve within quorum-review/scripts/, not peer-plan-review
        self.assertIn("quorum-review", path)


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


# ===========================================================================
# v2 tests: Structured review parsing
# ===========================================================================


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
            path = self._write_review(
                f"### Confidence\n{level}\n\nVERDICT: APPROVED\n"
            )
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


# ===========================================================================
# v2 tests: Cross-critique parsing
# ===========================================================================


class TestCrossCritiqueParsing(unittest.TestCase):
    """Tests for parse_cross_critique()."""

    def _write_review(self, text):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write(text)
        f.flush()
        f.close()
        return f.name

    def test_parse_cross_critique_agree(self):
        path = self._write_review(
            "[AGREE BLK-001]\n"
            "[AGREE BLK-002]\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_cross_critique(path)
        self.assertEqual(result["agrees"], ["BLK-001", "BLK-002"])
        os.unlink(path)

    def test_parse_cross_critique_disagree(self):
        path = self._write_review(
            "[DISAGREE BLK-003] This is actually handled by the middleware\n\n"
            "VERDICT: APPROVED\n"
        )
        result = parse_cross_critique(path)
        self.assertEqual(len(result["disagrees"]), 1)
        self.assertEqual(result["disagrees"][0]["id"], "BLK-003")
        self.assertIn("middleware", result["disagrees"][0]["reason"])
        os.unlink(path)

    def test_parse_cross_critique_refine(self):
        path = self._write_review(
            "[REFINE NB-001] Should also consider cursor-based pagination\n\n"
            "VERDICT: REVISE\n"
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


# ===========================================================================
# v2 tests: Issue ledger
# ===========================================================================


class TestIssueLedger(unittest.TestCase):
    """Tests for issue ledger operations."""

    def test_canonical_id_assignment(self):
        """BLK-001, BLK-002, NB-001 are monotonically increasing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "ledger01"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            # Reviewer 1: 2 blocking, 1 non-blocking
            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "### Blocking Issues\n"
                "- [B1] Issue one\n"
                "- [B2] Issue two\n"
                "### Non-Blocking Issues\n"
                "- [N1] Suggestion one\n\n"
                "VERDICT: REVISE\n"
            )
            # Reviewer 2: 1 blocking
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "### Blocking Issues\n"
                "- [B1] Issue three\n"
                "### Non-Blocking Issues\nNone\n\n"
                "VERDICT: REVISE\n"
            )
            # Reviewer 3: no structured issues
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "Looks good.\n\nVERDICT: APPROVED\n"
            )

            ledger = build_issue_ledger(panel, quorum_id, tmpdir, 1)

            # Should have BLK-001, BLK-002, BLK-003 (from reviewers 1 and 2)
            blk_ids = [i["id"] for i in ledger["issues"] if i["severity"] == "blocking"]
            self.assertEqual(blk_ids, ["BLK-001", "BLK-002", "BLK-003"])

            # Should have NB-001
            nb_ids = [i["id"] for i in ledger["issues"] if i["severity"] == "non_blocking"]
            self.assertEqual(nb_ids, ["NB-001"])

            # Next IDs should be correct
            self.assertEqual(ledger["next_blk_id"], 4)
            self.assertEqual(ledger["next_nb_id"], 2)

    def test_ledger_agreement_from_critique(self):
        """Cross-critique AGREE/DISAGREE updates support/dispute counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "ledger02"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            # Start with a round 1 ledger
            ledger = {
                "next_blk_id": 3,
                "next_nb_id": 1,
                "issues": [
                    {
                        "id": "BLK-001",
                        "source_reviewer": 1,
                        "source_label": "B1",
                        "round_introduced": 1,
                        "severity": "blocking",
                        "text": "No auth on admin",
                        "status": "open",
                        "resolved_round": None,
                        "merged_from": [],
                        "proposed_by": 1,
                        "endorsed_by": [],
                        "refined_by": [],
                        "disputed_by": [],
                        "support_count": 1,
                        "dispute_count": 0,
                        "owner_summary": "No auth on admin",
                    },
                    {
                        "id": "BLK-002",
                        "source_reviewer": 2,
                        "source_label": "B1",
                        "round_introduced": 1,
                        "severity": "blocking",
                        "text": "SQL injection risk",
                        "status": "open",
                        "resolved_round": None,
                        "merged_from": [],
                        "proposed_by": 2,
                        "endorsed_by": [],
                        "refined_by": [],
                        "disputed_by": [],
                        "support_count": 1,
                        "dispute_count": 0,
                        "owner_summary": "SQL injection risk",
                    },
                ],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 3, "blocking_open": 2,
                                 "nb_open": 0, "approved_count": 1}},
            }

            # Round 2: reviewer 1 agrees with BLK-002, reviewer 2 agrees with BLK-001,
            # reviewer 3 disagrees with BLK-002
            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "[AGREE BLK-002]\n\n"
                "### Blocking Issues\n- [B1] No auth on admin\n\n"
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[AGREE BLK-001]\n\n"
                "### Blocking Issues\n- [B1] SQL injection risk\n\n"
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "[DISAGREE BLK-002] Not exploitable in this context\n\n"
                "VERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)

            blk001 = next(i for i in updated["issues"] if i["id"] == "BLK-001")
            blk002 = next(i for i in updated["issues"] if i["id"] == "BLK-002")

            # BLK-001: proposed by 1, reviewer 2 endorsed
            self.assertEqual(blk001["support_count"], 2)
            self.assertIn(2, blk001["endorsed_by"])

            # BLK-002: proposed by 2, reviewer 1 endorsed, reviewer 3 disputed
            self.assertEqual(blk002["support_count"], 2)
            self.assertEqual(blk002["dispute_count"], 1)
            self.assertIn(3, blk002["disputed_by"])

    def test_ledger_new_issues_from_critique(self):
        """[B-NEW] and [N-NEW] tags create new issues with canonical IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "ledger03"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            ledger = {
                "next_blk_id": 2,
                "next_nb_id": 1,
                "issues": [{
                    "id": "BLK-001", "source_reviewer": 1, "source_label": "B1",
                    "round_introduced": 1, "severity": "blocking",
                    "text": "Existing issue", "status": "open",
                    "resolved_round": None, "merged_from": [],
                    "proposed_by": 1, "endorsed_by": [], "refined_by": [],
                    "disputed_by": [],
                    "support_count": 1, "dispute_count": 0,
                    "owner_summary": "Existing issue",
                }],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 3, "blocking_open": 1,
                                 "nb_open": 0, "approved_count": 0}},
            }

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "[AGREE BLK-001]\n"
                "[B-NEW] Missing rate limiting\n"
                "[N-NEW] Add docs\n\n"
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[AGREE BLK-001]\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)

            new_blk = next(
                (i for i in updated["issues"] if i["id"] == "BLK-002"), None
            )
            self.assertIsNotNone(new_blk)
            self.assertIn("rate limiting", new_blk["text"])
            self.assertEqual(new_blk["source_label"], "B-NEW")

            new_nb = next(
                (i for i in updated["issues"] if i["id"] == "NB-001"), None
            )
            self.assertIsNotNone(new_nb)
            self.assertIn("docs", new_nb["text"])

    def test_issue_ledger_round_tracking(self):
        """Round stats are correctly tracked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "ledger04"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "### Blocking Issues\n- [B1] Issue A\n\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "VERDICT: APPROVED\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            ledger = build_issue_ledger(panel, quorum_id, tmpdir, 1)
            self.assertIn("1", ledger["rounds"])
            self.assertEqual(ledger["rounds"]["1"]["reviewer_count"], 3)
            self.assertEqual(ledger["rounds"]["1"]["blocking_open"], 1)
            self.assertEqual(ledger["rounds"]["1"]["approved_count"], 2)

    def test_ledger_load_save_roundtrip(self):
        """Ledger survives JSON serialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = str(Path(tmpdir) / "test-ledger.json")
            ledger = {
                "next_blk_id": 3,
                "next_nb_id": 2,
                "issues": [{
                    "id": "BLK-001", "status": "open", "text": "Test",
                    "severity": "blocking",
                }],
                "merges": [{"survivor": "BLK-001", "absorbed": ["BLK-002"],
                            "round": 2, "reason": "Duplicate"}],
                "rounds": {"1": {"reviewer_count": 3}},
            }
            save_ledger(ledger_file, ledger)
            loaded = load_ledger(ledger_file)
            self.assertEqual(loaded["next_blk_id"], 3)
            self.assertEqual(len(loaded["issues"]), 1)
            self.assertEqual(len(loaded["merges"]), 1)
            self.assertEqual(loaded["merges"][0]["survivor"], "BLK-001")

    def test_ledger_load_missing_file(self):
        """Loading nonexistent file returns empty ledger."""
        ledger = load_ledger("/nonexistent/ledger.json")
        self.assertEqual(ledger["next_blk_id"], 1)
        self.assertEqual(ledger["issues"], [])


# ===========================================================================
# v3 tests: Ledger migration and merge pipeline
# ===========================================================================


class TestLedgerMigrationAndMergePipeline(unittest.TestCase):
    """Tests for v3 ledger migration and deterministic merge behavior."""

    def test_legacy_flat_ledger_migrates_to_nested_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = Path(tmpdir) / "legacy-ledger.json"
            legacy = {
                "next_blk_id": 2,
                "next_nb_id": 1,
                "issues": [
                    {
                        "id": "BLK-001",
                        "source_reviewer": 1,
                        "source_label": "B1",
                        "round_introduced": 1,
                        "severity": "blocking",
                        "status": "open",
                        "text": "No auth on admin routes",
                        "owner_summary": "No auth on admin routes",
                        "proposed_by": 1,
                        "endorsed_by": [2],
                        "refined_by": [],
                        "disputed_by": [],
                        "support_count": 2,
                        "dispute_count": 0,
                        "merged_from": [],
                        "conflict": ["BLK-002"],
                        "anchor": {
                            "path": "src/auth.py",
                            "line_start": 12,
                            "line_end": 18,
                        },
                    },
                ],
                "merges": [
                    {"survivor": "BLK-001", "absorbed": "BLK-002", "round": 1},
                ],
                "rounds": {"1": {"reviewer_count": 3}},
            }
            ledger_file.write_text(json.dumps(legacy), encoding="utf-8")

            loaded = load_ledger(str(ledger_file))
            issue = loaded["issues"][0]

            self.assertEqual(loaded["schema_version"], 3)
            self.assertEqual(loaded["version"], 3)
            self.assertEqual(issue["identity"]["severity"], "blocking")
            self.assertEqual(issue["claim"]["summary"], "No auth on admin routes")
            self.assertEqual(issue["anchor"]["artifact_path"], "src/auth.py")
            self.assertEqual(issue["anchor"]["anchor_kind"], "line_range")
            self.assertEqual(issue["anchor"]["anchor_start"], 12)
            self.assertEqual(issue["relations"]["conflict"], ["BLK-002"])
            self.assertEqual(loaded["merges"][0]["absorbed"], ["BLK-002"])
            self.assertEqual(loaded["merges"][0]["classification"], "EQUIVALENT")

            save_ledger(str(ledger_file), loaded)
            saved = json.loads(ledger_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema_version"], 3)
            self.assertIn("identity", saved["issues"][0])
            self.assertIn("relations", saved["issues"][0])

    def test_classify_merge_candidate_relation_only_outcomes(self):
        anchor = {
            "artifact_path": "src/app.py",
            "anchor_kind": "line_range",
            "anchor_start": 10,
            "anchor_end": 14,
        }
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1", "Add auth middleware", anchor=anchor)
        conflict = _make_issue("BLK-002", "blocking", 1, 2, "B2", "Remove auth middleware", anchor=anchor)
        related = _make_issue("BLK-003", "blocking", 1, 3, "B3", "Add rate limiting to endpoint", anchor=anchor)

        classification, reason = classify_merge_candidate(left, conflict)
        self.assertEqual(classification, "CONFLICT")
        self.assertIn("opposing actions", reason)

        classification, reason = classify_merge_candidate(left, related)
        self.assertEqual(classification, "RELATED_DISTINCT")

    def test_classify_high_similarity_anchor_as_equivalent(self):
        """Paraphrased issues on the same anchor merge at >= 0.50 similarity."""
        anchor = {
            "artifact_path": "src/app.py",
            "anchor_kind": "line_range",
            "anchor_start": 10,
            "anchor_end": 14,
        }
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1",
                           "Missing input validation on user registration endpoint", anchor=anchor)
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2",
                            "No input validation for user registration handler", anchor=anchor)
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "EQUIVALENT")
        self.assertIn("high similarity", reason)

    def test_classify_very_high_similarity_no_anchor_as_equivalent(self):
        """Near-identical wording merges even without anchor overlap."""
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1",
                           "SQL injection via string interpolation in login query")
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2",
                            "SQL injection via string interpolation in login query handler")
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "EQUIVALENT")
        self.assertIn("very high", reason)

    def test_classify_high_similarity_conflict_not_equivalent(self):
        """Conflict signal prevents EQUIVALENT even at high similarity."""
        anchor = {
            "artifact_path": "src/app.py",
            "anchor_kind": "line_range",
            "anchor_start": 10,
            "anchor_end": 14,
        }
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1",
                           "Add caching for product catalog", anchor=anchor)
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2",
                            "Remove caching from product catalog", anchor=anchor)
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "CONFLICT")
        self.assertIn("opposing actions", reason)

    def test_apply_merge_pipeline_merges_equivalent_issues_and_appends_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "merge01"

            def make_ledger():
                return {
                    "next_blk_id": 3,
                    "next_nb_id": 2,
                    "issues": [
                        _make_issue("BLK-001", "blocking", 1, 1, "B1", "No auth on admin routes"),
                        _make_issue("BLK-002", "blocking", 1, 2, "B2", "No auth on admin routes"),
                        _make_issue("NB-001", "non_blocking", 1, 3, "N1", "Add logging"),
                    ],
                    "merges": [],
                    "rounds": {"1": {"reviewer_count": 3, "blocking_open": 2, "nb_open": 1, "approved_count": 0}},
                }

            ledger = make_ledger()
            result = apply_merge_pipeline(ledger, quorum_id, tmpdir, 1)

            self.assertEqual(result["merged"], [{"survivor": "BLK-001", "absorbed": ["BLK-002"]}])
            self.assertEqual(len(result["candidates"]), 1)

            survivor = next(issue for issue in ledger["issues"] if issue["id"] == "BLK-001")
            absorbed = next(issue for issue in ledger["issues"] if issue["id"] == "BLK-002")
            self.assertEqual(survivor["status"], "open")
            self.assertEqual(survivor["support_count"], 2)
            self.assertEqual(survivor["merged_from"], ["BLK-002"])
            self.assertEqual(absorbed["status"], "merged")
            self.assertEqual(absorbed["adjudication"]["status"], "merged")

            log_path = Path(result["log_path"])
            first_lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(first_lines), 2)
            self.assertEqual(json.loads(first_lines[0])["action"], "merge_candidate")
            self.assertEqual(json.loads(first_lines[1])["action"], "merge_applied")

            second_ledger = make_ledger()
            apply_merge_pipeline(second_ledger, quorum_id, tmpdir, 2)
            appended_lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(appended_lines), 4)

    def test_apply_merge_pipeline_records_conflict_relations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "merge02"
            anchor = {
                "artifact_path": "src/app.py",
                "anchor_kind": "line_range",
                "anchor_start": 10,
                "anchor_end": 14,
            }
            ledger = {
                "next_blk_id": 3,
                "next_nb_id": 1,
                "issues": [
                    _make_issue("BLK-001", "blocking", 1, 1, "B1", "Add auth middleware", anchor=anchor),
                    _make_issue("BLK-002", "blocking", 1, 2, "B2", "Remove auth middleware", anchor=anchor),
                ],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 3, "blocking_open": 2, "nb_open": 0, "approved_count": 0}},
            }

            result = apply_merge_pipeline(ledger, quorum_id, tmpdir, 1)

            self.assertEqual(result["merged"], [])
            left = next(issue for issue in ledger["issues"] if issue["id"] == "BLK-001")
            right = next(issue for issue in ledger["issues"] if issue["id"] == "BLK-002")
            self.assertEqual(left["relations"]["conflicts_with"], ["BLK-002"])
            self.assertEqual(right["relations"]["conflicts_with"], ["BLK-001"])
            self.assertEqual(left["status"], "open")
            self.assertEqual(right["status"], "open")
            self.assertEqual(left["support_count"], 1)
            self.assertEqual(right["support_count"], 1)


# ===========================================================================
# v2 tests: Derived verdict
# ===========================================================================


class TestDerivedVerdict(unittest.TestCase):
    """Tests for derive_verdict()."""

    def test_derive_verdict_no_surviving_blockers(self):
        """APPROVED when no blockers survive threshold."""
        ledger = {
            "issues": [
                make_issue("BLK-001", "Minor concern", support_count=1),
            ],
            "next_blk_id": 2, "next_nb_id": 1, "merges": [], "rounds": {},
        }
        # supermajority of 3 requires 2 — support_count=1 doesn't survive
        verdict, surviving, dropped = derive_verdict(ledger, "super", 3)
        self.assertEqual(verdict, "APPROVED")
        self.assertEqual(len(surviving), 0)
        self.assertEqual(len(dropped), 1)

    def test_derive_verdict_surviving_blockers(self):
        """REVISE when blockers survive, regardless of advisory verdicts."""
        ledger = {
            "issues": [
                make_issue("BLK-001", "Auth missing", support_count=2),
                make_issue("BLK-002", "Minor", support_count=1),
                make_issue("NB-001", "Nice to have", severity="non_blocking", support_count=3),
            ],
            "next_blk_id": 3, "next_nb_id": 2, "merges": [], "rounds": {},
        }
        # supermajority of 3 requires 2 — BLK-001 survives, BLK-002 doesn't
        verdict, surviving, dropped = derive_verdict(ledger, "super", 3)
        self.assertEqual(verdict, "REVISE")
        self.assertEqual(len(surviving), 1)
        self.assertEqual(surviving[0]["id"], "BLK-001")
        self.assertEqual(len(dropped), 1)

    def test_derive_verdict_resolved_ignored(self):
        """Resolved issues don't affect verdict."""
        ledger = {
            "issues": [
                make_issue("BLK-001", "Fixed now", status="resolved", support_count=3),
            ],
            "next_blk_id": 2, "next_nb_id": 1, "merges": [], "rounds": {},
        }
        verdict, surviving, dropped = derive_verdict(ledger, "super", 3)
        self.assertEqual(verdict, "APPROVED")
        self.assertEqual(len(surviving), 0)

    def test_derive_verdict_unanimous_requires_all(self):
        """Unanimous threshold requires all reviewers to support."""
        ledger = {
            "issues": [
                make_issue("BLK-001", "Issue", support_count=2),
            ],
            "next_blk_id": 2, "next_nb_id": 1, "merges": [], "rounds": {},
        }
        # Unanimous of 3 requires 3 — support_count=2 doesn't survive
        verdict, surviving, _dropped = derive_verdict(ledger, "unanimous", 3)
        self.assertEqual(verdict, "APPROVED")

        # But if support is 3/3, it survives
        ledger["issues"][0]["adjudication"]["endorsed_by"] = [2, 3]
        run_quorum._sync_issue_aliases(ledger["issues"][0])
        verdict, surviving, _dropped = derive_verdict(ledger, "unanimous", 3)
        self.assertEqual(verdict, "REVISE")
        self.assertEqual(len(surviving), 1)

    def test_format_issue_consensus(self):
        """format_issue_consensus produces readable output."""
        ledger = {
            "issues": [
                make_issue("BLK-001", "Auth missing", support_count=2),
                make_issue("NB-001", "Add docs", severity="non_blocking", support_count=1),
            ],
            "next_blk_id": 2, "next_nb_id": 2, "merges": [], "rounds": {},
        }
        output = format_issue_consensus(ledger, "super", 3)
        self.assertIn("BLK-001", output)
        self.assertIn("SURVIVES", output)
        self.assertIn("NB-001", output)
        self.assertIn("NON-BLOCKING", output)
        self.assertIn("Derived Verdict: REVISE", output)


# ===========================================================================
# v2 tests: Anonymization
# ===========================================================================


class TestAnonymization(unittest.TestCase):
    """Tests for anonymous deliberation in ALL rounds."""

    def test_anonymize_deliberation_all_rounds(self):
        """ALL deliberation rounds use anonymous labels, no provider/model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "anon01"
            panel = [("claude", "opus"), ("gemini", "pro"), ("codex", None)]

            for idx, (_prov, model) in enumerate(panel, 1):
                review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
                review_file.write_text(f"Review #{idx} looks fine.\n\nVERDICT: APPROVED\n")
                session_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json"
                session_file.write_text(json.dumps({
                    "model": model or "default", "effort": "high",
                }))

            # Test for multiple rounds — always anonymous
            for round_num in [1, 2, 3, 4, 5]:
                delib_text, _, reviewer_map = compile_deliberation(
                    panel, quorum_id, tmpdir, round_num
                )
                # Anonymous labels present
                self.assertIn("Reviewer A", delib_text)
                # No provider/model info in HEADERS (section markers)
                # Note: we check that the section headers don't contain identity info
                for line in delib_text.splitlines():
                    if line.startswith("---"):
                        self.assertNotIn("claude", line)
                        self.assertNotIn("gemini", line)
                        self.assertNotIn("codex", line)
                        self.assertNotIn("opus", line)
                        self.assertNotIn("model:", line)
                        self.assertNotIn("effort:", line)

    def test_reviewer_map_in_tally(self):
        """Tally includes reviewer_map with true identities for final report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "anon02"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            for idx in range(1, 4):
                review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
                review_file.write_text("Good.\n\nVERDICT: APPROVED\n")
                session_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json"
                session_file.write_text(json.dumps({"model": "test", "effort": "med"}))

            _, _, reviewer_map = compile_deliberation(panel, quorum_id, tmpdir, 1)

            self.assertIn("Reviewer A", reviewer_map)
            self.assertEqual(reviewer_map["Reviewer A"]["provider"], "claude")
            self.assertEqual(reviewer_map["Reviewer A"]["idx"], 1)
            self.assertEqual(reviewer_map["Reviewer B"]["provider"], "gemini")
            self.assertEqual(reviewer_map["Reviewer C"]["provider"], "codex")


# ===========================================================================
# v2 tests: Context compression
# ===========================================================================


class TestContextCompression(unittest.TestCase):
    """Tests for compile_compressed_context()."""

    def test_compressed_context_omits_prose(self):
        """Round 3+ context has issue ledger table, not full review prose."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "comp01"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            # Write reviews with some prose
            for idx in range(1, 4):
                (Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md").write_text(
                    "This is a long prose review with many paragraphs.\n"
                    "It talks about architecture and design patterns.\n"
                    "There are several nuanced points here.\n\n"
                    "### Blocking Issues\n"
                    "- [B1] Missing auth\n\n"
                    "### Non-Blocking Issues\n"
                    "- [N1] Add docs\n\n"
                    "VERDICT: REVISE\n"
                )

            ledger = {
                "issues": [{
                    "id": "BLK-001", "severity": "blocking", "status": "open",
                    "owner_summary": "Missing auth", "support_count": 2,
                    "dispute_count": 0,
                }],
                "next_blk_id": 2, "next_nb_id": 1, "merges": [], "rounds": {},
            }

            compressed = compile_compressed_context(
                ledger, panel, quorum_id, tmpdir, 3
            )

            # Should contain issue ledger
            self.assertIn("BLK-001", compressed)
            self.assertIn("Missing auth", compressed)
            self.assertIn("Open Issue Ledger", compressed)

            # Should NOT contain full prose
            self.assertNotIn("long prose review", compressed)
            self.assertNotIn("nuanced points", compressed)

            # Should contain condensed issue lists per reviewer
            self.assertIn("Reviewer A", compressed)
            self.assertIn("[B1]", compressed)


# ===========================================================================
# v2 tests: Failure policy
# ===========================================================================


class TestFailurePolicy(unittest.TestCase):
    """Tests for --on-failure modes."""

    def test_fail_closed_policy(self):
        """fail-closed exits non-zero with --on-failure fail-closed (via CLI)."""
        # We can test the parse_args validation here
        from run_quorum import parse_args
        # Just verify the flag is accepted
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
            "--on-failure", "fail-closed",
        ]
        args = parse_args()
        self.assertEqual(args.on_failure, "fail-closed")

    def test_shrink_quorum_is_default(self):
        """shrink-quorum is the default failure policy."""
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
        ]
        args = parse_args()
        self.assertEqual(args.on_failure, "shrink-quorum")

    def test_shrink_quorum_policy(self):
        """shrink-quorum is accepted."""
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
            "--on-failure", "shrink-quorum",
        ]
        args = parse_args()
        self.assertEqual(args.on_failure, "shrink-quorum")

    def test_shrink_quorum_minimum_3(self):
        """shrink-quorum enforces minimum of 3 reviewers."""
        # Test that MIN_QUORUM_SIZE is used as the floor
        self.assertEqual(MIN_QUORUM_SIZE, 3)

    def test_tally_reports_panel_sizes(self):
        """Tally includes original and active panel sizes."""
        verdicts = [
            ("Reviewer A", "APPROVED", "sonnet", "high"),
            ("Reviewer B", "APPROVED", "pro", "medium"),
        ]
        tally = tally_verdicts(
            verdicts, "super",
            original_panel_size=3,
            active_panel_size=2,
        )
        self.assertEqual(tally["original_panel_size"], 3)
        self.assertEqual(tally["active_panel_size"], 2)
        self.assertIn("2 active of 3 original", tally["summary"])


# ===========================================================================
# v2 tests: Default threshold
# ===========================================================================


class TestDefaultThreshold(unittest.TestCase):
    """Test default threshold is supermajority."""

    def test_default_threshold_is_super(self):
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
        ]
        args = parse_args()
        self.assertEqual(args.threshold, "super")


# ===========================================================================
# v2 tests: Cross-critique prompt generation
# ===========================================================================


class TestCrossCritiquePrompt(unittest.TestCase):
    """Tests for write_cross_critique_prompt()."""

    def test_cross_critique_prompt_contains_all_sections(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_cross_critique_prompt(
                f.name,
                1, 3, 2,
                REVIEW_CONTRACT_V2,
                CROSS_CRITIQUE_INSTRUCTIONS,
                "--- Reviewer A ---\nSome review.",
                "- **BLK-001**: Issue [support: 1]",
                "- Fixed problem X",
                "# Updated plan",
            )
            content = Path(f.name).read_text()
            self.assertIn("Cross-Critique Instructions", content)
            self.assertIn("[AGREE BLK-001]", content)
            self.assertIn("[B-NEW]", content)
            self.assertIn("BLK-001", content)
            self.assertIn("Updated plan", content)
            self.assertIn("reviewer 1 of 3", content)
            self.assertIn("anonymous", content.lower())
            os.unlink(f.name)


# ===========================================================================
# v2.1 tests: Split support fields
# ===========================================================================


class TestSplitSupportFields(unittest.TestCase):
    """Tests for proposed_by/endorsed_by/refined_by/disputed_by fields."""

    def test_proposed_by_always_counts_as_support(self):
        """proposed_by reviewer always contributes 1 to support_count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "split01"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "### Blocking Issues\n- [B1] Auth missing\n\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "VERDICT: APPROVED\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            ledger = build_issue_ledger(panel, quorum_id, tmpdir, 1)
            blk001 = ledger["issues"][0]
            self.assertEqual(blk001["proposed_by"], 1)
            self.assertEqual(blk001["support_count"], 1)
            self.assertEqual(blk001["endorsed_by"], [])
            self.assertEqual(blk001["refined_by"], [])

    def test_endorsed_by_from_agree(self):
        """AGREE adds reviewer to endorsed_by and increments support_count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "split02"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            ledger = {
                "next_blk_id": 2, "next_nb_id": 1,
                "issues": [{
                    "id": "BLK-001", "source_reviewer": 1, "source_label": "B1",
                    "round_introduced": 1, "severity": "blocking",
                    "text": "Auth missing", "status": "open",
                    "resolved_round": None, "merged_from": [],
                    "proposed_by": 1, "endorsed_by": [], "refined_by": [],
                    "disputed_by": [],
                    "support_count": 1, "dispute_count": 0,
                    "owner_summary": "Auth missing",
                }],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 3, "blocking_open": 1,
                                 "nb_open": 0, "approved_count": 0}},
            }

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[AGREE BLK-001]\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "[AGREE BLK-001]\nVERDICT: REVISE\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)
            blk001 = updated["issues"][0]
            self.assertEqual(blk001["support_count"], 3)
            self.assertIn(2, blk001["endorsed_by"])
            self.assertIn(3, blk001["endorsed_by"])

    def test_refined_by_from_refine(self):
        """REFINE adds reviewer to refined_by and increments support_count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "split03"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            ledger = {
                "next_blk_id": 2, "next_nb_id": 1,
                "issues": [{
                    "id": "BLK-001", "source_reviewer": 1, "source_label": "B1",
                    "round_introduced": 1, "severity": "blocking",
                    "text": "Auth missing", "status": "open",
                    "resolved_round": None, "merged_from": [],
                    "proposed_by": 1, "endorsed_by": [], "refined_by": [],
                    "disputed_by": [],
                    "support_count": 1, "dispute_count": 0,
                    "owner_summary": "Auth missing",
                }],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 3, "blocking_open": 1,
                                 "nb_open": 0, "approved_count": 0}},
            }

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[REFINE BLK-001] Should use OAuth2 specifically\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)
            blk001 = updated["issues"][0]
            self.assertEqual(blk001["support_count"], 2)
            self.assertIn(2, blk001["refined_by"])

    def test_disputed_by_from_disagree(self):
        """DISAGREE adds reviewer to disputed_by and increments dispute_count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "split04"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            ledger = {
                "next_blk_id": 2, "next_nb_id": 1,
                "issues": [{
                    "id": "BLK-001", "source_reviewer": 1, "source_label": "B1",
                    "round_introduced": 1, "severity": "blocking",
                    "text": "Auth missing", "status": "open",
                    "resolved_round": None, "merged_from": [],
                    "proposed_by": 1, "endorsed_by": [], "refined_by": [],
                    "disputed_by": [],
                    "support_count": 1, "dispute_count": 0,
                    "owner_summary": "Auth missing",
                }],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 3, "blocking_open": 1,
                                 "nb_open": 0, "approved_count": 0}},
            }

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[DISAGREE BLK-001] Already handled by middleware\nVERDICT: APPROVED\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "[DISAGREE BLK-001] Not relevant\nVERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)
            blk001 = updated["issues"][0]
            self.assertEqual(blk001["dispute_count"], 2)
            self.assertIn(2, blk001["disputed_by"])
            self.assertIn(3, blk001["disputed_by"])
            # support_count unchanged — proposer only
            self.assertEqual(blk001["support_count"], 1)


# ===========================================================================
# v2.1 tests: Default changes
# ===========================================================================


class TestDefaultChanges(unittest.TestCase):
    """Tests for shrink-quorum default and 3-round default."""

    def test_default_shrink_quorum(self):
        """Default on-failure is shrink-quorum."""
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
        ]
        args = parse_args()
        self.assertEqual(args.on_failure, "shrink-quorum")

    def test_default_3_rounds(self):
        """Default max-rounds is 3."""
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
        ]
        args = parse_args()
        self.assertEqual(args.max_rounds, 3)

    def test_max_rounds_cap_at_5(self):
        """--max-rounds > 5 is rejected."""
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
            "--max-rounds", "6",
        ]
        with self.assertRaises(SystemExit):
            parse_args()

    def test_max_rounds_5_accepted(self):
        """--max-rounds 5 is accepted."""
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
            "--max-rounds", "5",
        ]
        args = parse_args()
        self.assertEqual(args.max_rounds, 5)


# ===========================================================================
# v2.1 tests: REVIEW.md support
# ===========================================================================


class TestReviewMdSupport(unittest.TestCase):
    """Tests for REVIEW.md rubric file loading."""

    def test_review_md_loaded(self):
        """REVIEW.md content is loaded when present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review_path = Path(tmpdir) / "REVIEW.md"
            review_path.write_text("## Custom Rules\n- Always check security\n")
            content = load_review_md(tmpdir)
            self.assertIn("Custom Rules", content)
            self.assertIn("security", content)

    def test_review_md_missing_ok(self):
        """Missing REVIEW.md returns empty string (not an error)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = load_review_md(tmpdir)
            self.assertEqual(content, "")

    def test_review_md_in_prompt(self):
        """REVIEW.md content appears in initial prompt when provided."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_initial_prompt(
                f.name, 1, 3, REVIEW_CONTRACT_V2, "# My Plan\nDo stuff.",
                rubric_text="## Custom Rules\n- Always check security",
            )
            content = Path(f.name).read_text()
            self.assertIn("Project Review Guidelines", content)
            self.assertIn("Custom Rules", content)
            self.assertIn("security", content)
            os.unlink(f.name)

    def test_review_md_absent_no_section(self):
        """No rubric section when rubric_text is empty."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_initial_prompt(
                f.name, 1, 3, REVIEW_CONTRACT_V2, "# My Plan\nDo stuff.",
                rubric_text="",
            )
            content = Path(f.name).read_text()
            self.assertNotIn("Project Review Guidelines", content)
            os.unlink(f.name)


# ===========================================================================
# v2.1 tests: INDETERMINATE exit code
# ===========================================================================


class TestIndeterminateExitCode(unittest.TestCase):
    """Tests for EXIT_INDETERMINATE when all reviews are unstructured."""

    def test_exit_code_constants(self):
        """Exit code constants are correct."""
        self.assertEqual(EXIT_APPROVED, 0)
        self.assertEqual(EXIT_REVISE, 2)
        self.assertEqual(EXIT_INDETERMINATE, 3)

    def test_parse_status_unstructured_detection(self):
        """Unstructured reviews are detected by parse_structured_review."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Just a plain text review.\n\nVERDICT: APPROVED\n")
            f.flush()
            result = parse_structured_review(f.name)
            self.assertFalse(result["structured"])
            os.unlink(f.name)

    def test_structured_review_detected(self):
        """Structured reviews are detected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "### Blocking Issues\n- [B1] Issue\n\n"
                "### Confidence\nHIGH\n\nVERDICT: REVISE\n"
            )
            f.flush()
            result = parse_structured_review(f.name)
            self.assertTrue(result["structured"])
            os.unlink(f.name)


# ===========================================================================
# v2.1 tests: Per-issue confidence
# ===========================================================================


class TestPerIssueConfidence(unittest.TestCase):
    """Tests for per-issue confidence parsing."""

    def _write_review(self, text):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write(text)
        f.flush()
        f.close()
        return f.name

    def test_parse_per_issue_confidence(self):
        """[B1] (HIGH) format is parsed correctly."""
        path = self._write_review(
            "### Blocking Issues\n"
            "- [B1] (HIGH) No auth on admin endpoint\n"
            "- [B2] (MEDIUM) Missing input validation\n\n"
            "### Confidence\nHIGH\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(len(result["blocking"]), 2)
        self.assertEqual(result["blocking"][0]["confidence"], "HIGH")
        self.assertEqual(result["blocking"][1]["confidence"], "MEDIUM")
        os.unlink(path)

    def test_per_issue_confidence_fallback(self):
        """Issues without per-issue confidence get None (caller uses review-level)."""
        path = self._write_review(
            "### Blocking Issues\n"
            "- [B1] No auth on admin endpoint\n\n"
            "### Confidence\nHIGH\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(len(result["blocking"]), 1)
        self.assertIsNone(result["blocking"][0]["confidence"])
        os.unlink(path)

    def test_per_issue_confidence_case_insensitive(self):
        """Per-issue confidence is case-insensitive."""
        path = self._write_review(
            "### Blocking Issues\n"
            "- [B1] (low) Minor concern\n\n"
            "VERDICT: REVISE\n"
        )
        result = parse_structured_review(path)
        self.assertEqual(result["blocking"][0]["confidence"], "LOW")
        os.unlink(path)

    def test_per_issue_confidence_in_ledger(self):
        """Per-issue confidence is stored in the issue ledger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "conf01"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "### Blocking Issues\n"
                "- [B1] (HIGH) Auth missing\n\n"
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "VERDICT: APPROVED\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            ledger = build_issue_ledger(panel, quorum_id, tmpdir, 1)
            blk001 = ledger["issues"][0]
            self.assertEqual(blk001["confidence"], "HIGH")


# ===========================================================================
# v2.1 tests: Verification stage
# ===========================================================================


class TestVerificationStage(unittest.TestCase):
    """Tests for verification prompt generation and response parsing."""

    def test_verification_prompt_generation(self):
        """Targeted verification prompts for surviving blockers."""
        ledger = {
            "issues": [
                make_issue(
                    "BLK-001",
                    "Auth missing",
                    support_count=2,
                    anchor={
                        "artifact_kind": "plan",
                        "section": "API gateway",
                        "anchor_start": 34,
                        "anchor_end": 40,
                        "raw": "Section: API gateway (lines 34-40)",
                    },
                ),
                make_issue("BLK-002", "Minor", support_count=1),
            ],
            "next_blk_id": 3, "next_nb_id": 1, "merges": [], "rounds": {},
        }
        prompts = generate_verification_prompts(ledger, "# Plan text", "super", 3)
        # Only BLK-001 survives supermajority (2/3), BLK-002 doesn't (1/3)
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["issue_id"], "BLK-001")
        prompt = prompts[0]["prompt"]
        self.assertIn("BLK-001", prompt)
        self.assertIn("Auth missing", prompt)
        self.assertIn("API gateway", prompt)
        self.assertIn("lines 34-40", prompt)
        self.assertIn("VERIFIED", prompt)
        self.assertIn("INVALIDATED", prompt)
        self.assertIn("Plan text", prompt)
        self.assertNotIn("support count", prompt.lower())
        self.assertNotIn("reviewer identities", prompt.lower())
        self.assertNotIn("prior debate", prompt.lower())

    def test_verification_response_parsing_verified(self):
        """Parse VERIFIED responses."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "After reviewing the plan, this is still a concern.\n\n"
                "VERIFIED BLK-001\n\n"
                "The admin routes still lack authentication.\n"
            )
            f.flush()
            results = parse_verification_response(f.name)
            self.assertEqual(results["BLK-001"], "VERIFIED")
            os.unlink(f.name)

    def test_verification_response_parsing_invalidated(self):
        """Parse INVALIDATED responses."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "The revised plan now includes auth middleware.\n\n"
                "INVALIDATED BLK-001\n\n"
                "This has been addressed in the latest revision.\n"
            )
            f.flush()
            results = parse_verification_response(f.name)
            self.assertEqual(results["BLK-001"], "INVALIDATED")
            os.unlink(f.name)

    def test_verification_response_multiple(self):
        """Parse multiple VERIFIED/INVALIDATED in one response."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "VERIFIED BLK-001\nAuth still missing.\n\n"
                "INVALIDATED BLK-002\nFixed in revision.\n"
            )
            f.flush()
            results = parse_verification_response(f.name)
            self.assertEqual(results["BLK-001"], "VERIFIED")
            self.assertEqual(results["BLK-002"], "INVALIDATED")
            os.unlink(f.name)

    def test_skip_verification_flag(self):
        """--skip-verification is accepted."""
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
            "--skip-verification",
        ]
        args = parse_args()
        self.assertTrue(args.skip_verification)


# ===========================================================================
# v2.1 tests: Verifier prompt routing
# ===========================================================================


class TestVerifierPromptRouting(unittest.TestCase):
    """Tests that Claude prompt routing switches for verification prompts."""

    def test_claude_verification_prompt_uses_verifier_system_prompt(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("## Verification Contract\n\n")
            f.flush()
            args = argparse.Namespace(
                prompt_file=f.name,
                resume=False,
                model=None,
                effort=None,
            )
            cmd = run_review.build_claude_cmd(args)
            self.assertIn("--append-system-prompt", cmd)
            prompt = cmd[cmd.index("--append-system-prompt") + 1]
            self.assertIn("independent verifier", prompt)
            self.assertIn("VERIFIED <ID>", prompt)
            self.assertNotIn("VERDICT: APPROVED", prompt)
            os.unlink(f.name)

    def test_claude_verification_mode_flag_overrides_prompt_sniffing(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("## Regular Review\n\n")
            f.flush()
            args = argparse.Namespace(
                prompt_file=f.name,
                resume=False,
                model=None,
                effort=None,
                verification_mode=True,
            )
            cmd = run_review.build_claude_cmd(args)
            prompt = cmd[cmd.index("--append-system-prompt") + 1]
            self.assertIn("independent verifier", prompt)
            self.assertIn("VERIFIED <ID>", prompt)
            os.unlink(f.name)


# ===========================================================================
# v2.1 tests: Threshold language
# ===========================================================================


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


# ===========================================================================
# v2.2 tests: Derive verdict skips invalidated issues
# ===========================================================================


class TestDeriveVerdictSkipsInvalidated(unittest.TestCase):
    """derive_verdict must ignore issues with status='invalidated_by_verifier'."""

    def test_derive_verdict_skips_invalidated(self):
        ledger = {
            "next_blk_id": 3,
            "next_nb_id": 1,
            "issues": [
                make_issue("BLK-001", "Was invalidated", status="invalidated_by_verifier", support_count=3),
                make_issue("BLK-002", "Low support", support_count=1, dispute_count=2),
            ],
            "merges": [],
            "rounds": {},
        }
        verdict, surviving, dropped = derive_verdict(ledger, "super", 3)
        # BLK-001 is invalidated so ignored; BLK-002 has support 1 < super(2/3)
        self.assertEqual(verdict, "APPROVED")
        self.assertEqual(len(surviving), 0)
        # Only BLK-002 is in dropped (open but below threshold)
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0]["id"], "BLK-002")

    def test_derive_verdict_skips_verification_invalidated_status(self):
        ledger = {
            "next_blk_id": 2,
            "next_nb_id": 1,
            "issues": [
                make_issue(
                    "BLK-001",
                    "Was invalidated",
                    support_count=3,
                    verification_status="invalidated",
                ),
            ],
            "merges": [],
            "rounds": {},
        }
        verdict, surviving, dropped = derive_verdict(ledger, "super", 3)
        self.assertEqual(verdict, "APPROVED")
        self.assertEqual(surviving, [])
        self.assertEqual(dropped, [])


class TestVerificationSync(unittest.TestCase):
    """Verification results must sync into verdict snapshots before derivation."""

    def test_sync_verification_state_marks_copy_invalidated(self):
        verdict_ledger = {
            "next_blk_id": 2,
            "next_nb_id": 1,
            "issues": [
                make_issue("BLK-001", "Missing validation", support_count=3),
            ],
            "merges": [],
            "rounds": {},
        }
        source_ledger = json.loads(json.dumps(verdict_ledger))
        source_issue = source_ledger["issues"][0]
        source_issue["verification"]["status"] = "invalidated"
        source_issue["verification"]["verified_by"] = {"provider": "copilot", "model": "gpt-5.4"}
        source_issue["verification"]["verification_rationale"] = "Anchor does not support the claim."
        source_issue["status"] = "invalidated_by_verifier"
        source_issue["adjudication"]["status"] = "invalidated_by_verifier"

        run_quorum._sync_verification_state(verdict_ledger, source_ledger)

        synced_issue = verdict_ledger["issues"][0]
        self.assertEqual(synced_issue["status"], "invalidated_by_verifier")
        self.assertEqual(synced_issue["verification"]["status"], "invalidated")
        self.assertEqual(
            synced_issue["verification"]["verified_by"],
            {"provider": "copilot", "model": "gpt-5.4"},
        )
        verdict, surviving, dropped = derive_verdict(verdict_ledger, "super", 3)
        self.assertEqual(verdict, "APPROVED")
        self.assertEqual(surviving, [])
        self.assertEqual(dropped, [])


# ===========================================================================
# v2.2 tests: _is_unanimous helper
# ===========================================================================


class TestIsUnanimous(unittest.TestCase):
    """Tests for _is_unanimous() helper."""

    def test_is_unanimous_true(self):
        ledger = {
            "issues": [
                make_issue("BLK-001", "Issue", support_count=3),
            ],
        }
        self.assertTrue(_is_unanimous(ledger, "BLK-001", 3))

    def test_is_unanimous_false(self):
        ledger = {
            "issues": [
                make_issue("BLK-001", "Issue", support_count=2),
            ],
        }
        self.assertFalse(_is_unanimous(ledger, "BLK-001", 3))

    def test_is_unanimous_missing_issue(self):
        ledger = {"issues": []}
        self.assertFalse(_is_unanimous(ledger, "BLK-999", 3))


# ===========================================================================
# v2.2 tests: should_exit_early
# ===========================================================================


class TestShouldExitEarly(unittest.TestCase):
    """Tests for should_exit_early() function."""

    def test_should_exit_early_no_blockers(self):
        ledger = {
            "issues": [
                make_issue("NB-001", "Suggestion", severity="non_blocking", support_count=2),
            ],
        }
        should_exit, reason = should_exit_early(ledger, "super", 3)
        self.assertTrue(should_exit)
        self.assertIn("no open blockers", reason)

    def test_should_exit_early_no_surviving(self):
        ledger = {
            "issues": [
                make_issue("BLK-001", "Issue", support_count=1, dispute_count=2),
            ],
        }
        should_exit, reason = should_exit_early(ledger, "super", 3)
        self.assertTrue(should_exit)
        self.assertIn("no blockers meet threshold", reason)

    def test_should_exit_early_max_support(self):
        ledger = {
            "issues": [
                make_issue("BLK-001", "Issue", support_count=3),
            ],
        }
        should_exit, reason = should_exit_early(ledger, "super", 3)
        self.assertTrue(should_exit)
        self.assertIn("maximum support", reason)

    def test_should_exit_early_not_yet(self):
        ledger = {
            "issues": [
                make_issue("BLK-001", "Issue", support_count=2),
            ],
        }
        should_exit, reason = should_exit_early(ledger, "super", 3)
        self.assertFalse(should_exit)
        self.assertEqual(reason, "")


# ===========================================================================
# v2.2 tests: Blind mode
# ===========================================================================


class TestBlindMode(unittest.TestCase):
    """Tests for blind mode in compressed context and ledger summary."""

    def _make_ledger(self):
        return {
            "next_blk_id": 2,
            "next_nb_id": 1,
            "issues": [
                {
                    "id": "BLK-001",
                    "severity": "blocking",
                    "status": "open",
                    "support_count": 2,
                    "dispute_count": 1,
                    "owner_summary": "Missing auth check",
                    "proposed_by": 1,
                    "endorsed_by": [2],
                    "refined_by": [],
                    "disputed_by": [3],
                },
            ],
            "merges": [],
            "rounds": {},
        }

    def test_blind_mode_compressed_context(self):
        """Compressed context omits Support/Disputes columns in blind mode."""
        ledger = self._make_ledger()
        panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal review files so parse_structured_review doesn't fail
            for idx in range(1, 4):
                review_file = Path(tmpdir) / f"qr-test-r{idx}-review.md"
                review_file.write_text("VERDICT: REVISE\n", encoding="utf-8")

            result = compile_compressed_context(
                ledger, panel, "test", tmpdir, 3, blind_mode=True
            )
            self.assertNotIn("Support", result)
            self.assertNotIn("Disputes", result)
            self.assertIn("BLK-001", result)
            self.assertIn("Missing auth check", result)

    def test_blind_mode_ledger_summary(self):
        """Ledger summary omits support/dispute counts in blind mode."""
        ledger = self._make_ledger()
        result = format_ledger_summary(ledger, blind_mode=True)
        self.assertNotIn("support:", result)
        self.assertNotIn("disputes:", result)
        self.assertIn("BLK-001", result)
        self.assertIn("Missing auth check", result)

    def test_normal_mode_shows_counts(self):
        """Default mode still shows support/dispute counts."""
        ledger = self._make_ledger()
        result = format_ledger_summary(ledger, blind_mode=False)
        self.assertIn("support: 2", result)
        self.assertIn("disputes: 1", result)

        # Compressed context too
        panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx in range(1, 4):
                review_file = Path(tmpdir) / f"qr-test-r{idx}-review.md"
                review_file.write_text("VERDICT: REVISE\n", encoding="utf-8")
            result = compile_compressed_context(
                ledger, panel, "test", tmpdir, 3, blind_mode=False
            )
            self.assertIn("Support", result)
            self.assertIn("Disputes", result)


# ===========================================================================
# v2.2 tests: AAD Reasoning section
# ===========================================================================


class TestReasoningSection(unittest.TestCase):
    """Tests for All-Agents Drafting (AAD) reasoning section."""

    def test_review_contract_has_reasoning(self):
        """REVIEW_CONTRACT_V2 includes ### Reasoning before ### Blocking Issues."""
        reasoning_pos = REVIEW_CONTRACT_V2.index("### Reasoning")
        blocking_pos = REVIEW_CONTRACT_V2.index("### Blocking Issues")
        self.assertLess(reasoning_pos, blocking_pos)

    def test_reasoning_not_parsed_as_issues(self):
        """Reasoning prose doesn't create false [B1] matches."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "### Reasoning\n"
                "The architecture looks solid overall. The authentication layer\n"
                "uses JWT tokens correctly. Performance considerations around\n"
                "database indexing should be reviewed.\n\n"
                "### Blocking Issues\n"
                "- [B1] (HIGH) Missing rate limiting on API\n\n"
                "### Non-Blocking Issues\n"
                "None\n\n"
                "### Confidence\n"
                "HIGH\n\n"
                "### Scope\n"
                "architecture, security\n\n"
                "VERDICT: REVISE\n"
            )
            f.flush()
            parsed = parse_structured_review(f.name)
            # Only 1 blocking issue from the actual section, none from reasoning
            self.assertEqual(len(parsed["blocking"]), 1)
            self.assertEqual(parsed["blocking"][0]["text"], "Missing rate limiting on API")
            self.assertTrue(parsed["structured"])
            os.unlink(f.name)

    def test_b_tags_in_reasoning_section_ignored(self):
        """[B1]-style tags in Reasoning section must NOT be parsed as issues."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "### Reasoning\n"
                "I want to flag a few things:\n"
                "- [B1] consider the auth approach carefully\n"
                "- [B2] the database schema needs work\n"
                "- [N1] pagination could be improved\n\n"
                "### Blocking Issues\n"
                "- [B1] (HIGH) SQL injection in user input handler\n\n"
                "### Non-Blocking Issues\n"
                "- [N1] Add request logging\n\n"
                "### Confidence\n"
                "HIGH\n\n"
                "### Scope\n"
                "security\n\n"
                "VERDICT: REVISE\n"
            )
            f.flush()
            parsed = parse_structured_review(f.name)
            # Only 1 blocking issue (from ### Blocking Issues section)
            # The 2 in Reasoning must be ignored
            self.assertEqual(len(parsed["blocking"]), 1)
            self.assertEqual(parsed["blocking"][0]["text"], "SQL injection in user input handler")
            # Only 1 non-blocking (from ### Non-Blocking Issues section)
            self.assertEqual(len(parsed["non_blocking"]), 1)
            self.assertEqual(parsed["non_blocking"][0]["text"], "Add request logging")
            os.unlink(f.name)

    def test_extract_section_helper(self):
        """_extract_section returns only the text under the specified header."""
        text = (
            "### Reasoning\nSome analysis.\n\n"
            "### Blocking Issues\n- [B1] Real issue\n\n"
            "### Non-Blocking Issues\nNone\n"
        )
        blocking = _extract_section(text, "Blocking Issues")
        self.assertIn("[B1] Real issue", blocking)
        self.assertNotIn("Some analysis", blocking)
        self.assertNotIn("Non-Blocking", blocking)

    def test_extract_section_fallback_when_missing(self):
        """_extract_section returns full text when header is not found."""
        text = "No headers here, just text with - [B1] something"
        result = _extract_section(text, "Blocking Issues")
        self.assertEqual(result, text)


# ===========================================================================
# Cross-critique instructions quality
# ===========================================================================


class TestCrossCritiqueInstructions(unittest.TestCase):
    """Tests that cross-critique instructions contain critical elements
    and that the embedded example is parseable by our regex parsers."""

    def test_instructions_require_every_issue_response(self):
        """Instructions must tell reviewers to respond to EVERY open issue."""
        text = CROSS_CRITIQUE_INSTRUCTIONS.lower()
        self.assertIn("every", text)
        # Must warn about consequences of skipping
        self.assertIn("skip", text)

    def test_instructions_clarify_refine_counts_as_support(self):
        """REFINE must be documented as counting toward support."""
        self.assertIn("counts as support", CROSS_CRITIQUE_INSTRUCTIONS)

    def test_instructions_specify_structure_order(self):
        """Instructions must tell reviewers to put cross-critique BEFORE review sections."""
        text = CROSS_CRITIQUE_INSTRUCTIONS
        # "before" must appear in context of ordering
        self.assertIn("BEFORE", text)

    def test_instructions_contain_example(self):
        """Instructions must include a concrete example of expected output."""
        self.assertIn("[AGREE BLK-", CROSS_CRITIQUE_INSTRUCTIONS)
        self.assertIn("[DISAGREE BLK-", CROSS_CRITIQUE_INSTRUCTIONS)
        self.assertIn("[REFINE", CROSS_CRITIQUE_INSTRUCTIONS)
        self.assertIn("VERDICT:", CROSS_CRITIQUE_INSTRUCTIONS)

    def test_embedded_example_is_parseable(self):
        """The example in the instructions must be parseable by our regex parsers."""
        # Extract the example text from between ``` markers
        text = CROSS_CRITIQUE_INSTRUCTIONS
        start = text.index("```\n") + 4
        end = text.index("\n```", start)
        example = text[start:end]

        # Write to temp file for parser functions
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(example)
            f.flush()

            # Cross-critique parser should find AGREE, DISAGREE, REFINE, B-NEW
            critique = parse_cross_critique(f.name)
            self.assertGreater(len(critique["agrees"]), 0, "Example must have AGREE tags")
            self.assertGreater(len(critique["disagrees"]), 0, "Example must have DISAGREE tags")
            self.assertGreater(len(critique["refines"]), 0, "Example must have REFINE tags")
            self.assertGreater(len(critique["new_blocking"]), 0, "Example must have B-NEW tags")

            # Structured review parser should find blocking issues and verdict
            parsed = parse_structured_review(f.name)
            self.assertGreater(len(parsed["blocking"]), 0, "Example must have blocking issues")
            self.assertEqual(parsed["verdict"], "REVISE")
            self.assertTrue(parsed["structured"])

            os.unlink(f.name)

    def test_cross_critique_prompt_contains_all_sections(self):
        """Round 2+ prompt must contain review contract, cross-critique, and all context."""
        ledger = {
            "issues": [
                {"id": "BLK-001", "severity": "blocking", "status": "open",
                 "support_count": 1, "dispute_count": 0,
                 "owner_summary": "Missing auth"},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            write_cross_critique_prompt(
                f.name, 1, 3, 2,
                REVIEW_CONTRACT_V2,
                CROSS_CRITIQUE_INSTRUCTIONS,
                "--- Reviewer A ---\nSome review...",
                format_ledger_summary(ledger),
                "Fixed bug X.",
                "# The Plan\nDo the thing.",
            )
            content = Path(f.name).read_text(encoding="utf-8")

            # Must contain all major section headings in order
            headings = [
                "## Review Contract",
                "## Cross-Critique Instructions",
                "## Panel Context",
                "## Reviews from Previous Round",
                "## Current Issue Ledger",
                "## Changes Since Last Round",
                "## Updated Plan",
            ]
            positions = []
            for heading in headings:
                pos = content.index(heading)
                positions.append(pos)
            # Verify headings appear in order
            self.assertEqual(positions, sorted(positions),
                             f"Section headings must appear in order: {headings}")

            # Must contain the actual issue from the ledger
            self.assertIn("BLK-001", content)
            self.assertIn("Missing auth", content)

            os.unlink(f.name)


# ===========================================================================
# Regression tests: verification call-site signature
# ===========================================================================


class TestVerificationCallSiteSignature(unittest.TestCase):
    """Regression tests ensuring generate_verification_prompts is called
    with the correct 4-argument signature (ledger, plan_text, threshold, total).

    These catch the bug where plan_text was omitted at the call site, causing
    args.threshold to be passed as plan_text and active_panel_size as threshold.
    """

    def test_generate_verification_prompts_requires_plan_text(self):
        """Unit test: plan_text content appears in generated prompts."""
        ledger = {
            "issues": [
                make_issue(
                    "BLK-001",
                    "Security flaw",
                    support_count=2,
                    anchor={
                        "artifact_kind": "plan",
                        "section": "Security",
                        "anchor_start": 12,
                        "anchor_end": 18,
                        "raw": "Section: Security (lines 12-18)",
                    },
                ),
            ],
            "next_blk_id": 2, "next_nb_id": 1, "merges": [], "rounds": {},
        }
        plan_text = "## My Specific Plan\nDeploy auth middleware to /admin."
        prompts = generate_verification_prompts(ledger, plan_text, "super", 3)
        self.assertEqual(len(prompts), 1)
        self.assertIn("BLK-001", prompts[0]["issue_id"])
        # Plan text must be embedded in the prompt
        self.assertIn("Security", prompts[0]["prompt"])
        self.assertIn("My Specific Plan", prompts[0]["prompt"])
        self.assertIn("auth middleware", prompts[0]["prompt"])
        self.assertNotIn("support count", prompts[0]["prompt"].lower())

    def test_generate_verification_prompts_wrong_arity_raises(self):
        """Calling with 3 args (the old bug) must raise TypeError."""
        ledger = {
            "issues": [
                {"id": "BLK-001", "severity": "blocking", "status": "open",
                 "support_count": 2, "owner_summary": "Issue"},
            ],
            "next_blk_id": 2, "next_nb_id": 1, "merges": [], "rounds": {},
        }
        with self.assertRaises(TypeError):
            generate_verification_prompts(ledger, "super", 3)

    def test_main_verification_path_no_type_error(self):
        """Integration test: main() verification branch doesn't raise TypeError.

        Seeds round-1 output with a surviving blocker, monkeypatches
        run_single_reviewer to write a canned verification response, and
        confirms no TypeError at the call site.
        """
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create plan file
            plan_file = os.path.join(tmpdir, "plan.md")
            Path(plan_file).write_text(
                "# Test Plan\nImplement feature X.", encoding="utf-8"
            )

            # Create a ledger with a surviving blocker (support=2, super threshold, total=3)
            ledger = {
                "next_blk_id": 2,
                "next_nb_id": 1,
                "issues": [
                    make_issue(
                        "BLK-001",
                        "Missing input validation",
                        support_count=2,
                        anchor={
                            "artifact_kind": "plan",
                            "section": "Security",
                            "anchor_start": 12,
                            "anchor_end": 18,
                            "raw": "Section: Security (lines 12-18)",
                        },
                    ),
                ],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 3, "active_reviewers": [1, 2, 3]}},
            }
            ledger_file = os.path.join(tmpdir, "qr-test-ledger.json")
            save_ledger(ledger_file, ledger)

            # Create fake round-1 review files (so file reads don't fail)
            for idx in range(1, 4):
                review_file = os.path.join(tmpdir, f"qr-test-r{idx}-review.md")
                Path(review_file).write_text(
                    "### Reasoning\nLooks risky.\n\n"
                    "### Blocking Issues\n"
                    "- [B1] (HIGH) Missing input validation\n\n"
                    "### Non-Blocking Issues\nNone\n\n"
                    "### Confidence\nHIGH\n\n"
                    "### Scope\nsecurity\n\n"
                    "VERDICT: REVISE\n",
                    encoding="utf-8",
                )

            # Track whether run_single_reviewer was called for verification
            verification_calls = []
            verifier_calls = []

            def mock_run_single_reviewer(
                run_review_py, provider, model, plan_file_arg,
                prompt_file, output_file, session_file, events_file,
                effort="high", resume=False, timeout=300, verification_mode=False,
            ):
                # Write a canned VERIFIED response
                Path(output_file).write_text(
                    f"VERIFIED BLK-001\nStill a valid concern.\n",
                    encoding="utf-8",
                )
                verification_calls.append(output_file)
                verifier_calls.append((provider, model, output_file))
                return 0

            # Patch sys.argv for parse_args and run_single_reviewer
            test_argv = [
                "run_quorum.py",
                "--reviewers", "claude:sonnet,gemini:pro,codex",
                "--plan-file", plan_file,
                "--quorum-id", "test",
                "--round", "2",
                "--threshold", "super",
                "--tmpdir", tmpdir,
                "--ledger-file", ledger_file,
                "--sequential",
                "--verifier", "copilot:gpt-5.4",
            ]

            # Create deliberation and changes files expected by round 2
            delib_file = os.path.join(tmpdir, "qr-test-deliberation.md")
            Path(delib_file).write_text("Prior deliberation.", encoding="utf-8")
            test_argv.extend(["--deliberation-file", delib_file])

            changes_file = os.path.join(tmpdir, "qr-test-changes.md")
            Path(changes_file).write_text("- Fixed auth.", encoding="utf-8")
            test_argv.extend(["--changes-summary", changes_file])

            with patch.object(sys, "argv", test_argv), \
                 patch.object(run_quorum, "run_single_reviewer", side_effect=mock_run_single_reviewer):
                try:
                    run_quorum.main()
                except SystemExit:
                    pass  # main() calls sys.exit(); that's expected

            # Verify that the verification path was actually reached
            # (at least one call should be for a verify file)
            verify_calls = [c for c in verification_calls if "verify" in c]
            self.assertGreater(
                len(verify_calls), 0,
                "Verification path was not exercised — test is not covering the bug",
            )
            self.assertTrue(
                any(provider == "copilot" and model == "gpt-5.4" for provider, model, _ in verifier_calls),
                f"Expected explicit verifier copilot:gpt-5.4, saw {verifier_calls}",
            )


# ===========================================================================
# v3 tests: Verifier selection
# ===========================================================================


class TestVerifierSelection(unittest.TestCase):
    """Tests for independent verifier selection."""

    def test_auto_selects_verifier_outside_active_panel(self):
        panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
        verifier = run_quorum.resolve_verifier(panel)
        self.assertNotIn(verifier, panel)

    def test_explicit_verifier_must_be_outside_active_panel(self):
        panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
        with self.assertRaises(SystemExit):
            run_quorum.resolve_verifier(panel, "claude:sonnet")

    def test_auto_select_verifier_fails_when_exhausted(self):
        panel = list(run_quorum.VERIFIER_CANDIDATE_SPECS)
        with self.assertRaises(SystemExit):
            run_quorum.resolve_verifier(panel)


# ===========================================================================
# Integration tests: main() orchestration paths
# ===========================================================================


class TestMainOrchestration(unittest.TestCase):
    """Integration tests exercising main() through full orchestration paths."""

    def _mock_reviewer(self, review_text):
        """Return a mock run_single_reviewer that writes canned review text."""
        def mock_fn(
            run_review_py, provider, model, plan_file_arg,
            prompt_file, output_file, session_file, events_file,
            effort="high", resume=False, timeout=300,
        ):
            Path(output_file).write_text(review_text, encoding="utf-8")
            Path(session_file).write_text(
                json.dumps({"model": model or "default", "effort": effort}),
                encoding="utf-8",
            )
            return 0
        return mock_fn

    def test_round1_all_approved_exits_0(self):
        """Round 1 with all APPROVED reviews → exit code 0 (APPROVED)."""
        from unittest.mock import patch

        review_text = (
            "### Reasoning\nPlan looks solid.\n\n"
            "### Blocking Issues\nNone\n\n"
            "### Non-Blocking Issues\n- [N1] Add logging\n\n"
            "### Confidence\nHIGH\n\n"
            "### Scope\narchitecture\n\n"
            "VERDICT: APPROVED\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = os.path.join(tmpdir, "plan.md")
            Path(plan_file).write_text("# Plan\nDo something.", encoding="utf-8")

            test_argv = [
                "run_quorum.py",
                "--reviewers", "claude:sonnet,gemini:pro,codex",
                "--plan-file", plan_file,
                "--quorum-id", "integ",
                "--round", "1",
                "--tmpdir", tmpdir,
                "--sequential",
            ]

            with patch.object(sys, "argv", test_argv), \
                 patch.object(run_quorum, "run_single_reviewer",
                              side_effect=self._mock_reviewer(review_text)):
                with self.assertRaises(SystemExit) as cm:
                    run_quorum.main()
                self.assertEqual(cm.exception.code, EXIT_APPROVED)

            # Verify tally was written
            tally_file = os.path.join(tmpdir, "qr-integ-tally.json")
            self.assertTrue(Path(tally_file).exists())
            tally = json.loads(Path(tally_file).read_text(encoding="utf-8"))
            self.assertEqual(tally["derived_verdict"], "APPROVED")

    def test_round1_with_blockers_applies_merge_pipeline(self):
        """Round 1 keeps the advisory verdict, but saves the merged ledger."""
        from unittest.mock import patch

        review_text = (
            "### Reasoning\nAuth is missing.\n\n"
            "### Blocking Issues\n"
            "- [B1] (HIGH) No authentication on admin routes\n\n"
            "### Non-Blocking Issues\nNone\n\n"
            "### Confidence\nHIGH\n\n"
            "### Scope\nsecurity\n\n"
            "VERDICT: REVISE\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = os.path.join(tmpdir, "plan.md")
            Path(plan_file).write_text("# Plan\nBuild API.", encoding="utf-8")

            test_argv = [
                "run_quorum.py",
                "--reviewers", "claude:sonnet,gemini:pro,codex",
                "--plan-file", plan_file,
                "--quorum-id", "integ2",
                "--round", "1",
                "--threshold", "majority",
                "--tmpdir", tmpdir,
                "--sequential",
                "--skip-verification",
            ]

            with patch.object(sys, "argv", test_argv), \
                 patch.object(run_quorum, "run_single_reviewer",
                              side_effect=self._mock_reviewer(review_text)):
                with self.assertRaises(SystemExit) as cm:
                    run_quorum.main()
                self.assertEqual(cm.exception.code, EXIT_APPROVED)

            ledger_file = os.path.join(tmpdir, "qr-integ2-ledger.json")
            ledger = json.loads(Path(ledger_file).read_text(encoding="utf-8"))
            blocking = [
                i for i in ledger["issues"]
                if i["severity"] == "blocking" and i["status"] == "open"
            ]
            self.assertEqual(len(blocking), 1)
            self.assertEqual(blocking[0]["support_count"], 3)
            self.assertEqual(blocking[0]["merged_from"], ["BLK-002", "BLK-003"])

            tally_file = os.path.join(tmpdir, "qr-integ2-tally.json")
            tally = json.loads(Path(tally_file).read_text(encoding="utf-8"))
            self.assertEqual(tally["derived_verdict"], "APPROVED")
            self.assertEqual(tally["merged_count"], 2)
            self.assertEqual(tally["merge_candidate_count"], 3)

    def test_round1_unstructured_exits_3(self):
        """Round 1 with all unstructured reviews → exit code 3 (INDETERMINATE)."""
        from unittest.mock import patch

        review_text = "The plan looks fine to me. No major concerns.\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = os.path.join(tmpdir, "plan.md")
            Path(plan_file).write_text("# Plan\nDo thing.", encoding="utf-8")

            test_argv = [
                "run_quorum.py",
                "--reviewers", "claude:sonnet,gemini:pro,codex",
                "--plan-file", plan_file,
                "--quorum-id", "integ3",
                "--round", "1",
                "--tmpdir", tmpdir,
                "--sequential",
            ]

            with patch.object(sys, "argv", test_argv), \
                 patch.object(run_quorum, "run_single_reviewer",
                              side_effect=self._mock_reviewer(review_text)):
                with self.assertRaises(SystemExit) as cm:
                    run_quorum.main()
                self.assertEqual(cm.exception.code, EXIT_INDETERMINATE)


# ===========================================================================
# v2.4 tests: Round 2+ section-scan issue leakage fix
# ===========================================================================


class TestRound2SectionScan(unittest.TestCase):
    """Tests for the section-scan block that catches new issues in standard
    review sections (### Blocking Issues / ### Non-Blocking Issues) without
    [B-NEW]/[N-NEW] tags in rounds 2+."""

    def _base_ledger(self):
        return {
            "next_blk_id": 2,
            "next_nb_id": 1,
            "issues": [{
                "id": "BLK-001", "source_reviewer": 1, "source_label": "B1",
                "round_introduced": 1, "severity": "blocking",
                "text": "Existing auth issue", "status": "open",
                "resolved_round": None, "merged_from": [],
                "proposed_by": 1, "endorsed_by": [], "refined_by": [],
                "disputed_by": [],
                "support_count": 1, "dispute_count": 0,
                "owner_summary": "Existing auth issue",
            }],
            "merges": [],
            "rounds": {"1": {"reviewer_count": 3, "blocking_open": 1,
                             "nb_open": 0, "approved_count": 0}},
        }

    def test_round2_section_scan_catches_untagged_issues(self):
        """New issues in ### Blocking Issues without [B-NEW] tags get registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "scan01"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
            ledger = self._base_ledger()

            # Reviewer 1: agrees with BLK-001, AND raises a new blocking issue
            # in the standard section WITHOUT using [B-NEW]
            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "[AGREE BLK-001]\n\n"
                "### Blocking Issues\n"
                "- [B1] Missing rate limiting on public API\n\n"
                "### Non-Blocking Issues\nNone\n\n"
                "VERDICT: REVISE\n"
            )
            # Reviewer 2: just agrees
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[AGREE BLK-001]\nVERDICT: REVISE\n"
            )
            # Reviewer 3: approves
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)

            # The new issue should have been caught by section-scan
            new_issues = [
                i for i in updated["issues"]
                if i["source_label"] == "section-scan"
            ]
            self.assertEqual(len(new_issues), 1)
            self.assertIn("rate limiting", new_issues[0]["text"])
            self.assertEqual(new_issues[0]["severity"], "blocking")
            self.assertEqual(new_issues[0]["round_introduced"], 2)

    def test_round2_section_scan_dedup(self):
        """Same text via [B-NEW] and standard section → only one entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "scan02"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
            ledger = self._base_ledger()

            # Reviewer 1: uses BOTH [B-NEW] AND puts it in ### Blocking Issues
            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "[AGREE BLK-001]\n"
                "[B-NEW] Missing rate limiting on public API\n\n"
                "### Blocking Issues\n"
                "- [B1] Missing rate limiting on public API\n\n"
                "### Non-Blocking Issues\nNone\n\n"
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[AGREE BLK-001]\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)

            # Count issues about rate limiting — should be exactly 1
            rate_limit_issues = [
                i for i in updated["issues"]
                if "rate limiting" in i["text"].lower()
            ]
            self.assertEqual(len(rate_limit_issues), 1,
                             f"Expected 1 rate-limiting issue, got {len(rate_limit_issues)}: "
                             f"{[i['id'] + ':' + i['source_label'] for i in rate_limit_issues]}")

    def test_round2_section_scan_ignores_existing(self):
        """Standard section issue matching existing ledger entry → not re-added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "scan03"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
            ledger = self._base_ledger()

            # Reviewer 1: restates the existing issue in their blocking section
            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "[AGREE BLK-001]\n\n"
                "### Blocking Issues\n"
                "- [B1] Existing auth issue\n\n"
                "### Non-Blocking Issues\nNone\n\n"
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[AGREE BLK-001]\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)

            # Should still have exactly 1 issue (the original BLK-001)
            self.assertEqual(len(updated["issues"]), 1)
            self.assertEqual(updated["issues"][0]["id"], "BLK-001")

    def test_round2_section_scan_catches_untagged_non_blocking(self):
        """New non-blocking issues in ### Non-Blocking Issues without [N-NEW] get registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "scan04"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
            ledger = self._base_ledger()

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "[AGREE BLK-001]\n\n"
                "### Blocking Issues\nNone\n\n"
                "### Non-Blocking Issues\n"
                "- [N1] Consider adding request logging\n\n"
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[AGREE BLK-001]\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)

            nb_scan = [
                i for i in updated["issues"]
                if i["source_label"] == "section-scan" and i["severity"] == "non_blocking"
            ]
            self.assertEqual(len(nb_scan), 1)
            self.assertIn("request logging", nb_scan[0]["text"])
            self.assertEqual(nb_scan[0]["round_introduced"], 2)


# ===========================================================================
# v3 tests: UNCERTAIN classification
# ===========================================================================


class TestUncertainClassification(unittest.TestCase):
    """UNCERTAIN candidates must be logged but not merged or linked."""

    def test_classify_returns_uncertain_for_low_similarity_same_area(self):
        anchor = {
            "artifact_path": "src/app.py",
            "anchor_kind": "line_range",
            "anchor_start": 10,
            "anchor_end": 14,
        }
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1", "Add auth middleware", anchor=anchor)
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2", "Refactor database pool", anchor=anchor)
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "UNCERTAIN")

    def test_apply_merge_pipeline_leaves_uncertain_untouched(self):
        """UNCERTAIN pairs must not merge, must not create relation links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = {
                "artifact_path": "src/app.py",
                "anchor_kind": "line_range",
                "anchor_start": 10,
                "anchor_end": 14,
            }
            ledger = {
                "next_blk_id": 3,
                "next_nb_id": 1,
                "issues": [
                    _make_issue("BLK-001", "blocking", 1, 1, "B1", "Add auth middleware", anchor=anchor),
                    _make_issue("BLK-002", "blocking", 1, 2, "B2", "Refactor database pool", anchor=anchor),
                ],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 2, "blocking_open": 2, "nb_open": 0, "approved_count": 0}},
            }
            result = apply_merge_pipeline(ledger, "uncertain01", tmpdir, 1)
            self.assertEqual(result["merged"], [])
            left = next(i for i in ledger["issues"] if i["id"] == "BLK-001")
            right = next(i for i in ledger["issues"] if i["id"] == "BLK-002")
            self.assertEqual(left["status"], "open")
            self.assertEqual(right["status"], "open")
            self.assertEqual(left["support_count"], 1)
            self.assertEqual(right["support_count"], 1)
            # UNCERTAIN must NOT create relation links
            self.assertEqual(left["relations"].get("related_distinct", []), [])
            self.assertEqual(left["relations"].get("conflicts_with", []), [])
            self.assertEqual(right["relations"].get("related_distinct", []), [])
            self.assertEqual(right["relations"].get("conflicts_with", []), [])


# ===========================================================================
# v3 tests: Cross-severity merge blocking
# ===========================================================================


class TestCrossSeverityMergeBlocking(unittest.TestCase):
    """Issues of different severity must never form merge candidates."""

    def test_no_candidates_across_severity(self):
        """Blocking and non-blocking issues with identical text must not be candidates."""
        ledger = {
            "next_blk_id": 2,
            "next_nb_id": 2,
            "issues": [
                _make_issue("BLK-001", "blocking", 1, 1, "B1", "Missing auth on admin routes"),
                _make_issue("NB-001", "non_blocking", 1, 2, "N1", "Missing auth on admin routes"),
            ],
            "merges": [],
            "rounds": {"1": {"reviewer_count": 2, "blocking_open": 1, "nb_open": 1, "approved_count": 0}},
        }
        candidates = generate_merge_candidates(ledger)
        self.assertEqual(candidates, [])

    def test_apply_merge_pipeline_no_cross_severity(self):
        """Merge pipeline must not merge issues of different severity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = {
                "next_blk_id": 2,
                "next_nb_id": 2,
                "issues": [
                    _make_issue("BLK-001", "blocking", 1, 1, "B1", "Missing auth on admin routes"),
                    _make_issue("NB-001", "non_blocking", 1, 2, "N1", "Missing auth on admin routes"),
                ],
                "merges": [],
                "rounds": {"1": {"reviewer_count": 2, "blocking_open": 1, "nb_open": 1, "approved_count": 0}},
            }
            result = apply_merge_pipeline(ledger, "xsev01", tmpdir, 1)
            self.assertEqual(result["merged"], [])
            self.assertEqual(ledger["issues"][0]["status"], "open")
            self.assertEqual(ledger["issues"][1]["status"], "open")


# ===========================================================================
# v3 tests: Role pack activation per mode
# ===========================================================================


class TestRolePackActivation(unittest.TestCase):
    """Role packs must vary by mode and cycle across reviewers."""

    def test_plan_mode_uses_plan_roles(self):
        self.assertEqual(_role_for_mode("plan", 1), "Skeptic")
        self.assertEqual(_role_for_mode("plan", 2), "Constraint Guardian")
        self.assertEqual(_role_for_mode("plan", 3), "User Advocate")
        self.assertEqual(_role_for_mode("plan", 4), "Integrator-minded reviewer")

    def test_spec_mode_uses_plan_roles(self):
        self.assertEqual(_role_for_mode("spec", 1), "Skeptic")

    def test_code_mode_uses_code_roles(self):
        self.assertEqual(_role_for_mode("code", 1), "Correctness reviewer")
        self.assertEqual(_role_for_mode("code", 2), "Security reviewer")
        self.assertEqual(_role_for_mode("code", 3), "Maintainability reviewer")
        self.assertEqual(_role_for_mode("code", 4), "Performance/operability reviewer")

    def test_roles_cycle_for_large_panel(self):
        self.assertEqual(_role_for_mode("code", 5), "Correctness reviewer")

    def test_role_label_embedded_in_initial_prompt(self):
        """write_initial_prompt includes the role label in prompt text."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            write_initial_prompt(
                tmp_path,
                reviewer_index=2,
                total_reviewers=3,
                review_contract="## Contract\n",
                plan_text="Some plan.",
                mode="code",
                role_label="Security reviewer",
            )
            content = Path(tmp_path).read_text(encoding="utf-8")
            self.assertIn("Security reviewer", content)
            self.assertIn("Your private role", content)
        finally:
            os.unlink(tmp_path)


# ===========================================================================
# v3 tests: Verifier prompt blindness
# ===========================================================================


class TestVerifierPromptBlindness(unittest.TestCase):
    """Verification prompts must never contain support counts or identities."""

    def test_verification_prompt_excludes_support_fields(self):
        ledger = {
            "issues": [
                make_issue(
                    "BLK-001",
                    "Missing auth",
                    support_count=3,
                    anchor={
                        "artifact_kind": "code_diff",
                        "artifact_path": "src/auth.ts",
                        "anchor_kind": "line_range",
                        "anchor_start": 10,
                        "anchor_end": 20,
                    },
                ),
            ],
            "next_blk_id": 2,
            "next_nb_id": 1,
            "merges": [],
            "rounds": {},
        }
        prompts = generate_verification_prompts(ledger, "# Code diff", "super", 3)
        self.assertEqual(len(prompts), 1)
        prompt_text = prompts[0]["prompt"]
        # Must not contain any support/dispute accounting
        self.assertNotIn("support_count", prompt_text)
        self.assertNotIn("dispute_count", prompt_text)
        self.assertNotIn("proposed_by", prompt_text)
        self.assertNotIn("endorsed_by", prompt_text)
        self.assertNotIn("refined_by", prompt_text)
        self.assertNotIn("disputed_by", prompt_text)
        # Must not contain reviewer identity references
        self.assertNotIn("Reviewer A", prompt_text)
        self.assertNotIn("Reviewer B", prompt_text)
        self.assertNotIn("Reviewer C", prompt_text)
        # Must contain only the expected fields
        self.assertIn("BLK-001", prompt_text)
        self.assertIn("Missing auth", prompt_text)
        self.assertIn("src/auth.ts", prompt_text)
        self.assertIn("Code diff", prompt_text)


if __name__ == "__main__":
    unittest.main()
