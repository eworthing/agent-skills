# Plan — Recommendation 1: certification cannot rest on one pass

**Status:** draft for discussion. Nothing implemented.
**Source of the requirement:** [`evals/scorecard-coupling/README.md § What this layer licenses`](../evals/scorecard-coupling/README.md), recommendation 1, derived from Layer 6 attempt 5.

## The measurement being implemented

| quantity | value |
|---|---|
| single-rater SEM (blind) | **0.283** |
| 95% band | **± 0.56** |
| score needed to clear a 9.5 cut by more than measurement error, one rater | **≥ 10.06** — above the scale maximum |
| same, on the mean of three | ≥ 9.82 |
| blind ICC(2,1) | 0.166 → panel of 3 reliability **0.374** |
| primed ICC(2,1) | 0.575 → panel of 3 reliability **0.802** |
| blind scores ever reaching 9.5, across 81 | **0** |

The one sentence that licenses this work: **G21 certifies `HALT_SUCCESS` per dimension at ≥ 9.5, and a single Critic pass cannot resolve a 9.5 cut at a 0.5-granular scale.** That holds independently of every anchoring question in attempts 2–4.

## What certification rests on today

1. The **loop Critic** (one rater) emits `HALT_SUCCESS_candidate` with all nine dimensions ≥ 9.5.
2. Main spawns **one challenger** ([`halt-verifier.md`](../references/halt-verifier.md)) which tries to *break* the verdict and returns a binary `held` / `broke`. It does **not** re-score.
3. `held` → promote to terminal `HALT_SUCCESS`. G32 gates the emit.

So the numeric claim — nine dimensions at ≥ 9.5 — is established by exactly one rater, and checked by a binary adversarial pass that never produces a second number.

## The design tension, stated plainly

Recommendation 1 says "N ≥ 3 independent passes, certify on the median." The panel size is easy. **What the panel is allowed to see is not, and recommendation 1 does not settle it:**

- A **blind** panel is uncontaminated but weak (reliability 0.374 at N=3) and, on the evidence, would essentially never certify — 0 of 81 blind scores ever reached 9.5.
- A **primed** panel is reliable (0.802 at N=3) but its agreement is partly contagion: profile correlation against the prime rose from +0.361 blind to +0.844 primed.

Neither configuration is clean, and the clean answer is recommendation 2 (an external calibration set), which is **not** in scope here. This plan therefore separates what ships cleanly from what needs a decision.

---

## Tier 1 — panel of N ≥ 3 challengers, unanimity of `held`

**No unresolved design questions. Implements "certification cannot rest on one pass" in the adversarial sense.**

Each panel member does exactly what today's single challenger does: same prompt, same inputs, same `held`/`broke` semantics, same arm-diversity requirement per member (members are independent; no cross-member coordination).

Aggregation is deliberately **asymmetric**:

- **`held` requires unanimity.** A hold is only the *absence* of evidence, and absence from one rater is weak — that is the whole finding.
- **One `broke` demotes.** A break carries a positive Evidence Chain that passed the Simplify Pressure Test. One valid finding is a valid finding regardless of how many other members missed it. Majority-voting on breaks would let a real defect be outvoted, which inverts the gate's purpose.

Fail-closed rules, extending the existing envelope:

| condition | outcome |
|---|---|
| all N `held` | promote to `HALT_SUCCESS` |
| any member `broke` | demote — CONTINUE with the finding as Priority 1 (as today) |
| fewer than N members return after the retry envelope | `HALT_STAGNATION` subtype `verification_blocked` |

## Tier 2 — each member also emits an independent per-dimension scorecard

**This is the actual implementation of the measurement. It needs a decision.**

### 2a — primed scoring
Members see the candidate scorecard (as today) and score. Certify on the **median ≥ 9.5** across the panel. Reliability 0.802; contaminated by the anchor.

### 2b — blind-then-challenge (Delphi ordering) — *recommended*
Each member (i) scores from source with no prior, (ii) then receives the candidate scorecard and residuals, (iii) then attempts the break.

The blind median is **not** used as a certification bar — blind raters never reach 9.5, so that would block everything. It is used as a **divergence check**: if the candidate's claim exceeds the blind panel median by more than a stated multiple of the measured SEM on any dimension, that is the Run B / Run C anchoring signature and the candidate is demoted or flagged.

Two things recommend 2b:
- It uses the uncontaminated estimate for the one thing it is good at — detecting divergence — rather than for absolute level, which it cannot do.
- It makes **every terminal produce a blind/primed pair**, feeding Layer 6 for free instead of requiring dedicated probes.

It also mirrors a rule the skill already states for the loop Critic at [`trust-model.md:64`](../references/trust-model.md) ("write your independent per-dimension scorecard from current source FIRST"), which is currently unenforced prose.

## Tier 3 — guard band on the candidate score. Deferred, with reason.

A guard band requires an observed **≥ 10.06** for one rater. Unreachable by construction. It only becomes meaningful once recommendation 2 (external calibration) shrinks SEM. Recording the arithmetic here so the next reader does not re-derive it.

---

## Work items

### Schema
`halt_success_challenge` gains `panel: [...]`, an array of N ≥ 3 challenge records, each carrying today's per-challenger fields (`challenger_model`, `outcome`, `binding`, `attempts[]`, `reason`), plus under Tier 2 an independent `scorecard` block. The existing top-level `outcome` becomes the **aggregate** verdict.

**Backward compatibility is the main cost.** Eight fixtures carry terminal `HALT_SUCCESS`:
`halt-success-bad`, `halt-terminal-binding-mismatch`, `halt-terminal-held`, `halt-terminal-invalid-arm`, `halt-terminal-missing-explanation`, `halt-terminal-no-challenge`, `halt-terminal-no-diversity`, `incremental-then-halt-success`.
Each needs a 3-member panel added **and mirrored verbatim into `REVIEW_HISTORY.json.loops[-1]`** or G18 fires. Three `HALT_SUCCESS_candidate` fixtures are unaffected (they require `halt_success_challenge: null`). This is the bulk of the work, exactly as it was for G43.

Open question: patch the eight at v4 (precedent: the G37 widening this session was breaking-by-design at v4 and fixtures were patched), or gate the panel requirement at v5.

### Code
`_artifact_halt.py` is at **693 / 800**. Panel validation is ~80–120 lines, which lands it at or over the hard cap. **Move the G32 block into a new `scripts/_artifact_panel.py`**, mirroring the G37 → `_artifact_residual.py` split done earlier this session. Do not reach for `# WAIVER: module-size`.

Extend **G32** rather than adding G44 — same rule, same concern, and splitting one rule across two IDs violates the disjointness discipline stated in G35's and G36's bodies.

### Prose and canon
- [`halt-verifier.md`](../references/halt-verifier.md) — panel spawn, aggregation table, asymmetric hold/break rule, Tier-2 ordering. The "Spawn" and "Outcome routing" sections both change.
- [`validation.md`](../references/validation.md) G32 body; `canon/validation-gates.toml` G32 title.
- [`output-format-json.md`](../references/output-format-json.md) § Schema version 4 changelog + the `halt_success_challenge` schema block; new rule in `output-format-json-rules.md`.
- `SKILL.md` Step 1 Routing, the `HALT_SUCCESS_candidate` branch.
- `provider-adapters.md` § Challenger-spawn profile — N parallel spawns.
- `halt-handoff.md` — `verification_blocked` wording for a partial panel.

### Tests
New `_g32_panel_selftest.py`. New fixtures: panel-of-2 (fail), panel with one `broke` at terminal (fail), panel unanimous held (pass), and under Tier 2 a divergence-exceeds-band case (fail).

---

## Cost, risk, and the thing to decide

**Token cost.** Tier 1 is 3× one challenger spawn, once per run, at the terminal only. Tier 2 makes each member do a full independent scoring pass first — roughly a full Critic pass each. On this session's measured numbers (~250k per pass) that is **~750k at the terminal**, once per run.

**This change makes certification strictly harder, and may mean no run ever certifies.** Four runs across 55 loops have never reached terminal `HALT_SUCCESS` anyway, so the practical impact is low — but it is a real consequence and it is the user's call, not mine. If the panel is the right instrument and nothing certifies, that is an answer about the codebase; if the instrument is simply too strict, it is a bug. The evidence cannot yet distinguish these.

**Risk register**
- Fixture churn: 8 fixtures × (artifact + history mirror). Mechanical but the largest single block of work.
- Module split forced by the 800-line cap; `_artifact_history.py` already sits at 794 and is untouched pre-existing debt.
- Tier 2b inherits recommendation 2's unresolved question. Shipping 2b before the calibration set means the divergence threshold is set from one corpus.
- Arm diversity per member (rather than per panel) triples the duplication sweep. Cheap, but worth naming.

## Questions for discussion

1. **Tier 1 only, or Tier 1 + Tier 2b?** Tier 1 ships clean; 2b is what actually implements the measurement and starts producing Layer-6 data on every terminal.
2. **Panel size** — fixed at 3, or a flag (`--panel N`) defaulting to 3?
3. **Divergence threshold for 2b** — what multiple of the measured SEM counts as anchoring rather than noise? 1.96×SEM on the mean of 3 is ±0.32; a candidate claiming 9.5 against a blind median of 7.6 exceeds that by ~6×.
4. **Fixture strategy** — patch the eight at v4, or gate the panel requirement at schema_version 5?
5. **Is "certification may become unreachable" acceptable?**
