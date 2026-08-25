from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import _canon

SCRIPT_DIR = Path(__file__).resolve().parent
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

# Per-provider default models (per references/provider-adapters.md, verified 2026-08-19).
# When *_model_source == "default", the model value MUST equal this table's entry.
# Used by check_g19_provider_model. Kept in sync with the prose by
# _provider_detection_selftest -- the drift this table had on 2026-08-19 (a bare
# `deepseek-v4-flash` against a prose that had moved to the qualified id) went
# unnoticed because nothing cross-checked the two.
_PROVIDER_DEFAULTS: dict[str, str | None] = {
    "claude_code": "claude-sonnet-5",
    "codex": "gpt-5.6-luna",
    # opencode's --model requires provider/model; a bare id is rejected by the CLI.
    "opencode": "opencode-go/deepseek-v4-flash",
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
# is required at schema_version >= 2. See also the no-finding pair below for a
# loop with an empty backlog.
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

# G22: no-finding subject form. A loop with an EMPTY backlog has no finding to
# fill `finding F<n> (stable_id F-<NNN>) <status>` with; before this form
# existed, the only escape was to fabricate a finding id -- observed in
# production as `stable_id F-NEW` on two BenchHype commits (register
# "Instrumented run #7" additional defect #5), which neither G42 (validates
# real backlog items, not commit prose) nor this check (the skip-guard bug
# fixed alongside this form) caught. Never carries a stable_id; unambiguous
# against the finding-bearing regex above (no `finding F` token). Format:
# `loop <N>: <verb-phrase>; no findings [registry: +0 findings]`.
_G22_COMMIT_SUBJECT_NO_FINDING_RE = re.compile(
    r"^loop \d+: .+?; no findings \[registry: \+0 findings\]$"
)
# G22: legacy v1 no-finding subject (no registry suffix) — mirrors
# _G22_COMMIT_SUBJECT_V1_RE so a no-finding subject missing the suffix gets
# the same specific diagnostic instead of the generic "does not match" one.
_G22_COMMIT_SUBJECT_NO_FINDING_V1_RE = re.compile(r"^loop \d+: .+?; no findings$")


class Issue:
    """A single rule failure in an artifact."""

    __slots__ = ("context", "message", "rule")

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
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        # Exit 2 (operator/input error, like "not a directory"), and also catch a
        # non-UTF-8 artifact file — UnicodeDecodeError is not a JSONDecodeError.
        sys.stderr.write(f"error: {path}: JSON parse failed: {exc}\n")
        raise SystemExit(2) from exc
    except OSError as exc:
        # path.exists() passed but the read failed (artifact path is a directory,
        # broken symlink, permissions) — same operator-error class, same exit 2.
        sys.stderr.write(f"error: {path}: could not read artifact file: {exc}\n")
        raise SystemExit(2) from exc


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


# The dev checkout of the agent-skills repo itself (this file lives at
# <repo>/contest-refactor/scripts/_artifact_core.py). Fixture dirs under
# contest-refactor/evals/fixtures/ are nested inside this checkout with no
# git repo of their own, so their git root resolves here too --
# check_g22_archive_divider uses that identity to skip the git shell-out for
# fixtures while still validating a real loop-managed repo that merely lacks
# a .contest-refactor.toml (see that function's docstring).
_SKILLS_REPO_ROOT = _find_git_root(SCRIPT_DIR)


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
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, str):
        try:
            cleaned = value.replace("Z", "+00:00")
            ts = datetime.fromisoformat(cleaned)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
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
    return datetime.now(UTC)


def check_required_artifacts(
    artifact_dir: Path, current_review: dict
) -> tuple[list[Issue], dict | None, dict | None]:
    """Verify required files exist per schema_version. Returns (issues, history, registry)."""
    issues: list[Issue] = []
    schema_version = current_review.get("schema_version") or 1
    md_path = artifact_dir / "CURRENT_REVIEW.md"
    if not md_path.exists():
        issues.append(Issue("required-artifact", "CURRENT_REVIEW.md missing"))
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
                    "REVIEW_HISTORY.json missing (required at schema_version >= 2)",
                )
            )
        else:
            history = _load_json(history_path)
        if not registry_path.exists():
            issues.append(
                Issue(
                    "required-artifact",
                    "findings_registry.json missing (required at schema_version >= 2)",
                )
            )
        else:
            registry = _load_json(registry_path)
        if not history_md_path.exists():
            issues.append(
                Issue(
                    "required-artifact",
                    "REVIEW_HISTORY.md missing (required at schema_version >= 2)",
                )
            )
    return issues, history, registry


def check_schema_enums(current_review: dict, canon: _canon.Canon) -> list[Issue]:
    """Every canon-typed value in CURRENT_REVIEW.json must be valid."""
    issues: list[Issue] = []
    state = current_review.get("state")
    if state is not None and state not in canon.states:
        issues.append(Issue("schema-enum", f"state {state!r} not in canon", context="state"))
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
        allowed_blocker_kinds = set(canon.residual_blocker_kinds)
        for key, entry in scorecard.items():
            if key not in allowed:
                issues.append(
                    Issue(
                        "schema-enum",
                        f"scorecard key {key!r} not in canon (allowed: {sorted(allowed)})",
                        context="scorecard",
                    )
                )
            if isinstance(entry, dict):
                blocker_kind = entry.get("residual_blocker_kind")
                if blocker_kind is not None and blocker_kind not in allowed_blocker_kinds:
                    issues.append(
                        Issue(
                            "schema-enum",
                            f"residual_blocker_kind {blocker_kind!r} not in canon "
                            f"(allowed: {sorted(allowed_blocker_kinds)})",
                            context=f"scorecard {key}",
                        )
                    )
    return issues


def check_per_finding_evidence_chain(current_review: dict) -> list[Issue]:
    """Every finding has all four Evidence Chain pieces populated."""
    issues: list[Issue] = []
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


def check_g16_registry_uniqueness(registry: dict | None) -> list[Issue]:
    """G16: every findings_registry.json entry carries a unique stable_id.

    Duplicates are silently corrupting: `_occurrences_for` returns the first
    match and G30's disposition map (keyed on stable_id) keeps the last, so
    retirement and oscillation run on incomplete occurrence history. G16 was a
    manual checklist only; this is its mechanical duplicate-id enforcement.
    """
    if registry is None:
        return []
    issues: list[Issue] = []
    first_index: dict[str, int] = {}
    for i, entry in enumerate(registry.get("entries") or []):
        sid = entry.get("stable_id")
        if sid is None:
            continue
        if sid in first_index:
            issues.append(
                Issue(
                    "G16",
                    f"duplicate stable_id {sid!r} in findings_registry.json "
                    f"(entries at index {first_index[sid]} and {i})",
                )
            )
        else:
            first_index[sid] = i
    return issues


def check_continue_backlog(current_review: dict) -> list[Issue]:
    """CONTINUE must carry next backlog work."""
    issues: list[Issue] = []
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


_G39_ENTRY_RE = re.compile(r"^([a-z_]+)\s+([+-]\d+(?:\.\d+)?)$")


def check_g39_backlog_score_impact(current_review: dict, canon) -> list[Issue]:
    """G39: every backlog item names the dimensions it moves, machine-readably.

    `score_impact` was a required field that no rule read, so it drifted into prose
    ("Architecture quality + State management each +1.0") that nothing could act on.
    The shape is `<canon_dim_id> <signed delta>`, semicolon-joined for multi-dimension
    items, so the Backlog Prioritization Pass and the priority probe grader can both
    attribute an item to a dimension without parsing English.

    Shape only: the gate never judges whether the projected move is *right*, which is
    the Critic's call and not mechanically decidable.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues

    backlog = current_review.get("backlog") or []
    if not backlog:
        return issues

    known = set(getattr(canon, "scorecard_dimensions", ()) or ())
    scorecard = current_review.get("scorecard") or {}

    for idx, item in enumerate(backlog):
        ctx = f"backlog[{idx}] (priority {item.get('priority')})"
        raw = item.get("score_impact")
        if not isinstance(raw, str) or not raw.strip():
            issues.append(
                Issue("G39", "score_impact is required and must be a non-empty string", ctx)
            )
            continue

        entries = [part.strip() for part in raw.split(";") if part.strip()]
        if not entries:
            issues.append(Issue("G39", f"score_impact has no entries: {raw!r}", ctx))
            continue

        for entry in entries:
            m = _G39_ENTRY_RE.match(entry)
            if not m:
                issues.append(
                    Issue(
                        "G39",
                        f"score_impact entry {entry!r} is not "
                        f"'<canon_dim_id> <+/-delta>' (e.g. 'data_flow +0.5'); "
                        f"join multiple dimensions with ';'",
                        ctx,
                    )
                )
                continue
            dim = m.group(1)
            if known and dim not in known:
                issues.append(
                    Issue(
                        "G39",
                        f"score_impact names unknown dimension {dim!r}; "
                        f"must be a canon/scorecard-dimensions.toml id",
                        ctx,
                    )
                )
            elif scorecard and dim not in scorecard:
                issues.append(
                    Issue(
                        "G39",
                        f"score_impact names {dim!r}, absent from this loop's scorecard",
                        ctx,
                    )
                )
    return issues


def check_g40_discovery_persistence(current_review: dict) -> list[Issue]:
    """G40: Step-0 Discovery survives every loop, not just the first.

    Presence and shape only -- deliberately NOT compared against a prior loop's
    discovery, since a legitimate Step-0 re-run (--reset, --purge) may change it.
    Carrying the object forward faithfully is rule #32's obligation, not the gate's.

    Full rationale: references/validation.md, G40.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues

    loop = current_review.get("loop")
    ctx = f"discovery (loop {loop})" if loop is not None else "discovery"
    discovery = current_review.get("discovery")

    if not isinstance(discovery, dict) or not discovery:
        issues.append(
            Issue(
                "G40",
                "discovery is required on every loop, not only the first — carry the "
                "Step-0 object forward verbatim (rule #32). Repopulate it from the prior "
                "loop's artifact or a real Step-0 re-run; never invent values, which would "
                "substitute a plausible test command for the verified one",
                ctx,
            )
        )
        return issues

    # source_roots is a list; test_command and lens are strings. All three are load-bearing:
    # source_roots and lens feed candidate_fingerprint.py, test_command is the ground-truth
    # oracle every loop re-runs at Step 1 and Step 3.
    roots = discovery.get("source_roots")
    if not isinstance(roots, list) or not [r for r in roots if str(r).strip()]:
        issues.append(Issue("G40", "discovery.source_roots must be a non-empty list", ctx))
    for field in ("test_command", "lens"):
        value = discovery.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(Issue("G40", f"discovery.{field} must be a non-empty string", ctx))
    return issues


def check_g41_cap_loop_executed(current_review: dict) -> list[Issue]:
    """G41: the loop that spends the cap does the work the cap bought.

    The cap gates the NEXT dispatch, not the current loop's execution, so a loop at
    loop == loop_cap with a non-empty backlog must have run Steps 2-3 and left a
    loop_result. The clarifying prose landed first; this gate exists because the
    artifact from the run that got it wrong passes strict validation with zero issues.

    Exemptions, each a legitimate no-work terminal:
      - loop > loop_cap : Step-1 emit on a resumed/misconfigured run; nothing to execute.
      - empty backlog   : Steps 2-3 are skipped by the protocol, so a converged cap
                          terminal honestly has no loop_result. That case is G37's.
      - loop < loop_cap : not policed here. It is an odd state under the clarified
                          semantics, but 13 v1-v3 fixtures carry loop=1/cap=10 while
                          testing unrelated things, and failing them would be noise.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues
    if current_review.get("state") != "HALT_LOOP_CAP":
        return issues

    loop = current_review.get("loop")
    cap = current_review.get("loop_cap")
    # bool is an int subclass; exclude it so a stray True cannot be read as loop 1.
    if isinstance(loop, bool) or isinstance(cap, bool):
        return issues
    if not isinstance(loop, int) or not isinstance(cap, int) or loop != cap:
        return issues

    if not (current_review.get("backlog") or []):
        return issues

    loop_result = current_review.get("loop_result")
    if isinstance(loop_result, dict) and loop_result:
        return issues

    issues.append(
        Issue(
            "G41",
            f"loop {loop} == loop_cap with a non-empty backlog but no loop_result: the "
            f"cap loop emitted HALT_LOOP_CAP without executing Steps 2-3. The cap gates "
            f"the NEXT dispatch, not this loop's execution — run the Priority 1 item, "
            f"then emit HALT_LOOP_CAP in the Step-3 wrap-up. (A reviewer-rejected "
            f"attempt still satisfies this: the revert path writes loop_result with "
            f"targeted_finding_status 'carried_forward'.)",
            f"state=HALT_LOOP_CAP loop={loop} loop_cap={cap}",
        )
    )
    return issues


_G42_STABLE_ID_RE = re.compile(r"^F-\d{3,}$")


def check_g42_backlog_stable_id(current_review: dict) -> list[Issue]:
    """G42: a backlog item carries the identity of the Finding it came from.

    After G39 an item says what it MOVES (score_impact) and priority/rank say where it
    RANKS, but nothing said which finding it IS. The id lived only inside the free-text
    title -- "Collapse the duplicated dialog ceremony (Finding F-003)" -- so following
    one item across loops meant regex-scraping English out of prose, the same
    anti-pattern G39 was written to remove.

    Not substitutable by the registry: findings_registry.json records an occurrence per
    loop while a finding is OPEN, which is not the same as being in the backlog. A
    production run carried a Cosmetic off-path finding as open for all ten loops while
    it never appeared in a backlog once, so a deferral count taken from open-streaks
    would escalate exactly the items that should stay parked.

    The findings link is conditional: membership in this loop's findings[] is required
    only when findings[] is non-empty. Minimal single-gate fixtures legitimately carry
    no findings, and a v4 artifact with a backlog and zero findings is malformed for a
    different reason that is not this gate's business.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues

    backlog = current_review.get("backlog") or []
    if not backlog:
        return issues

    known = {
        f.get("stable_id")
        for f in (current_review.get("findings") or [])
        if isinstance(f, dict) and f.get("stable_id")
    }

    for idx, item in enumerate(backlog):
        ctx = f"backlog[{idx}] (priority {item.get('priority') if isinstance(item, dict) else '?'})"
        if not isinstance(item, dict):
            issues.append(Issue("G42", "backlog item must be an object", ctx))
            continue
        raw = item.get("stable_id")
        if not isinstance(raw, str) or not raw.strip():
            issues.append(
                Issue(
                    "G42",
                    "stable_id is required on every backlog item — the F-NNN id of the "
                    "Finding it derives from. Without it the item has no identity a rule "
                    "can follow across loops, and its id survives only inside the title prose",
                    ctx,
                )
            )
            continue
        stable_id = raw.strip()
        if not _G42_STABLE_ID_RE.match(stable_id):
            issues.append(Issue("G42", f"stable_id {stable_id!r} is not of the form 'F-NNN'", ctx))
            continue
        if known and stable_id not in known:
            issues.append(
                Issue(
                    "G42",
                    f"stable_id {stable_id!r} is not among this loop's findings "
                    f"({', '.join(sorted(known))}). The backlog is derived only from "
                    f"Findings + the Simplification Check and introduces no new concerns, "
                    f"so an item pointing at nothing is a concern introduced at backlog time",
                    ctx,
                )
            )
    return issues
