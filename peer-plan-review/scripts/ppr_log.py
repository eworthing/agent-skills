"""
ppr_log.py — Append-only JSONL event logger for peer-plan-review.

Best-effort, append-only logging. A logging failure never crashes the review.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class EventLogger:
    """Append-only JSONL event logger.

    When log_path is None, all methods are no-ops.
    """

    def __init__(self, log_path=None, review_id=None):
        self._log_path = Path(log_path) if log_path else None
        self._review_id = review_id or "unknown"

    def log(self, event_type, *, provider=None, round_num=None, error=None, context=None):
        """Write one JSONL line. Opens file in append mode each call."""
        if self._log_path is None:
            return
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "review_id": self._review_id,
            "event": event_type,
        }
        if provider is not None:
            entry["provider"] = provider
        if round_num is not None:
            entry["round"] = round_num
        if error is not None:
            entry["error"] = str(error)
        if context is not None:
            entry["ctx"] = context
        try:
            # newline="" prevents \n → \r\n translation on Windows
            with self._log_path.open("a", encoding="utf-8", newline="") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError:
            pass  # best-effort — never crash the review
