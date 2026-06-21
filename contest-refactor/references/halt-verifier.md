# HALT_SUCCESS Verifier (the challenger)

The independent adjudication of a terminal `HALT_SUCCESS`. The loop never emits
terminal success directly; it emits `HALT_SUCCESS_candidate`, and the **main
orchestrator** spawns a cold challenger that tries to *break* the verdict. Only a
held challenge promotes the candidate to `HALT_SUCCESS` (gated by G32).

This is the complement to the Step-3 reviewer ([implementation-reviewer.md](implementation-reviewer.md)),
which is skipped on HALT loops — so without this pass a terminal success would get
**zero** independent review.

## Contents

- [When it runs](#when-it-runs)
- [Why a cold, main-owned agent](#why-a-cold-main-owned-agent)
- [Spawn (read-only)](#spawn-read-only)
- [The challenge — break the verdict](#the-challenge--break-the-verdict)
- [Outcome routing (main applies)](#outcome-routing-main-applies)
- [Output contract](#output-contract)
- [Oscillation](#oscillation)

## When it runs

In Step 1 routing, when the loop subagent returns `system_flag: HALT_SUCCESS_candidate`.
The candidate review is already committed (so the verdict survives a restart). The
main agent — not the loop subagent — runs the challenger before any terminal
`HALT_SUCCESS` is written. Fires at most once per terminal attempt.

## Why a cold, main-owned agent

The Critic that produced the all-9.5 scorecard cannot adjudicate it: G21, the
Residual Accounting Pass, and the Adversarial Pass on Accepted Residuals are all
self-administered by that same Critic. A field-presence gate alone would let the
Critic synthesize its own `halt_success_challenge`. **Independence is structural:
the main orchestrator owns the spawn**, and G32 binds the recorded challenge to
the candidate (`run_id`, `source_rev`, `candidate_commit_sha`). The challenger
never sees — and is never told — that its job is to confirm; its job is to break.

## Spawn (read-only)

Reuse the reviewer read-only spawn profile in
[provider-adapters.md § Challenger-spawn profile](provider-adapters.md). Transport,
the retry envelope, and the JSON-return discipline are identical to the Step-3
reviewer ([implementation-reviewer.md § Failure modes](implementation-reviewer.md));
only the prompt and the verdict semantics below differ. Same model tier as the
loop subagent (fresh eyes need equal capability).

Main hands the challenger: the candidate scorecard, every `accepted` residual + its
rationale, the source roots, the lens, and the binding triple
(`run_id`, `source_rev`, `candidate_commit_sha`).

## The challenge — break the verdict

Produce ONE of these, or report the verdict held:

- **`new_finding`** — one **Serious-or-worse** finding with a full Evidence Chain
  (Claim → Source → Consequence → Remedy per [method.md](method.md)) that **passes
  the Simplify Pressure Test**. Serious-or-worse is the bar because a Noticeable
  weakness is already compatible with a 9.5 accepted residual (architecture-rubric
  Terminal Normalization) — blocking on it would contradict the 9.5 threshold and
  loop forever.
- **`residual_refutation`** — disprove one `accepted` residual's documented
  acceptance premise by naming a concrete subtractive fix that passes the Simplify
  Pressure Test (the residual was mis-accepted; its dimension cannot sit at 9.5+).

**Anti-self-referential (shared with the Step-3 self-imposed-rule audit):** a
finding whose only evidence is "the code obeys project rule HR-X" is **not**
Serious-or-worse and does **not** break the verdict. Project-rule compliance is the
expected state, inert as a break. The 9-anchor is earned by structure surviving
source inspection, not by compliance proof.

**The inverse trap is just as fatal — do not let a compliance rationale stop you.**
When an accepted residual is *justified by* rule-compliance ("`state_management`
9.5 — follows HR-1, single owner"), **verify the claim against the actual
structure** before accepting it. A hollow compliance claim is *itself* the break:
if the residual says "single owner per HR-1" while three sites write the field, the
compliance rationale is fake-clean reward and you have a Serious ownership finding.
Never accept a residual's compliance rationale at face value — re-derive it from
source. The clause above forbids *manufacturing* a compliance-only finding; it does
**not** license rubber-stamping a compliance-rationalized residual.

## Outcome routing (main applies)

Every outcome is **durably committed before** the loop acts on it — so a crash
between adjudication and routing cannot lose the decision.

| Outcome | Main action |
|---|---|
| **broke** | Commit a CONTINUE transition carrying the finding as Priority 1 (with the `candidate_commit_sha` reference); re-dispatch loop N+1. If the fix needs a CLAUDE-md Stop/Ask decision → `HALT_STAGNATION` subtype `user_decision` instead. The challenger broke it → demote, never promote. |
| **held** | Record `halt_success_challenge` (challenger_model, outcome `"held"`, binding, attempts[], reason); promote to terminal `HALT_SUCCESS`; commit. G32 gates the emit. |
| **unavailable / timeout** (after the bounded retry envelope) | **Fail closed**: commit `HALT_STAGNATION` subtype `verification_blocked` (or `user_decision`). Never auto-promote; never route to CONTINUE-without-a-finding. A terminal success is never blessed by silence. |

## Output contract

The challenger returns JSON mirroring `halt_success_challenge` in
[output-format-json.md](output-format-json.md):

```json
{
  "challenger_model": "<model>",
  "outcome": "held",
  "binding": { "candidate_commit_sha": "<sha>", "run_id": "<id>", "source_rev": "<sha>" },
  "attempts": [
    { "arm": "new_finding", "target": "<dimension|finding>", "what_tried": "...", "why_failed": "..." }
  ],
  "reason": "<one sentence: why the candidate held, or what broke it>"
}
```

`outcome: "broke"` carries the finding (or residual refutation) in `attempts[]`;
main reads it to seed the next loop's Priority-1 work.

## Oscillation

A recurring candidate with the same **`candidate_fingerprint`** (the canonical
content hash owned by [`scripts/candidate_fingerprint.py`](../scripts/candidate_fingerprint.py),
which excludes volatile commit/run/loop/timestamp metadata) routes through the
existing Step-1.6 oscillation handling instead of re-invoking the challenger. The
`candidate_commit_sha` is **not** the recurrence key — it changes on every
recommit; the fingerprint is.
