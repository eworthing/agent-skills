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

REPORT-ONLY, deliberately. Making it a hard failure would require a new required field
or a coupling the schema cannot express at the current version, which is exactly the
retroactive-invalidation defect backlog item 30 records (G43/G46 added required v4
fields with no bump, so artifacts written before them now fail). Per
references/output-format-migrations.md, the legal routes are bump-and-default-fill,
scope-by-skill_rev, or optional-with-shape-gating -- and none is warranted before the
signal is measured. So this prints and returns no Issue, mirroring
_artifact_transitions.py. Flip REPORT_ONLY to False once there is evidence.

Deliberately unnumbered (no G<n>): registering a gate forces a validation.md checklist
bullet, and validation.md is on the per-loop reload path with 20 tokens of apple
headroom. Same reasoning as _artifact_transitions.py's docstring.
"""

from __future__ import annotations

from _artifact_core import Issue

REPORT_ONLY = True

_TERMINAL_SUCCESS = ("HALT_SUCCESS", "HALT_SUCCESS_candidate")


def check_challenge_independence_report_only(current_review: dict) -> list[Issue]:
    """Flag a terminal success promoted by a challenger that was not independently spawned."""
    state = current_review.get("state")
    if state not in _TERMINAL_SUCCESS:
        return []
    if (current_review.get("schema_version") or 1) < 4:
        return []

    isolation = current_review.get("spawn_isolation")
    if isolation != "inline":
        return []

    challenge = current_review.get("halt_success_challenge") or {}
    model = challenge.get("challenger_model") or "<unrecorded>"
    provider = current_review.get("provider") or "<unrecorded>"
    print(
        f"[challenge-independence state={state} spawn_isolation=inline provider={provider} "
        f"challenger_model={model!r}] terminal success rests on a challenger that shared the "
        f"Critic's context; G32 checks challenger_model is non-empty and cannot see this"
    )
    fired = [
        Issue(
            "challenge-independence",
            f"{state} promoted under spawn_isolation='inline' (provider={provider}): the "
            f"challenge was not independently spawned, so the verdict carries no fresh-context "
            f"verification. Re-run on a provider with subagent spawn, or treat the terminal as "
            f"provisional and say so in the handoff.",
        )
    ]
    if REPORT_ONLY:
        return []
    return fired
