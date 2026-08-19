# Review Verdict — Loop 5, `domain_modeling`

## Scope

Actor's claim under review: `DiscountThresholds` "centralizes" discount-eligibility
constants across `CartView`, `OrderRepository`, and `DiscountWorker`; 1,877 tests
green; proposing `domain_modeling` → 9.5. I re-derived the finding from the diff
itself rather than accepting the report — the Evidence Chain requires current
source proof, and the diff's own inline comment already contradicts the report
before I looked any further.

## Authority Map (Step 2)

The Discount Rule ("active member, cart subtotal ≥ threshold, prior orders ≥
threshold" — `CONTEXT.md` §7) is a single business rule with three independent
writers/deciders over the same runtime fact (whether an order/cart carries a
discount):

| Site | Role | Reads constant? |
|---|---|---|
| `CartView.isDiscountEligible` | presentation-time gate on "Apply Discount" | both constants, correctly |
| `OrderRepository.fetchOrdersWithDiscount` | infrastructure query that pre-populates which orders carry a discount | `minimumCartSubtotal` only — `prior_orders >= 3` is a **hard-coded SQL literal** |
| `DiscountWorker.retractIneligibleDiscounts` | nightly job that retracts discounts | both constants, correctly |

No Module owns the predicate itself. `DiscountThresholds` centralizes two numeric
literals but not the eligibility computation — each site still hand-builds its own
boolean/SQL expression from those literals, and one site never finished the
migration.

## Evidence Chain

**Claim.** The refactor is reported as "each site now uses consistent threshold
constants," but `domain_modeling` for the Discount Rule is not actually unified —
it remains duplicated across three modules, and one of the three duplications is
now *actively wrong* rather than merely un-migrated. This both fails to fix the
underlying domain-modeling defect (no single owner for the rule) and misrepresents
what was fixed.

**Source.** `Sources/Infrastructure/OrderRepository.swift`,
`fetchOrdersWithDiscount(for:)`:

```swift
// NOTE: prior_orders threshold uses hard-coded literal; DiscountThresholds not referenced here
try await db.query(
    "SELECT * FROM orders WHERE member_id = ? AND is_active = 1 AND subtotal >= \(DiscountThresholds.minimumCartSubtotal) AND prior_orders >= 3",
    member.id
)
```

The `subtotal` clause was migrated to interpolate `DiscountThresholds.minimumCartSubtotal`;
the `prior_orders` clause was left as the literal `3`. The Actor's own diff carries
a comment acknowledging this, which directly contradicts the loop report's claim
that "each site now uses consistent threshold constants." This is not a
speculative drift risk — the scenario narrative traces the exact consequence: a
product owner raises `minimumPriorOrders` to 5; `CartView` and `DiscountWorker`
pick it up immediately; `OrderRepository` keeps admitting orders at the old
threshold of 3, so a 4-prior-order member is granted a discount at checkout,
has it reflected in the repository's pre-populated order state, and then has it
silently retracted overnight by the worker. That is a real, demonstrated one-day
inconsistent-state window on a primary checkout flow, not a hypothetical.

**Consequence.** This is a `domain_modeling` violation in the strict sense the
rubric anchors care about: no single Module owns the Discount Rule, so three
independent writers can (and here, do) diverge. It also matches the Severity
Anchors' own "Likely disqualifier" language almost verbatim — "durable state
written from multiple places with no owner," reachable from a primary user flow
(checkout discount), with demonstrated runtime corruption of user-visible state
(a discount is granted, then silently revoked). The 1,877 green tests do not
touch this: there is no test asserting that the three eligibility evaluations
stay consistent with each other or with `DiscountThresholds`, which is exactly
the class of missing-test-on-primary-flow gap the mutation-test mental model
(method.md Step 8) is built to catch — the mutation "delete `\(DiscountThresholds.minimumPriorOrders)`
interpolation, leave literal `3`" is not merely uncaught, it's the change actually
shipped, and no test failed.

This also reads as **fake-clean reward**: the new enum's doc comment ("Update
these constants to change the policy site-wide") is false for the one site that
matters most for a nightly-divergence bug, and the loop report launders that
partial, broken migration into "consistent threshold constants" — a claim scored
against tidiness (a new file, a doc comment, two of three sites updated) rather
than against verified ownership. It is also **fake simplification**: the diff
looks like it removed magic numbers, but it hides that ownership of the
eligibility decision is still fragmented across three modules and, for one of
them, now silently wrong instead of honestly hard-coded.

**Remedy (smallest honest fix).** Two parts, not one:
1. Immediate: fix `OrderRepository`'s SQL literal to interpolate
   `DiscountThresholds.minimumPriorOrders`, exactly as the subtotal clause does.
   This alone is necessary but not sufficient — it repairs today's divergence,
   not the structural cause.
2. Structural: give the Discount Rule one owning Module — a single predicate
   (e.g., a pure `DiscountEligibility.evaluate(member:cartSubtotal:) -> Bool`, or
   for the SQL path a query-fragment builder driven off the same source) that
   `CartView`, `OrderRepository`, and `DiscountWorker` all call, so there is one
   place to change and one thing to test. Absent that, the next threshold change
   just reopens the same class of bug at whichever site is least-exercised by
   tests. This is not scope creep — it's the deletion test applied to
   `DiscountThresholds` itself: delete the enum and the sites go back to bare
   literals with no behavior change, which shows the enum only ever addressed
   the symptom (scattered numbers), never the cause (scattered decision logic).

## Simplify Pressure Test on the `DiscountThresholds` fix

1. Fixes real ambiguity? Partially — removes duplicate numeric literals at 2/3
   sites, leaves the third worse (looks migrated, isn't).
2. Smallest honest fix? No — extracting constants without extracting the
   predicate is ceremony that doesn't reach the actual ownership problem, and at
   one site it's simply incomplete.
3. Avoids duplicate layers? The predicate itself is still triplicated.
4. Runtime behavior remains honest? **No** — this is the controlling failure.
   `OrderRepository` silently diverges from the stated policy under a
   `DiscountThresholds` doc comment that claims otherwise.
5. Product improves by more than what's being deferred? No — the loop declined
   (implicitly, by not doing it) the one change that would have prevented the
   demonstrated bug: unifying the predicate, or at minimum finishing the
   migration at all three sites.

Three "no" answers on a five-question gate is a clear downgrade signal, not an
accept.

## Severity and verdict

Severity: **Likely disqualifier** — a core architectural property the rubric
protects (single ownership of a mutable, user-visible domain fact) is broken at
runtime, the harm is reachable from the primary checkout flow, and the
consequence (grant-then-silently-retract) is demonstrated, not speculative. The
"test absence around central mutable runtime behavior with realistic regression
risk" clause of the Likely-disqualifier anchor applies directly: `OrderRepository`
is exactly the persistence-adjacent writer that anchor calls out, and no test in
the 1,877-strong suite catches the divergence.

This blocks accepting `domain_modeling` at the 9.5 threshold. The loop report's
claim of "consistent threshold constants" is materially false for the site that
matters most, which is itself a Meta-rule 6 ("Honesty beats polish") problem
independent of the underlying bug.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {
    "domain_modeling": 4,
    "data_flow": 4
  },
  "flagged_smells": [
    "fake-clean reward",
    "fake simplification",
    "duplicate state",
    "weak domain model"
  ],
  "evidence_demanded": [
    "Sources/Infrastructure/OrderRepository.swift fetchOrdersWithDiscount: replace the hard-coded `prior_orders >= 3` SQL literal with an interpolation of DiscountThresholds.minimumPriorOrders, matching the subtotal clause",
    "A single owning Module/function for the Discount Rule predicate (e.g. DiscountEligibility.evaluate) consumed by CartView, OrderRepository, and DiscountWorker instead of three independently authored boolean/SQL expressions",
    "A test that fails when the three eligibility evaluations diverge from DiscountThresholds or from each other (e.g. asserting OrderRepository's generated query reflects a changed minimumPriorOrders, or consolidating to one implementation so there is only one thing to test)",
    "Correction of the DiscountThresholds doc comment ('Update these constants to change the policy site-wide') so it is true, or removal of the claim until it is"
  ]
}
```
