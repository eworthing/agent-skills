"""
ppr_providers.py — Provider command builders and constants.

Extracted from run_review.py. Contains EFFORT_MAP, MODEL_ALIASES, BINARIES,
and per-provider command builders for Codex, Gemini, Claude, and Copilot.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Effort mapping: portable level → provider-native value
# ---------------------------------------------------------------------------
EFFORT_MAP = {
    "codex": {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh"},
    "gemini": {"low": 2048, "medium": 8192, "high": 16384, "xhigh": 32768},
    "claude": {"low": "low", "medium": "medium", "high": "high", "xhigh": "max"},
    "copilot": {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh"},
}

# Provider defaults when effort is not specified and not discoverable.
_EFFORT_DEFAULTS = {
    "codex": "medium",  # Codex default per reasoning level selector
    "gemini": "medium",  # Gemini default thinkingBudget is 8192
    "claude": "medium",  # Claude Code default
    "copilot": "medium",  # Copilot default per GitHub docs
}

# ---------------------------------------------------------------------------
# Model aliases: shorthand → canonical name (per provider)
# ---------------------------------------------------------------------------
MODEL_ALIASES = {
    "claude": {"sonnet": "sonnet", "opus": "opus", "haiku": "haiku"},
    "gemini": {"auto": "auto", "pro": "pro", "flash": "flash", "flash-lite": "flash-lite"},
    "codex": {},
    "copilot": {},
}

BINARIES = {
    "codex": "codex",
    "gemini": "gemini",
    "claude": "claude",
    "copilot": "copilot",
}

# ---------------------------------------------------------------------------
# Provider capability table
# ---------------------------------------------------------------------------
PROVIDER_CAPS = {
    "codex": {
        "binary": "codex",
        "prompt_mode": "stdin",
        "output_mode": "file",
        "model_flag": "-m",
        "effort_flag": "-c model_reasoning_effort={level}",
        "resume_flag_style": "subcommand",
        "resume_supported": True,
        "safety_flags": ["--sandbox", "read-only", "-c", "approval_mode=never"],
    },
    "gemini": {
        "binary": "gemini",
        "prompt_mode": "flag",
        "output_mode": "stdout",
        "model_flag": "-m",
        "effort_flag": "config_overlay",
        "resume_flag_style": "flag",
        "resume_supported": True,
        "safety_flags": ["--sandbox", "--approval-mode", "yolo"],
    },
    "claude": {
        "binary": "claude",
        "prompt_mode": "flag",
        "output_mode": "stdout",
        "model_flag": "--model",
        "effort_flag": "--effort {level}",
        "resume_flag_style": "flag",
        "resume_supported": True,
        "safety_flags": ["--permission-mode", "plan"],
    },
    "copilot": {
        "binary": "copilot",
        "prompt_mode": "flag",
        "output_mode": "stdout",
        "model_flag": "--model",
        "effort_flag": "--reasoning-effort {level}",
        "resume_flag_style": "flag_eq",
        "resume_supported": True,
        "safety_flags": ["--no-ask-user", "--yolo", "--deny-tool=write,shell,memory"],
    },
}


# ---------------------------------------------------------------------------
# Provider command builders
# ---------------------------------------------------------------------------


def build_codex_cmd(args, session_id=None):
    """Build Codex exec command. Prompt fed via stdin.

    Web search/fetch works without flag changes — read-only sandbox +
    approval_mode=never already permits web access."""
    binary = BINARIES["codex"]
    cmd = [binary, "exec"]

    if args.resume and session_id:
        cmd.extend(["resume", str(session_id)])
        # --sandbox is NOT available on resume; original session policy applies
        cmd.extend(["-c", "approval_mode=never"])
    else:
        cmd.extend(["--sandbox", "read-only"])
        cmd.extend(["-c", "approval_mode=never"])

    cmd.append("--json")

    if args.output_file:
        cmd.extend(["--output-last-message", args.output_file])

    if args.model:
        cmd.extend(["-m", args.model])

    if args.effort:
        level = EFFORT_MAP["codex"].get(args.effort, args.effort)
        cmd.extend(["-c", f"model_reasoning_effort={level}"])

    # stdin marker — prompt is piped via stdin
    cmd.append("-")
    return cmd


def build_gemini_cmd(args, session_id=None):
    """Build Gemini CLI command."""
    binary = BINARIES["gemini"]
    cmd = [binary]

    if args.resume and session_id:
        cmd.extend(["--resume", str(session_id)])

    cmd.append("--sandbox")
    # yolo auto-approves URL fetch tools; --sandbox still prevents filesystem
    # writes.  plan mode hangs on URL fetch permission prompts in headless.
    cmd.extend(["--approval-mode", "yolo"])
    cmd.extend(["--output-format", "json"])

    if args.model:
        cmd.extend(["-m", args.model])

    # Prompt via -p flag (required for headless)
    prompt_text = read_prompt(args.prompt_file)
    cmd.extend(["-p", prompt_text or ""])

    return cmd


def build_claude_cmd(args, session_id=None):
    """Build Claude Code command."""
    binary = BINARIES["claude"]

    # Prompt via -p flag
    prompt_text = read_prompt(args.prompt_file)
    cmd = [binary, "-p", prompt_text or ""]

    if args.resume and session_id:
        cmd.extend(["--resume", session_id])
    else:
        cmd.append("--no-session-persistence")

    cmd.extend(["--permission-mode", "plan"])
    cmd.extend(["--tools", "Read,Grep,Glob,WebSearch,WebFetch"])
    cmd.extend(["--allowedTools", "WebSearch,WebFetch"])
    cmd.extend(["--output-format", "json"])
    cmd.extend(["--max-turns", "10"])
    cmd.extend(
        [
            "--append-system-prompt",
            "You are a code reviewer. Analyze the plan and provide feedback. "
            "End with VERDICT: APPROVED or VERDICT: REVISE on the last line.",
        ]
    )

    if args.model:
        cmd.extend(["--model", args.model])

    if args.effort:
        level = EFFORT_MAP["claude"].get(args.effort, args.effort)
        cmd.extend(["--effort", level])

    return cmd


def build_copilot_cmd(args, session_id=None):
    """Build Copilot CLI command."""
    binary = BINARIES["copilot"]

    prompt_text = read_prompt(args.prompt_file)
    cmd = [binary, "-p", prompt_text or "", "-s"]

    if args.resume and session_id:
        cmd.extend([f"--resume={session_id}"])

    cmd.append("--no-ask-user")
    # Do NOT use --autopilot.  It enables built-in tools (report_intent,
    # task_complete, skill, sql) that cause Copilot to encrypt response
    # content (encryptedContent only, content empty) and skip producing
    # visible review text.  Without --autopilot, Copilot outputs the
    # review as regular text with populated content fields.
    #
    # --allow-tool=url alone hangs on URL fetch permission prompts in
    # headless mode.  --yolo auto-approves all tools (including URL fetch)
    # while --deny-tool still blocks write/shell/memory.  Intermediate
    # messages may have encrypted content, but the final assistant.message
    # has populated content fields — text extraction works because it
    # filters empty-content messages.
    cmd.append("--yolo")
    cmd.append("--deny-tool=write,shell,memory")
    cmd.append("--no-custom-instructions")
    cmd.append("--no-auto-update")
    cmd.extend(["--output-format", "json"])

    if args.model:
        cmd.extend(["--model", args.model])

    if args.effort:
        level = EFFORT_MAP["copilot"].get(args.effort, args.effort)
        cmd.extend(["--reasoning-effort", level])

    return cmd


def read_prompt(prompt_file):
    """Read prompt text from file."""
    if not prompt_file or not Path(prompt_file).exists():
        return None
    try:
        with Path(prompt_file).open(encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None
