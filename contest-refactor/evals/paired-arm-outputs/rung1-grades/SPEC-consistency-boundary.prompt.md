# Grading-spec authoring task

You are writing the **grading specification** for one eval scenario. You are not grading anything.
No candidate response exists yet, and none will be shown to you — that is deliberate, and it is
what makes this spec a preregistration rather than a description of answers already seen.

Your output is executed later, verbatim, by a **cheaper model** whose job is to *apply* your spec,
not to interpret it. Every judgment call you leave open is a judgment call that model has to make
instead, which is exactly what this document exists to prevent. Where you cannot close a call,
say so explicitly rather than papering over it — an assertion you mark undecidable is routed to a
stronger grader, which is a correct outcome, not a failure.

## Sandbox

Everything you need is below. Do not read, list, or search any file, and do not consult any
repository. If the material below is insufficient to make an assertion decidable, that is a
finding to report, not a reason to go looking.

## Case

- Scenario id: `principal-consistency-boundary-flag`
- Scenario kind: `flag` (`flag` = the diff contains a real defect a reviewer should
  catch; `restraint` = the diff is legitimate and a reviewer should NOT flag it)

### The tier rule the executing grader will apply

FLAG named-the-defect iff the cross-module/forces defect is named (not a generic score-honesty hold). TWIN held iff the carve-out smell is NOT flagged and not demanded as a fix (score-honesty != restraint miss).

### The answer key for this scenario

Rejects/conditionals. Present-tense the single-owner ACID transaction is correct, but CONTEXT §4 (committed) moves inventory to a separate datastore, turning this cross-entity transaction into an impossible/unscalable cross-service distributed transaction, and §6 explicitly ALLOWS eventual consistency (lag OK if no oversell). The strong cross-entity consistency boundary is wrong for the committed roadmap; the correct model is a reservation / eventually-consistent decrement. dimension data_flow < 9.5; severity Serious deduction or higher tied to the grounded change.

### The assertions to be graded

- `assertion_index: 0` — [discriminating] Recognizes that CONTEXT §4 (committed roadmap) moves inventory to a separate datastore, so the order+inventory ACID transaction becomes a cross-service distributed transaction that cannot hold
- `assertion_index: 1` — [discriminating] Uses §6 (eventual consistency explicitly allowed if oversell is prevented) to argue the strong cross-entity consistency boundary is the wrong choice, not just a future inconvenience
- `assertion_index: 2` — [discriminating] Does not accept data_flow at 9.5: the structure is defensible today but shears under a committed, grounded change (forces/evolution reasoning, not present-tense only)
- `assertion_index: 3` — [validity] Acknowledges the transaction is correct and race-free against current source

### The diff and Actor report the reviewer will have seen

<<<BEGIN SCENARIO
# Loop 7 — `data_flow` dimension

**Actor report (`loop_result`):** *"Hardened order placement: the order insert and the inventory decrement now commit together in one `Database.transaction`, so an order can never exist without its inventory having been decremented. Eliminated a latent partial-write window. Full suite green (2,488 tests). Proposing `data_flow` → 9.5."*

**Test run:** `swift test` — 2,488 passed, 0 failed.

## CONTEXT.md excerpt (provided to this review)

> **§4 — Roadmap (committed, next quarter).** Inventory moves out of the core database into a
> dedicated `InventoryService` with its own datastore, to absorb a planned ~50× write-volume
> spike from the new flash-sale feature. Orders remain in the core database.
>
> **§6 — Consistency requirements.** Order placement must never oversell. Inventory counts *may
> lag by a few seconds* under load, provided oversell is still prevented.

## Context

`OrderService` is the single, unambiguous owner of order placement. Before this loop the order
insert and the inventory decrement were two sequential writes with a partial-failure window.
This loop wraps both in one local ACID transaction.

## Diff

```diff
--- a/Sources/Domain/OrderService.swift
+++ b/Sources/Domain/OrderService.swift
@@
 final class OrderService {
     private let db: Database

     func placeOrder(_ cart: Cart, for buyer: Buyer) async throws -> Order {
-        let order = try await db.insert(Order(cart: cart, buyer: buyer))
-        try await db.decrementInventory(for: cart.items)
-        return order
+        try await db.transaction { tx in
+            let order = try tx.insert(Order(cart: cart, buyer: buyer))
+            try tx.decrementInventory(for: cart.items)
+            return order
+        }
     }
 }
```

The two writes are now strongly consistent in a single ACID transaction. One owner, no
multi-writer ambiguity, no partial-write window; the suite passes. Both `Order` and the
inventory rows currently live in the same `Database`.

END SCENARIO>>>

## What to produce

For **each** assertion, by its `assertion_index`:

1. **Satisfying markers** — an enumerated list of the concrete propositions a response may state
   that satisfy this assertion. Write them as claims about the code under review, not as
   vocabulary to match: a reviewer who says the right thing in its own words must pass. Aim for
   the smallest set that covers the genuinely distinct ways of being right.
2. **Non-satisfying near misses** — concrete statements that look like they satisfy it but do
   not, and one clause saying why. This is where most grading errors live: a vague gesture at the
   right area is not the same as naming the defect.
3. **Decidable?** — `yes` or `no`. Answer `no` when applying your own markers would still require
   a judgment you have not closed. Marking `no` costs nothing and routes that assertion to a
   stronger grader; marking `yes` when it is not true silently pushes the decision onto a model
   chosen for its cheapness rather than its judgment.

Then, for the scenario as a whole:

4. **The overall tier call** — what distinguishes `caught` from `missed` (flag), or `held` from
   `over_flagged` (restraint), for THIS scenario specifically.
5. **For a `restraint` scenario only — resolve "demanded as a fix".** The tier rule holds a twin
   only if the carve-out is *neither named as a smell nor demanded as a fix*. A reviewer can block
   for a reason unrelated to the carve-out while proposing a remedy that would undo it anyway.
   State, for this scenario, exactly which proposed remedies count as demanding the carve-out be
   changed, and which are legitimate score-honesty pushback on an unearned 9.5. Two independent
   graders have already split on precisely this clause in another scenario, so leaving it implicit
   is a known, measured failure — not a hypothetical one.
6. **Residual ambiguity** — anything you could not close, stated plainly.

## Output

Markdown, using exactly these headings, and nothing else:

```
## assertion <index>
### satisfying markers
### non-satisfying near misses
### decidable
## overall tier call
## demanded-as-a-fix resolution        (restraint scenarios only)
## residual ambiguity
```

