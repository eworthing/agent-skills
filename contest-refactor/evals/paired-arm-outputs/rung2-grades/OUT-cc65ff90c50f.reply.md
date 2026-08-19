```json
{
  "output_id": "OUT-cc65ff90c50f",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "- `CartView`: `member.isActive && cart.subtotal >= T1 && member.priorOrderCount >= T2`\n- `DiscountWorker`: the same expression, independently written\n- `OrderRepository`: the same logic re-expressed as a raw SQL `WHERE` clause",
      "rationale": "The response names all three concrete sites (CartView, DiscountWorker, OrderRepository) as independently hand-written copies of the same eligibility predicate, explicitly distinguishing this from the numeric constants DiscountThresholds supplies, matching markers 1-3.",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "`OrderRepository.fetchOrdersWithDiscount` migrated the `subtotal >= 50` literal to\n`DiscountThresholds.minimumCartSubtotal`, but left `prior_orders >= 3` untouched as a raw\nliteral in the SQL string. So of the two constants the Actor introduced, one is not actually\nadopted at one of the three call sites.",
      "rationale": "The response names prior_orders specifically as the un-migrated literal, contrasts it with the successfully migrated subtotal clause (marker 3), and elsewhere ties it explicitly to a drift scenario when the threshold changes (marker 2).",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "The Actor's report claims: \"Each site now uses consistent threshold constants via\n`DiscountThresholds`.\" The diff does not support that claim, and the diff's own inline\ncomment contradicts it directly:",
      "rationale": "The response explicitly rejects the Actor's framing that DiscountThresholds achieved consistency/centralization, and elsewhere states a reviewer who assumes DiscountThresholds means the rule is centralized is wrong, satisfying markers 1 and 3.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "Reject. The claimed outcome (\"consistent threshold constants... site-wide\") is contradicted by\nthe diff itself at the `OrderRepository` call site, and the loop leaves the actual domain\nconcept (the Discount Rule as an evaluable predicate) un-modeled — three independent\nhand-written copies remain, one of them un-migrated even to the new constants.",
  "semantic_grade_rationale": "The response names the cross-module duplication of the eligibility predicate (assertion 0), the specific OrderRepository drift path (assertion 1), and declines to accept DiscountThresholds as centralizing evidence (assertion 5), satisfying the tier rule's caught criteria in full."
}
```
