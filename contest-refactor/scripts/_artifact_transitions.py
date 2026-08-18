"""_artifact_transitions.py — declarative state-transition legality (backlog item 12).

canon/states.toml (schema_version >= 2) carries a `transitions` table: for each
state, the set of legal next-states across a loop boundary, plus documentation
(`guards`, `gate`) for why each edge is legal. SKILL.md's Step 1 Routing +
Halting Conditions prose stays the instruction the model reads; this table is
the mechanical SSOT a validator can check without re-deriving the routing
logic from prose every time (see canon/states.toml's header comment for the
full guard-vocabulary + known-limitation writeup).

Event source: the observed per-loop state sequence is read from
REVIEW_HISTORY.json.loops[] (schema_version >= 2 — see
references/output-format-state-schemas.md § REVIEW_HISTORY.json schema). Each
entry's `state` is the loop's FINAL persisted state (Step 3 wrap-up overrides,
e.g. HALT_LOOP_CAP at loop == loop_cap, land in the same entry — there is no
separate pre-override snapshot). G18 requires the last entry to equal
CURRENT_REVIEW.json verbatim, so CURRENT_REVIEW.json never needs to be
appended separately. Only PAIRS of entries with adjacent loop numbers
(loop_b == loop_a + 1) are checked; a fixture that samples non-consecutive
loop numbers (a minimal repro for an unrelated gate) is skipped rather than
misread as a real transition.

--- The flip switch -------------------------------------------------------
Shadow-first (this change, per repo convention — mirrors
common/scripts/eval_guard.py's REPORT_ONLY idiom): every illegal transition
prints a '[transition-violation ...]' line, but check_transition_report_only
always returns an empty Issue list, so it can never fail validate-artifact.py
--mode strict or block validate-fixtures.py. Flip REPORT_ONLY to False below
to make it return a real Issue instead. This is the ONE place that decision
is made.
---------------------------------------------------------------------------

Deliberately unnumbered (no G<n> id): validation.md and canon/validation-gates.toml
are on the loop's per-loop reload path (token-budget.py's `loop` ceiling, see
SKILL.md § Reference Load Matrix), and that ceiling had 3 tokens of headroom
when this shipped. Registering a gate would force a validation.md checklist
bullet (validate-repo.py's check_gate_sequencing requires every canon gate id
referenced there) purely to describe a check the Critic never has to run by
hand — the validator runs it unconditionally. `check_continue_backlog` in
_artifact_core.py (rule id "CONTINUE") is the existing precedent for a
structural check with no G-number. This one's rule id is "transition-legality".
"""

from __future__ import annotations

from itertools import pairwise

from _artifact_core import Issue

REPORT_ONLY = True


def observed_transitions(review_history: dict | None) -> list[tuple[int, str, int, str]]:
    """(loop_a, state_a, loop_b, state_b) for every loop-number-adjacent pair
    in REVIEW_HISTORY.json.loops[], in array order.
    """
    if not review_history:
        return []
    loops = review_history.get("loops")
    if not isinstance(loops, list):
        return []
    pairs: list[tuple[int, str, int, str]] = []
    for a, b in pairwise(loops):
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        loop_a, state_a = a.get("loop"), a.get("state")
        loop_b, state_b = b.get("loop"), b.get("state")
        if not isinstance(loop_a, int) or not isinstance(loop_b, int):
            continue
        if loop_b != loop_a + 1:
            continue  # numbering gap (e.g. a minimal fixture) -- not a real pair
        pairs.append((loop_a, state_a, loop_b, state_b))
    return pairs


def check_transition_report_only(review_history: dict | None, canon) -> list[Issue]:
    """Print a diagnostic line for every observed transition absent from
    canon/states.toml's transition table. Report-only: see module docstring.
    """
    transitions = (getattr(canon, "extra", {}) or {}).get("transitions", {})
    fired: list[Issue] = []
    for loop_a, state_a, loop_b, state_b in observed_transitions(review_history):
        edges = (transitions.get(state_a) or {}).get("edges") or []
        legal_targets = {e.get("to") for e in edges if isinstance(e, dict)}
        if state_b in legal_targets:
            continue
        reason = (
            "terminal state has no legal next state"
            if not edges
            else f"no declared edge {state_a!r} -> {state_b!r} in canon/states.toml"
        )
        print(f"[transition-violation {state_a}→{state_b} reason={reason} loop={loop_a}->{loop_b}]")
        fired.append(
            Issue(
                "transition-legality",
                f"loop {loop_a} ({state_a}) -> loop {loop_b} ({state_b}): {reason}",
            )
        )
    if REPORT_ONLY:
        return []
    return fired
