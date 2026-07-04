"""
registry.py — Provider registry and command builders.

Ported from peer-plan-review/scripts/ppr_providers.py. Behavior preserved;
the only API change is that get_provider() now accepts an optional
`allowed` argument so consumers can declare a subset of providers their
skill accepts at its CLI boundary (e.g., quorum-review excludes opencode).

TO ADD A NEW PROVIDER:
    1. Write a build_<name>_cmd(args, session_id) function above the
       PROVIDERS dict.
    2. Add one entry to the PROVIDERS dict at the bottom of this file.
    3. Create references/<provider>.md in any consuming skill that
       documents its CLI surface.
    4. If session-ID extraction needs a custom path, add it to
       common/metadata/extractors.py.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Provider command builders
# ---------------------------------------------------------------------------


def build_codex_cmd(args, session_id=None):
    """Build Codex exec command. Prompt fed via stdin.

    Web search/fetch works without flag changes — read-only sandbox +
    approval_mode=never already permits web access."""
    cmd = ["codex", "exec"]

    if args.resume and session_id:
        cmd.extend(["resume", str(session_id)])
        # --sandbox is NOT available on resume; original session policy applies
    else:
        cmd.extend(["--sandbox", "read-only"])
    cmd.extend(["-c", "approval_mode=never"])

    cmd.append("--json")

    if args.output_file:
        cmd.extend(["--output-last-message", args.output_file])

    if args.model:
        cmd.extend(["-m", args.model])

    if args.effort:
        level = PROVIDERS["codex"]["effort_map"].get(args.effort, args.effort)
        cmd.extend(["-c", f"model_reasoning_effort={level}"])

    # stdin marker — prompt is piped via stdin
    cmd.append("-")
    return cmd


def build_gemini_cmd(args, session_id=None):
    """Build Gemini CLI command."""
    cmd = ["gemini"]

    if args.resume and session_id:
        cmd.extend(["--resume", str(session_id)])

    cmd.append("--sandbox")
    # yolo auto-approves URL fetch tools; --sandbox still prevents filesystem
    # writes.  plan mode hangs on URL fetch permission prompts in headless.
    cmd.extend(["--approval-mode", "yolo"])
    cmd.extend(["--output-format", "json"])
    # Review runs do not need user-installed Gemini extensions. Disabling them
    # avoids startup failures from unrelated, locally broken extension files.
    cmd.extend(["--extensions", ""])

    if args.model:
        cmd.extend(["-m", args.model])

    # -p requires an argument; prompt text is piped via stdin
    cmd.extend(["-p", ""])

    return cmd


def setup_gemini_config(args, env, *, prefix="gemini-", require_effort=False, deep_copy=False):
    """Build an isolated Gemini config overlay and point env at it.

    Gemini runs through a temp config overlay: the review runner needs auth
    and durable settings, but not mutable local approval policy, sessions,
    caches, or extensions from the user's real Gemini home. Mutates
    env["GEMINI_CONFIG_DIR"] on success. Returns the overlay dir (for
    teardown by the caller) or None.

    Two intentional divergences between the callers that use this (kept as
    parameters rather than hand-copied so the shared behavior can't drift):

    ``require_effort`` — if True, only build the overlay when ``args.effort``
    maps to a known thinking-budget value; skip isolation entirely otherwise
    (returns None). If False (default), always build the overlay regardless
    of effort.

    ``deep_copy`` — if True, clone the whole source config directory via
    ``shutil.copytree`` (includes subdirectories such as extensions). If
    False (default), copy only top-level files, which excludes subdirectories
    like auto-saved approval policies.
    """
    budget = PROVIDERS["gemini"]["effort_map"].get(args.effort) if args.effort else None
    if require_effort and not budget:
        return None
    gemini_config_dir = tempfile.mkdtemp(prefix=prefix)
    source_dir = os.environ.get(
        "GEMINI_CONFIG_DIR",
        str(Path("~/.gemini").expanduser()),
    )
    source_path = Path(source_dir)
    if source_path.is_dir():
        if deep_copy:
            try:
                shutil.copytree(source_dir, gemini_config_dir, dirs_exist_ok=True)
            except OSError as e:
                print(f"Warning: could not copy Gemini config dir: {e}", file=sys.stderr)
        else:
            for child in source_path.iterdir():
                if not child.is_file():
                    continue
                try:
                    shutil.copy2(child, Path(gemini_config_dir) / child.name)
                except OSError as e:
                    print(
                        f"Warning: could not copy Gemini config file {child.name}: {e}",
                        file=sys.stderr,
                    )
    settings_path = Path(gemini_config_dir) / "settings.json"
    try:
        existing = {}
        if settings_path.exists():
            with settings_path.open(encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = {}
        if budget:
            existing["thinkingConfig"] = {"thinkingBudget": budget}
        with settings_path.open("w", encoding="utf-8") as f:
            json.dump(existing, f)
        env["GEMINI_CONFIG_DIR"] = gemini_config_dir
    except OSError as e:
        print(f"Warning: could not write Gemini settings: {e}", file=sys.stderr)
        shutil.rmtree(gemini_config_dir, ignore_errors=True)
        gemini_config_dir = None
    return gemini_config_dir


def build_claude_cmd(args, session_id=None, prompt_text=None):
    """Build Claude Code command.

    When ``args.verification_mode`` is True OR the prompt begins with
    ``## Verification Request`` / ``## Verification Contract``, uses the
    independent-verifier system prompt instead of the default reviewer
    system prompt. This keeps the quorum-review verifier role usable
    through the shared adapter without affecting consumers (peer-plan-review)
    that never set the flag and never write a verifier-style prompt.

    ``prompt_text``, if given, is sniffed directly instead of re-reading
    ``args.prompt_file`` from disk. When omitted, the file is read exactly
    as before.
    """
    # -p requires an argument; prompt text is piped via stdin
    cmd = ["claude", "-p", ""]

    if args.resume and session_id:
        cmd.extend(["--resume", session_id])

    cmd.extend(["--permission-mode", "plan"])
    cmd.extend(["--tools", "Read,Grep,Glob,WebSearch,WebFetch"])
    cmd.extend(["--allowedTools", "WebSearch,WebFetch"])
    cmd.extend(["--output-format", "json"])
    cmd.extend(["--max-turns", "10"])

    verification_mode = bool(getattr(args, "verification_mode", False))
    if not verification_mode:
        if prompt_text is None and getattr(args, "prompt_file", None):
            prompt_text = read_prompt(args.prompt_file) or ""
        head = (prompt_text or "").lstrip()
        if head.startswith(("## Verification Request", "## Verification Contract")):
            verification_mode = True

    system_prompt = (
        "You are an independent verifier outside the active panel. "
        "Validate a single blocker using only the blocker ID, anchor, summary, and "
        "current artifact/context provided — do not investigate beyond what is given. "
        "Decide VERIFIED if the blocker is real and unresolved, or INVALIDATED if it is "
        "resolved, inapplicable, or unsupported by the provided context. "
        "Put VERIFIED <ID> or INVALIDATED <ID> on the first non-empty line, then give "
        "one concise rationale."
        if verification_mode
        else "You are a code reviewer. Read the files the plan references before "
        "judging it — do not rely on the plan text alone. Assess the plan for "
        "correctness, completeness, missing edge cases, and risks. "
        "If the artifact is an implementation plan or spec, also assess its "
        "executability — whether a fresh engineer with no prior context could "
        "implement and independently verify each task as written (flag tasks too "
        "large or coupled to verify alone, under-specified or placeholder steps, "
        "and references to files, functions, or signatures the plan never defines). "
        "End with VERDICT: APPROVED or VERDICT: REVISE on the last non-empty line."
    )
    cmd.extend(["--append-system-prompt", system_prompt])

    if args.model:
        cmd.extend(["--model", args.model])

    if args.effort:
        level = PROVIDERS["claude"]["effort_map"].get(args.effort, args.effort)
        cmd.extend(["--effort", level])

    return cmd


def build_copilot_cmd(args, session_id=None):
    """Build Copilot CLI command."""
    # -p requires an argument; prompt text is piped via stdin
    cmd = ["copilot", "-p", "", "-s"]

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
        level = PROVIDERS["copilot"]["effort_map"].get(args.effort, args.effort)
        cmd.extend(["--reasoning-effort", level])

    return cmd


def build_opencode_cmd(args, session_id=None):
    """Build opencode run command."""
    # Prompt text is piped via stdin; run still needs an empty string to avoid interactive mode
    cmd = ["opencode", "run", ""]

    cmd.extend(["--format", "json"])
    cmd.append("--dangerously-skip-permissions")

    if args.resume and session_id:
        cmd.extend(["-s", session_id])

    if args.model:
        cmd.extend(["-m", args.model])

    if args.effort:
        level = PROVIDERS["opencode"]["effort_map"].get(args.effort, args.effort)
        cmd.extend(["--variant", level])

    return cmd


# ---------------------------------------------------------------------------
# Antigravity (agy) — model/effort matrix + read-only preamble
# ---------------------------------------------------------------------------
# `agy models` encodes reasoning effort INSIDE the model name; there is no
# --effort flag. Verified 2026-06-14: only the "Gemini 3.5 Flash" family
# actually returns output in headless --print mode — the Pro variants and bare
# "Gemini 3 Flash" exit 0 with EMPTY output on the tested (enterprise/Vertex)
# account, so every effort level maps to a Flash 3.5 variant. xhigh → High
# (agy's highest). Raw model IDs still pass through for callers whose
# entitlements differ.
_AGY_FAMILIES = {
    "Gemini 3.5 Flash": {"low": "Low", "medium": "Medium", "high": "High", "xhigh": "High"},
}

# agy print mode auto-approves tools and exposes no read-only / system-prompt
# flag (verified: it will write files and run shell). This preamble is prepended
# to every agy review prompt as a best-effort read-only guard. agy is shipped
# EXPERIMENTAL — NOT a guaranteed-read-only reviewer. See references/antigravity.md.
AGY_READONLY_PREAMBLE = (
    "IMPORTANT — READ-ONLY REVIEW. You are reviewing a plan, not editing code. "
    "Do NOT create, modify, move, or delete any files. Do NOT run shell commands "
    "that change state (no writes, installs, git mutations, or network calls). "
    "You may READ files to inform the review. Output only your written review."
)


def build_agy_cmd(args, session_id=None):
    """Build an Antigravity CLI (`agy`) print-mode command.

    agy emits plain-text stdout (no JSON mode) and reads the prompt on stdin.
    Effort is encoded in the model name (see _AGY_FAMILIES); there is no
    --effort flag. The conversation id is recovered from the CLI log by the
    caller via a per-run --log-file (added in run_review.py, not here, so this
    builder stays pure and unit-testable).

    SAFETY: agy print mode auto-approves tools and is NOT guaranteed read-only.
    --sandbox contains terminal commands but the workspace stays writable; the
    caller prepends AGY_READONLY_PREAMBLE to the prompt as a best-effort guard.
    """
    cmd = ["agy", "--print", "--sandbox"]

    # Keep agy's own print-mode timeout >= the adapter timeout so the adapter's
    # process-tree kill stays the single source of truth for cancellation.
    timeout = getattr(args, "timeout", None)
    if timeout:
        cmd.extend(["--print-timeout", f"{timeout}s"])

    if args.resume and session_id:
        cmd.extend(["--conversation", str(session_id)])

    model = args.model
    effort = getattr(args, "effort", None)
    if not model:
        # Default to the only family verified to return output in --print mode
        # (Pro / bare "Gemini 3 Flash" come back empty on tested accounts).
        # Effort then selects the variant; with no effort, effort_default.
        model = "Gemini 3.5 Flash"
    stripped = model.rstrip()
    if stripped.endswith(")") and "(" in stripped:
        chosen = model  # already a full "Family (Level)" string — pass through
    elif model in _AGY_FAMILIES:
        eff = effort or PROVIDERS["agy"]["effort_default"]
        variants = _AGY_FAMILIES[model]
        chosen = f"{model} ({variants.get(eff, variants['high'])})"
    else:
        chosen = model  # raw model ID — pass through
    cmd.extend(["--model", chosen])

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


def build_stdin(reviewer, prompt_file):
    """Return the prompt text to pipe via stdin, or None for argv-prompt providers.

    Providers configured for stdin prompting get the prompt file's contents.
    agy has no system-prompt flag and auto-approves tools in print mode, so it
    gets a best-effort read-only directive prepended. agy is EXPERIMENTAL — not a
    guaranteed-read-only reviewer (see references/antigravity.md).
    """
    if PROVIDERS[reviewer]["caps"].get("prompt_mode") != "stdin":
        return None
    stdin_data = read_prompt(prompt_file)
    if reviewer == "agy" and stdin_data:
        stdin_data = f"{AGY_READONLY_PREAMBLE}\n\n{stdin_data}"
    return stdin_data


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
#                                 caps["binary"] and caps["resume_supported"]
#                                 are NOT authored here — they are mirrored
#                                 from the top-level keys below the PROVIDERS
#                                 dict, so there is a single place to edit.
# ---------------------------------------------------------------------------

PROVIDERS = {
    "codex": {
        "binary": "codex",
        "effort_map": {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh"},
        "effort_default": "medium",
        "model_aliases": {},
        # Available models, sourced from peer-plan-review/references/codex.md.
        "known_models": ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex", "gpt-5.2"],
        "resume_supported": True,
        "build_cmd": build_codex_cmd,
        "caps": {
            "prompt_mode": "stdin",
            "output_mode": "file",
            "model_flag": "-m",
            "effort_flag": "-c model_reasoning_effort={level}",
            "resume_flag_style": "subcommand",
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
            "prompt_mode": "stdin",
            "output_mode": "stdout",
            "model_flag": "-m",
            "effort_flag": "config_overlay",
            "resume_flag_style": "flag",
            "safety_flags": ["--sandbox", "--approval-mode", "yolo"],
        },
    },
    "claude": {
        "binary": "claude",
        "effort_map": {"low": "low", "medium": "medium", "high": "high", "xhigh": "max"},
        "effort_default": "medium",
        "model_aliases": {"fable": "fable", "sonnet": "sonnet", "opus": "opus", "haiku": "haiku"},
        "resume_supported": True,
        "build_cmd": build_claude_cmd,
        "caps": {
            "prompt_mode": "stdin",
            "output_mode": "stdout",
            "model_flag": "--model",
            "effort_flag": "--effort {level}",
            "resume_flag_style": "flag",
            "safety_flags": ["--permission-mode", "plan"],
        },
    },
    "copilot": {
        "binary": "copilot",
        "effort_map": {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh"},
        "effort_default": "medium",
        "model_aliases": {},
        # Default model is "GPT-5.4 mini" (verified April 2026); the CLI does
        # not expose a model-listing command, so this is the documented set
        # from peer-plan-review/references/copilot.md.
        "known_models": ["GPT-5.4 mini"],
        "resume_supported": True,
        "build_cmd": build_copilot_cmd,
        "caps": {
            "prompt_mode": "stdin",
            "output_mode": "stdout",
            "model_flag": "--model",
            "effort_flag": "--reasoning-effort {level}",
            "resume_flag_style": "flag_eq",
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
            "mimo": "opencode-go/mimo-v2.5",
            "mimo-pro": "opencode-go/mimo-v2.5-pro",
            "qwen": "opencode-go/qwen3.7-plus",
            "glm": "opencode-go/glm-5.2",
            "minimax": "opencode-go/minimax-m3",
        },
        "resume_supported": True,
        "build_cmd": build_opencode_cmd,
        "caps": {
            "prompt_mode": "stdin",
            "output_mode": "stdout",
            "model_flag": "-m",
            "effort_flag": "--variant {level}",
            "resume_flag_style": "flag",
            "safety_flags": ["--dangerously-skip-permissions"],
        },
        # opencode-go model discovery command — used by --list-models
        "list_models_cmd": ["opencode", "models", "opencode-go"],
    },
    "agy": {
        "binary": "agy",
        "effort_map": {"low": "Low", "medium": "Medium", "high": "High", "xhigh": "High"},
        "effort_default": "high",
        "model_aliases": {
            # Only Gemini 3.5 Flash returns output in headless --print (verified
            # 2026-06-14); effort picks the Low/Medium/High variant.
            "flash": "Gemini 3.5 Flash",
        },
        "resume_supported": True,
        "build_cmd": build_agy_cmd,
        "caps": {
            "prompt_mode": "stdin",
            "output_mode": "stdout",
            "model_flag": "--model",
            # Effort is part of the model name, not a flag (see _AGY_FAMILIES).
            "effort_flag": "model_variant",
            "resume_flag_style": "flag",
            # EXPERIMENTAL: agy print mode auto-approves tools; --sandbox only
            # contains terminal commands. NOT guaranteed read-only like the rest.
            "safety_flags": ["--sandbox"],
            "read_only": False,
        },
        # agy exposes effort via the model name; surface the real model list.
        "list_models_cmd": ["agy", "models"],
    },
}

# Mirror the top-level binary/resume_supported into each entry's caps dict so
# callers can read either location (see the caps docstring above). Authors
# only ever edit the top-level values.
for _spec in PROVIDERS.values():
    _spec["caps"]["binary"] = _spec["binary"]
    _spec["caps"]["resume_supported"] = _spec["resume_supported"]
del _spec


def get_provider(name, allowed=None):
    """Look up a provider by name.

    If ``allowed`` is provided (an iterable of accepted provider names),
    raise ValueError when ``name`` is not in that set. This lets a
    consumer declare a subset of providers its CLI accepts without
    having to re-implement provider lookup.

    Raises KeyError for genuinely unknown providers (regardless of
    ``allowed``).
    """
    if allowed is not None and name not in allowed:
        accepted = ", ".join(sorted(allowed))
        raise ValueError(f"unknown reviewer; accepted: {accepted}")
    return PROVIDERS[name]
