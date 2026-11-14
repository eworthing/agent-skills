import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cr_completion import (
    completion_error,
    inbox_completion_error,
    matching_reports,
    previous_run_is_active,
)


def report(**overrides):
    value = {
        "report_id": "run-a",
        "run_id": "run-a",
        "parent_session_id": "session-a",
        "scope_id": "scope-a",
        "requested_target": "HEAD~1..HEAD",
        "terminal_status": "complete",
        "terminal_outcome": "complete",
        "model": {"provider_id": "opencode", "id": "review-model", "variant": "max"},
        "partial": False,
        "truncated": False,
        "findings": [
            {
                "file": "README.md",
                "summary": "missing guard",
                "failure_scenario": "the missing guard admits invalid input",
            }
        ],
        "diagnostics": [],
        "generated_at": "2026-11-14T12:00:00.000Z",
        "files_changed": ["README.md"],
        "stats": {
            "finders": 1,
            "candidates": 1,
            "verifierAgents": 1,
            "verified": 1,
            "refuted": 0,
            "dupes": 0,
            "budgetDropped": 0,
            "reported": 1,
        },
    }
    value.update(overrides)
    if "stats" not in overrides:
        value["stats"]["reported"] = len(value["findings"])
    return value


class CompletionValidationTests(unittest.TestCase):
    def test_complete_empty_and_file_level_findings_are_accepted(self):
        self.assertIsNone(completion_error(report(), "session-a", "HEAD~1..HEAD"))
        self.assertIsNone(completion_error(report(findings=[]), "session-a", "HEAD~1..HEAD"))

    def test_actual_harness_accepts_complete_empty_inbox_with_terminal_artifact(self):
        self.assertIsNone(
            inbox_completion_error(
                report(findings=[]), "session-a", "HEAD~1..HEAD", "command_returned", []
            )
        )
        self.assertIsNone(
            inbox_completion_error(
                report(findings=[]), "session-a", "HEAD~1..HEAD", "command_error", []
            )
        )
        self.assertIn(
            "has not settled",
            inbox_completion_error(report(findings=[]), "session-a", "HEAD~1..HEAD", "running", []),
        )

    def test_wrong_session_target_and_non_array_findings_fail(self):
        self.assertIn("not associated", completion_error(report(), "session-b", "HEAD~1..HEAD"))
        self.assertIn("not associated", completion_error(report(), "session-a", "HEAD~2..HEAD"))
        self.assertIn(
            "not an array", completion_error(report(findings={}), "session-a", "HEAD~1..HEAD")
        )

    def test_partial_failed_truncated_and_malformed_findings_fail(self):
        self.assertIn(
            "partial", completion_error(report(partial=True), "session-a", "HEAD~1..HEAD")
        )
        self.assertIn(
            "status",
            completion_error(report(terminal_status="failed"), "session-a", "HEAD~1..HEAD"),
        )
        self.assertIn(
            "truncated", completion_error(report(truncated=True), "session-a", "HEAD~1..HEAD")
        )
        self.assertIn(
            "truncated", completion_error(report(truncated_from=30), "session-a", "HEAD~1..HEAD")
        )
        self.assertIn(
            "finding 0", completion_error(report(findings=[{}]), "session-a", "HEAD~1..HEAD")
        )
        self.assertIn(
            "statistics",
            completion_error(report(stats={}), "session-a", "HEAD~1..HEAD"),
        )

    def test_harness_retains_ownership_until_the_command_or_parent_session_settles(self):
        self.assertTrue(previous_run_is_active(None, "running"))
        self.assertTrue(previous_run_is_active(None, "command_error"))
        self.assertFalse(previous_run_is_active(None, "command_returned"))
        self.assertFalse(previous_run_is_active("succeeded", "command_error"))
        self.assertTrue(
            previous_run_is_active(None, "command_returned", "incomplete", "finder_fallback")
        )
        self.assertFalse(
            previous_run_is_active(None, "command_returned", "failed", "provider_error")
        )

    def test_harness_rejects_inbox_artifact_mismatch(self):
        mismatched = [{"file": "README.md", "summary": "other", "failure_scenario": "bad"}]
        self.assertIn(
            "do not match",
            inbox_completion_error(
                report(), "session-a", "HEAD~1..HEAD", "command_returned", mismatched
            ),
        )

    def test_driver_selects_only_the_requested_session_and_target(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "a.json").write_text(json.dumps(report()), encoding="utf-8")
            (directory / "b.json").write_text(
                json.dumps(report(run_id="run-b", parent_session_id="session-b")), encoding="utf-8"
            )
            matches = matching_reports(directory, "session-a", "HEAD~1..HEAD")
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0][1]["run_id"], "run-a")
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[1] / "scripts" / "cr_completion.py"),
                    "--directory",
                    temp,
                    "--session-id",
                    "session-a",
                    "--target",
                    "HEAD~1..HEAD",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
