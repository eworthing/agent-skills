#!/usr/bin/env python3
"""Self-test: canon/states.toml's declarative transition table (backlog item 12).

Before item 12, every transition rule -- which flag routes where, which state may
follow which -- lived only in SKILL.md's Step 1 Routing prose, and legality was
inferred after the fact from the artifact that resulted (G9's presence table,
G34's HALT-tail, G35's handoff shape). canon/states.toml schema_version 2 makes
the machine readable: `transitions.<state>.edges[]` declares the legal next
states, and _artifact_transitions.py answers "was this transition legal?"
mechanically off REVIEW_HISTORY.json's loop-indexed state sequence.

This file guards the table's own integrity plus the checker's behavior on the
two committed fixtures. It deliberately checks the guard vocabulary in BOTH
directions (canon/states.toml's header commits to this): an edge citing an
unknown token is a typo, and a declared token no edge uses is vocabulary that
outlived its rule -- the same "retired prose stays retired" hygiene
_retired_prose_selftest.py applies to reference text.

Enforcement is now epoch-scoped (backlog item [I1] item 2), not a single global
flag: check_transition_report_only always prints its `[transition-violation ...]`
diagnostics, but only returns a real Issue for a CURRENT-epoch `current_review`
(skill_rev present and shaped like a short SHA -- see _ruleset_epoch.py). A
LEGACY (marker-less) artifact's violation still prints and returns no Issue,
matching the original shadow-first behavior.

Run: python3 scripts/_transition_table_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import _artifact_transitions as trans
import _ruleset_epoch as epoch
from _canon import load_canon

FIXTURES = SKILL_ROOT / "evals" / "fixtures"
LEGAL_FIXTURE = FIXTURES / "transition-legal-multiloop"
ILLEGAL_FIXTURE = FIXTURES / "transition-illegal-post-cap-continue"

_LEGACY_REVIEW = {"schema_version": 3}  # no skill_rev -> LEGACY epoch


def _history(fixture_dir: Path) -> dict:
    return json.loads((fixture_dir / "REVIEW_HISTORY.json").read_text(encoding="utf-8"))


def _current_review(fixture_dir: Path) -> dict:
    return json.loads((fixture_dir / "CURRENT_REVIEW.json").read_text(encoding="utf-8"))


def _run_check(current_review: dict, history: dict, canon) -> tuple[list, str]:
    """Return (issues, captured stdout) for one check_transition_report_only call."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        issues = trans.check_transition_report_only(current_review, history, canon)
    return issues, buf.getvalue()


def main() -> int:
    failures: list[str] = []
    canon = load_canon(SKILL_ROOT)
    extra = canon.extra
    states = set(canon.states)
    transitions = extra.get("transitions") or {}
    guards = tuple(extra.get("transition_guards") or ())

    # --- schema ----------------------------------------------------------
    if extra.get("states_schema_version", 1) < 2:
        failures.append(
            "states.toml schema_version < 2: the transition table is the v2 addition, "
            "so a v1 file means the table is absent or the loader stopped reading it"
        )
    if not transitions:
        failures.append("canon/states.toml declares no `transitions` table")
    if not guards:
        failures.append("canon/states.toml declares no `guards` vocabulary")

    # --- referential integrity -------------------------------------------
    for state, entry in transitions.items():
        if state not in states:
            failures.append(
                f"transitions.{state} is not a member of `states` -- a renamed state "
                f"leaves an orphan table entry no artifact can ever match"
            )
        for edge in (entry or {}).get("edges") or []:
            target = edge.get("to")
            if target not in states:
                failures.append(f"transitions.{state} edge targets unknown state {target!r}")

    # --- closed guard enum, both directions -------------------------------
    used: set[str] = set()
    for state, entry in transitions.items():
        for edge in (entry or {}).get("edges") or []:
            edge_guards = edge.get("guards") or []
            if not edge_guards:
                failures.append(
                    f"transitions.{state} -> {edge.get('to')!r} declares no guards; every "
                    f"edge must document why it is legal"
                )
            for token in edge_guards:
                used.add(token)
                if token not in guards:
                    failures.append(
                        f"transitions.{state} -> {edge.get('to')!r} cites guard {token!r}, "
                        f"which is not in the closed `guards` enum"
                    )
    for token in guards:
        if token not in used:
            failures.append(
                f"guard {token!r} is declared but no edge uses it -- vocabulary that "
                f"outlived its rule; delete it or wire the edge that needs it"
            )

    # --- terminal states stay terminal ------------------------------------
    for state in states:
        if state.startswith("HALT_") and state != "HALT_SUCCESS_candidate":
            edges = (transitions.get(state) or {}).get("edges") or []
            if edges:
                failures.append(
                    f"{state} declares outgoing edges, but SKILL.md's Continuation "
                    f"Discipline stops the run at a terminal halt"
                )

    # --- observed-sequence derivation on the committed fixtures -----------
    legal_history = _history(LEGAL_FIXTURE)
    pairs = trans.observed_transitions(legal_history)
    if len(pairs) < 2:
        failures.append(
            f"{LEGAL_FIXTURE.name}: expected >=2 adjacent loop pairs, derived {len(pairs)} "
            f"-- the fixture or the derivation stopped seeing the loop sequence"
        )
    _, legal_out = _run_check(_current_review(LEGAL_FIXTURE), legal_history, canon)
    if "[transition-violation" in legal_out:
        failures.append(
            f"{LEGAL_FIXTURE.name}: an all-CONTINUE run fired a violation "
            f"(restraint twin must stay silent): {legal_out.strip()}"
        )

    illegal_history = _history(ILLEGAL_FIXTURE)
    illegal_current = _current_review(ILLEGAL_FIXTURE)
    illegal_issues, illegal_out = _run_check(illegal_current, illegal_history, canon)
    fired = illegal_out.count("[transition-violation")
    if fired != 1:
        failures.append(
            f"{ILLEGAL_FIXTURE.name}: expected exactly 1 violation line for the "
            f"(HALT_LOOP_CAP -> CONTINUE) pair, got {fired}: {illegal_out.strip()!r}"
        )
    if "HALT_LOOP_CAP" not in illegal_out or "terminal" not in illegal_out:
        failures.append(
            f"{ILLEGAL_FIXTURE.name}: the violation line must name the offending state and "
            f"why it is illegal; got {illegal_out.strip()!r}"
        )

    # --- epoch-gated enforcement (backlog item [I1] item 2) -----------------
    # The committed fixture now carries skill_rev (repaired as part of [I1]),
    # so it classifies CURRENT and the same violation must be a real Issue.
    if epoch.classify(illegal_current) != epoch.CURRENT:
        failures.append(
            f"{ILLEGAL_FIXTURE.name}'s CURRENT_REVIEW.json must classify CURRENT-epoch "
            f"post-[I1] repair (missing/malformed skill_rev?)"
        )
    if not any(i.rule == "transition-legality" for i in illegal_issues):
        failures.append(
            f"a CURRENT-epoch artifact's illegal transition must fire a real "
            f"transition-legality Issue; got {[i.rule for i in illegal_issues]}"
        )

    # The identical violation on a LEGACY (marker-less) artifact must still
    # print-only, matching the pre-[I1] shadow behavior exactly.
    legacy_issues, legacy_out = _run_check(_LEGACY_REVIEW, illegal_history, canon)
    if legacy_issues:
        failures.append(
            f"a LEGACY-epoch artifact's illegal transition must return no Issue "
            f"(print-only); got {[i.rule for i in legacy_issues]}"
        )
    if "[transition-violation" not in legacy_out:
        failures.append("a LEGACY-epoch illegal transition must still print its diagnostic")

    # --- a `--reset` boundary is not a transition ---------------------------
    # REVIEW_HISTORY.json legitimately holds several runs; --reset starts a new
    # one and the state machine restarts with it. Measured on a real repo: a run
    # that ended terminal HALT_SUCCESS, then --reset, then a fresh run reported a
    # bogus HALT_SUCCESS -> HALT_SUCCESS_candidate violation. The loop-adjacency
    # guard missed it because the numbering stayed contiguous across the
    # boundary -- exactly when a cross-run pair looks most like a real one.
    reset_history = {
        "loops": [
            {"loop": 1, "run_id": "run-A", "state": "HALT_SUCCESS"},
            {"loop": 2, "run_id": "run-B", "state": "HALT_SUCCESS_candidate"},
        ]
    }
    if trans.observed_transitions(reset_history):
        failures.append(
            "a run_id change is a --reset boundary, not a transition: "
            f"observed_transitions paired across it -> {trans.observed_transitions(reset_history)}"
        )
    _, reset_out = _run_check(_LEGACY_REVIEW, reset_history, canon)
    if "transition-violation" in reset_out:
        failures.append(f"cross-run pair reported a violation: {reset_out.strip()!r}")

    # The same two states WITHIN one run must still fire -- otherwise the fix
    # above silences the check rather than scoping it.
    same_run = {
        "loops": [
            {"loop": 1, "run_id": "run-A", "state": "HALT_SUCCESS"},
            {"loop": 2, "run_id": "run-A", "state": "HALT_SUCCESS_candidate"},
        ]
    }
    _, same_out = _run_check(_LEGACY_REVIEW, same_run, canon)
    if "transition-violation" not in same_out:
        failures.append(
            "scoping by run silenced a real in-run violation: "
            "HALT_SUCCESS -> HALT_SUCCESS_candidate within run-A must still fire"
        )

    # --- deriving nothing is not passing -----------------------------------
    # Scoping by run is one edit away from muting the check, and the dangerous
    # version is not a deliberate edit -- it is data. `run_id` is specified
    # run-scoped, but a loop that mints a fresh id per loop makes split_runs see
    # one run per loop, so no pair exists anywhere and report-only mode renders
    # that as silence. Observed live: a real run archived `run-2026-08-20-001`
    # then `loop-2-302837137`.
    per_loop_ids = {
        "loops": [
            {"loop": 1, "run_id": "loop-1-aaaaaaa", "state": "HALT_LOOP_CAP"},
            {"loop": 2, "run_id": "loop-2-bbbbbbb", "state": "CONTINUE"},
            {"loop": 3, "run_id": "loop-3-ccccccc", "state": "CONTINUE"},
        ]
    }
    _, blind_out = _run_check(_LEGACY_REVIEW, per_loop_ids, canon)
    if "transition-check-blind" not in blind_out:
        failures.append(
            "a history whose run_id changes every loop leaves no in-run pair, so the "
            "check cannot run -- that must be announced, not rendered as silence: "
            f"got {blind_out.strip()!r}"
        )

    # ...and a history the check CAN read must not cry blind.
    _, quiet_out = _run_check(_LEGACY_REVIEW, legal_history, canon)
    if "transition-check-blind" in quiet_out:
        failures.append(
            f"the legal multiloop fixture is readable; blind must not fire: {quiet_out.strip()!r}"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: transition table v{extra.get('states_schema_version')} -- "
        f"{len(transitions)} states, {len(guards)} guards all used, targets resolve, "
        f"terminals closed; fixtures: legal silent, illegal fires 1 line, report-only holds"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
