"""Execution-hardening regressions: session provenance, timeout observability,
process-lifecycle guarantees. Split from test_execution_paths.py (module-size
cap); same stub-subprocess technique.
"""

import json
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ._helpers import *


class TestExecutionHardening(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-run-review-")
        self.prompt_file = Path(self.tmpdir.name) / "prompt.md"
        self.prompt_file.write_text("Review this plan carefully.\n", encoding="utf-8")
        self.output_file = Path(self.tmpdir.name) / "review.json"
        self.session_file = Path(self.tmpdir.name) / "session.json"
        self.events_file = Path(self.tmpdir.name) / "events.jsonl"

    def tearDown(self):
        self.tmpdir.cleanup()

    @staticmethod
    def _proc(returncode, stdout="", stderr=""):
        proc = mock.MagicMock()
        proc.communicate.return_value = (stdout, stderr)
        proc.returncode = returncode
        proc.poll.return_value = returncode
        return proc

    def test_codex_stale_home_records_resume_not_attempted(self):
        """Regression: replacing a stale codex home forces a fresh exec — the
        persisted session must record resume_attempted=False (so the
        ppr_launch.sh degradation warning can fire) and must not resurrect
        the torn-down session id."""
        self.session_file.write_text(
            json.dumps({"session_id": "dead-id", "round": 1, "codex_home": "/fake/stale-home"}),
            encoding="utf-8",
        )
        args = make_args(
            reviewer="codex",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=True,
        )
        proc = self._proc(0, stdout="", stderr="")

        def communicate(input=None, timeout=None):
            self.output_file.write_text("Review text\n", encoding="utf-8")
            return "", ""

        proc.communicate.side_effect = communicate

        with (
            mock.patch("run_review.reuse_codex_home", return_value=False),
            mock.patch(
                "run_review.setup_codex_home", return_value=("/fake/ppr-codex-home-new", True)
            ),
            mock.patch("run_review.teardown_codex_home") as mock_teardown,
            mock.patch("run_review._codex_session_files", return_value=set()),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        mock_teardown.assert_any_call("/fake/stale-home")
        cmd = mock_popen.call_args_list[0].args[0]
        self.assertNotIn("dead-id", cmd)  # resume never attempted with the dead id
        session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertFalse(session["resume_attempted"])
        self.assertFalse(session["resume_fallback_used"])
        self.assertEqual(session["resume_reason"], "no_session_id")
        self.assertNotEqual(session.get("session_id"), "dead-id")

    def test_timeout_error_event_includes_stderr(self):
        """The provider_timeout event must carry the drained stderr snippet —
        without it, a timeout caused by an auth/config error is
        indistinguishable from a genuinely slow review."""
        error_log = Path(self.tmpdir.name) / "errors.jsonl"
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=False,
        )
        proc = mock.MagicMock()
        proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd=["claude"], timeout=args.timeout),
            ("", "boom: auth token expired"),
        ]
        proc.returncode = None
        proc.poll.return_value = None

        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review._kill_tree"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args, logger=EventLogger(str(error_log)))

        self.assertEqual(rc, 1)
        events = [
            json.loads(line)
            for line in error_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        timeout_events = [e for e in events if e["event"] == "provider_timeout"]
        self.assertEqual(len(timeout_events), 1)
        self.assertIn("boom: auth token expired", timeout_events[0]["ctx"]["stderr"])


if __name__ == "__main__":
    unittest.main()
