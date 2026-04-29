"""
ppr_metadata.py — Metadata and session ID extraction for peer-plan-review.

Extracted from run_review.py. Contains extract_metadata, session ID
extractors, and Codex session file helpers.
"""

import contextlib
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

_REVERSE_EFFORT_OPENCODE = {
    "low": "low", "medium": "medium",
    "high": "high", "max": "xhigh",
}


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


def extract_session_id_opencode(output_file):
    """Extract sessionID from first line of opencode JSONL output."""
    if not output_file or not Path(output_file).exists():
        return None
    try:
        with Path(output_file).open(encoding="utf-8") as f:
            first = json.loads(f.readline())
            return first.get("sessionID")
    except (json.JSONDecodeError, OSError):
        return None


def extract_metadata(output_file, events_file, reviewer, codex_session_file=None,
                     output_content=None, logger=None):
    """Extract model/effort metadata from structured output.

    For providers that read the output file (claude, gemini, copilot),
    output_content can be passed to avoid reading the file (eliminating
    temporal coupling with extract_text_from_output).

    Opencode metadata is NOT extracted here — callers must use
    _extract_opencode_metadata_via_export() separately for the
    subprocess-based export path.

    Returns dict with 'model' and optionally 'effort' if discoverable,
    or empty dict on failure.
    """
    meta = {}

    def _log_warn(reason):
        if logger:
            with contextlib.suppress(Exception):
                logger.log("metadata_warning", provider=reviewer, error=str(reason))

    # Claude / Gemini: single JSON object
    if reviewer in ("claude", "gemini"):
        raw = output_content
        if raw is None and output_file and Path(output_file).exists():
            try:
                raw = Path(output_file).read_text(encoding="utf-8")
            except OSError as e:
                _log_warn(e)
                return meta
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                _log_warn(e)
                return meta
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

    # Copilot: JSONL — model is in session.tools_updated or
    # tool.execution_complete events under data.model
    if reviewer == "copilot":
        raw = output_content
        if raw is None and output_file and Path(output_file).exists():
            try:
                raw = Path(output_file).read_text(encoding="utf-8")
            except OSError as e:
                _log_warn(e)
                return meta
        if raw:
            for line in raw.splitlines():
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
            except OSError as e:
                _log_warn(e)
            if meta.get("model"):
                break

    return meta


def _extract_opencode_metadata_via_export(session_id):
    """Extract opencode metadata via `opencode export <session_id>`.

    This is a side-effecting operation (shells out to the opencode CLI).
    Callers must decide whether to invoke it. All other metadata extraction
    is handled by extract_metadata().

    Returns dict with 'model' and optionally 'effort', or empty dict on
    any failure (openocode not installed, timeout, malformed export, etc.).
    """
    meta = {}
    try:
        export = subprocess.run(
            ["opencode", "export", session_id],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if export.returncode == 0:
            data = json.loads(export.stdout)
            for msg in data.get("messages", []):
                model = msg.get("info", {}).get("model", {})
                if model.get("providerID") and model.get("modelID"):
                    meta["model"] = f"{model['providerID']}/{model['modelID']}"
                    variant = model.get("variant")
                    if variant:
                        meta["effort"] = _REVERSE_EFFORT_OPENCODE.get(variant, variant)
                    break
    except (json.JSONDecodeError, OSError, subprocess.TimeoutExpired,
            subprocess.SubprocessError):
        pass
    return meta


def compute_plan_metadata(plan_file):
    """Compute plan file metadata for session tracking.

    Returns dict with plan_name, plan_bytes, plan_sha256, plan_mtime,
    or empty dict if plan_file is None or doesn't exist.
    """
    if not plan_file:
        return {}
    p = Path(plan_file)
    if not p.exists():
        return {}
    try:
        stat = p.stat()
        with p.open("rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        return {
            "plan_name": p.name,
            "plan_bytes": stat.st_size,
            "plan_sha256": sha,
            "plan_mtime": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        }
    except OSError:
        return {}
