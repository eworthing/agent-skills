"""quorum.verification — external-verifier dispatch and response parsing.

Builds the per-blocker verification prompts (panel-state redacted, anchor
+ blocker-summary + artifact text only), parses ``VERIFIED <BLK-id>`` /
``INVALIDATED <BLK-id>`` first-line responses, and syncs verifier outcomes
back into a ledger snapshot. Depends on ``quorum.parsing`` (for
``read_review``), ``quorum.ledger`` (for issue accessors and alias-sync),
and ``quorum.prompts`` (for the ``VERIFICATION_CONTRACT`` text and the
anchor-formatter).
"""

import copy
import re

from quorum.cli import THRESHOLDS
from quorum.ledger import (
    _issue_is_invalidated,
    _issue_severity,
    _issue_status,
    _issue_summary,
    _issue_support_count,
    _sync_issue_aliases,
)
from quorum.parsing import read_review
from quorum.prompts import (
    VERIFICATION_CONTRACT,
    _artifact_heading_for_mode,
    _format_anchor_for_prompt,
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
        if (
            _issue_severity(issue) != "blocking"
            or _issue_status(issue) != "open"
            or _issue_is_invalidated(issue)
        ):
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


_RE_VERIFIED = re.compile(r"^\s*(?:`)?VERIFIED\s+(BLK-\d+)(?:`)?", re.MULTILINE)
_RE_INVALIDATED = re.compile(r"^\s*(?:`)?INVALIDATED\s+(BLK-\d+)(?:`)?", re.MULTILINE)


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
