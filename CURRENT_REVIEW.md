provider: unknown; running inline; Loop Isolation unavailable

### Discovery
- Source roots: `contest-refactor/`
- Test command: full validator, fixture, smoke, standalone-selftest, recurrence-key, and Ruff suite
- Lens: Generic + Security + Efficiency

### Loop Counter
Loop 11 of 15.

### System Flag
[STATE: CONTINUE]

## Contest Verdict

Functionally solid, but canonical candidate identity is not enforced.

## Scorecard (1-10)

State management 8; Test strategy 8; Credibility 8. Architecture quality, domain modeling, data flow, framework idioms, and simplicity remain 9.5 accepted; Concurrency remains 10.

## Findings

### Finding #1: G32 accepts non-canonical candidate fingerprints

Stable ID `F-008`; Serious deduction. `_artifact_halt.py:165-201` checks only non-emptiness, while eight v4 success fixtures carry the placeholder `fp-sha256-architecture-payload-0001` and still match their expected result.

## Simplification Check

Call the existing canonical fingerprint function from G32, canonicalize existing fixtures, and add one mismatch fixture. No new algorithm, field, or Module.

## Improvement Backlog

1. `F-008` — recompute canonical candidate fingerprints at G32.

## Deepening Candidates

None.

## Builder Notes

- Priority 1 moves the three sub-target dimensions; no candidate further from target survives current-source review.
- Re-derived Loop 11 from `_artifact_halt.py`, `candidate_fingerprint.py`, and every v4 success fixture.
- Existing negative fixtures must retain their original failure clause after canonicalization.

## Final Judge Narrative

F-008 remains the sole Noticeable-or-worse correction. Reuse the existing digest owner at G32, preserve every other failure fixture, and re-score after the full gate.

## Loop 11 Result

- Reused `candidate_fingerprint()` in G32 for both candidate and terminal success states.
- Canonicalized all existing v4 success fixtures and added one mismatched-digest negative fixture.
- Focused proof: the mismatch fixture fails only on canonical-digest equality.
- Full proof: 54 fixtures, 11 smoke cases, all standalone self-tests, repository validation, and Ruff checks pass.
- Targeted finding: `F-008` resolved.

## Loop 11 Implementation Review

reviewer ran inline; verdict requires manual confirmation

Approved. Reality, honesty, and regression checks passed: G32 owns the trust-boundary comparison, the focused mismatch fixture isolates it, and the full suite remains green.
