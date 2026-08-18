#!/usr/bin/env python3
"""Validator for the paired with_skill/without_skill replication record (the principal + core
Layer-2 recall-lift measurement plan, `evals/paired_arm_replication.json`). The record-shape
checks live in `_paired_arm_validate.py`; this file is the CLI entry point.

Exit codes:
  0 - valid for its declared `record_state`
  1 - measured validation failure (the record's content violates a rule)
  2 - plumbing / cannot-measure (bad path, unparseable JSON, bad CLI args)

The record moves through four states over the life of the study (see the plan's "Record
lifecycle" section), and a DIFFERENT set of requirements is enforced at each one -- a
`preregistered` record legitimately has empty `attempts`/`per_scenario`; a `complete` one must
have exactly 5 terminal slots per (scenario, arm). Getting the wrong requirements for the wrong
state is exactly the failure mode a single hard-coded "attempts must have N entries" check would
produce on Phase 1's own artifact.

    record_state     | what is validated
    -----------------+-----------------------------------------------------------------------
    preregistered    | full prereg present + internally consistent (rules, decision tables,
                      | frozen order of 55 pair IDs, seeds, material hashes, terminal-selection
                      | predicate); attempts == [] and per_scenario == {}
    in_progress      | prereg byte-identical to its own frozen hash (`prereg_sha256`); every
                      | attempt individually well-formed per the nullability table; grade
                      | fields may be null; no completeness/summary check
    graded           | every attempt carries `grade_status`; every `grade_status: "graded"`
                      | attempt carries full grade fields
    complete         | everything above, plus exactly 5 terminal slots per (scenario_id, arm),
                      | per_scenario summaries present for all 11 study scenarios, and the
                      | arm-conditional subset invariant holds on with_skill

Always enforced regardless of state: `VALID_ARMS`, resolution + hash-match of every referenced
material/historical file, the closed `candidate_output_status` / `trial_validity` vocabularies,
and the per-attempt nullability table (item 21's exogenous-vs-adherence split, kept out of
`canon/trial-validity.toml`'s `invalid_reasons` enum for anything adherence-shaped).

Regression detection (append-only history, no attempt silently un-graded) runs ONLY when given
`--previous <path-or-git-rev>` -- without a baseline this validator makes no temporal claim.

`--check-git-provenance` is a documented stub in Phase 1: no attempts exist yet for it to check,
so it prints that explicitly and returns without affecting the exit code, rather than silently
doing nothing. It becomes a real check once Phase 3 dispatch produces committed attempts.

Usage:
    python3 scripts/validate-paired-arm.py <record.json>
    python3 scripts/validate-paired-arm.py <record.json> --previous <path-or-git-rev>
    python3 scripts/validate-paired-arm.py <record.json> --check-git-provenance
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _canon  # type: ignore[import-not-found]  # noqa: E402
from _paired_arm_validate import (  # type: ignore[import-not-found]  # noqa: E402
    SKILL_ROOT,
    VALID_RECORD_STATES,
    PlumbingError,
    load_record,
    validate_complete,
    validate_graded,
    validate_in_progress,
    validate_preregistered,
)


def load_previous(ref: str) -> dict:
    candidate = Path(ref)
    if candidate.is_file():
        return load_record(candidate)
    try:
        proc = subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "show", f"{ref}:evals/paired_arm_replication.json"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        raise PlumbingError(
            f"--previous {ref!r} is not a file and not a resolvable git ref: {exc}"
        ) from exc
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PlumbingError(
            f"--previous {ref!r}: git show did not return valid JSON: {exc}"
        ) from exc


def check_regression(previous: dict, current: dict) -> list[str]:
    """Two append-only guarantees, checked only when a baseline is supplied: (1) every attempt
    present before is still present, byte-identical on its immutable fields (no silent rewrite
    of committed history); (2) nothing already `grade_status: "graded"` reverts to
    `not_applicable` (no silent un-grading)."""
    issues: list[str] = []
    prev_attempts = {
        (a.get("scenario_id"), a.get("arm"), a.get("slot_index"), a.get("attempt_index")): a
        for a in previous.get("attempts", [])
        if isinstance(a, dict)
    }
    curr_attempts = {
        (a.get("scenario_id"), a.get("arm"), a.get("slot_index"), a.get("attempt_index")): a
        for a in current.get("attempts", [])
        if isinstance(a, dict)
    }
    for key, prev_a in prev_attempts.items():
        curr_a = curr_attempts.get(key)
        if curr_a is None:
            issues.append(
                f"[regression] attempt {key} present in --previous is missing from current record"
            )
            continue
        for field in (
            "trial_validity",
            "candidate_output_status",
            "verdict_json",
            "raw_output_path",
        ):
            if prev_a.get(field) != curr_a.get(field):
                issues.append(
                    f"[regression] attempt {key}: {field} changed since --previous (committed history must be immutable)"
                )
        if prev_a.get("grade_status") == "graded" and curr_a.get("grade_status") != "graded":
            issues.append(
                f"[regression] attempt {key}: grade_status regressed from 'graded' to {curr_a.get('grade_status')!r}"
            )
    return issues


def check_git_provenance_stub() -> None:
    sys.stdout.write(
        "validate-paired-arm --check-git-provenance: documented stub in Phase 1 -- "
        "no attempts exist yet for this to check (record_state=='preregistered' has an empty "
        "attempts[] by design). This becomes a real check (every attempt/output resolves in "
        "HEAD; terminal selection matches committed history; execution.json only appends) once "
        "Phase 3 dispatch begins. Exiting 0 without evaluating anything.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "record_path",
        type=Path,
        help="path to paired_arm_replication.json (or a fixture of the same shape)",
    )
    parser.add_argument(
        "--previous",
        metavar="PATH_OR_GIT_REV",
        default=None,
        help="a prior copy of the record (file path or git revision) to check append-only regression against; omit for no temporal claim",
    )
    parser.add_argument(
        "--check-git-provenance",
        action="store_true",
        help="documented Phase-1 stub (see module docstring): prints a notice and returns 0 without checking anything, since no attempts exist yet",
    )
    args = parser.parse_args(argv)

    if args.check_git_provenance:
        check_git_provenance_stub()
        return 0

    try:
        record = load_record(args.record_path)
        canon = _canon.load_canon(SKILL_ROOT)
    except PlumbingError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    except Exception as exc:
        sys.stderr.write(f"error: unexpected plumbing failure: {exc}\n")
        return 2

    record_state = record.get("record_state")
    if record_state not in VALID_RECORD_STATES:
        sys.stderr.write(
            f"FAIL: record_state {record_state!r} missing or not one of {VALID_RECORD_STATES}\n"
        )
        return 1

    validators = {
        "preregistered": lambda: validate_preregistered(record),
        "in_progress": lambda: validate_in_progress(record, canon),
        "graded": lambda: validate_graded(record, canon),
        "complete": lambda: validate_complete(record, canon),
    }
    issues = validators[record_state]()

    if args.previous is not None:
        try:
            previous = load_previous(args.previous)
        except PlumbingError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
        issues += check_regression(previous, record)

    if issues:
        for issue in issues:
            sys.stderr.write(issue + "\n")
        sys.stderr.write(
            f"\nvalidate-paired-arm: {len(issues)} issue(s), record_state={record_state}\n"
        )
        return 1

    sys.stdout.write(f"validate-paired-arm: OK, record_state={record_state}, {args.record_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
