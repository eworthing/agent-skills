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

    def test_codex_manifest_refresh_failure_falls_back_to_fresh_home(self):
        """An unrefreshable manifest on the reuse path is treated like
        stale-home replacement: drop the session binding and mint a fresh
        home, rather than running on a home the orphan sweep may reclaim
        mid-review."""
        self.session_file.write_text(
            json.dumps({"session_id": "old-id", "round": 1, "codex_home": "/fake/reusable-home"}),
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
            mock.patch("run_review.reuse_codex_home", return_value=True),
            mock.patch("run_review.record_codex_home", side_effect=OSError("read-only fs")),
            mock.patch(
                "run_review.setup_codex_home",
                return_value=("/fake/ppr-codex-home-fresh", True),
            ) as mock_setup,
            mock.patch("run_review.teardown_codex_home") as mock_teardown,
            mock.patch("run_review._codex_session_files", return_value=set()),
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        mock_setup.assert_called_once()
        mock_teardown.assert_any_call("/fake/reusable-home")
        session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertNotEqual(session.get("session_id"), "old-id")
        self.assertFalse(session["resume_attempted"])

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
            mock.patch("run_review._kill_tree") as mock_kill,
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
        self.assertTrue(mock_kill.called)

    def test_final_timeout_byte_partial_reaches_artifact(self):
        """A drain that itself times out hands back BYTE-valued partial
        stdout (truncated JSON, killed mid-write). The decoded partial must
        reach the output artifact raw (unwrap fails soft on truncated JSON)
        and the failure summary must say partial_output=true — pins commit
        6a4f41b's contract for a structured provider beyond opencode/codex."""
        summary_file = Path(self.tmpdir.name) / "summary.json"
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            summary_file=str(summary_file),
            resume=False,
        )
        truncated = b'{"result":"### Blocking Issues\\n- [B1] partial finding'
        proc = mock.MagicMock()
        proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd=["claude"], timeout=args.timeout),
            subprocess.TimeoutExpired(cmd=["claude"], timeout=30, output=truncated, stderr=b""),
        ]
        proc.returncode = None
        proc.poll.return_value = None

        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review._kill_tree") as mock_kill,
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 1)
        self.assertIn("partial finding", self.output_file.read_text(encoding="utf-8"))
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        self.assertIsNone(summary["verdict"])
        self.assertTrue(summary["partial_output"])
        self.assertTrue(mock_kill.called)

    def test_signal_handler_kills_active_proc_and_exits(self):
        proc = mock.MagicMock()
        proc.poll.return_value = None
        with (
            mock.patch("run_review._kill_tree") as mock_kill,
            mock.patch.object(run_review, "_active_proc", proc),
            self.assertRaises(SystemExit) as ctx,
        ):
            run_review._signal_handler(signal.SIGTERM, None)
        mock_kill.assert_called_once_with(proc)
        self.assertEqual(ctx.exception.code, 128 + signal.SIGTERM)

    def test_resume_empty_output_sentinel_falls_back_to_fresh(self):
        """A resume attempt that exits 0 with NO output is a silent failure:
        the synthetic sentinel (3) must trip the fresh-exec fallback, and the
        sentinel must never surface as the final rc when the fresh attempt
        succeeds."""
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=True,
        )
        empty_proc = self._proc(0, stdout="", stderr="quiet auth failure")
        fresh_proc = self._proc(0, stdout='{"result":"fresh review"}')

        with (
            mock.patch(
                "run_review.load_session",
                return_value={"session_id": "resume-session", "round": 1},
            ),
            mock.patch(
                "run_review.subprocess.Popen", side_effect=[empty_proc, fresh_proc]
            ) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="fresh-session"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        self.assertEqual(mock_popen.call_count, 2)
        session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertTrue(session["resume_fallback_used"])

    def test_binary_not_found_writes_failure_summary(self):
        summary_file = Path(self.tmpdir.name) / "summary.json"
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            summary_file=str(summary_file),
            resume=False,
        )
        with (
            mock.patch("run_review.subprocess.Popen", side_effect=FileNotFoundError("claude")),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 1)
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        self.assertIsNone(summary["verdict"])
        self.assertIn("binary_not_found", summary["error"])

    def test_post_execution_os_error_writes_failure_summary(self):
        """An OSError past the Popen launch (stat/open race) must land in the
        generic os_error summary, not vanish or masquerade as binary-missing."""
        summary_file = Path(self.tmpdir.name) / "summary.json"
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            summary_file=str(summary_file),
            resume=False,
        )
        proc = self._proc(0, stdout='{"result":"review"}')
        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", side_effect=OSError("disk full")),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 1)
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        self.assertIsNone(summary["verdict"])
        self.assertIn("os_error: disk full", summary["error"])

    def test_codex_multiple_concurrent_sessions_skip_binding(self):
        """>1 new cwd-matching session file means the diff is ambiguous: warn
        and bind nothing rather than guessing (run_review's concurrency
        guard)."""
        import os as _os

        sdir = Path(self.tmpdir.name) / "codex-sessions"
        sdir.mkdir()
        cwd = str(Path.cwd())
        files = []
        for i in (1, 2):
            f = sdir / f"rollout-2026-07-14T00-00-0{i}-uuid{i}.jsonl"
            f.write_text(
                json.dumps({"type": "session_meta", "payload": {"id": f"sess-{i}", "cwd": cwd}})
                + "\n",
                encoding="utf-8",
            )
            files.append(str(f))
        _os.utime(files[0], None)

        args = make_args(
            reviewer="codex",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=False,
        )
        proc = self._proc(0, stdout="", stderr="")

        def communicate(input=None, timeout=None):
            self.output_file.write_text("Review text\n", encoding="utf-8")
            return "", ""

        proc.communicate.side_effect = communicate

        with (
            mock.patch(
                "run_review.setup_codex_home", return_value=("/fake/ppr-codex-home-test", True)
            ),
            mock.patch("run_review._codex_session_files", side_effect=[set(), set(files)]),
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertIsNone(session.get("session_id"))

    def test_codex_round2_reuses_recorded_home(self):
        """Round 2 must reuse the recorded per-run home (env CODEX_HOME) and
        resume with the recorded session id — and refresh the manifest."""
        home = Path(self.tmpdir.name) / "ppr-codex-home-keep"
        (home / "sessions").mkdir(parents=True)
        self.session_file.write_text(
            json.dumps({"session_id": "sess-1", "round": 1, "codex_home": str(home)}),
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
            mock.patch("run_review.record_codex_home") as mock_record,
            mock.patch("run_review._codex_session_files", return_value=set()),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        cmd = mock_popen.call_args_list[0].args[0]
        self.assertIn("resume", cmd)
        self.assertIn("sess-1", cmd)
        env = mock_popen.call_args_list[0].kwargs["env"]
        self.assertEqual(env["CODEX_HOME"], str(home))
        mock_record.assert_called_once()  # manifest mtime refreshed on reuse
        session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertEqual(session.get("codex_home"), str(home))
        self.assertEqual(session.get("round"), 2)


if __name__ == "__main__":
    unittest.main()
