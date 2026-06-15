"""prompts context tests — relocated verbatim from test_run_quorum.py (mechanical split)."""
import argparse, json, os, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from ._helpers import *  # noqa: F401,F403


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
