# Critic Review — Loop 7, `data_flow` dimension

## Scope

Only `scenario.md`, `architecture-rubric.md`, and `method.md` were used. Per Step 1's
anchor-to-source rule, the Actor's report is treated as a claim to verify, not a verdict to
echo — the scorecard below is re-derived from the diff and CONTEXT.md excerpt, not copied from
`loop_result`.

## Step 2 — Authority Map

- **Concern:** order placement + its audit trail.
- **Owner:** `OrderService.placeOrder` — sole writer of both `Order` and `OrderAuditEntry`, before
  and after this diff.
- **Before:** two sequential `db.insert` calls, no shared transaction — a crash or throw between
  them leaves an `Order` with no matching `OrderAuditEntry` (partial-write window).
- **After:** both inserts happen inside one `db.transaction { tx in ... }` closure. Single writer,
  single atomic unit. No second writer introduced, no new mutable field, no ambiguity.

This is a strict improvement in ownership clarity: one owner, one atomic write, same as before.

## Step 3 — Architecture / Seam review

No new Seam, Interface, protocol, or Module is introduced. `db.transaction` is an existing
`Database` primitive being *used*, not a new abstraction being *built*. Checked against the smell
vocabulary:

- Architecture costume layer — no. No sidecar type, no rule-driven split.
- Repository theater / protocol soup — no. No protocol introduced.
- Fake simplification — no. The shorter code path (one transaction vs. two sequential awaits) does
  not hide ownership, failure behavior, or async lifetime — it makes failure behavior *more*
  honest (an inner throw now rolls back both writes instead of silently leaving one applied).
- Adapter output contract incompleteness / unstable shaped output / stable workflow identity /
  causal runtime context / reservation after suspension / state with no authority — none apply;
  none of the preconditions for these smells (adapter facts, projections, positional identity,
  ambient state, check-then-claim races, write-only fields) are present in this diff.

**Deletion test:** delete the transaction wrap, revert to two sequential inserts — the partial-
write window reappears immediately. The wrap earns its keep; this is not a pass-through.

## Step 6 — Simplify Pressure Test

1. Fixes real ambiguity? Yes — closes the partial-write window between order and audit insert.
2. Smallest honest fix? Yes — reuses an existing `Database.transaction` primitive; no new type,
   no new seam, four-line diff.
3. Avoids duplicate layers? Yes.
4. Runtime behavior stays honest? Yes — behavior is *more* honest than before (atomic vs.
   sequential-with-gap), and no suppression or silenced warning is involved.
5. Product improves, measurably, more than what's being declined? Yes — it directly satisfies a
   named regulatory requirement (below), and nothing else was on the table for this loop.

All five pass; the structural gate (friction proven — the partial-write window is the friction;
no new Seam to test against the Unified Seam Policy) also passes.

## CONTEXT.md check — and the context-sufficiency cap

CONTEXT.md §6 states the rule directly: *"A placed order must always have a matching audit entry
(regulatory: order history must be reconstructable). Audit entries must be strongly consistent
with their orders."* This is exactly the kind of business/regulatory rule the rubric's
context-sufficiency cap exists to protect against being certified on the Actor's say-so alone —
**but the cap only fires when that rule is absent from CONTEXT.md/ADRs**, and here it is not
absent; it is stated in terms specific enough to grade against ("strongly consistent," not
"eventually"). The rubric's own carve-out also covers this case on independent grounds: "an
aggregate's own internal writes are atomic by definition" — `Order` and its `OrderAuditEntry` are
one aggregate's own writes, both staying in the core database with (per §4) no planned extraction.
Capping this dimension for missing context would be over-reach here; the context is present and
the fix matches it exactly.

Also checked: §4 flags a *future* extraction of Inventory into its own datastore. The diff does
not touch inventory at all — only `Order` and `OrderAuditEntry`, both explicitly staying in the
core database. The Actor did not preemptively couple this fix to the roadmapped extraction, and
did not need to.

## Step 8 — Tests

Actor cites the full suite green (2,488/2,488). No specific test is cited that exercises the new
failure path directly — e.g., forcing the audit insert to throw and asserting the order insert is
also rolled back. Per the "aggregate-test-count-as-test-strategy" caution, a passing count alone
doesn't prove the *new* invariant holds; it only proves nothing else broke. That said, this is not
scored as a blocking gap for `data_flow`: `db.transaction` is an existing, presumably
already-exercised primitive being reused, not novel concurrency or transaction logic written in
this diff, so the risk is low and this doesn't meet the bar for a Serious or Noticeable finding on
its own. It is flagged below as evidence I'd want, not a blocker.

## Verdict

No structural finding blocks acceptance at 9.5 for `data_flow`. The change is a minimal,
subtractive-leaning fix (net: same call count, now correctly scoped inside one transaction) that
directly satisfies an explicit, specific CONTEXT.md consistency requirement, introduces no new
seam or costume layer, and passes the deletion test and full Simplify Pressure Test.

```json
{"verdict": "approved", "blocks_95": false, "blocking_severity": null, "dimension_scores": {"data_flow": 9.5}, "flagged_smells": [], "evidence_demanded": ["A focused test that forces the OrderAuditEntry insert to throw inside the transaction and asserts the Order insert does not persist — proves the atomicity claim directly rather than relying on aggregate suite-green count."]}
```
