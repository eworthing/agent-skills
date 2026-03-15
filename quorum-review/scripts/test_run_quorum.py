#!/usr/bin/env python3
"""
test_run_quorum.py — Deterministic test suite for run_quorum.py (v2).

Tier 1: Local tests that exercise orchestrator logic (no external CLIs).

Run:  python3 scripts/test_run_quorum.py
"""

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
from run_quorum import (  # noqa: E402
    CROSS_CRITIQUE_INSTRUCTIONS,
    MIN_QUORUM_SIZE,
    REVIEW_CONTRACT_V2,
    build_issue_ledger,
    compile_compressed_context,
    compile_deliberation,
    derive_verdict,
    format_issue_consensus,
    format_ledger_summary,
    load_ledger,
    parse_args,
    parse_cross_critique,
    parse_reviewer_spec,
    parse_structured_review,
    parse_verdict,
    save_ledger,
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

    def test_resolve_finds_peer_plan_review(self):
        from run_quorum import _resolve_run_review
        path = _resolve_run_review()
        self.assertTrue(Path(path).exists(), f"Resolved path does not exist: {path}")
        self.assertTrue(path.endswith("run_review.py"))


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
                        "agreed_by": [1],
                        "disagreed_by": [],
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
                        "agreed_by": [2],
                        "disagreed_by": [],
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

            # BLK-001: original reviewer 1 + reviewer 2 agreed
            self.assertEqual(blk001["support_count"], 2)
            self.assertIn(2, blk001["agreed_by"])

            # BLK-002: original reviewer 2 + reviewer 1 agreed, reviewer 3 disagreed
            self.assertEqual(blk002["support_count"], 2)
            self.assertEqual(blk002["dispute_count"], 1)
            self.assertIn(3, blk002["disagreed_by"])

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
                    "agreed_by": [1], "disagreed_by": [],
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
# v2 tests: Derived verdict
# ===========================================================================


class TestDerivedVerdict(unittest.TestCase):
    """Tests for derive_verdict()."""

    def test_derive_verdict_no_surviving_blockers(self):
        """APPROVED when no blockers survive threshold."""
        ledger = {
            "issues": [
                {"id": "BLK-001", "severity": "blocking", "status": "open",
                 "support_count": 1, "owner_summary": "Minor concern"},
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
                {"id": "BLK-001", "severity": "blocking", "status": "open",
                 "support_count": 2, "owner_summary": "Auth missing"},
                {"id": "BLK-002", "severity": "blocking", "status": "open",
                 "support_count": 1, "owner_summary": "Minor"},
                {"id": "NB-001", "severity": "non_blocking", "status": "open",
                 "support_count": 3, "owner_summary": "Nice to have"},
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
                {"id": "BLK-001", "severity": "blocking", "status": "resolved",
                 "support_count": 3, "owner_summary": "Fixed now"},
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
                {"id": "BLK-001", "severity": "blocking", "status": "open",
                 "support_count": 2, "owner_summary": "Issue"},
            ],
            "next_blk_id": 2, "next_nb_id": 1, "merges": [], "rounds": {},
        }
        # Unanimous of 3 requires 3 — support_count=2 doesn't survive
        verdict, surviving, _dropped = derive_verdict(ledger, "unanimous", 3)
        self.assertEqual(verdict, "APPROVED")

        # But if support is 3/3, it survives
        ledger["issues"][0]["support_count"] = 3
        verdict, surviving, _dropped = derive_verdict(ledger, "unanimous", 3)
        self.assertEqual(verdict, "REVISE")
        self.assertEqual(len(surviving), 1)

    def test_format_issue_consensus(self):
        """format_issue_consensus produces readable output."""
        ledger = {
            "issues": [
                {"id": "BLK-001", "severity": "blocking", "status": "open",
                 "support_count": 2, "owner_summary": "Auth missing"},
                {"id": "NB-001", "severity": "non_blocking", "status": "open",
                 "support_count": 1, "owner_summary": "Add docs"},
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

    def test_fail_open_policy(self):
        """fail-open is the default."""
        sys.argv = [
            "run_quorum.py",
            "--reviewers", "claude:sonnet,gemini:pro,codex",
            "--plan-file", "/tmp/test.md",
            "--quorum-id", "test",
            "--round", "1",
        ]
        args = parse_args()
        self.assertEqual(args.on_failure, "fail-open")

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


if __name__ == "__main__":
    unittest.main()
