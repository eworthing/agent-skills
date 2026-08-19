# Review: Loop 5 — `domain_modeling` (Discount Rule centralization)

## What the diff actually does

The Actor's report claims: "Each site now uses consistent threshold constants via
`DiscountThresholds`." The diff does not support that claim, and the diff's own inline
comment contradicts it directly:

```
// NOTE: prior_orders threshold uses hard-coded literal; DiscountThresholds not referenced here
```

`OrderRepository.fetchOrdersWithDiscount` migrated the `subtotal >= 50` literal to
`DiscountThresholds.minimumCartSubtotal`, but left `prior_orders >= 3` untouched as a raw
literal in the SQL string. So of the two constants the Actor introduced, one is not actually
adopted at one of the three call sites. This is a factual misstatement in the loop_result
("consistent threshold constants") that a green test suite did not catch and would not catch,
because nothing in the 1,877 tests asserts cross-site parity of the eligibility rule.

The scenario's own worked example demonstrates the consequence precisely: a product owner
raises `minimumPriorOrders` from 3 to 5, and the app now has three different answers to "is
this member eligible?" for members with 4 prior orders — eligible at the UI, eligible in the
repository query, then retracted overnight by the worker. That is a real, user-facing
correctness bug (a discount is shown, applied, and then silently clawed back), directly caused
by the refactor's incompleteness.

## Why this is a domain-modeling failure, not just a missed literal

Even setting aside the missed `prior_orders` migration, the deeper problem is what
`DiscountThresholds` was supposed to fix and didn't. CONTEXT.md §7 defines a single business
rule — the Discount Rule: "active member, cart ≥ $50, ≥3 prior orders." A correct
domain-modeling fix promotes that *rule* to a first-class, single-source-of-truth concept (a
`DiscountEligibility` predicate/spec type with one `isEligible(member:cart:)` implementation,
or equivalent) that all three sites call. Instead, this loop only extracted the two *numeric
constants* the rule happens to reference, while leaving the boolean predicate itself
hand-written three separate times:

- `CartView`: `member.isActive && cart.subtotal >= T1 && member.priorOrderCount >= T2`
- `DiscountWorker`: the same expression, independently written
- `OrderRepository`: the same logic re-expressed as a raw SQL `WHERE` clause

Three independent expressions of one rule, one of them in a different language (SQL string
interpolation) with no compiler or type-system link back to `DiscountThresholds` at all. Even
if the repository's literal were fixed today, nothing prevents the next change to the rule
(e.g., adding an "account not suspended" clause) from being applied to two of three sites again
— because there is still no single place the rule is *evaluated*, only a single place its
numeric parameters are declared. That's the actual shape of the domain-modeling debt CONTEXT.md
§7 implies should be fixed, and this loop did not fix it. Worse, it's arguably a regression in
legibility: a reviewer skimming the diff sees a `DiscountThresholds` enum and reasonably
assumes the rule is now centralized, when it demonstrably is not (per the diff's own comment
and the repository site).

The green test suite is not evidence against this: 1,877 passing tests reflects that no
existing test exercises the divergence scenario (member with 4 prior orders, threshold changed
from 3 to 5, three sites compared). Passing suite + wrong claim in the loop_result should not
be read as "verified," only as "untested along this axis."

## Verdict

Reject. The claimed outcome ("consistent threshold constants... site-wide") is contradicted by
the diff itself at the `OrderRepository` call site, and the loop leaves the actual domain
concept (the Discount Rule as an evaluable predicate) un-modeled — three independent
hand-written copies remain, one of them un-migrated even to the new constants. This is not a
9.5-caliber domain_modeling change; it's a partial, partially-incorrect one that ships a
concrete correctness bug and should not be accepted at that threshold.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — silent cross-module divergence of a financial/business-eligibility rule, demonstrated to produce a live correctness bug (discount granted then clawed back)", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["duplicated business rule (shotgun surgery) — Discount Rule hand-written independently in three places, one in SQL", "incomplete migration — prior_orders literal left un-migrated at OrderRepository despite loop_result claiming site-wide consistency", "false single source of truth — DiscountThresholds centralizes constants but not the predicate, creating an illusion of DRY-ness", "type-system-invisible drift — SQL string interpolation has no compiler linkage to DiscountThresholds, so future edits can silently diverge again", "test-suite blind spot — no test asserts eligibility parity across CartView/OrderRepository/DiscountWorker, so a green suite masks the defect"], "evidence_demanded": ["A single canonical eligibility predicate/spec type (e.g. DiscountEligibility.isEligible(member:cart:)) consumed by CartView and DiscountWorker, replacing the three hand-written boolean expressions", "OrderRepository's prior_orders literal fixed to route through DiscountThresholds, ideally via a bound query parameter rather than string interpolation of any threshold into raw SQL", "A regression test that fails if any of the three sites diverge from the canonical rule (e.g. a parity/golden test comparing CartView, the repository query's effective predicate, and DiscountWorker for the same fixture members)", "Correction of the loop_result claim, or evidence the 'consistent... site-wide' statement was verified rather than assumed"]}
```
