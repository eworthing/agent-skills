# Plan: a restraint clause for over-applied subtraction in `contest-refactor`

## Background

`contest-refactor` is an Actor–Critic code-review skill. A 23-pack gold corpus of
fixtures built from real expert-reviewed refactors was executed against blind sonnet
reviewers, each given the skill's own review protocol (`method.md` Meta-Rules +
Simplify Pressure Test, `architecture-rubric.md` severity anchors, `lens-generic.md`)
and only candidate-visible source. 127 findings were classified.

Result: 5 restraint misses (a reviewer flagged something the pack's `must_not_find`
says a good reviewer must not flag). **Four of the five are the same instinct:**

| Pack | What the reviewer wanted to collapse | Why the split is load-bearing |
| --- | --- | --- |
| `pandas-get-dummies-select-dtypes` | a Packed-unwrap one-liner duplicated in two functions — extract a helper | the duplication exists so `should_encode` no longer depends on `column_subset`'s internals; decoupling was the point of the accepted refactor |
| `pydantic-typing-extra` | two registries holding identical objects — re-export one from the other | they model independently-versioned vocabularies (the `typing` / `typing_extensions` problem) |
| `pytest-scope-enum-public-compat` | `_span` / `span`, same name different type — rename to disambiguate | a disclosed public-API compatibility surface |
| `store-core-composition-residual` | the `Panel` protocol adds nothing over parameterizing directly — delete it | `Panel`'s generic constraint is what buys the compile-time key-path check |

Diagnosis: **Meta-Rule 5 has no stopping condition.** It reads *"Prefer subtractive
fixes. Remove ceremony, duplicate authority, dead paths, pass-through Modules, shallow
abstractions before adding new structure."* The skill's existing anti-examples guard
only the additive direction (adding a Repository, a Coordinator, a rename). Nothing
guards over-applied subtraction.

Why this is worth pursuing rather than a recall lever: this project has measured
recall levers at zero lift repeatedly (advisory evals #35–#48; the same sweep scored
6/6 near-miss discrimination), while a restraint prose clause (W3.1) previously moved
sonnet over-claim from 2/5 to 0/5.

## The proposed change

Append to Meta-Rule 5 in `references/method.md` (204 tokens; both loop paths have
~2,000 tokens of headroom, so no ceiling bump):

> **Subtraction needs the same proof as addition.** This rule prefers removing
> structure; it does not license removing structure that merely *resembles* other
> structure. Two sites that look alike are duplication only if nothing depends on them
> differing. Before recommending a merge, rename, or deletion, say what changes for a
> caller. If the honest answer is "nothing" — the merged form produces the same
> results, the same diagnostics, the same scope — make the recommendation. If it is
> anything else, that difference is the reason the split exists, and removing it is a
> behavior change wearing a cleanup's clothes. Differences that routinely hide behind a
> resemblance: distinct lifetimes or owners, independently-versioned vocabularies, a
> compatibility surface a caller still reads, per-site diagnostics or error wording, a
> type distinction the compiler is enforcing, a scope deliberately spelled out rather
> than derived. "These look the same" is an observation; "nothing depends on them
> differing" is the finding, and only the second one is a finding.

## Measurement design (pre-registered, running now)

Control = protocol verbatim. Arm = identical + clause appended to Meta-Rule 5, only
delta. 5 independent sonnet reviewers per arm, each reviewing the same 5 accepted
variants blind (no manifest, no sibling variant, no grading file).

Cases 1–4 are the RED packs above. Case 5, `cpython-wasm-platform-predicate`, is the
discrimination control: its `must_find` requires **refusing** to collapse three
single-platform guards *and* **recognising** that collapsing two others leaves the skip
set unchanged. A clause that suppresses merge reasoning as a class fails it.

Primary outcome: collapse-miss rate over (reviewer, RED case) pairs, scored from the
`remedy` field — recommending unification is the miss; merely observing a resemblance
is not. Guard outcome: true-finding recall, chiefly `store`'s `must_find` #3 (naming
the unreferenced `QuietQueue` actor) and correct engagement with `cpython`'s guard
scope. Decision rule fixed in advance: ship only if the miss rate at least halves AND
recall does not fall; a recall drop is a veto regardless of miss rate; a move under 2
pairs counts as noise; report either way including a null.

Control results so far (4 of 5 reps; one reviewer never returned):

- pandas collapse miss **4/4** — every control reviewer recommended extracting the
  duplicated unwrap into a shared helper.
- pydantic, pytest, store collapse miss **0/4** each.
- `QuietQueue` correctly named for deletion **4/4** (a `must_find` hit, not a miss —
  dead code is not load-bearing separation).
- cpython guard scope correctly engaged 3/4; zero wrong collapses on the control.

## Open questions and uncertainties — the reason for this review

**U1 — the clause may not actually address its own strongest case, and I think it does
not.** Extracting a shared `_primitive_of` helper in the pandas case is
behavior-preserving: same results, same diagnostics, same scope. Under the clause as
written, the honest answer to "what changes for a caller" is *nothing*, so the clause
says **make the recommendation** — endorsing the exact miss it was written to stop.
The pandas split is load-bearing for a reason the clause does not name: shared code
creates a dependency, and *removing* that dependency was the point of the accepted
refactor. The clause tests for behavior change; this case is about coupling. If that
reading is right, the arm now running is testing an under-specified clause and a null
result would be uninformative about the idea rather than about the wording. Should the
clause gain a second limb ("a merge also costs a dependency: name what the merged form
would couple that is currently independent"), and does that limb weaken or preserve the
discrimination control?

**U2 — the RED collapsed to one case, after the threshold was set.** The
pre-registered threshold assumed the miss was spread across four cases; control data
shows it concentrated in one (pandas 4/4, others 0/4). The other three ran at 1/3 in
the original sweep, which n=5 cannot resolve. I kept the threshold as written rather
than move it after seeing data. Is holding it correct, or is the honest move to declare
the design underpowered for cases 2–4 and re-scope to a pandas-only claim?

**U3 — no negative control exists anywhere in the corpus.** No pack's `must_find`
requires *recommending* a merge. So this design can show the clause preserves
discrimination on case 5, but cannot show it is not over-suppressive in general. Is a
purpose-built pack ("these two really should be merged") a prerequisite for shipping,
or acceptable as follow-up?

**U4 — the clause's own examples are derived from the packs it is measured on.** The
list of "differences that routinely hide behind a resemblance" was written after
reading these four packs. That is teaching to the test. Does it invalidate the
measurement, or is it acceptable because the clause must be concrete to be usable?

**U5 — unblinded scoring.** I score the arm knowing which file is which, against a
rule I wrote. Should scoring be delegated to a classifier that does not know arm from
control?

**U6 — reps are not fully independent.** Each reviewer reviews all 5 cases in one
context, so case 1 may prime case 2. Symmetric across arms, but it could inflate the
arm's apparent effect.

**U7 — placement and standing cost.** Meta-Rules load on every step of every loop, so
204 tokens is a permanent per-loop cost; the Simplify Pressure Test is Step-2 only and
cheaper, but the misses occur at finding-raising time, not fix-proposal time — which is
why Meta-Rule 5 was chosen. Is that the right trade?

**U8 — is this a skill defect at all?** Meta-Rule 4 already demands fixes preserve
behavior and load-bearing invariants. One reading is that the reviewers simply failed
to apply an existing rule, and the right change is to strengthen the link from
Meta-Rule 5 to Meta-Rule 4 rather than add new prose. Against that: the pandas merge
*is* behavior-preserving, so Meta-Rule 4 genuinely does not reach it (see U1).

**U9 — n asymmetry.** One control reviewer never returned, so the comparison may be
4 control vs 5 arm unless it lands.

## Verification before shipping

`ruff check` + `ruff format --check`; every `contest-refactor/scripts/_*_selftest.py`
run directly (a prose edit can break a content-hash pin); `validate-repo.py`;
`validate-gold-corpus.py`; all 25 oracle batteries; `token-budget.py --check` (must
stay OK without a ceiling bump). Commit straight to `main`, never branch, never push
unless asked.
