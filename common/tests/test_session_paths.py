"""Tests for common.session.paths."""

import pytest

from common.session.paths import build_paths, render_shell


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
        for var in ("REVIEW_ID", "TMPDIR", "PLAN_FILE", "PROMPT_FILE",
                    "OUTPUT_FILE", "SESSION_FILE", "EVENTS_FILE", "ERROR_LOG"):
            assert f"export {var}=" in shell

    def test_paths_with_spaces_are_quoted(self, tmp_path):
        bad = tmp_path / "dir with space"
        bad.mkdir()
        paths = build_paths("rid", tmpdir=str(bad))
        shell = render_shell(paths)
        # shlex.quote wraps the path in single quotes when it contains a space.
        assert "'" in shell
