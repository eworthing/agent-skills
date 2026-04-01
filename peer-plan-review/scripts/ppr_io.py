"""
ppr_io.py — File I/O helpers for peer-plan-review.

Extracted from run_review.py. Contains session load/save and output text
extraction.
"""

import json
import sys
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
