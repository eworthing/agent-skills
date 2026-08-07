#!/usr/bin/env python3
"""Self-test for the panel_certification capability manifest lookup + partial-
panel resume router (_panel_capability.py, plans/rec1-panel-certification.md
§ Version transition, enablement, and delivery sequence).

Covers: shipped manifest default-deny, emit_check's five-way decision order
(measured, unmeasured, stale digest, model override, unknown provider,
rollback), and resume_route's routing precedence over a persisted partial v5
panel checkpoint (rollback, stale digest, drift, sub_phase normalization,
decisive break, stage-1 unavailable, complete_panel, stage-2 unavailable,
resume_stage2, malformed checkpoint).

Resume-case checkpoints stamp the LIVE computed protocol digest so route
decisions past the digest check are reachable.

Run: python3 scripts/_panel_capability_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys

import _panel_capability as cap
import _panel_gate_adapter as adapter

LIVE_DIGEST = adapter.compute_protocol_digest()
STALE_DIGEST = "sha256:" + "0" * 64


def _manifest(entries=None, unsupported=None):
    return {
        "schema_version": 1,
        "entries": entries or [],
        "unsupported_digests": unsupported or [],
    }


def _entry(provider="claude_code", model="claude-sonnet-5", digest=LIVE_DIGEST):
    return {
        "provider": provider,
        "model": model,
        "protocol_digest": digest,
        "evidence": "evals/panel_gate_results.json",
        "recorded": "2026-08-07",
    }


def _binding(source_rev="rev-1", fingerprint="fp-1"):
    return {
        "run_id": "run-1",
        "source_rev": source_rev,
        "candidate_commit_sha": "sha-1",
        "candidate_fingerprint": fingerprint,
    }


def _member(index, outcome):
    return {"member_index": index, "outcome": outcome}


def _checkpoint(
    members, sub_phase="members", digest=LIVE_DIGEST, source_rev="rev-1", fingerprint="fp-1"
):
    return {
        "phase": "halt_success_panel",
        "panel_state": {
            "protocol_digest": digest,
            "candidate_binding": _binding(source_rev, fingerprint),
            "sub_phase": sub_phase,
            "members": members,
            "registry_pending_writes": [],
        },
    }


# --- cases ---


def test_shipped_manifest_default_deny():
    manifest = cap.load_manifest()
    assert manifest["schema_version"] == 1, manifest
    assert manifest["entries"] == [], manifest["entries"]
    assert manifest["unsupported_digests"] == [], manifest["unsupported_digests"]


def test_measured_profile_matches():
    manifest = _manifest(entries=[_entry()])
    result = cap.emit_check("claude_code", "claude-sonnet-5", manifest=manifest)
    assert result == {"emit": "v5", "reason": "match", "protocol_digest": LIVE_DIGEST}, result


def test_unmeasured_profile_no_entry():
    result = cap.emit_check("claude_code", "claude-sonnet-5", manifest=_manifest())
    assert (result["emit"], result["reason"]) == ("v4", "no_entry"), result


def test_stale_digest():
    manifest = _manifest(entries=[_entry(digest=STALE_DIGEST)])
    result = cap.emit_check("claude_code", "claude-sonnet-5", manifest=manifest)
    assert (result["emit"], result["reason"]) == ("v4", "stale_digest"), result


def test_model_override_no_entry():
    manifest = _manifest(entries=[_entry(model="claude-opus-5")])
    result = cap.emit_check("claude_code", "claude-sonnet-5", manifest=manifest)
    assert (result["emit"], result["reason"]) == ("v4", "no_entry"), result


def test_unknown_provider():
    manifest = _manifest(entries=[_entry(provider="unknown")])
    result = cap.emit_check("unknown", "claude-sonnet-5", manifest=manifest)
    assert (result["emit"], result["reason"]) == ("v4", "unknown_provider"), result


def test_rollback_unsupported_digest():
    manifest = _manifest(entries=[_entry()], unsupported=[LIVE_DIGEST])
    result = cap.emit_check("claude_code", "claude-sonnet-5", manifest=manifest)
    assert (result["emit"], result["reason"]) == ("v4", "unsupported_digest"), result

    checkpoint = _checkpoint([_member(1, "held"), _member(2, "held"), _member(3, "held")])
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=manifest)
    assert route["route"] == "fail_closed_verification_blocked", route


def test_resume_stale_digest():
    checkpoint = _checkpoint([_member(1, "held")], digest=STALE_DIGEST)
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "fail_closed_verification_blocked", route


def test_resume_drift():
    checkpoint = _checkpoint([_member(1, "held")], source_rev="rev-1", fingerprint="fp-1")
    route = cap.resume_route(checkpoint, "rev-2", "fp-2", manifest=_manifest())
    assert route["route"] == "drift_fresh_critic", route


def test_resume_drift_source_rev_only():
    checkpoint = _checkpoint([_member(1, "held")], source_rev="rev-1", fingerprint="fp-1")
    route = cap.resume_route(checkpoint, "rev-2", "fp-1", manifest=_manifest())
    assert route["route"] == "drift_fresh_critic", route


def test_resume_empty_members_stage1():
    checkpoint = _checkpoint([])
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "resume_stage1", route


def test_resume_unchanged_candidate_stage2():
    checkpoint = _checkpoint([_member(1, "held")])
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "resume_stage2", route


def test_resume_decisive_break():
    checkpoint = _checkpoint([_member(1, "broke")])
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "route_decisive_break", route


def test_resume_member1_unavailable():
    checkpoint = _checkpoint([_member(1, "unavailable")])
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "route_verification_blocked", route


def test_resume_sub_phase_normalization():
    checkpoint = _checkpoint(
        [_member(1, "held"), _member(2, "held"), _member(3, "held")], sub_phase="normalization"
    )
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "complete_normalization", route


def test_resume_three_held_complete_panel():
    checkpoint = _checkpoint([_member(1, "held"), _member(2, "held"), _member(3, "held")])
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "complete_panel", route


def test_resume_stage2_unavailable():
    checkpoint = _checkpoint([_member(1, "held"), _member(2, "unavailable"), _member(3, "held")])
    route = cap.resume_route(checkpoint, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "route_verification_blocked", route


def test_resume_malformed_checkpoint():
    route = cap.resume_route({"phase": "halt_success_panel"}, "rev-1", "fp-1", manifest=_manifest())
    assert route["route"] == "fail_closed_verification_blocked", route
    assert "panel_state" in route["reason"], route


def main() -> int:
    cases = [
        (
            "shipped canon file parses; entries == [] (default-deny)",
            test_shipped_manifest_default_deny,
        ),
        ("measured profile, live digest -> v5/match", test_measured_profile_matches),
        ("unmeasured profile, empty entries -> v4/no_entry", test_unmeasured_profile_no_entry),
        ("stale digest -> v4/stale_digest", test_stale_digest),
        ("model override -> v4/no_entry", test_model_override_no_entry),
        ("unknown provider -> v4/unknown_provider", test_unknown_provider),
        (
            "rollback: unsupported digest -> v4/unsupported_digest; resume -> fail_closed",
            test_rollback_unsupported_digest,
        ),
        ("resume: stale stored digest -> fail_closed", test_resume_stale_digest),
        ("resume: candidate drift (both fields) -> drift_fresh_critic", test_resume_drift),
        (
            "resume: candidate drift (source_rev only) -> drift_fresh_critic",
            test_resume_drift_source_rev_only,
        ),
        (
            "resume: interrupted before member 1 delivered (0 records) -> resume_stage1",
            test_resume_empty_members_stage1,
        ),
        (
            "resume: unchanged candidate, member 1 held, 1 record -> resume_stage2",
            test_resume_unchanged_candidate_stage2,
        ),
        ("resume: member 1 broke -> route_decisive_break", test_resume_decisive_break),
        (
            "resume: member 1 unavailable -> route_verification_blocked",
            test_resume_member1_unavailable,
        ),
        (
            "resume: sub_phase=normalization -> complete_normalization",
            test_resume_sub_phase_normalization,
        ),
        ("resume: 3 held -> complete_panel", test_resume_three_held_complete_panel),
        (
            "resume: 3 records, one stage-2 unavailable -> route_verification_blocked",
            test_resume_stage2_unavailable,
        ),
        (
            "resume: malformed checkpoint (no panel_state) -> fail_closed",
            test_resume_malformed_checkpoint,
        ),
    ]
    failures: list[str] = []
    for label, fn in cases:
        try:
            fn()
        except AssertionError as e:
            failures.append(f"{label}: {e}")
        else:
            print(f"ok: {label}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: panel capability selftest holds across {len(cases)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
