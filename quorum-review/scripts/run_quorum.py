#!/usr/bin/env python3
"""
run_quorum.py — Orchestrator for multi-provider quorum review (v2.4).

Launches multiple reviewer instances (via run_review.py),
collects their verdicts, compiles the deliberation context for subsequent
rounds, and reports consensus status.

v2.4 changes:
  - Standalone: run_review.py and provider references bundled in quorum-review
  - Section-scan: new issues in Round 2+ standard sections (without [B-NEW]/[N-NEW])
    are now detected and registered in the ledger (fixes issue leakage bug)

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
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
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
# Structured review parsing (v2)
# ---------------------------------------------------------------------------

_RE_BLOCKING = re.compile(r"^\s*-\s*\*{0,2}\[B(\d+)\]\*{0,2}\s*(.+)", re.MULTILINE)
_RE_BLOCKING_WITH_CONF = re.compile(
    r"^\s*-\s*\*{0,2}\[B(\d+)\]\s*\((HIGH|MEDIUM|LOW)\)\*{0,2}\s*(.+)", re.MULTILINE | re.IGNORECASE
)
_RE_NON_BLOCKING = re.compile(r"^\s*-\s*\*{0,2}\[N(\d+)\]\*{0,2}\s*(.+)", re.MULTILINE)
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
    pattern = re.compile(
        r"(?:^|\n)###\s+" + re.escape(header) + r"\s*\n",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return text  # fallback: search entire text

    start = match.end()
    # Find the next ### header (but not #### sub-headers)
    next_header = re.search(r"\n###\s+(?!#)", text[start:])
    if next_header:
        return text[start : start + next_header.start()]
    return text[start:]


def parse_structured_review(review_file):
    """Parse structured review output into issue records.

    Returns dict with:
      - blocking: list of {"id": "B1", "text": "..."}
      - non_blocking: list of {"id": "N1", "text": "..."}
      - confidence: "HIGH"|"MEDIUM"|"LOW"|None
      - scope: list of strings
      - verdict: "APPROVED"|"REVISE"|None
      - raw_text: full review text
      - structured: bool (True if any structured sections found)
    """
    text = read_review(review_file)
    verdict = parse_verdict(review_file)

    # Extract section text to avoid matching issues from Reasoning section
    blocking_section = _extract_section(text, "Blocking Issues")
    nb_section = _extract_section(text, "Non-Blocking Issues")

    # Parse blocking issues — try per-issue confidence first
    conf_matches = {
        m.group(1): (m.group(2).upper(), m.group(3).strip())
        for m in _RE_BLOCKING_WITH_CONF.finditer(blocking_section)
    }
    blocking = []
    for m in _RE_BLOCKING.finditer(blocking_section):
        bid = m.group(1)
        if bid in conf_matches:
            issue_conf, issue_text = conf_matches[bid]
            blocking.append({"id": f"B{bid}", "text": issue_text, "confidence": issue_conf})
        else:
            blocking.append({"id": f"B{bid}", "text": m.group(2).strip(), "confidence": None})

    non_blocking = [
        {"id": f"N{m.group(1)}", "text": m.group(2).strip()}
        for m in _RE_NON_BLOCKING.finditer(nb_section)
    ]

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
# Verification stage (v2.1)
# ---------------------------------------------------------------------------


def generate_verification_prompts(ledger, plan_text, threshold_name, total):
    """Generate targeted verification prompts for surviving blockers.

    Returns list of dicts with:
      - issue_id: canonical ID
      - prompt: verification prompt text
    """
    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])
    prompts = []

    for issue in ledger["issues"]:
        if issue["severity"] != "blocking" or issue["status"] != "open":
            continue
        if not threshold_fn(issue["support_count"], total):
            continue

        prompt = (
            "## Verification Request\n\n"
            f"The following blocking issue was raised and survived cross-critique "
            f"with {issue['support_count']}/{total} endorsements:\n\n"
            f"**{issue['id']}**: {issue['owner_summary']}\n\n"
            "Given the current plan below, is this concern still valid?\n\n"
            "Respond with EXACTLY one of:\n"
            f"- `VERIFIED {issue['id']}` — the issue is still valid\n"
            f"- `INVALIDATED {issue['id']}` — the issue has been addressed "
            "or is not applicable\n\n"
            "Include a brief rationale after your response.\n\n"
            f"## Plan\n\n{plan_text}\n"
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
# Issue ledger (v2)
# ---------------------------------------------------------------------------


def _empty_ledger():
    """Create an empty issue ledger."""
    return {
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
        # Ensure all required keys exist
        for key in ("next_blk_id", "next_nb_id", "issues", "merges", "rounds"):
            if key not in data:
                data[key] = _empty_ledger()[key]
        return data
    except (json.JSONDecodeError, OSError):
        return _empty_ledger()


def save_ledger(ledger_file, ledger):
    """Save issue ledger to JSON file."""
    Path(ledger_file).write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def build_issue_ledger(panel, quorum_id, tmpdir, round_num, prev_ledger=None):
    """Build/update issue ledger from structured reviews.

    Round 1: Extract issues from each reviewer, assign canonical IDs.
    Rounds 2+: Parse cross-critique responses, update agreement counts,
               add new issues from [B-NEW]/[N-NEW] tags.

    Returns updated ledger dict.
    """
    ledger = prev_ledger if prev_ledger else _empty_ledger()

    if round_num == 1:
        # Round 1: extract issues from structured reviews
        blocking_count = 0
        nb_count = 0
        approved_count = 0

        for idx, (_provider, _model) in enumerate(panel, 1):
            review_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
            parsed = parse_structured_review(review_file)

            for issue in parsed["blocking"]:
                canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                ledger["next_blk_id"] += 1
                ledger["issues"].append({
                    "id": canonical_id,
                    "source_reviewer": idx,
                    "source_label": issue["id"],
                    "round_introduced": round_num,
                    "severity": "blocking",
                    "text": issue["text"],
                    "status": "open",
                    "resolved_round": None,
                    "merged_from": [],
                    "proposed_by": idx,
                    "endorsed_by": [],
                    "refined_by": [],
                    "disputed_by": [],
                    "support_count": 1,
                    "dispute_count": 0,
                    "owner_summary": issue["text"],
                    "confidence": issue.get("confidence"),
                })
                blocking_count += 1

            for issue in parsed["non_blocking"]:
                canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                ledger["next_nb_id"] += 1
                ledger["issues"].append({
                    "id": canonical_id,
                    "source_reviewer": idx,
                    "source_label": issue["id"],
                    "round_introduced": round_num,
                    "severity": "non_blocking",
                    "text": issue["text"],
                    "status": "open",
                    "resolved_round": None,
                    "merged_from": [],
                    "proposed_by": idx,
                    "endorsed_by": [],
                    "refined_by": [],
                    "disputed_by": [],
                    "support_count": 1,
                    "dispute_count": 0,
                    "owner_summary": issue["text"],
                })
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
        # Rounds 2+: parse cross-critique responses
        approved_count = 0
        issue_map = {issue["id"]: issue for issue in ledger["issues"]}

        for idx, (_provider, _model) in enumerate(panel, 1):
            review_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
            critique = parse_cross_critique(review_file)
            parsed = parse_structured_review(review_file)

            # Process agrees (endorsements)
            for issue_id in critique["agrees"]:
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx != issue.get("proposed_by") and idx not in issue["endorsed_by"]:
                        issue["endorsed_by"].append(idx)
                        issue["support_count"] = (
                            1 + len(issue["endorsed_by"]) + len(issue["refined_by"])
                        )

            # Process disagrees (disputes)
            for entry in critique["disagrees"]:
                issue_id = entry["id"]
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx not in issue["disputed_by"]:
                        issue["disputed_by"].append(idx)
                        issue["dispute_count"] = len(issue["disputed_by"])

            # Process refines (counts as support with modified text)
            for entry in critique["refines"]:
                issue_id = entry["id"]
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx != issue.get("proposed_by") and idx not in issue["refined_by"]:
                        issue["refined_by"].append(idx)
                        issue["support_count"] = (
                            1 + len(issue["endorsed_by"]) + len(issue["refined_by"])
                        )

            # Add new blocking issues
            for text in critique["new_blocking"]:
                canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                ledger["next_blk_id"] += 1
                new_issue = {
                    "id": canonical_id,
                    "source_reviewer": idx,
                    "source_label": "B-NEW",
                    "round_introduced": round_num,
                    "severity": "blocking",
                    "text": text,
                    "status": "open",
                    "resolved_round": None,
                    "merged_from": [],
                    "proposed_by": idx,
                    "endorsed_by": [],
                    "refined_by": [],
                    "disputed_by": [],
                    "support_count": 1,
                    "dispute_count": 0,
                    "owner_summary": text,
                }
                ledger["issues"].append(new_issue)
                issue_map[canonical_id] = new_issue

            # Add new non-blocking issues
            for text in critique["new_non_blocking"]:
                canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                ledger["next_nb_id"] += 1
                new_issue = {
                    "id": canonical_id,
                    "source_reviewer": idx,
                    "source_label": "N-NEW",
                    "round_introduced": round_num,
                    "severity": "non_blocking",
                    "text": text,
                    "status": "open",
                    "resolved_round": None,
                    "merged_from": [],
                    "proposed_by": idx,
                    "endorsed_by": [],
                    "refined_by": [],
                    "disputed_by": [],
                    "support_count": 1,
                    "dispute_count": 0,
                    "owner_summary": text,
                }
                ledger["issues"].append(new_issue)
                issue_map[canonical_id] = new_issue

            # Section-scan: catch new issues in standard review sections
            # that were NOT tagged with [B-NEW]/[N-NEW].  Exact-string
            # dedup prevents double-counting when a reviewer uses both
            # a tag and a standard section for the same issue.
            existing_texts = {
                i["owner_summary"].strip().lower()
                for i in ledger["issues"]
                if i.get("owner_summary")
            }

            for section_issue in parsed["blocking"]:
                text = section_issue["text"].strip()
                if text.lower() not in existing_texts:
                    canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                    ledger["next_blk_id"] += 1
                    new_issue = {
                        "id": canonical_id,
                        "source_reviewer": idx,
                        "source_label": "section-scan",
                        "round_introduced": round_num,
                        "severity": "blocking",
                        "text": text,
                        "status": "open",
                        "resolved_round": None,
                        "merged_from": [],
                        "proposed_by": idx,
                        "endorsed_by": [],
                        "refined_by": [],
                        "disputed_by": [],
                        "support_count": 1,
                        "dispute_count": 0,
                        "owner_summary": text,
                    }
                    ledger["issues"].append(new_issue)
                    issue_map[canonical_id] = new_issue
                    existing_texts.add(text.lower())

            for section_issue in parsed["non_blocking"]:
                text = section_issue["text"].strip()
                if text.lower() not in existing_texts:
                    canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                    ledger["next_nb_id"] += 1
                    new_issue = {
                        "id": canonical_id,
                        "source_reviewer": idx,
                        "source_label": "section-scan",
                        "round_introduced": round_num,
                        "severity": "non_blocking",
                        "text": text,
                        "status": "open",
                        "resolved_round": None,
                        "merged_from": [],
                        "proposed_by": idx,
                        "endorsed_by": [],
                        "refined_by": [],
                        "disputed_by": [],
                        "support_count": 1,
                        "dispute_count": 0,
                        "owner_summary": text,
                    }
                    ledger["issues"].append(new_issue)
                    issue_map[canonical_id] = new_issue
                    existing_texts.add(text.lower())

            if parsed["verdict"] == "APPROVED":
                approved_count += 1

        # Update round stats
        open_blocking = sum(
            1 for i in ledger["issues"]
            if i["severity"] == "blocking" and i["status"] == "open"
        )
        open_nb = sum(
            1 for i in ledger["issues"]
            if i["severity"] == "non_blocking" and i["status"] == "open"
        )
        ledger["rounds"][str(round_num)] = {
            "reviewer_count": len(panel),
            "blocking_open": open_blocking,
            "nb_open": open_nb,
            "approved_count": approved_count,
        }

    return ledger


# ---------------------------------------------------------------------------
# Derived verdict (v2)
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
        if i["severity"] == "blocking" and i["status"] == "open"
    ]

    surviving = []
    dropped = []

    for issue in open_blockers:
        # An issue "survives" if its support count meets the threshold
        # We invert the threshold: instead of "N approved out of total",
        # we check "support_count supporters out of total"
        if threshold_fn(issue["support_count"], total_reviewers):
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
                f"- {issue['id']} \"{issue['owner_summary']}\": "
                f"support {issue['support_count']}/{total_reviewers} "
                f"— SURVIVES"
            )
    if dropped:
        for issue in dropped:
            lines.append(
                f"- {issue['id']} \"{issue['owner_summary']}\": "
                f"support {issue['support_count']}/{total_reviewers} "
                f"— DROPPED"
            )

    # Non-blocking issues (informational)
    open_nb = [
        i for i in ledger["issues"]
        if i["severity"] == "non_blocking" and i["status"] == "open"
    ]
    for issue in open_nb:
        lines.append(
            f"- {issue['id']} \"{issue['owner_summary']}\": "
            f"support {issue['support_count']}/{total_reviewers} "
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
    return issue is not None and issue["support_count"] >= total


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
        if i["severity"] == "blocking" and i["status"] == "open"
    ]

    if not open_blockers:
        return True, "no open blockers remain"

    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])
    surviving = [i for i in open_blockers if threshold_fn(i["support_count"], total_reviewers)]

    if not surviving:
        return True, "no blockers meet threshold — verdict would be APPROVED"

    all_at_max = all(i["support_count"] >= total_reviewers for i in surviving)
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

    open_issues = [i for i in ledger["issues"] if i["status"] == "open"]
    if open_issues:
        if blind_mode:
            lines.append("| ID | Severity | Description |")
            lines.append("|-----|----------|-------------|")
            for issue in open_issues:
                lines.append(
                    f"| {issue['id']} | {issue['severity']} | "
                    f"{issue['owner_summary'][:60]} |"
                )
        else:
            lines.append("| ID | Severity | Description | Support | Disputes |")
            lines.append("|-----|----------|-------------|---------|----------|")
            for issue in open_issues:
                lines.append(
                    f"| {issue['id']} | {issue['severity']} | "
                    f"{issue['owner_summary'][:60]} | "
                    f"{issue['support_count']} | {issue['dispute_count']} |"
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
# Prompt generation (v2)
# ---------------------------------------------------------------------------

REVIEW_CONTRACT_V2 = (
    "## Review Contract\n\n"
    "You are reviewing a plan as part of a multi-reviewer quorum panel.\n\n"
    "Structure your review using EXACTLY these sections:\n\n"
    "### Reasoning\n"
    "Write your complete analysis of the plan here. Consider architecture,\n"
    "security, testing, performance, and any other relevant areas. This\n"
    "section MUST come before your issue lists.\n\n"
    "### Blocking Issues\n"
    "Issues that MUST be resolved before execution. Use [B1], [B2], etc.\n"
    "Optionally include per-issue confidence: (HIGH), (MEDIUM), or (LOW).\n"
    "- [B1] (HIGH) Description of blocking issue...\n"
    "- [B2] (MEDIUM) Description of blocking issue...\n"
    "(Write \"None\" if no blocking issues.)\n\n"
    "### Non-Blocking Issues\n"
    "Suggestions and improvements. Use [N1], [N2], etc.\n"
    "- [N1] Description...\n"
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
    "- [B2] (MEDIUM) New: No rate limiting on public API\n\n"
    "### Non-Blocking Issues\n"
    "None\n\n"
    "### Confidence\n"
    "HIGH\n\n"
    "### Scope\n"
    "security, API design\n\n"
    "VERDICT: REVISE\n"
    "```"
)


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


def write_initial_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    review_contract,
    plan_text,
    rubric_text="",
):
    """Write the initial review prompt for round 1."""
    rubric_section = ""
    if rubric_text:
        rubric_section = (
            f"\n\n## Project Review Guidelines\n\n{rubric_text}\n"
        )

    content = (
        f"{review_contract}{rubric_section}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"Other reviewers are also evaluating this plan independently. In subsequent\n"
        f"rounds you will see their feedback and can respond to it. For now, provide\n"
        f"your independent assessment.\n\n"
        f"## Plan\n\n"
        f"{plan_text}\n"
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
):
    """Write the deliberation prompt for a specific reviewer in rounds 2+."""
    content = (
        f"{review_contract}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"This is round {round_num}. Below are ALL reviews from the previous round,\n"
        f"including your own. Consider the other reviewers' points carefully.\n"
        f"You may agree, disagree, or refine their feedback. The host has revised\n"
        f"the plan based on the combined feedback.\n\n"
        f"## Reviews from Previous Round\n\n"
        f"{deliberation_text}\n\n"
        f"## Changes Since Last Round (by HOST)\n\n"
        f"{changes_summary}\n\n"
        f"## Updated Plan\n\n"
        f"{plan_text}\n"
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
):
    """Write round 2+ prompt with cross-critique instructions and issue ledger."""
    content = (
        f"{review_contract}\n\n"
        f"{cross_critique_instructions}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"This is round {round_num}. All reviewer identities are anonymous.\n\n"
        f"## Reviews from Previous Round\n\n"
        f"{deliberation_or_compressed}\n\n"
        f"## Current Issue Ledger\n\n"
        f"{ledger_summary}\n\n"
        f"## Changes Since Last Round (by HOST)\n\n"
        f"{changes_summary}\n\n"
        f"## Updated Plan\n\n"
        f"{plan_text}\n"
    )

    Path(prompt_file).write_text(content, encoding="utf-8")


def format_ledger_summary(ledger, blind_mode=False):
    """Format the issue ledger as a markdown summary for reviewer prompts.

    When blind_mode=True, omits support/dispute counts to prevent conformity
    anchoring in later rounds.
    """
    open_issues = [i for i in ledger["issues"] if i["status"] == "open"]
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
                f"[support: {issue['support_count']}, disputes: {issue['dispute_count']}]"
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
    p = argparse.ArgumentParser(description="Quorum review orchestrator (v2.4)")
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

    # Read plan text for prompt generation
    plan_text = Path(plan_file).read_text(encoding="utf-8")

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
        if round_num == 1:
            write_initial_prompt(
                str(prompt_file), idx, len(panel), REVIEW_CONTRACT_V2, plan_text,
                rubric_text=rubric_text,
            )
        elif round_num == 2:
            # Round 2: full anonymous prose + cross-critique instructions
            write_cross_critique_prompt(
                str(prompt_file),
                idx,
                len(panel),
                round_num,
                REVIEW_CONTRACT_V2,
                CROSS_CRITIQUE_INSTRUCTIONS,
                deliberation_text,
                format_ledger_summary(ledger),
                changes_summary,
                plan_text,
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
                REVIEW_CONTRACT_V2,
                CROSS_CRITIQUE_INSTRUCTIONS,
                compressed,
                format_ledger_summary(ledger, blind_mode=True),
                changes_summary,
                plan_text,
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
    save_ledger(ledger_file, ledger)

    # Verification stage: validate surviving blockers with a single reviewer
    if not args.skip_verification:
        # Derive current verdict to find surviving blockers
        _v_verdict, _v_surviving, _v_dropped = derive_verdict(
            ledger, args.threshold, active_panel_size
        )
        if _v_surviving:
            verification_prompts = generate_verification_prompts(
                ledger, plan_text, args.threshold, active_panel_size
            )
            # Filter out unanimously-endorsed blockers (high-probability true positives)
            verification_prompts = [
                p for p in verification_prompts
                if not _is_unanimous(ledger, p["issue_id"], active_panel_size)
            ]
            if verification_prompts:
                # Use the first active panel reviewer as verifier
                v_provider, v_model = active_panel[0]
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
                    )
                    if v_rc == 0:
                        v_results = parse_verification_response(v_output_file)
                        for issue_id, status in v_results.items():
                            if status == "INVALIDATED":
                                for issue in ledger["issues"]:
                                    if issue["id"] == issue_id:
                                        issue["status"] = "invalidated_by_verifier"
                                        break
                    else:
                        print(
                            f"[Verification] {vp['issue_id']}: verifier failed (exit {v_rc})",
                            file=sys.stderr,
                        )
                # Re-save ledger after verification updates
                save_ledger(ledger_file, ledger)

    # Early exit signal for host agent
    early_exit, early_exit_reason = should_exit_early(
        ledger, args.threshold, active_panel_size
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
        ledger, args.threshold, active_panel_size
    )
    issue_consensus = format_issue_consensus(
        ledger, args.threshold, active_panel_size
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
