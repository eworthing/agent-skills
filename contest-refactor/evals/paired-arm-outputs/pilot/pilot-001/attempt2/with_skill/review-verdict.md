# Independent Review — Loop 5, `domain_modeling`

## What the Actor claims

`DiscountPolicy.isEligible(member:cartSubtotal:)` is installed as the single owner of the
loyalty-discount rule. The Actor's report states all three call sites (`CartView`,
`OrderRepository`, `DiscountWorker`) now delegate to it, and that "no independent re-statement
of the predicate exists outside `DiscountPolicy`." Proposed score: `domain_modeling` → 9.5.
Evidence offered is a green full-suite run (1,877 tests) — an aggregate count, not a
file:line/assertion citation.

## Independent walk of the diff

**`CartView`** — old: `member.isActive && cart.subtotal >= 50 && member.priorOrderCount >= 3`.
New: `discountPolicy.isEligible(member: member, cartSubtotal: cart.subtotal)`. Same inputs
(current `member` fields + a subtotal), same operators, same thresholds. Faithful,
behavior-preserving extraction. Deletion test: removing `DiscountPolicy` would put this boolean
logic back at 3 call sites — the Module earns its keep here.

**`DiscountWorker`** — old: `member.isActive && order.subtotal >= 50 && member.priorOrderCount
>= 3`, where `member` comes from `memberService.member(for: order.memberID)` (a live lookup).
New call is the same shape against the same live `member`. Also faithful, behavior-preserving.

**`OrderRepository.fetchOrdersWithDiscount`** — this one does not match the other two. The
*old* SQL filters `orders` rows directly:

```sql
SELECT * FROM orders WHERE member_id = ? AND is_active = 1 AND subtotal >= 50 AND prior_orders >= 3
```

`is_active` and `prior_orders` here are columns on the `orders` row itself — no join to a
`members` table is shown. That is consistent with a common and deliberate pattern: snapshotting
the eligibility-determining facts onto the order at the time it was written, so a later query
over historical orders reflects the member's state *as of that order*, not their state today.
The presence of a dedicated `DiscountWorker.retractIneligibleDiscounts` job (a separate,
explicit reconciliation step that walks discounted orders and retracts ones that are no longer
eligible) is corroborating evidence for this reading: if eligibility on existing orders
auto-tracked current member state, a large part of the reason for that worker's existence goes
away.

The *new* code fetches every order row for `member_id` unfiltered, then filters in memory with
`discountPolicy.isEligible(member: member, cartSubtotal: order.subtotal)` — using the **current**
`member` object's `isActive` / `priorOrderCount`, applied uniformly to every historical order,
not the per-order `is_active` / `prior_orders` values that used to gate the query.

That is a different predicate over different data, not a restatement of the same predicate.
`DiscountPolicy.isEligible`'s two fields (`member.isActive`, `member.priorOrderCount`) are, by
construction, "current state," because that's what `CartView` and `DiscountWorker` both need
and both already had in hand. Routing `OrderRepository` through the same struct silently swaps
"was this order eligible when it was placed" for "is this member eligible right now," for every
row the query returns. The accompanying comment ("DiscountPolicy owns the rule's structure and
fields; this layer applies it in-memory after retrieval") asserts equivalence without addressing
this mismatch in provenance — it treats a possible behavior change as if it were pure
consolidation.

This is exactly the situation the rubric's context-sufficiency cap describes: whether
`orders.is_active` / `orders.prior_orders` are point-in-time snapshots or live-synced mirror
columns is a schema/consistency fact that is not derivable from the given diff and is not
addressed by `CONTEXT.md` §7 (which only defines cart-time eligibility, and is silent on
order-history/retraction semantics). I can't resolve that ambiguity in the Actor's favor and
certify 9.5 on the strength of "tests are green" — a single green suite run doesn't prove this
invariant either way, since no test citation pins down a case where current member state
diverges from an order's own snapshot columns.

Consequence if the snapshot reading is correct: a member who becomes inactive (or whose prior
order count is later revised) would retroactively lose the discount label on old, previously
correctly-discounted orders in this read path, and the reverse — a member who newly clears the
3-prior-orders bar would retroactively gain the label on old orders that never qualified when
placed. That's a real, user-visible correctness regression on what looks like a member-facing
order-history / discount-display path, not the checkout flow itself (which is `CartView`, and is
unaffected).

Secondary, lower-severity note: the new query also drops the SQL-side filter entirely and pulls
every order row for the member into memory before filtering — a real efficiency regression
versus the old query-time filter, though not the central `domain_modeling` concern.

## Rubric application

- **Deletion test**: passes for `CartView` and `DiscountWorker` (logic reappears at both call
  sites if `DiscountPolicy` is removed). Not meaningfully applicable to `OrderRepository` in the
  same way, because what was inlined there wasn't the same predicate to begin with.
- **Evidence Chain**: Claim (predicate provenance changed for one of three call sites) → Source
  (diff: `orders.is_active`/`orders.prior_orders` columns, no join, vs.
  `member.isActive`/`member.priorOrderCount` object fields) → Consequence (silent reinterpretation
  of historical discount eligibility on a member-facing read path) → Remedy (confirm via
  schema/migration/ADR that the order-row columns are live-synced mirrors, in which case the
  substitution is safe and should say so in the comment; otherwise keep `OrderRepository` on
  point-in-time data — e.g. read the columns already on the row — and reserve
  `DiscountPolicy.isEligible` for call sites that genuinely want current-state evaluation).
- **Severity**: Serious deduction — a real, source-backed data-flow hazard in a meaningful
  module, contained to one read path, not corrupting the primary checkout flow. Not a Likely
  disqualifier: no source evidence shown that this path drives revenue-critical or primary-flow
  behavior in the same way checkout does.
- **Test Guardrails / mutation-test mental model (method.md Step 8)**: the Actor's only evidence
  is an aggregate pass count (1,877 tests) — precisely the "aggregate-test-count-as-test-strategy"
  fake-clean sub-pattern the rubric calls out. No file:line/assertion is cited for
  `DiscountPolicy.isEligible` itself or for `OrderRepository.fetchOrdersWithDiscount`'s changed
  behavior. A nameable mutation — swap the current-member-state read for the order-row snapshot
  read in `fetchOrdersWithDiscount`, or drop a conjunct in `isEligible` — has no cited assertion
  that would catch it.

## What's genuinely good here

The `CartView` and `DiscountWorker` consolidation is real, faithful, Leverage/Locality-positive
work: named constants replace magic numbers `50`/`3`, one call to `isEligible` replaces two
independent restatements of the same boolean expression, and the deletion test passes cleanly
for both. `DiscountPolicy` itself is a plain, stateless value type — no unjustified seam, no
protocol/adapter ceremony, no costume layer. Two of the three call sites earn the "single owner"
claim outright.

## Verdict

The submission is not accepted as-is at 9.5 for `domain_modeling`: one of the three call sites
this loop touched does not demonstrably preserve the pre-refactor predicate, and the only
offered evidence (aggregate test count) does not resolve that. The `CartView`/`DiscountWorker`
portion of the work is sound and should stand; `OrderRepository.fetchOrdersWithDiscount` needs
either a schema-backed justification that the substitution is safe, or a fix that keeps it on
point-in-time order data.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"domain_modeling": 7.0, "test_strategy": 6.0}, "flagged_smells": ["fake simplification", "aggregate-test-count-as-test-strategy"], "evidence_demanded": ["Schema/migration/ADR confirmation of whether orders.is_active and orders.prior_orders (queried directly in the pre-refactor SQL, no join shown) are point-in-time snapshots captured at order creation or live-synced mirrors of the member's current state", "A test on OrderRepository.fetchOrdersWithDiscount covering a member whose current isActive/priorOrderCount diverges from an existing order's is_active/prior_orders column values, asserting which value the query is supposed to honor", "File:line citation of the specific test(s) exercising DiscountPolicy.isEligible directly, and of the call site(s) that consume fetchOrdersWithDiscount's result (to establish whether this is a primary member-facing flow or an off-path utility, which affects severity)"]}
```
