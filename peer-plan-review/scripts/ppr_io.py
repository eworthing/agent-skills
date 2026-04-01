"""
ppr_io.py — File I/O helpers for peer-plan-review.

Extracted from run_review.py. Contains session load/save and output text
extraction.
"""

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path


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


def validate_prompt_file(prompt_file):
    """Validate prompt file: exists, readable, UTF-8, non-empty.

    Returns (ok: bool, error_message: str | None).
    """
    p = Path(prompt_file)
    if not p.exists():
        return False, f"not found: {prompt_file}"
    try:
        with p.open("r", encoding="utf-8") as f:
            content = f.read()
    except PermissionError:
        return False, f"exists but is not readable: {prompt_file}"
    except UnicodeDecodeError:
        return False, f"is not valid UTF-8: {prompt_file}"
    except OSError as e:
        return False, f"cannot read: {prompt_file}: {e}"
    if not content.strip():
        return False, f"is empty: {prompt_file}"
    return True, None


def probe_writable(fpath):
    """Test actual writability of fpath.

    Returns (ok: bool, error_message: str | None).
    Rejects non-regular existing paths (directories, FIFOs, sockets, devices).
    Path.is_file() follows symlinks, so symlink-to-regular-file passes.
    """
    p = Path(fpath)
    parent = p.parent
    if not parent.is_dir():
        return False, f"directory does not exist: {parent}"
    if p.exists():
        if not p.is_file():
            return False, f"exists but is not a regular file: {fpath}"
        try:
            with p.open("a"):
                pass
            return True, None
        except OSError as e:
            return False, f"exists but is not writable: {fpath}: {e}"
    else:
        try:
            fd, probe = tempfile.mkstemp(dir=str(parent), prefix=".ppr-probe-")
            os.close(fd)
            with contextlib.suppress(OSError):
                os.unlink(probe)
            return True, None
        except OSError as e:
            return False, f"directory is not writable: {parent}: {e}"
