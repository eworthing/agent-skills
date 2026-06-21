#!/usr/bin/env python3
"""Canonical candidate_fingerprint for contest-refactor HALT_SUCCESS candidates.

The fingerprint is the OSCILLATION equivalence key (see G32 in validation.md and
halt-verifier.md): two candidates whose architecture-relevant payload is
identical must share a fingerprint even when volatile metadata (commit sha,
run_id, loop counter, timestamps, schema_version, state, narrative prose)
differs. It is DISTINCT from the candidate commit SHA, which is the G32 freshness
binding and changes on every recommit — so the SHA can never detect recurrence.

Owned here; referenced by references/output-format-json.md and halt-verifier.md.
Run directly to execute the stability self-test:  python3 scripts/candidate_fingerprint.py
"""
from __future__ import annotations

import hashlib
import json


def _architecture_payload(review: dict) -> dict:
    """The architecture-relevant subset that defines a candidate's identity.

    Includes scorecard scores + residual dispositions/rationales, findings
    (title + evidence + severity), and the analyzed source identity (lens +
    source roots). Excludes everything volatile by simply not reading it.
    """
    scorecard = {}
    for dim, entry in (review.get("scorecard") or {}).items():
        if isinstance(entry, dict):
            scorecard[dim] = {
                "score": entry.get("score"),
                "residual_disposition": entry.get("residual_disposition"),
                "residual_blocking_10": entry.get("residual_blocking_10"),
                "residual_rationale_or_backlog_ref": entry.get(
                    "residual_rationale_or_backlog_ref"
                ),
            }
    findings = [
        {
            "title": f.get("title"),
            "evidence": f.get("evidence"),
            "severity": f.get("severity"),
        }
        for f in (review.get("findings") or [])
        if isinstance(f, dict)
    ]
    discovery = review.get("discovery") or {}
    return {
        "lens": discovery.get("lens"),
        "source_roots": discovery.get("source_roots"),
        "scorecard": scorecard,
        "findings": findings,
    }


def candidate_fingerprint(review: dict) -> str:
    """Return the canonical oscillation fingerprint for a candidate review dict."""
    canonical = json.dumps(
        _architecture_payload(review), sort_keys=True, separators=(",", ":")
    )
    return "fp-sha256-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def _selftest() -> None:
    base = {
        "schema_version": 4,
        "state": "HALT_SUCCESS_candidate",
        "loop": 1,
        "run_id": "run-A",
        "source_rev": "sha-A",
        "discovery": {"lens": "Apple", "source_roots": ["src/"]},
        "scorecard": {
            "data_flow": {
                "score": 9.5,
                "residual_disposition": "accepted",
                "residual_blocking_10": "x",
                "residual_rationale_or_backlog_ref": "y",
            }
        },
        "findings": [],
    }
    # Identical architecture, different volatile metadata -> SAME fingerprint.
    other = json.loads(json.dumps(base))
    other.update(
        {
            "state": "HALT_SUCCESS",
            "loop": 7,
            "run_id": "run-B",
            "source_rev": "sha-B",
            "candidate_commit_sha": "deadbeef",
            "narrative": "completely different prose",
        }
    )
    assert candidate_fingerprint(base) == candidate_fingerprint(
        other
    ), "volatile metadata must not change the fingerprint"
    # Meaningful scorecard change -> DIFFERENT fingerprint.
    changed = json.loads(json.dumps(base))
    changed["scorecard"]["data_flow"]["score"] = 9.0
    assert candidate_fingerprint(base) != candidate_fingerprint(
        changed
    ), "a scorecard change must change the fingerprint"
    # Meaningful findings change -> DIFFERENT fingerprint.
    changed2 = json.loads(json.dumps(base))
    changed2["findings"] = [
        {"title": "new", "evidence": ["a.py:1"], "severity": "Serious deduction"}
    ]
    assert candidate_fingerprint(base) != candidate_fingerprint(
        changed2
    ), "a findings change must change the fingerprint"
    print("candidate_fingerprint self-test: OK (3 assertions passed)")


if __name__ == "__main__":
    _selftest()
