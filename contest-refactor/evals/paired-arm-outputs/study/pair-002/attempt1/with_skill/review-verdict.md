# Critic Review — Loop 5, `domain_modeling`

## Independent re-derivation (Method Step 1)

The Actor's report claims domain_modeling → 9.5 on the strength of "consistent
threshold constants via `DiscountThresholds`" and a green 1,877-test suite. Per
Method Step 1, that report is a historical claim, not proof; the diff is
re-derived from source below rather than taken at face value (this also
avoids the anchored-to-history failure mode the method flags — the Actor's
own proposed 9.5 is exactly the kind of "prior verdict" that must not be
rubber-stamped).

`CONTEXT.md` §7 names a single business rule — the Discount Rule: account
active AND subtotal ≥ $50 AND prior orders ≥ 3. Per Method Step 2 (Authority
Map for mutable/decision-owning concerns), this rule's *evaluation* is a
runtime decision made in three places:

- `CartView.isDiscountEligible` (presentation)
- `OrderRepository.fetchOrdersWithDiscount` (infrastructure — SQL predicate)
- `DiscountWorker.retractIneligibleDiscounts` (background job)

`DiscountThresholds` centralizes the two *numeric literals* the rule
consumes. It does not centralize the *predicate*. All three sites still
independently author the conjunction (`isActive && subtotal >= X &&
priorOrders >= Y`) — that is the actual domain concern under review, and
after this loop it still has no single owner, just a shared pair of
constants that owner-less code may or may not reference correctly.

## The concrete defect

The diff itself proves the hazard is not hypothetical:

```
+        // NOTE: prior_orders threshold uses hard-coded literal; DiscountThresholds not referenced here
         try await db.query(
             "SELECT * FROM orders WHERE member_id = ? AND is_active = 1 AND subtotal >= \(DiscountThresholds.minimumCartSubtotal) AND prior_orders >= 3",
```

`OrderRepository` migrated the subtotal literal but left `prior_orders >= 3`
hard-coded — and the comment documents the gap rather than closing it. This
is a self-admitted incomplete migration shipped as a "cleaned up ... uses
consistent threshold constants" claim.

The consequence chain is exactly what the Authority Map exercise is meant to
surface: the next time a product owner edits `DiscountThresholds.minimumPriorOrders`
(a normal, expected content change — CONTEXT.md documents the rule as a
policy, not a constant), `CartView` and `DiscountWorker` pick up the new
value; `OrderRepository`'s SQL string does not. A member with 4 prior orders
sees the discount in the UI, has it baked into the repository-populated
order (persistence writer), then has it silently retracted overnight by the
nightly job — a materially incorrect, customer-visible checkout state for a
full day, on the primary discount/checkout flow, not an off-path utility.

Per the doc comment on `DiscountThresholds` itself — "Update these constants
to change the policy site-wide" — the code now makes a claim about itself
that is false for one of its three consumers.

## Why 1,877 green tests don't clear this

This is the "aggregate-test-count-as-test-strategy" sub-pattern of
**fake-clean reward**: a large passing count is cited as evidence for the
domain_modeling dimension, but nothing in the suite asserts that
`CartView`, `OrderRepository`, and `DiscountWorker` agree on eligibility for
the same member/cart — the actual property the "cleanup" claims to buy. Per
Method Step 8's mutation-test check: bump
`DiscountThresholds.minimumPriorOrders` from 3 to 5 and no test in the
1,877 fails to catch that `OrderRepository` silently disagrees with the
other two sites. That mutation sits on a persistence-writer / primary-flow
surface, which the rubric's own severity anchor names explicitly as
disqualifying-caliber when untested ("test absence around central mutable
runtime behavior ... persistence writer").

## Deletion / ownership framing

Applying the deletion test to `DiscountThresholds`: deleting it reintroduces
magic numbers at 3 call sites — so it is not pure ceremony, it earns some
keep. But the module it should have been — a single `DiscountEligibility`
(or similarly named) predicate function/type that `CartView`,
`OrderRepository`, and `DiscountWorker` all call — was never built. What
shipped is Depth at the *constant* level only; the actual decision (is this
cart/member eligible) remains shallow and triplicated. That is a **weak
domain model**: a named business rule from CONTEXT.md with no domain type or
function that owns it, reimplemented independently at three call sites, one
of which is already provably out of sync.

## Severity

This lands as a **Likely disqualifier** for `domain_modeling`, not a
contained/local Serious deduction, because it matches the anchor's own
examples on two counts simultaneously: (1) the Discount Rule has
multi-writer authority — three independent implementations of one domain
concern with no owner — analogous to "durable state written from multiple
places with no owner"; and (2) there is test absence around a persistence
writer's mutable runtime behavior with *realized*, not merely theoretical,
regression risk (the diff ships the drift itself, documented by its own
comment). The harm is reachable from the primary checkout/loyalty-discount
flow, not an off-path utility, so the anchor's reachability qualifier is
also satisfied.

This blocks acceptance of `domain_modeling` at the 9.5 threshold. The
Actor's proposed 9.5 is rejected on evidence, not on the report's framing.

## What would clear it

A real fix centralizes the *predicate*, not just its inputs: one
`DiscountThresholds`-consuming eligibility function that `CartView` calls
directly, that `OrderRepository` uses to build its query (or that
`OrderRepository` defers to via a fetch-then-filter using the shared
predicate instead of a hand-built SQL fragment), and that `DiscountWorker`
calls unchanged. A cross-module consistency test (or the structural
elimination of the possibility of divergence via single ownership) is
required before the dimension can be re-scored above the current defect.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {
    "domain_modeling": 5.0
  },
  "flagged_smells": ["weak domain model", "fake-clean reward"],
  "evidence_demanded": [
    "A single domain-owned eligibility predicate (e.g. a DiscountEligibility type/function) that CartView, OrderRepository, and DiscountWorker all call, replacing the three independently-authored conjunctions",
    "OrderRepository.fetchOrdersWithDiscount migrated off the hard-coded `prior_orders >= 3` literal to reference DiscountThresholds.minimumPriorOrders (directly or via the shared predicate)",
    "A test that fails if any one of the three call sites diverges from DiscountThresholds (or structural proof that divergence is impossible because there is exactly one implementation)",
    "Correction of the DiscountThresholds doc comment ('Update these constants to change the policy site-wide') to be true, or made true by wiring the remaining call site"
  ]
}
```
