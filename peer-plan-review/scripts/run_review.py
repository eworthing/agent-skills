#!/usr/bin/env python3
"""
run_review.py — Deterministic CLI adapter for peer-plan-review skill.

Dispatches review requests to Codex, Gemini, Claude Code, or Copilot CLI
with provider-specific flags for headless, read-only, no-hang operation.
Supports exec, resume, session tracking, and self-check.
"""

import argparse
import contextlib
import copy
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from ppr_io import (
    extract_text_from_output,
    load_session,
    probe_writable,
    save_session,
    validate_prompt_file,
    write_summary,
)
from ppr_log import EventLogger
from ppr_metadata import (
    _codex_session_files,
    _extract_opencode_metadata_via_export,
    _parse_codex_session_id,
    compute_plan_metadata,
    extract_metadata,
    extract_session_id_copilot,
    extract_session_id_json,
    extract_session_id_opencode,
)
from ppr_process import _kill_tree, _popen_session_kwargs

# ---------------------------------------------------------------------------
# Re-exports from submodules (preserves mock.patch("run_review.X") paths)
# ---------------------------------------------------------------------------
from ppr_providers import (  # noqa: F401
    _EFFORT_DEFAULTS,
    BINARIES,
    BUILDERS,
    EFFORT_MAP,
    MODEL_ALIASES,
    PROVIDER_CAPS,
    PROVIDERS,
    build_claude_cmd,
    build_codex_cmd,
    build_copilot_cmd,
    build_gemini_cmd,
    build_opencode_cmd,
    get_provider,
    read_prompt,
)


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
    p.add_argument("--error-log", default=None, help="Path to append-only JSONL error/event log")
    p.add_argument("--review-id", default=None, help="Review ID for log correlation across rounds")
    p.add_argument(
        "--summary-file",
        default=None,
        help="Path to write machine-readable per-round summary JSON",
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


# Process tree management has been moved to ppr_process.py.
# It is re-exported above for backward compatibility.

# Module-level for signal handler access
_active_proc = None


def _signal_handler(signum, _frame):
    if _active_proc and _active_proc.poll() is None:
        _kill_tree(_active_proc)
    sys.exit(128 + signum)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def run_review(args, logger=None):
    """Execute the review command for the selected provider."""
    global _active_proc

    if logger is None:
        logger = EventLogger()

    reviewer = args.reviewer
    resume_requested = args.resume  # snapshot — args is never mutated
    use_resume = resume_requested
    fallback_used = False

    session = load_session(args.session_file) if use_resume else {}
    session_id = session.get("session_id") if use_resume else None

    logger.log(
        "execution_start",
        provider=reviewer,
        context={
            "model": args.model,
            "effort": args.effort,
            "resume": resume_requested,
            "session_id": session_id,
        },
    )

    # Build environment (shared across attempts)
    env = os.environ.copy()
    if reviewer == "claude":
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"

    # Gemini runs through a temp config overlay. The review runner needs auth
    # and durable settings, but not mutable local approval policy, sessions,
    # caches, or extensions from the user's real Gemini home.
    gemini_config_dir = None
    if reviewer == "gemini":
        budget = EFFORT_MAP["gemini"].get(args.effort) if args.effort else None
        gemini_config_dir = tempfile.mkdtemp(prefix="ppr-gemini-")
        source_dir = os.environ.get(
            "GEMINI_CONFIG_DIR",
            str(Path("~/.gemini").expanduser()),
        )
        source_path = Path(source_dir)
        if source_path.is_dir():
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

    # Prepare prompt stdin for providers configured for stdin prompting.
    stdin_data = None
    if PROVIDER_CAPS[reviewer].get("prompt_mode") == "stdin":
        stdin_data = read_prompt(args.prompt_file)

    # Snapshot Codex session files before exec
    codex_sessions_before = None
    if reviewer == "codex":
        codex_sessions_before = _codex_session_files()

    # Set up signal handlers
    prev_sigterm = signal.getsignal(signal.SIGTERM)
    prev_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    try:
        # Two-attempt loop: at most one resume attempt + one fresh attempt
        returncode = 1
        for attempt in range(2):
            if attempt == 0 and use_resume and session_id:
                logger.log("resume_attempted", provider=reviewer, context={"session_id": session_id})

            # Build provider-specific command using use_resume (not args.resume).
            # Create a lightweight namespace for the builder that reflects
            # current resume state without mutating the original args.
            build_args = copy.copy(args)
            build_args.resume = use_resume
            cmd = BUILDERS[reviewer](build_args, session_id)

            print(f"Running: {reviewer} review...", file=sys.stderr)

            # Truncate output file so stale data doesn't persist
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
                proc.communicate()
                print(f"Reviewer timed out after {args.timeout}s", file=sys.stderr)
                logger.log("provider_timeout", provider=reviewer, context={"timeout": args.timeout})
                return 1

            # Write stdout to output file for non-Codex providers
            if reviewer != "codex" and stdout and args.output_file:
                with Path(args.output_file).open("w", encoding="utf-8") as f:
                    f.write(stdout)

            # Write Codex JSONL events to events file
            if reviewer == "codex" and stdout and args.events_file:
                with Path(args.events_file).open("w", encoding="utf-8") as f:
                    f.write(stdout)

            # Check for resume fallback condition
            if returncode != 0:
                print(f"Reviewer exited with code {returncode}", file=sys.stderr)
                if stderr:
                    print(stderr, file=sys.stderr)

                output_path = Path(args.output_file) if args.output_file else None
                has_output = output_path and output_path.exists() and output_path.stat().st_size > 0

                if attempt == 0 and use_resume and session_id and not has_output:
                    print("Resume failed, falling back to fresh exec...", file=sys.stderr)
                    logger.log(
                        "resume_fallback",
                        provider=reviewer,
                        error=f"Resume failed with exit code {returncode}",
                        context={
                            "session_id": session_id,
                            "has_output": False,
                            "stderr": (stderr or "")[:500],
                        },
                    )

                    use_resume = False
                    session_id = None
                    fallback_used = True
                    continue  # retry as fresh exec
                else:
                    logger.log(
                        "provider_error",
                        provider=reviewer,
                        error=f"Exit code {returncode}",
                        context={"stderr": (stderr or "")[:500]},
                    )

            break  # success or non-recoverable failure

        # --- Post-execution: extract metadata and save session ---

        # Extract session ID
        new_session_id = None
        codex_session_path = None
        if reviewer == "codex":
            after = _codex_session_files()
            new_files = after - (codex_sessions_before or set())
            valid_files = [p for p in new_files if Path(p).is_file()]
            cwd_matches = []
            for candidate in sorted(valid_files, key=lambda p: Path(p).stat().st_mtime, reverse=True):
                parsed_id = _parse_codex_session_id(candidate)
                if parsed_id:
                    cwd_matches.append((candidate, parsed_id))
            if len(cwd_matches) == 1:
                codex_session_path, new_session_id = cwd_matches[0]
            elif len(cwd_matches) > 1:
                print(
                    "Warning: multiple concurrent Codex sessions "
                    "detected in same cwd; skipping session and "
                    "metadata extraction",
                    file=sys.stderr,
                )
            if not codex_session_path and resume_requested and session.get("session_id"):
                for sf in codex_sessions_before or set():
                    if _parse_codex_session_id(sf) == session.get("session_id"):
                        codex_session_path = sf
                        break
        elif reviewer == "copilot":
            new_session_id = extract_session_id_copilot(args.output_file)
        elif reviewer == "opencode":
            new_session_id = extract_session_id_opencode(args.output_file)
        elif reviewer in ("gemini", "claude"):
            new_session_id = extract_session_id_json(args.output_file)

        # Read output file content once (eliminates temporal coupling with
        # extract_text_from_output, which overwrites the file)
        output_content = None
        if reviewer in ("claude", "gemini", "copilot", "opencode") and args.output_file:
            out_p = Path(args.output_file)
            if out_p.exists():
                with contextlib.suppress(OSError):
                    output_content = out_p.read_text(encoding="utf-8", errors="replace")

        # Opencode: extract metadata via subprocess export (explicit side-effect)
        opencode_export_meta = {}
        if reviewer == "opencode" and new_session_id:
            opencode_export_meta = _extract_opencode_metadata_via_export(new_session_id)

        # Extract model metadata (uses pre-read content for claude/gemini/copilot)
        meta = extract_metadata(
            args.output_file, args.events_file, reviewer,
            codex_session_file=codex_session_path,
            output_content=output_content, logger=logger
        )
        if opencode_export_meta:
            meta.update(opencode_export_meta)

        # Extract plain text from structured output (uses pre-read content)
        if reviewer in ("claude", "gemini", "copilot", "opencode"):
            extract_text_from_output(args.output_file, reviewer, content=output_content)

        # Resolve actual model and effort
        actual_model = meta.get("model") or session.get("model") or args.model or "default"
        actual_effort = (
            meta.get("effort") or args.effort or _EFFORT_DEFAULTS.get(reviewer, "default")
        )
        round_num = session.get("round", 0) + 1

        # Build session data with resume metadata
        session_data = {
            "session_id": new_session_id or session.get("session_id"),
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
            "resume_requested": resume_requested,
            "resume_supported": PROVIDER_CAPS.get(reviewer, {}).get("resume_supported", False),
            "resume_attempted": resume_requested and session.get("session_id") is not None,
            "resume_fallback_used": fallback_used,
            "resume_reason": (
                "fallback_to_fresh" if fallback_used
                else "session_found" if resume_requested and session.get("session_id")
                else "no_session_id" if resume_requested
                else "fresh_exec"
            ),
        }
        if meta.get("thinking_tokens") is not None:
            session_data["thinking_tokens"] = meta["thinking_tokens"]
        if args.error_log:
            session_data["error_log"] = args.error_log

        # Plan-file metadata
        plan_meta = compute_plan_metadata(args.plan_file)
        if plan_meta:
            session_data.update(plan_meta)

        save_session(args.session_file, session_data)

        if args.summary_file:
            write_summary(args.summary_file, args.output_file, session_data)

        if returncode == 0:
            logger.log("execution_complete", provider=reviewer, context={"returncode": 0})
        return returncode

    except FileNotFoundError:
        print(f"Binary not found: {BINARIES[reviewer]}", file=sys.stderr)
        logger.log("binary_not_found", provider=reviewer, error=BINARIES[reviewer])
        return 1
    except OSError as e:
        print(f"Execution error: {e}", file=sys.stderr)
        logger.log("provider_error", provider=reviewer, error=str(e))
        return 1
    finally:
        _active_proc = None
        signal.signal(signal.SIGTERM, prev_sigterm)
        signal.signal(signal.SIGINT, prev_sigint)
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
                alias_strs = [
                    f"{k} ({v})" for k, v in sorted(aliases.items())
                ]
                print(f"{provider}: {', '.join(alias_strs)}")
            else:
                # Try provider-native model listing for empty-alias providers
                p = PROVIDERS.get(provider, {})
                list_cmd = p.get("list_models_cmd")
                if list_cmd:
                    try:
                        result = subprocess.run(
                            list_cmd,
                            capture_output=True,
                            encoding="utf-8",
                            errors="replace",
                            timeout=15,
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            models = [
                                m.strip() for m in result.stdout.strip().splitlines()
                                if m.strip()
                            ]
                            print(f"{provider}: {', '.join(models)}")
                        else:
                            print(f"{provider}: (raw model IDs only — no aliases)")
                    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
                        print(f"{provider}: (raw model IDs only — no aliases)")
                else:
                    print(f"{provider}: (raw model IDs only — no aliases)")
        sys.exit(0)

    if not args.reviewer:
        print("--reviewer is required (codex, gemini, claude, copilot, opencode)", file=sys.stderr)
        sys.exit(1)

    if not args.prompt_file:
        print("--prompt-file is required", file=sys.stderr)
        sys.exit(1)

    # Validate --error-log requires --review-id
    if args.error_log and not args.review_id:
        print("Error: --review-id is required when --error-log is set", file=sys.stderr)
        sys.exit(1)

    # Validate input files
    if args.plan_file and not Path(args.plan_file).exists():
        print(f"Error: --plan-file not found: {args.plan_file}", file=sys.stderr)
        sys.exit(1)

    # Strict prompt validation: exists, readable, UTF-8, non-empty
    ok, err = validate_prompt_file(args.prompt_file)
    if not ok:
        print(f"Error: --prompt-file {err}", file=sys.stderr)
        sys.exit(1)

    # Validate output paths with real write probes
    for arg_name, fpath in [
        ("--output-file", args.output_file),
        ("--session-file", args.session_file),
        ("--events-file", args.events_file),
    ]:
        if fpath:
            ok, err = probe_writable(fpath)
            if not ok:
                print(f"Error: {arg_name} {err}", file=sys.stderr)
                sys.exit(1)

    # Verify binary is installed
    binary = BINARIES[args.reviewer]
    if not shutil.which(binary):
        print(f"Error: {binary} not found in PATH. Install it first.", file=sys.stderr)
        sys.exit(1)

    logger = EventLogger(args.error_log, review_id=args.review_id)
    rc = run_review(args, logger=logger)
    sys.exit(rc)


if __name__ == "__main__":
    main()
