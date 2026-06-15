"""cli validators tests — relocated verbatim from test_run_quorum.py (mechanical split)."""
import argparse, json, os, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from ._helpers import *  # noqa: F401,F403


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


class TestPathResolution(unittest.TestCase):
    """Test 31: run_review.py path resolution."""

    def test_resolve_finds_local_run_review(self):
        from run_quorum import _resolve_run_review
        path = _resolve_run_review()
        self.assertTrue(Path(path).exists(), f"Resolved path does not exist: {path}")
        self.assertTrue(path.endswith("run_review.py"))
        # Must resolve within quorum-review/scripts/, not peer-plan-review
        self.assertIn("quorum-review", path)


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
