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
import os
import re
import subprocess
import sys
import tomllib
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
# resolved / fixed_by_user / withdrawn are done and need not appear.
ELIGIBLE_BACKLOG_STATUSES = ("open", "rejected_attempt", "unresolvable")

# Sidecar field required per disposition (per output-format-json.md halt_handoff schema)
DISPOSITION_SIDECARS = {
    "unresolvable": None,  # no extra sidecar; registry carries retirement block
    "user_decision": "user_decision_ref",
    "outside_scope": "scope_label",
    "unverifiable": "reason",
    "superseded": "superseded_by",
}

# Per-provider default models (per references/provider-adapters.md, verified 2026-05-25).
# When *_model_source == "default", the model value MUST equal this table's entry.
# Used by check_g19_provider_model.
_PROVIDER_DEFAULTS: dict[str, str | None] = {
    "claude_code": "claude-sonnet-4-6",
    "codex": "gpt-5.4-mini",
    "opencode": "deepseek-v4-flash",
    "unknown": None,
}

# G27: forbidden infra-cause vocabulary in implementation_review.reason.
# Spec at validation.md:107-108: reason must not mention "after 2 attempts" or transient
# causes; those live in retry_cause / retry_attempts. Pattern matches only retry-envelope
# infra phrasings the spec explicitly enumerates plus the English variant "timed out".
_G27_FORBIDDEN_REASON_VOCAB = re.compile(
    r"(?i)(after\s+2\s+attempts|\btimeout\b|timed\s+out|spawn[_\s]?error|malformed[_\s]?json)"
)

# G27: exact canonical phrase required when all attempts fail.
_G27_CANONICAL_FAILED_PHRASE = "reviewer unavailable; manual verification required"

# G27: retry_cause enum per spec at validation.md:107.
_G27_RETRY_CAUSES = {"timeout", "spawn_error", "malformed_json"}

# Optional top-level `strictness` preset (advisory metadata only — records the
# `--strictness` the user invoked). MUST NOT influence any score/threshold gate:
# the HALT_SUCCESS / G21 / G5 path reads only score + residual_disposition, never
# this value. `_strictness_isolation_selftest.py` proves that preset-independence
# against the real gate functions. Absent ⇒ "standard". See architecture-rubric.md
# § 9.5+ Threshold ("Strictness presets") and output-format-json.md.
_STRICTNESS_LEVELS = {"standard", "aggressive"}

# G22: archive divider regex for REVIEW_HISTORY.md per output-format-markdown.md.
# Format: `--- Loop <N> (UTC <ISO-8601 timestamp>) ---`
_G22_DIVIDER_RE = re.compile(
    r"^--- Loop \d+ \(UTC \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?(?:\+\d{2}:?\d{2})?\) ---$"
)

# G28: orphan threshold per validation.md:115 (24 hours).
_G28_ORPHAN_SECONDS = 24 * 3600

# G22: commit subject regex per validation.md:92 (PR 1 origin).
# Format: `loop <N>: <verb-phrase>; finding F<n> (stable_id F-<NNN>) <status>
# [registry: +<n> findings(, ~<n> occurrences)?]`. The `[registry: ...]` suffix
# is required at schema_version >= 2.
_G22_COMMIT_SUBJECT_RE = re.compile(
    r"^loop \d+: .+?; finding F\d+ \(stable_id F-\d+\) "
    r"(resolved|carried_forward|fixed_by_user|rejected_attempt|withdrawn)"
    r" \[registry: \+\d+ findings(?:, ~\d+ occurrences)?\]$"
)
# G22: legacy v1 subject (no registry suffix) — used to detect v1 in v2+ artifact.
_G22_COMMIT_SUBJECT_V1_RE = re.compile(
    r"^loop \d+: .+?; finding F\d+ \(stable_id F-\d+\) "
    r"(resolved|carried_forward|fixed_by_user|rejected_attempt|withdrawn)$"
)


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


def _find_git_root(start: Path) -> Path | None:
    """Walk up from `start` looking for a `.git` entry; return its parent or None."""
    try:
        resolved = start.resolve()
    except OSError:
        return None
    for ancestor in [resolved, *resolved.parents]:
        if (ancestor / ".git").exists():
            return ancestor
    return None


def _git_command(repo_root: Path, *args: str) -> tuple[int | None, str]:
    """Run `git <args...>` in `repo_root`. Returns (returncode, stdout) or
    (None, "") if git binary missing or invocation failed entirely.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None, ""
    return result.returncode, (result.stdout or "")


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


def _reference_now() -> datetime:
    """Current UTC time, overridable via the CONTEST_REFACTOR_NOW env var
    (ISO-8601) for deterministic fixture testing of time-relative gates such as
    G28's 24h orphan threshold. Unset in production (the default), so real runs
    are unchanged. A set-but-unparseable value falls back to the wall clock
    rather than crashing a live validation."""
    override = os.environ.get("CONTEST_REFACTOR_NOW")
    if override:
        parsed = _parse_iso_timestamp(override)
        if parsed is not None:
            return parsed
    return datetime.now(timezone.utc)


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
    # Advisory-only preset; validated for typos but never consulted by any gate.
    strictness = current_review.get("strictness")
    if strictness is not None and strictness not in _STRICTNESS_LEVELS:
        issues.append(
            Issue(
                "schema-enum",
                f"strictness {strictness!r} not in {sorted(_STRICTNESS_LEVELS)}",
                context="strictness",
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
    scorecard = current_review.get("scorecard") or {}
    if isinstance(scorecard, dict):
        allowed = set(canon.scorecard_dimensions)
        for key in scorecard.keys():
            if key not in allowed:
                issues.append(
                    Issue(
                        "schema-enum",
                        f"scorecard key {key!r} not in canon (allowed: {sorted(allowed)})",
                        context="scorecard",
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
                    f"finding {stable_id} disposition {disposition!r} not in canon/retirement-reasons.toml",
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


def check_g18_review_history_append(
    current_review: dict, history: dict | None
) -> List[Issue]:
    """G18: REVIEW_HISTORY.json must contain exactly N entries (N = current loop),
    and the most recent entry must equal CURRENT_REVIEW.json (parsed-dict equality).
    Per validation.md:82-83. Schema_version >= 2.
    """
    issues: List[Issue] = []
    if (current_review.get("schema_version") or 1) < 2:
        return issues
    if history is None:
        return issues
    loops = history.get("loops")
    if not isinstance(loops, list):
        issues.append(
            Issue(
                "G18",
                "REVIEW_HISTORY.json.loops must be a list",
            )
        )
        return issues
    expected_n = current_review.get("loop")
    if isinstance(expected_n, int) and len(loops) != expected_n:
        issues.append(
            Issue(
                "G18",
                f"REVIEW_HISTORY.json has {len(loops)} loops[] entries; "
                f"current_review.loop == {expected_n} requires exactly {expected_n} entries",
            )
        )
    if loops and loops[-1] != current_review:
        issues.append(
            Issue(
                "G18",
                "REVIEW_HISTORY.json.loops[-1] must equal CURRENT_REVIEW.json verbatim "
                "(parsed-dict equality)",
            )
        )
    return issues


def check_g19_provider_model(current_review: dict) -> List[Issue]:
    """G19: provider/model attribution per validation.md:84-85 + provider-adapters.md.
    Schema_version >= 2.

    Invariants:
    - Required keys non-empty: provider, *_model_source, spawn_isolation.
    - *_model_source ∈ {"default", "env_override", "user_flag"}.
    - When *_model_source == "default", model value must equal _PROVIDER_DEFAULTS[provider].
    - provider == "unknown" ⇒ spawn_isolation == "inline" AND both models null AND
      both sources == "default" (per provider-adapters.md § unknown explicit text).
    - Known providers (claude_code, codex, opencode) ⇒ both models are non-null strings.
    - Reject placeholder literal "inline-current-model".
    """
    issues: List[Issue] = []
    if (current_review.get("schema_version") or 1) < 2:
        return issues

    provider = current_review.get("provider")
    loop_model = current_review.get("loop_model")
    loop_source = current_review.get("loop_model_source")
    reviewer_model = current_review.get("reviewer_model")
    reviewer_source = current_review.get("reviewer_model_source")
    spawn = current_review.get("spawn_isolation")

    if not provider:
        issues.append(Issue("G19", "provider field required (non-empty)"))
        return issues
    if not spawn:
        issues.append(Issue("G19", "spawn_isolation field required (non-empty)"))
    if not loop_source:
        issues.append(Issue("G19", "loop_model_source field required (non-empty)"))
    if not reviewer_source:
        issues.append(Issue("G19", "reviewer_model_source field required (non-empty)"))

    valid_sources = {"default", "env_override", "user_flag"}
    if loop_source is not None and loop_source not in valid_sources:
        issues.append(
            Issue(
                "G19",
                f"loop_model_source={loop_source!r} not in {sorted(valid_sources)}",
            )
        )
    if reviewer_source is not None and reviewer_source not in valid_sources:
        issues.append(
            Issue(
                "G19",
                f"reviewer_model_source={reviewer_source!r} not in {sorted(valid_sources)}",
            )
        )

    if provider == "unknown":
        if spawn != "inline":
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires spawn_isolation='inline', got {spawn!r}",
                )
            )
        if loop_model is not None:
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires loop_model=null, got {loop_model!r}",
                )
            )
        if reviewer_model is not None:
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires reviewer_model=null, got {reviewer_model!r}",
                )
            )
        if loop_source not in (None, "default"):
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires loop_model_source='default', "
                    f"got {loop_source!r} (per provider-adapters.md § unknown)",
                )
            )
        if reviewer_source not in (None, "default"):
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires reviewer_model_source='default', "
                    f"got {reviewer_source!r} (per provider-adapters.md § unknown)",
                )
            )
    elif provider in _PROVIDER_DEFAULTS:
        # Known provider: both models must be non-null strings (and not the placeholder).
        for field, value in (("loop_model", loop_model), ("reviewer_model", reviewer_model)):
            if value is None or not isinstance(value, str) or not value:
                issues.append(
                    Issue(
                        "G19",
                        f"known provider {provider!r} requires {field} non-empty string, "
                        f"got {value!r}",
                    )
                )
            elif value == "inline-current-model":
                issues.append(
                    Issue(
                        "G19",
                        f"{field}={value!r} is a placeholder; record the real model identity",
                    )
                )
        # Default-source ⇒ value matches provider default.
        provider_default = _PROVIDER_DEFAULTS[provider]
        if loop_source == "default" and isinstance(loop_model, str) and loop_model != provider_default:
            issues.append(
                Issue(
                    "G19",
                    f"loop_model={loop_model!r} marked source='default' but provider "
                    f"{provider!r} default is {provider_default!r}",
                )
            )
        if reviewer_source == "default" and isinstance(reviewer_model, str) and reviewer_model != provider_default:
            issues.append(
                Issue(
                    "G19",
                    f"reviewer_model={reviewer_model!r} marked source='default' but provider "
                    f"{provider!r} default is {provider_default!r}",
                )
            )
    else:
        # Provider not in known table and not "unknown" — invalid value.
        issues.append(
            Issue(
                "G19",
                f"provider={provider!r} not in {sorted(_PROVIDER_DEFAULTS)} "
                "(per provider-adapters.md)",
            )
        )
    return issues


def check_g22_archive_divider(
    artifact_dir: Path, current_review: dict, project_config: dict | None = None
) -> List[Issue]:
    """G22 (both halves): REVIEW_HISTORY.md `--- Loop ` dividers must match
    output-format-markdown.md format; recent commit subjects must match the
    pattern from validation.md:92. Schema_version >= 2.

    The commit-subject sub-check runs only when project_config is non-None
    (i.e., a .contest-refactor.toml is findable in the artifact ancestor
    chain — signal that we're in a loop-managed repo). Fixture dirs nested
    inside the skills repo skip the git shell-out silently.
    """
    issues: List[Issue] = []
    if (current_review.get("schema_version") or 1) < 2:
        return issues
    md_path = artifact_dir / "REVIEW_HISTORY.md"
    if md_path.exists():
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(Issue("G22", f"REVIEW_HISTORY.md unreadable: {exc}"))
            text = ""
        for lineno, line in enumerate(text.splitlines(), start=1):
            if line.startswith("--- Loop "):
                if not _G22_DIVIDER_RE.match(line):
                    issues.append(
                        Issue(
                            "G22",
                            f"REVIEW_HISTORY.md line {lineno}: archive divider does not match "
                            f"`--- Loop <N> (UTC <ISO-8601 timestamp>) ---`",
                            context=line[:120],
                        )
                    )
    # Commit-subject sub-check (requires git + loop-managed repo).
    if project_config is None:
        return issues
    git_root = _find_git_root(artifact_dir)
    if git_root is None:
        return issues
    loop_n = current_review.get("loop")
    if not isinstance(loop_n, int) or loop_n < 1:
        return issues
    rc, out = _git_command(git_root, "log", f"-n{loop_n}", "--format=%s")
    if rc != 0 or not out:
        return issues
    subjects = [s for s in out.splitlines() if s.strip()]
    for subject in subjects:
        if _G22_COMMIT_SUBJECT_RE.match(subject):
            continue
        if _G22_COMMIT_SUBJECT_V1_RE.match(subject):
            issues.append(
                Issue(
                    "G22",
                    f"commit subject missing required `[registry: ...]` suffix "
                    f"(schema_version >= 2 requires it)",
                    context=subject[:120],
                )
            )
        else:
            issues.append(
                Issue(
                    "G22",
                    f"commit subject does not match loop-N pattern "
                    f"`loop <N>: <verb-phrase>; finding F<n> (stable_id F-<NNN>) "
                    f"<status> [registry: +<n> findings(, ~<n> occurrences)?]`",
                    context=subject[:120],
                )
            )
    return issues


def check_g27_retry_envelope(current_review: dict) -> List[Issue]:
    """G27: implementation_review retry envelope shape per validation.md:104-110.
    Schema_version >= 3.

    - retry_count ∈ {1, 2}.
    - retry_count == 1 ⇒ retry_cause is None AND len(retry_attempts) == 1.
    - retry_count == 2 ⇒ retry_cause ∈ {timeout, spawn_error, malformed_json}
      AND len(retry_attempts) == 2 AND retry_attempts[0]["outcome"] == retry_cause.
    - reason MUST NOT match forbidden infra-cause vocabulary.
    - When all attempts non-ok AND verdict == "rejected", reason must equal the
      exact canonical phrase.
    """
    issues: List[Issue] = []
    if (current_review.get("schema_version") or 1) < 3:
        return issues
    impl = current_review.get("implementation_review")
    if not isinstance(impl, dict):
        return issues
    retry_count = impl.get("retry_count")
    retry_cause = impl.get("retry_cause")
    retry_attempts = impl.get("retry_attempts") or []
    reason = impl.get("reason") or ""
    verdict = impl.get("verdict")

    if retry_count not in (1, 2):
        issues.append(
            Issue(
                "G27",
                f"implementation_review.retry_count={retry_count!r} not in {{1, 2}}",
            )
        )
        return issues  # downstream checks depend on retry_count being valid

    if not isinstance(retry_attempts, list):
        issues.append(
            Issue(
                "G27",
                "implementation_review.retry_attempts must be a list",
            )
        )
        return issues

    if retry_count == 1:
        if retry_cause is not None:
            issues.append(
                Issue(
                    "G27",
                    f"retry_count=1 requires retry_cause=null, got {retry_cause!r}",
                )
            )
        if len(retry_attempts) != 1:
            issues.append(
                Issue(
                    "G27",
                    f"retry_count=1 requires retry_attempts length 1, got {len(retry_attempts)}",
                )
            )
    else:  # retry_count == 2
        if retry_cause not in _G27_RETRY_CAUSES:
            issues.append(
                Issue(
                    "G27",
                    f"retry_count=2 requires retry_cause ∈ {sorted(_G27_RETRY_CAUSES)}, "
                    f"got {retry_cause!r}",
                )
            )
        if len(retry_attempts) != 2:
            issues.append(
                Issue(
                    "G27",
                    f"retry_count=2 requires retry_attempts length 2, got {len(retry_attempts)}",
                )
            )
        elif isinstance(retry_attempts[0], dict):
            first_outcome = retry_attempts[0].get("outcome")
            if first_outcome != retry_cause:
                issues.append(
                    Issue(
                        "G27",
                        f"retry_attempts[0].outcome={first_outcome!r} must match "
                        f"retry_cause={retry_cause!r}",
                    )
                )

    if isinstance(reason, str) and _G27_FORBIDDEN_REASON_VOCAB.search(reason):
        match = _G27_FORBIDDEN_REASON_VOCAB.search(reason)
        issues.append(
            Issue(
                "G27",
                f"implementation_review.reason contains forbidden infra-cause vocab "
                f"{match.group(0)!r}; transient causes belong in retry_cause/retry_attempts, "
                f"not reason",
            )
        )

    # Canonical-phrase enforcement: retry_count == 2 AND all attempts non-ok AND verdict rejected.
    if retry_count == 2 and verdict == "rejected" and isinstance(retry_attempts, list):
        all_failed = retry_attempts and all(
            isinstance(a, dict) and a.get("outcome") != "ok" for a in retry_attempts
        )
        if all_failed and reason != _G27_CANONICAL_FAILED_PHRASE:
            issues.append(
                Issue(
                    "G27",
                    f"when retry_count=2 with all attempts non-ok and verdict=rejected, "
                    f"implementation_review.reason must equal exactly "
                    f"{_G27_CANONICAL_FAILED_PHRASE!r}; got {reason!r}",
                )
            )
    return issues


def check_g28_loop_state_freshness(
    artifact_dir: Path,
    current_review: dict,
    project_config: dict | None = None,
) -> List[Issue]:
    """G28 (full): LOOP_STATE.json invariants per validation.md:113-120.
    Schema_version >= 3.

    Sub-checks:
    - loop-number consistency (loop_state.loop == current_review.loop)
    - checkpoint freshness (last_checkpoint_at not >24h before now)
    - step range (step_started ∈ 1..11, step_completed ∈ 0..11)
    - step ordering (step_started >= step_completed)
    - pre_step3_blob_shas covers loop_result.changed_paths
    - post-commit cleanup: LOOP_STATE.json must be absent when commit_attempted_sha
      matches git HEAD (requires project_config + git available)
    """
    issues: List[Issue] = []
    if (current_review.get("schema_version") or 1) < 3:
        return issues
    loop_state_path = artifact_dir / "LOOP_STATE.json"
    if not loop_state_path.exists():
        return issues  # post-commit cleanup state is legal
    loop_state = _load_json(loop_state_path)
    if not isinstance(loop_state, dict):
        issues.append(
            Issue(
                "G28",
                "LOOP_STATE.json must be a JSON object",
            )
        )
        return issues

    ls_loop = loop_state.get("loop")
    cr_loop = current_review.get("loop")
    if ls_loop != cr_loop:
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.loop={ls_loop!r} must equal CURRENT_REVIEW.loop={cr_loop!r} "
                "(mismatch routes to --reset per Resume Precedence Matrix row 3)",
            )
        )

    step_started = loop_state.get("step_started")
    step_completed = loop_state.get("step_completed")
    if not isinstance(step_started, int) or step_started not in range(1, 12):
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.step_started={step_started!r} must be int in 1..11",
            )
        )
    if not isinstance(step_completed, int) or step_completed not in range(0, 12):
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.step_completed={step_completed!r} must be int in 0..11",
            )
        )
    if (
        isinstance(step_started, int)
        and isinstance(step_completed, int)
        and step_started < step_completed
    ):
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.step_started={step_started} < step_completed={step_completed} "
                "(step_started >= step_completed required)",
            )
        )

    last_checkpoint_raw = loop_state.get("last_checkpoint_at")
    last_checkpoint = _parse_iso_timestamp(last_checkpoint_raw)
    if last_checkpoint is None:
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.last_checkpoint_at={last_checkpoint_raw!r} not ISO-8601 parseable",
            )
        )
    else:
        now = _reference_now()
        age_seconds = (now - last_checkpoint).total_seconds()
        if age_seconds > _G28_ORPHAN_SECONDS:
            issues.append(
                Issue(
                    "G28",
                    f"LOOP_STATE.last_checkpoint_at={last_checkpoint_raw!r} is "
                    f"{age_seconds / 3600:.1f}h old (>24h orphan threshold); "
                    "routes to --reset recommendation per Resume Precedence Matrix row 2",
                )
            )

    # pre_step3_blob_shas cross-check (artifact-only, no git required).
    # Per validation.md:118: empty pre_step3_blob_shas AND non-empty
    # loop_result.changed_paths = G28 failure (no restore source recorded).
    loop_result = current_review.get("loop_result") or {}
    changed_paths = loop_result.get("changed_paths") or []
    blob_shas = loop_state.get("pre_step3_blob_shas") or {}
    if changed_paths and not blob_shas:
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.pre_step3_blob_shas is empty but loop_result.changed_paths "
                f"has {len(changed_paths)} entries; no restore source recorded "
                "(narrow revert would have no blob to checkout)",
            )
        )
    elif changed_paths and isinstance(blob_shas, dict):
        missing = [p for p in changed_paths if p not in blob_shas]
        if missing:
            issues.append(
                Issue(
                    "G28",
                    f"loop_result.changed_paths has {len(missing)} entries missing from "
                    f"LOOP_STATE.pre_step3_blob_shas: {missing[:3]}"
                    f"{'…' if len(missing) > 3 else ''}",
                )
            )

    # Post-commit cleanup invariant (requires project_config + git).
    # Per validation.md:117: after Step 3 sub-step 11.f, LOOP_STATE.json must
    # be absent. Presence after a successful commit (commit_attempted_sha
    # matches git HEAD) is a violation.
    if project_config is None:
        return issues
    commit_sha = loop_state.get("commit_attempted_sha")
    if not isinstance(commit_sha, str) or not commit_sha:
        return issues
    git_root = _find_git_root(artifact_dir)
    if git_root is None:
        return issues
    rc, head_sha = _git_command(git_root, "rev-parse", "HEAD")
    if rc != 0 or not head_sha.strip():
        return issues
    head_sha = head_sha.strip()
    if head_sha == commit_sha:
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.json present after successful commit (commit_attempted_sha "
                f"== HEAD {head_sha[:12]}); sub-step 11.f cleanup did not run",
            )
        )
    return issues


def check_halt_success_gating(
    current_review: dict, project_config: dict | None
) -> List[Issue]:
    """HALT_SUCCESS: no unresolved Serious-or-worse, no expired accepted residuals."""
    issues: List[Issue] = []
    if current_review.get("state") not in ("HALT_SUCCESS", "HALT_SUCCESS_candidate"):
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


def check_g21_scorecard(current_review: dict) -> List[Issue]:
    """G21-scorecard: HALT_SUCCESS requires every dimension to satisfy
    score == 10 OR (score >= 9.5 AND residual_disposition == "accepted").

    Promotes [validation.md G21] + [output-format-json.md rule #13] to a
    structural check. Mirrors the rule text from references/validation.md:
        - score == 10                                            → pass
        - score >= 9.5 AND score < 10 AND disp == "accepted"     → pass
        - anything else (including queued at any score)          → fail
    """
    issues: List[Issue] = []
    if current_review.get("state") not in ("HALT_SUCCESS", "HALT_SUCCESS_candidate"):
        return issues
    scorecard = current_review.get("scorecard") or {}
    if not isinstance(scorecard, dict):
        issues.append(
            Issue(
                "G21-scorecard",
                "scorecard must be a mapping of dimension → entry",
            )
        )
        return issues
    for dim, entry in scorecard.items():
        if not isinstance(entry, dict):
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"scorecard {dim!r} entry must be a mapping",
                )
            )
            continue
        score_raw = entry.get("score")
        # Convert score to float for comparison; accept int and float
        try:
            score = float(score_raw)
        except (TypeError, ValueError):
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"scorecard {dim!r} score={score_raw!r} is not a number",
                )
            )
            continue
        disposition = entry.get("residual_disposition")
        if score == 10:
            continue  # explicit pass
        if 9.5 <= score < 10 and disposition == "accepted":
            continue  # accepted residual pass
        # Anything else fails. Build a precise diagnostic.
        if score < 9.5:
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"HALT_SUCCESS dimension {dim!r} score={score} < 9.5 "
                    f"(every scorecard dimension must satisfy score == 10 OR "
                    f"(score >= 9.5 AND residual_disposition == 'accepted'))",
                )
            )
        elif 9.5 <= score < 10 and disposition == "queued":
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"HALT_SUCCESS dimension {dim!r} score={score} has "
                    f"residual_disposition='queued' "
                    f"(queued residuals block HALT_SUCCESS; promote to "
                    f"'accepted' with a rationale or keep state CONTINUE "
                    f"until the backlog item is resolved)",
                )
            )
        else:
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"HALT_SUCCESS dimension {dim!r} score={score} "
                    f"residual_disposition={disposition!r} "
                    f"(every scorecard dimension must satisfy score == 10 OR "
                    f"(score >= 9.5 AND residual_disposition == 'accepted'))",
                )
            )
    return issues


def check_g32_halt_success_challenge(current_review: dict) -> List[Issue]:
    """G32: HALT_SUCCESS terminal state (v4+) requires an independent challenge.

    When state == "HALT_SUCCESS" and schema_version >= 4:
    - halt_success_challenge must be non-null.
    - .outcome must be "held" (outcome "broke" with terminal HALT_SUCCESS is illegal).
    - .challenger_model must be non-empty.
    - .attempts must be a non-empty list.
    - .binding.run_id must equal top-level run_id.
    - .binding.source_rev must equal top-level source_rev.
    - .binding.candidate_commit_sha must be non-empty.

    When state == "HALT_SUCCESS_candidate" and schema_version >= 4:
    - halt_success_challenge must be null.
    - run_id, source_rev, candidate_fingerprint must all be non-null.

    When schema_version < 4: G32 does not fire.
    """
    issues: List[Issue] = []
    schema_version = current_review.get("schema_version") or 1
    if schema_version < 4:
        return issues  # legacy v3 HALT_SUCCESS without a challenge stays valid

    state = current_review.get("state")
    if state not in ("HALT_SUCCESS", "HALT_SUCCESS_candidate"):
        return issues

    top_run_id = current_review.get("run_id")
    top_source_rev = current_review.get("source_rev")
    top_fingerprint = current_review.get("candidate_fingerprint")
    challenge = current_review.get("halt_success_challenge")

    if state == "HALT_SUCCESS_candidate":
        # Candidate is exempt from challenge but must carry identity fields.
        if challenge is not None:
            issues.append(
                Issue(
                    "G32",
                    "state=HALT_SUCCESS_candidate must have halt_success_challenge=null "
                    "(candidate is not yet promoted to terminal; challenge belongs on HALT_SUCCESS)",
                )
            )
        if not top_run_id:
            issues.append(
                Issue(
                    "G32",
                    "state=HALT_SUCCESS_candidate requires run_id non-null (v4+)",
                )
            )
        if not top_source_rev:
            issues.append(
                Issue(
                    "G32",
                    "state=HALT_SUCCESS_candidate requires source_rev non-null (v4+)",
                )
            )
        if not top_fingerprint:
            issues.append(
                Issue(
                    "G32",
                    "state=HALT_SUCCESS_candidate requires candidate_fingerprint non-null (v4+)",
                )
            )
        return issues

    # state == "HALT_SUCCESS" (terminal)
    if challenge is None:
        issues.append(
            Issue(
                "G32",
                "state=HALT_SUCCESS at schema_version >= 4 requires halt_success_challenge "
                "non-null (independent challenge must be run before terminal success)",
            )
        )
        return issues

    if not isinstance(challenge, dict):
        issues.append(
            Issue(
                "G32",
                f"halt_success_challenge must be an object, got {type(challenge).__name__}",
            )
        )
        return issues

    outcome = challenge.get("outcome")
    if outcome == "broke":
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.outcome='broke' with state=HALT_SUCCESS is illegal; "
                "main agent must demote candidate before emitting terminal HALT_SUCCESS",
            )
        )
    elif outcome != "held":
        issues.append(
            Issue(
                "G32",
                f"halt_success_challenge.outcome={outcome!r} must be 'held' "
                "(terminal HALT_SUCCESS requires a passing challenge)",
            )
        )

    challenger_model = challenge.get("challenger_model")
    if not isinstance(challenger_model, str) or not challenger_model.strip():
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.challenger_model must be a non-empty string",
            )
        )

    attempts = challenge.get("attempts")
    if not isinstance(attempts, list) or len(attempts) == 0:
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.attempts must be a non-empty list "
                "(challenger must make at least one arm attempt)",
            )
        )

    binding = challenge.get("binding")
    if not isinstance(binding, dict):
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.binding must be an object with "
                "candidate_commit_sha, run_id, source_rev",
            )
        )
    else:
        candidate_commit_sha = binding.get("candidate_commit_sha")
        if not isinstance(candidate_commit_sha, str) or not candidate_commit_sha.strip():
            issues.append(
                Issue(
                    "G32",
                    "halt_success_challenge.binding.candidate_commit_sha must be a non-empty string",
                )
            )
        binding_run_id = binding.get("run_id")
        if binding_run_id != top_run_id:
            issues.append(
                Issue(
                    "G32",
                    f"halt_success_challenge.binding.run_id={binding_run_id!r} must equal "
                    f"top-level run_id={top_run_id!r}",
                )
            )
        binding_source_rev = binding.get("source_rev")
        if binding_source_rev != top_source_rev:
            issues.append(
                Issue(
                    "G32",
                    f"halt_success_challenge.binding.source_rev={binding_source_rev!r} must equal "
                    f"top-level source_rev={top_source_rev!r}",
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
    """Load `.contest-refactor.toml` from the artifact dir or its repo root."""
    candidates: List[Path] = [
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
    required_issues, history, registry = check_required_artifacts(
        artifact_dir, current_review
    )
    issues.extend(required_issues)
    issues.extend(check_schema_enums(current_review, canon))
    issues.extend(check_per_finding_evidence_chain(current_review))
    issues.extend(check_retirement_rule(current_review, registry))
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
    issues.extend(check_g32_halt_success_challenge(current_review))
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
