"""features tests — relocated verbatim from test_run_quorum.py (mechanical split)."""
import argparse, json, os, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from ._helpers import *  # noqa: F401,F403


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
