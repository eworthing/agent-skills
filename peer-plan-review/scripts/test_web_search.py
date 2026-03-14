#!/usr/bin/env python3
"""
test_web_search.py — Test web search capability per provider.

Tests whether each provider can perform web searches in headless mode
without hanging on permission prompts. Uses a short timeout to detect hangs.

Usage:
    python3 test_web_search.py                    # test all providers
    python3 test_web_search.py --provider claude   # test one provider
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
import time
from pathlib import Path

TIMEOUT = 180  # seconds — URL fetch can be slow (Gemini/Copilot take 50-70s)

PROMPT = (
    "Fetch this URL and tell me the FIRST heading (h1) on the page: "
    "https://docs.python.org/3/whatsnew/3.13.html "
    "Then tell me how many PEP links are in the first section. "
    "You MUST actually fetch/read the page content — do NOT guess from memory. "
    "Do NOT use any file tools."
)


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


def test_claude_web(output_file):
    """Claude: plan mode + WebSearch,WebFetch whitelisted + allowedTools."""
    cmd = [
        "claude", "-p", PROMPT,
        "--permission-mode", "plan",
        "--tools", "Read,Grep,Glob,WebSearch,WebFetch",
        "--allowedTools", "WebSearch,WebFetch",
        "--output-format", "json",
        "--max-turns", "5",
        "--no-session-persistence",
    ]
    env = os.environ.copy()
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    return cmd, env, None


def test_codex_web(output_file):
    """Codex: read-only sandbox + approval_mode=never (web works by default)."""
    cmd = [
        "codex", "exec",
        "--sandbox", "read-only",
        "-c", "approval_mode=never",
        "--json",
        "--output-last-message", output_file,
        "-",
    ]
    return cmd, os.environ.copy(), PROMPT


def test_gemini_web(output_file):
    """Gemini: yolo mode (required for URL fetch) + sandbox (prevents writes)."""
    cmd = [
        "gemini",
        "--sandbox",
        "--approval-mode", "yolo",
        "--output-format", "json",
        "-p", PROMPT,
    ]
    return cmd, os.environ.copy(), None


def test_copilot_web(output_file):
    """Copilot: --yolo + deny write/shell/memory (--allow-tool=url hangs)."""
    cmd = [
        "copilot", "-p", PROMPT, "-s",
        "--no-ask-user",
        "--yolo",
        "--deny-tool=write,shell,memory",
        "--no-custom-instructions",
        "--no-auto-update",
        "--output-format", "json",
    ]
    return cmd, os.environ.copy(), None


# Production configs — matches run_review.py --web flags per provider
TEST_CASES = [
    ("claude:web", test_claude_web),
    ("codex:web", test_codex_web),
    ("gemini:web", test_gemini_web),
    ("copilot:web", test_copilot_web),
]


def extract_response(output_file, test_name, stdout):
    """Extract the text response from structured output."""
    provider = test_name.split(":")[0]

    # For Codex, response is in the output file
    if provider == "codex":
        if Path(output_file).exists():
            with Path(output_file).open() as f:
                return f.read().strip()
        return stdout.strip() if stdout else "(no output)"

    if not stdout:
        return "(no output)"

    # Claude/Gemini: single JSON
    if provider in ("claude", "gemini"):
        try:
            data = json.loads(stdout)
            if provider == "claude":
                return data.get("result", stdout)[:500]
            elif provider == "gemini":
                return data.get("response", stdout)[:500]
        except json.JSONDecodeError:
            return stdout[:500]

    # Copilot: JSONL
    if provider == "copilot":
        messages = []
        for line in stdout.splitlines():
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
        return "\n".join(messages)[:500] if messages else stdout[:500]

    return stdout[:500]


def run_test(test_name, test_fn):
    """Run a single test case and return results."""
    tmpdir = tempfile.gettempdir()
    output_file = str(Path(tmpdir) / f"web-test-{test_name.replace(':', '-')}.txt")

    provider = test_name.split(":")[0]
    binary = provider if provider != "claude" else "claude"
    if not shutil.which(binary):
        return {
            "test": test_name,
            "status": "SKIP",
            "reason": f"{binary} not installed",
            "duration": 0,
        }

    try:
        cmd, env, stdin_data = test_fn(output_file)
    except Exception as e:
        return {
            "test": test_name,
            "status": "ERROR",
            "reason": str(e),
            "duration": 0,
        }

    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"CMD:  {' '.join(cmd)}")
    print(f"{'='*60}")

    start = time.time()
    try:
        if stdin_data:
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace",
                env=env, **_popen_session_kwargs(),
            )
        else:
            proc = subprocess.Popen(
                cmd, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace",
                env=env, **_popen_session_kwargs(),
            )

        try:
            stdout, stderr = proc.communicate(
                input=stdin_data, timeout=TIMEOUT
            )
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

        response = extract_response(output_file, test_name, stdout)

        # Check if response mentions page content (indicates actual URL fetch)
        web_search_worked = any(kw in response.lower() for kw in [
            "new in python", "what's new", "pep", "heading", "h1",
            "3.13", "whatsnew",
        ])

        result = {
            "test": test_name,
            "status": "PASS" if returncode == 0 else "FAIL",
            "returncode": returncode,
            "duration": round(duration, 1),
            "web_search_worked": web_search_worked,
            "response_preview": response[:300],
        }

        if stderr and returncode != 0:
            result["stderr_preview"] = stderr[:300]

        return result

    except FileNotFoundError:
        return {
            "test": test_name,
            "status": "SKIP",
            "reason": "Binary not found",
            "duration": 0,
        }
    except Exception as e:
        return {
            "test": test_name,
            "status": "ERROR",
            "reason": str(e),
            "duration": time.time() - start,
        }
    finally:
        output_path = Path(output_file)
        if output_path.exists():
            output_path.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["claude", "codex", "gemini", "copilot"],
                        help="Test only this provider")
    args = parser.parse_args()

    cases = TEST_CASES
    if args.provider:
        cases = [(name, fn) for name, fn in TEST_CASES
                 if name.startswith(args.provider)]

    results = []
    for name, fn in cases:
        result = run_test(name, fn)
        results.append(result)

        # Print result immediately
        status = result["status"]
        duration = result.get("duration", 0)
        icon = {"PASS": "+", "FAIL": "X", "HUNG": "!", "SKIP": "-", "ERROR": "?"}
        print(f"\n[{icon.get(status, '?')}] {name}: {status} ({duration}s)")
        if result.get("web_search_worked"):
            print("    Web search: YES")
        elif status == "PASS":
            print("    Web search: NO (ran but didn't search web)")
        if result.get("response_preview"):
            # Print first 200 chars of response
            preview = result["response_preview"][:200].replace("\n", " ")
            print(f"    Response: {preview}")
        if result.get("reason"):
            print(f"    Reason: {result['reason']}")
        if result.get("stderr_preview"):
            preview = result["stderr_preview"][:200].replace("\n", " ")
            print(f"    Stderr: {preview}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status = r["status"]
        web = " (web: YES)" if r.get("web_search_worked") else ""
        dur = f" [{r.get('duration', 0)}s]"
        print(f"  {status:6s} {r['test']}{web}{dur}")

    # Recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    for r in results:
        if r["status"] == "HUNG":
            print(f"  AVOID {r['test']}: hangs on permission prompts")
        elif r["status"] == "PASS" and r.get("web_search_worked"):
            print(f"  USE   {r['test']}: web search works without hanging")
        elif r["status"] == "PASS":
            print(f"  MAYBE {r['test']}: runs but web search didn't trigger")
        elif r["status"] == "FAIL":
            print(f"  CHECK {r['test']}: failed with exit code {r.get('returncode')}")


if __name__ == "__main__":
    main()
