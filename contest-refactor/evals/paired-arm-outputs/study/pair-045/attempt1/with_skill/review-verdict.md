# Critic Review — Loop 7 (`data_flow`)

## Method application

**Step 1 — inspect current code only, re-derive independently.** The Actor's report ("hardened
order placement," "eliminated a latent partial-write window," "proposing `data_flow` → 9.5") is
treated as a claim to verify, not a score to confirm. Re-deriving from the diff itself: before
this loop, `placeOrder` performed two independent sequential writes —

```swift
let order = try await db.insert(Order(cart: cart, buyer: buyer))
try await db.insert(OrderAuditEntry(orderID: order.id, action: .placed))
```

— with a real partial-failure window: a crash, cancellation, or thrown error between the two
`await`s leaves an `Order` row with no matching `OrderAuditEntry`. After this loop, both writes
happen inside `db.transaction { tx in ... }`, so they commit or fail together.

**Step 2 — Authority Map.** `Order` and `OrderAuditEntry`: single writer for both is
`OrderService.placeOrder`, via one `tx`. The Context note ("`OrderService` is the single,
unambiguous owner of order placement") is consistent with the diff — no second write site is
shown or implied. No multi-writer hazard, no state-with-no-authority pattern.

**Step 3 — architecture / Seams.** No new Seam, protocol, or Adapter is introduced. The fix calls
an existing `Database.transaction` primitive already implied to exist on `Database`. Unified Seam
Policy doesn't come into play — nothing is being justified as a new seam — so the two-adapter
rule / single-adapter policy tests are not applicable here. No repository theater, no protocol
soup, no architecture costume layer.

**Step 6 — simplification / fake-simplification check.** The closure adds one level of nesting
but does not hide ownership, failure behavior, state transitions, or async lifetime — it does the
opposite: it converts an implicit, undocumented "hope both writes land" behavior into an explicit,
enforced atomic unit. This is the inverse of the *fake simplification* smell, not an instance of
it.

**Simplify Pressure Test (5 questions):**
1. Fixes real ambiguity? Yes — closes a genuine partial-write window between two prior sequential
   writes.
2. Smallest honest fix? Yes — one existing transaction primitive, no new types, no new seam.
3. Avoids duplicate layers? Yes — nothing duplicated; the transaction subsumes both existing
   inserts.
4. Runtime behavior stays honest? Yes — failure behavior is now atomic and explicit rather than
   partial and implicit.
5. Measurable product improvement? Yes, against the dimension in scope: it converts a data-flow
   hazard that could violate a documented regulatory requirement (see below) into a structurally
   guaranteed invariant.

All five clear. No fake-clean anti-example (repository-for-one, needless coordinator, cosmetic
rename, suppressed-warning-as-fix) matches this diff.

**Context-sufficiency cap — checked and does not apply.** The rubric caps a dimension below 9.5
when a score above 9 depends on a business/regulatory/consistency rule that is *not derivable from
source and absent from CONTEXT.md*. Here the opposite is true: CONTEXT.md §6 states explicitly
that "a placed order must always have a matching audit entry (regulatory: order history must be
reconstructable)" and "audit entries must be strongly consistent with their orders." That is
exactly the rule this diff enforces — the decision isn't missing, it's present and satisfied. §4
additionally forecloses the one plausible future risk (a later split of `OrderAuditEntry` into a
separate datastore, which would break a same-database transaction): the audit log is explicitly
scoped as staying in the core database with "no planned extraction," unlike the inventory tables
that are moving out for volume reasons. So there is no missing decision here to halt on, and no
present-but-unresolved conflict between roadmap and implementation — the cap does not fire.

**Smell sweep against the rubric's named list:** reservation-after-suspension (no
check-then-claim pattern — this is two unconditional inserts, not an availability check followed
by a claim), unstable shaped output, workflow time in presentation, stable workflow identity,
causal runtime context, adapter output contract incompleteness, architecture costume /
rule-driven sidecar, repository theater, protocol soup — none apply to this diff. No finding
survives the Evidence Chain (Claim → Source → Consequence → Remedy) because there is no
structural harm to source against a Claim in the first place.

**Scope limits of this review.** Per the sandbox, the only "current source" available for this
loop is the diff and Context excerpt in `scenario.md`; `Database.transaction`'s implementation
(rollback-on-throw semantics, whether the generated `order.id` is visible to a subsequent
statement inside the same open transaction) is not shown. That is a standard, already-existing
primitive being invoked, not new plumbing introduced by this diff, so demanding its internals as
a precondition for accepting *this* loop's change would be speculation beyond the evidence the
rubric warns against, not a grounded finding — it's noted here only as a scope acknowledgment, not
a blocking gap.

## Verdict

The diff is a small, well-targeted, single-owner fix that converts a real (if narrow) data-flow
hazard — a partial-write window between order and audit-log rows — into an atomically-enforced
invariant, and it does so in exactly the way the project's own documented regulatory requirement
(CONTEXT.md §6) calls for, with no roadmap conflict (§4 confirms both tables stay co-located).
Full suite green on 2,488 tests is consistent with (not proof of, but not contradicted by) the
change. No smell in the rubric's vocabulary applies, the Simplify Pressure Test passes on all five
axes, and the context-sufficiency cap does not fire because the governing rule is present and
satisfied rather than absent. `data_flow` accepts at 9.5.

```json
{"verdict": "approved", "blocks_95": false, "blocking_severity": null, "dimension_scores": {"data_flow": 9.5}, "flagged_smells": [], "evidence_demanded": []}
```
