#!/usr/bin/env python3
"""Structural/shape self-test for G32's v5 panel extension -- Tier 1 of
Recommendation 1 (plans/rec1-panel-certification.md).

Aggregate/state-coupling, pending-route, and rule #6 findings-count cases live
in _g32_panel_coupling_selftest.py (split out when this file crossed the
800-line module cap). Builders shared by both live in _g32_panel_testkit.py.

v4's single-challenger contract is exercised only at the version boundary here
(the full v4 corpus lives in evals/fixtures/ and is unaffected -- this file's job is
the NEW v5 shape). Every other case here targets panel/member SHAPE: staged-launch
length rules, member_index ordering, per-member arm diversity (the v4 rule reused
verbatim), the retry envelope extended with budget_exhausted, token_usage
arithmetic, the break_evidence normalized-form fields, and candidate_binding /
protocol_digest shape.

A few cases are load-bearing because they pin decisions the plan flags as easy to
get wrong:
  - "budget_exhausted is legal in both retry enums" pins the ONE value v5 adds to
    rule #25's envelope; a validator that forgot either enum would make every
    real exhaustion record schema-invalid (plan § Cost).
  - "candidate_binding shape required but NOT compared for equality on CONTINUE"
    pins that G32 never compares candidate_binding against top-level fields
    outside HALT_SUCCESS -- those fields are absent by construction elsewhere, and
    the plan documents two prior drafts that wrongly asked G32 for a comparison it
    has no source for.
  - "3-entry panel with member 1 broke fails" pins the converse of the staged
    length rule: members 2/3 only launch after member 1 held, so a 3-entry panel
    recording member 1 broke/unavailable describes an execution the staged
    launch cannot produce.

Run: python3 scripts/_g32_panel_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import sys

import _g32_panel_testkit

_load_validator = _g32_panel_testkit._load_validator
_attempts = _g32_panel_testkit._attempts
_retry_attempt = _g32_panel_testkit._retry_attempt
_normalized_evidence = _g32_panel_testkit._normalized_evidence
_member = _g32_panel_testkit._member
_challenge = _g32_panel_testkit._challenge
_success_review = _g32_panel_testkit._success_review
_nonterminal_review = _g32_panel_testkit._nonterminal_review
_candidate_review = _g32_panel_testkit._candidate_review
_binding = _g32_panel_testkit._binding
RUN_ID = _g32_panel_testkit.RUN_ID
SOURCE_REV = _g32_panel_testkit.SOURCE_REV
COMMIT_SHA = _g32_panel_testkit.COMMIT_SHA
STABLE_A = _g32_panel_testkit.STABLE_A
FP = _g32_panel_testkit.FP


def _cases():
    """(label, review, expect_fire)"""
    cases: list[tuple[str, dict, bool]] = []

    # --- v4/v5 version boundary ---
    v4_challenge = {
        "outcome": "held",
        "challenger_model": "opus",
        "attempts": _attempts(),
        "reason": "no residual found",
        "binding": {"candidate_commit_sha": COMMIT_SHA, "run_id": RUN_ID, "source_rev": SOURCE_REV},
    }

    def v4_review(sv):
        return {
            "schema_version": sv,
            "state": "HALT_SUCCESS",
            "run_id": RUN_ID,
            "source_rev": SOURCE_REV,
            "candidate_fingerprint": FP,
            "scorecard": {},
            "findings": [],
            "halt_success_challenge": v4_challenge,
        }

    cases.append(
        ("v4 single-challenger shape still validates at schema_version=4", v4_review(4), False)
    )
    cases.append(
        ("v4 single-challenger shape is not a valid panel at schema_version=5", v4_review(5), True)
    )

    # --- required_panel_size ---
    cases.append(
        ("required_panel_size != 3 fails", _success_review(_challenge(required_panel_size=2)), True)
    )

    # --- panel length vs staged rule ---
    cases.append(
        ("panel of 2 fails", _success_review(_challenge(panel=[_member(1), _member(2)])), True)
    )
    cases.append(
        (
            "1-entry panel with member 1 held fails (staged rule)",
            _success_review(_challenge(panel=[_member(1, outcome="held")])),
            True,
        )
    )
    broke1 = _member(
        1, outcome="broke", break_evidence=_normalized_evidence(), reason="dialog logic duplicated"
    )
    cases.append(
        (
            "1-entry panel, member 1 broke -> CONTINUE, aggregate broke: passes",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(outcome="broke", panel=[broke1]),
                findings=[{"stable_id": STABLE_A}],
            ),
            False,
        )
    )
    unavailable1 = _member(
        1,
        outcome="unavailable",
        reason="all retries exhausted",
        retry_count=2,
        retry_cause="timeout",
        retry_attempts=[_retry_attempt(1, "timeout"), _retry_attempt(2, "timeout")],
    )
    cases.append(
        (
            "1-entry panel, member 1 unavailable -> verification_blocked, aggregate blocked: passes",
            _nonterminal_review(
                "HALT_STAGNATION",
                "verification_blocked",
                _challenge(outcome="blocked", panel=[unavailable1]),
            ),
            False,
        )
    )
    cases.append(
        (
            "3-entry panel with member 1 broke fails: members 2/3 never launch after a break",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(
                    outcome="broke",
                    panel=[
                        _member(
                            1,
                            outcome="broke",
                            break_evidence=_normalized_evidence("F-020"),
                            reason="a",
                        ),
                        _member(2),
                        _member(3),
                    ],
                ),
                findings=[{"stable_id": "F-020"}],
            ),
            True,
        )
    )

    # --- member_index gaps / reordering ---
    bad_order = [_member(1), {**_member(2), "member_index": 3}, {**_member(3), "member_index": 2}]
    cases.append(
        ("member_index reordering fails", _success_review(_challenge(panel=bad_order)), True)
    )
    gap = [_member(1), _member(2), {**_member(3), "member_index": 4}]
    cases.append(("member_index gap fails", _success_review(_challenge(panel=gap)), True))

    # --- per-member arm diversity (v4 rule reused per member) ---
    no_diversity = _member(2, attempts=_attempts(diverse=False))
    cases.append(
        (
            "member missing the new_finding/simplicity|domain_modeling arm fails",
            _success_review(_challenge(panel=[_member(1), no_diversity, _member(3)])),
            True,
        )
    )

    # --- retry envelope: rule #25 + budget_exhausted ---
    mismatched_first = _member(
        2,
        retry_count=2,
        retry_cause="timeout",
        retry_attempts=[_retry_attempt(1, "spawn_error"), _retry_attempt(2, "ok")],
    )
    cases.append(
        (
            "retry_attempts[0].outcome must match retry_cause",
            _success_review(_challenge(panel=[_member(1), mismatched_first, _member(3)])),
            True,
        )
    )
    short_retry = _member(
        2, retry_count=2, retry_cause="timeout", retry_attempts=[_retry_attempt(1, "timeout")]
    )
    cases.append(
        (
            "retry_attempts length must equal retry_count",
            _success_review(_challenge(panel=[_member(1), short_retry, _member(3)])),
            True,
        )
    )
    budget_retry = _member(
        2,
        retry_count=2,
        retry_cause="budget_exhausted",
        retry_attempts=[_retry_attempt(1, "budget_exhausted"), _retry_attempt(2, "ok")],
    )
    cases.append(
        (
            "budget_exhausted is legal in both retry enums (v5 extension)",
            _success_review(_challenge(panel=[_member(1), budget_retry, _member(3)])),
            False,
        )
    )

    # --- token_usage arithmetic ---
    bad_usage = _member(2, token_usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 16})
    cases.append(
        (
            "token_usage.total_tokens must equal input + output",
            _success_review(_challenge(panel=[_member(1), bad_usage, _member(3)])),
            True,
        )
    )
    cases.append(
        (
            "token_usage=null is permitted",
            _success_review(
                _challenge(panel=[_member(1), _member(2, token_usage=None), _member(3)])
            ),
            False,
        )
    )
    negative_usage = _member(
        2, token_usage={"input_tokens": -1, "output_tokens": 5, "total_tokens": 4}
    )
    cases.append(
        (
            "token_usage fields must be non-negative",
            _success_review(_challenge(panel=[_member(1), negative_usage, _member(3)])),
            True,
        )
    )

    # --- break_evidence normalized form ---
    cases.append(
        (
            "finding_stable_id that does not resolve in findings[] fails",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(
                    outcome="broke",
                    panel=[
                        _member(1),
                        _member(2, outcome="broke", break_evidence=_normalized_evidence("F-999")),
                        _member(3),
                    ],
                ),
                findings=[{"stable_id": STABLE_A}],
            ),
            True,
        )
    )
    cases.append(
        (
            "spt.result != 'passed' fails",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(
                    outcome="broke",
                    panel=[
                        _member(1),
                        _member(
                            2,
                            outcome="broke",
                            break_evidence={
                                "finding_stable_id": STABLE_A,
                                "spt": {"result": "failed", "rationale": "x"},
                            },
                        ),
                        _member(3),
                    ],
                ),
                findings=[{"stable_id": STABLE_A}],
            ),
            True,
        )
    )
    cases.append(
        (
            "empty spt.rationale fails",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(
                    outcome="broke",
                    panel=[
                        _member(1),
                        _member(
                            2,
                            outcome="broke",
                            break_evidence={
                                "finding_stable_id": STABLE_A,
                                "spt": {"result": "passed", "rationale": "  "},
                            },
                        ),
                        _member(3),
                    ],
                ),
                findings=[{"stable_id": STABLE_A}],
            ),
            True,
        )
    )
    cases.append(
        (
            "break_evidence=null with outcome='broke' fails",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(
                    outcome="broke", panel=[_member(1), _member(2, outcome="broke"), _member(3)]
                ),
                findings=[],
            ),
            True,
        )
    )
    cases.append(
        (
            "break_evidence present with outcome != 'broke' fails",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(
                    outcome="broke",
                    panel=[
                        _member(1, break_evidence=_normalized_evidence()),
                        _member(2, outcome="broke", break_evidence=_normalized_evidence()),
                        _member(3),
                    ],
                ),
                findings=[{"stable_id": STABLE_A}],
            ),
            True,
        )
    )

    # --- candidate_binding shape / equality ---
    incomplete_binding = {
        **_challenge(),
        "candidate_binding": {
            "run_id": RUN_ID,
            "source_rev": SOURCE_REV,
            "candidate_commit_sha": COMMIT_SHA,
        },
    }
    cases.append(
        (
            "candidate_binding missing a required field fails",
            _success_review(incomplete_binding),
            True,
        )
    )
    cases.append(
        (
            "candidate_binding equality mismatch at HALT_SUCCESS fails",
            _success_review(
                {**_challenge(), "candidate_binding": _binding(run_id="different-run")}
            ),
            True,
        )
    )
    # A minimal valid 3-entry panel with one resolvable stage-2 break -- used
    # only to exercise candidate_binding's equality scoping below.
    broke_panel = [
        _member(1),
        _member(
            2, outcome="broke", break_evidence=_normalized_evidence(STABLE_A), reason="broke it"
        ),
        _member(3),
    ]
    cases.append(
        (
            "candidate_binding shape required but NOT compared for equality on CONTINUE",
            _nonterminal_review(
                "CONTINUE",
                None,
                {
                    **_challenge(outcome="broke", panel=broke_panel),
                    "candidate_binding": _binding(run_id="unrelated-run-id"),
                },
                findings=[{"stable_id": STABLE_A}],
            ),
            False,
        )
    )

    # --- protocol_digest shape only ---
    cases.append(
        (
            "protocol_digest missing 'sha256:' prefix fails",
            _success_review({**_challenge(), "protocol_digest": "deadbeef" * 8}),
            True,
        )
    )
    cases.append(
        (
            "protocol_digest with uppercase hex fails",
            _success_review({**_challenge(), "protocol_digest": "sha256:" + "A" * 64}),
            True,
        )
    )

    # --- HALT_SUCCESS_candidate: unchanged from v4 ---
    cases.append(
        (
            "HALT_SUCCESS_candidate at v5 with null challenge passes (unchanged from v4)",
            _candidate_review(challenge=None),
            False,
        )
    )
    cases.append(
        (
            "HALT_SUCCESS_candidate at v5 with non-null challenge fails (unchanged from v4)",
            _candidate_review(challenge=_challenge()),
            True,
        )
    )

    # --- every other state requires null ---
    cases.append(
        (
            "HALT_LOOP_CAP with null halt_success_challenge passes",
            {
                "schema_version": 5,
                "state": "HALT_LOOP_CAP",
                "halt_subtype": None,
                "halt_success_challenge": None,
                "findings": [],
            },
            False,
        )
    )
    cases.append(
        (
            "HALT_LOOP_CAP with a non-null panel fails (not a panel-permitted state)",
            {
                "schema_version": 5,
                "state": "HALT_LOOP_CAP",
                "halt_subtype": None,
                "halt_success_challenge": _challenge(),
                "findings": [],
            },
            True,
        )
    )
    cases.append(
        (
            "HALT_STAGNATION/oscillation with a non-null panel fails (only user_decision/verification_blocked permitted)",
            {
                "schema_version": 5,
                "state": "HALT_STAGNATION",
                "halt_subtype": "oscillation",
                "halt_success_challenge": _challenge(),
                "findings": [],
            },
            True,
        )
    )
    cases.append(
        (
            "CONTINUE with a null challenge passes (a halt can have non-panel causes)",
            _nonterminal_review("CONTINUE", None, None),
            False,
        )
    )

    # --- candidate_fingerprint canonical digest preserved at v5 (ambiguous-decision case) ---
    cases.append(
        (
            "HALT_SUCCESS with candidate_fingerprint mismatch fails (v4 identity check preserved)",
            {**_success_review(_challenge()), "candidate_fingerprint": "wrong-fingerprint"},
            True,
        )
    )

    return cases


def main() -> int:
    va = _load_validator()
    failures: list[str] = []
    cases = _cases()

    for label, review, expect_fire in cases:
        issues = va.check_g32_halt_success_challenge(copy.deepcopy(review))
        fired = bool(issues)
        if fired != expect_fire:
            detail = "\n  " + "\n  ".join(i.message for i in issues) if issues else ""
            failures.append(
                f"{label}: expected {'FIRE' if expect_fire else 'PASS'}, got "
                f"{'FIRE' if fired else 'PASS'}{detail}"
            )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: G32 v5 panel shape gate holds across {len(cases)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
