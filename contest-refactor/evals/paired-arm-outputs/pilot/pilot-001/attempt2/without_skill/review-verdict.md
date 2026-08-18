# Review — Loop 5, `domain_modeling`

## What the diff actually does

The stated goal — one owner for the loyalty-discount rule, three callers delegating to it — is
real. `DiscountPolicy.isEligible` correctly encodes all three conjuncts from `CONTEXT.md` §7
(`member.isActive`, `cartSubtotal >= 50`, `member.priorOrderCount >= 3`), the magic numbers are
gone from every call site, and `CartView` / `DiscountWorker` now call the policy directly with no
restated predicate. As a structural move this is good: it passes the deletion test (delete
`DiscountPolicy` and every caller breaks, rather than silently falling back to a local copy of the
rule), and there's no second definition of "eligible" left lying around in the diff.

That said, "delegates to `DiscountPolicy` everywhere" is not the same claim as "behavior is
preserved everywhere," and one of the three call sites quietly changes behavior while being
reported as a pure structural move.

## The problem: `OrderRepository.fetchOrdersWithDiscount` changes what it computes, not just how

**Before:**
```sql
SELECT * FROM orders WHERE member_id = ? AND is_active = 1 AND subtotal >= 50 AND prior_orders >= 3
```
This filters on columns that live on the `orders` row itself — `is_active` and `prior_orders`,
alongside `subtotal`. Whatever those columns mean, they are values captured in the context of the
order row, not a live join to today's member state.

**After:**
```swift
let candidates = try await db.query("SELECT * FROM orders WHERE member_id = ?", member.id)
return candidates.filter { order in
    discountPolicy.isEligible(member: member, cartSubtotal: order.subtotal)
}
```
This now evaluates eligibility against the **caller-supplied `member` object's current state**
(`member.isActive`, `member.priorOrderCount`) for every historical order returned, not against
whatever `is_active`/`prior_orders` recorded on that order row.

Unless `orders.is_active` and `orders.prior_orders` are guaranteed to always equal the member's
live values (e.g. a synced/generated column, or the table is actually a view over `members`), this
is a semantic change disguised as a refactor:

- A member who was active with 3+ prior orders when an order was placed, but is inactive today,
  would previously show up as eligible for that historical order and now would not.
- A member who has since crossed the 3-prior-orders threshold, but hadn't at order time, would now
  retroactively make old orders show as eligible when they previously wouldn't have.

The Actor's report frames this purely as "delegate to `DiscountPolicy.isEligible`" with no mention
that the *evaluation basis* moved from a per-row snapshot to live member state. If that's
intentional, it needed to be called out and justified against what callers of
`fetchOrdersWithDiscount` actually expect (a point-in-time record vs. a live recheck). If it's
not intentional, it's a correctness regression sitting inside a diff that's being sold as safe,
behavior-preserving centralization.

`DiscountWorker.retractIneligibleDiscounts` is the one place where re-evaluating against live
member state is clearly the *intended* semantics (its whole job is to catch members who are no
longer eligible) — that call site is fine. `OrderRepository` is different: nothing in the diff or
report establishes that its callers want a live recheck rather than a historical read.

## Evidence gaps

1. **No test evidence for the changed path.** The diff contains no test file. "1,877 tests, 0
   failed" tells us the existing suite didn't regress, but if the existing suite mocked/stubbed
   `OrderRepository` at the SQL layer (plausible, since the old implementation was a raw query),
   it may never have exercised a case where a member's live state diverges from the order-time
   snapshot — which is exactly the case this diff would behave differently on. A green suite is
   not evidence of behavior preservation here; it may just mean the suite never had a case
   sensitive to the change.
2. **No test for `DiscountPolicy.isEligible` directly** — boundary cases (`subtotal == 50`,
   `priorOrderCount == 3`, inactive member with otherwise-qualifying cart) aren't shown anywhere.
3. **"All three call sites" is asserted, not demonstrated.** The report claims exhaustiveness
   ("All three call sites... now delegate") but nothing in the material shows a repo-wide search
   (e.g., grep for the old inline predicate shape) confirming no fourth site was missed. I can only
   confirm what's in the diff; I can't confirm completeness from this material alone.

## Assessment

The centralization design itself is sound and matches what good domain modeling for this rule
should look like — I'd have no complaint about `DiscountPolicy`'s shape, the CONTEXT.md alignment,
or the CartView/DiscountWorker migrations. But a refactor loop claiming a policy-centralization win
should not also silently change what a data-fetching method returns, and this one does, without
acknowledging it or presenting evidence that the change is safe or intended. That's a correctness
question sitting directly on the dimension being graded (domain_modeling: is the rule now correct
and singly-owned, not just textually deduplicated), so it blocks acceptance at a 9.5 bar until
resolved.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "high — unacknowledged behavior change (SQL row-snapshot filter replaced by live-member-state filter) in OrderRepository.fetchOrdersWithDiscount, reported as a pure delegation refactor and unverified by any test targeting the divergent case",
  "dimension_scores": {
    "domain_modeling": 7
  },
  "flagged_smells": [
    "refactor reported as behavior-preserving centralization while silently changing evaluation semantics in OrderRepository",
    "test-green claim used as proof of correctness for a code path the existing suite likely never exercised",
    "exhaustiveness claim (\"all three call sites\") asserted without search evidence"
  ],
  "evidence_demanded": [
    "Confirm whether orders.is_active / orders.prior_orders are live-synced to Member or are point-in-time snapshots captured at order time",
    "If snapshots: justify (or revert) the switch to live member.isActive/member.priorOrderCount in fetchOrdersWithDiscount, and identify every caller of that method to confirm they want live re-evaluation",
    "Add a test for fetchOrdersWithDiscount covering a member whose isActive/priorOrderCount today differs from the order-time values",
    "Add a direct unit test for DiscountPolicy.isEligible covering the three boundary conditions (subtotal==50, priorOrderCount==3, inactive member)",
    "Show the search (grep/graph query) used to confirm CartView/OrderRepository/DiscountWorker are the only three call sites of the old inline predicate"
  ]
}
```
