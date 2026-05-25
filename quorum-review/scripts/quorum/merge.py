"""quorum.merge — issue-pair classification and deterministic merge pipeline.

Classifies every open issue pair as ``EQUIVALENT`` / ``RELATED_DISTINCT``
/ ``CONFLICT`` / ``UNCERTAIN`` (the four ``MERGE_CLASSIFICATIONS``), then
applies a union-find merge for ``EQUIVALENT`` pairs and emits per-decision
records to a merge-log JSONL alongside the ledger. Depends on
``quorum.parsing`` (text helpers) and ``quorum.ledger`` (issue accessors
and alias-sync). The reverse direction is broken via a lazy import inside
``ledger._migrate_ledger`` for ``_migrate_merge``.
"""

import copy
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from quorum.parsing import (
    _STOPWORDS,
    _NEGATION_WORDS,
    _normalize_text,
    _summary_tokens,
)
from quorum.ledger import (
    _as_list,
    _issue_adjudication,
    _issue_is_invalidated,
    _issue_severity,
    _issue_status,
    _issue_summary,
    _sync_issue_aliases,
    _unique_preserve_order,
    _refresh_round_snapshot,
)


MERGE_CLASSIFICATIONS = {"EQUIVALENT", "RELATED_DISTINCT", "CONFLICT", "UNCERTAIN"}

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


def _issue_sort_key(issue):
    match = re.search(r"-(\d+)$", issue.get("id", ""))
    return (0 if _issue_severity(issue) == "blocking" else 1, int(match.group(1)) if match else 10**9, issue.get("id", ""))


def _issue_is_mergeable(issue):
    return _issue_status(issue) == "open" and not _issue_is_invalidated(issue)


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
