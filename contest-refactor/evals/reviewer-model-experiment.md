# Reviewer model-tier experiment: can the claude_code reviewer run on haiku?

**Date:** 2026-06-27 · **Outcome:** flip rejected · **Status:** closed (re-runnable)

This is the full write-up of the experiment that produced the reviewer-judgment
harness (`evals/reviewer-cases/`). The terse versions live in
`reviewer_baseline.json` (`measurement` block), `EVAL.md`, and `README.md`
(Layer 3); this file is the narrative + lessons.

## The question

The implementation reviewer (`references/implementation-reviewer.md`) runs on
**every** loop — sometimes twice — and on `claude_code` it defaulted to the same
model as the loop/Critic (`claude-sonnet-4-6`). The skill's own docs say it
"rarely needs upgrading — verifying a small diff against three checks is well
within the small-tier models." So: **can we default it to cheaper
`claude-haiku-4-5` to cut per-loop tokens + wall-clock, without regressing
verification efficacy?**

Two facts framed it:
- **Only `claude_code` can get cheaper.** codex (`gpt-5.4-mini`) and opencode
  (`deepseek-v4-flash`) reviewers are already at the cheapest tier.
- **No regression test existed.** The flag/restraint harness
  (`principal_baseline.json`) grades only the **Critic**; the reviewer and the
  HALT_SUCCESS challenger had no test at all. So measuring this safely required
  building one first.

## The method

A net-new harness at the reviewer's own input grain: `{targeted finding, diff} →
verdict JSON` (`approved | rejected | conditional`).

- **20 cases, 10 categories, 4 look-alike axes.** Each "reject" category is
  paired (`pair_id`) with an "approve (restraint)" twin that a paranoid reviewer
  would wrongly reject — so a reject-everything reviewer is caught failing its
  twin. Axes: `reality`, `seam`, `suppression`, `invariant`. Plus 2 standalone
  approve positive controls (`pass-through-deletion`) and 2 `conditional`
  (`small-fixable`). See `README.md` Layer 3 for the table.
- **Materialization.** Each case is a `base/` + `head/` tree; the runner builds a
  throwaway git repo so the **verbatim** reviewer prompt — which runs `git diff
  HEAD` — works byte-identically to a real loop. `prereg.reviewer_prompt_sha256`
  pins the prompt; edit it and the baseline must be re-measured.
- **Asymmetric thresholds — the core design choice.** The two error directions
  are not equally dangerous:
  - **`false_approve_tolerance = 0`** — approving a must-reject diff carries a
    fake-clean refactor into the audit trail. Zero tolerance.
  - **`false_reject_regression_tolerance = 1`** — rejecting a must-approve diff
    only costs a carried-forward loop. Bounded, not zero.
- **The run.** Host-dispatched reviewer spawns, `model=sonnet` (arm A) vs
  `model=haiku` (arm B), on each case, multiple reps. Raw verdicts in
  `reviewer_baseline_replication.json`.

## The results

| | Arm A (sonnet) | Arm B (haiku) |
|---|---|---|
| **Must-reject cases (8) + conditional (2)** | all reject/conditional | **all reject/conditional — 0 approvals** |
| **Approve cases (10)** | all approve | **7/10 unanimous approve; over-rejects 3** |

- **GATE A (false-approve) — CLEAN.** Across every rep, haiku **never** approved a
  must-reject or conditional case. The cheaper reviewer does **not** let a
  fake-clean / regression diff through. The dangerous direction is solid.
- **GATE B (false-reject) — FAILED.** Haiku over-rejects three legitimate cases
  across **two** restraint axes where sonnet approves unanimously:
  - `justified-single-adapter-1` — haiku ~2/3 approve
  - `risk-evidence-present-1` — haiku ~2/3 approve
  - `risk-evidence-present-2` — haiku ~1/2 approve

  The tolerance allows at most **one** approve category dropping below the bar;
  haiku breaches it on two.

## The decision

**Do not flip the `claude_code` reviewer default to haiku.** Keep
`claude-sonnet-4-6`. `claude-haiku-4-5` remains available opt-in via
`--reviewer-model` / `CONTEST_REFACTOR_REVIEWER_MODEL` for cost-sensitive runs
that can absorb extra carry-forwards. `provider-adapters.md` defaults,
validators, canon, schema, and artifact fixtures are all unchanged.

## What was learned

1. **The cheap model's failure mode is over-rejection, not under-rejection.**
   Haiku is *safe* — it never rubber-stamps a bad refactor — but *over-conservative*.
   For a verification gate that is the less-dangerous direction (a false reject
   just re-attempts the loop), but it is still a real efficacy cost: it would make
   the loop carry-forward legitimate refactors ~1/3 of the time on the affected
   axes, wasting iterations and risking non-convergence on those fix types.

2. **It degrades specifically on *judgment*, not *detection*.** Haiku nailed every
   mechanical smell-detection reject (two-writers, recording-stub, `nonisolated(unsafe)`
   suppression, missing-evidence). Where it wobbled was the nuanced "is this
   carve-out legitimate?" calls — **single-adapter-seam justification** and
   **risk-boundary invariant evidence**. Those are exactly the architectural
   judgments the reviewer exists to make, which is why they're disqualifying.

3. **Authoring provably-clean restraint twins from short diffs is genuinely hard.**
   The K=1 pilot's sonnet arm caught **real residuals** in 3/10 approve cases that
   the author missed: a cited TSAN test that didn't exist, a URL that silently
   changed behavior, and a computed-property refactor that broke SwiftUI
   `objectWillChange`. All three had to be hardened before the false-reject signal
   was measurable. This mirrors the `principal_baseline` experience exactly — the
   capable reviewer is a tougher critic than the case author.

4. **Asymmetric tolerance was the right model.** A symmetric "match sonnet exactly"
   bar would have failed haiku on noise; a single global tolerance would have
   missed that false-approve is categorically worse than false-reject. Splitting
   them (0 vs 1) let the safe-but-conservative result read as exactly that.

5. **Staged measurement paid off.** The cheap kill-check first (K=1 pilot on the
   must-reject cases) would have killed the flip immediately and cheaply if haiku
   false-approved. It didn't — it surfaced the case defects and pointed at the
   real question (false-reject on restraint), which the full run then answered.

6. **The reviewer/challenger now has a regression test it never had.** Regardless
   of this specific verdict, the harness is the durable asset: any future change to
   the reviewer prompt or model can be re-measured against it.

## Operational caveats (so the next run is cleaner)

- **K-run write-dropouts.** The run targeted K=5 × 20 × 2 = 200 reviews but ~65
  spawned reviewers idled **without writing** their verdict file (a harness write
  quirk, not a verdict). Achieved 2–4 usable reps per cell. The decision is robust
  to this — GATE A is unanimous and GATE B fails at the achieved K — so cases stay
  `baseline_unmeasured` and the `measurement` block is authoritative rather than
  faking a clean K=5.
- **For a future re-run:** make the verdict-file write the agent's *primary*
  deliverable (not a "reply done" afterthought), and/or collect via a single
  poll-then-nudge sweep. Consider committing the materializer (kept in scratchpad
  this round) if the harness is run regularly.

## Sibling result: is Opus a better Critic than the Sonnet default? (no measured benefit)

The reviewer is the *cheap* end of the question; the Critic is the *expensive* end —
should the loop/Critic default be **upgraded** to Opus? Tested 2026-06-27 with the
low-token method below (3 spawns, ~15k tokens — vs the ~5M the reviewer run cost).

- **Method.** A condensed-rubric "micro-judgment": instead of each agent re-reading
  ~600 lines of `method.md` + `architecture-rubric.md` + lens, the key cross-module
  tests + verdict contract were inlined (~250 tokens). Ran **Sonnet only** on the **3
  hardest** cross-module flags (`principal-consistency-boundary`, `-abstraction-seam`,
  `-process-owner`), cheap-arm-first with an early stop.
- **Result.** Sonnet caught all 3 **decisively** — `rejected`, `blocks_95: true`,
  target dimension 4.5–6.5, defect named (`missing-process-owner` / `fake-clean
  reward`). This corroborates `principal_baseline`'s **5/5** default-arm recall.
  Because the default tier already saturates recall on the hardest tested defects,
  **Opus has no recall headroom — there is nothing for it to catch that Sonnet
  misses.** Early-stopped; no Opus run needed.
- **Decision.** Keep the Sonnet Critic default. Opus/Fable stay opt-in, and
  `provider-adapters.md § When to upgrade` was rewritten from a vague ">100K LOC"
  benefit-claim into an **evidence-based precaution**: no measured recall benefit on
  the tested corpus, so don't upgrade reflexively (it burns tokens for an unmeasured
  gain) — upgrade only for codebases beyond what the corpus exercises or when a run
  visibly stalls.
- **Scope / honesty.** This measures **recall** (catching defects), not restraint
  precision or fine scoring calibration, and the corpus is the existing principal
  cases — Opus *might* help on defects harder than any tested, but if Sonnet doesn't
  miss them, Opus isn't needed. K=1 per case here, but each was decisive and
  `principal_baseline` already showed K=5 5/5 for the default arm.

## The low-token tier-test method (reusable)

The reviewer run cost ~5M tokens (200 spawns × ~25k each, because every agent re-read
the full reference set). For *tier-discrimination* questions ("is model X measurably
better than model Y at job Z?") that is wildly overpriced. Three levers cut it >100×:

1. **Condensed inline rubric** — embed a ~250-token distilled judgment surface in the
   prompt instead of having each agent read the full `method.md` + `architecture-rubric.md`
   + lens. Per-spawn drops ~25k → ~4k. Valid for *discrimination* (does the tier spot
   the defect?); **not** a substitute for the full-fidelity materialized harness when
   you're measuring the skill's actual output *shape*.
2. **Frontier-only cases** — test only the discriminators (the hardest cases, where a
   weaker tier is most likely to fail), not the whole corpus. 3 cases, not 20.
3. **Cheap-arm-first + early-stop** — run the cheaper tier first. If it already
   saturates (catches every defect / matches the expensive tier), the expensive tier
   has no headroom — **stop, never spawn it.** Only escalate on a miss.

Plus: **reuse existing measured data** (don't re-run an arm already on record), and
prefer **single-shot judgment** prompts over full multi-loop runs when the question is
about one decision, not end-to-end behavior. The Critic-tier test above used all of
these and resolved in 3 spawns.

## How to re-run / reuse

- **Cases + manifest:** `evals/reviewer-cases/<id>/` (`case.toml`, `finding.md`,
  `base/`, `head/`, optional `deleted_paths`); registered in
  `evals/reviewer_baseline.json`.
- **Selftest (no model):** `python3 scripts/_reviewer_baseline_selftest.py` —
  enforces no-silent-exclusion, reject↔restraint twins, enum/canon validity, and
  (once cases are `measured`) the asymmetric false-approve gate.
- **Re-measure trigger:** if `references/implementation-reviewer.md`'s fenced
  prompt changes, recompute `prereg.reviewer_prompt_sha256`
  (`awk 'NR>=35 && NR<=182' references/implementation-reviewer.md | shasum -a 256`)
  and re-run both arms.
- **Materialization recipe:** copy `base/` → `git init/commit` → apply `head/` +
  `git rm` each `deleted_paths` → `git add -A` (uncommitted) → splice `finding.md`
  into a synthetic `CURRENT_REVIEW.md`, then spawn the reviewer with the verbatim
  prompt at the arm's model.
