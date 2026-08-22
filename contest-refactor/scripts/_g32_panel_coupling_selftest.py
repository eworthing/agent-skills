#!/usr/bin/env python3
"""Aggregate/state-coupling self-test for G32's v5 panel extension -- Tier 1 of
Recommendation 1 (plans/rec1-panel-certification.md).

Structural/shape cases (version boundary, panel length/member_index, member
shape, retry envelope, token_usage, break_evidence normalized-form fields,
candidate_binding, protocol_digest) live in _g32_panel_selftest.py -- split out
when that file crossed the 800-line module cap. Builders shared by both live in
_g32_panel_testkit.py.

This file covers: the aggregate outcome <-> state/halt_subtype coupling table
(held/broke/blocked/pending), the pending route's raw-break-evidence and
open_question_for_user requirements, and the rule #6 exception (d)
findings-count/dedup rule aggregate 'broke' owes.

A few cases are load-bearing because they pin decisions the plan flags as easy to
get wrong:
  - "two members dedup to one stable_id" / "findings[] count exceeds distinct
    referenced break ids" pin the panel-keyed half of rule #6 exception (d): the
    findings[] count must equal the number of DISTINCT stable_ids the panel's
    breaks resolve to, not the number of breaking members. (A third break is not
    constructible here: a 3-entry panel requires member 1 held, so at most
    members 2/3 break -- see _g32_panel_selftest.py's converse case.)
  - "normalized break_evidence under aggregate pending fails" pins that the raw/
    normalized dispatch is AGGREGATE-driven, not shape-driven: a normalized-looking
    record under a pending aggregate must still be rejected as not-raw.
  - "aggregate pending without open_question_for_user fails" pins the fourth leg
    of the plan's raw-acceptance condition for a pending aggregate.

Run: python3 scripts/_g32_panel_coupling_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import sys

import _g32_panel_testkit

_load_validator = _g32_panel_testkit._load_validator
_normalized_evidence = _g32_panel_testkit._normalized_evidence
_raw_finding = _g32_panel_testkit._raw_finding
_member = _g32_panel_testkit._member
_challenge = _g32_panel_testkit._challenge
_success_review = _g32_panel_testkit._success_review
_nonterminal_review = _g32_panel_testkit._nonterminal_review
_retry_attempt = _g32_panel_testkit._retry_attempt
STABLE_A = _g32_panel_testkit.STABLE_A
STABLE_B = _g32_panel_testkit.STABLE_B


def _cases():
    """(label, review, expect_fire)"""
    cases: list[tuple[str, dict, bool]] = []

    # --- aggregate/state coupling ---
    cases.append(
        (
            "unanimous 3x held at HALT_SUCCESS passes",
            _success_review(_challenge(outcome="held")),
            False,
        )
    )
    cases.append(
        (
            "aggregate held with a member broke fails",
            _success_review(
                _challenge(
                    outcome="held",
                    panel=[
                        _member(1),
                        _member(2, outcome="broke", break_evidence=_normalized_evidence()),
                        _member(3),
                    ],
                )
            ),
            True,
        )
    )
    broke_panel = [
        _member(1),
        _member(
            2, outcome="broke", break_evidence=_normalized_evidence(STABLE_A), reason="broke it"
        ),
        _member(3),
    ]
    cases.append(
        (
            "aggregate broke at CONTINUE passes",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(outcome="broke", panel=broke_panel),
                findings=[{"stable_id": STABLE_A}],
            ),
            False,
        )
    )
    cases.append(
        (
            "aggregate broke at HALT_STAGNATION/user_decision passes (Stop/Ask route)",
            _nonterminal_review(
                "HALT_STAGNATION",
                "user_decision",
                _challenge(outcome="broke", panel=broke_panel),
                findings=[{"stable_id": STABLE_A}],
            ),
            False,
        )
    )
    cases.append(
        (
            "aggregate broke at a state outside {CONTINUE, HALT_STAGNATION/user_decision} fails",
            _nonterminal_review(
                "HALT_STAGNATION",
                "no_progress",
                _challenge(outcome="broke", panel=broke_panel),
                findings=[{"stable_id": STABLE_A}],
            ),
            True,
        )
    )
    # Member 1 must be held -- stage 2 (members 2/3) only launches after a hold,
    # so a 'blocked' aggregate (fewer than 3 usable verdicts) needs member 1 held
    # and at least one of 2/3 exhausting its retry envelope.
    blocked_panel = [
        _member(1, outcome="held"),
        _member(
            2,
            outcome="unavailable",
            reason="exhausted",
            retry_count=2,
            retry_cause="timeout",
            retry_attempts=[_retry_attempt(1, "timeout"), _retry_attempt(2, "timeout")],
        ),
        _member(
            3,
            outcome="unavailable",
            reason="exhausted",
            retry_count=2,
            retry_cause="spawn_error",
            retry_attempts=[_retry_attempt(1, "spawn_error"), _retry_attempt(2, "ok")],
        ),
    ]
    cases.append(
        (
            "aggregate blocked at HALT_STAGNATION/verification_blocked passes",
            _nonterminal_review(
                "HALT_STAGNATION",
                "verification_blocked",
                _challenge(outcome="blocked", panel=blocked_panel),
            ),
            False,
        )
    )
    cases.append(
        (
            "aggregate blocked with 3 held members fails (a full hold is 'held', not 'blocked')",
            _nonterminal_review(
                "HALT_STAGNATION",
                "verification_blocked",
                _challenge(outcome="blocked", panel=[_member(1), _member(2), _member(3)]),
            ),
            True,
        )
    )
    # Member 1 held: a pending aggregate with a 3-entry panel can only arise from
    # a stage-2 break hitting the ambiguous registry match. (A member-1 ambiguous
    # break yields a 1-entry pending panel instead -- members 2/3 never launch.)
    pending_panel = [
        _member(1),
        _member(
            2,
            outcome="broke",
            break_evidence={
                "finding": _raw_finding(),
                "spt": {"result": "passed", "rationale": "ambiguous match"},
            },
            normalization="pending_user_decision",
            reason="ambiguous registry match",
        ),
        _member(
            3,
            outcome="broke",
            break_evidence={
                "finding": _raw_finding("Second distinct issue"),
                "spt": {"result": "passed", "rationale": "confirmed"},
            },
            normalization="deferred_by_pending_registry_decision",
            reason="valid sibling break",
        ),
    ]
    cases.append(
        (
            "aggregate pending at HALT_STAGNATION/user_decision, findings[] empty, raw markers: passes",
            _nonterminal_review(
                "HALT_STAGNATION",
                "user_decision",
                _challenge(outcome="pending", panel=pending_panel),
                findings=[],
            ),
            False,
        )
    )
    cases.append(
        (
            "aggregate pending with non-empty findings[] fails",
            _nonterminal_review(
                "HALT_STAGNATION",
                "user_decision",
                _challenge(outcome="pending", panel=pending_panel),
                findings=[{"stable_id": "F-999"}],
            ),
            True,
        )
    )
    # The plan's raw-acceptance condition has FOUR legs; this pins the fourth.
    no_question = _nonterminal_review(
        "HALT_STAGNATION",
        "user_decision",
        _challenge(outcome="pending", panel=pending_panel),
        findings=[],
    )
    no_question["open_question_for_user"] = None
    cases.append(
        (
            "aggregate pending without open_question_for_user fails",
            no_question,
            True,
        )
    )
    # Member 1 must be held for a 3-entry panel; the ambiguous member is stage-2.
    normalized_under_pending = [
        _member(1, outcome="held"),
        _member(
            2,
            outcome="broke",
            break_evidence=_normalized_evidence(),
            normalization="pending_user_decision",
            reason="ambiguous",
        ),
        _member(3, outcome="held"),
    ]
    cases.append(
        (
            "normalized break_evidence under aggregate pending fails (must stay raw)",
            _nonterminal_review(
                "HALT_STAGNATION",
                "user_decision",
                _challenge(outcome="pending", panel=normalized_under_pending),
                findings=[],
            ),
            True,
        )
    )

    # --- aggregate broke: findings count / dedup (rule #6 exception (d), panel half) ---
    dedup_panel = [
        _member(1),
        _member(
            2, outcome="broke", break_evidence=_normalized_evidence(STABLE_A), reason="found it"
        ),
        _member(
            3, outcome="broke", break_evidence=_normalized_evidence(STABLE_A), reason="found it too"
        ),
    ]
    cases.append(
        (
            "two members dedup to one stable_id: findings has 1 entry, passes",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(outcome="broke", panel=dedup_panel),
                findings=[{"stable_id": STABLE_A}],
            ),
            False,
        )
    )
    # Isolates the distinct-id-count comparison itself. Both existing dedup cases
    # above pass, and the RED ones below trip a DIFFERENT check first (per-member
    # "finding_stable_id not in findings[]", or the {1,2} cap), so deleting the
    # `len(stable_ids) != findings_count` comparison left the whole suite green.
    # Here every other leg holds -- STABLE_A is present in findings[], and
    # findings_count 2 is inside the {1,2} cap -- so only the count mismatch fires.
    cases.append(
        (
            "two members dedup to one stable_id but findings has 2 entries: fails",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(outcome="broke", panel=dedup_panel),
                findings=[{"stable_id": STABLE_A}, {"stable_id": "F-999"}],
            ),
            True,
        )
    )
    distinct_panel = [
        _member(1),
        _member(
            2, outcome="broke", break_evidence=_normalized_evidence(STABLE_A), reason="found A"
        ),
        _member(
            3, outcome="broke", break_evidence=_normalized_evidence(STABLE_B), reason="found B"
        ),
    ]
    cases.append(
        (
            "two distinct stage-2 breaks: findings has 2 entries, passes",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(outcome="broke", panel=distinct_panel),
                findings=[{"stable_id": STABLE_A}, {"stable_id": STABLE_B}],
            ),
            False,
        )
    )
    cases.append(
        (
            "findings[] count not matching distinct stable_ids referenced fails",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(outcome="broke", panel=distinct_panel),
                findings=[{"stable_id": STABLE_A}, {"stable_id": "F-999"}],
            ),
            True,
        )
    )
    # A 3-entry panel caps at 2 breaks (members 2/3; member 1 must be held), so
    # the {1,2} findings cap is violated via a findings[] that outruns the
    # distinct referenced break ids -- not via an unconstructible third break.
    two_breaks_three_findings = [
        _member(1),
        _member(2, outcome="broke", break_evidence=_normalized_evidence("F-020"), reason="b"),
        _member(3, outcome="broke", break_evidence=_normalized_evidence("F-021"), reason="c"),
    ]
    cases.append(
        (
            "findings[] count exceeds distinct referenced break ids and the {1,2} cap",
            _nonterminal_review(
                "CONTINUE",
                None,
                _challenge(outcome="broke", panel=two_breaks_three_findings),
                findings=[{"stable_id": "F-020"}, {"stable_id": "F-021"}, {"stable_id": "F-022"}],
            ),
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
    print(f"OK: G32 v5 panel coupling gate holds across {len(cases)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
