"""Tests for common.providers.registry."""

from types import SimpleNamespace

import pytest

from common.providers import PROVIDERS, get_provider, read_prompt
from common.providers.registry import (
    build_claude_cmd,
    build_codex_cmd,
    build_copilot_cmd,
    build_gemini_cmd,
    build_opencode_cmd,
)


def _args(**overrides):
    """Build a minimal args namespace the build_*_cmd helpers expect."""
    base = {
        "resume": False,
        "model": None,
        "effort": None,
        "output_file": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestRegistry:
    def test_all_five_providers_present(self):
        assert set(PROVIDERS.keys()) == {"claude", "gemini", "codex", "copilot", "opencode"}

    def test_required_keys(self):
        required = {"binary", "effort_map", "effort_default", "model_aliases",
                    "resume_supported", "build_cmd", "caps"}
        for name, spec in PROVIDERS.items():
            missing = required - set(spec.keys())
            assert not missing, f"{name} missing keys: {missing}"

    def test_effort_map_covers_portable_levels(self):
        for name, spec in PROVIDERS.items():
            for level in ("low", "medium", "high", "xhigh"):
                assert level in spec["effort_map"], (
                    f"{name} effort_map missing portable level {level!r}"
                )


class TestGetProvider:
    def test_lookup_known(self):
        assert get_provider("claude")["binary"] == "claude"

    def test_lookup_unknown_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_provider("nonsense")

    def test_allow_list_accepts(self):
        assert get_provider("claude", allowed={"claude", "gemini"})["binary"] == "claude"

    def test_allow_list_rejects(self):
        with pytest.raises(ValueError) as excinfo:
            get_provider("opencode", allowed={"claude", "gemini", "codex", "copilot"})
        msg = str(excinfo.value)
        assert "accepted:" in msg
        # Error message must enumerate the accepted set so users can self-correct.
        for allowed_name in ("claude", "gemini", "codex", "copilot"):
            assert allowed_name in msg


class TestBuildCmd:
    """Each build_*_cmd produces a non-empty argv list with the binary first
    and safety flags applied. Exact flag matching is intentionally light to
    keep the test resilient to harmless flag-ordering changes."""

    def test_codex_basic(self):
        cmd = build_codex_cmd(_args())
        assert cmd[0] == "codex"
        assert "exec" in cmd
        assert "--sandbox" in cmd
        assert "read-only" in cmd

    def test_codex_resume(self):
        cmd = build_codex_cmd(_args(resume=True), session_id="abc-123")
        assert "resume" in cmd
        assert "abc-123" in cmd
        # Sandbox flag is not valid on resume.
        assert "--sandbox" not in cmd

    def test_gemini_basic(self):
        cmd = build_gemini_cmd(_args())
        assert cmd[0] == "gemini"
        assert "--sandbox" in cmd
        assert "--approval-mode" in cmd
        assert "yolo" in cmd

    def test_claude_basic(self):
        cmd = build_claude_cmd(_args())
        assert cmd[0] == "claude"
        assert "--permission-mode" in cmd
        assert "plan" in cmd

    def test_claude_effort_xhigh_maps_to_max(self):
        cmd = build_claude_cmd(_args(effort="xhigh"))
        # Claude is the one provider that maps xhigh → max (its highest level).
        assert "--effort" in cmd
        idx = cmd.index("--effort")
        assert cmd[idx + 1] == "max"

    def test_copilot_basic(self):
        cmd = build_copilot_cmd(_args())
        assert cmd[0] == "copilot"
        assert "--no-ask-user" in cmd
        # --autopilot is explicitly NOT used (it encrypts response content).
        assert "--autopilot" not in cmd
        assert "--yolo" in cmd
        assert "--deny-tool=write,shell,memory" in cmd

    def test_opencode_basic(self):
        cmd = build_opencode_cmd(_args())
        assert cmd[0] == "opencode"
        assert "run" in cmd
        assert "--dangerously-skip-permissions" in cmd


class TestReadPrompt:
    def test_missing_file_returns_none(self, tmp_path):
        assert read_prompt(str(tmp_path / "nope.md")) is None

    def test_empty_path_returns_none(self):
        assert read_prompt(None) is None
        assert read_prompt("") is None

    def test_reads_existing(self, tmp_path):
        p = tmp_path / "prompt.md"
        p.write_text("hello world", encoding="utf-8")
        assert read_prompt(str(p)) == "hello world"
