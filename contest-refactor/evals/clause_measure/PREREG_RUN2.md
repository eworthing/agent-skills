# Pre-registration — run 2, clause v3

Written before any run-2 reviewer output existed. Addresses codex round-1 blockers
B1, B3, B4, B6 and N1 against run 1 (`PREREG.md`, `RESULT.md`).

## What changed since run 1

**B1 — wording.** v1 asked only "what changes for a caller", which returns *nothing*
on the one live RED case and therefore endorsed the miss. v3 (223 tok) adds the
dependency limb **and** codex's positive criterion: *where two sites express one
policy and must change together, consolidating them is the fix and leaving them apart
is the defect.* v3's example list is carried over from v1 unchanged, so it remains
derived only from the run-1 packs and the run-2 negative control stays held out (B5).

**B3 — endpoint.** Scored per case, not pooled. pandas is the primary regression
claim; the three zero-baseline cases are dropped rather than diluting it.

**B4 — a real negative control now exists.** `config-precedence-duplicate-authority`
was built for this and did not exist during run 1. Reviewers see
`two-owners-drifted` (the pre-consolidation state), where the graded-correct answer is
to **recommend consolidation**. A clause that suppresses merging as a class fails here,
which is the failure run 1 could not detect at all.

**B6 — blinded scoring.** Reviewers write to `r01`–`r10`; arms are interleaved so
adjacent ids do not leak the arm. The arm key is held outside the repo until scoring
is complete, and scoring is done by an agent that is not told which file is which.

**N1 — order counterbalanced.** Each reviewer sees both cases; six see pandas first,
four see config first, split across both arms.

## Cases and outcomes, opposite-signed by design

| Case | Variant shown | Correct behaviour | Failure |
| --- | --- | --- | --- |
| `pandas-get-dummies-select-dtypes` | `local-predicate` | do **not** recommend extracting the duplicated Packed-unwrap | recommending the shared helper (over-merge) |
| `config-precedence-duplicate-authority` | `two-owners-drifted` | **do** recommend giving the layer-order walk one owner | not recommending consolidation, or proposing only a local repair of the truthiness test (over-restraint) |

Run 1 could only move one of these. Run 2 can fail in both directions, which is the
point.

## Decision rule, fixed in advance

- **Ship** only if pandas over-merge falls by ≥2 of 5 **and** config consolidation
  recall is ≥4/5 in the arm and no worse than control.
- **Do not ship** if config recall falls at all versus control — that is the
  over-suppression this pack exists to catch, and it vetoes any pandas gain.
- **Do not ship** if pandas moves by fewer than 2 of 5 (noise floor at n=5).
- **Report either way**, including a null or a both-directions-worse result.

## Baselines carried forward

Run 1 control, pandas: **5/5 over-merge** (`CONTROL_SCORED.md`). Run 1 clause v1:
4/5. Run 2 re-measures control on the same case, so the comparison is within-run.

There is no prior baseline for the config case; run 2 establishes it.

## Limits that remain

The negative control is constructed, not harvested (recorded in the pack's own
`provenance_note` and `grading.md`). n=5 per arm still cannot resolve effects smaller
than ~2/5. Two cases in one context is a weaker mitigation than one case per context;
order is counterbalanced but carryover is not eliminated.
