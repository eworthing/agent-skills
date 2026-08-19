## Review: Loop 4 — `domain_modeling`

**Actor's claim:** `RosterView` and `ImportService` now both enforce the One-League Rule, full suite green, propose `domain_modeling` → 9.5.

**What the diff actually does:** it does not touch the problem the dimension is scored on. The domain invariant ("a player may not be active on two rosters in the same league simultaneously") still has no home in the domain layer. `LeagueRoster.addPlayer` is untouched behaviorally — the only change is a doc comment ("Callers are expected to pre-validate the One-League Rule"), which is not enforcement, it's a request for trust. A domain type that depends on every caller remembering to pre-check an invariant before calling a plain mutator is, by definition, not modeling that invariant — it's disclaiming it.

Instead of centralizing the check, the loop duplicated it into two call sites:

- `RosterView.handleAdd` filters `store.allRosters` by `leagueID == store.currentRoster.leagueID` and `activePlayers.contains(player)`.
- `ImportService.importRoster` filters the same shape by `leagueID == row.leagueID` and `activePlayers.contains(player)`.

Both guards reach directly into `LeagueRoster.activePlayers` and `leagueID` from outside the type to reimplement domain logic — textbook Feature Envy: the logic is more interested in `LeagueRoster`'s data than in anything belonging to `RosterView` or `ImportService`. It is also straightforward duplicated code (DRY violation) spanning two architectural layers (presentation and infrastructure), which is worse than duplication within one layer because the two copies now have independent reasons to drift — and the diff's own context section confirms they already read from *different sources of truth* (`store.currentRoster.leagueID` vs. `row.leagueID`). That's not a hypothetical risk, it's an admitted, currently-unverified assumption that those two values are always equal. Nothing in the diff adds a test that pins this equivalence or exercises the divergence case.

This means:

1. The stated goal of the loop (extract the invariant so it has one authoritative owner) was not achieved — the invariant is exactly as un-owned as before, just written out twice instead of implied ad hoc.
2. A third caller of `RosterStore.addPlayer` (there will eventually be one — background sync, a debug console, a test helper, an admin tool) gets zero protection. The domain type still permits any caller to violate the invariant outright.
3. The Actor's report describes this as "RosterView validates... ImportService now also guards the invariant," language that reads as if the invariant is now safely handled. That's misleading relative to what actually shipped: two independent, unverified-equivalent implementations at the edges, with the domain type explicitly disclaiming responsibility in a comment.
4. 2,041 green tests say nothing about this. They confirm the two known call paths behave correctly today under whatever leagueID values currently happen to line up; they cannot and do not prove the two guards are equivalent, nor guard against a third caller, nor guard against one of the two copies being edited without the other being noticed.

Net effect on the `domain_modeling` dimension: this loop moved the problem sideways, not forward. If anything it is a step backward from a maintainability standpoint — the pre-existing "ad-hoc guard logic" is now formalized as apparently-intentional duplicated logic with a comment on the domain method that actively encourages continuing the pattern ("Callers are expected to pre-validate") rather than pointing engineers at a shared enforcement point.

This is not a 9.5-quality domain-modeling change; it does not clear a much lower bar either, since it is the copy-paste-across-layers pattern this dimension exists to catch.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "critical — domain invariant enforcement duplicated across presentation and infrastructure layers instead of centralized in the domain owner; the two copies read divergent sources of truth (store.currentRoster.leagueID vs row.leagueID) with no test proving equivalence",
  "dimension_scores": {
    "domain_modeling": 2
  },
  "flagged_smells": [
    "Shotgun Surgery (invariant duplicated across two layers, both must change together to stay correct)",
    "Anemic Domain Model (LeagueRoster.addPlayer is a plain mutator; invariant enforcement pushed to callers via comment only)",
    "Feature Envy (RosterView and ImportService reach into LeagueRoster.activePlayers/leagueID to reimplement domain logic that isn't theirs)",
    "Duplicated Code / DRY violation (structurally similar guards independently implemented, not shared)",
    "Divergent duplication risk (the two guards already read different leagueID sources with no equivalence test)",
    "Misleading self-report (Actor's language implies centralized enforcement that was not actually built)"
  ],
  "evidence_demanded": [
    "A single domain-level enforcement point (e.g. LeagueRoster.addPlayer(_:) throws, or a validating method on the aggregate that owns all rosters for a league) that both RosterView and ImportService call through, with the duplicated filter/guard blocks deleted from both call sites",
    "Removal of the 'callers are expected to pre-validate' comment in favor of actual enforcement — either a throwing/failable API or a type that makes constructing an invalid state impossible",
    "A regression test that pins the exact divergence risk named in the diff's own commentary: store.currentRoster.leagueID vs row.leagueID resolving to different values, proving the invariant still holds (or currently doesn't) under that condition",
    "A test demonstrating that a third, not-yet-written caller of the roster-mutation API cannot bypass the invariant — i.e. enforcement by construction, not by caller convention"
  ]
}
```
