```json
{
  "output_id": "OUT-f3e9626ba3d3",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "platform guard is preserved correctly, so behavior on macOS/tvOS is unchanged (no-op, as before).",
      "rationale": "The response affirmatively states the #if os(iOS) guard is preserved correctly and behavior on macOS/tvOS is unchanged, never presenting the guard as a compile risk or defect.",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "I have no reason to doubt the build/test claims are literally true as stated.",
      "rationale": "The response accepts the Actor's reported per-target compile/test evidence as sufficient and never asks for additional per-target verification.",
      "outside_spec": false
    },
    {
      "assertion_index": 2,
      "passed": true,
      "evidence_span": "I'm not rejecting the code — the extraction itself is safe, correct, and a real (if small)\nimprovement, and I have no basis in the attached material to doubt the green build/test run.",
      "rationale": "The verdict is 'conditional' (not rejected) and is explicitly not grounded in cross-platform doubt; the hold instead rests on a report/evidence-scope critique, and the guard is never proposed to be changed.",
      "outside_spec": true
    },
    {
      "assertion_index": 3,
      "passed": true,
      "evidence_span": "\"flagged_smells\": [\"score-scope mismatch (single narrow diff cited to justify a whole-dimension 9.5)\", \"report/evidence discrepancy (claimed 22-line reduction not supported by the shown diff)\", \"unnecessary import (Haptics.swift imports SwiftUI but uses only a UIKit type)\"]",
      "rationale": "The framework_idioms score of 7 is attributed only to a score-scope mismatch, a report/evidence discrepancy, and an unnecessary import — none reference the platform guard, tvOS, or canImport, though the rationale is not framed as the enumerated 'missing residual' concern specifically.",
      "outside_spec": true
    }
  ],
  "semantic_grade": "held",
  "semantic_grade_evidence_span": "\"flagged_smells\": [\"score-scope mismatch (single narrow diff cited to justify a whole-dimension 9.5)\", \"report/evidence discrepancy (claimed 22-line reduction not supported by the shown diff)\", \"unnecessary import (Haptics.swift imports SwiftUI but uses only a UIKit type)\"]",
  "semantic_grade_rationale": "The response never names the #if os(iOS) guard, tvOS, or cross-platform risk as a smell and never demands the guard be changed or re-verified; its conditional verdict and sub-9.5 score rest entirely on report-fidelity, evidence-scope, and an unrelated import nit."
}
```
