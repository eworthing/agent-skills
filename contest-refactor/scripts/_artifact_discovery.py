"""Artifact checks for persisted Step-0 discovery evidence."""

from __future__ import annotations

from typing import Any

import _ruleset_epoch
from _artifact_core import Issue

_QUEUES = {"control", "mutation", "navigation"}
_SCAN_KEYS = {
    "schema_version",
    "status",
    "promotion_allowed",
    "coverage",
    "candidates",
    "queue_counts",
}
_CANDIDATE_KEYS = {
    "path",
    "symbol",
    "line_range",
    "candidate_queues",
    "primary_queue",
    "signals",
    "neighborhood",
}
_SIGNAL_KEYS = {
    "decision_count",
    "max_nesting",
    "condition_operand_max",
    "logical_lines",
    "mutation_sites",
    "mutation_span",
    "distinct_mutated_fields",
    "mutable_local_count",
    "private_helper_fanout",
    "single_use_private_helper_count",
    "private_call_depth",
    "direct_call_fanout",
}


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _coverage_error(coverage: Any) -> tuple[str | None, str | None]:
    if not isinstance(coverage, dict) or set(coverage) != {"python", "ast_grep"}:
        return "coverage must contain exactly python and ast_grep records", None

    python = coverage["python"]
    ast_grep = coverage["ast_grep"]
    if not isinstance(python, dict) or set(python) != {"discovered", "scanned", "failed"}:
        return "coverage.python has an invalid shape", None
    if not isinstance(ast_grep, dict) or set(ast_grep) != {
        "discovered",
        "scanned",
        "failed",
        "outcome",
    }:
        return "coverage.ast_grep has an invalid shape", None

    for name, record in (("python", python), ("ast_grep", ast_grep)):
        if not all(
            _nonnegative_int(record[field]) for field in ("discovered", "scanned", "failed")
        ):
            return f"coverage.{name} counts must be non-negative integers", None
        if record["scanned"] + record["failed"] != record["discovered"]:
            return f"coverage.{name} scanned + failed must equal discovered", None

    outcome = ast_grep["outcome"]
    if not isinstance(outcome, str) or outcome not in {
        "ok",
        "partial",
        "absent",
        "not_applicable",
    }:
        return "coverage.ast_grep.outcome is invalid", None
    if ast_grep["discovered"] == 0:
        expected_outcome = "not_applicable"
    elif outcome == "absent":
        expected_outcome = "absent"
        if ast_grep["scanned"] != 0 or ast_grep["failed"] != ast_grep["discovered"]:
            return "ast_grep outcome absent requires every discovered file to fail", None
    elif ast_grep["failed"]:
        expected_outcome = "partial"
    else:
        expected_outcome = "ok"
    if outcome != expected_outcome:
        return f"coverage.ast_grep.outcome must be {expected_outcome!r}", None

    total_discovered = python["discovered"] + ast_grep["discovered"]
    total_failed = python["failed"] + ast_grep["failed"]
    if total_discovered == 0:
        status = "not_applicable"
    elif python["discovered"] == 0 and outcome == "absent":
        status = "absent"
    elif total_failed:
        status = "partial"
    else:
        status = "ok"
    return None, status


def _candidate_error(candidate: Any) -> str | None:
    if not isinstance(candidate, dict) or set(candidate) != _CANDIDATE_KEYS:
        return "candidate contains missing or unrecognized fields"
    if not all(
        isinstance(candidate[field], str) and candidate[field].strip()
        for field in ("path", "symbol")
    ):
        return "candidate path and symbol must be non-empty strings"

    line_range = candidate["line_range"]
    if not isinstance(line_range, dict) or set(line_range) != {"start", "end"}:
        return "candidate line_range has an invalid shape"
    start, end = line_range["start"], line_range["end"]
    if not (_nonnegative_int(start) and start >= 1 and _nonnegative_int(end) and end >= start):
        return "candidate line_range must be positive and ordered"

    queues = candidate["candidate_queues"]
    if (
        not isinstance(queues, list)
        or not queues
        or not all(isinstance(queue, str) for queue in queues)
        or len(queues) != len(set(queues))
    ):
        return "candidate_queues must be a non-empty unique list"
    if not set(queues) <= _QUEUES or candidate["primary_queue"] not in queues:
        return "candidate queues or primary_queue are invalid"

    signals = candidate["signals"]
    if not isinstance(signals, dict) or set(signals) != _SIGNAL_KEYS:
        return "candidate signals contain missing or unrecognized fields"
    if not all(_nonnegative_int(value) for value in signals.values()):
        return "candidate signals must be non-negative integers"

    neighborhood = candidate["neighborhood"]
    if not isinstance(neighborhood, dict) or set(neighborhood) != {"direct_private_helpers"}:
        return "candidate neighborhood has an invalid shape"
    helpers = neighborhood["direct_private_helpers"]
    if not isinstance(helpers, list) or not all(
        isinstance(helper, str) and helper.strip() for helper in helpers
    ):
        return "direct_private_helpers must be a list of non-empty strings"
    return None


def validate_hotspot_scan(scan: Any) -> list[str]:
    """Return schema errors for one persisted audit_hotspots.py record."""
    if not isinstance(scan, dict):
        return ["hotspot_scan must be a JSON object"]
    errors: list[str] = []
    if set(scan) != _SCAN_KEYS:
        errors.append("record contains missing or unrecognized fields")
    if scan.get("schema_version") != 2:
        errors.append("schema_version must equal 2")
    if scan.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be false")

    status = scan.get("status")
    if not isinstance(status, str):
        errors.append("status must be a string")
    coverage_error, expected_status = _coverage_error(scan.get("coverage"))
    if coverage_error:
        errors.append(coverage_error)
    elif isinstance(status, str) and status != expected_status:
        errors.append(f"status must be {expected_status!r} for the recorded coverage")

    candidates = scan.get("candidates")
    if not isinstance(candidates, list):
        errors.append("candidates must be a list")
        candidates = []
    for index, candidate in enumerate(candidates):
        if error := _candidate_error(candidate):
            errors.append(f"candidates[{index}]: {error}")

    queue_counts = scan.get("queue_counts")
    if not isinstance(queue_counts, dict) or set(queue_counts) != _QUEUES:
        errors.append("queue_counts must contain exactly control, mutation, and navigation")
    elif not all(_nonnegative_int(value) for value in queue_counts.values()):
        errors.append("queue_counts values must be non-negative integers")
    else:
        memberships = {
            queue: sum(
                isinstance(candidate, dict)
                and isinstance(candidate.get("candidate_queues"), list)
                and queue in candidate["candidate_queues"]
                for candidate in candidates
            )
            for queue in _QUEUES
        }
        if any(bool(queue_counts[queue]) != bool(memberships[queue]) for queue in _QUEUES):
            errors.append("queue_counts presence must match retained candidate queue memberships")
        # Per-queue rosters are capped before their union is persisted, so only
        # this upper bound is reconstructible from the sanitized record.
        elif any(queue_counts[queue] > memberships[queue] for queue in _QUEUES):
            errors.append("queue_counts cannot exceed retained candidate queue memberships")

    if (
        isinstance(status, str)
        and status in {"absent", "not_applicable"}
        and (candidates or (isinstance(queue_counts, dict) and any(queue_counts.values())))
    ):
        errors.append("absent/not_applicable scans cannot retain candidates or queue counts")

    return errors


def check_g49_hotspot_scan(current_review: dict) -> list[Issue]:
    """G49: post-651ea50 artifacts carry real sanitized hotspot evidence."""
    if not _ruleset_epoch.applies("G49_HOTSPOT_SCAN", current_review):
        return []

    loop = current_review.get("loop")
    context = f"discovery.hotspot_scan (loop {loop})"
    discovery = current_review.get("discovery")
    scan = discovery.get("hotspot_scan") if isinstance(discovery, dict) else None
    if not isinstance(scan, dict):
        return [
            Issue(
                "G49",
                "hotspot_scan must come from a real Step-0 audit_hotspots.py --json run; "
                "rerun with --reset and never invent placeholder values",
                context,
            )
        ]

    return [Issue("G49", error, context) for error in validate_hotspot_scan(scan)]
