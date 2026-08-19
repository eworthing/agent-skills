# Critic Review — Loop 4, `domain_modeling`

## Step 1 — Inspect current source (not the Actor's report)

The Actor's `loop_result` claims `RosterView` "validates the single-league invariant before
adding a player" and `ImportService` "now also guards the invariant on bulk imports," proposing
`domain_modeling` → 9.5. Re-deriving independently from the diff and the described current state:

- `Sources/Domain/LeagueRoster.swift` — `addPlayer` is unchanged in behavior; only a doc comment
  was added: *"Callers are expected to pre-validate the One-League Rule."* The method body is
  still `activePlayers.append(player)` — an unconditional mutation. `LeagueRoster` is the stated
  domain owner of the invariant (CONTEXT.md §3, "One-League Rule": a player may not be active on
  two rosters in the same league simultaneously) but exposes no operation that can enforce it.
- `Sources/Presentation/RosterView.swift` — `handleAdd` now computes `alreadyActive` by filtering
  `store.allRosters` on `$0.leagueID == store.currentRoster.leagueID && $0.activePlayers.contains(player)`,
  then guards and calls `store.addPlayer(player)`.
- `Sources/Infrastructure/ImportService.swift` — `importRoster` now computes `activeRosters` by
  filtering `store.allRosters` on `$0.leagueID == row.leagueID && $0.activePlayers.contains(player)`
  (behind an `await`), guards, throws `ImportError.playerAlreadyInLeague` on violation, otherwise
  `await store.addPlayer(player)`.

Both guards are independent re-implementations of the same predicate, keyed off two different
sources of "which league": `store.currentRoster.leagueID` vs. `row.leagueID`. The diff's own
commentary already names the consequence: if those two resolve differently, the guards diverge
silently.

## Step 2 — Map the mutable runtime concern

**Concern:** `LeagueRoster.activePlayers`, mutated via `addPlayer`.
**Stated owner:** `LeagueRoster` (domain type).
**Actual write authority:** `addPlayer` — but it performs *no validation*; it "remains a plain
mutation that trusts its caller" (per the scenario's own framing).
**Actual invariant-enforcement authority:** split across two non-domain layers —
`RosterView` (presentation) and `ImportService` (infrastructure) — each holding a private copy
of the predicate.

This is a write authority with no corresponding *validation* authority at the same site. The one
type that could make the invariant unconditionally true (`LeagueRoster`) instead delegates
enforcement to every caller, by convention, with no compiler or runtime backstop if a new caller
(a third import path, an admin tool, a future migration script) forgets to copy the guard.

## Step 3 — Architecture / ownership review

Apply the deletion test to the two guard blocks: delete them, and invariant enforcement
disappears completely — not because they were a pass-through wrapper over real domain logic, but
because they *are* the only logic that exists, duplicated. That is the signature of a **weak
domain model**: the type that owns the state does not own the rule that governs the state.

Apply leverage/locality: one Implementation should pay back across N call sites. Here, the
"Implementation" of the One-League Rule is written twice, by hand, and the two copies have
*already* diverged in which field they read for league identity. That is **duplicate
abstractions**, not shared logic reused at two call sites — and the diff description confirms
the two are on a collision course, not merely stylistically different.

There's also an unaddressed concurrency gap. `ImportService.importRoster` does `await
store.allRosters` (check) and, after filtering off the actor, a separate `await
store.addPlayer(player)` (claim) — two separate suspension points with nothing atomic connecting
them. Because `LeagueRoster.addPlayer` performs no re-validation at the point of mutation, nothing
stops a concurrent `RosterView.handleAdd` (or another import) from passing the same check during
that gap and both committing. This is the canon **reservation after suspension** shape: check
availability, suspend, then commit without re-checking at the point of authority. The carve-out
("the actual authority rechecks and atomically claims in one step") does not apply — the actual
authority (`addPlayer`) does not recheck at all.

## Step 6 / Simplify Pressure Test

Run the Actor's fix through SPT:

1. Does it fix real ambiguity? — No. The ambiguity ("who enforces the invariant") is unchanged;
   it's now enforced twice, by different code, reading different fields.
2. Smallest honest fix? — No. Two hand-written duplicates is a larger, more fragile surface than
   one domain-owned check.
3. Avoids duplicate layers? — No, this *is* the duplicate-layer case: same predicate, two owners.
4. Runtime behavior honest? — No. The report presents the invariant as now "guarded" at both
   sites, but the guard is non-atomic and already documented to be divergence-prone — the
   runtime guarantee is weaker than represented.
5. Product improvement vs. what's being declined? — What's declined is centralizing the rule in
   `LeagueRoster`, which is the smaller, more leveraged fix and was directly available (the loop
   even added a doc comment on `addPlayer` gesturing at the requirement without implementing it).

Three of five fail outright. Per the "Fake-clean fix anti-examples" list, this is closest to the
`UserManager`→`UserService` case: ceremony was added (named guard blocks, new error cases) without
resolving the ownership ambiguity that was the actual defect. That the Actor's report reads as
progress — comments, explicit error branches, a green 2,041-test suite — while ownership is still
split is the **fake-clean reward** pattern by definition ("scoring up because names, comments,
[...] look tidy while ownership [...] [is] weak").

## Step 8 — Test scrutiny

The Actor's evidence is an aggregate count ("Full suite green, 2,041 tests"), not a citation of
which test(s) exercise the invariant *through `LeagueRoster`'s interface*. Per the rubric's
Interface-coverage carve-out, that requires a specific `interface_test_coverage_path` naming
`target_symbol` (here, `LeagueRoster.addPlayer` or a new validating method) and an assertion that
would fail if that symbol's body were replaced with a no-op. None is cited. Naming a mutation the
current tests plausibly do not catch: flip `row.leagueID` to `store.currentRoster.leagueID` (or
vice versa) in one of the two guards — nothing forces a test to fail, because there is no single
Interface test asserting the invariant holds regardless of which layer performs the add. This
mutation sits on a primary flow (roster membership, both interactive add and bulk import), so per
Step 8's guidance this is Noticeable-or-worse on its own, compounding the domain-modeling finding
rather than mitigating it.

## Verdict

This loop does not do what it reports. It does not move invariant ownership into the domain
type; it formalizes and duplicates the pre-existing ad-hoc guard logic across two non-domain
layers, with a documented (by the diff's own commentary) divergence hazard between them, and no
atomic re-check at the actual write authority. Per the Severity Anchors, this matches **Likely
disqualifier**: a core architectural property the rubric rewards (one owner per mutable/invariant
concern) is broken, the invariant is a CONTEXT.md-designated hard domain rule, and the harm is
reachable from two primary flows (interactive roster add, bulk CSV import) — not an off-path
utility.

`domain_modeling` cannot be certified at 9.5. The claimed fix is real in the sense that it does
narrow the previous "no check at all in the ad-hoc callers" gap, but it re-implements rather than
resolves the ownership problem the dimension is scored on, so credit is given only for the
(modest, non-dispositive) improvement in visibility/error-typing, not for closing the invariant.

**Minimal correction path:** give `LeagueRoster` the sole authority — e.g. `mutating func
addPlayer(_:) throws` (or a `Result`-returning variant) that checks `activePlayers` against its
own `leagueID` internally and rejects a duplicate before appending. Have `RosterView.handleAdd`
and `ImportService.importRoster` call that single method and branch on its outcome, deleting both
local guard blocks. This also closes the reservation-after-suspension gap, because the check and
the append become one call into the type that owns the state, rather than two independently
awaited steps with caller-side logic in between.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"domain_modeling": 4.5},
  "flagged_smells": ["weak domain model", "duplicate abstractions", "fake-clean reward", "reservation after suspension"],
  "evidence_demanded": [
    "LeagueRoster owns the One-League Rule check internally (e.g. a throwing/Result-returning addPlayer) instead of trusting callers",
    "RosterView.handleAdd and ImportService.importRoster call through that single validating domain method; both local guard blocks are deleted",
    "A test (or actor-isolation argument) demonstrating the check-and-append is atomic against concurrent add/import calls on the same league, not just sequential-happy-path",
    "A specific interface_test_coverage_path citing test file(s) and assertions on LeagueRoster's interface that would fail if the invariant check were replaced with a no-op, not an aggregate suite-passed count"
  ]
}
```
