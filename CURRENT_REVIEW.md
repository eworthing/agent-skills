### Discovery
- Source roots: `contest-refactor/`
- Test command: full validator, fixture, smoke, standalone-selftest, and Ruff suite
- Lens: Generic + Security + Efficiency

### Loop Counter
Loop 8 of 10.

### System Flag
[STATE: CONTINUE]

## Contest Verdict

Contest-grade source; F-006 is resolved and current source awaits convergence scoring.

## Scorecard (1-10)

Test strategy 8; Credibility 8. Other dimensions retain the source-derived 9.5/10 scores until the next Critic pass.

## Findings

### Finding #1: Candidate recurrence ignores changed source revisions

Stable ID `F-006`; Serious deduction; resolved in this loop. Candidate commits `3e51000` and `6c80090` shared one fingerprint across materially changed source revisions, which the verifier incorrectly routed to finding-based oscillation.

## Simplification Check

Pair the existing fingerprint with `source_rev`. No source digest, new field, or new validator layer.

## Improvement Backlog

1. `F-006` — resolved; re-score on the next loop.

## Deepening Candidates

None.

## Builder Notes

`candidate_commit_sha` remains the freshness binding; `(candidate_fingerprint, source_rev)` is the recurrence key.

## Final Judge Narrative

Candidate recurrence now distinguishes corrected source from artifact-only recommits. F-006 is resolved; the next loop must re-score current source.

## Loop 8 Plan

Pair the existing architecture fingerprint with `source_rev`, document the changed-source challenge rule, and executable-spec the pair. Do not add a source-tree digest.

## Loop 8 Result

The recurrence key now changes for a changed source revision and stays stable for artifact-only metadata changes.

## Loop 8 Implementation Review

Approved: the fix reuses both existing fields and directly covers the reproduced false-oscillation path.
