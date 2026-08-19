# Review: Loop 5 — `domain_modeling`

## What the Actor claims vs. what the diff shows

The Actor's report says: *"Each site now uses consistent threshold constants via
`DiscountThresholds`."* That claim is false on the evidence of the Actor's own diff.

`OrderRepository.fetchOrdersWithDiscount` was changed to interpolate
`DiscountThresholds.minimumCartSubtotal` into the SQL string, but the `prior_orders >= 3`
clause was left as a bare literal — and the diff even adds a comment admitting it:
`// NOTE: prior_orders threshold uses hard-coded literal; DiscountThresholds not
referenced here`. That is not an oversight that slipped past review; it's a known gap
that was written down and then reported as "consistent." A report that claims uniform
migration while the diff it's describing contains a comment disclosing the opposite is
a credibility problem independent of the underlying design issue.

## The underlying design problem: constants extracted, rule not extracted

`CONTEXT.md` §7 defines a single business rule (the "Discount Rule": active account +
subtotal ≥ $50 + ≥3 prior orders). Before this loop, that rule's *numbers* were
duplicated as magic literals in three places. After this loop, the numbers live in one
enum, but the *rule itself* — the boolean predicate that combines them — is still
written out independently in `CartView`, `OrderRepository`, and `DiscountWorker`. This
is "Move Constant," not domain modeling. It doesn't touch the actual defect class the
loop was scoped to fix: shotgun surgery on a single business concept spread across
presentation, infrastructure, and a background job.

Proof this doesn't hold up under the deletion test: delete `DiscountThresholds` and each
call site can trivially fall back to inlining a literal again with zero compile-time
signal that the sites have diverged — which is exactly what happened to
`OrderRepository`, mid-refactor, in this very diff. A domain abstraction that doesn't
prevent its own re-duplication one file over isn't doing domain-modeling work; it's
cosmetic.

## The bug this produces is not hypothetical

The scenario walks the concrete failure: a product owner bumps
`minimumPriorOrders` from 3 to 5. `DiscountWorker` and `CartView` pick it up
automatically (they reference the constant). `OrderRepository` silently keeps using 3
because its SQL literal was never migrated. Result: a member with 4 prior orders is
shown the discount at checkout, has it baked into the repository's query result, and
then has it retracted by the nightly job — a real, user-visible one-day inconsistent
window, caused directly by this refactor's incompleteness, not by anything pre-existing.
Before the refactor, all three sites at least agreed with each other (all hard-coded to
`3`); after it, they can disagree, and nothing in the code prevents or flags that.

## Why "1,877 tests, 0 failed" doesn't clear this

The bug is latent, not currently triggered — today `minimumPriorOrders` is still 3, so
the hard-coded `OrderRepository` literal and the constant agree by coincidence. No test
in the suite exercises "change the constant, verify all three call sites reflect it,"
so a green run is exactly what you'd expect whether or not the centralization actually
holds. Green tests here are evidence of absence-of-currently-triggered-regression, not
evidence that the domain rule is now centralized. The Actor's report treats "tests
green" as sufficient warrant for a 9.5 domain_modeling claim; it isn't, because the
suite has no test shaped to catch the specific failure mode this refactor was
supposed to eliminate.

## Verdict

Reject. This does not clear 9.5 on `domain_modeling`. Partial/incomplete centralization
that leaves the actual business predicate triplicated, silently introduces a
correctness bug via an unmigrated call site, and is described in the loop report in
terms the diff itself contradicts, is a regression in trustworthiness even where it's a
lateral move in code shape. The fix is not "polish" — it requires either a single
shared predicate/policy type used by all three sites (with `OrderRepository` querying
broadly and filtering via the shared Swift predicate, or generating its SQL fragment
from the same source of truth) or, at minimum, completing the constant migration in
`OrderRepository` plus a regression test that pins constant changes to all three call
sites' behavior. Until then this should not be scored as centralization achieved.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["shotgun surgery", "duplicated business rule (rule triplicated across layers)", "primitive obsession (only partially resolved — constants extracted, predicate not)", "silent data/logic drift", "incomplete migration left with a self-admitting comment", "false completion claim in loop report"], "evidence_demanded": ["a single shared eligibility predicate/policy type (not just shared numeric constants) consumed by CartView, OrderRepository, and DiscountWorker", "OrderRepository's prior_orders clause migrated off the hard-coded literal onto DiscountThresholds.minimumPriorOrders", "a test that changes DiscountThresholds.minimumPriorOrders and asserts CartView, OrderRepository, and DiscountWorker all agree on eligibility for the same member/cart fixture", "a corrected loop report that does not claim uniform migration the diff contradicts"]}
```
