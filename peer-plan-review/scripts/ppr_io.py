"""
ppr_io.py — File I/O helpers for peer-plan-review.

Extracted from run_review.py. Contains session load/save and output text
extraction.
"""

import contextlib
import json
import os
import re
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


# ---------------------------------------------------------------------------
# Structured review parsing (adapted from quorum-review run_quorum.py)
# ---------------------------------------------------------------------------


def _extract_section(text, heading):
    """Extract content under a ### heading, stopping at the next ### or end."""
    pattern = re.compile(
        rf"^###\s+{re.escape(heading)}\s*$(.+?)(?=^###\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


_RE_FINDING_TAG = re.compile(
    r"^\s*-\s*\*{0,2}\[([BN])(\d+)\]\*{0,2}"
    r"(?:\s*\((HIGH|MEDIUM|LOW)\))?"
    r"\s*(.+)",
    re.MULTILINE | re.IGNORECASE,
)
_RE_SECTION_REF = re.compile(
    r"^\s+Section:\s*(.+?)(?:\s*\(lines?\s*([\d\-,\s]+)\))?\s*$",
)
_RE_RECOMMENDATION = re.compile(
    r"^\s+Recommendation:\s*(.+)$",
)


def _parse_finding_block(section_text, tag_match):
    """Parse a single finding, consuming indented continuation lines."""
    kind = tag_match.group(1).upper()
    num = tag_match.group(2)
    conf = tag_match.group(3)
    desc = tag_match.group(4).strip()

    finding = {
        "id": f"{kind}{num}",
        "severity": "blocking" if kind == "B" else "non_blocking",
        "confidence": conf.upper() if conf else None,
        "description": desc,
    }

    rest = section_text[tag_match.end():]
    if rest.startswith("\n"):
        rest = rest[1:]
    lines_after = rest.split("\n")
    for line in lines_after:
        stripped = line.strip()
        if not stripped or stripped.startswith("- "):
            break
        sec_m = _RE_SECTION_REF.match(line)
        if sec_m:
            finding["section"] = sec_m.group(1).strip()
            if sec_m.group(2):
                finding["lines"] = sec_m.group(2).strip()
            continue
        rec_m = _RE_RECOMMENDATION.match(line)
        if rec_m:
            finding["recommendation"] = rec_m.group(1).strip()
            continue

    return finding


def parse_structured_review(review_text):
    """Parse structured findings from review text.

    Scopes to ### Blocking Issues and ### Non-Blocking Issues sections
    to avoid false positives from ### Reasoning content.

    Returns list of finding dicts, or empty list if no structured
    findings found. Each dict has: id, severity, confidence,
    description, and optionally section, lines, recommendation.
    """
    findings = []
    for heading in ("Blocking Issues", "Non-Blocking Issues"):
        section_text = _extract_section(review_text, heading)
        if not section_text:
            continue
        for m in _RE_FINDING_TAG.finditer(section_text):
            finding = _parse_finding_block(section_text, m)
            findings.append(finding)
    return findings


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
