"""
ppr_providers.py — Provider registry, command builders, and constants.

TO ADD A NEW PROVIDER:
    1. Add one entry to the PROVIDERS dict at the bottom of this file
       (below the build_*_cmd functions).
    2. Create references/<provider>.md with install/auth/CLI notes.
    3. If session-ID extraction needs a custom path, add it to ppr_metadata.py
       and wire it into the registry entry.

All other modules (run_review.py, ppr_metadata.py, tests) consume the derived
BINARIES / EFFORT_MAP / MODEL_ALIASES / PROVIDER_CAPS / _EFFORT_DEFAULTS views
below — no call sites need to change.
"""

from pathlib import Path


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


def build_opencode_cmd(args, session_id=None):
    """Build opencode run command. Prompt passed as positional arg."""
    binary = BINARIES["opencode"]
    prompt_text = read_prompt(args.prompt_file)
    cmd = [binary, "run", prompt_text or ""]

    cmd.extend(["--format", "json"])
    cmd.append("--dangerously-skip-permissions")

    if args.resume and session_id:
        cmd.extend(["-s", session_id])

    if args.model:
        cmd.extend(["-m", args.model])

    if args.effort:
        level = EFFORT_MAP["opencode"].get(args.effort, args.effort)
        cmd.extend(["--variant", level])

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


# ---------------------------------------------------------------------------
# Provider registry — single source of truth
# ---------------------------------------------------------------------------
# To add a provider: add one entry here. Every dict below is derived from this.
#
# Required keys:
#   binary              str     — CLI name on $PATH
#   effort_map          dict    — portable level → native value
#   effort_default      str     — assumed when effort is unspecified and not
#                                 discoverable from provider output
#   model_aliases       dict    — shorthand → canonical (empty = raw IDs only)
#   resume_supported    bool    — does the CLI accept a resume flag
#   build_cmd           callable— (args, session_id) → argv list
#   caps                dict    — capability descriptors used by callers that
#                                 want to reason about the CLI shape without
#                                 invoking build_cmd (sandbox/resume flavor).
# ---------------------------------------------------------------------------

PROVIDERS = {
    "codex": {
        "binary": "codex",
        "effort_map": {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh"},
        "effort_default": "medium",
        "model_aliases": {},
        "resume_supported": True,
        "build_cmd": build_codex_cmd,
        "caps": {
            "binary": "codex",
            "prompt_mode": "stdin",
            "output_mode": "file",
            "model_flag": "-m",
            "effort_flag": "-c model_reasoning_effort={level}",
            "resume_flag_style": "subcommand",
            "resume_supported": True,
            "safety_flags": ["--sandbox", "read-only", "-c", "approval_mode=never"],
        },
    },
    "gemini": {
        "binary": "gemini",
        "effort_map": {"low": 2048, "medium": 8192, "high": 16384, "xhigh": 32768},
        "effort_default": "medium",
        "model_aliases": {
            "auto": "auto",
            "pro": "pro",
            "flash": "flash",
            "flash-lite": "flash-lite",
        },
        "resume_supported": True,
        "build_cmd": build_gemini_cmd,
        "caps": {
            "binary": "gemini",
            "prompt_mode": "flag",
            "output_mode": "stdout",
            "model_flag": "-m",
            "effort_flag": "config_overlay",
            "resume_flag_style": "flag",
            "resume_supported": True,
            "safety_flags": ["--sandbox", "--approval-mode", "yolo"],
        },
    },
    "claude": {
        "binary": "claude",
        "effort_map": {"low": "low", "medium": "medium", "high": "high", "xhigh": "max"},
        "effort_default": "medium",
        "model_aliases": {"sonnet": "sonnet", "opus": "opus", "haiku": "haiku"},
        "resume_supported": True,
        "build_cmd": build_claude_cmd,
        "caps": {
            "binary": "claude",
            "prompt_mode": "flag",
            "output_mode": "stdout",
            "model_flag": "--model",
            "effort_flag": "--effort {level}",
            "resume_flag_style": "flag",
            "resume_supported": True,
            "safety_flags": ["--permission-mode", "plan"],
        },
    },
    "copilot": {
        "binary": "copilot",
        "effort_map": {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh"},
        "effort_default": "medium",
        "model_aliases": {},
        "resume_supported": True,
        "build_cmd": build_copilot_cmd,
        "caps": {
            "binary": "copilot",
            "prompt_mode": "flag",
            "output_mode": "stdout",
            "model_flag": "--model",
            "effort_flag": "--reasoning-effort {level}",
            "resume_flag_style": "flag_eq",
            "resume_supported": True,
            "safety_flags": ["--no-ask-user", "--yolo", "--deny-tool=write,shell,memory"],
        },
    },
    "opencode": {
        "binary": "opencode",
        "effort_map": {"low": "low", "medium": "medium", "high": "high", "xhigh": "max"},
        "effort_default": "medium",
        "model_aliases": {
            "deepseek": "opencode-go/deepseek-v4-pro",
            "deepseek-flash": "opencode-go/deepseek-v4-flash",
            "kimi": "opencode-go/kimi-k2.6",
            "kimi-vision": "opencode-go/kimi-k2.5",
            "mimo": "opencode-go/mimo-v2.5",
            "mimo-pro": "opencode-go/mimo-v2.5-pro",
            "mimo-omni": "opencode-go/mimo-v2-omni",
            "qwen": "opencode-go/qwen3.6-plus",
            "glm": "opencode-go/glm-5.1",
            "minimax": "opencode-go/minimax-m2.7",
        },
        "resume_supported": True,
        "build_cmd": build_opencode_cmd,
        "caps": {
            "binary": "opencode",
            "prompt_mode": "positional",
            "output_mode": "stdout",
            "model_flag": "-m",
            "effort_flag": "--variant {level}",
            "resume_flag_style": "flag",
            "resume_supported": True,
            "safety_flags": ["--dangerously-skip-permissions"],
        },
        # opencode-go model discovery command — used by --list-models
        "list_models_cmd": ["opencode", "models", "opencode-go"],
    },
}


def get_provider(name):
    """Look up a provider by name. Raises KeyError on unknown provider."""
    return PROVIDERS[name]


# Derived views — kept for backward compatibility. Do NOT edit these directly;
# edit PROVIDERS above and they stay consistent.
BINARIES = {name: p["binary"] for name, p in PROVIDERS.items()}
EFFORT_MAP = {name: p["effort_map"] for name, p in PROVIDERS.items()}
_EFFORT_DEFAULTS = {name: p["effort_default"] for name, p in PROVIDERS.items()}
MODEL_ALIASES = {name: p["model_aliases"] for name, p in PROVIDERS.items()}
PROVIDER_CAPS = {name: p["caps"] for name, p in PROVIDERS.items()}
BUILDERS = {name: p["build_cmd"] for name, p in PROVIDERS.items()}
