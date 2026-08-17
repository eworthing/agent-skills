# Assertion-strength probe (Item 2 RED control)

**Status: fixtures built, probe NOT yet run.** Nothing in `references/` has been
changed on the strength of this hypothesis.

## What this measures

`references/implementation-reviewer.md` Check 2 (Tests-at-new-Interface) has two branches:

- **(a)** now-shallow tests deleted AND new tests live at the new Interface;
- **(b)** the indirect-coverage carve-out, requiring `loop_result.interface_test_coverage_path`.

The four verification items — ending in *"the assertion would fail if `target_symbol`'s
body were replaced with `fatalError()`"* — are scoped **`For (b)`**. Branch (a) has no
assertion-strength check. `G17` (`references/validation.md`) mirrors the asymmetry: it
fires only when a Deepening Keyword is present **and the diff contains no test file
changes**, and nothing in `scripts/` implements `interface_test_coverage_path` or
`distinguishes_no_op`.

Net: the no-op discriminator is active exactly when **no test was touched**, and absent
on the branch where the Actor **did** edit tests.

**This is a recall hypothesis, not a missing rule.** Check 2 opens by applying the full
Simplify Pressure Test to the actual diff; Meta-Rule 4 forbids unintended behavior change;
`suppression-as-fix` already covers silencing a signal. The open question is only whether
the reviewer *reliably applies* them to a weakened assertion with no explicit cue. Per the
repo's own standard (and the round-1 peer-review finding that killed a sibling proposal),
that does not justify a prompt edit before a RED control.

## Why these fixtures live here and not in `reviewer-cases/`

`scripts/_reviewer_baseline_selftest.py` fails any on-disk directory under
`evals/reviewer-cases/` that is not registered in `evals/reviewer_baseline.json`
("silent exclusion"). Registering a probe pair would:

1. break the selftest the moment the directories are created, unless registered; and
2. permanently add 10 runs per case to every future full re-baseline
   (20 cases x 2 arms x 5 reps = 200 today; 220 with a registered pair)

for a probe that may come back GREEN and ship nothing. So the pair sits in a sibling
fixture directory — the same pattern as `loop-fixtures/`, `exec-fixtures/`,
`priority-fixtures/`, `repo-map-fixtures/`. The internal layout is byte-compatible with a
reviewer-case, so **if Item 2 ships**, `git mv` into `reviewer-cases/` + a manifest entry
is the whole promotion.

## Pre-registered decision rule

Fixed before running. Do not renegotiate after seeing results.

| field | value |
|---|---|
| Arm | A only (`claude-sonnet-4-6`) — probe, not a baseline entry |
| K | 5 reps per fixture |
| Decision rule | >=4/5, matching `evals/reviewer_baseline.json` `thresholds` |
| `assertion-weakened-1` | expected `rejected` (or `conditional`) — the reviewer catches the weakened assertion |
| `assertion-strong-1` | expected `approved` — legitimate Replace-don't-layer test migration |
| **GREEN control (kill)** | weakened flagged >=4/5 **and** strong approved >=4/5 -> the cue is unnecessary. Ship nothing. Record the negative result here. |
| **RED (proceed)** | weakened flagged <=2/5 -> add the Check-2 cue, batched into one prompt patch with Item 1 |
| **Inconclusive (3/5)** | do not ship. Either raise K to 9 on `assertion-weakened-1` only, or park with the measurement recorded. |

The restraint twin is what makes this falsifiable: a reviewer that rejects any diff
touching test files passes `assertion-weakened-1` for the wrong reason and fails
`assertion-strong-1`. Both halves must hold.

## The planted defect

Both fixtures share one base and one targeted finding (shallow `DiscountApplier`), and
both correctly delete the now-shallow `DiscountApplierTests` — so both are branch (a).

`assertion-weakened-1` additionally reverses the ordering invariant: head/ taxes the full
subtotal and then subtracts the discount, where base/ discounted first and then taxed.

| inputs (subtotal, discount, taxBps) | base / strong | weakened | differs |
|---|---|---|---|
| 10_000, 2_000, 1_250 | 9_000 | 9_250 | **yes** |
| 10_000, 0, 1_250 | 11_250 | 11_250 | no |
| 1_000, 5_000, 1_250 | 0 | 0 | no |

So exactly **one** retained assertion is forced to weaken
(`XCTAssertEqual(total, 9_000)` -> `XCTAssertTrue(total > 0)`); the second stays exact.
The diff is surgical rather than a wholesale test rewrite, which is the realistic shape of
the failure. Re-derive the table with `python3 verify_fixture_math.py`.

## Materialization

Identical to Layer 3 (`../README.md`, base/head/deleted_paths convention): copy `base/`
into a throwaway git repo, `git commit`; overlay every `head/` file; `git rm` each
`deleted_paths` entry; `git add -A`; leave uncommitted. Splice `finding.md` into a
synthetic `CURRENT_REVIEW.md` Findings section. Then run the **verbatim, unmodified**
reviewer prompt from `references/implementation-reviewer.md`.

If the prompt has been edited since `prereg.reviewer_prompt_sha256` was recorded, this
probe is invalid — it measures the current prompt, and the whole point is to measure it
*before* any change.

## Measurement conditions (recorded before the run)

| field | value |
|---|---|
| date | 2026-08-17 |
| arm | A |
| model | host `sonnet` tier |
| reps | K=5 per fixture, 10 spawns total |
| reviewer prompt body | lines 35-185, sha256 `fbc5950e368b358283b599364b962c6f713191da07fd3066e077b87891884588` |
| prompt edited by this probe? | **no** — measured as-found |

**Two deviations from `evals/reviewer_baseline.json` `prereg`, both recorded rather than hidden:**

1. **`arm_a_model` is stale.** The prereg names `claude-sonnet-4-6`; the host `sonnet`
   tier now resolves to a later Sonnet. The probe measures the reviewer *as it runs
   today*, which is the question being asked, but this is not a like-for-like
   comparison against the 2026-06-27 numbers.
2. **`reviewer_prompt_sha256` no longer matches** — see below. The probe records the
   true current body sha instead.

## Finding: the pinned reviewer prompt had drifted, undetected — FIXED 2026-08-17

`prereg.reviewer_prompt_sha256` is `72207944...`, recorded at commit `ded1e97`. It no
longer matches, and the documented recipe no longer reads the right lines.

| commit | closing fence | body sha | |
|---|---|---|---|
| `ded1e97` (baseline) | 183 | `72207944...` | matches prereg |
| `f3222cd` | 184 | `4384c622...` | drift 1 |
| `6f03dda` | 185 | `da23bb9f...` | drift 2 |
| `36832f1` | 186 | `53df5515...` | drift 3 |
| `adfbe0b` | 186 | `fbc5950e...` | drift 4 — current |

Two separate defects:

1. **Content drift.** The prompt body changed four times after the baseline was
   recorded. No re-baseline was run and `prereg` was never updated, so the Layer-3
   numbers describe a prompt that no longer exists. Nothing detects this — no gate
   recomputes the sha.
2. **The recipe is line-fragile.** `awk 'NR>=35 && NR<=182'` hardcodes both bounds. The
   closing fence has moved to 186, so the documented command now under-reads by three
   lines and produces `b1125eb4...`, which matches *neither* the prereg nor the true
   body. Deriving the fence positions (e.g. `awk '/^```$/{n++; next} n==1'`) would be
   drift-proof.

**Consequence for cost planning:** a "re-baseline" was being budgeted at 200 runs to
protect a guarantee that was already void.

### Resolution (2026-08-17)

1. **Recipe is now fence-derived**, not line-numbered:
   `awk '/^```$/{n++; next} n==1' references/implementation-reviewer.md | shasum -a 256`.
   It cannot drift when the fence moves.
2. **Pin recomputed** to `f620648a...` (the body after Item 1's edit) and recorded in
   `prereg.reviewer_prompt_sha256`.
3. **`measurement.prompt_sha256` added**, recording that the 2026-06-27 numbers were
   taken against `72207944...`, plus a `prompt_staleness` field stating plainly that
   those gates are advisory until re-measured.
4. **`_reviewer_baseline_selftest.py` check (f) added** — hard-fails when the pin stops
   matching the live prompt, and prints an ADVISORY when the recorded measurement
   predates the current pin. RED-tested against both historical failure modes (a prompt
   edit without re-pinning, and a moved closing fence); both fail with an actionable
   message, and the clean tree passes.

The staleness itself is NOT closed — that costs a 200-run re-measurement and is a
separate decision. What is closed is the silence: the gap is now machine-visible on
every run instead of being discovered by accident.

## Results — 2026-08-17: **GREEN control. Item 2 ships nothing.**

Unanimous on both halves. 10/10 usable reps, zero dropouts.

| fixture | expected | k1 | k2 | k3 | k4 | k5 | hits | threshold |
|---|---|---|---|---|---|---|---|---|
| `assertion-weakened-1` | flagged | rejected | rejected | rejected | rejected | rejected | **5/5** | >=4/5 met |
| `assertion-strong-1` | approved | approved | approved | approved | approved | approved | **5/5** | >=4/5 met |

Every rejection was *semantically* correct, not just mechanically: each named both halves
of the planted defect — the reversed ordering invariant (9_000 -> 9_250) **and** the
weakened assertion — with `file:line` on both. Every approval correctly read the test
deletion as required Replace-don't-layer migration rather than as a smell.

### Decision

Per the pre-registered rule: weakened flagged >=4/5 **and** strong approved >=4/5 ->
**the cue is unnecessary. Ship nothing.** No edit to `references/implementation-reviewer.md`
Check 2, no edit to `G17`. The branch-(a) asymmetry documented above is real as a matter
of *text*, but it is not a behavioral gap: the reviewer closes it by other routes.

### Why it already works (the interesting part)

The reps reached the same catch by **different paths**, which is the signature of genuine
coverage rather than a lucky keyword match:

- *"failing Simplify Pressure Test Q4 (runtime behavior does not remain honest)"* (k1)
- *"a suppression-as-fix that silences the signal rather than preserving behavior"* (k2)
- *"passes on both the correct value (9000) and the now-wrong value (9250)"* (k3) — an
  independently reconstructed no-op discriminator, which is exactly what item 4 of the
  branch-(b) checklist asks for, applied on branch (a) unprompted
- *"a fake-clean reward that masks the regression"* (k4)
- *"deletes the comment warning that a tax-first order gives 9_250"* (k5) — caught the
  removed warning comment as corroborating evidence

Check 2 opens by applying the **full** Simplify Pressure Test to the actual diff, and
Meta-Rule 4 forbids unintended behavior change. Those general instruments were sufficient.
Adding a targeted cue would have bought nothing and cost a 200-run re-baseline.

### What this cost, and what it bought

10 reviewer spawns (~780k subagent tokens) to avoid a prompt edit plus a full re-baseline.
The negative result is the deliverable: **the branch-(a) asymmetry is now measured, not
suspected**, and the next person to notice the same asymmetry in the text can read this
instead of re-litigating it.

### Caveat on scope

One defect class, one stack (Swift/XCTest), one arm. This does not establish that the
reviewer catches *every* form of assertion weakening — only that it catches an
ordering-invariant reversal hidden behind a loosened equality assertion, reliably, at K=5.
A subtler weakening (e.g. narrowing a boundary rather than replacing the assertion) is
untested.
