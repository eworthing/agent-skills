"""parsing durability tests — relocated verbatim from test_run_review.py (mechanical split)."""

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


class TestCorruption(unittest.TestCase):
    """Tests for edge cases with corrupt/unexpected files."""

    def test_zero_byte_output_no_crash(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            tmp_path = f.name
        try:
            from _common.session import extract_text_from_output

            extract_text_from_output(tmp_path, "claude")  # should not raise
            self.assertEqual(Path(tmp_path).read_text(), "")
        finally:
            Path(tmp_path).unlink()

    def test_corrupt_session_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{corrupt json")
            tmp_path = f.name
        try:
            from _common.session import load_session

            result = load_session(tmp_path)
            self.assertEqual(result, {})
        finally:
            Path(tmp_path).unlink()

    def test_resume_with_no_session_id(self):
        """Resume=True but session file has no session_id — should not crash."""
        tmpdir = tempfile.mkdtemp(prefix="ppr-corrupt-")
        prompt = Path(tmpdir) / "prompt.md"
        prompt.write_text("Review.\n", encoding="utf-8")
        session = Path(tmpdir) / "session.json"
        session.write_text("{}", encoding="utf-8")

        args = make_args(
            reviewer="claude",
            prompt_file=str(prompt),
            output_file=str(Path(tmpdir) / "out.json"),
            session_file=str(session),
            events_file=str(Path(tmpdir) / "events.jsonl"),
            resume=True,
        )

        proc = mock.MagicMock()
        proc.communicate.return_value = ('{"result":"ok"}', "")
        proc.returncode = 0
        proc.poll.return_value = 0

        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value=None),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)
        self.assertEqual(rc, 0)
        shutil.rmtree(tmpdir)

    def test_nonzero_exit_with_output_still_extracts(self):
        """Non-zero exit but output present — should extract and not retry."""
        tmpdir = tempfile.mkdtemp(prefix="ppr-extract-")
        prompt = Path(tmpdir) / "prompt.md"
        prompt.write_text("Review.\n", encoding="utf-8")
        output = Path(tmpdir) / "review.json"
        output.write_text('{"result":"Review text here"}', encoding="utf-8")

        args = make_args(
            reviewer="claude",
            prompt_file=str(prompt),
            output_file=str(output),
            session_file=str(Path(tmpdir) / "session.json"),
            events_file=str(Path(tmpdir) / "events.jsonl"),
            resume=False,
        )

        proc = mock.MagicMock()
        proc.communicate.return_value = ('{"result":"Review text here"}', "warning")
        proc.returncode = 1
        proc.poll.return_value = 1

        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)
        self.assertEqual(rc, 1)  # returns the error code, doesn't retry
        shutil.rmtree(tmpdir)

    def test_resume_with_output_still_retries_on_nonzero(self):
        """Resume failure WITH output (e.g. an error JSON payload on stdout)
        must still fall back to a fresh attempt — a nonzero exit makes the
        resume attempt's output unusable regardless of whether it produced
        bytes. (Previously a resume error payload counted as "has_output"
        and suppressed the fallback entirely, leaving the error payload as
        the round's persisted output — see run_review.py's resume-fallback
        fix.) If the fresh attempt also fails, its exit code is returned."""
        tmpdir = tempfile.mkdtemp(prefix="ppr-no-retry-")
        prompt = Path(tmpdir) / "prompt.md"
        prompt.write_text("Review.\n", encoding="utf-8")
        output = Path(tmpdir) / "review.json"

        args = make_args(
            reviewer="claude",
            prompt_file=str(prompt),
            output_file=str(output),
            session_file=str(Path(tmpdir) / "session.json"),
            events_file=str(Path(tmpdir) / "events.jsonl"),
            resume=True,
        )

        proc = mock.MagicMock()
        # Non-zero exit but produces output — must still trigger fallback.
        proc.communicate.return_value = ('{"result":"partial review"}', "error")
        proc.returncode = 1
        proc.poll.return_value = 1

        with (
            mock.patch("run_review.load_session", return_value={"session_id": "s1", "round": 1}),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)
        self.assertEqual(rc, 1)  # fresh attempt also failed — its code is returned
        # Both the resume attempt and the fresh-exec fallback ran.
        self.assertEqual(mock_popen.call_count, 2)
        shutil.rmtree(tmpdir)


class TestMockPathCompatibility(unittest.TestCase):
    """Verify re-export mock paths intercept calls from run_review.run_review()."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ppr-compat-")
        self.prompt_file = Path(self.tmpdir.name) / "prompt.md"
        self.prompt_file.write_text("Review.\n", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    @staticmethod
    def _proc(returncode=0, stdout='{"result":"ok"}', stderr=""):
        proc = mock.MagicMock()
        proc.communicate.return_value = (stdout, stderr)
        proc.returncode = returncode
        proc.poll.return_value = returncode
        return proc

    def _run_and_check(self):
        """Run run_review with standard mocks, return mock objects for assertions."""
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(Path(self.tmpdir.name) / "out.json"),
            session_file=str(Path(self.tmpdir.name) / "session.json"),
            events_file=str(Path(self.tmpdir.name) / "events.jsonl"),
        )
        with (
            mock.patch("run_review.subprocess.Popen", return_value=self._proc()) as m_popen,
            mock.patch("run_review.extract_metadata", return_value={}) as m_meta,
            mock.patch("run_review.extract_text_from_output") as m_text,
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args)
            return {"popen": m_popen, "meta": m_meta, "text": m_text}

    def test_extract_metadata_intercepted(self):
        mocks = self._run_and_check()
        mocks["meta"].assert_called()

    def test_extract_text_intercepted(self):
        mocks = self._run_and_check()
        mocks["text"].assert_called()

    def test_build_cmd_intercepted(self):
        sentinel_cmd = ["echo", "test"]
        mock_build = mock.Mock(return_value=sentinel_cmd)
        from _common.providers import PROVIDERS as _PROVIDERS

        with (
            mock.patch.dict(_PROVIDERS["claude"], {"build_cmd": mock_build}),
            mock.patch("run_review.subprocess.Popen", return_value=self._proc()),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="s1"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            args = make_args(
                reviewer="claude",
                prompt_file=str(self.prompt_file),
                output_file=str(Path(self.tmpdir.name) / "out.json"),
                session_file=str(Path(self.tmpdir.name) / "session.json"),
                events_file=str(Path(self.tmpdir.name) / "events.jsonl"),
            )
            run_review.run_review(args)
            mock_build.assert_called_once()


class TestStructuredReviewParsing(unittest.TestCase):
    """Tests for parse_structured_review() — section-scoped finding extraction."""

    def test_finding_with_confidence_section_recommendation(self):
        text = """\
### Reasoning
Some analysis here with [B1] mentioned in passing.

### Blocking Issues
- [B1] (HIGH) Race condition in migration step
  Section: Step 3 — Database migration (lines 42-55)
  Recommendation: Add dependency gate between steps 2 and 3

### Non-Blocking Issues
- [N1] Monitoring gap
  Section: Step 7 — Post-deploy (line 95)
  Recommendation: Add health checks

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 2)
        b1 = findings[0]
        self.assertEqual(b1["id"], "B1")
        self.assertEqual(b1["severity"], "blocking")
        self.assertEqual(b1["confidence"], "HIGH")
        self.assertIn("Race condition", b1["description"])
        self.assertEqual(b1["section"], "Step 3 — Database migration")
        self.assertEqual(b1["lines"], "42-55")
        self.assertEqual(b1["recommendation"], "Add dependency gate between steps 2 and 3")
        n1 = findings[1]
        self.assertEqual(n1["id"], "N1")
        self.assertEqual(n1["severity"], "non_blocking")

    def test_finding_without_confidence(self):
        text = """\
### Blocking Issues
- [B1] Missing rollback strategy

### Non-Blocking Issues
None

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "B1")
        self.assertIsNone(findings[0]["confidence"])

    def test_non_blocking_severity(self):
        text = """\
### Blocking Issues
None

### Non-Blocking Issues
- [N1] Consider adding smoke test
  Recommendation: Add post-deploy verification

VERDICT: APPROVED
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "non_blocking")
        self.assertEqual(findings[0]["recommendation"], "Add post-deploy verification")

    def test_plain_text_returns_empty(self):
        text = "This is just plain text review.\n\nVERDICT: REVISE\n"
        findings = parse_structured_review(text)
        self.assertEqual(findings, [])

    def test_markdown_bold_tags(self):
        text = """\
### Blocking Issues
- **[B1]** (MEDIUM) Bold-tagged finding
  Section: Step 1 (lines 1-5)

### Non-Blocking Issues
None

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "B1")
        self.assertEqual(findings[0]["confidence"], "MEDIUM")

    def test_multi_finding_across_sections(self):
        text = """\
### Reasoning
Analysis...

### Blocking Issues
- [B1] (HIGH) First blocker
  Section: Step 1 (lines 1-10)
- [B2] (MEDIUM) Second blocker
  Section: Step 2 (lines 20-30)

### Non-Blocking Issues
- [N1] First suggestion
- [N2] Second suggestion

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 4)
        ids = [f["id"] for f in findings]
        self.assertEqual(ids, ["B1", "B2", "N1", "N2"])

    def test_reasoning_section_contamination(self):
        """[B1] in ### Reasoning must NOT produce a false positive."""
        text = """\
### Reasoning
The plan mentions [B1] rollback but I disagree with the approach.

### Blocking Issues
None

### Non-Blocking Issues
None

VERDICT: APPROVED
"""
        findings = parse_structured_review(text)
        self.assertEqual(findings, [])

    def test_multiline_spacing(self):
        """Findings separated by blank lines with varying indent."""
        text = """\
### Blocking Issues
- [B1] (HIGH) First issue
  Section: Step 1 (lines 1-5)
  Recommendation: Fix it

- [B2] (LOW) Second issue
  Section: Step 2 (lines 10-15)
  Recommendation: Also fix

### Non-Blocking Issues
None

VERDICT: REVISE
"""
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["recommendation"], "Fix it")
        self.assertEqual(findings[1]["recommendation"], "Also fix")

    def test_section_heading_trailing_whitespace(self):
        """Section heading with trailing spaces should still match."""
        text = "### Blocking Issues   \n- [B1] (HIGH) Found an issue\n\n### Non-Blocking Issues\nNone\n\nVERDICT: REVISE\n"
        findings = parse_structured_review(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "B1")


class TestProviderRegistry(unittest.TestCase):
    """PROVIDERS is the single source of truth for all provider plumbing."""

    def test_get_provider_returns_entry(self):
        from _common.providers import get_provider

        codex = get_provider("codex")
        self.assertEqual(codex["binary"], "codex")
        self.assertTrue(codex["resume_supported"])
        with self.assertRaises(KeyError):
            get_provider("nonexistent")

    def test_all_providers_have_required_keys(self):
        from _common.providers import PROVIDERS

        required = {
            "binary",
            "effort_map",
            "effort_default",
            "model_aliases",
            "resume_supported",
            "build_cmd",
            "caps",
        }
        for name, p in PROVIDERS.items():
            self.assertTrue(required.issubset(p.keys()), f"{name} missing keys")
            self.assertTrue(callable(p["build_cmd"]))


class TestSessionDurability(unittest.TestCase):
    """save_session must be atomic — partial writes must not clobber the target."""

    def test_save_session_atomic_rename(self):
        from _common.session import save_session

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "session.json"
            target.write_text(json.dumps({"round": 1, "session_id": "abc"}))
            save_session(str(target), {"round": 2, "session_id": "def"})
            self.assertEqual(json.loads(target.read_text())["round"], 2)
            self.assertFalse((Path(tmpdir) / "session.json.tmp").exists())

    def test_save_session_failure_preserves_target(self):
        from _common.session import save_session

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "session.json"
            target.write_text(json.dumps({"round": 1}))
            with mock.patch("_common.session.io.json.dump", side_effect=OSError("disk full")):
                save_session(str(target), {"round": 2})
            self.assertEqual(json.loads(target.read_text())["round"], 1)
            self.assertFalse((Path(tmpdir) / "session.json.tmp").exists())


class TestSummaryFile(unittest.TestCase):
    """write_summary emits machine-readable per-round summary JSON."""

    def test_summary_with_findings(self):
        from _common.session import write_summary

        with tempfile.TemporaryDirectory() as tmpdir:
            review = Path(tmpdir) / "review.md"
            review.write_text(
                "### Blocking Issues\n"
                "- [B1] (HIGH) problem one\n"
                "- [B2] (MEDIUM) problem two\n\n"
                "### Non-Blocking Issues\n"
                "- [N1] nit\n\n"
                "VERDICT: REVISE\n"
            )
            summary = Path(tmpdir) / "summary.json"
            write_summary(
                str(summary),
                str(review),
                {"reviewer": "codex", "model": "gpt-5.4", "effort": "medium", "round": 2},
            )
            data = json.loads(summary.read_text())
            self.assertEqual(data["verdict"], "REVISE")
            self.assertEqual(data["reviewer"], "codex")
            self.assertEqual(data["finding_count"], 3)
            self.assertEqual(data["blocking_count"], 2)

    def test_summary_missing_output_file(self):
        from _common.session import write_summary

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.json"
            write_summary(str(summary), str(Path(tmpdir) / "nope.md"), {"reviewer": "claude"})
            data = json.loads(summary.read_text())
            self.assertIsNone(data["verdict"])
            self.assertEqual(data["finding_count"], 0)

    def test_summary_none_path_is_noop(self):
        from _common.session import write_summary

        write_summary(None, None, {})  # must not raise
