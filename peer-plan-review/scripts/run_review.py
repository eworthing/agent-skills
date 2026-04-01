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
# Re-exports from submodules (preserves mock.patch("run_review.X") paths)
# ---------------------------------------------------------------------------
from ppr_providers import (  # noqa: F401
    EFFORT_MAP,
    _EFFORT_DEFAULTS,
    MODEL_ALIASES,
    BINARIES,
    build_codex_cmd,
    build_gemini_cmd,
    build_claude_cmd,
    build_copilot_cmd,
    read_prompt,
)
from ppr_io import (  # noqa: F401
    load_session,
    save_session,
    extract_text_from_output,
)
from ppr_metadata import (  # noqa: F401
    extract_metadata,
    extract_session_id_json,
    extract_session_id_copilot,
    _parse_codex_session_id,
    _codex_session_files,
)
from ppr_log import EventLogger  # noqa: F401


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


# Session helpers, metadata extraction, command builders, and text extraction
# have been moved to ppr_io.py, ppr_metadata.py, and ppr_providers.py.
# They are re-exported above for backward compatibility.




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
