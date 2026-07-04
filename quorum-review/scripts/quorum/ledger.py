"""quorum.ledger — issue-ledger CRUD, canonical IDs, schema migration.

Owns the on-disk and in-memory shape of the issue ledger: per-issue
identity/claim/adjudication/verification/relations sub-dicts, the
``_sync_issue_aliases`` invariant maintainer, ID assignment helpers, and
the v2→v3 migration path. Depends only on ``quorum.parsing`` (for anchor
normalization and text helpers). Calls ``quorum.merge._migrate_merge``
lazily inside ``_migrate_ledger`` to avoid a circular import with merge.
"""

import copy
import json
import re
from pathlib import Path

from quorum.parsing import _normalize_anchor

LEDGER_VERSION = 3
LEDGER_SCHEMA_VERSION = 3


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
        relations.get("proposed_by") or adjudication.get("proposed_by", issue.get("proposed_by"))
    )
    endorsed = _as_list(
        relations.get("endorsed_by") or adjudication.get("endorsed_by", issue.get("endorsed_by"))
    )
    refined = _as_list(
        relations.get("refined_by") or adjudication.get("refined_by", issue.get("refined_by"))
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
        relations.get("disputed_by") or adjudication.get("disputed_by", issue.get("disputed_by"))
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
    relations["related_distinct"] = _unique_preserve_order(
        _as_list(relations.get("related_distinct"))
    )
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
            "status": "invalidated"
            if migrated.get("status") == "invalidated_by_verifier"
            else "pending",
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


def _migrate_ledger(ledger):
    # Lazy import to avoid a top-level cycle: merge imports ledger helpers,
    # and ledger needs _migrate_merge from merge during ledger normalization.
    from quorum.merge import _migrate_merge

    if not isinstance(ledger, dict):
        return _empty_ledger()

    migrated = _empty_ledger()
    migrated.update(
        {k: copy.deepcopy(v) for k, v in ledger.items() if k not in {"issues", "merges", "rounds"}}
    )
    migrated["schema_version"] = LEDGER_SCHEMA_VERSION
    migrated["version"] = LEDGER_SCHEMA_VERSION
    migrated["issues"] = []
    for issue in ledger.get("issues", []):
        migrated_issue = _migrate_issue(issue)
        if migrated_issue:
            migrated["issues"].append(migrated_issue)
    migrated["merges"] = [
        merge for merge in (_migrate_merge(entry) for entry in ledger.get("merges", [])) if merge
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


def _issue_is_invalidated(issue):
    verification = _issue_verification(issue)
    return (
        _issue_status(issue) == "invalidated_by_verifier"
        or verification.get("status") == "invalidated"
    )


def _refresh_issue(issue):
    _sync_issue_aliases(issue)
    return issue


def _refresh_round_snapshot(ledger, round_num):
    key = str(round_num)
    round_info = ledger.setdefault("rounds", {}).setdefault(key, {})
    round_info.setdefault("reviewer_count", 0)
    round_info["blocking_open"] = sum(
        1
        for issue in ledger.get("issues", [])
        if _issue_severity(issue) == "blocking" and _issue_status(issue) == "open"
    )
    round_info["nb_open"] = sum(
        1
        for issue in ledger.get("issues", [])
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
