"""Provider registry and CLI command builders."""

from .registry import (
    PROVIDERS,
    build_claude_cmd,
    build_codex_cmd,
    build_copilot_cmd,
    build_gemini_cmd,
    build_opencode_cmd,
    get_provider,
    read_prompt,
)

__all__ = [
    "PROVIDERS",
    "build_claude_cmd",
    "build_codex_cmd",
    "build_copilot_cmd",
    "build_gemini_cmd",
    "build_opencode_cmd",
    "get_provider",
    "read_prompt",
]
