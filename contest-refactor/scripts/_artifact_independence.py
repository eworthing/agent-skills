"""_artifact_independence.py — a terminal success resting on a non-independent challenge.

Found live, 2026-08-19, on a real BenchHype run: HALT_SUCCESS at loop 1, nine
dimensions all exactly 9.5 with accepted residuals, promoted by
`challenger_model: "inline-vetting (provider=unknown, no subagent spawn)"`. All 46
gates passed clean.

G32 requires `halt_success_challenge.challenger_model` to be a NON-EMPTY STRING and
nothing more, so an inline self-vet satisfies it exactly as well as an independently
spawned challenger does. Meanwhile `spawn_isolation` is already a typed enum
(`subagent | inline`, output-format-json.md:202) recording precisely the distinction
the gate ignores. The independence data is in the artifact; no gate reads it.

Why this matters more than the one run: halt-verifier.md grounds challenger
independence in *who spawns it* (main, not the Critic) and *fresh context*. Inline has
neither -- Critic and Challenger are the same agent in the same conversation. That is
the weakest possible reading of "an independent challenger held the verdict", and it is
what a reader of `state: HALT_SUCCESS` is entitled to assume did NOT happen.

On the run that surfaced this, the model volunteered an excellent provenance note of
its own accord ("structurally weaker than a fresh-context independent verification --
both Critic and Challenger ran in this same conversation"). That disclosure was
model-volunteered, not gate-enforced: a less careful model emits the same terminal with
no note and passes every gate. This check is the difference between lucky and reliable.

REAL ISSUES for CURRENT-epoch artifacts, backlog item [I1] item 1. Still print-only
for LEGACY (marker-less) artifacts -- unverified independence there stays a visible
warning, never a failure, per the retroactive-invalidation rule backlog item 30
records (G43/G46 added required v4 fields with no bump, so artifacts written before
them fail on fields that did not exist yet when they were written). See
_ruleset_epoch.py for the classifier and REQUIREMENT_EPOCHS["INDEPENDENCE_ISOLATION_FIELDS"]
for this requirement's epoch floor.

Two independent claims a terminal success rests on, both gated the same way:
  (a) terminal promotion (HALT_SUCCESS / HALT_SUCCESS_candidate) requires
      halt_success_challenge.challenger_isolation == "subagent"
  (b) an APPROVED implementation_review requires
      implementation_review.reviewer_isolation == "subagent"
Missing or "inline" fails either one, for CURRENT-epoch artifacts only. The
live-promotion half of this (the loop refusing to commit a violating terminal
mid-run, rather than a validator catching it after the fact) stays open --
this module is the validator side only, per the register.

Deliberately unnumbered (no G<n>): registering a gate forces a validation.md checklist
bullet, and validation.md is on the per-loop reload path with 20 tokens of apple
headroom. Same reasoning as _artifact_transitions.py's docstring.
"""

from __future__ import annotations

import _ruleset_epoch
from _artifact_core import Issue

_TERMINAL_SUCCESS = ("HALT_SUCCESS", "HALT_SUCCESS_candidate")
_REQUIREMENT = "INDEPENDENCE_ISOLATION_FIELDS"


def check_challenge_independence_report_only(current_review: dict) -> list[Issue]:
    """Flag a terminal success whose challenger (or approving reviewer) was not
    independently spawned. Real Issue at CURRENT epoch; print-only at LEGACY.

    Three challenger outcomes, because the middle one is what the first version of
    this check got wrong: it returned silently whenever top-level `spawn_isolation`
    was `subagent`, treating "the LOOP was isolated" as proof the CHALLENGE was.
    Those are different spawns. A real run (BenchHype, 2026-08-19) walked straight
    through that gap -- `spawn_isolation: subagent` with
    `implementation_review.spawn_mode: "inline (no subagent tool available in this
    opencode session)"`, because an opencode subagent cannot nest-spawn. The loop was
    isolated; the challenge that promoted it to HALT_SUCCESS was not.

      inline recorded    -> fires: the challenge shared the Critic's context
      subagent recorded  -> silent: independence is established
      neither recorded   -> UNVERIFIED: absence of evidence is not evidence of
                            independence, so it is reported (and, at CURRENT epoch,
                            failed) rather than passed
    """
    state = current_review.get("state")
    provider = current_review.get("provider") or "<unrecorded>"
    is_current_epoch = _ruleset_epoch.applies(_REQUIREMENT, current_review)
    fired: list[Issue] = []

    # --- (b) the implementation reviewer ------------------------------------
    # A terminal success rests on TWO verifications: the implementation reviewer
    # approving the change, and the challenger failing to break the candidate. An
    # inline reviewer is a self-review for the same reason an inline challenger is a
    # self-vet, so it is disclosed alongside rather than silently ignored.
    review = current_review.get("implementation_review") or {}
    reviewer_isolation = review.get("reviewer_isolation")
    verdict = review.get("verdict")
    if reviewer_isolation == "inline":
        print(
            f"[reviewer-independence state={state} provider={provider}] the implementation "
            f"review that approved this loop ran inline; its verdict shares the context it judges"
        )
    elif verdict == "approved" and reviewer_isolation != "subagent":
        # Absent on an APPROVED review -- same "absence is not evidence of
        # independence" reasoning as the challenger's unverified branch below.
        print(
            f"[reviewer-independence-unverified state={state} provider={provider}] "
            f"implementation_review.verdict == 'approved' but reviewer_isolation is absent; "
            f"independence is unverified, which is not the same as verified"
        )
    if verdict == "approved" and reviewer_isolation != "subagent" and is_current_epoch:
        fired.append(
            Issue(
                "reviewer-independence",
                f"implementation_review.verdict == 'approved' but reviewer_isolation="
                f"{reviewer_isolation!r} (must be 'subagent'): an approved review must be "
                f"independently spawned, not a self-review of the context it judges.",
            )
        )

    # --- (a) the terminal challenge -----------------------------------------
    if state not in _TERMINAL_SUCCESS:
        return fired
    if (current_review.get("schema_version") or 1) < 4:
        return fired

    challenge = current_review.get("halt_success_challenge") or {}
    model = challenge.get("challenger_model") or "<unrecorded>"
    challenger_isolation = challenge.get("challenger_isolation")
    loop_isolation = current_review.get("spawn_isolation")

    # The challenger's own record wins; the loop's isolation is a fallback signal
    # only because a loop that itself ran inline cannot have spawned anything.
    if challenger_isolation in ("subagent", "inline"):
        effective, source = challenger_isolation, "challenger_isolation"
    elif loop_isolation == "inline":
        effective, source = "inline", "spawn_isolation (the loop itself ran inline)"
    else:
        print(
            f"[challenge-independence-unverified state={state} provider={provider} "
            f"challenger_model={model!r}] halt_success_challenge.challenger_isolation is "
            f"absent, and spawn_isolation={loop_isolation!r} describes the LOOP spawn, not "
            f"the challenge. Independence is unverified, which is not the same as verified"
        )
        if is_current_epoch:
            fired.append(
                Issue(
                    "challenge-independence",
                    f"{state} promoted with halt_success_challenge.challenger_isolation "
                    f"absent (spawn_isolation={loop_isolation!r} describes the LOOP spawn, "
                    f"not the challenge): independence is unverified, which does not satisfy "
                    f"the requirement that it be established.",
                )
            )
        return fired

    if effective == "subagent":
        return fired

    print(
        f"[challenge-independence state={state} provider={provider} source={source} "
        f"challenger_model={model!r}] terminal success rests on a challenger that shared "
        f"the Critic's context; G32 checks challenger_model is non-empty and cannot see this"
    )
    if is_current_epoch:
        fired.append(
            Issue(
                "challenge-independence",
                f"{state} promoted by a challenge that ran inline (per {source}, provider="
                f"{provider}): no fresh-context verification backs the verdict. Re-run on a "
                f"provider whose subagents can nest-spawn, or treat the terminal as provisional "
                f"and say so in the handoff.",
            )
        )
    return fired
