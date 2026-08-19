```json
{
  "output_id": "OUT-5da4dbaa2164",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "`CheckoutViewModel.purchaseTicket` sequences three durable, cross-module\nwrites (hold seat → charge card → write booking record) with no process that owns the\ncombined invariant \"all three durable effects land, or none do / are compensated.\"",
      "rationale": "The response locates the orchestration in CheckoutViewModel.purchaseTicket (marker 1) and explicitly states no process owns the combined multi-step invariant (marker 2), and elsewhere states this owner \"does not belong in CheckoutViewModel (presentation layer... not a durable-side-effect authority)\" (marker 3).",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "// No compensation: if charge succeeded but finalize failed,\n    // the seat remains held and the card is debited with no booking record.",
      "rationale": "States the precise failure ordering (charge succeeds, finalize fails) and the concrete resulting inconsistency (seat remains held, card debited, no booking record), satisfying markers 1 and 2, and the surrounding prose adds that the catch block \"performs no refund, no seat release, no reconciliation write\" (marker 3).",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "3,104 passing tests is not evidence against either finding (Meta-Rule 4: \"A green\nsingle-config test run does not prove preservation of every invariant: a data race\npasses nondeterministically\").",
      "rationale": "The response explicitly denies that the passing suite is evidence for either finding and states Finding 1's partial-failure path \"is not evidenced\" by any test, satisfying marker 1 while never treating the suite as reassurance.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "The `data_flow` dimension cannot be certified at 9.5 with an\nunowned, uncompensated multi-write failure mode sitting in the exact code this loop\ntouched.",
  "semantic_grade_rationale": "Both discriminating assertions (0 and 1) are satisfied — the response names CheckoutViewModel as the unowned orchestrator of the reserve/charge/confirm sequence and the concrete charge-succeeds/finalize-throws consequence — so under the spec's literal tier-rule reading this counts as caught."
}
```
