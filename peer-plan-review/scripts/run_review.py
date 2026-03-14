#!/usr/bin/env python3
"""
run_review.py — Deterministic CLI adapter for peer-plan-review skill.

Dispatches review requests to Codex, Gemini, Claude Code, or Copilot CLI
with provider-specific flags for headless, read-only, no-hang operation.
Supports exec, resume, session tracking, and self-check.
"""

import argparse
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
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


def parse_args():
    p = argparse.ArgumentParser(description="Peer plan review CLI adapter")
    p.add_argument("--reviewer", required=False, choices=BINARIES.keys(), help="Reviewer backend")
    p.add_argument("--plan-file", help="Path to plan markdown file")
    p.add_argument("--prompt-file", help="Path to review prompt file")
    p.add_argument("--output-file", help="Path to write reviewer response")
    p.add_argument("--session-file", help="Path to session metadata JSON")
    p.add_argument("--events-file", help="Path to event stream log")
    p.add_argument("--model", default=None, help="Model override")
    p.add_argument(
        "--effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Reasoning effort level",
    )
    p.add_argument("--resume", action="store_true", help="Resume previous session")
    p.add_argument("--timeout", type=int, default=600, help="Timeout in seconds (default: 600)")
    p.add_argument(
        "--self-check", action="store_true", help="Verify CLI binary and flags, exit 0/1"
    )
    p.add_argument(
        "--list-models",
        action="store_true",
        help="Print known model aliases for --reviewer and exit",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------


def self_check(reviewer):
    """Verify the reviewer CLI is installed and responsive."""
    binary = BINARIES.get(reviewer)
    if not binary:
        print(f"Unknown reviewer: {reviewer}", file=sys.stderr)
        return False

    path = shutil.which(binary)
    if not path:
        print(f"FAIL: {binary} not found in PATH", file=sys.stderr)
        return False

    print(f"OK: {binary} found at {path}")

    try:
        result = subprocess.run(
            [binary, "--help"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode == 0:
            print(f"OK: {binary} --help succeeded")
            return True
        if reviewer == "copilot" and "SecItemCopyMatching failed -50" in (result.stderr or ""):
            print(
                "WARN: copilot is installed but --help failed with a "
                "macOS Keychain error in this automation context. "
                "Treating install check as inconclusive success.",
                file=sys.stderr,
            )
            return True
        print(f"FAIL: {binary} --help exited {result.returncode}", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        if reviewer == "gemini":
            print(
                "WARN: gemini is installed but --help timed out in this "
                "non-interactive automation context. Treating install "
                "check as inconclusive success.",
                file=sys.stderr,
            )
            return True
        print(f"FAIL: {binary} --help timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"FAIL: {binary} --help error: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


def load_session(session_file):
    """Load session metadata from JSON file."""
    if not session_file or not Path(session_file).exists():
        return {}
    try:
        with Path(session_file).open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_session(session_file, data):
    """Save session metadata to JSON file."""
    if not session_file:
        return
    try:
        with Path(session_file).open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print(f"Warning: could not save session: {e}", file=sys.stderr)


def _codex_session_files():
    """Return set of all Codex session file paths."""
    codex_home = os.environ.get("CODEX_HOME", str(Path("~/.codex").expanduser()))
    sessions_dir = Path(codex_home) / "sessions"
    if not sessions_dir.is_dir():
        return set()
    result = set()
    for root, _, files in os.walk(sessions_dir):
        for f in files:
            if f.endswith(".jsonl"):
                result.add(str(Path(root) / f))
    return result


def _parse_codex_session_id(session_file):
    """Extract session UUID from first line of a Codex session file."""
    try:
        with Path(session_file).open(encoding="utf-8") as fh:
            first = json.loads(fh.readline())
            if first.get("type") == "session_meta":
                sid = first.get("payload", {}).get("id")
                # Validate cwd matches to avoid binding to a concurrent session
                cwd = first.get("payload", {}).get("cwd", "")
                if cwd and Path(cwd).resolve() != Path.cwd().resolve():
                    return None
                return sid
    except (json.JSONDecodeError, KeyError, OSError):
        pass
    return None


def extract_session_id_json(output_file, field="session_id"):
    """Extract session_id from JSON output."""
    if not output_file or not Path(output_file).exists():
        return None
    try:
        with Path(output_file).open(encoding="utf-8") as f:
            data = json.load(f)
            return data.get(field)
    except (json.JSONDecodeError, OSError):
        pass
    return None


def extract_session_id_copilot(output_file):
    """Parse sessionId from Copilot JSONL result event."""
    if not output_file or not Path(output_file).exists():
        return None
    try:
        with Path(output_file).open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event.get("type") == "result":
                        return event.get("sessionId")
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return None


def extract_metadata(output_file, events_file, reviewer, codex_session_file=None):
    """Extract model/effort metadata from structured output before text rewrite.

    Returns dict with 'model' and optionally 'effort' if discoverable.
    Must be called BEFORE extract_text_from_output (which overwrites the file).
    """
    meta = {}

    # Claude / Gemini: single JSON object
    if reviewer in ("claude", "gemini") and output_file and Path(output_file).exists():
        try:
            with Path(output_file).open(encoding="utf-8") as f:
                data = json.load(f)
            if reviewer == "claude":
                # Claude JSON: {"result": "...", "model": "claude-opus-4-6", ...}
                if data.get("model"):
                    meta["model"] = data["model"]
            elif reviewer == "gemini":
                # Gemini JSON: {"stats": {"models": {"gemini-3-pro-preview": {...}}}}
                # The model name is the first key in stats.models.
                stats = data.get("stats", {})
                if isinstance(stats, dict):
                    models = stats.get("models", {})
                    if isinstance(models, dict) and models:
                        model_name = next(iter(models))
                        meta["model"] = model_name
                        # Record thinking tokens as telemetry (not used
                        # for effort — actual usage doesn't reflect the
                        # configured budget reliably).
                        model_stats = models[model_name]
                        thoughts = model_stats.get("tokens", {}).get("thoughts", 0)
                        if thoughts and isinstance(thoughts, (int, float)):
                            meta["thinking_tokens"] = int(thoughts)
                if not meta.get("model") and data.get("model"):
                    meta["model"] = data["model"]
        except (json.JSONDecodeError, OSError):
            pass

    # Copilot: JSONL — model is in session.tools_updated or
    # tool.execution_complete events under data.model
    if reviewer == "copilot" and output_file and Path(output_file).exists():
        try:
            with Path(output_file).open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        data = event.get("data", {})
                        if isinstance(data, dict) and data.get("model"):
                            meta["model"] = data["model"]
                            break
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    # Codex: model/effort live in the on-disk session file (turn_context
    # event), NOT in the stdout JSONL stream.  Fall back to the stdout
    # events file if no on-disk session file was provided.
    if reviewer == "codex":
        sources = [s for s in (codex_session_file, events_file) if s and Path(s).exists()]
        for source in sources:
            try:
                with Path(source).open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            # turn_context has model + effort (on-disk only)
                            if event.get("type") == "turn_context":
                                payload = event.get("payload", {})
                                if payload.get("model"):
                                    meta["model"] = payload["model"]
                                if payload.get("effort"):
                                    meta["effort"] = payload["effort"]
                                break
                            # session_meta may have model in payload
                            if event.get("type") == "session_meta":
                                model = event.get("payload", {}).get("model")
                                if model:
                                    meta["model"] = model
                        except json.JSONDecodeError:
                            continue
            except OSError:
                pass
            if meta.get("model"):
                break

    return meta


def extract_text_from_output(output_file, reviewer):
    """Extract review text from structured output and rewrite as plain text."""
    if not output_file or not Path(output_file).exists():
        return
    try:
        with Path(output_file).open(encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return

        if reviewer == "copilot":
            # JSONL: one JSON object per line
            messages = []
            for line in content.splitlines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if event.get("type") == "assistant.message":
                        msg = event.get("data", {}).get("content", "")
                        if msg:
                            messages.append(msg)
                except json.JSONDecodeError:
                    continue
            text = "\n".join(messages) if messages else content
        else:
            # Single JSON object (Claude, Gemini)
            data = json.loads(content)
            if reviewer == "claude":
                text = data.get("result", content)
            elif reviewer == "gemini":
                text = data.get("response", content)
            else:
                text = content

        with Path(output_file).open("w", encoding="utf-8") as f:
            f.write(text if isinstance(text, str) else json.dumps(text))
    except (json.JSONDecodeError, OSError) as e:
        print(
            f"Warning: could not extract review text from {output_file} "
            f"for {reviewer}: {e}. File left as raw output.",
            file=sys.stderr,
        )


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
        cmd.extend(["resume", session_id])
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
    if prompt_text:
        cmd.extend(["-p", prompt_text])

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


# ---------------------------------------------------------------------------
# Process tree management
# ---------------------------------------------------------------------------


def _kill_tree(proc):
    """Kill process and all descendants."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            capture_output=True,
        )
        proc.wait()
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        proc.wait()


def _popen_session_kwargs():
    """Return Popen kwargs for process-group isolation, per platform."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


# Module-level for signal handler access
_active_proc = None


def _signal_handler(signum, _frame):
    if _active_proc and _active_proc.poll() is None:
        _kill_tree(_active_proc)
    sys.exit(128 + signum)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def run_review(args):
    """Execute the review command for the selected provider."""
    global _active_proc

    reviewer = args.reviewer
    session = load_session(args.session_file) if args.resume else {}
    session_id = session.get("session_id") if args.resume else None

    # Build provider-specific command
    builders = {
        "codex": build_codex_cmd,
        "gemini": build_gemini_cmd,
        "claude": build_claude_cmd,
        "copilot": build_copilot_cmd,
    }
    cmd = builders[reviewer](args, session_id)

    # Build environment
    env = os.environ.copy()

    # Claude-specific env vars
    if reviewer == "claude":
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"

    # Gemini effort via temp settings overlay
    # Clone the real config dir so auth, extensions, and other state survive,
    # then overlay the effort-specific settings.json.
    gemini_config_dir = None
    if reviewer == "gemini" and args.effort:
        budget = EFFORT_MAP["gemini"].get(args.effort)
        if budget:
            gemini_config_dir = tempfile.mkdtemp(prefix="ppr-gemini-")
            source_dir = os.environ.get(
                "GEMINI_CONFIG_DIR",
                str(Path("~/.gemini").expanduser()),
            )
            # Copy existing config if present (auth, extensions, etc.)
            if Path(source_dir).is_dir():
                shutil.copytree(source_dir, gemini_config_dir, dirs_exist_ok=True)
            # Overlay effort settings (merges into existing settings.json)
            settings_path = Path(gemini_config_dir) / "settings.json"
            try:
                existing = {}
                if settings_path.exists():
                    with settings_path.open(encoding="utf-8") as f:
                        try:
                            existing = json.load(f)
                        except json.JSONDecodeError:
                            existing = {}
                existing["thinkingConfig"] = {"thinkingBudget": budget}
                with settings_path.open("w", encoding="utf-8") as f:
                    json.dump(existing, f)
                env["GEMINI_CONFIG_DIR"] = gemini_config_dir
            except OSError as e:
                print(f"Warning: could not write Gemini settings: {e}", file=sys.stderr)

    # Prepare stdin for Codex (prompt via stdin)
    stdin_data = None
    if reviewer == "codex":
        stdin_data = read_prompt(args.prompt_file)

    # Snapshot Codex session files before exec for race-safe ID extraction
    codex_sessions_before = None
    if reviewer == "codex":
        codex_sessions_before = _codex_session_files()

    # Set up signal handlers for cleanup
    prev_sigterm = signal.getsignal(signal.SIGTERM)
    prev_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    try:
        print(f"Running: {reviewer} review...", file=sys.stderr)

        # Truncate output file so stale data from a prior round doesn't
        # make has_output think the current round produced output.
        if args.output_file and Path(args.output_file).exists():
            Path(args.output_file).write_text("")

        if stdin_data is not None:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                env=env,
                **_popen_session_kwargs(),
            )
        else:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                env=env,
                **_popen_session_kwargs(),
            )
        _active_proc = proc

        try:
            stdout, stderr = proc.communicate(input=stdin_data, timeout=args.timeout)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            # Drain pipes to avoid FD leak (process is already dead)
            proc.communicate()
            print(f"Reviewer timed out after {args.timeout}s", file=sys.stderr)
            return 1

        # Write stdout to output file for non-Codex providers
        # (Codex uses --output-last-message)
        if reviewer != "codex" and stdout and args.output_file:
            with Path(args.output_file).open("w", encoding="utf-8") as f:
                f.write(stdout)

        # Write Codex JSONL events to events file
        if reviewer == "codex" and stdout and args.events_file:
            with Path(args.events_file).open("w", encoding="utf-8") as f:
                f.write(stdout)

        # Extract session ID
        new_session_id = None
        codex_session_path = None
        if reviewer == "codex":
            after = _codex_session_files()
            new_files = after - (codex_sessions_before or set())
            # Scan all new files for ones whose cwd matches ours.
            # If multiple match, same-cwd concurrency is ambiguous —
            # skip metadata extraction rather than risk cross-contamination.
            cwd_matches = []
            for candidate in sorted(new_files, key=lambda p: Path(p).stat().st_mtime, reverse=True):
                parsed_id = _parse_codex_session_id(candidate)
                if parsed_id:
                    cwd_matches.append((candidate, parsed_id))
            if len(cwd_matches) == 1:
                codex_session_path, new_session_id = cwd_matches[0]
            elif len(cwd_matches) > 1:
                # Ambiguous: multiple same-cwd sessions created during
                # this run. Skip both session_id and metadata extraction
                # to avoid cross-contamination and resume poisoning.
                print(
                    "Warning: multiple concurrent Codex sessions "
                    "detected in same cwd; skipping session and "
                    "metadata extraction",
                    file=sys.stderr,
                )
            # On resume, no new file is created — find the existing one
            if not codex_session_path and args.resume and session_id:
                for sf in codex_sessions_before or set():
                    if _parse_codex_session_id(sf) == session_id:
                        codex_session_path = sf
                        break
        elif reviewer == "copilot":
            new_session_id = extract_session_id_copilot(args.output_file)
        elif reviewer in ("gemini", "claude"):
            new_session_id = extract_session_id_json(args.output_file)

        # Extract model metadata from structured output (before text rewrite)
        meta = extract_metadata(
            args.output_file, args.events_file, reviewer, codex_session_file=codex_session_path
        )

        # Extract plain text from structured output
        if reviewer in ("claude", "gemini", "copilot"):
            extract_text_from_output(args.output_file, reviewer)

        # Resolve actual model: prefer detected > session (prior round)
        # > user-specified > "default"
        actual_model = meta.get("model") or session.get("model") or args.model or "default"

        # Save session metadata
        # Effort: detected (from reviewer output) is the canonical value
        # because it reflects what was actually used. Fall back to
        # user-requested, then provider default.
        actual_effort = (
            meta.get("effort") or args.effort or _EFFORT_DEFAULTS.get(reviewer, "default")
        )
        round_num = session.get("round", 0) + 1
        session_data = {
            "session_id": new_session_id or session_id,
            "reviewer": reviewer,
            "model": actual_model,
            "model_requested": args.model or "default",
            "effort": actual_effort,
            "effort_requested": args.effort or "default",
            "effort_source": (
                "detected"
                if meta.get("effort")
                else "requested"
                if args.effort
                else "provider_default"
            ),
            "round": round_num,
        }
        if meta.get("thinking_tokens") is not None:
            session_data["thinking_tokens"] = meta["thinking_tokens"]
        save_session(args.session_file, session_data)

        if returncode != 0:
            print(f"Reviewer exited with code {returncode}", file=sys.stderr)
            if stderr:
                print(stderr, file=sys.stderr)

            # Only retry as fresh exec when resume was requested AND
            # no output was produced (i.e. the session itself failed to
            # resume, not a crash/warning during review).  If output
            # exists, the provider ran — retrying would duplicate the
            # review and waste tokens.
            output_path = Path(args.output_file) if args.output_file else None
            has_output = output_path and output_path.exists() and output_path.stat().st_size > 0
            if args.resume and session_id and not has_output:
                print("Resume failed, falling back to fresh exec...", file=sys.stderr)
                args.resume = False
                return run_review(args)

            return returncode

        return 0

    except FileNotFoundError:
        print(f"Binary not found: {BINARIES[reviewer]}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Execution error: {e}", file=sys.stderr)
        return 1
    finally:
        _active_proc = None
        signal.signal(signal.SIGTERM, prev_sigterm)
        signal.signal(signal.SIGINT, prev_sigint)
        # Clean up Gemini temp config
        if gemini_config_dir:
            shutil.rmtree(gemini_config_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _validate_model(args):
    """Normalize model alias or warn if unrecognized."""
    if not args.model or not args.reviewer:
        return
    aliases = MODEL_ALIASES.get(args.reviewer, {})
    if not aliases:
        # Providers with no aliases (codex, copilot): pass through silently
        return
    # Case-insensitive alias lookup only — raw IDs pass through unchanged
    model_lower = args.model.lower()
    matched = {k: v for k, v in aliases.items() if k.lower() == model_lower}
    if matched:
        args.model = next(iter(matched.values()))
    else:
        known = sorted(aliases.keys())
        prefix_matches = [k for k in known if k.startswith(model_lower)]
        if len(prefix_matches) == 1:
            suggestion = f" Did you mean '{prefix_matches[0]}'?"
        elif prefix_matches:
            suggestion = f" Did you mean one of: {', '.join(prefix_matches)}?"
        else:
            suggestion = ""
        print(
            f"Warning: '{args.model}' is not a recognized shorthand for "
            f"{args.reviewer} (known: {', '.join(known)}).{suggestion} "
            f"Passing through as raw model ID.",
            file=sys.stderr,
        )


def main():
    args = parse_args()

    _validate_model(args)

    if args.self_check:
        if not args.reviewer:
            # Check all providers
            all_ok = True
            for r in BINARIES:
                if not self_check(r):
                    all_ok = False
            sys.exit(0 if all_ok else 1)
        else:
            sys.exit(0 if self_check(args.reviewer) else 1)

    if args.list_models:
        providers = [args.reviewer] if args.reviewer else list(MODEL_ALIASES.keys())
        for provider in providers:
            aliases = MODEL_ALIASES.get(provider, {})
            if aliases:
                print(f"{provider}: {', '.join(sorted(aliases.keys()))}")
            else:
                print(f"{provider}: (raw model IDs only — no aliases)")
        sys.exit(0)

    if not args.reviewer:
        print("--reviewer is required (codex, gemini, claude, copilot)", file=sys.stderr)
        sys.exit(1)

    if not args.prompt_file:
        print("--prompt-file is required", file=sys.stderr)
        sys.exit(1)

    # Validate input files exist
    for arg_name, fpath in [("--plan-file", args.plan_file), ("--prompt-file", args.prompt_file)]:
        if fpath and not Path(fpath).exists():
            print(f"Error: {arg_name} not found: {fpath}", file=sys.stderr)
            sys.exit(1)

    # Validate output paths: directory must exist, and either the file
    # already exists and is writable, or the directory is writable (so
    # the file can be created).  On POSIX, writing to an existing file
    # depends on file permissions, not directory permissions.
    for arg_name, fpath in [
        ("--output-file", args.output_file),
        ("--session-file", args.session_file),
        ("--events-file", args.events_file),
    ]:
        if fpath:
            parent = Path(fpath).parent
            if not parent.is_dir():
                print(f"Error: directory for {arg_name} does not exist: {parent}", file=sys.stderr)
                sys.exit(1)
            if Path(fpath).exists():
                if not os.access(fpath, os.W_OK):
                    print(f"Error: {arg_name} exists but is not writable: {fpath}", file=sys.stderr)
                    sys.exit(1)
            elif not os.access(parent, os.W_OK):
                print(f"Error: directory for {arg_name} is not writable: {parent}", file=sys.stderr)
                sys.exit(1)

    # Verify binary is installed
    binary = BINARIES[args.reviewer]
    if not shutil.which(binary):
        print(f"Error: {binary} not found in PATH. Install it first.", file=sys.stderr)
        sys.exit(1)

    rc = run_review(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
