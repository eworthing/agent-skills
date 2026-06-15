"""verification tests — relocated verbatim from test_run_quorum.py (mechanical split)."""
import argparse, json, os, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from ._helpers import *  # noqa: F401,F403


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
