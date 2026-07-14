"""agy (Antigravity) execution-path test — moved verbatim from test_execution_paths.py (mechanical split)."""

import argparse
import glob
import io
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


class TestRunReviewAgy(unittest.TestCase):
    """agy (Antigravity) execution path: plain-text stdout, conversation-id
    capture from a per-run --log-file, and the read-only prompt preamble."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-agy-")
        self.prompt_file = Path(self.tmpdir.name) / "prompt.md"
        self.prompt_file.write_text("Review this plan.\n", encoding="utf-8")
        self.output_file = Path(self.tmpdir.name) / "review.txt"
        self.session_file = Path(self.tmpdir.name) / "session.json"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_agy_captures_conversation_id_and_passes_text_through(self):
        review_text = "### Blocking Issues\nNone.\n\nVERDICT: APPROVED\n"
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            # agy logs the conversation id to its --log-file (not stdout).
            for tok in cmd:
                if tok.startswith("--log-file="):
                    Path(tok.split("=", 1)[1]).write_text(
                        "I0614 printmode.go:155] Print mode: conversation="
                        "abc12345-1111-2222-3333-444455556666, sending message\n",
                        encoding="utf-8",
                    )
            proc = mock.MagicMock()
            proc.communicate.return_value = (review_text, "")
            proc.returncode = 0
            proc.poll.return_value = 0
            return proc

        args = make_args(
            reviewer="agy",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
        )
        with (
            mock.patch("run_review.subprocess.Popen", side_effect=fake_popen),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        # Plain text is written through verbatim (no JSON unwrap for agy).
        self.assertEqual(self.output_file.read_text(encoding="utf-8"), review_text)
        self.assertIn("--print", captured["cmd"])
        self.assertIn("--sandbox", captured["cmd"])
        self.assertNotIn("--dangerously-skip-permissions", captured["cmd"])
        self.assertTrue(any(t.startswith("--log-file=") for t in captured["cmd"]))
        session = json.loads(self.session_file.read_text(encoding="utf-8"))
        self.assertEqual(session["session_id"], "abc12345-1111-2222-3333-444455556666")
        self.assertEqual(session["reviewer"], "agy")

    def test_agy_prepends_readonly_preamble_to_prompt(self):
        captured = {}

        def fake_popen(cmd, **kwargs):
            proc = mock.MagicMock()

            def communicate(input=None, timeout=None):
                captured["input"] = input
                return ("VERDICT: APPROVED\n", "")

            proc.communicate.side_effect = communicate
            proc.returncode = 0
            proc.poll.return_value = 0
            return proc

        args = make_args(
            reviewer="agy",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
        )
        with (
            mock.patch("run_review.subprocess.Popen", side_effect=fake_popen),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)

        self.assertIsNotNone(captured.get("input"))
        self.assertTrue(captured["input"].startswith(run_review.AGY_READONLY_PREAMBLE))
        self.assertIn("Review this plan.", captured["input"])
