```json
{
  "output_id": "OUT-3380bdb472bd",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "the *rule itself* — the boolean predicate that combines them — is still written out independently in `CartView`, `OrderRepository`, and `DiscountWorker`.",
      "rationale": "The response explicitly states the numeric constants were centralized but the eligibility predicate combining them is still independently duplicated in all three named modules, matching satisfying marker 2.",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "a product owner bumps `minimumPriorOrders` from 3 to 5. `DiscountWorker` and `CartView` pick it up automatically (they reference the constant). `OrderRepository` silently keeps using 3 because its SQL literal was never migrated.",
      "rationale": "The response names the specific hard-coded prior_orders literal in OrderRepository and explicitly walks through how a future constant change silently fails to propagate there while the other two sites update, satisfying markers 1 and 2.",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "This is \"Move Constant,\" not domain modeling.",
      "rationale": "The response explicitly refuses to credit DiscountThresholds as having centralized the rule, characterizing it as only moving constants while the predicate itself remains duplicated, matching satisfying marker 1.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "the *rule itself* — the boolean predicate that combines them — is still written out independently in `CartView`, `OrderRepository`, and `DiscountWorker`.",
  "semantic_grade_rationale": "The response names, in its own words, that DiscountThresholds centralized only the constants while the eligibility predicate remains independently duplicated across all three modules, satisfying assertion 0 and the tier rule's caught condition."
}
```
