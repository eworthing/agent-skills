"""Tests for common.session.paths."""

import sys

import pytest
from common.session.paths import build_paths, load_review_id, main, render_shell


class TestBuildPaths:
    def test_default_tmpdir(self):
        paths = build_paths("abc123")
        assert paths["review_id"] == "abc123"
        assert paths["plan_file"].endswith("ppr-abc123-plan.md")
        assert paths["prompt_file"].endswith("ppr-abc123-prompt.md")
        assert paths["output_file"].endswith("ppr-abc123-review.md")
        assert paths["session_file"].endswith("ppr-abc123-session.json")
        assert paths["events_file"].endswith("ppr-abc123-events.jsonl")
        assert paths["error_log"].endswith("ppr-abc123-errors.jsonl")

    def test_custom_tmpdir(self, tmp_path):
        paths = build_paths("x", tmpdir=str(tmp_path))
        assert paths["tmpdir"] == str(tmp_path)
        assert paths["plan_file"] == str(tmp_path / "ppr-x-plan.md")


class TestRenderShell:
    def test_shell_export_format(self, tmp_path):
        paths = build_paths("rid", tmpdir=str(tmp_path))
        shell = render_shell(paths)
        for var in (
            "REVIEW_ID",
            "TMPDIR",
            "PLAN_FILE",
            "PROMPT_FILE",
            "OUTPUT_FILE",
            "SESSION_FILE",
            "EVENTS_FILE",
            "ERROR_LOG",
        ):
            assert f"export {var}=" in shell

    def test_paths_with_spaces_are_quoted(self, tmp_path):
        bad = tmp_path / "dir with space"
        bad.mkdir()
        paths = build_paths("rid", tmpdir=str(bad))
        shell = render_shell(paths)
        # shlex.quote wraps the path in single quotes when it contains a space.
        assert "'" in shell


class TestLoadReviewIdErrors:
    class _Args:
        review_id = None
        review_id_file = None

    def test_no_id_source_raises_value_error(self):
        # Neither --review-id nor --review-id-file supplied (the argparse
        # group is not required, so this is reachable from --cleanup with no
        # id args at all) must raise ValueError, not TypeError from Path(None).
        with pytest.raises(ValueError, match="no review id"):
            load_review_id(self._Args())


class TestCleanupCLI:
    def test_bare_cleanup_exits_cleanly(self, monkeypatch, capsys):
        # `--cleanup` with no --review-id, --review-id-file, or --id-prefix
        # used to blow up with an uncaught TypeError from Path(None) inside
        # load_review_id. It must now fail with a clean error, no traceback.
        monkeypatch.setattr(sys, "argv", ["paths.py", "--cleanup"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "no review id" in captured.err
        assert "Traceback" not in captured.err
