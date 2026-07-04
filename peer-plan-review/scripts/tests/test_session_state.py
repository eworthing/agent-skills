"""session state tests — relocated verbatim from test_run_review.py (mechanical split)."""

import argparse
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ._helpers import *
from ._helpers import _CREATE_NEW_PROCESS_GROUP


class TestEventLogger(unittest.TestCase):
    """Tests for the EventLogger JSONL logger."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-logger-")
        self.log_path = Path(self.tmpdir.name) / "events.jsonl"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_writes_valid_jsonl_line(self):
        logger = EventLogger(str(self.log_path), review_id="test123")
        logger.log("execution_start", provider="claude")
        lines = self.log_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["event"], "execution_start")
        self.assertEqual(data["provider"], "claude")
        self.assertEqual(data["review_id"], "test123")

    def test_appends_across_calls(self):
        logger = EventLogger(str(self.log_path), review_id="test")
        logger.log("event_a")
        logger.log("event_b")
        lines = self.log_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)

    def test_noop_when_no_path(self):
        logger = EventLogger(None)
        logger.log("should_not_crash")  # no exception

    def test_includes_all_fields(self):
        logger = EventLogger(str(self.log_path), review_id="r1")
        logger.log("test_event", provider="codex", round_num=3, error="boom", context={"k": "v"})
        data = json.loads(self.log_path.read_text().strip())
        self.assertIn("ts", data)
        self.assertEqual(data["review_id"], "r1")
        self.assertEqual(data["event"], "test_event")
        self.assertEqual(data["provider"], "codex")
        self.assertEqual(data["round"], 3)
        self.assertEqual(data["error"], "boom")
        self.assertEqual(data["ctx"], {"k": "v"})

    def test_handles_unwritable_log_path(self):
        logger = EventLogger("/nonexistent/dir/events.jsonl", review_id="r1")
        logger.log("should_not_crash")  # no exception

    def test_handles_missing_parent_directory(self):
        logger = EventLogger("/tmp/ppr-missing-dir-xyz/events.jsonl", review_id="r1")
        logger.log("should_not_crash")  # no exception

    def test_handles_non_serializable_context(self):
        logger = EventLogger(str(self.log_path), review_id="r1")
        logger.log("test", context={"path": Path("/tmp/test")})
        data = json.loads(self.log_path.read_text().strip())
        self.assertIn("/tmp/test", data["ctx"]["path"])

    def test_timestamp_format(self):
        logger = EventLogger(str(self.log_path), review_id="r1")
        logger.log("test")
        data = json.loads(self.log_path.read_text().strip())
        self.assertIn("+00:00", data["ts"])


class TestPromptValidation(unittest.TestCase):
    """Tests for validate_prompt_file."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-prompt-")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_empty_prompt_rejected(self):
        f = Path(self.tmpdir.name) / "empty.md"
        f.write_text("", encoding="utf-8")
        ok, err = validate_prompt_file(str(f))
        self.assertFalse(ok)
        self.assertIn("empty", err)

    def test_whitespace_only_prompt_rejected(self):
        f = Path(self.tmpdir.name) / "whitespace.md"
        f.write_text("   \n\t  \n", encoding="utf-8")
        ok, err = validate_prompt_file(str(f))
        self.assertFalse(ok)
        self.assertIn("empty", err)

    def test_binary_prompt_rejected(self):
        f = Path(self.tmpdir.name) / "binary.md"
        f.write_bytes(bytes([0x80, 0x81, 0x82, 0x83]))
        ok, err = validate_prompt_file(str(f))
        self.assertFalse(ok)
        self.assertIn("UTF-8", err)

    def test_valid_prompt_accepted(self):
        f = Path(self.tmpdir.name) / "valid.md"
        f.write_text("Review this plan.\n", encoding="utf-8")
        ok, err = validate_prompt_file(str(f))
        self.assertTrue(ok)
        self.assertIsNone(err)

    @unittest.skipIf(sys.platform == "win32", "POSIX file permissions not supported on Windows")
    def test_unreadable_prompt_rejected(self):
        f = Path(self.tmpdir.name) / "unreadable.md"
        f.write_text("content", encoding="utf-8")
        f.chmod(0o000)
        try:
            ok, err = validate_prompt_file(str(f))
            self.assertFalse(ok)
            self.assertIn("not readable", err)
        finally:
            f.chmod(stat.S_IRWXU)


class TestWriteProbes(unittest.TestCase):
    """Tests for probe_writable."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-probe-")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_existing_writable_file(self):
        f = Path(self.tmpdir.name) / "writable.json"
        f.write_text("{}", encoding="utf-8")
        ok, err = probe_writable(str(f))
        self.assertTrue(ok)
        self.assertIsNone(err)

    @unittest.skipIf(sys.platform == "win32", "POSIX file permissions not supported on Windows")
    def test_existing_readonly_file(self):
        f = Path(self.tmpdir.name) / "readonly.json"
        f.write_text("{}", encoding="utf-8")
        f.chmod(stat.S_IRUSR)
        try:
            ok, err = probe_writable(str(f))
            self.assertFalse(ok)
            self.assertIn("not writable", err)
        finally:
            f.chmod(stat.S_IRWXU)

    def test_new_file_in_writable_dir(self):
        ok, err = probe_writable(str(Path(self.tmpdir.name) / "new.json"))
        self.assertTrue(ok)
        self.assertIsNone(err)

    @unittest.skipIf(
        sys.platform == "win32", "POSIX directory permissions not supported on Windows"
    )
    def test_new_file_in_readonly_dir(self):
        readonly = Path(self.tmpdir.name) / "readonly"
        readonly.mkdir()
        readonly.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            ok, err = probe_writable(str(readonly / "new.json"))
            self.assertFalse(ok)
            self.assertIn("not writable", err)
        finally:
            readonly.chmod(stat.S_IRWXU)

    def test_path_is_directory(self):
        d = Path(self.tmpdir.name) / "subdir"
        d.mkdir()
        ok, err = probe_writable(str(d))
        self.assertFalse(ok)
        self.assertIn("not a regular file", err)

    @unittest.skipIf(
        sys.platform == "win32", "Symlink creation requires elevated privileges on Windows"
    )
    def test_path_is_symlink_to_directory(self):
        d = Path(self.tmpdir.name) / "target_dir"
        d.mkdir()
        link = Path(self.tmpdir.name) / "link_to_dir"
        link.symlink_to(d)
        ok, err = probe_writable(str(link))
        self.assertFalse(ok)
        self.assertIn("not a regular file", err)

    @unittest.skipIf(sys.platform == "win32", "FIFOs require POSIX")
    def test_path_is_fifo(self):
        fifo = Path(self.tmpdir.name) / "test.fifo"
        os.mkfifo(str(fifo))
        ok, err = probe_writable(str(fifo))
        self.assertFalse(ok)
        self.assertIn("not a regular file", err)


class TestProviderCapabilityTable(unittest.TestCase):
    """Tests for the caps field on every PROVIDERS entry."""

    def test_all_providers_have_caps(self):
        for name, p in PROVIDERS.items():
            self.assertIn("caps", p, f"Missing caps on PROVIDERS[{name}]")

    def test_caps_fields_present(self):
        required = {
            "binary",
            "prompt_mode",
            "output_mode",
            "model_flag",
            "effort_flag",
            "resume_flag_style",
            "resume_supported",
            "safety_flags",
        }
        for name, p in PROVIDERS.items():
            caps = p["caps"]
            for field in required:
                self.assertIn(field, caps, f"Missing {field} in PROVIDERS[{name}].caps")


class TestResumeMetadata(unittest.TestCase):
    """Tests for resume metadata in session data."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-resume-meta-")
        self.prompt_file = Path(self.tmpdir.name) / "prompt.md"
        self.prompt_file.write_text("Review.\n", encoding="utf-8")
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

    def test_session_records_resume_requested_false(self):
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=False,
        )
        proc = self._proc(0, stdout='{"result":"ok"}')
        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)
        session = json.loads(self.session_file.read_text())
        self.assertFalse(session["resume_requested"])
        self.assertFalse(session["resume_fallback_used"])
        self.assertEqual(session["resume_reason"], "fresh_exec")

    def test_session_records_resume_requested_true(self):
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=True,
        )
        proc = self._proc(0, stdout='{"result":"ok"}')
        with (
            mock.patch("run_review.load_session", return_value={"session_id": "s1", "round": 1}),
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)
        session = json.loads(self.session_file.read_text())
        self.assertTrue(session["resume_requested"])
        self.assertTrue(session["resume_attempted"])
        self.assertEqual(session["resume_reason"], "session_found")

    def test_session_records_fallback(self):
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=True,
        )
        first_proc = self._proc(2, stdout="", stderr="resume failed")
        second_proc = self._proc(0, stdout='{"result":"ok"}')
        with (
            mock.patch("run_review.load_session", return_value={"session_id": "s1", "round": 1}),
            mock.patch("run_review.subprocess.Popen", side_effect=[first_proc, second_proc]),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s2"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)
        session = json.loads(self.session_file.read_text())
        self.assertTrue(session["resume_requested"])
        self.assertTrue(session["resume_fallback_used"])
        self.assertEqual(session["resume_reason"], "fallback_to_fresh")


class TestPlanMetadata(unittest.TestCase):
    """Tests for compute_plan_metadata."""

    def test_computes_correctly(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Plan\nStep 1\n")
            f.flush()
            meta = compute_plan_metadata(f.name)
        try:
            self.assertEqual(meta["plan_name"], Path(f.name).name)
            self.assertEqual(meta["plan_bytes"], Path(f.name).stat().st_size)
            self.assertEqual(len(meta["plan_sha256"]), 64)
            self.assertIn("+00:00", meta["plan_mtime"])
        finally:
            Path(f.name).unlink()

    def test_plan_name_is_filename_only(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("content")
            f.flush()
            meta = compute_plan_metadata(f.name)
        try:
            self.assertNotIn("/", meta["plan_name"])
        finally:
            Path(f.name).unlink()

    def test_missing_file_returns_empty(self):
        meta = compute_plan_metadata("/nonexistent/plan.md")
        self.assertEqual(meta, {})

    def test_none_returns_empty(self):
        meta = compute_plan_metadata(None)
        self.assertEqual(meta, {})
