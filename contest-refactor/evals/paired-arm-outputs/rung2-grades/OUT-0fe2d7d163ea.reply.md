```json
{
  "output_id": "OUT-0fe2d7d163ea",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "this rule's *evaluation* is a\nruntime decision made in three places:\n\n- `CartView.isDiscountEligible` (presentation)\n- `OrderRepository.fetchOrdersWithDiscount` (infrastructure — SQL predicate)\n- `DiscountWorker.retractIneligibleDiscounts` (background job)\n\n`DiscountThresholds` centralizes the two *numeric literals* the rule\nconsumes. It does not centralize the *predicate*. All three sites still\nindependently author the conjunction (`isActive && subtotal >= X &&\npriorOrders >= Y`)",
      "rationale": "The response names all three concrete sites (CartView, OrderRepository, DiscountWorker) as independent implementations of the same eligibility conjunction and explicitly distinguishes the shared numeric constants from the still-duplicated predicate.",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "`OrderRepository` migrated the subtotal literal but left `prior_orders >= 3`\nhard-coded — and the comment documents the gap rather than closing it. This\nis a self-admitted incomplete migration shipped as a \"cleaned up ... uses\nconsistent threshold constants\" claim.",
      "rationale": "The response identifies that OrderRepository's subtotal clause was migrated to the constant but the prior_orders clause was left as a hard-coded literal, and elsewhere in the same paragraph block ties this to a silent drift path when the constant is changed elsewhere ('CartView` and `DiscountWorker` pick up the new value; `OrderRepository`'s SQL string does not').",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "`DiscountThresholds` centralizes the two *numeric literals* the rule\nconsumes. It does not centralize the *predicate*.",
      "rationale": "The response explicitly declines to treat DiscountThresholds as centralizing the eligibility rule, stating it only centralizes the numeric inputs and not the predicate that consumes them, and withholds the 9.5 score on that basis.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "`DiscountThresholds` centralizes the two *numeric literals* the rule\nconsumes. It does not centralize the *predicate*. All three sites still\nindependently author the conjunction (`isActive && subtotal >= X &&\npriorOrders >= Y`) — that is the actual domain concern under review, and\nafter this loop it still has no single owner, just a shared pair of\nconstants that owner-less code may or may not reference correctly.",
  "semantic_grade_rationale": "The response names, in its own words, that DiscountThresholds centralized only the numeric constants while the eligibility predicate remains independently authored in all three modules, satisfying the tier rule's requirement for a caught verdict."
}
```
