"""execution paths tests — relocated verbatim from test_run_review.py (mechanical split)."""
import argparse, json, os, shutil, signal, stat, subprocess, sys, tempfile, unittest  # noqa: F401
from pathlib import Path  # noqa: F401
from unittest import mock  # noqa: F401
from ._helpers import *  # noqa: F401,F403
from ._helpers import _CREATE_NEW_PROCESS_GROUP  # noqa: F401


class TestSelfCheckUnit(unittest.TestCase):
    """Pure unit tests for self_check edge cases."""

    @mock.patch("run_review.shutil.which", return_value="/fake/gemini")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_gemini_timeout_is_inconclusive_success(self, mock_run, _mock_which):
        """Gemini help timeout under automation should not fail install check."""
        mock_run.side_effect = subprocess.TimeoutExpired(["gemini", "--help"], 15)

        self.assertTrue(self_check("gemini"))

    @mock.patch("run_review.shutil.which", return_value="/fake/copilot")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_copilot_keychain_error_is_inconclusive_success(self, mock_run, _mock_which):
        """Copilot keychain startup errors under automation should not fail install check."""
        mock_run.return_value = subprocess.CompletedProcess(
            ["copilot", "--help"],
            1,
            stdout="",
            stderr="ERROR: SecItemCopyMatching failed -50\n",
        )

        self.assertTrue(self_check("copilot"))

    @mock.patch("run_review.shutil.which", return_value="/fake/claude")
    @mock.patch("run_review.subprocess.run")
    def test_self_check_generic_timeout_still_fails(self, mock_run, _mock_which):
        """Timeouts remain failures for providers without a known automation exception."""
        mock_run.side_effect = subprocess.TimeoutExpired(["claude", "--help"], 15)

        self.assertFalse(self_check("claude"))


class TestSelfCheck(unittest.TestCase):
    """Tier 2: Optional self-checks for installed provider CLIs."""

    @unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
    def test_self_check_claude(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "claude")
        self.assertEqual(rc, 0, f"stderr: {stderr}")

    @unittest.skipUnless(shutil.which("gemini"), "gemini CLI not installed")
    def test_self_check_gemini(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "gemini")
        self.assertEqual(rc, 0, f"stderr: {stderr}")

    @unittest.skipUnless(shutil.which("codex"), "codex CLI not installed")
    def test_self_check_codex(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "codex")
        self.assertEqual(rc, 0, f"stderr: {stderr}")

    @unittest.skipUnless(shutil.which("copilot"), "copilot CLI not installed")
    def test_self_check_copilot(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "copilot")
        self.assertEqual(rc, 0, f"stderr: {stderr}")

    @unittest.skipUnless(shutil.which("opencode"), "opencode CLI not installed")
    def test_self_check_opencode(self):
        rc, _stdout, stderr = run_script("--self-check", "--reviewer", "opencode")
        self.assertEqual(rc, 0, f"stderr: {stderr}")


class TestPlatformHelpers(unittest.TestCase):
    """Tests for cross-platform process helpers."""

    @mock.patch("_common.process.tree.sys")
    def test_popen_session_kwargs_posix(self, mock_sys):
        mock_sys.platform = "linux"
        result = run_review._popen_session_kwargs()
        self.assertEqual(result, {"start_new_session": True})

    @mock.patch(
        "_common.process.tree.subprocess.CREATE_NEW_PROCESS_GROUP", _CREATE_NEW_PROCESS_GROUP, create=True
    )
    @mock.patch("_common.process.tree.sys")
    def test_popen_session_kwargs_windows(self, mock_sys):
        mock_sys.platform = "win32"
        result = run_review._popen_session_kwargs()
        self.assertIn("creationflags", result)
        self.assertEqual(result["creationflags"], _CREATE_NEW_PROCESS_GROUP)

    @mock.patch("_common.process.tree.sys")
    def test_kill_tree_windows_uses_taskkill(self, mock_sys):
        mock_sys.platform = "win32"
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        with mock.patch("_common.process.tree.subprocess.run") as mock_run:
            run_review._kill_tree(mock_proc)
            mock_run.assert_called_once_with(
                ["taskkill", "/T", "/F", "/PID", "12345"],
                capture_output=True,
            )
            mock_proc.wait.assert_called_once()

    @mock.patch("_common.process.tree.sys")
    def test_kill_tree_posix_uses_killpg(self, mock_sys):
        mock_sys.platform = "linux"
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        with (
            mock.patch("_common.process.tree.os.getpgid", return_value=12345),
            mock.patch("_common.process.tree.os.killpg"),
        ):
            run_review._kill_tree(mock_proc)
            mock_proc.wait.assert_called()


class TestRunReviewExecution(unittest.TestCase):
    """Execution-path unit tests that stub subprocess behavior."""

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

    def test_run_review_gemini_effort_overlay_preserves_existing_settings(self):
        source_dir = Path(self.tmpdir.name) / "source-config"
        source_dir.mkdir()
        (source_dir / "settings.json").write_text(
            json.dumps({"theme": "dark", "thinkingConfig": {"thinkingBudget": 1}}),
            encoding="utf-8",
        )
        overlay_dir = Path(self.tmpdir.name) / "overlay-config"
        overlay_dir.mkdir()

        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            effort="high",
        )

        proc = self._proc(0, stdout='{"response":"ok"}')
        with (
            mock.patch.dict(os.environ, {"GEMINI_CONFIG_DIR": str(source_dir)}, clear=False),
            mock.patch("run_review.tempfile.mkdtemp", return_value=str(overlay_dir)),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="gemini-session"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
            mock.patch("run_review.shutil.rmtree"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        settings = json.loads((overlay_dir / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["theme"], "dark")
        self.assertEqual(settings["thinkingConfig"]["thinkingBudget"], 16384)
        popen_env = mock_popen.call_args.kwargs["env"]
        self.assertEqual(popen_env["GEMINI_CONFIG_DIR"], str(overlay_dir))

    def test_run_review_gemini_effort_overlay_excludes_auto_saved_policies(self):
        source_dir = Path(self.tmpdir.name) / "source-config"
        policies_dir = source_dir / "policies"
        policies_dir.mkdir(parents=True)
        (source_dir / "settings.json").write_text("{}", encoding="utf-8")
        (policies_dir / "auto-saved.toml").write_text(
            '[allow]\ncommand = "python3 -c \\"very large stale prompt\\""\n',
            encoding="utf-8",
        )
        overlay_dir = Path(self.tmpdir.name) / "overlay-config"
        overlay_dir.mkdir()

        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            effort="high",
        )

        proc = self._proc(0, stdout='{"response":"ok"}')
        with (
            mock.patch.dict(os.environ, {"GEMINI_CONFIG_DIR": str(source_dir)}, clear=False),
            mock.patch("run_review.tempfile.mkdtemp", return_value=str(overlay_dir)),
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="gemini-session"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
            mock.patch("run_review.shutil.rmtree"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        self.assertFalse((overlay_dir / "policies" / "auto-saved.toml").exists())

    def test_run_review_gemini_without_effort_uses_isolated_config_overlay(self):
        source_dir = Path(self.tmpdir.name) / "source-config"
        policies_dir = source_dir / "policies"
        policies_dir.mkdir(parents=True)
        (source_dir / "settings.json").write_text('{"theme":"dark"}', encoding="utf-8")
        (policies_dir / "auto-saved.toml").write_text(
            '[allow]\ncommand = "python3 -c \\"very large stale prompt\\""\n',
            encoding="utf-8",
        )
        overlay_dir = Path(self.tmpdir.name) / "overlay-config"
        overlay_dir.mkdir()

        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            effort=None,
        )

        proc = self._proc(0, stdout='{"response":"ok"}')
        with (
            mock.patch.dict(os.environ, {"GEMINI_CONFIG_DIR": str(source_dir)}, clear=False),
            mock.patch("run_review.tempfile.mkdtemp", return_value=str(overlay_dir)),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="gemini-session"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
            mock.patch("run_review.shutil.rmtree"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        settings = json.loads((overlay_dir / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["theme"], "dark")
        self.assertFalse((overlay_dir / "policies" / "auto-saved.toml").exists())
        popen_env = mock_popen.call_args.kwargs["env"]
        self.assertEqual(popen_env["GEMINI_CONFIG_DIR"], str(overlay_dir))

    def test_run_review_gemini_pipes_prompt_via_stdin(self):
        source_dir = Path(self.tmpdir.name) / "source-config"
        source_dir.mkdir()
        overlay_dir = Path(self.tmpdir.name) / "overlay-config"
        overlay_dir.mkdir()
        args = make_args(
            reviewer="gemini",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
        )

        proc = self._proc(0, stdout='{"response":"ok"}')
        with (
            mock.patch.dict(os.environ, {"GEMINI_CONFIG_DIR": str(source_dir)}, clear=False),
            mock.patch("run_review.subprocess.Popen", return_value=proc) as mock_popen,
            mock.patch("run_review.tempfile.mkdtemp", return_value=str(overlay_dir)),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="gemini-session"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
            mock.patch("run_review.shutil.rmtree"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        self.assertEqual(mock_popen.call_args.kwargs["stdin"], subprocess.PIPE)
        proc.communicate.assert_called_once_with(
            input="Review this plan carefully.\n",
            timeout=args.timeout,
        )

    def test_run_review_resume_failure_retries_once_without_resume(self):
        args = make_args(
            reviewer="claude",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=True,
        )

        first_proc = self._proc(2, stdout="", stderr="resume failed")
        second_proc = self._proc(1, stdout="", stderr="fresh exec failed")

        with (
            mock.patch(
                "run_review.load_session",
                return_value={"session_id": "resume-session", "round": 1, "model": "prior-model"},
            ),
            mock.patch("run_review.subprocess.Popen", side_effect=[first_proc, second_proc]) as mock_popen,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 1)
        # args.resume is NOT mutated — resume state is tracked via locals
        self.assertTrue(args.resume)
        self.assertEqual(mock_popen.call_count, 2)
        first_cmd = mock_popen.call_args_list[0].args[0]
        second_cmd = mock_popen.call_args_list[1].args[0]
        self.assertIn("--resume", first_cmd)
        self.assertNotIn("--resume", second_cmd)

    def test_run_review_claude_round1_to_round2_session_persistence(self):
        """Round 1 fresh exec must produce a command without --no-session-persistence,
        so that round 2 resume can find the session."""
        # Round 1: fresh exec
        args_round1 = make_args(
            reviewer="claude", prompt_file=str(self.prompt_file),
            output_file=str(self.output_file), session_file=str(self.session_file),
            events_file=str(self.events_file), resume=False,
        )
        proc1 = self._proc(0, stdout='{"result":"ok","session_id":"round1-sess"}')
        with (
            mock.patch("run_review.subprocess.Popen", return_value=proc1) as mock_popen1,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="round1-sess"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args_round1)

        round1_cmd = mock_popen1.call_args_list[0].args[0]
        self.assertNotIn("--no-session-persistence", round1_cmd)
        self.assertNotIn("--resume", round1_cmd)

        # Round 2: resume=True with session_id from round 1
        args_round2 = make_args(
            reviewer="claude", prompt_file=str(self.prompt_file),
            output_file=str(self.output_file), session_file=str(self.session_file),
            events_file=str(self.events_file), resume=True,
        )
        proc2 = self._proc(0, stdout='{"result":"ok","session_id":"round2-sess"}')
        with (
            mock.patch("run_review.load_session", return_value={"session_id": "round1-sess", "round": 1}),
            mock.patch("run_review.subprocess.Popen", return_value=proc2) as mock_popen2,
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.extract_text_from_output"),
            mock.patch("run_review.extract_session_id_json", return_value="round2-sess"),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            run_review.run_review(args_round2)

        round2_cmd = mock_popen2.call_args_list[0].args[0]
        self.assertIn("--resume", round2_cmd)
        self.assertIn("round1-sess", round2_cmd)
        self.assertNotIn("--no-session-persistence", round2_cmd)

    def test_run_review_codex_stale_events_do_not_mask_empty_current_output(self):
        """A stale Codex events file must not satisfy the current-run output guard."""
        self.events_file.write_text('{"type":"old"}\n', encoding="utf-8")
        args = make_args(
            reviewer="codex",
            prompt_file=str(self.prompt_file),
            output_file=str(self.output_file),
            session_file=str(self.session_file),
            events_file=str(self.events_file),
            resume=False,
        )
        proc = self._proc(0, stdout="", stderr="")

        with (
            mock.patch("run_review._codex_session_files", return_value=set()),
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 124)
        self.assertEqual(self.events_file.read_text(encoding="utf-8"), "")

    def test_run_review_codex_accepts_last_message_file_without_json_stdout(self):
        """Codex may produce only --output-last-message output and no JSON stdout."""
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
            mock.patch("run_review._codex_session_files", return_value=set()),
            mock.patch("run_review.subprocess.Popen", return_value=proc),
            mock.patch("run_review.extract_metadata", return_value={}),
            mock.patch("run_review.signal.getsignal", return_value=signal.SIG_DFL),
            mock.patch("run_review.signal.signal"),
        ):
            rc = run_review.run_review(args)

        self.assertEqual(rc, 0)
        self.assertEqual(self.output_file.read_text(encoding="utf-8"), "Review text\n")


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
