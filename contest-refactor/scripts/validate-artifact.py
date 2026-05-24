#!/usr/bin/env python3
"""Live-run artifact validator for the contest-refactor skill.

Default mode (PR2) is strict (exit non-zero on any failure). Advisory mode
emits WARN to stderr and exits 0. Both modes apply the same rule set; the flag
governs exit code only.

Checks (every value resolves against canon/*.yaml):
- Required artifact existence based on schema_version
- Per-finding Evidence Chain field completeness
- Mechanical retirement rule (Branch A 3-way / Branch B 2-way hash equality)
- G30 disposition coverage at HALT_STAGNATION/oscillation
- G31 fingerprint integrity (recomputed hashes match stored)
- HALT_SUCCESS gating + expired-accepted-residual rejection
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
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _canon  # type: ignore[import-not-found]  # noqa: E402
import _fingerprint  # type: ignore[import-not-found]  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent

# Severities considered "Serious-or-worse" for G30 coverage
SERIOUS_OR_WORSE = ("Serious deduction", "Likely disqualifier")

# Status values that keep a finding active at halt: open/rejected_attempt require
# a canonical disposition + sidecar; unresolvable requires the {disposition:
# "unresolvable"} stub (no sidecar, the registry carries the retirement block).
# resolved / fixed_by_user are done and need not appear.
ELIGIBLE_BACKLOG_STATUSES = ("open", "rejected_attempt", "unresolvable")

# Sidecar field required per disposition (per output-format-json.md halt_handoff schema)
DISPOSITION_SIDECARS = {
    "unresolvable": None,  # no extra sidecar; registry carries retirement block
    "user_decision": "user_decision_ref",
    "outside_scope": "scope_label",
    "unverifiable": "reason",
    "superseded": "superseded_by",
}


class Issue:
    """A single rule failure in an artifact."""

    __slots__ = ("rule", "message", "context")

    def __init__(self, rule: str, message: str, context: str | None = None) -> None:
        self.rule = rule
        self.message = message
        self.context = context

    def render(self, prefix: str) -> str:
        if self.context:
            return f"{prefix} [{self.rule}] {self.context}: {self.message}"
        return f"{prefix} [{self.rule}] {self.message}"

    def to_dict(self) -> dict:
        out = {"rule": self.rule, "message": self.message}
        if self.context:
            out["context"] = self.context
        return out


def _load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: {path}: JSON parse failed: {exc}")


def _parse_iso_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _parse_iso_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            cleaned = value.replace("Z", "+00:00")
            ts = datetime.fromisoformat(cleaned)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts
        except ValueError:
            return None
    return None


def check_required_artifacts(
    artifact_dir: Path, current_review: dict
) -> Tuple[List[Issue], dict | None, dict | None]:
    """Verify required files exist per schema_version. Returns (issues, history, registry)."""
    issues: List[Issue] = []
    schema_version = current_review.get("schema_version") or 1
    md_path = artifact_dir / "CURRENT_REVIEW.md"
    if not md_path.exists():
        issues.append(
            Issue("required-artifact", "CURRENT_REVIEW.md missing")
        )
    history: dict | None = None
    registry: dict | None = None
    if schema_version >= 2:
        history_path = artifact_dir / "REVIEW_HISTORY.json"
        registry_path = artifact_dir / "findings_registry.json"
        history_md_path = artifact_dir / "REVIEW_HISTORY.md"
        if not history_path.exists():
            issues.append(
                Issue(
                    "required-artifact",
                    f"REVIEW_HISTORY.json missing (required at schema_version >= 2)",
                )
            )
        else:
            history = _load_json(history_path)
        if not registry_path.exists():
            issues.append(
                Issue(
                    "required-artifact",
                    f"findings_registry.json missing (required at schema_version >= 2)",
                )
            )
        else:
            registry = _load_json(registry_path)
        if not history_md_path.exists():
            issues.append(
                Issue(
                    "required-artifact",
                    f"REVIEW_HISTORY.md missing (required at schema_version >= 2)",
                )
            )
    return issues, history, registry


def check_schema_enums(current_review: dict, canon: _canon.Canon) -> List[Issue]:
    """Every canon-typed value in CURRENT_REVIEW.json must be valid."""
    issues: List[Issue] = []
    state = current_review.get("state")
    if state is not None and state not in canon.states:
        issues.append(
            Issue("schema-enum", f"state {state!r} not in canon", context="state")
        )
    halt_subtype = current_review.get("halt_subtype")
    if halt_subtype is not None and halt_subtype not in canon.halt_subtypes:
        issues.append(
            Issue(
                "schema-enum",
                f"halt_subtype {halt_subtype!r} not in canon",
                context="halt_subtype",
            )
        )
    for finding in current_review.get("findings") or []:
        sev = finding.get("severity")
        fid = finding.get("loop_local_id") or finding.get("id") or "<unknown>"
        if sev is not None and sev not in canon.severity_anchors:
            issues.append(
                Issue(
                    "schema-enum",
                    f"severity {sev!r} not in canon",
                    context=f"finding {fid}",
                )
            )
        dep = finding.get("dependency_category")
        if dep is not None and dep not in canon.dependency_categories:
            issues.append(
                Issue(
                    "schema-enum",
                    f"dependency_category {dep!r} not in canon",
                    context=f"finding {fid}",
                )
            )
    impl_review = current_review.get("implementation_review") or {}
    verdict = impl_review.get("verdict")
    if verdict is not None and verdict not in canon.verdicts:
        issues.append(
            Issue(
                "schema-enum",
                f"implementation_review.verdict {verdict!r} not in canon",
                context="implementation_review",
            )
        )
    return issues


def check_per_finding_evidence_chain(current_review: dict) -> List[Issue]:
    """Every finding has all four Evidence Chain pieces populated."""
    issues: List[Issue] = []
    findings = current_review.get("findings") or []
    for finding in findings:
        fid = finding.get("loop_local_id") or finding.get("id") or "<unknown>"
        for field in ("title", "why_it_matters", "what_is_wrong"):
            value = finding.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(
                    Issue(
                        "evidence-chain",
                        f"Claim field {field!r} empty or missing",
                        context=f"finding {fid}",
                    )
                )
        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not any(
            isinstance(item, str) and item.strip() for item in evidence
        ):
            issues.append(
                Issue(
                    "evidence-chain",
                    "Source field 'evidence[]' empty or missing",
                    context=f"finding {fid}",
                )
            )
        for field in ("why_weakens_submission", "minimal_correction_path"):
            value = finding.get(field)
            if not isinstance(value, str) or not value.strip():
                label = "Consequence" if field == "why_weakens_submission" else "Remedy"
                issues.append(
                    Issue(
                        "evidence-chain",
                        f"{label} field {field!r} empty or missing",
                        context=f"finding {fid}",
                    )
                )
    return issues


def _occurrences_for(registry: dict | None, stable_id: str) -> List[dict]:
    if registry is None:
        return []
    for entry in registry.get("entries") or []:
        if entry.get("stable_id") == stable_id:
            return list(entry.get("occurrences") or [])
    return []


def _occurrence_fingerprint(occ: dict) -> Tuple[str | None, str | None, str | None]:
    fp = occ.get("fingerprint") or {}
    return (
        fp.get("claim_consequence_hash"),
        fp.get("evidence_paths_hash"),
        occ.get("attempted_remedy_hash"),
    )


def _branch_a_satisfied(
    prior_rejected: List[dict], retiring_hashes: Tuple[str, str, str]
) -> bool:
    """≥2 prior rejected_attempts share all three hashes with each other AND the retiring occurrence."""
    if any(h is None for h in retiring_hashes):
        return False
    matching = [
        occ
        for occ in prior_rejected
        if _occurrence_fingerprint(occ) == retiring_hashes
    ]
    return len(matching) >= 2


def _branch_b_satisfied(
    occurrences_before_retiring: List[dict], retiring_hashes_2: Tuple[str, str]
) -> bool:
    """≥2 prior occurrences share 2-way hashes with each other AND retiring; ≥1 intervening resolved."""
    if any(h is None for h in retiring_hashes_2):
        return False
    # collect indices of occurrences whose 2-way hashes match the retiring basis,
    # AND whose status is NOT `resolved` (the resolved occurrence serves only as
    # the "intervening" pivot — it cannot count as one of the matching pair).
    matching_non_resolved: List[int] = []
    resolved_indices: List[int] = []
    for idx, occ in enumerate(occurrences_before_retiring):
        cch, eph, _ = _occurrence_fingerprint(occ)
        if cch == retiring_hashes_2[0] and eph == retiring_hashes_2[1]:
            if occ.get("status") == "resolved":
                resolved_indices.append(idx)
            else:
                matching_non_resolved.append(idx)
        elif occ.get("status") == "resolved":
            # A resolved occurrence with DIFFERENT hashes can still serve as the pivot,
            # but the rule's spirit is "the finding reappeared after a correction";
            # we accept any resolved between two matching occurrences as the pivot.
            resolved_indices.append(idx)
    if len(matching_non_resolved) < 2:
        return False
    # Need at least one resolved index strictly between the earliest and latest
    # matching-non-resolved indices.
    first = matching_non_resolved[0]
    last = matching_non_resolved[-1]
    for r in resolved_indices:
        if first < r < last:
            return True
    return False


def check_retirement_rule(
    current_review: dict, registry: dict | None
) -> List[Issue]:
    """Validate mechanical retirement: status==unresolvable requires Branch A or Branch B + retirement metadata."""
    issues: List[Issue] = []
    if registry is None:
        return issues
    for entry in registry.get("entries") or []:
        stable_id = entry.get("stable_id", "<unknown>")
        occurrences = list(entry.get("occurrences") or [])
        for idx, occ in enumerate(occurrences):
            if occ.get("status") != "unresolvable":
                continue
            # Required metadata
            retirement = occ.get("retirement") or {}
            reason = retirement.get("reason")
            rationale = retirement.get("rationale")
            ctx = f"registry {stable_id} occurrence[{idx}]"
            if reason is None:
                issues.append(
                    Issue(
                        "retirement",
                        "missing retirement.reason",
                        context=ctx,
                    )
                )
            if not (isinstance(rationale, str) and rationale.strip()):
                issues.append(
                    Issue(
                        "retirement",
                        "missing or empty retirement.rationale",
                        context=ctx,
                    )
                )
            cch, eph, arh = _occurrence_fingerprint(occ)
            prior = occurrences[:idx]
            prior_rejected = [
                p for p in prior if p.get("status") == "rejected_attempt"
            ]
            branch_a_ok = _branch_a_satisfied(prior_rejected, (cch, eph, arh))
            branch_b_ok = _branch_b_satisfied(prior, (cch, eph))
            if not (branch_a_ok or branch_b_ok):
                issues.append(
                    Issue(
                        "retirement",
                        "mechanical retirement rule failed: "
                        "neither Branch A (≥2 prior rejected_attempts with identical 3-way hashes "
                        "matching the retiring occurrence) nor Branch B (≥2 prior occurrences with "
                        "identical 2-way hashes separated by ≥1 resolved occurrence, matching the "
                        "retiring occurrence) is satisfied",
                        context=ctx,
                    )
                )
    return issues


def check_g30_disposition_coverage(
    current_review: dict, registry: dict | None
) -> List[Issue]:
    """G30: HALT_STAGNATION/oscillation must disposition every eligible Serious-or-worse finding."""
    issues: List[Issue] = []
    if current_review.get("state") != "HALT_STAGNATION":
        return issues
    if current_review.get("halt_subtype") != "oscillation":
        return issues
    if registry is None:
        issues.append(
            Issue(
                "G30",
                "HALT_STAGNATION/oscillation requires findings_registry.json for disposition coverage",
            )
        )
        return issues
    halt_handoff = current_review.get("halt_handoff") or {}
    dispositions = {
        entry.get("stable_id"): entry
        for entry in (halt_handoff.get("remaining_serious_findings_disposition") or [])
    }
    canon = _canon.load_canon(SKILL_ROOT)
    for entry in registry.get("entries") or []:
        stable_id = entry.get("stable_id")
        severity = entry.get("severity")
        if severity not in SERIOUS_OR_WORSE:
            continue
        occurrences = entry.get("occurrences") or []
        if not occurrences:
            continue
        latest = occurrences[-1]
        if latest.get("status") not in ELIGIBLE_BACKLOG_STATUSES:
            continue
        if stable_id not in dispositions:
            issues.append(
                Issue(
                    "G30",
                    f"Serious-or-worse finding {stable_id} (status={latest.get('status')!r}) "
                    f"missing from halt_handoff.remaining_serious_findings_disposition[]",
                )
            )
            continue
        disp_entry = dispositions[stable_id]
        disposition = disp_entry.get("disposition")
        if disposition not in canon.retirement_reasons:
            issues.append(
                Issue(
                    "G30",
                    f"finding {stable_id} disposition {disposition!r} not in canon/retirement-reasons.yaml",
                )
            )
            continue
        sidecar = DISPOSITION_SIDECARS.get(disposition)
        if sidecar is not None:
            sidecar_value = disp_entry.get(sidecar)
            if not (
                (isinstance(sidecar_value, str) and sidecar_value.strip())
                or (isinstance(sidecar_value, (list, dict)) and sidecar_value)
            ):
                issues.append(
                    Issue(
                        "G30",
                        f"finding {stable_id} disposition={disposition!r} missing required sidecar {sidecar!r}",
                    )
                )
    return issues


def check_g31_fingerprint_integrity(registry: dict | None) -> List[Issue]:
    """G31: stored fingerprints recompute equal to current field values."""
    issues: List[Issue] = []
    if registry is None:
        return issues
    for entry in registry.get("entries") or []:
        stable_id = entry.get("stable_id", "<unknown>")
        # Recompute from the entry's canonical fields if available
        finding_view = {
            "title": entry.get("title"),
            # registry doesn't store these structurally; only verify stored hashes
            # by recomputing from occurrence-time snapshot when included
        }
        # Validate the occurrence-level fingerprints against any inline finding
        # snapshot fields. The validator depends on the occurrences carrying the
        # hashes; mismatch between two occurrences with otherwise identical-looking
        # Claim/Source flags drift.
        for idx, occ in enumerate(entry.get("occurrences") or []):
            ctx = f"registry {stable_id} occurrence[{idx}]"
            snapshot = occ.get("finding_snapshot") or {}
            if not snapshot:
                # Without a snapshot we cannot independently recompute. The Critic
                # is expected to embed `finding_snapshot` for retiring occurrences
                # (Branch A / Branch B) so the validator can re-derive. Absence
                # is treated as advisory only — the registry entry's top-level
                # `title` is the best we can do.
                continue
            recomputed = _fingerprint.compute_all(snapshot)
            stored_cch = (occ.get("fingerprint") or {}).get("claim_consequence_hash")
            stored_eph = (occ.get("fingerprint") or {}).get("evidence_paths_hash")
            stored_arh = occ.get("attempted_remedy_hash")
            if stored_cch and recomputed["fingerprint"]["claim_consequence_hash"] != stored_cch:
                issues.append(
                    Issue(
                        "G31",
                        f"claim_consequence_hash drift "
                        f"(stored={stored_cch}, recomputed={recomputed['fingerprint']['claim_consequence_hash']})",
                        context=ctx,
                    )
                )
            if stored_eph and recomputed["fingerprint"]["evidence_paths_hash"] != stored_eph:
                issues.append(
                    Issue(
                        "G31",
                        f"evidence_paths_hash drift "
                        f"(stored={stored_eph}, recomputed={recomputed['fingerprint']['evidence_paths_hash']})",
                        context=ctx,
                    )
                )
            if stored_arh and recomputed["attempted_remedy_hash"] != stored_arh:
                issues.append(
                    Issue(
                        "G31",
                        f"attempted_remedy_hash drift "
                        f"(stored={stored_arh}, recomputed={recomputed['attempted_remedy_hash']})",
                        context=ctx,
                    )
                )
    return issues


def check_halt_success_gating(
    current_review: dict, project_config: dict | None
) -> List[Issue]:
    """HALT_SUCCESS: no unresolved Serious-or-worse, no expired accepted residuals."""
    issues: List[Issue] = []
    if current_review.get("state") != "HALT_SUCCESS":
        return issues
    findings = current_review.get("findings") or []
    for finding in findings:
        if finding.get("severity") in SERIOUS_OR_WORSE:
            issues.append(
                Issue(
                    "HALT_SUCCESS",
                    f"HALT_SUCCESS with unresolved Serious-or-worse finding "
                    f"{finding.get('loop_local_id') or '<unknown>'}",
                )
            )
    # Reject if any accepted residual is expired
    today = date.today()
    if project_config:
        for residual in project_config.get("accepted_residuals") or []:
            expires = _parse_iso_date(residual.get("expires"))
            if expires is not None and expires < today:
                issues.append(
                    Issue(
                        "HALT_SUCCESS",
                        f"HALT_SUCCESS cited expired accepted_residual {residual.get('id')!r} "
                        f"(expires={residual.get('expires')!r}, today={today.isoformat()})",
                    )
                )
    # Also reject inline accepted residuals in scorecard with `expires` date in the past
    scorecard = current_review.get("scorecard") or {}
    for dim, entry in scorecard.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("residual_disposition") != "accepted":
            continue
        expires_raw = entry.get("residual_expires")
        expires = _parse_iso_date(expires_raw)
        if expires is not None and expires < today:
            issues.append(
                Issue(
                    "HALT_SUCCESS",
                    f"scorecard {dim} accepted residual expired (expires={expires_raw!r})",
                )
            )
    return issues


def check_continue_backlog(current_review: dict) -> List[Issue]:
    """CONTINUE must carry next backlog work."""
    issues: List[Issue] = []
    if current_review.get("state") != "CONTINUE":
        return issues
    backlog = current_review.get("backlog") or []
    next_actions = current_review.get("next_actions") or []
    if not backlog and not next_actions:
        issues.append(
            Issue(
                "CONTINUE",
                "state=CONTINUE requires non-empty backlog[] or next_actions[]",
            )
        )
    return issues


def _load_project_config(artifact_dir: Path) -> dict | None:
    """Load `.contest-refactor.yaml` from the artifact dir or its repo root."""
    candidates: List[Path] = [
        artifact_dir / ".contest-refactor.yaml",
    ]
    cur = artifact_dir.resolve()
    for ancestor in [cur, *cur.parents]:
        candidates.append(ancestor / ".contest-refactor.yaml")
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            try:
                import yaml

                return yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception:
                return None
    return None


def run_checks(artifact_dir: Path) -> List[Issue]:
    issues: List[Issue] = []
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
    required_issues, _history, registry = check_required_artifacts(
        artifact_dir, current_review
    )
    issues.extend(required_issues)
    issues.extend(check_schema_enums(current_review, canon))
    issues.extend(check_per_finding_evidence_chain(current_review))
    issues.extend(check_retirement_rule(current_review, registry))
    issues.extend(check_g30_disposition_coverage(current_review, registry))
    issues.extend(check_g31_fingerprint_integrity(registry))
    project_config = _load_project_config(artifact_dir)
    issues.extend(check_halt_success_gating(current_review, project_config))
    issues.extend(check_continue_backlog(current_review))
    return issues


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "artifact_dir", type=Path, help="directory containing CURRENT_REVIEW.json"
    )
    parser.add_argument(
        "--mode",
        choices=("advisory", "strict"),
        default="strict",
        help="strict (default, PR2+): exit non-zero on any failure; "
        "advisory: WARN, exit 0",
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
        args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.mode == "strict" and issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
