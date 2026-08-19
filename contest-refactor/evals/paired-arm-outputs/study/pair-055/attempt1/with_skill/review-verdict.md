# Critic Review — Loop 4, `domain_modeling`

## Step 1: Inspect current code (not the Actor's report)

The Actor's report claims the One-League Rule is now "guarded" in `RosterView` and `ImportService`, and proposes `domain_modeling` → 9.5 on the strength of a green 2,041-test suite. Per Method meta-rule 2 ("Counts are not quality") and Method Step 1 ("Inspect current code only"), the test count is not evidence for this claim — I re-derive from the diff itself.

**What actually changed:**

- `Sources/Domain/LeagueRoster.swift`: `addPlayer` is untouched in behavior — only a doc comment was added ("Callers are expected to pre-validate the One-League Rule"). The domain aggregate that owns `activePlayers` gained **zero** enforcement of its own hard invariant. This is the domain type — the one place with authority over the roster — and it remains, in the scenario's own words, "a plain mutation that trusts its caller."
- `Sources/Presentation/RosterView.swift`: a guard clause was added that filters `store.allRosters` by `$0.leagueID == store.currentRoster.leagueID` before calling `store.addPlayer`.
- `Sources/Infrastructure/ImportService.swift`: a **second, independently written** guard clause filters `store.allRosters` by `$0.leagueID == row.leagueID`, with a suspension (`await store.allRosters`) **before** the claim (`await store.addPlayer(player)`).

## Step 2/4: Authority Map

| Concern | Owner (claimed) | Owner (actual) | Notes |
|---|---|---|---|
| One-League invariant | `LeagueRoster` (domain) | **Nobody** — enforcement logic duplicated in `RosterView` and `ImportService` | The domain object exposes an unsafe entry point (`addPlayer`) and documents the danger away instead of closing it |
| `activePlayers` mutation | `LeagueRoster.addPlayer` | Same, but callable directly by any future caller with no validation | Single mutator, but the *validation* gate in front of it has two independent, divergent implementations |

This is a textbook anemic domain model: the aggregate that should protect its own invariant ("One-League Rule," `CONTEXT.md` §3) has been left as a bare setter, and the actual business rule now lives as copy-pasted logic in a presentation view and a background actor — two layers that should not need to know how to validate a domain invariant at all.

## Step 5/6: Concurrency cross-check (Method Step 5, canon smell "Reservation after suspension")

This is the finding that moves the verdict from "sloppy but contained" to disqualifying.

`ImportService.importRoster` is:

```swift
let activeRosters = await store.allRosters.filter { ... }   // CHECK (suspends)
guard activeRosters.isEmpty else { throw ... }
await store.addPlayer(player)                                 // CLAIM (suspends again)
```

Per architecture-rubric.md's canon smell definition: *"a check-then-claim flow that suspends (`await`) between 'this slot/resource/work item is available' and 'this attempt owns it' is reentrant: another task can pass the same check during the suspension and both can commit."* The carve-out only applies when *"the actual authority rechecks and atomically claims in one transactional / actor-isolated / unique-constraint step."* It does not here — `LeagueRoster.addPlayer` was explicitly left as a trusting, non-revalidating mutation (see the diff comment itself: "Callers are expected to pre-validate").

The window is not hypothetical:

1. `ImportService` (its own actor) awaits `store.allRosters` to check the invariant.
2. While suspended, `RosterView`, running synchronously on the main actor with **no await between its own check and its own `store.addPlayer` call**, can add the same player to a roster in the same league.
3. `ImportService` resumes with a now-stale "no active roster" result, passes its guard, and calls `store.addPlayer` — the exact invariant violation the whole loop was supposed to close.

This is precisely "racing async flows that can corrupt user-visible state," one of the Severity-Anchor examples for **Likely disqualifier**, and it sits on the primary flow named in `CONTEXT.md` §3 (bulk import is an explicit first-class flow, not an off-path utility). Per Method meta-rule 4, this loop crossed a risk boundary (actor isolation / check-then-claim across suspension) and the Actor was required to record preserving evidence (a focused concurrency test, or at minimum documented reasoning) in `loop_result`. None was recorded — "Full suite green (2,041 tests)" is a single-config, non-racing test run and proves nothing about this interleaving (meta-rule 4: "A green single-config test run does not prove preservation of every invariant... a data race passes nondeterministically").

## Step 6: Duplication sweep

The two guard blocks are near-identical business logic (same predicate shape, same domain rule) living in two unrelated layers (`Presentation`, `Infrastructure`) instead of the one layer that should own it (`Domain`). This is copy-paste of domain policy across two behavior-bearing sites with already-diverging inputs (`store.currentRoster.leagueID` vs `row.leagueID`) — satisfies the "three or more sites" bar loosely at two sites *plus* proven behavioral drift risk (the scenario text itself names the exact divergence scenario), which is enough to promote from smoke ("duplicate abstractions," "weak domain model," "unclear ownership") to a Noticeable-or-worse finding on its own, and to Likely-disqualifier once combined with the concurrency hole above.

## Simplify Pressure Test on the Actor's fix

1. Does it fix real ambiguity? No — it relocates the ambiguity into two callers instead of resolving it once at the aggregate.
2. Smallest honest fix? No — two guard blocks is more code, in the wrong place, than one guard in `LeagueRoster.addPlayer`.
3. Avoids duplicate layers? No — this is the duplicate-layer anti-pattern by definition.
4. Runtime behavior honest? No — the doc comment ("callers are expected to pre-validate") documents an obligation the type system and the actual code cannot enforce, and the reservation-after-suspension hole means the invariant *can* be violated at runtime today.
5. Product improvement bigger than what's foregone? No — this "fix" trades a missing guard for a false sense of coverage (2,041 green tests) while leaving the actual authority ungated.

Matches the rubric's own fake-clean fix anti-example shape: ceremony (two new guard blocks) added around an unaddressed ownership problem, not a fix to it.

## Remedy (minimal correction path)

Move the invariant check into the domain layer at the point of mutation: `LeagueRoster` (or the `RosterStore` acting as its actual write authority) should expose something like `addPlayer(_:) throws` that atomically validates the One-League Rule and commits in one step, under one owner, with no suspension between check and claim. Delete both duplicated guard blocks in `RosterView` and `ImportService`; both callers call the single validating entry point and handle its thrown/typed failure. This closes the duplication, the divergence risk, and the reentrancy hole in one move (Method: "prefer subtractive fixes").

## Verdict

Reject. The domain type central to this loop's own stated goal — enforcing the One-League Rule — was left unenforced at its only mutation point, the enforcement logic was duplicated (and already reads different inputs) across presentation and infrastructure, and the infrastructure path has a live check-then-claim suspension window with no atomic recheck at the authority. This is reachable from a primary domain flow (roster add, bulk import) named explicitly in `CONTEXT.md` §3. The green test suite does not touch this — it is a single-config run with no interleaving/concurrency coverage of the new guard logic. `domain_modeling` cannot be certified at 9.5; the aggregate remains anemic and the invariant remains provably violable.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"domain_modeling": 3.0},
  "flagged_smells": ["weak domain model", "duplicate abstractions", "duplicate state", "unclear ownership", "Reservation after suspension"],
  "evidence_demanded": [
    "A single domain-owned entry point (e.g. LeagueRoster.addPlayer(_:) throws, or the RosterStore acting as sole write authority) that validates the One-League Rule and commits the mutation atomically, with no await between check and claim",
    "Deletion of the two duplicated guard blocks in RosterView and ImportService, replaced with calls to the single validating entry point",
    "An executable concurrency/regression test demonstrating that a concurrent RosterView.handleAdd and ImportService.importRoster (or two concurrent imports) cannot both pass a stale check and double-add a player to the same league",
    "Confirmation, or reconciliation, that row.leagueID (ImportService) and store.currentRoster.leagueID (RosterView) are guaranteed to resolve the same league rather than being two independently-derived values that currently happen to agree"
  ]
}
```
