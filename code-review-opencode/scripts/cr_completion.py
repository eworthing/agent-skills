#!/usr/bin/env python3
"""Validate terminal code-review artifacts for batch drivers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def report_matches(report: Any, session_id: str, target: str | None = None) -> bool:
    if not isinstance(report, dict):
        return False
    if report.get("parent_session_id") != session_id:
        return False
    return target is None or report.get("requested_target") == target


def completion_error(report: Any, session_id: str, target: str | None = None) -> str | None:
    if not report_matches(report, session_id, target):
        return "artifact is not associated with the requested session and target"
    if not isinstance(report.get("run_id"), str) or not report["run_id"]:
        return "artifact has no run identity"
    if report.get("report_id") != report["run_id"]:
        return "artifact run and report identities do not match"
    if not isinstance(report.get("scope_id"), str) or not report["scope_id"]:
        return "artifact has no scope identity"
    model = report.get("model")
    if (
        not isinstance(model, dict)
        or not isinstance(model.get("provider_id"), str)
        or not model["provider_id"]
        or not isinstance(model.get("id"), str)
        or not model["id"]
    ):
        return "artifact model identity is malformed"
    if report.get("terminal_outcome") != "complete":
        return f"terminal outcome is {report.get('terminal_outcome')!r}, not complete"
    if report.get("terminal_status") != "complete":
        return f"terminal status is {report.get('terminal_status')!r}, not complete"
    if report.get("partial") is not False:
        return "artifact is partial or has no partial status"
    if report.get("truncated") is not False or report.get("truncated_from") is not None:
        return "artifact is truncated"
    if not isinstance(report.get("findings"), list):
        return "findings is not an array"
    stats = report.get("stats")
    stat_fields = (
        "finders",
        "candidates",
        "verifierAgents",
        "verified",
        "refuted",
        "dupes",
        "budgetDropped",
        "reported",
    )
    if not isinstance(stats, dict) or any(
        isinstance(stats.get(field), bool)
        or not isinstance(stats.get(field), int)
        or stats[field] < 0
        for field in stat_fields
    ):
        return "artifact statistics are malformed"
    if stats["reported"] != len(report["findings"]):
        return "reported finding count does not match the findings array"
    if not isinstance(report.get("generated_at"), str) or not report["generated_at"]:
        return "artifact has no generation timestamp"
    if not isinstance(report.get("files_changed"), list) or any(
        not isinstance(item, str) for item in report["files_changed"]
    ):
        return "artifact changed-file list is malformed"
    for index, finding in enumerate(report["findings"]):
        if not isinstance(finding, dict):
            return f"finding {index} is not an object"
        if not isinstance(finding.get("file"), str) or not finding["file"]:
            return f"finding {index} has no file"
        line = finding.get("line")
        if line is not None and (isinstance(line, bool) or not isinstance(line, int) or line < 1):
            return f"finding {index} has no valid line"
        if not isinstance(finding.get("summary"), str) or not finding["summary"]:
            return f"finding {index} has no summary"
        if not isinstance(finding.get("failure_scenario"), str) or not finding["failure_scenario"]:
            return f"finding {index} has no failure scenario"
        kind = finding.get("kind")
        if kind is not None and kind not in {"correctness", "cleanup"}:
            return f"finding {index} has an invalid kind"
        verdict = finding.get("verdict")
        if verdict is not None and verdict not in {"CONFIRMED", "PLAUSIBLE"}:
            return f"finding {index} has an invalid verdict"
    diagnostics = report.get("diagnostics")
    if not isinstance(diagnostics, list) or any(not isinstance(item, str) for item in diagnostics):
        return "artifact diagnostics are malformed"
    return None


def previous_run_is_active(
    session_outcome: Any,
    owner_state: Any,
    terminal_status: Any = None,
    terminal_outcome: Any = None,
) -> bool:
    """Keep ownership while a prompt fallback may still be running on the parent."""
    if session_outcome is not None:
        return False
    if (
        owner_state == "command_error"
        and terminal_status == "complete"
        and terminal_outcome == "complete"
    ):
        return False
    if owner_state != "command_returned":
        return True
    return terminal_outcome == "finder_fallback" and terminal_status != "complete"


def inbox_completion_error(
    report: Any,
    session_id: str,
    target: str,
    command_state: str,
    findings: Any,
) -> str | None:
    error = completion_error(report, session_id, target)
    if error:
        return error
    if command_state not in {"command_returned", "command_error"}:
        return "command request has not settled"
    if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
        return "inbox payload is not a findings array"
    artifact_findings = [
        {
            key: finding[key]
            for key in ("file", "line", "summary", "failure_scenario")
            if key in finding
        }
        for finding in report["findings"]
    ]
    if findings != artifact_findings:
        return "inbox findings do not match the terminal artifact"
    return None


def matching_reports(
    directory: Path, session_id: str, target: str | None = None
) -> list[tuple[Path, Any]]:
    matches: list[tuple[Path, Any]] = []
    for path in directory.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as handle:
                report = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if report_matches(report, session_id, target):
            matches.append((path, report))
    matches.sort(key=lambda item: (str(item[1].get("generated_at", "")), item[1].get("run_id", "")))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--target")
    parser.add_argument(
        "--path-only", action="store_true", help="print the selected associated artifact path"
    )
    args = parser.parse_args()

    matches = matching_reports(args.directory, args.session_id, args.target)
    if not matches:
        print("no report artifact is associated with this session and target", file=sys.stderr)
        return 3
    path, report = matches[-1]
    error = completion_error(report, args.session_id, args.target)
    if args.path_only:
        print(path)
    if error:
        print(error, file=sys.stderr)
        return 2
    if not args.path_only:
        print(
            json.dumps(
                {"path": str(path), "run_id": report["run_id"], "findings": len(report["findings"])}
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
