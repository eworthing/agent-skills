```json
{
  "output_id": "OUT-f16cf89c7cc2",
  "assertions": [
    {
      "assertion_index": 1,
      "passed": false,
      "evidence_span": "**Finding 1 — Concurrency test covers writer/writer serialization only, not reader/writer.**",
      "rationale": "The verdict word is 'conditional' not 'rejected', but the blocking rationale (Finding 1, cited alongside Finding 2 as the reason the dimension is held below 9.5) is grounded in the lock-protected storage's test-coverage completeness rather than solely in the Actor's failure to name a residual, so the pushback functions as demanding further justification of the suppression's evidence rather than pure score-honesty.",
      "outside_spec": false
    },
    {
      "assertion_index": 2,
      "passed": false,
      "evidence_span": "A TSAN-covered concurrency test that runs image(for:) reads concurrently interleaved with insert(_:for:) writes (not just insert-vs-insert), to substantiate the 'safe to share' claim for the cache's actual read+write access pattern.",
      "rationale": "The concurrency score is docked to 9.0 and the response explicitly states this evidentiary gap in the suppression-protected storage's TSAN coverage as a stated blocking condition (blocks_95: true), not solely the absence of a named residual, so it fails the requirement that any reduction be grounded only in the missing-residual rule.",
      "outside_spec": false
    },
    {
      "assertion_index": 3,
      "passed": true,
      "evidence_span": "This passes the carve-out.",
      "rationale": "The response walks the carve-out's three prongs directly against the diff (narrow scope, a justification comment stating the invariant, and both image(for:) and insert(_:for:) routing through lock.withLock) and concludes explicitly that the suppression passes the carve-out.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "over_flagged",
  "semantic_grade_evidence_span": "A TSAN-covered concurrency test that runs image(for:) reads concurrently interleaved with insert(_:for:) writes (not just insert-vs-insert), to substantiate the 'safe to share' claim for the cache's actual read+write access pattern.",
  "semantic_grade_rationale": "The response affirms the suppression passes the carve-out on inspection but still blocks the 9.5 score (blocks_95: true) on a demand for additional TSAN evidence covering the same lock-protected storage, which is justification beyond what the case already supplies and contradicts the answer key's statement that concurrency takes no deduction for the conformance."
}
```
