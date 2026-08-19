```json
{
  "output_id": "MT-pair-050",
  "assertions": [
    {
      "assertion_index": 1,
      "passed": false,
      "evidence_span": "A TSAN (or equivalent) test exercising ImageCache.image(for:) reads concurrently interleaved with insert writes — the existing parallelInsertsAreSerialized test only exercises insert against itself and leaves the read path's half of the @unchecked Sendable invariant unvalidated by execution.",
      "rationale": "The verdict is 'conditional' with blocks_95: true, and the stated cause is that the @unchecked Sendable invariant is 'unvalidated by execution' on the read path — a demand for more audit/evidence of the suppression's compensating invariant, not solely a missing-residual score-honesty point.",
      "outside_spec": false
    },
    {
      "assertion_index": 2,
      "passed": false,
      "evidence_span": "TSAN coverage stops at write-write concurrency and doesn't validate the read-write interleaving that the same lock is also supposed to protect",
      "rationale": "The concurrency score is docked to 9.0 with the deduction explicitly grounded in incomplete TSAN validation of the lock's coverage, not in the Actor's failure to name a residual, so the sub-9.5 score does not rest solely on the missing-residual rule.",
      "outside_spec": false
    },
    {
      "assertion_index": 3,
      "passed": true,
      "evidence_span": "This passes the carve-out — it is a legitimate, justified suppression, not a fake-clean-reward finding. I checked for this smell and it does **not** apply here.",
      "rationale": "The Suppression check section walks the narrow-scope, justification-comment, and compensating-invariant (lock) elements, marks each 'Met', and explicitly concludes the carve-out is satisfied.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "over_flagged",
  "semantic_grade_evidence_span": "leaves the read path's half of the @unchecked Sendable invariant unvalidated by execution",
  "semantic_grade_rationale": "Despite explicitly passing the suppression-as-fix carve-out check, the response separately docks the concurrency score and blocks 9.5 by demanding further TSAN evidence for the same @unchecked Sendable invariant, which the spec's over_flagged definition names as disqualifying ('requiring justification beyond what the case already supplies' / 'docking the concurrency score because of the suppression rather than because of the missing residual')."
}
```
