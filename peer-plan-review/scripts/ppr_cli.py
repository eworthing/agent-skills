#!/usr/bin/env python3
"""
ppr_cli.py — CLI front-end helpers for run_review.py.

argparse wiring, model-alias validation/listing, and provider self-check —
the non-run-loop CLI surface split out of run_review.py. Re-imported back
into run_review so mock.patch("run_review.<name>") targets and the public
`from run_review import self_check` entrypoint keep resolving.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _common.providers import PROVIDERS

# Friendly reviewer aliases normalized to canonical provider keys at the CLI
# boundary (the registry key stays `agy`; `antigravity` is accepted too).
REVIEWER_ALIASES = {"antigravity": "agy"}


def parse_args():
    p = argparse.ArgumentParser(description="Peer plan review CLI adapter")
    p.add_argument(
        "--reviewer",
        required=False,
        choices=list(PROVIDERS.keys()) + list(REVIEWER_ALIASES),
        help="Reviewer backend",
    )
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
    p.add_argument("--timeout", type=int, default=1200, help="Timeout in seconds (default: 1200)")
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
        "--codex-home-manifest",
        default=None,
        help="Review-scoped manifest path tracking per-run Codex homes for "
        "concurrency-safe isolation + terminal cleanup (defaults to a path "
        "derived from --session-file).",
    )
    p.add_argument(
        "--summary-file",
        default=None,
        help="Path to write machine-readable per-round summary JSON",
    )
    args = p.parse_args()
    if args.reviewer:
        args.reviewer = REVIEWER_ALIASES.get(args.reviewer, args.reviewer)
    return args


def self_check(reviewer):
    """Verify the reviewer CLI is installed and responsive."""
    provider = PROVIDERS.get(reviewer)
    if not provider:
        print(f"Unknown reviewer: {reviewer}", file=sys.stderr)
        return False
    binary = provider["binary"]

    path = shutil.which(binary)
    if not path:
        print(f"FAIL: {binary} not found in PATH", file=sys.stderr)
        return False

    print(f"OK: {binary} found at {path}")

    try:
        help_cmd = [binary, "run", "--help"] if reviewer == "opencode" else [binary, "--help"]
        result = subprocess.run(
            help_cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode == 0:
            help_text = "\n".join(filter(None, (result.stdout, result.stderr)))
            if reviewer == "opencode" and "--auto" not in help_text:
                print(
                    "FAIL: opencode run --help does not advertise required --auto flag",
                    file=sys.stderr,
                )
                return False
            print(f"OK: {' '.join(help_cmd)} succeeded")
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


def _validate_model(args):
    """Normalize model alias or warn if unrecognized."""
    if not args.model or not args.reviewer:
        return
    aliases = PROVIDERS.get(args.reviewer, {}).get("model_aliases", {})
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


def _list_models(provider):
    """One-line --list-models description for ``provider``.

    Precedence: live model_aliases > provider-native list_models_cmd (live
    query) > known_models (doc-sourced, not live-queried) > raw-IDs-only.
    """
    spec = PROVIDERS.get(provider, {})
    aliases = spec.get("model_aliases", {})
    if aliases:
        alias_strs = [f"{k} ({v})" for k, v in sorted(aliases.items())]
        return f"{provider}: {', '.join(alias_strs)}"

    list_cmd = spec.get("list_models_cmd")
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
                models = [m.strip() for m in result.stdout.strip().splitlines() if m.strip()]
                return f"{provider}: {', '.join(models)}"
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            pass

    known_models = spec.get("known_models")
    if known_models:
        return f"{provider}: {', '.join(known_models)} (known models — not live-queried)"

    return f"{provider}: (raw model IDs only — no aliases)"
