"""Provider registry and CLI command builders."""

from .registry import (
    AGY_READONLY_PREAMBLE,
    PROVIDERS,
    build_agy_cmd,
    build_claude_cmd,
    build_codex_cmd,
    build_copilot_cmd,
    build_gemini_cmd,
    build_opencode_cmd,
    get_provider,
    read_prompt,
)

__all__ = [
    "AGY_READONLY_PREAMBLE",
    "PROVIDERS",
    "build_agy_cmd",
    "build_claude_cmd",
    "build_codex_cmd",
    "build_copilot_cmd",
    "build_gemini_cmd",
    "build_opencode_cmd",
    "get_provider",
    "read_prompt",
]
