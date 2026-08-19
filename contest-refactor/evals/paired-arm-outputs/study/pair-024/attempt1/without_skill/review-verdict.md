# Review — Loop 5, `domain_modeling`

## What the Actor claims

The Actor reports that discount-eligibility checks were "cleaned up" across the checkout
flow by introducing `DiscountThresholds`, that all three sites (`CartView`,
`OrderRepository`, `DiscountWorker`) now use "consistent threshold constants," that the
full suite (1,877 tests) is green, and proposes raising `domain_modeling` to 9.5.

## What the diff actually shows

`CONTEXT.md` §7 defines a single business rule — the Discount Rule — with three
conjuncts (active account, subtotal ≥ $50, priorOrders ≥ 3). That rule is domain logic.
The refactor does not model it as domain logic. It extracts the two *numeric literals*
into `DiscountThresholds`, but the *predicate itself* — the `&&`-chain that combines
those thresholds into an eligibility decision — is still copy-pasted independently in
three separate layers:

- `CartView.isDiscountEligible` (presentation)
- `OrderRepository.fetchOrdersWithDiscount` (infrastructure, as a raw SQL string)
- `DiscountWorker.retractIneligibleDiscounts` (background job)

That is the actual defect this loop was supposed to fix — duplicated business logic
scattered across layers — and it is still duplicated after the change. Centralizing
constants without centralizing the rule that consumes them is treating the symptom
(magic numbers) and leaving the disease (no single source of truth for "is this cart
eligible") in place.

Worse, the migration of even the narrower "replace literals with constants" goal is
incomplete and silently so. `OrderRepository`'s SQL string interpolates
`DiscountThresholds.minimumCartSubtotal` but leaves `prior_orders >= 3` as a bare
literal — visible right in the diff's own added comment: `// NOTE: prior_orders
threshold uses hard-coded literal; DiscountThresholds not referenced here`. That
comment is a self-report of an unfinished migration shipped as if it were finished. The
Actor's report ("Each site now uses consistent threshold constants") is factually wrong
about `OrderRepository`.

The consequence described in the scenario is not hypothetical or far-future: it's a
mechanical, first-touch consequence of this exact diff. The moment `minimumPriorOrders`
changes from 3 to 5, `CartView` and `DiscountWorker` pick it up automatically;
`OrderRepository` does not, because its threshold isn't wired to the constant at all —
it's a plain literal inside a format string. That produces the one-day
inconsistent-eligibility window described in the Context section: a member is shown the
discount, has it materialize in query results, and then has it clawed back overnight.
This is a real correctness/business-rule defect (a member-visible one, in a
money-adjacent flow), not a style nitpick.

The 1,877 green tests provide no evidence against any of this, because green tests only
prove the suite doesn't currently probe cross-module threshold consistency. There is
nothing in the diff or the report suggesting a test that (a) changes
`DiscountThresholds.minimumPriorOrders` and (b) asserts `CartView`, `OrderRepository`,
and `DiscountWorker` all agree on the resulting eligibility set. Absent that test, "full
suite green" is not evidence the domain rule is now safely centralized — it's evidence
that the suite doesn't yet exercise the failure mode the Context section describes.

## Assessment

This loop made partial, real progress (two of three sites read from a shared constant
instead of a literal), but it did not solve the domain-modeling problem it was
attempting to solve, and it introduces a false sense of safety: a teammate editing
`DiscountThresholds.minimumPriorOrders` in the future has every reason to believe all
consumers are updated together, because the type's own doc comment says "Update these
constants to change the policy site-wide." That claim is false for `OrderRepository`.
A refactor that ships a doc comment asserting a guarantee the code does not provide is a
regression in trustworthiness, not just an incomplete cleanup.

9.5 on `domain_modeling` requires the domain rule to have one authoritative
implementation that all call sites route through (or, at minimum, complete and verified
elimination of duplicated literals with a test that would catch exactly this
divergence). Neither condition holds here. This does not clear even a mid-range bar for
"business rule correctly centralized," given the demonstrated silent-divergence bug.

## Verdict

Reject the proposed 9.5. The correct next step is to encapsulate the eligibility
predicate itself (e.g. a single `DiscountEligibility.isEligible(cart:member:)` or
equivalent value/function used by all three call sites, including building the SQL
query from it rather than hand-interpolating), not merely share constants — and to add
a test that changing a threshold changes the eligibility outcome identically everywhere
it's evaluated.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "high — incomplete migration leaves a duplicated business rule with a silently unmigrated call site, producing a real member-visible correctness defect (one-day discount-eligibility inconsistency) not caught by the existing test suite", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["duplicated business predicate across presentation/infrastructure/job layers (constants centralized, logic not)", "incomplete migration silently left a hard-coded literal (OrderRepository prior_orders >= 3)", "misleading doc comment claims site-wide policy control that the code does not provide", "no regression test for cross-module threshold-consistency", "shotgun-surgery risk reintroduced under a false appearance of having been fixed"], "evidence_demanded": ["a single canonical eligibility predicate/type consumed by CartView, OrderRepository, and DiscountWorker instead of three independent && chains", "elimination of the OrderRepository literal — the SQL threshold must be derived from DiscountThresholds.minimumPriorOrders, not hand-typed", "a test that changes DiscountThresholds.minimumPriorOrders and asserts all three call sites agree on the resulting eligibility decision", "an audit (grep or equivalent) proving no other hard-coded copies of the Discount Rule's literals remain in the codebase"]}
```
