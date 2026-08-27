# Pre-registration — collapse-instinct prose clause

Written 2026-08-26, after the control arm was launched and **before any arm
(clause-present) output was read**. ctl2's control output had been read at the
time of writing; no arm output existed.

## Hypothesis

Meta-Rule 5 (`Prefer subtractive fixes`) has no stopping condition, and four of
the five restraint misses measured in the 23-pack sweep are over-applied
subtraction: a reviewer treats load-bearing separation as duplication and
recommends collapsing it. A clause requiring the reviewer to name what changes
for a caller before recommending a merge should reduce that miss **without**
reducing true-finding recall.

## Arms

- **Control** — `method.md` Meta-Rules 1–7 + Simplify Pressure Test, verbatim.
- **Arm** — identical, plus the clause appended to Meta-Rule 5. Only delta.

5 independent sonnet reviewers per arm, each reviewing the same 5 accepted
variants, blind (no manifest, no sibling variant, no grading file).

## Cases

RED (a collapse recommendation here is a restraint miss, named in the pack's
own `must_not_find`):

1. `pandas-get-dummies-select-dtypes/local-predicate` — the Packed-unwrap
   one-liner is duplicated on purpose; decoupling beat de-duplicating.
2. `pydantic-typing-extra/dual-registry-split` — two registries model
   independently-versioned vocabularies.
3. `pytest-scope-enum-public-compat/enum-with-compat-property` — the
   same-name-different-type split is a disclosed compatibility surface.
4. `store-core-composition-residual/core-composition-with-dead-isolation` — the
   `Panel` protocol is what buys the compile-time key-path check.

DISCRIMINATION CONTROL:

5. `cpython-wasm-platform-predicate/shared-flag` — `must_find` requires
   refusing to collapse three single-platform guards **and** recognising that
   collapsing two others leaves the skip set unchanged. A clause that
   suppresses merge reasoning as a class fails this case.

## Primary outcome

**Collapse-miss rate** = number of (reviewer, RED case) pairs, out of 20, whose
findings recommend merging, extracting, renaming-to-unify, or deleting a
separation the pack declares load-bearing. Counted from the `remedy` field:
the recommendation is what misses, not the observation. Noting that two sites
resemble each other, without recommending they be unified, is **not** a miss.

## Guard outcome (the trade this must not make)

**True-finding recall**, counted on the same runs:

- `store-core-composition-residual` — `must_find` #3 requires naming the
  unreferenced `QuietQueue` actor. Recommending its deletion is a **hit**, not
  a miss; it is dead code, not load-bearing separation.
- `cpython-wasm-platform-predicate` — any finding that engages the
  per-platform guard scope correctly.

A drop in the primary outcome that comes with a drop in recall is a **bad
trade and will be reported as one**, not as a win.

## Decision rule, fixed in advance

- **Ship** if collapse-miss rate falls by at least half (control ≥ 4/20 → arm
  ≤ half of control) AND recall does not fall.
- **Do not ship** if recall falls at all, whatever the miss rate does.
- **Do not ship** if the miss rate moves by less than 2 pairs — below that the
  arm is noise at n=5, and the project's own history (advisory evals #35–#48)
  is that unmeasured prose changes get shipped on hope.
- **Report either way**, including a null result.

## Known limit, stated in advance

No pack in the 25-pack corpus requires *recommending* a merge as its correct
answer. This design can show the clause preserves discrimination on case 5; it
cannot prove the clause is not over-suppressive in general. A future pack whose
`must_find` is "these two really should be merged" is the missing negative
control.
