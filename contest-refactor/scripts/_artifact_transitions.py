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
separate pre-override snapshot). G18 requires a same-loop HALT_SUCCESS promotion
to replace its candidate snapshot, so cross-loop legality normalizes that final
state back to HALT_SUCCESS_candidate; G21/G32 validate the promotion itself.
CURRENT_REVIEW.json never needs to be appended separately. Only PAIRS of
entries with adjacent loop numbers (loop_b == loop_a + 1) are checked; a
fixture that samples non-consecutive loop numbers (a minimal repro for an
unrelated gate) is skipped rather than misread as a real transition.

--- Enforcement (backlog item [I1] item 2) ---------------------------------
Was a global shadow-first flag (every illegal transition printed, the function
always returned []). Now epoch-scoped instead of globally switched: an illegal
transition in a CURRENT-epoch artifact's history is a real Issue; the same
violation in a LEGACY (marker-less) artifact still only prints, per the
retroactive-invalidation rule (`_ruleset_epoch.py`,
REQUIREMENT_EPOCHS["TRANSITIONS_REQUIRED_FIELDS"]) -- canon/states.toml's
transition table existed before skill_rev did, but this checker only started
reading it as a hard gate after [I1], so a marker-less artifact cannot be
proven to have run under a ruleset that enforced it.
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

import _ruleset_epoch
from _artifact_core import Issue

# The run-boundary rule already exists and is already tested; a second copy here
# would be a second thing to keep correct. coverage_ledger has no import-time
# side effects (argparse lives under __main__).
from coverage_ledger import split_runs

_REQUIREMENT = "TRANSITIONS_REQUIRED_FIELDS"


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
    # Pair only WITHIN a run. REVIEW_HISTORY.json legitimately holds several runs
    # -- `--reset` starts a new one -- and the state machine restarts at each
    # boundary, so the last loop of one run does not transition into the first
    # loop of the next. Measured on a real repo: a run that ended terminal
    # HALT_SUCCESS, then `--reset`, reported a bogus
    # HALT_SUCCESS -> HALT_SUCCESS_candidate violation. The loop-adjacency guard
    # below did not catch it because the numbering happened to stay contiguous
    # across the boundary, which is precisely when it looks most like a real pair.
    for run in split_runs(review_history):
        for a, b in pairwise(run):
            if not isinstance(a, dict) or not isinstance(b, dict):
                continue
            loop_a, state_a = a.get("loop"), a.get("state")
            loop_b, state_b = b.get("loop"), b.get("state")
            if not isinstance(loop_a, int) or not isinstance(loop_b, int):
                continue
            if loop_b != loop_a + 1:
                continue  # numbering gap (e.g. a minimal fixture) -- not a real pair
            transition_state_b = "HALT_SUCCESS_candidate" if state_b == "HALT_SUCCESS" else state_b
            pairs.append((loop_a, state_a, loop_b, transition_state_b))
    return pairs


def check_transition_report_only(
    current_review: dict, review_history: dict | None, canon
) -> list[Issue]:
    """Print a diagnostic line for every observed transition absent from
    canon/states.toml's transition table; return it as a real Issue when
    `current_review` classifies CURRENT-epoch, print-only otherwise. See
    module docstring.

    `current_review` (not the tail of `review_history`) is what decides the
    epoch, matching the classifier's own contract and the `check_g43_*`/
    `check_g46_*` precedent -- G18 already requires `review_history.loops[-1]`
    to equal `current_review` verbatim, so the two never disagree on a valid
    artifact, but only one of them is the classifier's documented input.
    """
    transitions = (getattr(canon, "extra", {}) or {}).get("transitions", {})
    is_current_epoch = _ruleset_epoch.applies(_REQUIREMENT, current_review)
    fired: list[Issue] = []
    observed = observed_transitions(review_history)

    # A check that derives nothing from a history with loops in it has not passed
    # -- it has failed to run, and report-only mode would hide that as silence.
    # The live case: `run_id` is specified as run-scoped ("identifies the loop run
    # that produced the candidate", example `run-2026-06-21-0a1b…`), but a loop that
    # mints a fresh id per loop makes split_runs see one run per loop, leaving no
    # adjacent pair anywhere. Same discipline as exit code 2 elsewhere in this
    # repo: cannot-measure is its own outcome, never a clean result.
    loops = (review_history or {}).get("loops")
    if (
        isinstance(loops, list)
        and len([x for x in loops if isinstance(x, dict)]) >= 2
        and not observed
    ):
        print(
            "[transition-check-blind reason=no adjacent in-run pair derived "
            f"loops={len(loops)} runs={len(split_runs(review_history or {}))} "
            "hint=run_id must be stable across the loops of one run]"
        )

    for loop_a, state_a, loop_b, state_b in observed:
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
        if is_current_epoch:
            fired.append(
                Issue(
                    "transition-legality",
                    f"loop {loop_a} ({state_a}) -> loop {loop_b} ({state_b}): {reason}",
                )
            )
    return fired
