#!/usr/bin/env python3
"""Live-run artifact validator for the contest-refactor skill.

Default mode (PR2) is strict (exit non-zero on any failure). Advisory mode
emits WARN to stderr and exits 0. Both modes apply the same rule set; the flag
governs exit code only.

Checks (every value resolves against canon/*.toml):
- Required artifact existence based on schema_version
- Per-finding Evidence Chain field completeness
- Mechanical retirement rule (Branch A 3-way / Branch B 2-way hash equality)
- G30 disposition coverage at HALT_STAGNATION/oscillation
- G31 fingerprint integrity (recomputed hashes match stored)
- HALT_SUCCESS gating + expired-accepted-residual rejection
- G21-scorecard: every HALT_SUCCESS dimension must satisfy score==10 OR
  (score>=9.5 AND residual_disposition=="accepted")
- CONTINUE backlog presence

Usage:
    python3 scripts/validate-artifact.py <artifact-dir> [--mode {advisory,strict}]
                                                       [--json <out.json>]
                                                       [--quiet]
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _canon  # type: ignore[import-not-found]  # noqa: E402
from _artifact_core import (  # noqa: E402
    Issue,
    _load_json,
    check_continue_backlog,
    check_g16_registry_uniqueness,
    check_g39_backlog_score_impact,
    check_g40_discovery_persistence,
    check_g41_cap_loop_executed,
    check_g42_backlog_stable_id,
    check_per_finding_evidence_chain,
    check_required_artifacts,
    check_schema_enums,
)
from _artifact_credentials import check_g44_credential_quarantine  # noqa: E402
from _artifact_halt import (  # noqa: E402
    check_g21_scorecard,
    check_g33_risk_boundary_evidence,
    check_g34_halt_tail_invariants,
    check_g35_halt_handoff_shape,
    check_g36_required_state,
    check_g38_premium_model_budget_guard,
    check_halt_success_gating,
)
from _artifact_history import (  # noqa: E402
    _G22_COMMIT_SUBJECT_RE,
    _G22_COMMIT_SUBJECT_V1_RE,
    ELIGIBLE_BACKLOG_STATUSES,
    SERIOUS_OR_WORSE,
    check_g18_review_history_append,
    check_g19_provider_model,
    check_g22_archive_divider,
    check_g27_retry_envelope,
    check_g28_loop_state_freshness,
    check_g30_disposition_coverage,
    check_g31_fingerprint_integrity,
    check_retirement_rule,
)
from _artifact_panel import check_g32_halt_success_challenge  # noqa: E402
from _artifact_residual import (  # noqa: E402
    check_g5_sub95_residual_fields,
    check_g37_terminal_residual_accounting,
    check_g43_convergence_pass,
)

SKILL_ROOT = SCRIPT_DIR.parent

__all__ = (
    "ELIGIBLE_BACKLOG_STATUSES",
    "SERIOUS_OR_WORSE",
    "_G22_COMMIT_SUBJECT_RE",
    "_G22_COMMIT_SUBJECT_V1_RE",
)


def _load_project_config(artifact_dir: Path) -> dict | None:
    """Load `.contest-refactor.toml` from the artifact dir or its repo root."""
    candidates: list[Path] = [
        artifact_dir / ".contest-refactor.toml",
    ]
    cur = artifact_dir.resolve()
    for ancestor in [cur, *cur.parents]:
        candidates.append(ancestor / ".contest-refactor.toml")
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            try:
                with path.open("rb") as fh:
                    return tomllib.load(fh)
            except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
                # UnicodeDecodeError (a ValueError, not TOMLDecodeError/OSError)
                # covers a non-UTF-8 config, e.g. a UTF-16/cp1252 file on Windows.
                sys.stderr.write(f"error: {path}: malformed .contest-refactor.toml: {exc}\n")
                raise SystemExit(2) from exc
            except OSError as exc:
                sys.stderr.write(f"error: {path}: could not read .contest-refactor.toml: {exc}\n")
                raise SystemExit(2) from exc
    return None


def run_checks(artifact_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    canon = _canon.load_canon(SKILL_ROOT)
    current_review_path = artifact_dir / "CURRENT_REVIEW.json"
    if not current_review_path.exists():
        return [
            Issue(
                "required-artifact",
                f"CURRENT_REVIEW.json missing in {artifact_dir}",
            )
        ]
    current_review = _load_json(current_review_path) or {}
    required_issues, history, registry = check_required_artifacts(artifact_dir, current_review)
    issues.extend(required_issues)
    issues.extend(check_schema_enums(current_review, canon))
    issues.extend(check_per_finding_evidence_chain(current_review))
    issues.extend(check_retirement_rule(current_review, registry))
    issues.extend(check_g16_registry_uniqueness(registry))
    issues.extend(check_g30_disposition_coverage(current_review, registry))
    issues.extend(check_g31_fingerprint_integrity(registry))
    issues.extend(check_g18_review_history_append(current_review, history))
    issues.extend(check_g19_provider_model(current_review))
    project_config = _load_project_config(artifact_dir)
    issues.extend(check_g22_archive_divider(artifact_dir, current_review, project_config))
    issues.extend(check_g27_retry_envelope(current_review))
    issues.extend(check_g28_loop_state_freshness(artifact_dir, current_review, project_config))
    issues.extend(check_halt_success_gating(current_review, project_config))
    issues.extend(check_g21_scorecard(current_review))
    issues.extend(check_g5_sub95_residual_fields(current_review))
    issues.extend(check_g32_halt_success_challenge(current_review))
    issues.extend(check_g33_risk_boundary_evidence(current_review, canon))
    issues.extend(check_g34_halt_tail_invariants(current_review, canon))
    issues.extend(check_g35_halt_handoff_shape(current_review, canon))
    issues.extend(check_g36_required_state(current_review, canon))
    issues.extend(check_g37_terminal_residual_accounting(current_review))
    issues.extend(check_g38_premium_model_budget_guard(current_review, canon))
    issues.extend(check_g39_backlog_score_impact(current_review, canon))
    issues.extend(check_g40_discovery_persistence(current_review))
    issues.extend(check_g41_cap_loop_executed(current_review))
    issues.extend(check_g42_backlog_stable_id(current_review))
    issues.extend(check_g43_convergence_pass(current_review, history, canon))
    issues.extend(check_g44_credential_quarantine(artifact_dir))
    issues.extend(check_continue_backlog(current_review))
    return issues


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path, help="directory containing CURRENT_REVIEW.json")
    parser.add_argument(
        "--mode",
        choices=("advisory", "strict"),
        default="strict",
        help="strict (default, PR2+): exit non-zero on any failure; advisory: WARN, exit 0",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="emit findings as JSON to this path",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress passing-rule output (only print failures)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    artifact_dir: Path = args.artifact_dir
    if not artifact_dir.is_dir():
        sys.stderr.write(f"error: not a directory: {artifact_dir}\n")
        return 2
    issues = run_checks(artifact_dir)
    label_prefix = "WARN" if args.mode == "advisory" else "FAIL"
    if issues:
        for issue in issues:
            sys.stderr.write(issue.render(label_prefix) + "\n")
        sys.stderr.write(
            f"\nvalidate-artifact ({args.mode}): {len(issues)} issue(s) in {artifact_dir}\n"
        )
    else:
        if not args.quiet:
            sys.stdout.write(f"validate-artifact ({args.mode}): OK {artifact_dir}\n")
    if args.json is not None:
        payload = {
            "artifact_dir": str(artifact_dir),
            "mode": args.mode,
            "issue_count": len(issues),
            "issues": [issue.to_dict() for issue in issues],
        }
        try:
            args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"error: could not write --json output to {args.json}: {exc}\n")
            return 2
    if args.mode == "strict" and issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
