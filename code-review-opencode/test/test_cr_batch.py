import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DRIVER = REPO / "scripts" / "cr-batch.sh"


def completion_artifact(**overrides):
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
        "findings": [
            {
                "file": "README.md",
                "line": 2,
                "summary": "missing guard",
                "failure_scenario": "invalid input passes",
                "kind": "correctness",
                "verdict": "CONFIRMED",
            }
        ],
    }
    value.update(overrides)
    if "stats" not in overrides:
        value["stats"]["reported"] = len(value["findings"])
    return value


class BatchDriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.report_dir = root / "reports"
        self.state_dir = root / "state"
        self.bin_dir = root / "bin"
        self.report_dir.mkdir()
        self.state_dir.mkdir()
        self.bin_dir.mkdir()
        (self.state_dir / "password").write_text("not-a-secret\n", encoding="utf-8")
        (self.state_dir / "session-a.target").write_text("HEAD~1..HEAD\n", encoding="utf-8")
        fake_curl = self.bin_dir / "curl"
        fake_curl.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "print(json.dumps({'data': {'id': 'session-a', 'outcome': None}}))\n",
            encoding="utf-8",
        )
        fake_curl.chmod(0o755)
        self.env = os.environ.copy()
        self.env.update(
            {
                "CR_REPO": self.temp.name,
                "CR_REPORT_DIR": str(self.report_dir),
                "CR_STATE_DIR": str(self.state_dir),
                "CR_PORT": "49499",
                "PATH": str(self.bin_dir) + os.pathsep + self.env["PATH"],
            }
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_report(self, report):
        (self.report_dir / f"{report['run_id']}.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

    def run_driver(self, command):
        return subprocess.run(
            ["/bin/bash", str(DRIVER), command, "session-a"],
            check=False,
            capture_output=True,
            text=True,
            env=self.env,
        )

    def test_complete_synthetic_report_succeeds_before_http_command_status(self):
        self.write_report(completion_artifact())
        result = self.run_driver("wait")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("completion:", result.stdout)

    def test_complete_empty_findings_is_a_valid_report(self):
        self.write_report(completion_artifact(findings=[]))
        result = self.run_driver("status")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_wrong_session_target_partial_truncated_and_missing_reports_fail(self):
        cases = [
            completion_artifact(parent_session_id="session-b"),
            completion_artifact(requested_target="other-target"),
            completion_artifact(terminal_status="incomplete", partial=True),
            completion_artifact(truncated=True),
        ]
        for report in cases:
            with self.subTest(report=report):
                for path in self.report_dir.glob("*.json"):
                    path.unlink()
                self.write_report(report)
                result = self.run_driver("status")
                self.assertNotEqual(result.returncode, 0)
        for path in self.report_dir.glob("*.json"):
            path.unlink()
        (self.state_dir / "session-a.command-status").write_text("succeeded\n", encoding="utf-8")
        missing = self.run_driver("status")
        self.assertNotEqual(missing.returncode, 0)

    def test_session_without_target_association_fails_closed(self):
        (self.state_dir / "session-a.target").unlink()
        result = self.run_driver("status")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing target association", result.stderr)


if __name__ == "__main__":
    unittest.main()
