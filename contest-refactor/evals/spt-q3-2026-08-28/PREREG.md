# Pre-registration — SPT Q3 bidirectional clause, measured on diffs

Written 2026-08-28, before any treatment run started and before the treatment prose
was written into the probe environment. Decision rules fixed here; nothing below
changes after data arrives.

## The hypothesis, and where it came from

`RESULT_DIFF.md` (2026-08-27, n=9 probes): the Simplify Pressure Test rejected ten
proposed fixes, nine correctly. The one wrong rejection was d1
(`config-precedence-duplicate-authority` RED), where the correct consolidation was
**raised and then rejected on Q2 (ceremony) and Q5 (no measurable gain)**, and the
loop instead applied exactly the symptom patch `must_not_find` #2 forbids.

Diagnosis, verbatim from that result: *"Q2 and Q5 measure a consolidation by size and
by gain. Neither asks whether the two sites answer the same question."* Q3 as shipped
(`method.md:110`, "Does it avoid duplicate layers?") only brakes **adding** a layer;
no SPT question asks whether an **existing** duplicate authority should collapse.

Hypothesis: making Q3 bidirectional — with explicit rewiring of how Q2/Q5 weigh a
proven-duplicate-authority collapse — flips d1 to the graded-correct consolidation
**without** flipping any of the nine correct rejections.

## Why this is not the third flat prose measurement

The two clause_measure runs had no observed failure at the diff level to target and
were graded at finding level, where the harness itself proved unstable (control
5/5 → 2/5 on identical inputs). This run targets one **observed applied-diff
failure**, and grades **diffs against manifests plus executable oracles** — the
grading layer that stayed stable all session.

**In-sample honesty:** the clause is derived from d1's failure, so d1 is in-sample.
A SHIP result claims "fixes the observed failure without breaking the nine correct
restraint judgments" — the restraint specimens are the out-of-sample half. It does
NOT claim generalization to unseen duplicate-authority shapes.

## The treatment

A full copy of `references/` in the scratchpad, byte-identical except two edits to
`method.md`'s SPT section:

1. Q3 line becomes: *"Does it avoid duplicate layers — both directions: it adds no
   second owner of a question, and where two existing sites already answer the same
   question, it does not leave both standing?"*
2. One new paragraph (**"Q3 cuts both ways."**) after the "Q5 is the leverage
   question" paragraph: defines when two sites answer the same question (demonstrated
   drift that is a bug, or a documented contract each must satisfy independently);
   states that such a collapse is not ceremony under Q2 and that closing the
   demonstrated drift class is the measurable gain under Q5; states that serving
   different callers does not make it a different question; and carries the guard —
   sites that merely look alike or may legitimately diverge are load-bearing
   duplication, and collapsing them fails Q4.

Estimated cost if ever shipped: ~170 tokens in `method.md` (a charged file; shipping
would move `token-budget.py` and requires an honest measured-basis ceiling update).

## Arms

**Control = the existing 2026-08-27 probe results**, reused as-is (d1, d2, pyd, pyt,
d6 all ran the shipped prose under the same probe protocol). No control re-runs.

**Treatment = 6 sequential sonnet runs**, prompts byte-identical to each specimen's
original probe prompt except: probe directory path, and the three PROTOCOL paths
point at the scratchpad prose copy (agents may not read anything under
`/Users/Shared/git/` at all, so they cannot see the shipped SPT). Test-count numbers
in prompts updated to each specimen's measured baseline.

| Run | Specimen / variant | Role |
| --- | --- | --- |
| T-d1a, T-d1b | `config-precedence-duplicate-authority` / `two-owners-drifted` (RED) | must flip: consolidation applied. ×2 because it is decision-critical |
| T-d2 | `auth-unusable-password-policy` / `sentinel-marked-no-credential` | restraint: must not invent findings against the sentinel scheme |
| T-pyd | `pydantic-typing-extra` / `dual-registry-split` | highest flip risk: two near-identical classifier functions whose split is deliberate |
| T-pyt | `pytest-scope-enum-public-compat` / `enum-with-compat-property` | flip risk: internal/public type split that looks like an inconsistency |
| T-d6 | `cpython-genexpr-iterability` / `lazy-consistent` | restraint spine: RED and GREEN are the same edit |

pyd and pyt are chosen precisely because they are the collapse-bait specimens: a
clause that merely says "merge things that look alike" will fail here first.

## Grading — from diffs and executed behaviour, never self-reports

**d1 flip achieved** requires all of:
- after the edit, the layer-precedence question has a single owner: one code path
  both `effective_value` and `describe_source` route through (shared walk, or one
  implemented via the other); the two independent membership cascades are gone;
- the falsy-but-present repro fixed: `env={"retries": ""}` → both functions agree on
  `env`;
- bundled suite passes; the pack's three oracles (`value_and_reported_source_agree`,
  `env_outranks_project`, `default_when_no_layer_carries`) green on the edited code.

**FLIP (restraint failure)** per specimen, straight from each manifest's
`must_not_find`:
- T-d2: any applied edit or remedy replacing the sentinel with nullable column /
  boolean flag (#1), deleting or shortening the random suffix (#3), or "fixing" the
  exact-prefix check (#4).
- T-pyd: merging `is_derived_marker` / `is_derived_annotation` (#1); collapsing the
  two marker registries; treating the disclosed alias gap as must-close (#3).
- T-pyt: public `span` returns the `Span` enum (#1); unifying/renaming the
  `_span`/`span` split as an inconsistency (#2).
- T-d6: introducing a CheckedSource-style wrapper (#1–#2) or otherwise relocating
  rather than honouring the disclosed eager/lazy timing contract; breaking the
  retained-source safety property (`must_find` #5).

HARM / VALUE / CHURN labels carry over from `PREREG_DIFF.md` unchanged for anything
else that lands.

## Decision rules, fixed now

- **SHIP** the clause into `method.md` only if: d1 flip achieved in **2/2** runs, AND
  **zero** FLIPs across T-d2/T-pyd/T-pyt/T-d6, AND no new HARM anywhere.
- **KILL** — any FLIP on a restraint specimen kills the clause outright, regardless
  of d1. Nine correct rejections traded for one correct consolidation is a net loss.
- **NO-SHIP** — d1 flips 0/2 or 1/2 with no FLIPs: the clause is insufficient;
  record, do not iterate wording within this measurement, present to owner.

One attempt per run, no retries on disliked outcomes; a run that dies on
infrastructure (not judgment) may be relaunched once and the relaunch noted.

## Limits, stated up front

Control and treatment runs are separated by a day and this harness has documented
run-to-run variance at the finding level; diff-level grading was stable but n stays
small. Six treatment runs, one model, one attempt each. d1 is in-sample by
construction. A SHIP here still means "shipped to `method.md` prose", whose effect
in the full harness (LOOP_STATE, 50 gates) remains unobserved — the same
prose-vs-harness gap every measurement this session has carried.
