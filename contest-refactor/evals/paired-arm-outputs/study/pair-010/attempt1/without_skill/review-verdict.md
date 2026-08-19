# Review — Loop 4, `domain_modeling`

## What the Actor claims

The Actor's report says roster management was "refactored" so that both `RosterView` and
`ImportService` "validate the single-league invariant before adding a player," that the full
suite is green (2,041/2,041), and proposes `domain_modeling` → 9.5.

Test-green is true but irrelevant to the claim being made. 2,041 passing tests says nothing
about whether *this specific invariant* is now safely enforced, because nothing in the diff
or the report indicates a new test was added that exercises the invariant across both call
paths (UI add vs. bulk import). "Suite is green" is being used as a stand-in for "the domain
rule is now guaranteed," and those are not the same claim. That gap alone is reason to distrust
the self-report and check the actual change.

## What the diff actually does

Three files touched:

1. **`LeagueRoster.addPlayer`** (the domain owner) — unchanged behavior. The only edit is a
   doc comment: *"Callers are expected to pre-validate the One-League Rule."* The method is
   still an unconditional `activePlayers.append(player)`. The domain type that owns the
   invariant still cannot enforce it and still trusts every caller to have done so correctly.
   This is documentation posing as a guarantee — it compiles the same as before the loop.

2. **`RosterView.handleAdd`** (presentation layer) — gained a local guard: filters
   `store.allRosters` by `$0.leagueID == store.currentRoster.leagueID` and checks
   `activePlayers.contains(player)`.

3. **`ImportService.importRoster`** (infrastructure layer) — gained a *structurally similar but
   independently written* guard: filters `store.allRosters` by `$0.leagueID == row.leagueID`
   instead.

This is not "extracting" the guard logic into the domain — it's the opposite. The invariant
check that should live once, on `LeagueRoster` (or a domain service `LeagueRoster` delegates
to), has been hand-copied into two unrelated layers, each deriving the league id from a
different source (`store.currentRoster.leagueID` vs. `row.leagueID`). The context note in the
scenario spells out the resulting failure mode precisely: if those two league-id derivations
ever diverge, a bulk import can add a player already active in that league and *neither* guard
fires, because each guard only checks its own (already-consistent-with-itself) notion of which
league is being touched. That's not a hypothetical edge case introduced by paranoia — it's the
direct, structural consequence of duplicating an invariant check instead of centralizing it.

## Why this fails `domain_modeling` at 9.5, not passes it

A 9.5-grade domain-modeling change would make the invalid state *unrepresentable* or
*unreachable through the domain object itself* — e.g. `LeagueRoster.addPlayer` becomes
throwing/failable and rejects a player already active in the same league, with both
`RosterView` and `ImportService` reduced to calling that one guarded entry point and handling
the failure. That was available and cheaper than what was actually done (one guard clause
inside `addPlayer`, deleting both ad-hoc filters). Instead:

- The domain type (`LeagueRoster`) still has zero enforcement — it is exactly as anemic as
  before the loop, just with a comment asserting the problem is someone else's job.
- The "someone else's job" is now discharged twice, by two different layers, with two
  independently-maintained copies of the same filter predicate, keyed off two different
  values that are only accidentally equivalent today.
- This is worse for maintainability than the pre-loop "ad-hoc guard logic" the Actor's report
  frames as the starting problem: before, there was one obviously-ad-hoc thing to eventually
  fix; now there are two guards dressed up as the fix, which will read as "already handled" to
  the next engineer and make the divergence bug harder to notice.

This is a textbook "shotgun surgery" / anemic-domain-model smell being introduced in the name
of fixing it. It should not clear a domain-modeling bar at any grade approaching 9.5 — if
anything, the score should reflect that the core problem (invariant not owned by the domain
type) is unresolved and the blast radius of a future fix has grown from one call site to two
divergent ones.

## What would change my mind

- Move the check into `LeagueRoster` itself (or a domain service it owns) as the single source
  of truth, with `addPlayer` becoming throwing/failable on violation.
- Both `RosterView` and `ImportService` calling that one guarded entry point and reacting to
  the failure, with the ad-hoc filter blocks deleted, not duplicated.
- A regression test that specifically proves the invariant holds when exercised through
  `ImportService` with roster/player data shaped so that a naive per-call-site guard (using the
  wrong league-id source) would miss it — i.e., a test that would have failed against *this*
  diff. "2,041 passed" does not demonstrate this; nothing in the report or diff suggests such a
  test exists.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — domain invariant enforcement duplicated outside the domain owner (anemic domain model), with two guards deriving league identity from different sources and no shared source of truth, risking silent invariant violation on import", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["anemic domain model (LeagueRoster still cannot enforce its own invariant)", "duplicated invariant logic across presentation and infrastructure layers (shotgun surgery risk)", "comment-only enforcement ('callers are expected to pre-validate') masquerading as a guarantee", "divergent duplicate guards keyed off different league-id sources (store.currentRoster.leagueID vs row.leagueID)", "test-green used as proxy for invariant-safety with no test actually covering the divergence path"], "evidence_demanded": ["LeagueRoster.addPlayer (or a domain service it owns) rejects/throws on One-League Rule violation, becoming the single enforcement point", "RosterView and ImportService refactored to call that single guarded entry point, with the ad-hoc filter blocks deleted rather than duplicated", "A regression test through ImportService that would fail against the current diff — i.e., one that specifically exercises a case where row.leagueID and store.currentRoster.leagueID could diverge", "Confirmation that no existing test currently asserts the One-League Rule end-to-end for the import path (the reported 2,041-pass count does not establish this)"]}
```
