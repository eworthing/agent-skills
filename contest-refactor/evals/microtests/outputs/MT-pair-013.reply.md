```json
{
  "output_id": "MT-pair-013",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "is compiled in on an iOS build (that's the whole point of the guard)",
      "rationale": "The response never names tvOS or macOS as at risk and explicitly treats the #if os(iOS) guard itself as intentional and correct, faulting only a missing import inside the guarded branch.",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": false,
      "evidence_span": "the recorded \"iOS build: success\" is inconsistent with the file contents it's supposedly evidence for",
      "rationale": "The response affirmatively contests the recorded per-target compile evidence as wrong/inconsistent rather than recognizing it as satisfying Meta-Rule 4.",
      "outside_spec": false
    },
    {
      "assertion_index": 2,
      "passed": false,
      "evidence_span": "A fresh, reproducible `xcodebuild build -destination 'generic/platform=iOS'` log run against the corrected file — the reported iOS build success cannot be reconciled with the diff as shown",
      "rationale": "The verdict is 'rejected' and the remedy demands re-verification of already-recorded per-target compile evidence rather than resting solely on the missing-residual/score-honesty ground the assertion requires.",
      "outside_spec": false
    },
    {
      "assertion_index": 3,
      "passed": "uncertain",
      "evidence_span": null,
      "rationale": "The framework_idioms score of 2 is rationalized around a missing import inside the guarded branch rather than the choice of #if os(iOS) itself, but the rationale is saturated with platform/build vocabulary (iOS build, UIKit, the guarded branch) and neither the spec's bright line nor its near-miss list cleanly resolves whether that counts as 'mentioning the guard/platform topic.'",
      "outside_spec": false
    }
  ],
  "semantic_grade": "over_flagged",
  "semantic_grade_evidence_span": "A fresh, reproducible `xcodebuild build -destination 'generic/platform=iOS'` log run against the corrected file — the reported iOS build success cannot be reconciled with the diff as shown",
  "semantic_grade_rationale": "Although the response never disputes the #if os(iOS) guard's choice or raises tvOS/macOS risk, it does what the tier rule separately treats as over-flagging: it disputes the recorded per-target compile evidence and demands additional verification for a declared target beyond what Meta-Rule 4 already certified."
}
```
