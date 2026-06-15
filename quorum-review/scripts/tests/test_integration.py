"""integration tests — relocated verbatim from test_run_quorum.py (mechanical split)."""
import argparse, json, os, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from ._helpers import *  # noqa: F401,F403


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

    def test_round2_dashless_reference_without_sections_is_not_registered(self):
        """Cross-critique references like [B2] must not become section-scan issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "scan03b"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
            ledger = self._base_ledger()

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "[AGREE BLK-001]\n"
                "[B2] See reviewer 1's point — this is already captured.\n\n"
                "VERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r2-review.md").write_text(
                "[AGREE BLK-001]\nVERDICT: REVISE\n"
            )
            (Path(tmpdir) / f"qr-{quorum_id}-r3-review.md").write_text(
                "VERDICT: APPROVED\n"
            )

            updated = build_issue_ledger(panel, quorum_id, tmpdir, 2, ledger)

            self.assertEqual(len(updated["issues"]), 1)
            self.assertEqual(updated["issues"][0]["id"], "BLK-001")

    def test_round2_dashless_issue_inside_explicit_section_is_still_registered(self):
        """Dashless structured items inside a real section still count for section-scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            quorum_id = "scan03c"
            panel = [("claude", "sonnet"), ("gemini", "pro"), ("codex", None)]
            ledger = self._base_ledger()

            (Path(tmpdir) / f"qr-{quorum_id}-r1-review.md").write_text(
                "[AGREE BLK-001]\n\n"
                "### Blocking Issues\n"
                "[B2] Missing rate limiting on public API\n\n"
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
            scan_issues = [
                issue for issue in updated["issues"]
                if issue["source_label"] == "section-scan"
            ]
            self.assertEqual(len(scan_issues), 1)
            self.assertIn("rate limiting", scan_issues[0]["text"].lower())

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


class TestRunReviewAgy(unittest.TestCase):
    """quorum's run_review.py agy path: per-run --log-file conversation-id
    capture (race-free under parallel fan-out) and the read-only preamble."""

    def _agy_args(self, tmp):
        prompt = Path(tmp) / "prompt.md"
        prompt.write_text("Review this plan.\n", encoding="utf-8")
        return argparse.Namespace(
            reviewer="agy", plan_file=None, prompt_file=str(prompt),
            output_file=str(Path(tmp) / "out.txt"),
            session_file=str(Path(tmp) / "session.json"),
            events_file=None, model=None, effort=None, resume=False,
            timeout=600, self_check=False, list_models=False,
            verification_mode=False,
        )

    def test_agy_captures_id_and_prepends_preamble(self):
        from unittest import mock
        import signal
        with tempfile.TemporaryDirectory(prefix="qr-agy-test-") as tmp:
            args = self._agy_args(tmp)
            captured = {}

            def fake_popen(cmd, **kwargs):
                captured["cmd"] = cmd
                for tok in cmd:
                    if tok.startswith("--log-file="):
                        Path(tok.split("=", 1)[1]).write_text(
                            "I0614 printmode.go:155] Print mode: conversation="
                            "dd11dd22-1111-2222-3333-444455556666, sending message\n",
                            encoding="utf-8",
                        )
                proc = mock.MagicMock()

                def communicate(input=None, timeout=None):
                    captured["input"] = input
                    return ("### Blocking Issues\nNone.\n\nVERDICT: APPROVED\n", "")

                proc.communicate.side_effect = communicate
                proc.returncode = 0
                proc.poll.return_value = 0
                return proc

            with (
                mock.patch("run_review.subprocess.Popen", side_effect=fake_popen),
                mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
                mock.patch("run_review.signal.signal"),
            ):
                rc = run_review.run_review(args)

            self.assertEqual(rc, 0)
            self.assertIn("--print", captured["cmd"])
            self.assertIn("--sandbox", captured["cmd"])
            self.assertNotIn("--dangerously-skip-permissions", captured["cmd"])
            self.assertTrue(any(t.startswith("--log-file=") for t in captured["cmd"]))
            self.assertTrue(captured["input"].startswith(run_review.AGY_READONLY_PREAMBLE))
            session = json.loads(Path(args.session_file).read_text(encoding="utf-8"))
            self.assertEqual(session["session_id"], "dd11dd22-1111-2222-3333-444455556666")
            self.assertEqual(session["reviewer"], "agy")
