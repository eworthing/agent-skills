#!/usr/bin/env python3
"""Canonical candidate fingerprint and recurrence key for HALT_SUCCESS candidates.

The fingerprint identifies an architecture-relevant payload. Recurrence pairs it
with source_rev so a materially changed source tree can be challenged again while
artifact-only recommits remain equivalent. candidate_commit_sha is the separate
G32 freshness binding and changes on every recommit.

Owned here; referenced by references/output-format-json.md and halt-verifier.md.

CLI:
  python3 scripts/candidate_fingerprint.py                    # stability self-test
  python3 scripts/candidate_fingerprint.py compute <artifact>  # print canonical fingerprint
  python3 scripts/candidate_fingerprint.py verify <artifact>   # exit 0 iff recorded == canonical
  python3 scripts/candidate_fingerprint.py write <artifact>    # recompute + atomic in-place write

These replace the ad-hoc "import and call candidate_fingerprint() by hand" snippet
the register's instrumented-run audit found operators reaching for.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _architecture_payload(review: dict) -> dict:
    """The architecture-relevant subset that defines a candidate's identity.

    Includes scorecard scores + residual dispositions/blocker kinds, findings
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
                "residual_blocker_kind": entry.get("residual_blocker_kind"),
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
    canonical = json.dumps(_architecture_payload(review), sort_keys=True, separators=(",", ":"))
    return "fp-sha256-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def candidate_recurrence_key(review: dict) -> tuple[str, object]:
    """Return the oscillation key: architecture payload plus analyzed source revision."""
    return candidate_fingerprint(review), review.get("source_rev")


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
                "residual_blocker_kind": "cosmetic",
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
    assert candidate_fingerprint(base) == candidate_fingerprint(other), (
        "volatile metadata must not change the fingerprint"
    )
    assert candidate_recurrence_key(base) != candidate_recurrence_key(other), (
        "a changed source revision must be eligible for a fresh challenge"
    )
    same_source = json.loads(json.dumps(other))
    same_source["source_rev"] = base["source_rev"]
    assert candidate_recurrence_key(base) == candidate_recurrence_key(same_source), (
        "artifact-only metadata must not defeat recurrence detection"
    )
    rephrased = json.loads(json.dumps(base))
    rephrased["scorecard"]["data_flow"]["residual_rationale_or_backlog_ref"] = "new wording"
    assert candidate_fingerprint(base) == candidate_fingerprint(rephrased), (
        "free-form rationale wording must not defeat recurrence detection"
    )
    changed_kind = json.loads(json.dumps(base))
    changed_kind["scorecard"]["data_flow"]["residual_blocker_kind"] = "structural"
    assert candidate_fingerprint(base) != candidate_fingerprint(changed_kind), (
        "a changed structured blocker kind must change the fingerprint"
    )
    # Meaningful scorecard change -> DIFFERENT fingerprint.
    changed = json.loads(json.dumps(base))
    changed["scorecard"]["data_flow"]["score"] = 9.0
    assert candidate_fingerprint(base) != candidate_fingerprint(changed), (
        "a scorecard change must change the fingerprint"
    )
    # Meaningful findings change -> DIFFERENT fingerprint.
    changed2 = json.loads(json.dumps(base))
    changed2["findings"] = [
        {"title": "new", "evidence": ["a.py:1"], "severity": "Serious deduction"}
    ]
    assert candidate_fingerprint(base) != candidate_fingerprint(changed2), (
        "a findings change must change the fingerprint"
    )
    print("candidate_fingerprint self-test: OK (7 assertions passed)")

    # --- CLI modes: minimal coverage against a scratch artifact file ---
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        artifact_path = Path(tmp, "CURRENT_REVIEW.json")
        artifact_path.write_text(json.dumps(base), encoding="utf-8")

        assert _cmd_compute(artifact_path) == 0
        assert _cmd_verify(artifact_path) != 0, "no candidate_fingerprint recorded yet -> mismatch"

        assert _cmd_write(artifact_path) == 0
        written = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert written["candidate_fingerprint"] == candidate_fingerprint(base)
        assert _cmd_verify(artifact_path) == 0, "write must leave the artifact self-consistent"

        artifact_path.write_text(
            json.dumps({**base, "candidate_fingerprint": "stale"}), encoding="utf-8"
        )
        assert _cmd_verify(artifact_path) != 0, "a stale recorded fingerprint must fail verify"
    print("candidate_fingerprint CLI self-test: OK (compute/verify/write)")


def _load_review(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cmd_compute(path: Path) -> int:
    print(candidate_fingerprint(_load_review(path)))
    return 0


def _cmd_verify(path: Path) -> int:
    review = _load_review(path)
    recorded = review.get("candidate_fingerprint")
    expected = candidate_fingerprint(review)
    if recorded == expected:
        print(f"OK: candidate_fingerprint matches ({expected})")
        return 0
    sys.stderr.write(f"MISMATCH: recorded={recorded!r} canonical={expected!r}\n")
    return 1


def _cmd_write(path: Path) -> int:
    review = _load_review(path)
    review["candidate_fingerprint"] = candidate_fingerprint(review)
    tmp_path = path.parent / f"{path.name}.tmp"
    tmp_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    print(f"wrote candidate_fingerprint={review['candidate_fingerprint']} to {path}")
    return 0


def _main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        _selftest()
        return 0
    parser = argparse.ArgumentParser(description="candidate_fingerprint artifact CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn, help_text in (
        ("compute", _cmd_compute, "print the canonical fingerprint"),
        ("verify", _cmd_verify, "exit 0 iff the recorded fingerprint matches canonical"),
        ("write", _cmd_write, "recompute and atomically write the fingerprint in place"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("artifact", type=Path, help="path to a CURRENT_REVIEW.json-shaped artifact")
        p.set_defaults(func=fn)
    args = parser.parse_args(argv)
    try:
        return args.func(args.artifact)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
