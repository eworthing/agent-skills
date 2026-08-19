# Critic Review — Loop 7, `data_flow`

## Scope

Reviewing only the three attached materials (`scenario.md`, `architecture-rubric.md`, `method.md`) per the sandbox instructions. No other file, git history, or live source was consulted. Per Method Step 1, the Actor's report is treated as a claim to verify, not a verdict to echo — the assessment below is re-derived from the diff and the provided `CONTEXT.md` excerpt independently of the Actor's framing.

## Step 1 — What changed

`OrderService.placeOrder` previously did two sequential, independently-committed writes: insert `Order`, then insert `OrderAuditEntry`. A failure between the two left an order with no audit entry — a partial-write window. The loop replaces this with a single `db.transaction { tx in ... }` closure that inserts both rows and returns the order. No new type, protocol, or module is introduced; no existing Module is removed. This is a same-owner change inside `OrderService`, not a Seam change.

## Step 2 — Authority Map

- **Owner of order placement:** `OrderService`, unchanged — confirmed single-writer both before and after the diff (`Context` section states this and the diff does not touch any other writer).
- **Written state:** `Order` row, `OrderAuditEntry` row. Both writes now happen inside one local transaction on the same `Database` instance (`db`/`tx` — no second store, no cross-service call).
- **No multi-writer ambiguity, no new mutable field, no new async entry point.** The change narrows a failure window; it does not widen ownership or add a state holder.

## Step 3 — Architectural tests

- **Deletion test:** not applicable — nothing is being removed, no Module is up for deletion.
- **Two-adapter rule / Unified Seam Policy:** not applicable — no new or restructured Seam is introduced. This is inlined transactional logic inside the existing owner, not a new abstraction, protocol, or port. Nothing here needs seam justification.
- **Shallow module test:** not applicable, no Interface was added.

No architectural-test failure is triggered by this diff.

## Step 5/6 — Smell sweep

Walking the rubric's named smells against this diff:

- **Architecture costume layer / Repository theater / Protocol soup:** none — no protocol, no sidecar, no new indirection.
- **Fake simplification:** the opposite is true here. The old code *hid* a partial-write failure mode behind two innocuous sequential `await`s; the new code makes the consistency guarantee explicit and enforced by the database, not merely documented. This is a case of removing hidden failure behavior, not introducing it.
- **State with no authority / unstable shaped output / workflow time in presentation / stable workflow identity / causal runtime context / adapter output contract incompleteness / reservation after suspension:** none apply — there is no stored mutable field, no shaped/ordered output, no clock, no positional identity, no ambient "current" state, no externally-owned fact being dropped, and no check-then-claim pattern spanning a suspension point.

No smell on the list is triggered.

## CONTEXT.md cross-check (§4 / §6)

This is the load-bearing check for this loop. Two context facts matter:

- **§6** states the regulatory requirement directly: *"A placed order must always have a matching audit entry... Audit entries must be strongly consistent with their orders."* The diff is a direct, minimal implementation of exactly this rule — not a superset, not a workaround.
- **§4** confirms this doesn't collide with the roadmap: the planned extraction is `Inventory` → `InventoryService` for a 50× write-volume spike. Orders and the audit log are explicitly named as staying in the core database with **no planned extraction**. So wrapping `Order` and `OrderAuditEntry` in one local transaction does not create a future cross-service/distributed-transaction problem — both rows are staying put by the roadmap's own terms. Nothing in this diff touches Inventory.

**Context-sufficiency cap does not fire here.** The rubric's cap exists for the case where a dimension's 9.5 score depends on a consistency rule that is *absent* from `CONTEXT.md`/ADRs — its own worked example is "whether two entities must be strongly consistent." That is precisely the question in play, and unlike the example, the answer is not absent: §6 states it outright. This is also the rubric's own named carve-out territory — "an aggregate's own internal writes are atomic by definition" — Order and its audit entry are both core-database rows owned by the same service with no planned split, so a local ACID transaction is the source- and context-determinable correct choice, not a judgment call resting on the Actor's say-so. Capping this dimension for missing context here would be the over-reach the rubric explicitly warns against, not caution.

## Evidence quality note (non-blocking)

The Actor's only cited evidence is the aggregate suite count (2,488 green), not a dedicated fault-injection/negative test that forces the audit insert to fail and asserts the order insert rolls back. That would be a stronger proof of the specific atomicity claim than an unrelated green suite. I'm not treating this as blocking for `data_flow`: the mechanism being relied on is the database's own transaction primitive (an ACID guarantee), not new application-level rollback logic that could itself be buggy, and the rubric's mutation-test/test-surface guardrails are scoped to scoring `test_strategy`, not `data_flow`, which is the dimension this loop touches. Worth a follow-up test if `test_strategy` is scored later, not a reason to withhold `data_flow` credit now.

## Verdict rationale

Single owner preserved, no new Seam, no smell triggered, no architectural-test failure, and the one place a real judgment call existed (does this consistency requirement hold, and does it conflict with the Inventory-extraction roadmap) is answered affirmatively and explicitly by the provided `CONTEXT.md` excerpt rather than left to the Actor's framing. The fix is the smallest honest change that closes a real, named partial-write hazard. Nothing here rises to Cosmetic-for-contest, let alone a higher severity anchor.

```json
{"verdict": "approved", "blocks_95": false, "blocking_severity": null, "dimension_scores": {"data_flow": 9.5}, "flagged_smells": [], "evidence_demanded": []}
```
