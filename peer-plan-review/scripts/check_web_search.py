#!/usr/bin/env python3
"""
check_web_search.py — Manual diagnostic: web-search capability per provider.

Checks whether each provider CLI can perform a live web fetch in headless
mode without hanging on a permission prompt. Not a pytest suite — it invokes
real provider CLIs; run it by hand.

Design: every command is built by calling the SAME command builders
run_review.py uses in production (``PROVIDERS[name]["build_cmd"]`` from the
shared ``_common/providers/registry.py``, fed a minimal argparse.Namespace
produced by ``run_review.parse_args()`` itself). Stdin delivery reuses
``_common.providers.build_stdin`` and non-codex/agy response extraction reuses
``_common.session.io.extract_text_from_output``. Because every provider- and
extraction-specific decision is delegated to the real production code paths,
this script's commands cannot silently drift from what a live review run
would actually execute — there is nothing here to hand-copy out of sync.

Two isolation layers that run_review.py applies for concurrency safety are
intentionally NOT replicated here for simplicity (this is a one-shot
diagnostic, not a production run):
  - Codex: runs against the user's real CODEX_HOME rather than a per-run
    isolated home.
  - Gemini: runs against the user's real Gemini config rather than an
    isolated config-dir overlay.
Neither omission changes the flags under test (sandbox/approval-mode/output
format), only session/config isolation that doesn't matter for a single
ad hoc run.

Usage:
    python3 check_web_search.py                    # check all providers
    python3 check_web_search.py --provider claude   # check one provider
    python3 check_web_search.py --dry-run           # print built argv only
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, SCRIPT_DIR)
from _common.process.tree import _kill_tree, _popen_session_kwargs  # noqa: E402
from _common.providers import PROVIDERS, build_stdin  # noqa: E402
from _common.session import extract_text_from_output  # noqa: E402

import run_review  # noqa: E402 — reuse parse_args() defaults so this
# diagnostic's argv construction can never hand-drift from what a real
# review run executes.

TIMEOUT = 180  # seconds — URL fetch can be slow (Gemini/Copilot take 50-70s)

PROVIDER_NAMES = ["claude", "codex", "gemini", "copilot", "opencode", "agy"]

# The answer ("Wouters") is on the fetched page but never appears in this
# prompt, so a match proves an actual fetch happened rather than the model
# echoing the prompt/URL back or guessing from training data.
PROMPT = (
    "Fetch this URL and read its content: "
    "https://docs.python.org/3/whatsnew/3.13.html "
    "Answer with ONLY the name of the release manager for Python 3.13, as "
    "stated on that page. You MUST actually fetch/read the page content — "
    "do NOT guess from memory. Do NOT use any file tools."
)
EXPECTED_ANSWER = "wouters"

REFUSAL_PHRASES = (
    "cannot fetch",
    "cannot access",
    "unable to access",
    "unable to fetch",
    "no internet",
    "not able to browse",
    "can't access",
    "don't have the ability",
)


def _base_args():
    """A real parse_args() Namespace (all defaults), same technique as
    scripts/tests/_helpers.make_args — so a new run_review.py argument
    flows into this diagnostic automatically instead of needing a
    hand-maintained parallel Namespace that can drift."""
    saved_argv = sys.argv
    sys.argv = ["run_review.py"]
    try:
        return run_review.parse_args()
    finally:
        sys.argv = saved_argv


def build_test_args(reviewer, prompt_file, output_file):
    args = _base_args()
    args.reviewer = reviewer
    args.prompt_file = str(prompt_file)
    args.output_file = str(output_file)
    args.timeout = TIMEOUT
    return args


def build_env(reviewer):
    env = os.environ.copy()
    if reviewer == "claude":
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    return env


def extract_response_text(reviewer, output_file, stdout):
    """Extract plain response text for success/refusal detection.

    codex writes its own --output-last-message file; agy emits plain text on
    stdout with no structured envelope. Every other provider gets routed
    through production's own extract_text_from_output so this diagnostic
    parses output exactly like a real review run does.
    """
    if reviewer == "codex":
        out_p = Path(output_file)
        if out_p.exists():
            text = out_p.read_text(encoding="utf-8", errors="replace").strip()
            return text or "(no output)"
        return (stdout or "").strip() or "(no output)"

    if reviewer == "agy":
        return (stdout or "").strip() or "(no output)"

    if not stdout:
        return "(no output)"
    Path(output_file).write_text(stdout, encoding="utf-8")
    extract_text_from_output(output_file, reviewer, content=stdout)
    try:
        text = Path(output_file).read_text(encoding="utf-8", errors="replace").strip()
        return text or "(no output)"
    except OSError:
        return stdout.strip()


def _cleanup(*paths):
    for p in paths:
        try:
            Path(p).unlink(missing_ok=True)
        except OSError:
            pass


def dry_run(reviewers):
    """Print each provider's built argv + stdin mode without executing."""
    for reviewer in reviewers:
        binary = PROVIDERS[reviewer]["binary"]
        if not shutil.which(binary):
            print(f"{reviewer:8s}: SKIP ({binary} not installed)")
            continue

        prompt_fd, prompt_file = tempfile.mkstemp(prefix=f"ppr-web-dry-{reviewer}-", suffix=".txt")
        output_fd, output_file = tempfile.mkstemp(prefix=f"ppr-web-dry-{reviewer}-out-", suffix=".txt")
        os.close(output_fd)
        try:
            with os.fdopen(prompt_fd, "w", encoding="utf-8") as f:
                f.write(PROMPT)

            args = build_test_args(reviewer, prompt_file, output_file)
            try:
                cmd = PROVIDERS[reviewer]["build_cmd"](args, None)
            except Exception as e:
                print(f"{reviewer:8s}: ERROR building command: {e}")
                continue

            stdin_data = build_stdin(reviewer, prompt_file)
            stdin_desc = f"piped ({len(stdin_data)} bytes)" if stdin_data is not None else "none (argv prompt)"

            print(f"\n{reviewer}:web")
            print(f"  cmd:   {' '.join(cmd)}")
            print(f"  stdin: {stdin_desc}")
        finally:
            _cleanup(prompt_file, output_file)


def run_test(reviewer):
    """Run a single provider's web-fetch test and return a result dict."""
    test_name = f"{reviewer}:web"
    binary = PROVIDERS[reviewer]["binary"]
    if not shutil.which(binary):
        return {"test": test_name, "status": "SKIP", "reason": f"{binary} not installed", "duration": 0}

    prompt_fd, prompt_file = tempfile.mkstemp(prefix=f"ppr-web-test-{reviewer}-", suffix=".txt")
    output_fd, output_file = tempfile.mkstemp(prefix=f"ppr-web-test-{reviewer}-out-", suffix=".txt")
    os.close(output_fd)
    try:
        with os.fdopen(prompt_fd, "w", encoding="utf-8") as f:
            f.write(PROMPT)

        args = build_test_args(reviewer, prompt_file, output_file)
        try:
            cmd = PROVIDERS[reviewer]["build_cmd"](args, None)
        except Exception as e:
            return {"test": test_name, "status": "ERROR", "reason": str(e), "duration": 0}

        env = build_env(reviewer)
        stdin_data = build_stdin(reviewer, prompt_file)

        print(f"\n{'=' * 60}")
        print(f"TEST: {test_name}")
        print(f"CMD:  {' '.join(cmd)}")
        print(f"{'=' * 60}")

        start = time.time()
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                env=env,
                **_popen_session_kwargs(),
            )
        except FileNotFoundError:
            return {"test": test_name, "status": "SKIP", "reason": "Binary not found", "duration": 0}

        try:
            stdout, stderr = proc.communicate(input=stdin_data, timeout=TIMEOUT)
            duration = time.time() - start
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            _kill_tree(proc)
            proc.communicate()
            return {
                "test": test_name,
                "status": "HUNG",
                "reason": f"Timed out after {TIMEOUT}s — likely stuck on permission prompt",
                "duration": duration,
            }
        except Exception as e:
            return {"test": test_name, "status": "ERROR", "reason": str(e), "duration": time.time() - start}

        response = extract_response_text(reviewer, output_file, stdout)
        response_lower = response.lower()

        refused = any(phrase in response_lower for phrase in REFUSAL_PHRASES)
        web_search_worked = (not refused) and (EXPECTED_ANSWER in response_lower)

        result = {
            "test": test_name,
            "status": "PASS" if returncode == 0 else "FAIL",
            "returncode": returncode,
            "duration": round(duration, 1),
            "web_search_worked": web_search_worked,
            "refusal_detected": refused,
            "response_preview": response[:300],
        }

        if stderr and returncode != 0:
            result["stderr_preview"] = stderr[:300]

        return result
    finally:
        _cleanup(prompt_file, output_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        choices=PROVIDER_NAMES,
        help="Test only this provider",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print each provider's built argv + stdin mode without executing",
    )
    args = parser.parse_args()

    reviewers = [args.provider] if args.provider else PROVIDER_NAMES

    if args.dry_run:
        dry_run(reviewers)
        return

    results = []
    for reviewer in reviewers:
        result = run_test(reviewer)
        results.append(result)

        # Print result immediately
        status = result["status"]
        duration = result.get("duration", 0)
        icon = {"PASS": "+", "FAIL": "X", "HUNG": "!", "SKIP": "-", "ERROR": "?"}
        print(f"\n[{icon.get(status, '?')}] {result['test']}: {status} ({duration}s)")
        if result.get("web_search_worked"):
            print("    Web search: YES")
        elif result.get("refusal_detected"):
            print("    Web search: NO (refused to fetch)")
        elif status == "PASS":
            print("    Web search: NO (ran but didn't return the expected fact)")
        if result.get("response_preview"):
            preview = result["response_preview"][:200].replace("\n", " ")
            print(f"    Response: {preview}")
        if result.get("reason"):
            print(f"    Reason: {result['reason']}")
        if result.get("stderr_preview"):
            preview = result["stderr_preview"][:200].replace("\n", " ")
            print(f"    Stderr: {preview}")

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for r in results:
        status = r["status"]
        web = " (web: YES)" if r.get("web_search_worked") else ""
        dur = f" [{r.get('duration', 0)}s]"
        print(f"  {status:6s} {r['test']}{web}{dur}")

    # Recommendations
    print(f"\n{'=' * 60}")
    print("RECOMMENDATIONS")
    print(f"{'=' * 60}")
    for r in results:
        if r["status"] == "HUNG":
            print(f"  AVOID {r['test']}: hangs on permission prompts")
        elif r["status"] == "PASS" and r.get("web_search_worked"):
            print(f"  USE   {r['test']}: web search works without hanging")
        elif r["status"] == "PASS" and r.get("refusal_detected"):
            print(f"  CHECK {r['test']}: ran but refused to fetch the URL")
        elif r["status"] == "PASS":
            print(f"  MAYBE {r['test']}: runs but web search didn't trigger")
        elif r["status"] == "FAIL":
            print(f"  CHECK {r['test']}: failed with exit code {r.get('returncode')}")


if __name__ == "__main__":
    main()
