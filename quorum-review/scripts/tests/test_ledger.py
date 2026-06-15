"""ledger tests — relocated verbatim from test_run_quorum.py (mechanical split)."""
import argparse, json, os, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from ._helpers import *  # noqa: F401,F403


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
        """Paraphrased issues on the same anchor merge when concern signatures match."""
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
        self.assertIn("signature", reason)

    def test_classify_very_high_similarity_no_anchor_as_equivalent(self):
        """Near-identical wording can merge without anchors when signatures match."""
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1",
                           "SQL injection via string interpolation in login query")
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2",
                            "SQL injection via string interpolation in login query handler")
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "EQUIVALENT")
        self.assertIn("signature", reason)

    def test_classify_distinct_concerns_same_anchor_as_related_distinct(self):
        """Different blockers on the same endpoint must not merge."""
        anchor = {
            "artifact_path": "src/auth.py",
            "anchor_kind": "section",
            "section": "POST /api/auth/login",
        }
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1",
                           "Missing rate limiting on login", anchor=anchor)
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2",
                            "Missing CSRF protection on login", anchor=anchor)
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "RELATED_DISTINCT")
        self.assertIn("same area", reason)

    def test_classify_broad_and_narrow_no_anchor_as_related_distinct(self):
        """A broad blocker must not absorb a narrower blocker without anchors."""
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1",
                           "Missing auth on admin route")
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2",
                            "Missing auth and CSRF protection on admin route")
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "RELATED_DISTINCT")
        self.assertIn("lexically related", reason)

    def test_classify_same_summary_different_section_paths_as_related_distinct(self):
        """Shared tail section names must not collapse distinct section anchors."""
        left = _make_issue(
            "BLK-001",
            "blocking",
            1,
            1,
            "B1",
            "Missing auth guard",
            anchor={"anchor_kind": "section", "section": "Admin Flows > Authentication"},
        )
        right = _make_issue(
            "BLK-002",
            "blocking",
            1,
            2,
            "B2",
            "Missing auth guard",
            anchor={"anchor_kind": "section", "section": "User Flows > Authentication"},
        )
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "RELATED_DISTINCT")
        self.assertIn("different anchors", reason)

    def test_classify_same_summary_different_hunks_as_related_distinct(self):
        """Same file but different hunks must not merge as one blocker."""
        left = _make_issue(
            "BLK-001",
            "blocking",
            1,
            1,
            "B1",
            "Missing auth guard",
            anchor={
                "artifact_kind": "code_diff",
                "artifact_path": "src/routes.ts",
                "anchor_kind": "hunk",
                "anchor_hash": "sha256:hunk-1",
                "raw": "@@ -10,4 +10,5 @@",
            },
        )
        right = _make_issue(
            "BLK-002",
            "blocking",
            1,
            2,
            "B2",
            "Missing auth guard",
            anchor={
                "artifact_kind": "code_diff",
                "artifact_path": "src/routes.ts",
                "anchor_kind": "hunk",
                "anchor_hash": "sha256:hunk-2",
                "raw": "@@ -40,4 +41,5 @@",
            },
        )
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "RELATED_DISTINCT")
        self.assertIn("different anchors", reason)

    def test_classify_same_anchor_hash_distinct_concerns_as_related_distinct(self):
        """Same anchor hash still needs the same concern to merge."""
        anchor = {
            "artifact_kind": "code_diff",
            "artifact_path": "src/routes.ts",
            "anchor_kind": "line_range",
            "anchor_start": 10,
            "anchor_end": 14,
            "anchor_hash": "sha256:same-anchor",
        }
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1",
                           "Missing auth guard on admin route", anchor=anchor)
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2",
                            "Missing input validation on admin route", anchor=anchor)
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "RELATED_DISTINCT")
        self.assertIn("same area", reason)

    def test_classify_same_anchor_hash_conflict_as_conflict(self):
        """Shared anchor hashes must still respect conflict detection."""
        anchor = {
            "artifact_kind": "code_diff",
            "artifact_path": "src/cache.ts",
            "anchor_kind": "line_range",
            "anchor_start": 20,
            "anchor_end": 24,
            "anchor_hash": "sha256:cache-anchor",
        }
        left = _make_issue("BLK-001", "blocking", 1, 1, "B1",
                           "Add caching on product route", anchor=anchor)
        right = _make_issue("BLK-002", "blocking", 1, 2, "B2",
                            "Remove caching on product route", anchor=anchor)
        classification, reason = classify_merge_candidate(left, right)
        self.assertEqual(classification, "CONFLICT")
        self.assertIn("opposing actions", reason)

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
