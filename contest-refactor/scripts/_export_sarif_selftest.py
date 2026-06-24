#!/usr/bin/env python3
"""Self-test: export_sarif.py turns the findings that SURVIVE a contest-refactor run
into a valid SARIF 2.1.0 log — and fabricates nothing.

What "survives" means here: a registry entry whose *latest* occurrence is
`unresolvable` (retired per Step 1.6), plus — when a CURRENT_REVIEW.json is passed —
any scorecard dimension carrying an `accepted` residual. Same-run-fixed findings
(terminal status `resolved` / `fixed_by_user`) are NOT durable and must not appear.

No pytest in this repo (pyproject configures only ruff), so this standalone check
builds throwaway fixtures in a tempdir, runs the export CLI as a subprocess, and
asserts on the parsed SARIF JSON.

Cases:
  - unresolvable-terminal registry  -> exactly one result, ruleId == stable_id,
    level mapped from the severity anchor, physical location from primary_file +
    primary_evidence_lines.
  - fully-resolved registry         -> a VALID but EMPTY-results SARIF (no fabrication).
  - accepted residual via --review  -> a note-level result for the carved-out dim.
  - missing registry file           -> non-zero exit with a clear message.

Run: python3 scripts/_export_sarif_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

EXPORT = Path(__file__).with_name("export_sarif.py")


def _unresolvable_registry() -> dict:
    """A registry whose single entry is terminally `unresolvable` (loop 5)."""
    return {
        "registry_schema_version": 2,
        "next_serial": 401,
        "entries": [
            {
                "stable_id": "F-400",
                "title": "Test suite reads UTC timestamps in local zone",
                "primary_file": "Tests/Common/DateAssertions.swift",
                "primary_evidence_lines": [21, 21],
                "test_failed": "n/a",
                "severity": "Noticeable weakness",
                "first_seen_loop": 3,
                "first_seen_sha": "aaaa111",
                "last_seen_loop": 5,
                "occurrences": [
                    {"loop": 3, "loop_local_id": "F1", "status": "rejected_attempt",
                     "sha": "aaaa111"},
                    {"loop": 5, "loop_local_id": "F2", "status": "unresolvable",
                     "sha": "bbbb222",
                     "retirement": {"reason": "unresolvable", "rationale": "exhausted attempts"}},
                ],
            }
        ],
    }


def _resolved_registry() -> dict:
    """Same shape, but the entry's terminal occurrence is `resolved` -> not durable."""
    reg = _unresolvable_registry()
    reg["entries"][0]["stable_id"] = "F-500"
    reg["entries"][0]["occurrences"][-1]["status"] = "resolved"
    return reg


def _review_with_accepted_residual() -> dict:
    return {
        "state": "HALT_SUCCESS",
        "scorecard": {
            "concurrency": {
                "score": 9.5,
                "residual_disposition": "accepted",
                "residual_blocking_10": "deinit cannot await teardown",
                "residual_rationale_or_backlog_ref": "Swift constraint; AudioConfig.swift:88; covered by test.",
            },
            "framework_idioms": {"score": 10, "residual_disposition": None},
        },
    }


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(EXPORT), *args],
        capture_output=True, text=True,
    )


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _assert_valid_sarif(sarif: dict, failures: list[str], label: str) -> bool:
    ok = True
    if sarif.get("version") != "2.1.0":
        failures.append(f"{label}: version != 2.1.0 (got {sarif.get('version')!r})")
        ok = False
    runs = sarif.get("runs")
    if not isinstance(runs, list) or len(runs) != 1:
        failures.append(f"{label}: expected exactly one run")
        return False
    driver = runs[0].get("tool", {}).get("driver", {})
    if driver.get("name") != "contest-refactor":
        failures.append(f"{label}: tool.driver.name != contest-refactor")
        ok = False
    if not isinstance(runs[0].get("results"), list):
        failures.append(f"{label}: runs[0].results is not a list")
        ok = False
    return ok


def main() -> int:
    if not EXPORT.is_file():
        print(f"FAIL: export script missing: {EXPORT}")
        return 1

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # --- Case 1: unresolvable-terminal registry -> one result ---
        reg1 = base / "reg_unresolvable.json"
        _write_json(reg1, _unresolvable_registry())
        p = _run([str(reg1)])
        if p.returncode != 0:
            failures.append(f"unresolvable: non-zero exit\n{p.stderr.rstrip()}")
        else:
            sarif = json.loads(p.stdout)
            if _assert_valid_sarif(sarif, failures, "unresolvable"):
                results = sarif["runs"][0]["results"]
                if len(results) != 1:
                    failures.append(f"unresolvable: expected 1 result, got {len(results)}")
                else:
                    r = results[0]
                    if r.get("ruleId") != "F-400":
                        failures.append(f"unresolvable: ruleId != F-400 (got {r.get('ruleId')!r})")
                    if r.get("level") != "warning":
                        failures.append(
                            f"unresolvable: 'Noticeable weakness' must map to 'warning' "
                            f"(got {r.get('level')!r})"
                        )
                    loc = (r.get("locations") or [{}])[0].get("physicalLocation", {})
                    uri = loc.get("artifactLocation", {}).get("uri")
                    region = loc.get("region", {})
                    if uri != "Tests/Common/DateAssertions.swift":
                        failures.append(f"unresolvable: location uri wrong (got {uri!r})")
                    if region.get("startLine") != 21:
                        failures.append(f"unresolvable: region.startLine != 21 (got {region.get('startLine')!r})")

        # --- Case 2: fully-resolved registry -> empty results, still valid ---
        reg2 = base / "reg_resolved.json"
        _write_json(reg2, _resolved_registry())
        p = _run([str(reg2)])
        if p.returncode != 0:
            failures.append(f"resolved: non-zero exit\n{p.stderr.rstrip()}")
        else:
            sarif = json.loads(p.stdout)
            if _assert_valid_sarif(sarif, failures, "resolved"):
                results = sarif["runs"][0]["results"]
                if results:
                    failures.append(
                        f"resolved: expected 0 results (no fabrication), got {len(results)}"
                    )

        # --- Case 3: accepted residual via --review -> a note result ---
        review = base / "CURRENT_REVIEW.json"
        _write_json(review, _review_with_accepted_residual())
        p = _run([str(reg2), "--review", str(review)])
        if p.returncode != 0:
            failures.append(f"residual: non-zero exit\n{p.stderr.rstrip()}")
        else:
            sarif = json.loads(p.stdout)
            if _assert_valid_sarif(sarif, failures, "residual"):
                results = sarif["runs"][0]["results"]
                resid = [r for r in results if str(r.get("ruleId", "")).startswith("residual/")]
                if len(resid) != 1:
                    failures.append(
                        f"residual: expected 1 residual result, got {len(resid)} "
                        f"(ruleIds={[r.get('ruleId') for r in results]})"
                    )
                elif resid[0].get("level") != "note":
                    failures.append(f"residual: accepted residual must be 'note' (got {resid[0].get('level')!r})")

        # --- Case 4: missing registry file -> non-zero exit, clear message ---
        p = _run([str(base / "does_not_exist.json")])
        if p.returncode == 0:
            failures.append("missing-file: expected non-zero exit, got 0")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: export_sarif — unresolvable findings export as SARIF 2.1.0 results, "
        "resolved registries yield empty results (no fabrication), accepted residuals "
        "map to note-level, missing input fails cleanly"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
