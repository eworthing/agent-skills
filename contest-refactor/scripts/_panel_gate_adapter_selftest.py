#!/usr/bin/env python3
"""Self-test for the pre-enforcement behavioral-gate grading adapter
(_panel_gate_adapter.py, plans/rec1-panel-certification.md § Pre-enforcement gate).

Covers: protocol-digest determinism and shape, tolerant JSON extraction from a
challenger's final message, member-record assembly (unparseable/malformed-break
conversion to 'unavailable'), the gate-scope break-normalization transaction,
aggregate/state mapping, structural grading (reused G32 panel validation, never
reimplemented), deterministic semantic grading for both gate scenarios, the
budget audit, and an end-to-end grade_captures run.

Run: python3 scripts/_panel_gate_adapter_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import sys

import _panel_gate_adapter as adapter


def _attempts():
    return [
        {
            "arm": "residual_refutation",
            "target": "state_management",
            "what_tried": "reread the accepted residual against source",
            "why_failed": "residual holds",
        },
        {
            "arm": "new_finding",
            "target": "simplicity",
            "what_tried": "grep leaf modules for duplicated formatting/dispatch logic",
            "why_failed": "none found beyond the reviewed residual",
        },
    ]


def _held_json(model="claude-sonnet-5"):
    return json.dumps(
        {
            "challenger_model": model,
            "outcome": "held",
            "attempts": _attempts(),
            "reason": "candidate holds; no Serious-or-worse finding survives inspection",
        }
    )


def _broke_flag_json(model="claude-sonnet-5"):
    return json.dumps(
        {
            "challenger_model": model,
            "outcome": "broke",
            "attempts": _attempts(),
            "reason": "selectedTab has split ownership across three writers",
            "break_evidence": {
                "finding": {
                    "title": "selectedTab has three independent writers, not a single owner",
                    "why_it_matters": "HR-1 requires a single mutable owner; the residual's compliance claim is unverified",
                    "what_is_wrong": "TabView's selection binding, DeepLinkRouter.handle, and LoginViewModel.onSuccess all write selectedTab directly",
                    "evidence": [
                        "RootView.swift:23",
                        "DeepLinkRouter.swift:29",
                        "LoginViewModel.swift:34",
                    ],
                    "why_weakens_submission": "the accepted residual rests on a compliance rationale source does not support",
                    "minimal_correction_path": "route every selectedTab write through the reducer intent pipeline",
                    "severity": "Serious deduction",
                },
                "spt": {
                    "result": "passed",
                    "rationale": "removing any one writer breaks a required navigation path, so consolidation is a real subtractive fix",
                },
            },
        }
    )


def _broke_generic_json(model="claude-sonnet-5"):
    return json.dumps(
        {
            "challenger_model": model,
            "outcome": "broke",
            "attempts": _attempts(),
            "reason": "found a naming inconsistency",
            "break_evidence": {
                "finding": {
                    "title": "Inconsistent naming in navigation helpers",
                    "why_it_matters": "makes the code harder to read",
                    "what_is_wrong": "some helpers use camelCase, others snake_case",
                    "evidence": ["Helpers.swift:12"],
                    "why_weakens_submission": "minor readability issue",
                    "minimal_correction_path": "rename for consistency",
                    "severity": "Noticeable",
                },
                "spt": {"result": "passed", "rationale": "renaming is a genuine simplification"},
            },
        }
    )


def _broke_filelength_json(model="claude-sonnet-5"):
    return json.dumps(
        {
            "challenger_model": model,
            "outcome": "broke",
            "attempts": _attempts(),
            "reason": "file is too long",
            "break_evidence": {
                "finding": {
                    "title": "VendorCatalogClient.swift is 979 LOC",
                    "why_it_matters": "large files are hard to navigate",
                    "what_is_wrong": "the file exceeds typical file length guidance",
                    "evidence": ["VendorCatalogClient.swift:1"],
                    "why_weakens_submission": "file length alone",
                    "minimal_correction_path": "split the file",
                    "severity": "Serious deduction",
                },
                "spt": {"result": "passed", "rationale": "splitting reduces file length"},
            },
        }
    )


def _malformed_break_json(model="claude-sonnet-5"):
    return json.dumps(
        {
            "challenger_model": model,
            "outcome": "broke",
            "attempts": _attempts(),
            "reason": "found something",
            "break_evidence": {"finding": {"title": "x"}},  # missing spt
        }
    )


def _usage(total):
    input_t = int(total * 0.7)
    return {"input_tokens": input_t, "output_tokens": total - input_t, "total_tokens": total}


def _retry_ok():
    return [{"attempt": 1, "outcome": "ok", "error": None, "duration_ms": 45000}]


def _capture_member(index, raw_text, token_usage=None, retry_attempts=None, retry_cause=None):
    return {
        "member_index": index,
        "raw_response_text": raw_text,
        "retry_cause": retry_cause,
        "retry_attempts": retry_attempts if retry_attempts is not None else _retry_ok(),
        "token_usage": token_usage if token_usage is not None else _usage(1500),
    }


def _panel(index, members):
    return {"panel_index": index, "members": members}


def _capture(scenario, panels, provider="claude_code", model="claude-sonnet-5"):
    return {"provider": provider, "model": model, "scenario": scenario, "panels": panels}


def _held_record(index):
    return adapter._assemble_member(_capture_member(index, _held_json()))


# --- cases ---


def test_digest_format_and_determinism():
    d1 = adapter.compute_protocol_digest()
    d2 = adapter.compute_protocol_digest()
    assert d1 == d2, "digest not deterministic across calls"
    assert d1.startswith("sha256:"), d1
    hex_part = d1[len("sha256:") :]
    assert len(hex_part) == 64, len(hex_part)
    assert all(c in "0123456789abcdef" for c in hex_part), hex_part


def test_digest_manifest_shape():
    manifest = adapter.digest_manifest()
    assert len(manifest) == 10, len(manifest)
    labels = [label for label, _ in manifest]
    assert labels == [f"input-{i:02d}" for i in range(1, 11)], labels
    assert all(length > 0 for _, length in manifest), manifest


def test_extract_member_json_variants():
    bare = _held_json()
    assert adapter.extract_member_json(bare) == json.loads(bare)
    fenced = "Here is my analysis.\n\n```json\n" + bare + "\n```\n\nThat is my verdict."
    assert adapter.extract_member_json(fenced) == json.loads(bare)
    assert adapter.extract_member_json("not json at all, just prose") is None


def test_extract_member_json_double_encoded():
    bare = _held_json()
    double_encoded = json.dumps(bare)  # whole object serialized again as a JSON string
    assert adapter.extract_member_json(double_encoded) == json.loads(bare)


def test_assemble_member_unparseable():
    record = adapter._assemble_member(_capture_member(1, "not json at all"))
    assert record["outcome"] == "unavailable", record
    assert record["break_evidence"] is None
    assert record["reason"] == "malformed challenger response after retry envelope"


def test_assemble_member_malformed_break():
    record = adapter._assemble_member(_capture_member(1, _malformed_break_json()))
    assert record["outcome"] == "unavailable", record
    assert record["break_evidence"] is None


def test_normalize_single_broke():
    member_records = [
        _held_record(1),
        adapter._assemble_member(_capture_member(2, _broke_flag_json())),
        _held_record(3),
    ]
    records, findings, aggregate, _state, _subtype = adapter.normalize_panel(member_records)
    assert aggregate == "broke", aggregate
    assert records[1]["break_evidence"]["finding_stable_id"] == "F-1"
    assert len(findings) == 1
    assert findings[0]["stable_id"] == "F-1"
    assert findings[0]["loop_local_id"] == "F1"


def test_aggregate_mapping():
    records = [_held_record(1), _held_record(2), _held_record(3)]
    _, _, aggregate, state, subtype = adapter.normalize_panel(records)
    assert (aggregate, state, subtype) == ("held", "HALT_SUCCESS", None)

    records = [adapter._assemble_member(_capture_member(1, _broke_flag_json()))]
    _, _, aggregate, state, subtype = adapter.normalize_panel(records)
    assert (aggregate, state, subtype) == ("broke", "CONTINUE", None)

    records = [adapter._assemble_member(_capture_member(1, "garbage"))]
    _, _, aggregate, state, subtype = adapter.normalize_panel(records)
    assert (aggregate, state, subtype) == ("blocked", "HALT_STAGNATION", "verification_blocked")


def test_structural_pass_three_held():
    capture = _capture(
        "halt-challenge-restraint",
        [
            _panel(
                1,
                [
                    _capture_member(1, _held_json()),
                    _capture_member(2, _held_json()),
                    _capture_member(3, _held_json()),
                ],
            )
        ],
    )
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    run = results["runs"][0]
    assert run["structural_pass"] is True, run["structural_issues"]
    assert run["structural_issues"] == []


def test_structural_pass_single_broke():
    capture = _capture("halt-challenge-flag", [_panel(1, [_capture_member(1, _broke_flag_json())])])
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    run = results["runs"][0]
    assert run["structural_pass"] is True, run["structural_issues"]


def test_structural_fail_member1_broke_three_entries():
    capture = _capture(
        "halt-challenge-flag",
        [
            _panel(
                1,
                [
                    _capture_member(1, _broke_flag_json()),
                    _capture_member(2, _held_json()),
                    _capture_member(3, _held_json()),
                ],
            )
        ],
    )
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    run = results["runs"][0]
    assert run["structural_pass"] is False
    assert any("member 1 outcome" in issue for issue in run["structural_issues"]), run[
        "structural_issues"
    ]


def test_semantic_flag_pass():
    capture = _capture("halt-challenge-flag", [_panel(1, [_capture_member(1, _broke_flag_json())])])
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    checks = {c["assertion"]: c["passed"] for c in results["runs"][0]["semantic_checks"]}
    assert checks["f1-broke-maps-rejected"] is True
    assert checks["f2-names-split-ownership"] is True
    assert checks["f4-severity-serious-or-worse"] is True
    assert results["runs"][0]["semantic_pass"] is True


def test_semantic_flag_fail_generic():
    capture = _capture(
        "halt-challenge-flag", [_panel(1, [_capture_member(1, _broke_generic_json())])]
    )
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    checks = {c["assertion"]: c["passed"] for c in results["runs"][0]["semantic_checks"]}
    assert checks["f2-names-split-ownership"] is False
    assert results["runs"][0]["semantic_pass"] is False


def test_semantic_restraint_pass():
    capture = _capture(
        "halt-challenge-restraint",
        [
            _panel(
                1,
                [
                    _capture_member(1, _held_json()),
                    _capture_member(2, _held_json()),
                    _capture_member(3, _held_json()),
                ],
            )
        ],
    )
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    checks = {c["assertion"]: c["passed"] for c in results["runs"][0]["semantic_checks"]}
    assert checks["r1-all-held"] is True
    assert checks["r2-no-file-length-break"] is True
    assert results["runs"][0]["semantic_pass"] is True


def test_semantic_restraint_overflag_fail():
    capture = _capture(
        "halt-challenge-restraint", [_panel(1, [_capture_member(1, _broke_filelength_json())])]
    )
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    checks = {c["assertion"]: c["passed"] for c in results["runs"][0]["semantic_checks"]}
    assert checks["r1-all-held"] is False
    assert checks["r2-no-file-length-break"] is False
    assert results["runs"][0]["semantic_pass"] is False


def _all_held_members():
    return [
        _capture_member(1, _held_json()),
        _capture_member(2, _held_json()),
        _capture_member(3, _held_json()),
    ]


def test_budget_violation():
    over_budget = [
        _capture_member(1, _held_json(), token_usage=_usage(adapter.C_MAX + 50_000)),
        _capture_member(2, _held_json()),
        _capture_member(3, _held_json()),
    ]
    capture = _capture(
        "halt-challenge-restraint",
        [_panel(1, over_budget), _panel(2, _all_held_members()), _panel(3, _all_held_members())],
    )
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    run1 = results["runs"][0]
    assert run1["exhaustion_cause"] == "budget_exhausted"
    assert run1["budget_violation"] is True
    assert results["scenario_gate"]["halt-challenge-restraint"]["pass"] is False


def test_budget_per_attempt_no_violation():
    # attempt 1 is tagged budget_exhausted (over cap by definition -- that's
    # why it was discarded and retried) and is excluded from the per-attempt
    # check; attempt 2 (outcome "ok") is the one actually checked, and stays
    # under C_MAX (1_200_000). The member aggregate (required to sum every
    # attempt) is still over C_MAX -- exactly the shape the old aggregate-only
    # audit falsely flagged.
    exhausted_total = 1_250_000
    ok_total = 400_000
    member = _capture_member(
        1,
        _held_json(),
        token_usage=_usage(exhausted_total + ok_total),
        retry_cause="budget_exhausted",
        retry_attempts=[
            {
                "attempt": 1,
                "outcome": "budget_exhausted",
                "error": "cumulative session tokens exceeded C_max",
                "duration_ms": 90000,
                "token_usage": _usage(exhausted_total),
            },
            {
                "attempt": 2,
                "outcome": "ok",
                "error": None,
                "duration_ms": 45000,
                "token_usage": _usage(ok_total),
            },
        ],
    )
    capture = _capture(
        "halt-challenge-restraint",
        [_panel(1, [member, _capture_member(2, _held_json()), _capture_member(3, _held_json())])],
    )
    results = adapter.grade_captures([capture], skill_rev="deadbeef")
    run = results["runs"][0]
    assert run["exhaustion_cause"] is None, run["exhaustion_cause"]
    assert run["budget_violation"] is False
    assert run["structural_pass"] is True, run["structural_issues"]
    # G32 stripped retry_attempts back to the v5 envelope shape -- no leaked token_usage.
    for attempt in run["normalized_member_records"][0]["retry_attempts"]:
        assert "token_usage" not in attempt, attempt


def _flag_members():
    return [_capture_member(1, _broke_flag_json())]


def test_end_to_end_grade_captures():
    flag_capture = _capture(
        "halt-challenge-flag",
        [_panel(1, _flag_members()), _panel(2, _flag_members()), _panel(3, _flag_members())],
    )
    restraint_capture = _capture(
        "halt-challenge-restraint",
        [
            _panel(1, _all_held_members()),
            _panel(2, _all_held_members()),
            _panel(3, _all_held_members()),
        ],
    )
    results = adapter.grade_captures([flag_capture, restraint_capture], skill_rev="deadbeef")
    assert results["scenario_gate"]["halt-challenge-flag"]["pass"] is True, results["scenario_gate"]
    assert results["scenario_gate"]["halt-challenge-restraint"]["pass"] is True, results[
        "scenario_gate"
    ]
    assert results["profile_verdict"]["gate_pass"] is True
    assert len(results["runs"]) == 6, len(results["runs"])
    required_keys = {
        "provider",
        "model",
        "skill_rev",
        "protocol_digest",
        "scenario",
        "panel_index",
        "raw_member_responses",
        "normalized_member_records",
        "aggregate_outcome",
        "state",
        "halt_subtype",
        "findings",
        "enforced_C_max",
        "observed_usage",
        "exhaustion_cause",
        "budget_violation",
        "structural_pass",
        "structural_issues",
        "semantic_pass",
        "semantic_checks",
    }
    for run in results["runs"]:
        assert required_keys.issubset(run.keys()), sorted(required_keys - run.keys())
    assert results["measured_C"]["max_member_total_tokens"] == 1500, results["measured_C"]


def main() -> int:
    cases = [
        ("digest format and determinism", test_digest_format_and_determinism),
        ("digest manifest has 10 labeled inputs, all non-empty", test_digest_manifest_shape),
        ("extract_member_json: bare / fenced / garbage", test_extract_member_json_variants),
        ("extract_member_json: double-encoded verdict", test_extract_member_json_double_encoded),
        (
            "unparseable member -> unavailable, break_evidence None",
            test_assemble_member_unparseable,
        ),
        (
            "broke with malformed break_evidence -> unavailable",
            test_assemble_member_malformed_break,
        ),
        ("normalize: single valid broke gets F-1/F1", test_normalize_single_broke),
        ("aggregate mapping: held/broke/blocked", test_aggregate_mapping),
        ("structural pass: 3-held panel, zero issues", test_structural_pass_three_held),
        ("structural pass: 1-member valid-broke panel", test_structural_pass_single_broke),
        (
            "structural fail: member 1 broke in a 3-entry panel",
            test_structural_fail_member1_broke_three_entries,
        ),
        ("semantic flag pass: names the writers, Serious severity", test_semantic_flag_pass),
        ("semantic flag fail: generic break doesn't name writers", test_semantic_flag_fail_generic),
        ("semantic restraint pass: all 3 held", test_semantic_restraint_pass),
        (
            "semantic restraint fail: overflags on 979-LOC file length",
            test_semantic_restraint_overflag_fail,
        ),
        ("budget violation: exhausted member fails its panel", test_budget_violation),
        (
            "budget: per-attempt exhaustion doesn't falsely flag a retried member",
            test_budget_per_attempt_no_violation,
        ),
        ("end-to-end grade_captures: both scenario gates pass", test_end_to_end_grade_captures),
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
    print(f"OK: panel gate adapter selftest holds across {len(cases)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
