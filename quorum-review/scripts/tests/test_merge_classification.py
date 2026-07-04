"""merge classification tests — relocated verbatim from test_run_quorum.py (mechanical split)."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ._helpers import *


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
        right = _make_issue(
            "BLK-002", "blocking", 1, 2, "B2", "Refactor database pool", anchor=anchor
        )
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
                    _make_issue(
                        "BLK-001", "blocking", 1, 1, "B1", "Add auth middleware", anchor=anchor
                    ),
                    _make_issue(
                        "BLK-002", "blocking", 1, 2, "B2", "Refactor database pool", anchor=anchor
                    ),
                ],
                "merges": [],
                "rounds": {
                    "1": {
                        "reviewer_count": 2,
                        "blocking_open": 2,
                        "nb_open": 0,
                        "approved_count": 0,
                    }
                },
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
            "rounds": {
                "1": {"reviewer_count": 2, "blocking_open": 1, "nb_open": 1, "approved_count": 0}
            },
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
                    _make_issue(
                        "NB-001", "non_blocking", 1, 2, "N1", "Missing auth on admin routes"
                    ),
                ],
                "merges": [],
                "rounds": {
                    "1": {
                        "reviewer_count": 2,
                        "blocking_open": 1,
                        "nb_open": 1,
                        "approved_count": 0,
                    }
                },
            }
            result = apply_merge_pipeline(ledger, "xsev01", tmpdir, 1)
            self.assertEqual(result["merged"], [])
            self.assertEqual(ledger["issues"][0]["status"], "open")
            self.assertEqual(ledger["issues"][1]["status"], "open")


class TestDerivedVerdict(unittest.TestCase):
    """Tests for derive_verdict()."""

    def test_derive_verdict_no_surviving_blockers(self):
        """APPROVED when no blockers survive threshold."""
        ledger = {
            "issues": [
                make_issue("BLK-001", "Minor concern", support_count=1),
            ],
            "next_blk_id": 2,
            "next_nb_id": 1,
            "merges": [],
            "rounds": {},
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
            "next_blk_id": 3,
            "next_nb_id": 2,
            "merges": [],
            "rounds": {},
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
            "next_blk_id": 2,
            "next_nb_id": 1,
            "merges": [],
            "rounds": {},
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
            "next_blk_id": 2,
            "next_nb_id": 1,
            "merges": [],
            "rounds": {},
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
            "next_blk_id": 2,
            "next_nb_id": 2,
            "merges": [],
            "rounds": {},
        }
        output = format_issue_consensus(ledger, "super", 3)
        self.assertIn("BLK-001", output)
        self.assertIn("SURVIVES", output)
        self.assertIn("NB-001", output)
        self.assertIn("NON-BLOCKING", output)
        self.assertIn("Derived Verdict: REVISE", output)


class TestDeriveVerdictSkipsInvalidated(unittest.TestCase):
    """derive_verdict must ignore issues with status='invalidated_by_verifier'."""

    def test_derive_verdict_skips_invalidated(self):
        ledger = {
            "next_blk_id": 3,
            "next_nb_id": 1,
            "issues": [
                make_issue(
                    "BLK-001", "Was invalidated", status="invalidated_by_verifier", support_count=3
                ),
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
        source_issue["verification"]["verification_rationale"] = (
            "Anchor does not support the claim."
        )
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
