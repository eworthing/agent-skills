"""G52 — site-pass ledger completeness (report-only). SITE-PASS plan W1, 2026-09-03.

Scoped runs (``discovery.scope`` non-null, ``site_pass`` epoch+) must carry a per-file
ledger ``site_pass.files[]`` covering the script-emitted roster
``discovery.site_pass_roster.paths`` exactly, each entry partitioning the eight
site-pass questions (references/site-pass.md) into ``clean`` / ``finding`` (with the
finding ids it produced, every one present in ``findings``) / ``not_applicable``
(with a reason). Unscoped runs must carry ``site_pass: null``. Everything checked is
artifact-internal, so the gate is phase-stable (the Tier-3 hook may run it after
Step 3 changed the tree).

Why REPORT_ONLY: the ledger is the treatment arm of a measurement that has not run
yet. Promotion bar (report-only is permanent by default unless the bar is written
down -- the G17 lesson): graduate to an Issue only when the SITE-PASS plan's W2 bar
is met -- treat real-site hits >= 10/29 on >= 2 of 3 scored flash reps against
``evals/ocr-corpus/benchhype-settings-2026-09.json``, zero rejected-site hits outside
the W0 exclusion set [65], and the four rubric findings retained -- recorded in
docs/contest-refactor-run-log.md. On a missed bar this module is removed with the
epoch (plan § negative disposition).
"""

from __future__ import annotations

import hashlib

import _ruleset_epoch
from _artifact_core import Issue

REPORT_ONLY = True
QUESTION_IDS = frozenset(f"Q{i}" for i in range(1, 9))
STATUSES = frozenset({"clean", "finding", "not_applicable"})


def roster_digest(paths: list[str]) -> str:
    return hashlib.sha256("\n".join(paths).encode("utf-8")).hexdigest()


def site_pass_diagnostics(current_review: dict) -> list[str]:
    """The diagnostics G52 would raise as Issues once promoted. Pure; no printing."""
    discovery = current_review.get("discovery")
    scope = discovery.get("scope") if isinstance(discovery, dict) else None
    site_pass = current_review.get("site_pass")
    if scope is None:
        if site_pass is not None:
            return ["site_pass must be null on an unscoped run (discovery.scope is null)"]
        return []
    fired: list[str] = []
    roster = discovery.get("site_pass_roster")
    paths = roster.get("paths") if isinstance(roster, dict) else None
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        return [
            "scoped run: discovery.site_pass_roster must be the script-emitted "
            "{scope, paths, digest} object (startup.md 6c)"
        ]
    if roster.get("digest") != roster_digest(paths):
        fired.append(
            "discovery.site_pass_roster.digest does not re-derive from paths "
            "(sha256 over paths joined by \\n, UTF-8) -- the roster was hand-edited"
        )
    files = site_pass.get("files") if isinstance(site_pass, dict) else None
    if not isinstance(files, list):
        fired.append(
            "scoped run: site_pass must be {files: [...]} with one entry per roster path "
            "(method.md Step 6.5; references/site-pass.md)"
        )
        return fired
    finding_ids = {
        str(f.get("id"))
        for f in (current_review.get("findings") or [])
        if isinstance(f, dict) and f.get("id") is not None
    }
    seen: list[str] = []
    for index, entry in enumerate(files):
        label = f"site_pass.files[{index}]"
        if not isinstance(entry, dict):
            fired.append(f"{label}: entry must be an object")
            continue
        path = entry.get("path")
        if isinstance(path, str) and path:
            seen.append(path)
            label = f"{label} ({path})"
        else:
            fired.append(f"{label}: path must be a non-empty string")
        reads = entry.get("reads")
        if not (isinstance(reads, str) and (reads == "full" or reads.startswith("partial:"))):
            fired.append(f'{label}: reads must be "full" or "partial:<line-ranges>"')
        questions = entry.get("questions")
        if not isinstance(questions, dict) or set(questions) != QUESTION_IDS:
            fired.append(f"{label}: questions keys must be exactly Q1..Q8")
            continue
        for q in sorted(QUESTION_IDS):
            answer = questions[q]
            status = answer.get("status") if isinstance(answer, dict) else None
            if status not in STATUSES:
                fired.append(f"{label} {q}: status must be clean | finding | not_applicable")
            elif status == "finding":
                ids = answer.get("finding_ids")
                if not (isinstance(ids, list) and ids):
                    fired.append(f"{label} {q}: status finding requires non-empty finding_ids")
                else:
                    unknown = [str(i) for i in ids if str(i) not in finding_ids]
                    if unknown:
                        fired.append(f"{label} {q}: finding_ids not present in findings: {unknown}")
            elif status == "not_applicable":
                reason = answer.get("reason")
                if not (isinstance(reason, str) and reason.strip()):
                    fired.append(f"{label} {q}: not_applicable requires a non-empty reason")
            elif answer.get("finding_ids"):
                fired.append(f"{label} {q}: clean must not carry finding_ids")
    roster_set = set(paths)
    seen_set = set(seen)
    duplicates = sorted({p for p in seen if seen.count(p) > 1})
    missing = sorted(roster_set - seen_set)
    extra = sorted(seen_set - roster_set)
    if missing:
        fired.append(
            f"site_pass covers {len(seen_set & roster_set)} of {len(roster_set)} roster files; "
            f"missing {len(missing)}: {missing[:5]}{' ...' if len(missing) > 5 else ''}"
        )
    if extra:
        fired.append(f"site_pass lists paths outside the roster: {extra[:5]}")
    if duplicates:
        fired.append(f"site_pass lists a path more than once: {duplicates[:5]}")
    return fired


def check_g52_site_pass(current_review) -> list[Issue]:
    if not isinstance(current_review, dict):
        return []
    if not _ruleset_epoch.applies("G52_SITE_PASS", current_review):
        return []
    loop = current_review.get("loop")
    for msg in site_pass_diagnostics(current_review):
        print(f"[g52-site-pass loop={loop} {msg}]")
    return []  # REPORT_ONLY: diagnostics only, never an Issue -- see the promotion bar above
