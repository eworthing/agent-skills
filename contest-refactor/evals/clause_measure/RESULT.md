# Result: clause v1 is a NULL. Do not ship.

Scored per `PREREG.md`, against `CONTROL_SCORED.md` which was written before any arm
output was read.

## Primary outcome

| Arm | pandas | pydantic | pytest | store (`Panel`) | total |
| --- | --- | --- | --- | --- | --- |
| Control | 5/5 | 0/5 | 0/5 | 0/5 | **5/20** |
| Clause v1 | 4/5 | 0/5 | 0/5 | 0/5 | **4/20** |

Movement: **1 pair.** The pre-registered rule is *do not ship if the miss rate moves
by fewer than 2 pairs — below that the arm is noise at n=5.* **Do not ship.**

## Guard outcome — no recall damage, and no benefit

| Guard | Control | Clause v1 |
| --- | --- | --- |
| `store` `must_find` #3 (`QuietQueue` named for deletion) | 5/5 | 5/5 |
| `cpython` guard scope engaged correctly | 4/5 | 4/5 |
| Wrong collapses on the discrimination control | 0/5 | 0/5 |

The clause cost 204 tokens per loop and bought nothing.

## The mechanism is visible in the reviewers' own words

This is not a weak effect. The clause **supplied the justification** for the miss it
was written to prevent. Three of the four arm reviewers who missed cited the clause's
own test as their reason:

- arm1: *"Nothing about the two call sites depends on that unwrap logic differing"* —
  then recommended the helper. That is the clause's decision rule, run correctly, to
  the wrong answer.
- arm4: *"No behavior changes for any caller of either function."*
- arm5: *"Same behavior for every existing caller."*

Clause v1 asks "what changes for a caller?" and the honest answer in this case is
*nothing*. Merging is behavior-preserving. What it costs is **coupling**: the accepted
refactor existed to stop `should_encode` depending on `column_subset`'s internals, and
the helper puts that dependency back. The clause tested for the wrong property.

## Provenance of the diagnosis

The flaw was identified **before** the arm was scored — recorded in
`CONTROL_SCORED.md` and referred to peer review as U1 — and independently confirmed by
codex `gpt-5.6-sol` at high confidence (B1) in the same round. The null is therefore a
confirmed prediction, not a post-hoc explanation.

## What is dead and what survives

Dead: this wording, and any claim built on this run.

Survives:

- **The diagnosis.** Meta-Rule 5 has no stopping condition, and the pandas collapse is
  a reliable 5/5 control failure. That defect is real and reproducible.
- **The harness.** Control/arm briefs, five blind reviewers per arm, pre-registered
  scoring, and a decision rule that fired correctly on a null.

## Blocking gaps before any re-run (codex round 1, adjudicated on merit)

1. **B1 — wording.** Needs a dependency limb *plus* the positive criterion for when
   merging is still right: codex's *"centralization remains appropriate when the sites
   express one policy and should change together."* v2 as drafted (181 tok) names the
   cost but not that criterion, so it is also incomplete.
2. **B4 — there is no working negative control.** Verified against the data: **zero of
   five** control reviewers made `cpython`'s `must_find` #3 observation. All four who
   engaged that pack did so through the untested-platform gap instead. A clause that
   refuses every merge would pass this design undetected. An earlier claim in this
   session that a blanket clause "fails the cpython control" was wrong.
3. **B3 — endpoint.** Pooling four cases dilutes a 5/5 signal with fifteen
   zero-baseline observations. Re-scope to pandas as the primary claim.
4. **B5 — contamination.** The clause's example list was written from the four packs it
   is scored on. Held-out cases are needed for any generalization claim.
5. **B6 / N1 — scoring and clustering.** Blind the remedy coding; one case per fresh
   context rather than five cases in one.
