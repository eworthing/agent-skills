"""Tests for common.providers.registry."""

from types import SimpleNamespace

import pytest

from common.providers import PROVIDERS, get_provider, read_prompt
from common.providers.registry import (
    build_agy_cmd,
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
    def test_all_providers_present(self):
        assert set(PROVIDERS.keys()) == {
            "claude", "gemini", "codex", "copilot", "opencode", "agy",
        }

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

    def test_caps_binary_and_resume_supported_mirror_top_level(self):
        # binary/resume_supported are authored once at the top level and
        # mechanically mirrored into caps — verify the mirror actually ran
        # and stayed in sync, for every provider.
        for name, spec in PROVIDERS.items():
            assert spec["caps"]["binary"] == spec["binary"], name
            assert spec["caps"]["resume_supported"] == spec["resume_supported"], name

    def test_known_models_present_for_codex_and_copilot(self):
        # codex and copilot have no list_models_cmd (no CLI model-listing
        # command), so --list-models relies on this authored fallback.
        assert PROVIDERS["codex"]["known_models"]
        assert "gpt-5.4" in PROVIDERS["codex"]["known_models"]
        assert PROVIDERS["copilot"]["known_models"]


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

    def test_codex_fresh_argv_order_pinned(self):
        # approval_mode=never is hoisted below the resume/fresh branch, but
        # the emitted order for a fresh exec must stay exactly what
        # consumers' own tests assert (peer-plan-review test_command_builders).
        cmd = build_codex_cmd(_args())
        assert cmd[:6] == ["codex", "exec", "--sandbox", "read-only", "-c", "approval_mode=never"]

    def test_codex_resume_argv_order_pinned(self):
        cmd = build_codex_cmd(_args(resume=True), session_id="codex-session")
        assert cmd[:6] == ["codex", "exec", "resume", "codex-session", "-c", "approval_mode=never"]

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

    def test_claude_prompt_text_sniffs_verification_without_file_read(self):
        # prompt_text lets a caller sniff the verification-mode header without
        # a real prompt_file on disk (and without re-reading a file it already
        # has in memory).
        cmd = build_claude_cmd(
            _args(prompt_file="/nonexistent/path/does-not-exist.md"),
            prompt_text="## Verification Request\nblah",
        )
        idx = cmd.index("--append-system-prompt")
        assert "independent verifier" in cmd[idx + 1]

    def test_claude_prompt_text_none_falls_back_to_file_read(self, tmp_path):
        p = tmp_path / "prompt.md"
        p.write_text("## Verification Contract\nblah", encoding="utf-8")
        cmd = build_claude_cmd(_args(prompt_file=str(p)))
        idx = cmd.index("--append-system-prompt")
        assert "independent verifier" in cmd[idx + 1]

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

    def test_agy_safety_flag_contract(self):
        # Full safety-flag contract for the EXPERIMENTAL, not-guaranteed-read-only
        # agy reviewer. Pinned here (the source of truth vendored into both skills)
        # so a future edit can't silently weaken the posture:
        #   - --print + --sandbox present (headless + terminal containment)
        #   - --dangerously-skip-permissions ABSENT (never blanket auto-approve)
        #   - --effort ABSENT (effort is folded into the model name, not a flag)
        #   - --model present with a non-empty value (defaults to the Flash family)
        cmd = build_agy_cmd(_args())
        assert cmd[0] == "agy"
        assert "--print" in cmd
        assert "--sandbox" in cmd
        assert "--dangerously-skip-permissions" not in cmd
        assert "--effort" not in cmd
        assert "--model" in cmd
        assert cmd[cmd.index("--model") + 1]  # non-empty model value

    def test_agy_resume(self):
        cmd = build_agy_cmd(_args(resume=True), session_id="conv-uuid")
        assert "--conversation" in cmd
        assert "conv-uuid" in cmd

    def test_agy_effort_composes_into_model_name(self):
        # Effort lives in the model name; "Gemini 3.5 Flash" + high → "(High)".
        cmd = build_agy_cmd(_args(model="Gemini 3.5 Flash", effort="high"))
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "Gemini 3.5 Flash (High)"

    def test_agy_defaults_to_flash_when_no_model(self):
        # No model → inject the only family verified to return output in
        # --print mode, at the default effort (high).
        cmd = build_agy_cmd(_args())
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "Gemini 3.5 Flash (High)"

    def test_agy_full_model_string_passes_through(self):
        cmd = build_agy_cmd(_args(model="Gemini 3.5 Flash (Low)"))
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "Gemini 3.5 Flash (Low)"

    def test_agy_unknown_model_passes_through_raw(self):
        # Non-Flash models aren't a known family — pass through untouched so a
        # caller with different entitlements can still try them.
        cmd = build_agy_cmd(_args(model="Gemini 3.1 Pro (High)"))
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "Gemini 3.1 Pro (High)"


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
