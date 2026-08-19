# Critic Review — Loop 5, `domain_modeling`

## Step 1: Inspect current code, not the Actor's report

The Actor's report claims: *"Each site now uses consistent threshold constants via `DiscountThresholds`... Proposing `domain_modeling` → 9.5."* Per method.md Meta-Rule 1 ("metrics support judgment; they never decide it") and Step 1 ("older reviews/claims are historical, require current source proof"), the 1,877-passing-test count and the Actor's summary are not evidence of correctness — they are claims to verify against the diff.

Reading the diff directly, the claim is false for one of the three call sites. That is the finding.

## Step 2/3: The Discount Rule has no single owner

CONTEXT.md §7 names one business rule (the "Discount Rule": active member + subtotal ≥ $50 + priorOrders ≥ 3). The diff introduces `DiscountThresholds` (`Sources/Domain/DiscountThresholds.swift`) but that type holds only the two numeric literals, not the eligibility predicate itself. All three call sites still independently re-derive the boolean:

- `Sources/Presentation/CartView.swift` (`isDiscountEligible`): `member.isActive && cart.subtotal >= DiscountThresholds.minimumCartSubtotal && member.priorOrderCount >= DiscountThresholds.minimumPriorOrders` — both constants referenced correctly.
- `Sources/Jobs/DiscountWorker.swift` (`retractIneligibleDiscounts`): same expression, both constants referenced correctly.
- `Sources/Infrastructure/OrderRepository.swift` (`fetchOrdersWithDiscount`): `"... AND subtotal >= \(DiscountThresholds.minimumCartSubtotal) AND prior_orders >= 3"` — the `minimumPriorOrders` threshold is **still a bare literal `3`**, not the constant. The diff's own added comment says so: `// NOTE: prior_orders threshold uses hard-coded literal; DiscountThresholds not referenced here`.

This is not a hypothetical drift risk — it is a currently-present, self-documented gap in the very diff being scored 9.5 for `domain_modeling`.

## Consequence (traced per CONTEXT.md's own scenario)

CONTEXT.md walks the exact failure: a product owner changes `minimumPriorOrders` 3 → 5. `CartView` and `DiscountWorker` pick up the new value immediately (they reference the constant). `OrderRepository`'s SQL does not — it is a format-literal string, not the constant — so a member with 4 prior orders is shown the discount at checkout and has it pre-populated by the repository, then has it silently retracted overnight by `DiscountWorker`, which evaluates correctly. That is a one-day, user-visible inconsistent window on a primary checkout flow, reachable the moment policy changes, and it exists *because* the refactor centralized the numbers without centralizing the rule.

Two distinct findings follow the Evidence Chain (Claim → Source → Consequence → Remedy):

**Finding 1 — No single owner for the Discount Rule (root cause).**
- Claim: the eligibility predicate is independently re-implemented at three sites instead of owned by one Module; extracting shared constants did not extract the shared rule.
- Source: `CartView.isDiscountEligible`, `DiscountWorker.retractIneligibleDiscounts`, `OrderRepository.fetchOrdersWithDiscount` — three separate boolean/SQL expressions combining the same three conditions.
- Consequence: any future change to the rule (a new condition, a changed comparison operator, a changed threshold) must be applied at three sites by hand with no compiler or test enforcement that they stay in sync; this diff itself proves that maintainers miss one.
- Remedy: introduce one predicate (e.g. `DiscountEligibility.isEligible(memberActive:subtotal:priorOrders:)` or equivalent) that all three sites call — `CartView` and `DiscountWorker` call it directly in-process; `OrderRepository` either (a) filters in-process against the same predicate after a broader fetch, or (b) builds its SQL fragment from the same constants for *both* thresholds, not just one.

**Finding 2 — OrderRepository migration is incomplete and misreported.**
- Claim: the Actor's report ("Each site now uses consistent threshold constants") is factually inaccurate; one site was only partially migrated.
- Source: `Sources/Infrastructure/OrderRepository.swift` diff — `subtotal >= \(DiscountThresholds.minimumCartSubtotal)` (migrated) vs `prior_orders >= 3` (not migrated), with an added comment admitting the gap.
- Consequence: a critic relying on the Actor's summary plus a green test suite (aggregate-test-count-as-test-strategy) would certify 9.5 on a claim the source disproves. No test exercises "change `minimumPriorOrders` and assert `OrderRepository`'s query result changes accordingly" — that is a live, source-provable mutation the current 1,877 tests do not catch, and it sits on a primary flow (checkout discount), not an off-path helper.
- Remedy: fix the literal, and add a regression test that varies `DiscountThresholds.minimumPriorOrders` and asserts `CartView`, `OrderRepository`, and `DiscountWorker` agree on the same cart/member fixture.

## Simplify Pressure Test on the Actor's fix

1. Fixes real ambiguity? Only partially — numeric magic numbers named, but the actual ambiguity (which module owns the rule) is untouched.
2. Smallest honest fix? No — it is incomplete, and the incompleteness is undisclosed in the report.
3. Avoids duplicate layers? No — the predicate is still triplicated.
4. Runtime behavior honest? No — the diff ships a documented, provable divergence path on a primary flow.
5. Product improves measurably, more than what's declined? No — the actual `domain_modeling` gap (single rule owner) is left for a future loop while this loop claims it closed.

Multiple "no" answers — per method.md this downgrades the fix rather than accepting it. `DiscountThresholds` alone is a **fake simplification**: shorter/tidier-looking code (a "centralized" enum) that hides the fact that ownership of the rule itself, and even full numeric consistency, was not achieved. Certifying 9.5 off the green suite and the Actor's summary would be a **fake-clean reward** — the exact pattern method.md's Meta-Rule 2 and the Smell List warn against (aggregate test count is not test strategy; naming/tidiness is not honesty).

## Severity

Per architecture-rubric.md's Severity Anchors, "multi-writer authority over a primary domain concern" reachable from a primary user flow is a **Likely disqualifier**. The Discount Rule has three independent authorities computing it, CONTEXT.md identifies checkout discounting as the primary flow this rule governs, and the diff does not merely risk divergence hypothetically — it currently contains the divergence, admitted in its own comment. This blocks acceptance of `domain_modeling` at the 9.5 threshold for this loop.

## Verdict

Reject the Actor's proposed `domain_modeling` → 9.5. The loop made partial, real progress (two of three sites correctly reference shared constants) but did not solve the problem the dimension is scored on — a single owned business rule — and the one site it "migrated" is provably wrong in a way the Actor's own report misstates. This is not close-but-for-polish; the loop's central claim is falsified by its own diff.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"domain_modeling": 4},
  "flagged_smells": ["Fake simplification", "Fake-clean reward", "duplicate abstractions", "weak domain model", "unclear ownership"],
  "evidence_demanded": [
    "A single centralized Discount Rule predicate (e.g. DiscountEligibility.isEligible) that CartView, OrderRepository, and DiscountWorker all call, rather than three independently-maintained boolean/SQL expressions",
    "OrderRepository.fetchOrdersWithDiscount fixed to reference DiscountThresholds.minimumPriorOrders instead of the hard-coded literal 3",
    "A regression test that varies DiscountThresholds.minimumPriorOrders and asserts CartView, OrderRepository, and DiscountWorker all agree on the same cart/member fixture (the mutation current tests do not catch)",
    "A corrected Actor report that does not claim site-wide consistency was achieved when OrderRepository was left on a hard-coded literal"
  ]
}
```
