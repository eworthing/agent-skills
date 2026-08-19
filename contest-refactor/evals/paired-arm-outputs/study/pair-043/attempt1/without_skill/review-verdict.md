# Review — Loop 5, `domain_modeling`

## What the Actor claims vs. what the diff shows

The Actor's report says: *"Cleaned up discount eligibility checks across the checkout flow. Each
site now uses consistent threshold constants via `DiscountThresholds`... Proposing `domain_modeling`
→ 9.5."* The diff does not support that claim, and in fact contradicts it in its own text.

`OrderRepository.fetchOrdersWithDiscount` still hard-codes `prior_orders >= 3` in the SQL string
literal — it was only partially migrated (the `subtotal` comparison now interpolates
`DiscountThresholds.minimumCartSubtotal`, but `prior_orders` was left as a bare `3`). Critically,
the diff itself adds a comment directly above that line:

```
// NOTE: prior_orders threshold uses hard-coded literal; DiscountThresholds not referenced here
```

That means the Actor's own change acknowledges, in writing, the exact fact that the loop report
denies ("consistent threshold constants... site-wide"). This is not an oversight a reviewer has to
dig for — it's a self-contradiction sitting three lines away from the report's claim. A report that
says "consistent" while shipping a code comment that says "not referenced here" cannot be taken at
face value, and 1,877 green tests do not resolve the contradiction — nothing in this diff adds a
test that would catch the divergence, so "tests green" only means "nothing already covered broke,"
not "the stated goal was achieved."

## The deeper problem: constants were centralized, the rule was not

Per `CONTEXT.md` §7 there is exactly one business rule — the Discount Rule — with three conditions
(active account, subtotal ≥ $50, ≥3 prior orders). The correct domain-modeling move is to give that
rule **one** authoritative implementation (a method, a small evaluator type, anything callable from
all three sites) so there is structurally only one place the logic can diverge. What actually
shipped is `DiscountThresholds`, an enum of two numeric constants, still referenced by **three
independently written boolean expressions** in `CartView`, `OrderRepository`, and `DiscountWorker`.
Pulling magic numbers into named constants is a legitimate, if minor, improvement, but it is not the
same fix as centralizing the predicate — and the `OrderRepository` gap proves the difference is not
academic. Even where all three sites *do* reference the same constants correctly, the expression
itself (`isActive && subtotal >= x && priorOrders >= y`) is still copy-pasted three times; a future
change to the rule's *structure* (e.g., adding an "OR is VIP" clause) would require three
synchronized edits with no compiler or type-level guardrail forcing them to agree, which is exactly
the "shotgun surgery" shape `CONTEXT.md` §7 is describing as a single business rule in the first
place.

The doc-comment on the new type overstates what it delivers: *"Update these constants to change the
policy site-wide."* That is presented as a guarantee to future maintainers, and it's false today for
`minimumPriorOrders` — the whole point of the Context section's worked example (product owner bumps
3→5, `OrderRepository` doesn't move, one-day inconsistent window where a discount is granted then
silently retracted) is a direct demonstration of that guarantee failing on the very next
threshold change. Shipping a misleading doc-comment on a checkout/discount code path is worse than
shipping no comment, because it invites the next engineer to trust a promise the code doesn't keep.

## Why this blocks acceptance at 9.5

- The stated goal ("consistent threshold constants... site-wide") is not met; one of three call
  sites is explicitly, self-acknowledged unmigrated.
- The Actor's own report misrepresents this as complete — the report and the diff disagree, and the
  report is more visible than the code comment.
- No regression test exercises the exact failure mode the loop's own context section describes
  (threshold change → cross-module divergence), so "1,877 passed" is not evidence for the property
  being claimed.
- Even a fully-migrated version of this diff (all three sites referencing both constants) would only
  be a partial fix — it addresses "duplicated magic numbers" while leaving "duplicated business
  rule" (the actual named problem in the Context section) unresolved. Centralizing constants without
  centralizing the predicate is the shape of fix that looks done in a diff review but recreates the
  exact bug class it was meant to close.

This is a checkout/billing-adjacent code path (discount eligibility, money). An incomplete
migration with a false "site-wide" claim in both the doc-comment and the loop report is not a
9.5-caliber domain-modeling result — it's a partial, mis-reported one.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["Duplicated business rule / shotgun surgery (single Discount Rule reimplemented independently in three modules)", "Incomplete migration masquerading as complete (OrderRepository prior_orders still hard-coded)", "False/misleading documentation (\"Update these constants to change the policy site-wide\" is not true)", "Actor report contradicted by its own diff", "Test-count used as unrelated proof of correctness (no test covers cross-module threshold consistency)"], "evidence_demanded": ["OrderRepository.fetchOrdersWithDiscount migrated so prior_orders references DiscountThresholds.minimumPriorOrders, not a literal 3", "A single canonical predicate/evaluator for the Discount Rule (e.g. DiscountThresholds.isEligible(member:cart:) or a dedicated DiscountEligibility type) consumed identically by CartView, OrderRepository, and DiscountWorker, replacing the three hand-written boolean expressions", "A regression test that changes minimumPriorOrders and asserts CartView, OrderRepository's query, and DiscountWorker all agree on eligibility for a boundary member (e.g. 4 prior orders across a 3→5 threshold change) — i.e. a test that reproduces the Context section's worked failure", "A corrected loop report that does not claim site-wide consistency while a site remains unmigrated"]}
```
