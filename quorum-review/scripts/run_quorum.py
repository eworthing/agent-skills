#!/usr/bin/env python3
"""
run_quorum.py — Orchestrator for multi-provider quorum review (v3).

Launches multiple reviewer instances (via run_review.py),
collects their verdicts, compiles the deliberation context for subsequent
rounds, and reports consensus status.

v3 changes:
  - Anchor-aware ledger with deterministic conservative merge pipeline
  - Independent verifier outside the panel
  - Mode split for plan/spec/code review with role packs
  - Code anchors and verification prompts that redact panel state

v2.2 changes:
  - Verification execution wired into main() (was functions-only in v2.1)
  - Unanimous blocker optimization: skip verification for unanimously-endorsed blockers
  - should_exit_early() for confidence-based early termination signals
  - Blind mode for rounds 3+: strips support/dispute counts to prevent conformity anchoring
  - All-Agents Drafting: ### Reasoning section added before structured issues

v2.1 changes:
  - Split support fields: proposed_by, endorsed_by, refined_by, disputed_by
  - Default failure policy changed from fail-open to shrink-quorum
  - Default max rounds changed from 5 to 3 (max 5)
  - REVIEW.md rubric file support
  - INDETERMINATE exit code (3) for all-unstructured reviews
  - Per-issue confidence parsing: [B1] (HIGH) description
  - Verification stage for surviving blockers (VERIFIED/INVALIDATED)

v2 changes:
  - Structured review parsing (blocking/non-blocking issues, confidence, scope)
  - Canonical issue IDs (BLK-001, NB-001) with explicit merge metadata
  - Anonymous deliberation (all rounds) to reduce prestige bias
  - Issue-level consensus: artifact verdict derived from surviving blockers
  - Per-issue cross-critique (AGREE/DISAGREE/REFINE) in rounds 2+
  - Context compression in rounds 3+ (issue ledger, not full prose)
  - Explicit failure policy (fail-closed, fail-open, shrink-quorum)
  - Default threshold changed from unanimous to supermajority

This script does NOT revise the plan — the host agent does that between
rounds. This script handles:
  1. Parsing the reviewer panel specification
  2. Launching reviewers (sequential or concurrent)
  3. Collecting and tallying verdicts
  4. Parsing structured reviews into an issue ledger
  5. Compiling deliberation context (anonymous) for next-round prompts
  6. Deriving artifact verdict from surviving blocking issues
  7. Writing round summary with tally and consensus status
"""

import argparse
import copy
import json
import re
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path


# ---------------------------------------------------------------------------
# Quorum thresholds
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "unanimous": lambda approved, total: approved == total,
    "super": lambda approved, total: approved >= total - 1,
    "majority": lambda approved, total: approved > total / 2,
}

MIN_QUORUM_SIZE = 3
MAX_ROUNDS_LIMIT = 5

EXIT_APPROVED = 0
EXIT_ERROR = 1
EXIT_REVISE = 2
EXIT_INDETERMINATE = 3

LEDGER_VERSION = 3


def parse_reviewer_spec(spec):
    """Parse 'provider[:model]' into (provider, model_or_None).

    >>> parse_reviewer_spec("claude:sonnet")
    ('claude', 'sonnet')
    >>> parse_reviewer_spec("codex")
    ('codex', None)
    """
    parts = spec.split(":", 1)
    provider = parts[0].lower()
    model = parts[1] if len(parts) > 1 else None
    return provider, model


VALID_PROVIDERS = {"claude", "gemini", "codex", "copilot"}

VERIFIER_CANDIDATE_SPECS = [
    ("copilot", "gpt-5.4"),
    ("claude", "opus"),
    ("gemini", "pro"),
    ("codex", "o3"),
    ("claude", "sonnet"),
    ("claude", "haiku"),
    ("gemini", "flash"),
    ("gemini", "flash-lite"),
    ("gemini", "auto"),
    ("codex", "o4-mini"),
    ("copilot", None),
    ("claude", None),
    ("gemini", None),
    ("codex", None),
]


def validate_panel(reviewers):
    """Validate the reviewer panel. Returns list of (provider, model) tuples."""
    panel = []
    for spec in reviewers:
        provider, model = parse_reviewer_spec(spec)
        if provider not in VALID_PROVIDERS:
            print(
                f"Error: unknown provider '{provider}'. "
                f"Valid: {', '.join(sorted(VALID_PROVIDERS))}",
                file=sys.stderr,
            )
            sys.exit(1)
        panel.append((provider, model))

    if len(panel) < MIN_QUORUM_SIZE:
        print(
            f"Error: quorum requires at least {MIN_QUORUM_SIZE} reviewers, "
            f"got {len(panel)}. "
            "Add more reviewers to meet the minimum panel size.",
            file=sys.stderr,
        )
        sys.exit(1)

    return panel


def resolve_verifier(panel, verifier_spec=None):
    """Resolve an external verifier outside the active panel.

    If verifier_spec is provided, it must be a provider:model pair and must not
    match any active panel member exactly. Otherwise a deterministic external
    verifier is auto-selected from VERIFIER_CANDIDATE_SPECS.
    """
    active = {tuple(member) for member in panel}

    if verifier_spec:
        if ":" not in verifier_spec:
            print("Error: --verifier must be specified as provider:model", file=sys.stderr)
            sys.exit(1)
        provider, model = parse_reviewer_spec(verifier_spec)
        if provider not in VALID_PROVIDERS:
            print(
                f"Error: unknown verifier provider '{provider}'. "
                f"Valid: {', '.join(sorted(VALID_PROVIDERS))}",
                file=sys.stderr,
            )
            sys.exit(1)
        if not model:
            print("Error: --verifier must be specified as provider:model", file=sys.stderr)
            sys.exit(1)
        verifier = (provider, model)
        if verifier in active:
            print(
                f"Error: verifier '{provider}:{model}' is part of the active panel. "
                "Choose a verifier outside the panel.",
                file=sys.stderr,
            )
            sys.exit(1)
        return verifier

    for verifier in VERIFIER_CANDIDATE_SPECS:
        if verifier not in active:
            return verifier

    active_summary = ", ".join(f"{provider}:{model or 'default'}" for provider, model in panel)
    print(
        "Error: unable to auto-select an external verifier outside the active panel. "
        f"Active panel: {active_summary}. "
        "Pass --verifier provider:model to choose one explicitly.",
        file=sys.stderr,
    )
    sys.exit(1)


def _resolve_verifier_spec(panel, explicit_verifier=None):
    """Backward-compatible wrapper around resolve_verifier()."""
    return resolve_verifier(panel, explicit_verifier)


# ---------------------------------------------------------------------------
# Reviewer execution
# ---------------------------------------------------------------------------


def _resolve_run_review():
    """Locate run_review.py in this skill's scripts/ directory."""
    this_dir = Path(__file__).resolve().parent
    candidate = this_dir / "run_review.py"
    if candidate.exists():
        return str(candidate)
    # Not found — exit with guidance
    print(
        "Error: cannot locate scripts/run_review.py. "
        "Ensure run_review.py is present in the quorum-review scripts/ directory.",
        file=sys.stderr,
    )
    sys.exit(1)


def run_single_reviewer(
    run_review_py,
    provider,
    model,
    plan_file,
    prompt_file,
    output_file,
    session_file,
    events_file,
    effort=None,
    resume=False,
    timeout=600,
    verification_mode=False,
):
    """Run a single reviewer via run_review.py. Returns exit code."""
    cmd = [
        sys.executable,
        run_review_py,
        "--reviewer", provider,
        "--plan-file", plan_file,
        "--prompt-file", prompt_file,
        "--output-file", output_file,
        "--session-file", session_file,
        "--events-file", events_file,
        "--timeout", str(timeout),
    ]
    if model:
        cmd.extend(["--model", model])
    if effort:
        cmd.extend(["--effort", effort])
    if resume:
        cmd.append("--resume")
    if verification_mode:
        cmd.append("--verification-mode")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 30,  # grace period beyond reviewer timeout
        )
        if result.stderr:
            print(f"[{provider}:{model or 'default'}] {result.stderr}", file=sys.stderr)
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"[{provider}:{model or 'default'}] orchestrator timeout", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[{provider}:{model or 'default'}] error: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Verdict parsing
# ---------------------------------------------------------------------------


def parse_verdict(review_file):
    """Parse VERDICT from the last non-empty line of review output.

    Returns 'APPROVED', 'REVISE', or None.
    """
    if not review_file or not Path(review_file).exists():
        return None
    try:
        with Path(review_file).open(encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            if line == "VERDICT: APPROVED":
                return "APPROVED"
            if line == "VERDICT: REVISE":
                return "REVISE"
            # Only check last non-empty line
            return None
    except OSError:
        return None


def read_review(review_file):
    """Read the full review text from a reviewer's output file."""
    if not review_file or not Path(review_file).exists():
        return ""
    try:
        with Path(review_file).open(encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def read_session_meta(session_file):
    """Read session metadata JSON."""
    if not session_file or not Path(session_file).exists():
        return {}
    try:
        with Path(session_file).open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------


_WORD_RE = re.compile(r"[a-z0-9]+")

_COMMON_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "into", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "with",
}

_NEGATION_WORDS = {
    "avoid", "cannot", "denies", "deny", "disable", "disabled", "excluding",
    "exclude", "false", "lacks", "lack", "missing", "never", "no", "not",
    "off", "without",
}

_ACTION_OPPOSITES = (
    ("add", "remove"),
    ("allow", "deny"),
    ("enable", "disable"),
    ("include", "exclude"),
    ("keep", "remove"),
    ("use", "avoid"),
)


def _normalized_tokens(text):
    return [tok for tok in _WORD_RE.findall((text or "").lower()) if tok not in _COMMON_WORDS]


def _normalized_text(text):
    return " ".join(_normalized_tokens(text))


def _parse_anchor_line(line):
    """Parse an anchor-ish line such as `Section: X (lines 12-18)`."""
    stripped = line.strip()
    if not stripped:
        return {}

    key, sep, value = stripped.partition(":")
    if not sep:
        return {}

    key = key.strip().lower()
    value = value.strip()
    if key not in {"section", "anchor", "file", "path", "hunk"}:
        return {}

    anchor = {"kind": key, "raw": stripped}
    if key in {"section", "anchor"}:
        anchor["section"] = value
        line_match = re.search(
            r"\((?:lines?|line)\s*(\d+)(?:\s*-\s*(\d+))?\)\s*$",
            value,
            re.IGNORECASE,
        )
        if line_match:
            anchor["line_start"] = int(line_match.group(1))
            anchor["line_end"] = int(line_match.group(2) or line_match.group(1))
            anchor["section"] = re.sub(
                r"\s*\((?:lines?|line)\s*\d+(?:\s*-\s*\d+)?\)\s*$",
                "",
                value,
                flags=re.IGNORECASE,
            ).strip()
    else:
        anchor["path"] = value

    return anchor


def _extract_issue_anchor(block_text):
    """Extract anchor metadata from trailing issue lines."""
    anchor = {}
    for line in block_text.splitlines():
        parsed = _parse_anchor_line(line)
        if parsed:
            anchor = parsed
            break
    return anchor


# ---------------------------------------------------------------------------
# Structured review parsing (v2)
# ---------------------------------------------------------------------------

_RE_BLOCKING = re.compile(r"^\s*(?:-\s*)?\*{0,2}\[B(\d+)\]\*{0,2}\s*(.+)", re.MULTILINE)
_RE_BLOCKING_WITH_CONF = re.compile(
    r"^\s*(?:-\s*)?\*{0,2}\[B(\d+)\]\s*\((HIGH|MEDIUM|LOW)\)\*{0,2}\s*(.+)", re.MULTILINE | re.IGNORECASE
)
_RE_NON_BLOCKING = re.compile(r"^\s*(?:-\s*)?\*{0,2}\[N(\d+)\]\*{0,2}\s*(.+)", re.MULTILINE)
_RE_CONFIDENCE = re.compile(
    r"(?:^|\n)\s*(?:###?\s*)?Confidence\s*[:\-]?\s*\n?\s*(HIGH|MEDIUM|LOW)",
    re.IGNORECASE,
)
_RE_SCOPE = re.compile(
    r"(?:^|\n)\s*(?:###?\s*)?Scope\s*[:\-]?\s*\n?\s*(.+)",
)


def _extract_section(text, header):
    """Extract text under a ### header, up to the next ### header or end of text.

    Returns the section body text, or the full text if the header is not found
    (backward compatibility with unstructured reviews).
    """
    section_text, _found = _extract_section_with_presence(text, header)
    return section_text


def _extract_section_with_presence(text, header):
    """Return (section_text, found) for a ### section header."""
    pattern = re.compile(
        r"(?:^|\n)###\s+" + re.escape(header) + r"\s*\n",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return text, False  # fallback: search entire text

    start = match.end()
    # Find the next ### header (but not #### sub-headers)
    next_header = re.search(r"\n###\s+(?!#)", text[start:])
    if next_header:
        return text[start : start + next_header.start()], True
    return text[start:], True


def parse_structured_review(review_file):
    """Parse structured review output into issue records.

    Returns dict with:
      - blocking: list of {"id": "B1", "text": "...", "anchor": {...}}
      - non_blocking: list of {"id": "N1", "text": "...", "anchor": {...}}
      - confidence: "HIGH"|"MEDIUM"|"LOW"|None
      - scope: list of strings
      - verdict: "APPROVED"|"REVISE"|None
      - raw_text: full review text
      - structured: bool (True if any structured sections found)
    """
    text = read_review(review_file)
    verdict = parse_verdict(review_file)

    # Extract section text to avoid matching issues from Reasoning section
    blocking_section, has_blocking_section = _extract_section_with_presence(
        text, "Blocking Issues"
    )
    nb_section, has_nb_section = _extract_section_with_presence(
        text, "Non-Blocking Issues"
    )

    # Parse blocking issues — try per-issue confidence first
    conf_matches = {
        m.group(1): (m.group(2).upper(), m.group(3).strip())
        for m in _RE_BLOCKING_WITH_CONF.finditer(blocking_section)
    }
    blocking_matches = list(_RE_BLOCKING.finditer(blocking_section))
    blocking = []
    for idx, m in enumerate(blocking_matches):
        bid = m.group(1)
        next_start = blocking_matches[idx + 1].start() if idx + 1 < len(blocking_matches) else len(blocking_section)
        anchor = _extract_issue_anchor(blocking_section[m.end():next_start])
        if bid in conf_matches:
            issue_conf, issue_text = conf_matches[bid]
            blocking.append({
                "id": f"B{bid}",
                "text": issue_text,
                "confidence": issue_conf,
                "anchor": anchor or None,
            })
        else:
            blocking.append({
                "id": f"B{bid}",
                "text": m.group(2).strip(),
                "confidence": None,
                "anchor": anchor or None,
            })

    nb_matches = list(_RE_NON_BLOCKING.finditer(nb_section))
    non_blocking = []
    for idx, m in enumerate(nb_matches):
        next_start = nb_matches[idx + 1].start() if idx + 1 < len(nb_matches) else len(nb_section)
        anchor = _extract_issue_anchor(nb_section[m.end():next_start])
        non_blocking.append({
            "id": f"N{m.group(1)}",
            "text": m.group(2).strip(),
            "anchor": anchor or None,
        })

    conf_match = _RE_CONFIDENCE.search(text)
    confidence = conf_match.group(1).upper() if conf_match else None

    scope_match = _RE_SCOPE.search(text)
    scope = []
    if scope_match:
        scope = [s.strip().strip('"').strip("'") for s in scope_match.group(1).split(",")]
        scope = [s for s in scope if s]

    structured = bool(blocking or non_blocking or confidence or scope)

    return {
        "blocking": blocking,
        "non_blocking": non_blocking,
        "confidence": confidence,
        "scope": scope,
        "verdict": verdict,
        "raw_text": text,
        "structured": structured,
        "has_blocking_section": has_blocking_section,
        "has_non_blocking_section": has_nb_section,
    }


# ---------------------------------------------------------------------------
# Cross-critique parsing (v2)
# ---------------------------------------------------------------------------

_RE_AGREE = re.compile(r"^\s*\*{0,2}\[AGREE\s+(BLK-\d+|NB-\d+)\]\*{0,2}", re.MULTILINE)
_RE_DISAGREE = re.compile(r"^\s*\*{0,2}\[DISAGREE\s+(BLK-\d+|NB-\d+)\]\*{0,2}\s*(.*)", re.MULTILINE)
_RE_REFINE = re.compile(r"^\s*\*{0,2}\[REFINE\s+(BLK-\d+|NB-\d+)\]\*{0,2}\s*(.*)", re.MULTILINE)
_RE_NEW_BLOCKING = re.compile(r"^\s*\*{0,2}\[B-NEW\]\*{0,2}\s*(.+)", re.MULTILINE)
_RE_NEW_NON_BLOCKING = re.compile(r"^\s*\*{0,2}\[N-NEW\]\*{0,2}\s*(.+)", re.MULTILINE)


def parse_cross_critique(review_file):
    """Extract per-issue AGREE/DISAGREE/REFINE responses from round 2+ reviews.

    Returns dict with:
      - agrees: list of canonical issue IDs
      - disagrees: list of {"id": canonical_id, "reason": "..."}
      - refines: list of {"id": canonical_id, "text": "..."}
      - new_blocking: list of text descriptions
      - new_non_blocking: list of text descriptions
    """
    text = read_review(review_file)

    agrees = [m.group(1) for m in _RE_AGREE.finditer(text)]
    disagrees = [
        {"id": m.group(1), "reason": m.group(2).strip()}
        for m in _RE_DISAGREE.finditer(text)
    ]
    refines = [
        {"id": m.group(1), "text": m.group(2).strip()}
        for m in _RE_REFINE.finditer(text)
    ]
    new_blocking = [m.group(1).strip() for m in _RE_NEW_BLOCKING.finditer(text)]
    new_non_blocking = [m.group(1).strip() for m in _RE_NEW_NON_BLOCKING.finditer(text)]

    return {
        "agrees": agrees,
        "disagrees": disagrees,
        "refines": refines,
        "new_blocking": new_blocking,
        "new_non_blocking": new_non_blocking,
    }


# ---------------------------------------------------------------------------
# Verification stage (v3)
# ---------------------------------------------------------------------------


def _format_anchor_for_prompt(anchor):
    anchor = anchor if isinstance(anchor, dict) else {}
    if not anchor:
        return "None"
    lines = []
    for key in (
        "artifact_kind",
        "artifact_path",
        "anchor_kind",
        "anchor_start",
        "anchor_end",
        "anchor_hash",
        "section",
        "path",
        "kind",
        "line_start",
        "line_end",
        "raw",
    ):
        value = anchor.get(key)
        if value not in (None, "", []):
            lines.append(f"- {key}: {value}")
    if not lines:
        return "None"
    return "\n".join(lines)


def generate_verification_prompts(ledger, artifact_text, threshold_name, total, mode="plan"):
    """Generate independent verification prompts for surviving blockers.

    Returns list of dicts with:
      - issue_id: canonical ID
      - prompt: verification prompt text
    """
    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])
    prompts = []
    artifact_heading = _artifact_heading_for_mode(mode)

    for issue in ledger["issues"]:
        if _issue_severity(issue) != "blocking" or _issue_status(issue) != "open" or _issue_is_invalidated(issue):
            continue
        if not threshold_fn(_issue_support_count(issue), total):
            continue

        anchor_text = _format_anchor_for_prompt(issue.get("anchor"))
        prompt = (
            f"{VERIFICATION_CONTRACT}\n\n"
            "## Blocker\n\n"
            f"- ID: {issue['id']}\n"
            f"- Summary: {_issue_summary(issue)}\n\n"
            "### Anchor\n\n"
            f"{anchor_text}\n\n"
            f"## Current {artifact_heading}\n\n"
            f"{artifact_text}\n"
        )
        prompts.append({"issue_id": issue["id"], "prompt": prompt})

    return prompts


_RE_VERIFIED = re.compile(
    r"^\s*(?:`)?VERIFIED\s+(BLK-\d+)(?:`)?", re.MULTILINE
)
_RE_INVALIDATED = re.compile(
    r"^\s*(?:`)?INVALIDATED\s+(BLK-\d+)(?:`)?", re.MULTILINE
)


def parse_verification_response(review_file):
    """Parse VERIFIED/INVALIDATED responses from a verification review.

    Returns dict mapping issue_id -> "VERIFIED" or "INVALIDATED".
    """
    text = read_review(review_file)
    results = {}

    for m in _RE_VERIFIED.finditer(text):
        results[m.group(1)] = "VERIFIED"
    for m in _RE_INVALIDATED.finditer(text):
        results[m.group(1)] = "INVALIDATED"

    return results


# ---------------------------------------------------------------------------
# Issue ledger (v3)
# ---------------------------------------------------------------------------


LEDGER_SCHEMA_VERSION = 3
MERGE_CLASSIFICATIONS = {"EQUIVALENT", "RELATED_DISTINCT", "CONFLICT", "UNCERTAIN"}
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from",
    "if", "in", "into", "is", "it", "may", "of", "on", "or", "our", "should",
    "that", "the", "their", "this", "to", "use", "with",
}
_POSITIVE_VERBS = {"add", "allow", "enable", "keep", "permit", "retain", "support", "use"}
_NEGATIVE_VERBS = {"avoid", "block", "deny", "disable", "drop", "forbid", "remove"}
_MERGE_IGNORE_TOKENS = {
    "endpoint",
    "endpoints",
    "handler",
    "handlers",
    "route",
    "routes",
    "path",
    "paths",
    "file",
    "files",
    "line",
    "lines",
    "hunk",
    "diff",
    "query",
    "queries",
}
_MERGE_TOKEN_ALIASES = {
    "authentication": "auth",
    "authorisation": "auth",
    "authorization": "auth",
}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item is not None]
    return [value]


def _unique_preserve_order(items):
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _normalize_text(text):
    text = " ".join((text or "").lower().split())
    return re.sub(r"[^a-z0-9\s]+", " ", text).strip()


def _summary_tokens(text):
    tokens = [t for t in re.findall(r"[a-z0-9]+", _normalize_text(text)) if t not in _STOPWORDS]
    return tokens


def _summary_similarity(left, right):
    left_norm = _normalize_text(left)
    right_norm = _normalize_text(right)
    if not left_norm and not right_norm:
        return 1.0
    if not left_norm or not right_norm:
        return 0.0
    ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
    left_tokens = set(_summary_tokens(left_norm))
    right_tokens = set(_summary_tokens(right_norm))
    if left_tokens and right_tokens:
        ratio = max(ratio, len(left_tokens & right_tokens) / len(left_tokens | right_tokens))
    return ratio


def _anchor_context_tokens(anchor):
    anchor = anchor if isinstance(anchor, dict) else {}
    tokens = set()
    for field in ("artifact_path", "section"):
        value = anchor.get(field)
        if value:
            tokens.update(_summary_tokens(str(value)))
    return tokens


def _canonical_merge_token(token):
    return _MERGE_TOKEN_ALIASES.get(token, token)


def _issue_merge_signature(issue):
    anchor = issue.get("anchor") if isinstance(issue, dict) else {}
    ignore = _anchor_context_tokens(anchor) | _MERGE_IGNORE_TOKENS | _NEGATION_WORDS
    tokens = [
        _canonical_merge_token(token)
        for token in _summary_tokens(_issue_summary(issue))
        if token not in ignore
    ]
    return tuple(tokens)


def _normalize_anchor(anchor, artifact_kind="plan"):
    anchor = anchor if isinstance(anchor, dict) else {}
    artifact_path = anchor.get("artifact_path") or anchor.get("path")
    anchor_kind = anchor.get("anchor_kind") or anchor.get("kind")
    if not anchor_kind:
        if anchor.get("anchor_start") is not None or anchor.get("line_start") is not None:
            anchor_kind = "line_range"
        elif anchor.get("section"):
            anchor_kind = "section"
    return {
        "artifact_kind": anchor.get("artifact_kind") or artifact_kind,
        "artifact_path": artifact_path,
        "anchor_kind": anchor_kind,
        "anchor_start": anchor.get("anchor_start", anchor.get("line_start")),
        "anchor_end": anchor.get("anchor_end", anchor.get("line_end")),
        "anchor_hash": anchor.get("anchor_hash"),
        "section": anchor.get("section"),
        "raw": anchor.get("raw"),
    }


def _issue_summary(issue):
    claim = issue.get("claim") if isinstance(issue.get("claim"), dict) else {}
    return (
        claim.get("summary")
        or claim.get("text")
        or claim.get("owner_summary")
        or issue.get("owner_summary")
        or issue.get("text")
        or ""
    )


def _format_verification_anchor(anchor):
    anchor = anchor if isinstance(anchor, dict) else {}
    if anchor.get("raw"):
        return anchor["raw"]
    if anchor.get("artifact_path"):
        return f"Path: {anchor['artifact_path']}"
    if anchor.get("section"):
        if anchor.get("anchor_start") is not None:
            start = anchor.get("anchor_start")
            end = anchor.get("anchor_end") if anchor.get("anchor_end") is not None else start
            if start == end:
                return f"Section: {anchor['section']} (line {start})"
            return f"Section: {anchor['section']} (lines {start}-{end})"
        return f"Section: {anchor['section']}"
    if anchor.get("anchor_kind"):
        return anchor["anchor_kind"]
    return "No anchor provided"


def _issue_category(issue):
    claim = issue.get("claim") if isinstance(issue.get("claim"), dict) else {}
    return claim.get("category") or "general"


def _issue_status(issue):
    adjudication = _issue_adjudication(issue)
    return adjudication.get("status") or issue.get("status") or "open"


def _issue_severity(issue):
    identity = issue.get("identity") if isinstance(issue.get("identity"), dict) else {}
    return identity.get("severity") or issue.get("severity") or "blocking"


def _issue_round_introduced(issue):
    identity = issue.get("identity") if isinstance(issue.get("identity"), dict) else {}
    return identity.get("round_introduced") or issue.get("round_introduced") or 0


def _issue_adjudication(issue):
    adjudication = issue.get("adjudication")
    if isinstance(adjudication, dict):
        return adjudication
    return {}


def _issue_verification(issue):
    verification = issue.get("verification")
    if isinstance(verification, dict):
        return verification
    return {}


def _issue_relations(issue):
    relations = issue.get("relations")
    if isinstance(relations, dict):
        return relations
    return {
        "proposed_by": [],
        "endorsed_by": [],
        "refined_by": [],
        "disputed_by": [],
        "merged_from": [],
        "related_distinct": [],
        "conflict": [],
        "conflicts_with": [],
    }


def _issue_support_count(issue):
    adjudication = _issue_adjudication(issue)
    relations = _issue_relations(issue)
    proposed = _as_list(
        relations.get("proposed_by")
        or adjudication.get("proposed_by", issue.get("proposed_by"))
    )
    endorsed = _as_list(
        relations.get("endorsed_by")
        or adjudication.get("endorsed_by", issue.get("endorsed_by"))
    )
    refined = _as_list(
        relations.get("refined_by")
        or adjudication.get("refined_by", issue.get("refined_by"))
    )
    derived = len(proposed) + len(endorsed) + len(refined)
    if derived:
        return derived
    support_count = adjudication.get("support_count", issue.get("support_count"))
    return int(support_count) if support_count is not None else 0


def _issue_dispute_count(issue):
    adjudication = _issue_adjudication(issue)
    relations = _issue_relations(issue)
    disputed = _as_list(
        relations.get("disputed_by")
        or adjudication.get("disputed_by", issue.get("disputed_by"))
    )
    if disputed:
        return len(disputed)
    dispute_count = adjudication.get("dispute_count", issue.get("dispute_count"))
    return int(dispute_count) if dispute_count is not None else 0


def _sync_issue_aliases(issue):
    identity = issue.setdefault("identity", {})
    claim = issue.setdefault("claim", {})
    adjudication = issue.setdefault("adjudication", {})
    verification = issue.setdefault("verification", {})
    relations = issue.setdefault("relations", {})

    identity.setdefault("source_reviewer", issue.get("source_reviewer"))
    identity.setdefault("source_label", issue.get("source_label"))
    identity.setdefault("round_introduced", issue.get("round_introduced", 1))
    identity.setdefault("severity", issue.get("severity", "blocking"))

    claim.setdefault("summary", "")
    claim.setdefault("category", "general")
    claim.setdefault("impact", "")
    claim.setdefault("evidence_refs", [])
    claim.setdefault("text", claim.get("summary", issue.get("text", "")))
    claim.setdefault("owner_summary", claim.get("summary", issue.get("owner_summary", "")))

    proposed = _unique_preserve_order(_as_list(adjudication.get("proposed_by")))
    endorsed = _unique_preserve_order(_as_list(adjudication.get("endorsed_by")))
    refined = _unique_preserve_order(_as_list(adjudication.get("refined_by")))
    disputed = _unique_preserve_order(_as_list(adjudication.get("disputed_by")))
    merged_from = _unique_preserve_order(_as_list(adjudication.get("merged_from")))

    adjudication["proposed_by"] = proposed
    adjudication["endorsed_by"] = endorsed
    adjudication["refined_by"] = refined
    adjudication["disputed_by"] = disputed
    adjudication["support_count"] = len(proposed) + len(endorsed) + len(refined)
    adjudication["dispute_count"] = len(disputed)
    adjudication["merged_from"] = merged_from
    adjudication["status"] = adjudication.get("status", issue.get("status", "open"))
    adjudication["resolved_round"] = adjudication.get("resolved_round", issue.get("resolved_round"))

    verification.setdefault("status", "pending")
    verification.setdefault("verified_by", None)
    verification.setdefault("verification_rationale", None)

    relations["proposed_by"] = _unique_preserve_order(
        _as_list(relations.get("proposed_by")) + proposed
    )
    relations["endorsed_by"] = _unique_preserve_order(
        _as_list(relations.get("endorsed_by")) + endorsed
    )
    relations["refined_by"] = _unique_preserve_order(
        _as_list(relations.get("refined_by")) + refined
    )
    relations["disputed_by"] = _unique_preserve_order(
        _as_list(relations.get("disputed_by")) + disputed
    )
    relations["merged_from"] = _unique_preserve_order(
        _as_list(relations.get("merged_from")) + merged_from
    )
    relations["related_distinct"] = _unique_preserve_order(_as_list(relations.get("related_distinct")))
    relations["conflict"] = _unique_preserve_order(
        _as_list(relations.get("conflict")) + _as_list(relations.get("conflicts_with"))
    )
    relations["conflicts_with"] = relations["conflict"]

    issue["identity"] = identity
    issue["source_reviewer"] = identity.get("source_reviewer", issue.get("source_reviewer"))
    issue["source_label"] = identity.get("source_label", issue.get("source_label"))
    issue["round_introduced"] = identity.get("round_introduced", issue.get("round_introduced"))
    issue["severity"] = identity.get("severity", issue.get("severity"))
    issue["proposed_by"] = proposed[0] if proposed else issue.get("proposed_by")
    issue["endorsed_by"] = endorsed
    issue["refined_by"] = refined
    issue["disputed_by"] = disputed
    issue["support_count"] = adjudication["support_count"]
    issue["dispute_count"] = adjudication["dispute_count"]
    issue["merged_from"] = merged_from
    issue["owner_summary"] = claim.get("summary", issue.get("owner_summary", ""))
    issue["text"] = issue["owner_summary"]
    issue["confidence"] = issue.get("confidence")
    issue["status"] = adjudication["status"]
    issue["resolved_round"] = adjudication["resolved_round"]
    issue["verification_status"] = verification.get("status")
    issue["verification_reason"] = verification.get("verification_rationale")
    issue["conflict"] = relations["conflict"]
    issue["relation"] = relations
    return issue


def _make_issue(
    canonical_id,
    severity,
    round_num,
    reviewer_idx,
    source_label,
    text,
    *,
    anchor=None,
    category="general",
    confidence=None,
):
    issue = {
        "id": canonical_id,
        "identity": {
            "source_reviewer": reviewer_idx,
            "source_label": source_label,
            "round_introduced": round_num,
            "severity": severity,
        },
        "severity": severity,
        "status": "open",
        "round_introduced": round_num,
        "anchor": _normalize_anchor(anchor),
        "claim": {
            "summary": text,
            "text": text,
            "owner_summary": text,
            "category": category or "general",
            "impact": "",
            "evidence_refs": [],
        },
        "adjudication": {
            "proposed_by": [reviewer_idx],
            "endorsed_by": [],
            "refined_by": [],
            "disputed_by": [],
            "support_count": 1,
            "dispute_count": 0,
            "merged_from": [],
            "status": "open",
            "resolved_round": None,
        },
        "verification": {
            "status": "pending",
            "verified_by": None,
            "verification_rationale": None,
        },
        "relations": {
            "proposed_by": [reviewer_idx],
            "endorsed_by": [],
            "refined_by": [],
            "disputed_by": [],
            "merged_from": [],
            "related_distinct": [],
            "conflict": [],
            "conflicts_with": [],
        },
        "source_reviewer": reviewer_idx,
        "source_label": source_label,
        "text": text,
        "owner_summary": text,
        "proposed_by": reviewer_idx,
        "endorsed_by": [],
        "refined_by": [],
        "disputed_by": [],
        "support_count": 1,
        "dispute_count": 0,
        "merged_from": [],
        "confidence": confidence,
        "resolved_round": None,
    }
    return _sync_issue_aliases(issue)


def _migrate_issue(issue):
    if not isinstance(issue, dict):
        return None
    migrated = copy.deepcopy(issue)
    identity = migrated.get("identity") if isinstance(migrated.get("identity"), dict) else {}
    if "claim" not in migrated:
        summary = migrated.get("owner_summary") or migrated.get("text") or ""
        migrated["claim"] = {
            "summary": summary,
            "text": migrated.get("text") or summary,
            "owner_summary": migrated.get("owner_summary") or summary,
            "category": migrated.get("category") or "general",
            "impact": migrated.get("impact") or "",
            "evidence_refs": _as_list(migrated.get("evidence_refs")),
        }
    if "anchor" not in migrated:
        migrated["anchor"] = _normalize_anchor(migrated.get("anchor"))
    else:
        migrated["anchor"] = _normalize_anchor(migrated.get("anchor"))
    if "adjudication" not in migrated:
        proposed = _as_list(migrated.get("proposed_by") or migrated.get("source_reviewer"))
        if not proposed and migrated.get("source_reviewer") is not None:
            proposed = [migrated["source_reviewer"]]
        migrated["adjudication"] = {
            "proposed_by": proposed,
            "endorsed_by": _as_list(migrated.get("endorsed_by")),
            "refined_by": _as_list(migrated.get("refined_by")),
            "disputed_by": _as_list(migrated.get("disputed_by")),
            "support_count": migrated.get("support_count"),
            "dispute_count": migrated.get("dispute_count"),
            "merged_from": _as_list(migrated.get("merged_from")),
            "status": migrated.get("status") or "open",
            "resolved_round": migrated.get("resolved_round"),
        }
    if "verification" not in migrated:
        migrated["verification"] = {
            "status": "invalidated" if migrated.get("status") == "invalidated_by_verifier" else "pending",
            "verified_by": None,
            "verification_rationale": None,
        }
    if "relations" not in migrated:
        migrated["relations"] = {
            "proposed_by": _as_list(migrated.get("proposed_by") or migrated.get("source_reviewer")),
            "endorsed_by": _as_list(migrated.get("endorsed_by")),
            "refined_by": _as_list(migrated.get("refined_by")),
            "disputed_by": _as_list(migrated.get("disputed_by")),
            "merged_from": _as_list(migrated.get("merged_from")),
            "related_distinct": _as_list(migrated.get("related_distinct")),
            "conflict": _as_list(migrated.get("conflict") or migrated.get("conflicts_with")),
            "conflicts_with": _as_list(migrated.get("conflicts_with")),
        }
    if "identity" not in migrated:
        migrated["identity"] = {
            "source_reviewer": migrated.get("source_reviewer"),
            "source_label": migrated.get("source_label"),
            "round_introduced": migrated.get("round_introduced", 1),
            "severity": migrated.get("severity") or "blocking",
        }
    migrated["identity"].setdefault("source_reviewer", migrated.get("source_reviewer"))
    migrated["identity"].setdefault("source_label", migrated.get("source_label"))
    migrated["identity"].setdefault("round_introduced", migrated.get("round_introduced", 1))
    migrated["identity"].setdefault("severity", migrated.get("severity") or "blocking")
    migrated.setdefault("status", "open")
    migrated.setdefault("round_introduced", 1)
    migrated.setdefault("source_reviewer", migrated.get("proposed_by"))
    migrated.setdefault("source_label", migrated.get("id"))
    migrated = _sync_issue_aliases(migrated)
    if migrated["verification"].get("status") == "invalidated" and migrated["status"] != "merged":
        migrated["status"] = "invalidated_by_verifier"
    return migrated


def _migrate_merge(merge):
    if not isinstance(merge, dict):
        return None
    migrated = copy.deepcopy(merge)
    migrated["survivor"] = migrated.get("survivor")
    migrated["absorbed"] = _unique_preserve_order(_as_list(migrated.get("absorbed")))
    migrated["round"] = migrated.get("round")
    migrated["classification"] = migrated.get("classification") or "EQUIVALENT"
    migrated["reason"] = migrated.get("reason") or ""
    return migrated


def _migrate_ledger(ledger):
    if not isinstance(ledger, dict):
        return _empty_ledger()

    migrated = _empty_ledger()
    migrated.update({k: copy.deepcopy(v) for k, v in ledger.items() if k not in {"issues", "merges", "rounds"}})
    migrated["schema_version"] = LEDGER_SCHEMA_VERSION
    migrated["version"] = LEDGER_SCHEMA_VERSION
    migrated["issues"] = []
    for issue in ledger.get("issues", []):
        migrated_issue = _migrate_issue(issue)
        if migrated_issue:
            migrated["issues"].append(migrated_issue)
    migrated["merges"] = [
        merge for merge in (
            _migrate_merge(entry) for entry in ledger.get("merges", [])
        )
        if merge
    ]
    migrated["rounds"] = copy.deepcopy(ledger.get("rounds", {}))

    if "next_blk_id" not in ledger:
        next_blk = 1
        for issue in migrated["issues"]:
            if issue.get("id", "").startswith("BLK-"):
                match = re.search(r"(\d+)$", issue["id"])
                if match:
                    next_blk = max(next_blk, int(match.group(1)) + 1)
        migrated["next_blk_id"] = next_blk
    else:
        migrated["next_blk_id"] = ledger["next_blk_id"]

    if "next_nb_id" not in ledger:
        next_nb = 1
        for issue in migrated["issues"]:
            if issue.get("id", "").startswith("NB-"):
                match = re.search(r"(\d+)$", issue["id"])
                if match:
                    next_nb = max(next_nb, int(match.group(1)) + 1)
        migrated["next_nb_id"] = next_nb
    else:
        migrated["next_nb_id"] = ledger["next_nb_id"]

    return migrated


def _issue_sort_key(issue):
    match = re.search(r"-(\d+)$", issue.get("id", ""))
    return (0 if _issue_severity(issue) == "blocking" else 1, int(match.group(1)) if match else 10**9, issue.get("id", ""))


def _issue_is_invalidated(issue):
    verification = _issue_verification(issue)
    return _issue_status(issue) == "invalidated_by_verifier" or verification.get("status") == "invalidated"


def _issue_is_mergeable(issue):
    return _issue_status(issue) == "open" and not _issue_is_invalidated(issue)


def _sync_verification_state(target_ledger, source_ledger):
    """Copy verifier outcomes from a source ledger snapshot into a target."""
    source_map = {issue["id"]: issue for issue in source_ledger.get("issues", [])}
    for issue in target_ledger.get("issues", []):
        source_issue = source_map.get(issue.get("id"))
        if not source_issue:
            continue
        verification = source_issue.get("verification")
        if isinstance(verification, dict):
            issue.setdefault("verification", {}).update(copy.deepcopy(verification))
        if source_issue.get("status") == "invalidated_by_verifier":
            issue["status"] = "invalidated_by_verifier"
            issue.setdefault("adjudication", {})["status"] = "invalidated_by_verifier"
        _sync_issue_aliases(issue)


def _refresh_issue(issue):
    _sync_issue_aliases(issue)
    return issue


def _refresh_round_snapshot(ledger, round_num):
    key = str(round_num)
    round_info = ledger.setdefault("rounds", {}).setdefault(key, {})
    round_info.setdefault("reviewer_count", 0)
    round_info["blocking_open"] = sum(
        1 for issue in ledger.get("issues", [])
        if _issue_severity(issue) == "blocking" and _issue_status(issue) == "open"
    )
    round_info["nb_open"] = sum(
        1 for issue in ledger.get("issues", [])
        if _issue_severity(issue) == "non_blocking" and _issue_status(issue) == "open"
    )
    return round_info


def _empty_ledger():
    """Create an empty issue ledger."""
    return {
        "version": LEDGER_SCHEMA_VERSION,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "next_blk_id": 1,
        "next_nb_id": 1,
        "issues": [],
        "merges": [],
        "rounds": {},
    }


def load_ledger(ledger_file):
    """Load issue ledger from JSON file."""
    if not ledger_file or not Path(ledger_file).exists():
        return _empty_ledger()
    try:
        with Path(ledger_file).open(encoding="utf-8") as f:
            data = json.load(f)
        return _migrate_ledger(data)
    except (json.JSONDecodeError, OSError):
        return _empty_ledger()


def save_ledger(ledger_file, ledger):
    """Save issue ledger to JSON file."""
    normalized = _migrate_ledger(ledger)
    Path(ledger_file).write_text(json.dumps(normalized, indent=2), encoding="utf-8")


def build_issue_ledger(panel, quorum_id, tmpdir, round_num, prev_ledger=None):
    """Build/update issue ledger from structured reviews.

    Round 1: Extract issues from each reviewer, assign canonical IDs.
    Rounds 2+: Parse cross-critique responses, update agreement counts,
               add new issues from [B-NEW]/[N-NEW] tags.

    Returns updated ledger dict.
    """
    ledger = _migrate_ledger(prev_ledger) if prev_ledger else _empty_ledger()

    if round_num == 1:
        blocking_count = 0
        nb_count = 0
        approved_count = 0

        for idx, (_provider, _model) in enumerate(panel, 1):
            review_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
            parsed = parse_structured_review(review_file)
            category = ", ".join(parsed["scope"]) if parsed["scope"] else "general"

            for issue in parsed["blocking"]:
                canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                ledger["next_blk_id"] += 1
                ledger["issues"].append(
                    _make_issue(
                        canonical_id,
                        "blocking",
                        round_num,
                        idx,
                        issue["id"],
                        issue["text"],
                        anchor=issue.get("anchor"),
                        category=category,
                        confidence=issue.get("confidence"),
                    )
                )
                blocking_count += 1

            for issue in parsed["non_blocking"]:
                canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                ledger["next_nb_id"] += 1
                ledger["issues"].append(
                    _make_issue(
                        canonical_id,
                        "non_blocking",
                        round_num,
                        idx,
                        issue["id"],
                        issue["text"],
                        anchor=issue.get("anchor"),
                        category=category,
                    )
                )
                nb_count += 1

            if parsed["verdict"] == "APPROVED":
                approved_count += 1

        ledger["rounds"][str(round_num)] = {
            "reviewer_count": len(panel),
            "blocking_open": blocking_count,
            "nb_open": nb_count,
            "approved_count": approved_count,
        }

    else:
        approved_count = 0
        issue_map = {issue["id"]: issue for issue in ledger["issues"]}

        for idx, (_provider, _model) in enumerate(panel, 1):
            review_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
            critique = parse_cross_critique(review_file)
            parsed = parse_structured_review(review_file)
            category = ", ".join(parsed["scope"]) if parsed["scope"] else "general"

            for issue_id in critique["agrees"]:
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx not in _as_list(issue["adjudication"].get("proposed_by")) and idx not in issue["adjudication"]["endorsed_by"]:
                        issue["adjudication"]["endorsed_by"].append(idx)
                        _refresh_issue(issue)

            for entry in critique["disagrees"]:
                issue_id = entry["id"]
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx not in issue["adjudication"]["disputed_by"]:
                        issue["adjudication"]["disputed_by"].append(idx)
                        _refresh_issue(issue)

            for entry in critique["refines"]:
                issue_id = entry["id"]
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx not in _as_list(issue["adjudication"].get("proposed_by")) and idx not in issue["adjudication"]["refined_by"]:
                        issue["adjudication"]["refined_by"].append(idx)
                        _refresh_issue(issue)

            for text in critique["new_blocking"]:
                canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                ledger["next_blk_id"] += 1
                new_issue = _make_issue(
                    canonical_id,
                    "blocking",
                    round_num,
                    idx,
                    "B-NEW",
                    text,
                    category=category,
                )
                ledger["issues"].append(new_issue)
                issue_map[canonical_id] = new_issue

            for text in critique["new_non_blocking"]:
                canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                ledger["next_nb_id"] += 1
                new_issue = _make_issue(
                    canonical_id,
                    "non_blocking",
                    round_num,
                    idx,
                    "N-NEW",
                    text,
                    category=category,
                )
                ledger["issues"].append(new_issue)
                issue_map[canonical_id] = new_issue

            existing_texts = {
                _normalize_text(_issue_summary(i))
                for i in ledger["issues"]
                if _issue_summary(i)
            }

            if parsed.get("has_blocking_section"):
                for section_issue in parsed["blocking"]:
                    text = section_issue["text"].strip()
                    normalized = _normalize_text(text)
                    if normalized not in existing_texts:
                        canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                        ledger["next_blk_id"] += 1
                        new_issue = _make_issue(
                            canonical_id,
                            "blocking",
                            round_num,
                            idx,
                            "section-scan",
                            text,
                            anchor=section_issue.get("anchor"),
                            category=category,
                            confidence=section_issue.get("confidence"),
                        )
                        ledger["issues"].append(new_issue)
                        issue_map[canonical_id] = new_issue
                        existing_texts.add(normalized)

            if parsed.get("has_non_blocking_section"):
                for section_issue in parsed["non_blocking"]:
                    text = section_issue["text"].strip()
                    normalized = _normalize_text(text)
                    if normalized not in existing_texts:
                        canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                        ledger["next_nb_id"] += 1
                        new_issue = _make_issue(
                            canonical_id,
                            "non_blocking",
                            round_num,
                            idx,
                            "section-scan",
                            text,
                            anchor=section_issue.get("anchor"),
                            category=category,
                        )
                        ledger["issues"].append(new_issue)
                        issue_map[canonical_id] = new_issue
                        existing_texts.add(normalized)

            if parsed["verdict"] == "APPROVED":
                approved_count += 1

        ledger["rounds"][str(round_num)] = {
            "reviewer_count": len(panel),
            "blocking_open": sum(
                1 for i in ledger["issues"]
                if _issue_severity(i) == "blocking" and _issue_status(i) == "open"
            ),
            "nb_open": sum(
                1 for i in ledger["issues"]
                if _issue_severity(i) == "non_blocking" and _issue_status(i) == "open"
            ),
            "approved_count": approved_count,
        }

    return ledger


def _line_range_overlap(left_anchor, right_anchor, proximity=3):
    left_start = left_anchor.get("anchor_start")
    left_end = left_anchor.get("anchor_end")
    right_start = right_anchor.get("anchor_start")
    right_end = right_anchor.get("anchor_end")
    if left_start is None or right_start is None:
        return False
    left_end = left_end if left_end is not None else left_start
    right_end = right_end if right_end is not None else right_start
    return not (left_end + proximity < right_start or right_end + proximity < left_start)


def _normalize_section(section):
    """Normalize a section string for fuzzy comparison.

    Strips parenthetical suffixes like '(lines 28-31)' and collapses
    whitespace. Deliberately keeps the full section path so different parent
    sections do not collapse into one anchor.
    """
    if not section:
        return ""
    s = re.sub(r"\(lines?\s*[\d\-,\s]+\)", "", section)
    return " ".join(s.lower().split()).strip()


def _sections_related(left_section, right_section):
    """Conservative section comparison after normalization."""
    left_norm = _normalize_section(left_section)
    right_norm = _normalize_section(right_section)
    if not left_norm or not right_norm:
        return False
    return left_norm == right_norm


def _anchors_related(left, right):
    left_anchor = left.get("anchor") or {}
    right_anchor = right.get("anchor") or {}
    if not left_anchor or not right_anchor:
        return False
    if (
        left_anchor.get("anchor_hash")
        and left_anchor.get("anchor_hash") == right_anchor.get("anchor_hash")
    ):
        return True
    if (
        left_anchor.get("artifact_path")
        and left_anchor.get("artifact_path") == right_anchor.get("artifact_path")
    ):
        if _line_range_overlap(left_anchor, right_anchor):
            return True
        if (
            left_anchor.get("anchor_kind") == right_anchor.get("anchor_kind") == "section"
            and _sections_related(left_anchor.get("section"), right_anchor.get("section"))
        ):
            return True
        if (
            left_anchor.get("anchor_kind") == right_anchor.get("anchor_kind") == "hunk"
            and left_anchor.get("raw")
            and left_anchor.get("raw") == right_anchor.get("raw")
        ):
            return True
    left_section = left_anchor.get("section")
    right_section = right_anchor.get("section")
    if (
        left_anchor.get("anchor_kind") == right_anchor.get("anchor_kind") == "section"
        and not left_anchor.get("artifact_path")
        and not right_anchor.get("artifact_path")
        and left_section
        and right_section
        and _sections_related(left_section, right_section)
    ):
        return True
    return False


def _anchor_has_location(anchor):
    if not isinstance(anchor, dict):
        return False
    return any(
        anchor.get(field) is not None
        for field in ("artifact_path", "anchor_hash", "section", "anchor_start", "anchor_end")
    )


def _has_conflict_signal(left_summary, right_summary):
    left_tokens = set(_summary_tokens(left_summary))
    right_tokens = set(_summary_tokens(right_summary))
    shared_tokens = (left_tokens & right_tokens) - _STOPWORDS
    if not shared_tokens:
        return False
    left_positive = bool(left_tokens & _POSITIVE_VERBS)
    left_negative = bool(left_tokens & _NEGATIVE_VERBS)
    right_positive = bool(right_tokens & _POSITIVE_VERBS)
    right_negative = bool(right_tokens & _NEGATIVE_VERBS)
    return (left_positive and right_negative) or (left_negative and right_positive)


def generate_merge_candidates(ledger):
    candidates = []
    issues = [
        issue for issue in ledger.get("issues", [])
        if _issue_is_mergeable(issue)
    ]
    issues.sort(key=_issue_sort_key)

    for left, right in combinations(issues, 2):
        if _issue_severity(left) != _issue_severity(right):
            continue

        left_summary = _issue_summary(left)
        right_summary = _issue_summary(right)
        similarity = _summary_similarity(left_summary, right_summary)
        anchor_related = _anchors_related(left, right)
        if not (anchor_related or similarity >= 0.45):
            continue

        basis = []
        if anchor_related:
            basis.append("anchor")
        if similarity >= 0.85:
            basis.append("summary_exact")
        elif similarity >= 0.55:
            basis.append("summary_close")

        candidates.append(
            {
                "left": left["id"],
                "right": right["id"],
                "severity": _issue_severity(left),
                "left_summary": left_summary,
                "right_summary": right_summary,
                "similarity": round(similarity, 3),
                "basis": basis,
            }
        )

    return candidates


def classify_merge_candidate(left, right):
    left_summary = _issue_summary(left)
    right_summary = _issue_summary(right)
    similarity = _summary_similarity(left_summary, right_summary)
    anchor_related = _anchors_related(left, right)
    conflict_signal = _has_conflict_signal(left_summary, right_summary)
    same_norm = _normalize_text(left_summary) == _normalize_text(right_summary)
    left_anchor = left.get("anchor") or {}
    right_anchor = right.get("anchor") or {}
    left_has_location = _anchor_has_location(left_anchor)
    right_has_location = _anchor_has_location(right_anchor)
    left_signature = _issue_merge_signature(left)
    right_signature = _issue_merge_signature(right)
    same_signature = bool(left_signature) and left_signature == right_signature

    if conflict_signal and anchor_related:
        return "CONFLICT", "opposing actions on the same anchor"
    if same_norm:
        if anchor_related or (not left_has_location and not right_has_location):
            return "EQUIVALENT", "identical normalized summaries"
        return "RELATED_DISTINCT", "same wording but different anchors"
    if same_signature:
        if anchor_related:
            return "EQUIVALENT", "matching concern signature on the same anchor"
        if not left_has_location and not right_has_location:
            return "EQUIVALENT", "matching concern signature without anchors"
    if anchor_related:
        if similarity >= 0.35:
            return "RELATED_DISTINCT", "same area but meaningfully different concerns"
        return "UNCERTAIN", "same area without enough evidence for equivalence"
    if similarity >= 0.45:
        return "RELATED_DISTINCT", "lexically related but distinct"
    return "UNCERTAIN", "insufficient similarity"


def _log_merge_decision(log_path, record):
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(log_path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def _merge_issue_records(survivor, absorbed):
    survivor_adj = survivor.setdefault("adjudication", {})
    absorbed_adj = absorbed.get("adjudication", {})

    for field in ("proposed_by", "endorsed_by", "refined_by", "disputed_by", "merged_from"):
        survivor_adj[field] = _unique_preserve_order(
            _as_list(survivor_adj.get(field)) + _as_list(absorbed_adj.get(field))
        )
    survivor_adj["merged_from"] = _unique_preserve_order(
        _as_list(survivor_adj.get("merged_from")) + [absorbed["id"]]
    )

    survivor_rel = survivor.setdefault("relations", {})
    absorbed_rel = absorbed.get("relations", {})
    for field in ("related_distinct", "conflict", "conflicts_with"):
        survivor_rel[field] = _unique_preserve_order(
            _as_list(survivor_rel.get(field)) + _as_list(absorbed_rel.get(field))
        )

    survivor_claim = survivor.setdefault("claim", {})
    absorbed_claim = absorbed.get("claim", {})
    if not survivor_claim.get("impact") and absorbed_claim.get("impact"):
        survivor_claim["impact"] = absorbed_claim["impact"]
    if not survivor_claim.get("evidence_refs") and absorbed_claim.get("evidence_refs"):
        survivor_claim["evidence_refs"] = list(absorbed_claim["evidence_refs"])

    if not survivor.get("anchor") or survivor.get("anchor", {}).get("artifact_kind") == "plan":
        absorbed_anchor = absorbed.get("anchor") or {}
        if absorbed_anchor:
            survivor["anchor"] = copy.deepcopy(absorbed_anchor)

    _sync_issue_aliases(survivor)
    absorbed["status"] = "merged"
    absorbed.setdefault("adjudication", {})["status"] = "merged"
    absorbed.setdefault("verification", {})["status"] = "pending"
    return survivor


def apply_merge_pipeline(ledger, quorum_id, tmpdir, round_num):
    candidates = generate_merge_candidates(ledger)
    if not candidates:
        return {"candidates": [], "merged": [], "log_path": str(Path(tmpdir) / f"qr-{quorum_id}-merge-log.jsonl")}

    issue_map = {issue["id"]: issue for issue in ledger.get("issues", [])}
    parent = {issue_id: issue_id for issue_id in issue_map}
    rank = {issue_id: 0 for issue_id in issue_map}
    log_path = Path(tmpdir) / f"qr-{quorum_id}-merge-log.jsonl"
    merged_pairs = []

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left_id, right_id):
        left_root = find(left_id)
        right_root = find(right_id)
        if left_root == right_root:
            return
        if rank[left_root] < rank[right_root]:
            parent[left_root] = right_root
        elif rank[left_root] > rank[right_root]:
            parent[right_root] = left_root
        else:
            parent[right_root] = left_root
            rank[left_root] += 1

    for candidate in candidates:
        left = issue_map[candidate["left"]]
        right = issue_map[candidate["right"]]
        classification, reason = classify_merge_candidate(left, right)
        decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "round": round_num,
            "left": left["id"],
            "right": right["id"],
            "severity": _issue_severity(left),
            "classification": classification,
            "reason": reason,
            "basis": candidate["basis"],
            "similarity": candidate["similarity"],
        }

        if classification == "EQUIVALENT":
            union(left["id"], right["id"])
            decision["action"] = "merge_candidate"
        elif classification == "RELATED_DISTINCT":
            left_rel = left.setdefault("relations", {})
            right_rel = right.setdefault("relations", {})
            left_rel.setdefault("related_distinct", [])
            right_rel.setdefault("related_distinct", [])
            if right["id"] not in left_rel["related_distinct"]:
                left_rel["related_distinct"].append(right["id"])
            if left["id"] not in right_rel["related_distinct"]:
                right_rel["related_distinct"].append(left["id"])
            _sync_issue_aliases(left)
            _sync_issue_aliases(right)
            decision["action"] = "relation_only"
        elif classification == "CONFLICT":
            left_rel = left.setdefault("relations", {})
            right_rel = right.setdefault("relations", {})
            left_rel.setdefault("conflict", left_rel.get("conflicts_with", []))
            right_rel.setdefault("conflict", right_rel.get("conflicts_with", []))
            if right["id"] not in left_rel["conflict"]:
                left_rel["conflict"].append(right["id"])
            if left["id"] not in right_rel["conflict"]:
                right_rel["conflict"].append(left["id"])
            left_rel["conflicts_with"] = left_rel["conflict"]
            right_rel["conflicts_with"] = right_rel["conflict"]
            _sync_issue_aliases(left)
            _sync_issue_aliases(right)
            decision["action"] = "relation_only"
        else:
            decision["action"] = "log_only"

        _log_merge_decision(log_path, decision)

    groups = defaultdict(list)
    for issue_id in issue_map:
        groups[find(issue_id)].append(issue_id)

    for root, issue_ids in groups.items():
        if len(issue_ids) <= 1:
            continue
        ordered = sorted(issue_ids, key=lambda issue_id: _issue_sort_key(issue_map[issue_id]))
        survivor_id = ordered[0]
        survivor = issue_map[survivor_id]
        absorbed_ids = ordered[1:]
        for absorbed_id in absorbed_ids:
            absorbed = issue_map[absorbed_id]
            _merge_issue_records(survivor, absorbed)
            ledger.setdefault("merges", []).append(
                {
                    "survivor": survivor_id,
                    "absorbed": [absorbed_id],
                    "round": round_num,
                    "classification": "EQUIVALENT",
                    "reason": "merged by deterministic equivalence",
                }
            )
            merged_pairs.append({"survivor": survivor_id, "absorbed": [absorbed_id]})
            _log_merge_decision(
                log_path,
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "round": round_num,
                    "left": survivor_id,
                    "right": absorbed_id,
                    "severity": _issue_severity(survivor),
                    "classification": "EQUIVALENT",
                    "action": "merge_applied",
                    "survivor": survivor_id,
                    "absorbed": [absorbed_id],
                    "reason": "deterministic merge applied",
                },
            )

    _refresh_round_snapshot(ledger, round_num)
    return {
        "candidates": candidates,
        "merged": merged_pairs,
        "log_path": str(log_path),
    }


# ---------------------------------------------------------------------------
# Derived verdict (v3)
# ---------------------------------------------------------------------------


def derive_verdict(ledger, threshold_name, total_reviewers):
    """Derive artifact verdict from surviving blocking issues.

    A blocking issue 'survives' if its support_count meets the configured
    threshold relative to total_reviewers.

    Returns (verdict, surviving_issues, dropped_issues) where:
      - verdict: "APPROVED" or "REVISE"
      - surviving_issues: list of issue dicts that survive
      - dropped_issues: list of issue dicts that don't meet threshold
    """
    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])

    open_blockers = [
        i for i in ledger["issues"]
        if _issue_severity(i) == "blocking" and _issue_status(i) == "open" and not _issue_is_invalidated(i)
    ]

    surviving = []
    dropped = []

    for issue in open_blockers:
        # An issue "survives" if its support count meets the threshold
        # We invert the threshold: instead of "N approved out of total",
        # we check "support_count supporters out of total"
        if threshold_fn(_issue_support_count(issue), total_reviewers):
            surviving.append(issue)
        else:
            dropped.append(issue)

    verdict = "REVISE" if surviving else "APPROVED"
    return verdict, surviving, dropped


def format_issue_consensus(ledger, threshold_name, total_reviewers):
    """Format issue consensus for display.

    Returns human-readable markdown showing which issues survive.
    """
    verdict, surviving, dropped = derive_verdict(ledger, threshold_name, total_reviewers)

    lines = ["### Issue Consensus\n"]

    if surviving:
        for issue in surviving:
            lines.append(
                f"- {issue['id']} \"{_issue_summary(issue)}\": "
                f"support {_issue_support_count(issue)}/{total_reviewers} "
                f"— SURVIVES"
            )
    if dropped:
        for issue in dropped:
            lines.append(
                f"- {issue['id']} \"{_issue_summary(issue)}\": "
                f"support {_issue_support_count(issue)}/{total_reviewers} "
                f"— DROPPED"
            )

    # Non-blocking issues (informational)
    open_nb = [
        i for i in ledger["issues"]
        if _issue_severity(i) == "non_blocking" and _issue_status(i) == "open"
    ]
    for issue in open_nb:
        lines.append(
            f"- {issue['id']} \"{_issue_summary(issue)}\": "
            f"support {_issue_support_count(issue)}/{total_reviewers} "
            f"— NON-BLOCKING"
        )

    surviving_count = len(surviving)
    lines.append(
        f"\n### Derived Verdict: {verdict} "
        f"({surviving_count} blocking issue(s) survive {threshold_name} threshold)"
    )

    return "\n".join(lines)


def _is_unanimous(ledger, issue_id, total):
    """Check if a blocker has unanimous support (support_count >= total).

    Used to skip verification for unanimously-endorsed blockers — these are
    high-probability true positives that don't need additional validation.
    """
    issue = next((i for i in ledger["issues"] if i["id"] == issue_id), None)
    return issue is not None and _issue_support_count(issue) >= total and not _issue_is_invalidated(issue)


def should_exit_early(ledger, threshold_name, total_reviewers):
    """Check whether further deliberation rounds would be mathematically futile.

    Returns (should_exit, reason) where:
      - should_exit: True if no further rounds can change the outcome
      - reason: human-readable explanation (empty string if should_exit is False)

    Checks:
    1. No open blockers remain → verdict is APPROVED, stop
    2. No blockers meet threshold → verdict would be APPROVED, stop
    3. All surviving blockers at max support → more rounds won't change, stop
    """
    open_blockers = [
        i for i in ledger["issues"]
        if _issue_severity(i) == "blocking" and _issue_status(i) == "open" and not _issue_is_invalidated(i)
    ]

    if not open_blockers:
        return True, "no open blockers remain"

    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])
    surviving = [i for i in open_blockers if threshold_fn(_issue_support_count(i), total_reviewers)]

    if not surviving:
        return True, "no blockers meet threshold — verdict would be APPROVED"

    all_at_max = all(_issue_support_count(i) >= total_reviewers for i in surviving)
    if all_at_max:
        return True, "all surviving blockers at maximum support — further rounds cannot change outcome"

    return False, ""


# ---------------------------------------------------------------------------
# Deliberation context compilation (v2 — always anonymous)
# ---------------------------------------------------------------------------


def compile_deliberation(panel, quorum_id, tmpdir, round_num):
    """Compile all reviews from a round into a deliberation document.

    All deliberation context is ANONYMOUS — reviewers are labeled as
    Reviewer A, B, C, etc. with no provider/model information. This
    prevents prestige bias from anchoring convergence.

    Returns (deliberation_text, verdicts, reviewer_map) where:
      - deliberation_text: anonymous markdown for prompts
      - verdicts: list of (anon_label, verdict, actual_model, actual_effort)
      - reviewer_map: dict mapping anon labels to true identities
    """
    sections = []
    verdicts = []
    reviewer_map = {}

    for idx, (provider, model) in enumerate(panel, 1):
        anon_label = f"Reviewer {chr(64 + idx)}"  # A, B, C, ...
        review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
        session_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json"

        review_text = read_review(str(review_file))
        verdict = parse_verdict(str(review_file))
        meta = read_session_meta(str(session_file))

        actual_model = meta.get("model", model or "default")
        actual_effort = meta.get("effort", "default")

        verdict_str = verdict or "NO VERDICT"
        verdicts.append((anon_label, verdict, actual_model, actual_effort))

        reviewer_map[anon_label] = {
            "provider": provider,
            "model": model,
            "actual_model": actual_model,
            "actual_effort": actual_effort,
            "idx": idx,
        }

        # Anonymous section header — no model/effort info
        sections.append(
            f"--- {anon_label} — VERDICT: {verdict_str} ---\n\n{review_text}"
        )

    deliberation_text = "\n\n".join(sections)
    return deliberation_text, verdicts, reviewer_map


# ---------------------------------------------------------------------------
# Context compression (v2)
# ---------------------------------------------------------------------------


def compile_compressed_context(ledger, panel, quorum_id, tmpdir, round_num,
                               blind_mode=False):
    """Build compressed context for rounds 3+.

    Instead of full prose, carries forward:
    1. Issue ledger table (open issues only, with agreement counts)
    2. Per-reviewer: only their issue lists + verdict (not full prose)

    When blind_mode=True, omits Support and Disputes columns to prevent
    conformity anchoring in later rounds.

    Returns markdown string.
    """
    lines = ["## Open Issue Ledger\n"]

    open_issues = [i for i in ledger["issues"] if _issue_status(i) == "open"]
    if open_issues:
        if blind_mode:
            lines.append("| ID | Severity | Description |")
            lines.append("|-----|----------|-------------|")
            for issue in open_issues:
                lines.append(
                    f"| {issue['id']} | {_issue_severity(issue)} | "
                    f"{_issue_summary(issue)[:60]} |"
                )
        else:
            lines.append("| ID | Severity | Description | Support | Disputes |")
            lines.append("|-----|----------|-------------|---------|----------|")
            for issue in open_issues:
                lines.append(
                    f"| {issue['id']} | {_issue_severity(issue)} | "
                    f"{_issue_summary(issue)[:60]} | "
                    f"{_issue_support_count(issue)} | {_issue_dispute_count(issue)} |"
                )
    else:
        lines.append("No open issues remaining.")

    lines.append("\n## Prior Round Issue Lists (condensed)\n")

    for idx, (_provider, _model) in enumerate(panel, 1):
        anon_label = f"Reviewer {chr(64 + idx)}"
        review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
        parsed = parse_structured_review(str(review_file))

        lines.append(f"### {anon_label} — VERDICT: {parsed['verdict'] or 'NO VERDICT'}")
        if parsed["blocking"]:
            lines.append("**Blocking:**")
            for issue in parsed["blocking"]:
                lines.append(f"- [{issue['id']}] {issue['text']}")
        if parsed["non_blocking"]:
            lines.append("**Non-blocking:**")
            for issue in parsed["non_blocking"]:
                lines.append(f"- [{issue['id']}] {issue['text']}")
        if not parsed["blocking"] and not parsed["non_blocking"]:
            lines.append("(No structured issues found)")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt generation (v3)
# ---------------------------------------------------------------------------

REVIEW_CONTRACT_PLAN = (
    "## Review Contract\n\n"
    "You are reviewing a plan or spec as part of a multi-reviewer quorum panel.\n\n"
    "Structure your review using EXACTLY these sections:\n\n"
    "### Reasoning\n"
    "Write your complete analysis of the plan here. Consider architecture,\n"
    "security, testing, performance, and any other relevant areas. This\n"
    "section MUST come before your issue lists.\n\n"
    "### Blocking Issues\n"
    "Issues that MUST be resolved before execution. Use [B1], [B2], etc.\n"
    "Optionally include per-issue confidence: (HIGH), (MEDIUM), or (LOW).\n"
    "For each issue, include a Section: line referencing the plan section name\n"
    "and line numbers from the numbered plan (e.g., Section: Step 3 (lines 42-55)).\n"
    "- [B1] (HIGH) Description of blocking issue...\n"
    "  Section: <plan section> (lines <N-M>)\n"
    "  Recommendation: Concrete fix or mitigation\n"
    "- [B2] (MEDIUM) Description of blocking issue...\n"
    "(Write \"None\" if no blocking issues.)\n\n"
    "### Non-Blocking Issues\n"
    "Suggestions and improvements. Use [N1], [N2], etc.\n"
    "- [N1] Description...\n"
    "  Section: <plan section> (lines <N-M>)\n"
    "  Recommendation: Suggested improvement\n"
    "(Write \"None\" if no non-blocking issues.)\n\n"
    "### Confidence\n"
    "State your confidence in this review: HIGH, MEDIUM, or LOW\n\n"
    "### Scope\n"
    "Which areas of the plan does your review cover? (e.g., \"architecture\",\n"
    "\"security\", \"testing\", \"API design\", \"performance\")\n\n"
    "Your review MUST end with a verdict on the LAST non-empty line:\n"
    "- `VERDICT: APPROVED` if the plan is ready to execute as-is\n"
    "- `VERDICT: REVISE` if changes are needed before execution\n\n"
    "The verdict line must be EXACTLY one of these two strings, nothing else."
)

REVIEW_CONTRACT_SPEC = REVIEW_CONTRACT_PLAN
REVIEW_CONTRACT_V2 = REVIEW_CONTRACT_PLAN

CROSS_CRITIQUE_INSTRUCTIONS = (
    "## Cross-Critique Instructions\n\n"
    "Below are anonymous reviews from the prior round and the current issue ledger.\n\n"
    "### Part 1: Respond to every open issue\n\n"
    "For EACH open issue in the Current Issue Ledger section below, write exactly\n"
    "one response. Every issue needs your position — if you skip an issue, the\n"
    "orchestrator records no data from you on it, which weakens the consensus.\n\n"
    "- `[AGREE BLK-001]` — you confirm this issue is valid\n"
    "- `[DISAGREE BLK-001] reason` — you dispute this issue (include your reasoning)\n"
    "- `[REFINE BLK-001] revised description` — the concern is valid but you want to\n"
    "  adjust its scope or description (counts as support, like AGREE)\n\n"
    "You may also raise entirely new issues discovered in this round:\n"
    "- `[B-NEW] description` — new blocking issue\n"
    "- `[N-NEW] description` — new non-blocking issue\n\n"
    "Put all cross-critique responses together BEFORE your review sections.\n\n"
    "### Part 2: Updated structured review\n\n"
    "After your cross-critique responses, provide your full updated review using\n"
    "the standard sections (### Reasoning, ### Blocking Issues, ### Non-Blocking\n"
    "Issues, ### Confidence, ### Scope) and end with your VERDICT line.\n\n"
    "### Example round 2+ response\n\n"
    "```\n"
    "[AGREE BLK-001]\n"
    "[DISAGREE BLK-002] The plan already handles this via the retry middleware\n"
    "[REFINE NB-001] Should also cover WebSocket connections, not just HTTP\n"
    "[B-NEW] No rate limiting on the public API endpoints\n\n"
    "### Reasoning\n"
    "After reviewing the other panelists' feedback...\n\n"
    "### Blocking Issues\n"
    "- [B1] (HIGH) BLK-001 remains unaddressed — auth is still missing\n"
    "  Section: Auth middleware (lines 12-18)\n"
    "  Recommendation: Add role-based access control before deployment\n"
    "- [B2] (MEDIUM) New: No rate limiting on public API\n"
    "  Section: API gateway (lines 34-40)\n"
    "  Recommendation: Add token-bucket rate limiter\n\n"
    "### Non-Blocking Issues\n"
    "None\n\n"
    "### Confidence\n"
    "HIGH\n\n"
    "### Scope\n"
    "security, API design\n\n"
    "VERDICT: REVISE\n"
    "```"
)

REVIEW_CONTRACT_CODE = (
    "## Review Contract\n\n"
    "You are reviewing a code change as part of a multi-reviewer quorum panel.\n\n"
    "Structure your review using EXACTLY these sections:\n\n"
    "### Reasoning\n"
    "Write your complete analysis of the change here. Consider correctness,\n"
    "security, performance, maintainability, and operational risk. This section\n"
    "MUST come before your issue lists.\n\n"
    "### Blocking Issues\n"
    "Issues that MUST be resolved before execution. Use [B1], [B2], etc.\n"
    "For each issue, include an Anchor line naming a file/path and either a line\n"
    "range or a diff hunk. Examples:\n"
    "- [B1] (HIGH) Missing auth check on admin handler\n"
    "  Anchor: src/auth/admin.ts (lines 45-52)\n"
    "  Recommendation: Add the missing authorization guard\n"
    "- [B2] (MEDIUM) Diff hunk still allows unsafe fallback\n"
    "  Anchor: diff hunk @@ -12,7 +12,9 @@\n"
    "  Recommendation: Remove the fallback branch\n"
    "(Write \"None\" if no blocking issues.)\n\n"
    "### Non-Blocking Issues\n"
    "Suggestions and improvements. Use [N1], [N2], etc.\n"
    "Include an Anchor line when the note refers to a specific file or hunk.\n"
    "(Write \"None\" if no non-blocking issues.)\n\n"
    "### Confidence\n"
    "State your confidence in this review: HIGH, MEDIUM, or LOW\n\n"
    "### Scope\n"
    "Which areas of the change does your review cover? (e.g., \"correctness\",\n"
    "\"security\", \"maintainability\", \"performance\", \"operability\")\n\n"
    "Your review MUST end with a verdict on the LAST non-empty line:\n"
    "- `VERDICT: APPROVED` if the change is ready to land as-is\n"
    "- `VERDICT: REVISE` if changes are needed before landing\n\n"
    "The verdict line must be EXACTLY one of these two strings, nothing else."
)

VERIFICATION_CONTRACT = (
    "## Verification Contract\n\n"
    "You are an independent verifier outside the panel.\n"
    "Use only the blocker ID, anchor data, the current artifact/context, and the blocker\n"
    "summary to decide whether the concern still holds.\n\n"
    "Respond with EXACTLY one of these on the first non-empty line:\n"
    "- `VERIFIED <BLOCKER_ID>` — the blocker is still valid\n"
    "- `INVALIDATED <BLOCKER_ID>` — the blocker is no longer valid\n\n"
    "Then add one concise rationale grounded in the artifact text."
)

MODE_ROLE_PACKS = {
    "plan": [
        "Skeptic",
        "Constraint Guardian",
        "User Advocate",
        "Integrator-minded reviewer",
    ],
    "spec": [
        "Skeptic",
        "Constraint Guardian",
        "User Advocate",
        "Integrator-minded reviewer",
    ],
    "code": [
        "Correctness reviewer",
        "Security reviewer",
        "Maintainability reviewer",
        "Performance/operability reviewer",
    ],
}


def _normalize_mode(mode):
    return "code" if mode == "code" else "plan"


def _review_contract_for_mode(mode):
    return REVIEW_CONTRACT_CODE if _normalize_mode(mode) == "code" else REVIEW_CONTRACT_PLAN


def _artifact_heading_for_mode(mode):
    return "Code Change" if _normalize_mode(mode) == "code" else "Plan"


def _artifact_lower_for_mode(mode):
    return _artifact_heading_for_mode(mode).lower()


def _role_for_mode(mode, reviewer_index):
    pack = MODE_ROLE_PACKS[_normalize_mode(mode)]
    return pack[(reviewer_index - 1) % len(pack)]


def load_review_md(directory=None):
    """Load REVIEW.md from the given directory (or cwd) if it exists.

    Returns the file contents as a string, or empty string if not found.
    """
    review_path = Path(directory or ".").resolve() / "REVIEW.md"
    if review_path.exists():
        try:
            return review_path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return ""


def _number_plan(plan_text):
    """Add line numbers to plan text for reviewer citation."""
    lines = plan_text.split("\n")
    width = len(str(len(lines)))
    return "\n".join(f"{i + 1:>{width}}\t{line}" for i, line in enumerate(lines))


def write_initial_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    review_contract,
    plan_text,
    rubric_text="",
    mode="plan",
    role_label=None,
    artifact_heading="Plan",
):
    """Write the initial review prompt for round 1."""
    rubric_section = ""
    if rubric_text:
        rubric_section = (
            f"\n\n## Project Review Guidelines\n\n{rubric_text}\n"
        )
    artifact_lower = artifact_heading.lower()
    role_line = (
        f"Your private role for this round is: {role_label}.\n"
        if role_label
        else ""
    )

    content = (
        f"{review_contract}{rubric_section}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"{role_line}"
        f"Other reviewers are also evaluating this {artifact_lower} independently. In subsequent\n"
        f"rounds you will see their feedback and can respond to it. For now, provide\n"
        f"your independent assessment.\n\n"
        f"## {artifact_heading}\n\n"
        f"{_number_plan(plan_text)}\n"
    )

    Path(prompt_file).write_text(content, encoding="utf-8")


def write_deliberation_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    round_num,
    review_contract,
    deliberation_text,
    changes_summary,
    plan_text,
    mode="plan",
    role_label=None,
    artifact_heading="Plan",
):
    """Write the deliberation prompt for a specific reviewer in rounds 2+."""
    artifact_lower = artifact_heading.lower()
    role_line = (
        f"Your private role for this round is: {role_label}.\n"
        if role_label
        else ""
    )
    content = (
        f"{review_contract}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"{role_line}"
        f"This is round {round_num}. Below are ALL reviews from the previous round,\n"
        f"including your own. Consider the other reviewers' points carefully.\n"
        f"You may agree, disagree, or refine their feedback. The host has revised\n"
        f"the {artifact_lower} based on the combined feedback.\n\n"
        f"## Reviews from Previous Round\n\n"
        f"{deliberation_text}\n\n"
        f"## Changes Since Last Round (by HOST)\n\n"
        f"{changes_summary}\n\n"
        f"## Updated {artifact_heading}\n\n"
        f"{_number_plan(plan_text)}\n"
    )

    Path(prompt_file).write_text(content, encoding="utf-8")


def write_cross_critique_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    round_num,
    review_contract,
    cross_critique_instructions,
    deliberation_or_compressed,
    ledger_summary,
    changes_summary,
    plan_text,
    mode="plan",
    role_label=None,
    artifact_heading="Plan",
):
    """Write round 2+ prompt with cross-critique instructions and issue ledger."""
    role_line = (
        f"Your private role for this round is: {role_label}.\n"
        if role_label
        else ""
    )
    content = (
        f"{review_contract}\n\n"
        f"{cross_critique_instructions}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"{role_line}"
        f"This is round {round_num}. All reviewer identities are anonymous.\n\n"
        f"## Reviews from Previous Round\n\n"
        f"{deliberation_or_compressed}\n\n"
        f"## Current Issue Ledger\n\n"
        f"{ledger_summary}\n\n"
        f"## Changes Since Last Round (by HOST)\n\n"
        f"{changes_summary}\n\n"
        f"## Updated {artifact_heading}\n\n"
        f"{_number_plan(plan_text)}\n"
    )

    Path(prompt_file).write_text(content, encoding="utf-8")


def format_ledger_summary(ledger, blind_mode=False):
    """Format the issue ledger as a markdown summary for reviewer prompts.

    When blind_mode=True, omits support/dispute counts to prevent conformity
    anchoring in later rounds.
    """
    open_issues = [i for i in ledger["issues"] if _issue_status(i) == "open"]
    if not open_issues:
        return "No open issues."

    lines = []
    for issue in open_issues:
        if blind_mode:
            lines.append(
                f"- **{issue['id']}** ({issue['severity']}): {issue['owner_summary']}"
            )
        else:
            lines.append(
                f"- **{issue['id']}** ({issue['severity']}): {issue['owner_summary']} "
                f"[support: {_issue_support_count(issue)}, disputes: {_issue_dispute_count(issue)}]"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tally & consensus (v2 — advisory verdicts + derived verdict)
# ---------------------------------------------------------------------------


def tally_verdicts(verdicts, threshold_name, original_panel_size=None,
                   active_panel_size=None):
    """Compute advisory tally from a list of (label, verdict, model, effort) tuples.

    In v2, this tally is ADVISORY — the authoritative verdict comes from
    derive_verdict() based on surviving blocking issues.

    Returns dict with:
      - approved: list of verdict tuples that approved
      - revise: list of verdict tuples that voted revise
      - failed: list of verdict tuples with no verdict
      - total: active reviewers
      - original_panel_size: original panel before failures
      - active_panel_size: surviving panel after failure policy
      - threshold_met: bool (advisory)
      - summary: human-readable tally string
    """
    approved = [v for v in verdicts if v[1] == "APPROVED"]
    revise = [v for v in verdicts if v[1] == "REVISE"]
    failed = [v for v in verdicts if v[1] is None]

    total = len(verdicts)
    n_approved = len(approved)
    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])
    threshold_met = threshold_fn(n_approved, total)

    orig = original_panel_size if original_panel_size is not None else total
    active = active_panel_size if active_panel_size is not None else total

    # Build threshold label
    if threshold_name == "unanimous":
        threshold_label = f"unanimous ({total}/{total})"
    elif threshold_name == "super":
        threshold_label = f"supermajority ({total - 1}/{total})"
    else:
        threshold_label = f"majority ({total // 2 + 1}/{total})"

    lines = [
        f"- APPROVED: {n_approved}/{total}"
        + (f" ({', '.join(v[0] for v in approved)})" if approved else ""),
        f"- REVISE: {len(revise)}/{total}"
        + (f" ({', '.join(v[0] for v in revise)})" if revise else ""),
    ]
    if failed:
        lines.append(
            f"- NO VERDICT: {len(failed)}/{total}"
            f" ({', '.join(v[0] for v in failed)})"
        )
    lines.append(f"- Threshold: {threshold_label}")
    if orig != active:
        lines.append(f"- Panel: {active} active of {orig} original")
    lines.append(
        f"- Advisory status: "
        f"{'CONSENSUS REACHED' if threshold_met else 'NOT MET'}"
        f" (advisory — derived verdict from issue ledger is authoritative)"
    )

    return {
        "approved": approved,
        "revise": revise,
        "failed": failed,
        "total": total,
        "original_panel_size": orig,
        "active_panel_size": active,
        "threshold_met": threshold_met,
        "summary": "\n".join(lines),
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(description="Quorum review orchestrator (v3)")
    p.add_argument(
        "--reviewers",
        required=True,
        help="Comma-separated reviewer specs (e.g., 'claude:sonnet,gemini:pro,codex')",
    )
    p.add_argument("--plan-file", required=True, help="Path to plan markdown file")
    p.add_argument("--quorum-id", required=True, help="Unique quorum session ID")
    p.add_argument("--round", type=int, required=True, help="Current round number (1-indexed)")
    p.add_argument(
        "--threshold",
        default="super",
        choices=list(THRESHOLDS.keys()),
        help="Consensus threshold (default: super)",
    )
    p.add_argument(
        "--effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Effort level for all reviewers",
    )
    p.add_argument("--timeout", type=int, default=600, help="Per-reviewer timeout in seconds")
    p.add_argument("--tmpdir", default=None, help="Temp directory (default: system temp)")
    p.add_argument(
        "--deliberation-file",
        default=None,
        help="Path to write compiled deliberation context",
    )
    p.add_argument(
        "--changes-summary",
        default=None,
        help="Path to file containing changes-since-last-round bullet list",
    )
    p.add_argument(
        "--sequential",
        action="store_true",
        help="Run reviewers sequentially instead of in parallel",
    )
    p.add_argument(
        "--tally-file",
        default=None,
        help="Path to write JSON tally results",
    )
    p.add_argument(
        "--ledger-file",
        default=None,
        help="Path to read/write the issue ledger JSON",
    )
    p.add_argument(
        "--on-failure",
        default="shrink-quorum",
        choices=["fail-closed", "fail-open", "shrink-quorum"],
        help="How to handle reviewer failures (default: shrink-quorum)",
    )
    p.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Max deliberation rounds (default: 3, max: 5)",
    )
    p.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip the verification stage for surviving blockers",
    )
    p.add_argument(
        "--mode",
        default="plan",
        choices=["plan", "spec", "code"],
        help="Review mode (default: plan; plan/spec share the same tribunal path)",
    )
    p.add_argument(
        "--verifier",
        default=None,
        help="Independent verifier provider:model (auto-selects outside panel when omitted)",
    )
    args = p.parse_args()
    if args.max_rounds > MAX_ROUNDS_LIMIT:
        p.error(f"--max-rounds cannot exceed {MAX_ROUNDS_LIMIT}")
    return args


def main():
    args = parse_args()

    # Parse and validate panel
    reviewer_specs = [s.strip() for s in args.reviewers.split(",") if s.strip()]
    panel = validate_panel(reviewer_specs)
    round_num = args.round
    original_panel_size = len(panel)

    # Resolve paths
    run_review_py = _resolve_run_review()
    tmpdir = args.tmpdir or tempfile.gettempdir()
    quorum_id = args.quorum_id
    plan_file = args.plan_file

    # Validate plan file exists
    if not Path(plan_file).exists():
        print(f"Error: --plan-file not found: {plan_file}", file=sys.stderr)
        sys.exit(1)

    # Read artifact text for prompt generation (plan/spec or code diff)
    artifact_text = Path(plan_file).read_text(encoding="utf-8")
    plan_text = artifact_text
    review_contract = _review_contract_for_mode(args.mode)
    artifact_heading = _artifact_heading_for_mode(args.mode)

    # Load REVIEW.md rubric if present
    rubric_text = load_review_md()

    # Load issue ledger (for rounds 2+)
    ledger_file = args.ledger_file or str(
        Path(tmpdir) / f"qr-{quorum_id}-ledger.json"
    )
    ledger = load_ledger(ledger_file) if round_num > 1 else _empty_ledger()

    # Read deliberation context from prior round (for rounds 2+)
    deliberation_text = ""
    changes_summary = "N/A (first round)"
    if round_num > 1:
        delib_file = args.deliberation_file
        if delib_file and Path(delib_file).exists():
            deliberation_text = Path(delib_file).read_text(encoding="utf-8")
        if args.changes_summary and Path(args.changes_summary).exists():
            changes_summary = Path(args.changes_summary).read_text(encoding="utf-8")

    # Generate per-reviewer prompts
    resume = round_num > 1
    for idx, (_provider, _model) in enumerate(panel, 1):
        prompt_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-prompt.md"
        role_label = _role_for_mode(args.mode, idx)
        if round_num == 1:
            write_initial_prompt(
                str(prompt_file), idx, len(panel), review_contract, plan_text,
                rubric_text=rubric_text,
                mode=args.mode,
                role_label=role_label,
                artifact_heading=artifact_heading,
            )
        elif round_num == 2:
            # Round 2: full anonymous prose + cross-critique instructions
            write_cross_critique_prompt(
                str(prompt_file),
                idx,
                len(panel),
                round_num,
                review_contract,
                CROSS_CRITIQUE_INSTRUCTIONS,
                deliberation_text,
                format_ledger_summary(ledger),
                changes_summary,
                plan_text,
                mode=args.mode,
                role_label=role_label,
                artifact_heading=artifact_heading,
            )
        else:
            # Rounds 3+: compressed context + cross-critique instructions
            # blind_mode=True strips support/dispute counts to prevent
            # conformity anchoring in later rounds
            compressed = compile_compressed_context(
                ledger, panel, quorum_id, tmpdir, round_num,
                blind_mode=True,
            )
            write_cross_critique_prompt(
                str(prompt_file),
                idx,
                len(panel),
                round_num,
                review_contract,
                CROSS_CRITIQUE_INSTRUCTIONS,
                compressed,
                format_ledger_summary(ledger, blind_mode=True),
                changes_summary,
                plan_text,
                mode=args.mode,
                role_label=role_label,
                artifact_heading=artifact_heading,
            )

    # Execute reviewers
    results = {}  # idx -> exit_code

    def _run_reviewer(idx, provider, model):
        prompt_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-prompt.md")
        output_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
        session_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json")
        events_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-events.jsonl")

        rc = run_single_reviewer(
            run_review_py,
            provider,
            model,
            plan_file,
            prompt_file,
            output_file,
            session_file,
            events_file,
            effort=args.effort,
            resume=resume,
            timeout=args.timeout,
        )
        return idx, rc

    if args.sequential:
        for idx, (provider, model) in enumerate(panel, 1):
            i, rc = _run_reviewer(idx, provider, model)
            results[i] = rc
            label = f"{provider}:{model or 'default'}"
            status = "OK" if rc == 0 else f"FAILED (exit {rc})"
            print(f"[Round {round_num}] {label}: {status}", file=sys.stderr)
    else:
        with ThreadPoolExecutor(max_workers=len(panel)) as pool:
            futures = {
                pool.submit(_run_reviewer, idx, provider, model): (idx, provider, model)
                for idx, (provider, model) in enumerate(panel, 1)
            }
            for future in as_completed(futures):
                idx, provider, model = futures[future]
                label = f"{provider}:{model or 'default'}"
                try:
                    i, rc = future.result()
                    results[i] = rc
                    status = "OK" if rc == 0 else f"FAILED (exit {rc})"
                    print(f"[Round {round_num}] {label}: {status}", file=sys.stderr)
                except Exception as e:
                    results[idx] = 1
                    print(f"[Round {round_num}] {label}: EXCEPTION: {e}", file=sys.stderr)

    # Apply failure policy
    failed_reviewers = [idx for idx, rc in results.items() if rc != 0]
    active_panel = panel
    active_panel_size = len(panel)

    if failed_reviewers:
        if args.on_failure == "fail-closed":
            print(
                f"FAIL-CLOSED: {len(failed_reviewers)} reviewer(s) failed. Aborting.",
                file=sys.stderr,
            )
            sys.exit(1)
        elif args.on_failure == "shrink-quorum":
            surviving = len(panel) - len(failed_reviewers)
            if surviving < MIN_QUORUM_SIZE:
                print(
                    f"FAIL-CLOSED: only {surviving} reviewer(s) survived, "
                    f"minimum is {MIN_QUORUM_SIZE}. Aborting.",
                    file=sys.stderr,
                )
                sys.exit(1)
            # Build surviving panel (preserve order)
            active_panel = [
                (provider, model)
                for idx, (provider, model) in enumerate(panel, 1)
                if idx not in failed_reviewers
            ]
            active_panel_size = len(active_panel)
            print(
                f"SHRINK-QUORUM: panel reduced from {original_panel_size} "
                f"to {active_panel_size}",
                file=sys.stderr,
            )
        # fail-open: continue with original panel size as threshold denominator

    # Compile deliberation (always anonymous) and tally
    deliberation_text, verdicts, reviewer_map = compile_deliberation(
        panel, quorum_id, tmpdir, round_num
    )

    # For shrink-quorum, filter verdicts to active panel only
    if args.on_failure == "shrink-quorum" and failed_reviewers:
        verdicts = [
            v for v in verdicts
            if reviewer_map[v[0]]["idx"] not in failed_reviewers
        ]

    tally = tally_verdicts(
        verdicts, args.threshold,
        original_panel_size=original_panel_size,
        active_panel_size=active_panel_size,
    )

    # Build/update issue ledger
    ledger = build_issue_ledger(panel, quorum_id, tmpdir, round_num, ledger)
    verdict_ledger = copy.deepcopy(ledger) if round_num == 1 else ledger
    merge_result = apply_merge_pipeline(ledger, quorum_id, tmpdir, round_num)
    save_ledger(ledger_file, ledger)

    # Verification stage: validate surviving blockers with an external verifier
    verifier_spec = None
    if not args.skip_verification:
        # Derive current verdict to find surviving blockers
        _v_verdict, _v_surviving, _v_dropped = derive_verdict(
            verdict_ledger, args.threshold, active_panel_size
        )
        if _v_surviving:
            verification_prompts = generate_verification_prompts(
                verdict_ledger, artifact_text, args.threshold, active_panel_size, mode=args.mode
            )
            if verification_prompts:
                v_provider, v_model = _resolve_verifier_spec(active_panel, args.verifier)
                verifier_spec = {"provider": v_provider, "model": v_model}
                for vp in verification_prompts:
                    v_prompt_file = str(
                        Path(tmpdir) / f"qr-{quorum_id}-verify-{vp['issue_id']}-prompt.md"
                    )
                    v_output_file = str(
                        Path(tmpdir) / f"qr-{quorum_id}-verify-{vp['issue_id']}-review.md"
                    )
                    v_session_file = str(
                        Path(tmpdir) / f"qr-{quorum_id}-verify-{vp['issue_id']}-session.json"
                    )
                    v_events_file = str(
                        Path(tmpdir) / f"qr-{quorum_id}-verify-{vp['issue_id']}-events.jsonl"
                    )
                    # Write verification prompt
                    Path(v_prompt_file).write_text(vp["prompt"], encoding="utf-8")
                    # Run verifier
                    v_rc = run_single_reviewer(
                        run_review_py,
                        v_provider,
                        v_model,
                        plan_file,
                        v_prompt_file,
                        v_output_file,
                        v_session_file,
                        v_events_file,
                        effort=args.effort,
                        resume=False,
                        timeout=args.timeout,
                        verification_mode=True,
                    )
                    if v_rc == 0:
                        v_results = parse_verification_response(v_output_file)
                        for issue_id, status in v_results.items():
                            for issue in ledger["issues"]:
                                if issue["id"] != issue_id:
                                    continue
                                issue["verification"]["status"] = status.lower()
                                issue["verification"]["verified_by"] = {
                                    "provider": v_provider,
                                    "model": v_model,
                                }
                                issue["verification"]["verification_rationale"] = read_review(v_output_file)
                                if status == "INVALIDATED":
                                    issue["status"] = "invalidated_by_verifier"
                                    issue.setdefault("adjudication", {})["status"] = "invalidated_by_verifier"
                                break
                    else:
                        print(
                            f"[Verification] {vp['issue_id']}: verifier failed (exit {v_rc})",
                            file=sys.stderr,
                        )
                # Re-save ledger after verification updates
                save_ledger(ledger_file, ledger)

    if verdict_ledger is not ledger:
        _sync_verification_state(verdict_ledger, ledger)

    # Early exit signal for host agent
    early_exit, early_exit_reason = should_exit_early(
        verdict_ledger, args.threshold, active_panel_size
    )

    # Check parse status — detect all-unstructured reviews
    parse_statuses = []
    for idx, (_provider, _model) in enumerate(panel, 1):
        review_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
        parsed = parse_structured_review(review_file)
        parse_statuses.append(parsed["structured"])
    all_unstructured = not any(parse_statuses)
    unstructured_count = sum(1 for s in parse_statuses if not s)

    # Derive verdict from surviving blocking issues
    derived_verdict, surviving_issues, dropped_issues = derive_verdict(
        verdict_ledger, args.threshold, active_panel_size
    )
    issue_consensus = format_issue_consensus(
        verdict_ledger, args.threshold, active_panel_size
    )

    # Write deliberation file for next round
    delib_out = args.deliberation_file or str(
        Path(tmpdir) / f"qr-{quorum_id}-deliberation.md"
    )
    Path(delib_out).write_text(deliberation_text, encoding="utf-8")

    # Write tally as JSON
    tally_data = {
        "round": round_num,
        "threshold": args.threshold,
        "original_panel_size": original_panel_size,
        "active_panel_size": active_panel_size,
        "on_failure": args.on_failure,
        "mode": args.mode,
        "advisory_threshold_met": tally["threshold_met"],
        "derived_verdict": derived_verdict,
        "surviving_blockers": len(surviving_issues),
        "dropped_blockers": len(dropped_issues),
        "approved_count": len(tally["approved"]),
        "revise_count": len(tally["revise"]),
        "failed_count": len(tally["failed"]),
        "total": tally["total"],
        "all_unstructured": all_unstructured,
        "unstructured_count": unstructured_count,
        "reviewers": [
            {
                "label": v[0],
                "verdict": v[1],
                "model": v[2],
                "effort": v[3],
            }
            for v in verdicts
        ],
        "reviewer_map": {
            label: info for label, info in reviewer_map.items()
        },
        "exit_codes": results,
        "early_exit": early_exit,
        "early_exit_reason": early_exit_reason,
        "merge_log_path": merge_result["log_path"],
        "merged_count": len(merge_result["merged"]),
        "merge_candidate_count": len(merge_result["candidates"]),
        "verifier": verifier_spec,
    }
    tally_file = args.tally_file or str(Path(tmpdir) / f"qr-{quorum_id}-tally.json")
    Path(tally_file).write_text(json.dumps(tally_data, indent=2), encoding="utf-8")

    # Print summary to stdout for host agent consumption
    print(f"\n## Quorum Review — Round {round_num} Tally\n")
    print(tally["summary"])
    if unstructured_count > 0:
        print(
            f"\nWARNING: {unstructured_count}/{len(panel)} reviewer(s) produced "
            "unstructured output (parse_status: unstructured)"
        )
    print(f"\n{issue_consensus}")
    if early_exit:
        print(f"\nEARLY EXIT SIGNAL: {early_exit_reason}")
    print(f"\nDeliberation context written to: {delib_out}")
    print(f"Tally written to: {tally_file}")
    print(f"Issue ledger written to: {ledger_file}")

    # Exit codes: 0=APPROVED, 2=REVISE, 3=INDETERMINATE
    if all_unstructured:
        print("\nINDETERMINATE: all reviews were unstructured")
        sys.exit(EXIT_INDETERMINATE)
    elif derived_verdict == "APPROVED":
        print("\nDERIVED CONSENSUS: APPROVED")
        sys.exit(EXIT_APPROVED)
    else:
        print(f"\nDERIVED CONSENSUS: REVISE ({len(surviving_issues)} blocker(s) survive)")
        sys.exit(EXIT_REVISE)


if __name__ == "__main__":
    main()
