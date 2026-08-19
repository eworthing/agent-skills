# Review: Loop 4 — domain_modeling (LeagueRoster One-League Rule centralization)

## Summary

I reject this loop. The diff as presented does not compile, which directly contradicts the
Actor's claim of "2,041 passed, 0 failed." Beyond that specific defect, there is a second,
independent correctness risk in the same code (a classic Swift exclusivity-access conflict), and
the diff's own shape leaves open whether the prior unguarded mutation path was actually removed.
None of these are cosmetic — each bears directly on whether "the invariant lives exclusively
inside `LeagueRoster.addPlayer(checking:)`" is actually true, which is the entire claim this loop
is asking to be scored at 9.5.

## Finding 1 (blocking): `RosterView.handleAdd` will not compile as shown

```swift
private func handleAdd(_ player: Player) {
    do {
        try store.addPlayerToCurrentRoster(player)
    } catch RosterError.playerAlreadyInLeague(let p, _) {
        store.presentError(.playerAlreadyInLeague(p))
    }
}
```

`handleAdd` is not declared `throws`. `addPlayerToCurrentRoster` is declared as ordinary
`throws` — untyped, so it can throw `any Error`, not narrowed to a single `RosterError` case —
and `RosterError` itself has at least two cases in scope in this file alone
(`playerAlreadyInLeague` and, per `RosterStore.addPlayer(toLeague:)`, `leagueNotFound`). A
`do-catch` with only one specific-pattern `catch` clause and no catch-all is not exhaustive.
Swift's rule is explicit: an unhandled error inside a `do-catch` may propagate only when the
enclosing function is itself a throwing context; inside a non-throwing function, the catch set
must be exhaustive or the code fails to compile ("errors thrown here are not handled because the
enclosing catch is not exhaustive"). `handleAdd` has neither a `throws` signature nor a catch-all
clause.

This isn't a nitpick: it means the diff as described could not have produced a project that runs
2,041 tests, let alone passes them. Either the `scenario.md` diff doesn't match what was actually
compiled and tested, or the report is simply wrong. Both are disqualifying for a domain_modeling
claim whose only supporting evidence is "full suite green."

## Finding 2 (needs verification before acceptance): exclusivity-access risk in both new `RosterStore` methods

```swift
func addPlayerToCurrentRoster(_ player: Player) throws {
    try rosters[currentRosterIndex].addPlayer(player, checking: rosters)
}
...
try rosters[idx].addPlayer(player, checking: rosters)
```

Both new methods call a **mutating** method on an element of `rosters`
(`rosters[i].addPlayer(...)`, which requires exclusive/write access to the whole `rosters` array
for the call's duration so the mutated element can be written back) while, in that same call,
passing `rosters` itself as a second argument — a read access to the same storage. This is the
textbook shape of Swift's exclusivity-access conflict (`array[i].mutatingMethod(array)`), which
shows up either as a compile-time "overlapping accesses" diagnostic or, once it's behind a
class/`@Published` property (as `rosters` is here, on `RosterStore`), as a runtime trap
("Fatal error: Simultaneous accesses to 0x..., but modification requires exclusive access") the
first time either method actually runs.

Given Finding 1 already shows the reported "green suite" can't be taken at face value, I have no
basis to assume this second risk was exercised and found safe. If a test really did drive
`addPlayerToCurrentRoster` or `addPlayer(toLeague:)` end-to-end, a crash here would be hard to
miss — which makes it more likely these new call paths simply weren't exercised by whatever ran.

## Finding 3 (evidence gap): does the old bypass method still exist?

The pre-diff call sites shown are `store.addPlayer(player)` (View) and
`await store.addPlayer(player)` (ImportService) — i.e., an existing, unguarded
`RosterStore.addPlayer` method both call sites are migrated away from. The `RosterStore.swift`
hunk, however, shows only additions between the stored properties and the closing brace, with no
`-` line removing that old method. Either the hunk is non-exhaustive and elides the removal, or
the old unguarded method is still sitting in the class — unused by these two call sites but still
callable from anywhere else in the codebase (other views, previews, seed/test code). The claim
that the invariant "lives exclusively" in the domain method requires the old bypass to be gone,
not just unreferenced by the two sites shown. The diff doesn't establish that either way.

## On the design itself, independent of the bugs above

Setting the defects aside, there's a more debatable structural weakness worth naming:
`LeagueRoster.addPlayer(_:checking:)` enforces a **League**-scoped invariant (no player on two
rosters in the same league) from inside a single-roster value type that has no independent way to
obtain its siblings — it depends on every caller to hand it a correct, live, complete
`allRosters` snapshot. That is not the invariant "living exclusively" in the domain type; it's the
domain type performing the check correctly *given correct input*, while responsibility for
supplying correct input stays distributed across every caller (today, `RosterStore`'s two
methods; tomorrow, anything else that ever touches `LeagueRoster.addPlayer`). Nothing in the type
system stops a future call site from passing a stale or filtered array. A `League`/roster-
collection aggregate that owns the full set and is the sole thing permitted to mutate any roster's
membership would make the invariant structurally impossible to bypass rather than conventionally
impossible. I'm not scoring this as a standalone blocker on its own — it's a legitimate
architecture conversation — but it weakens the "single authoritative enforcement point" claim even
in the best case where Findings 1–3 are resolved.

## What would change my verdict

- A real, current build log (not a hand-summarized diff) showing the project compiles clean after
  this change.
- A fix to `RosterView.handleAdd`: either give it a `throws`/async-task path that lets unmatched
  errors propagate, or add a catch-all clause.
- A concrete answer on the exclusivity risk — a test that actually drives
  `addPlayerToCurrentRoster` / `addPlayer(toLeague:)` end-to-end through `RosterStore` (not just a
  unit test against `LeagueRoster` in isolation, which would sidestep the
  `rosters[i].addPlayer(..., checking: rosters)` call shape entirely), or a code change that
  copies-then-checks to remove the aliasing.
- Confirmation, via grep/build evidence rather than narrative, that the old unguarded
  `RosterStore.addPlayer` no longer exists or is provably unreachable.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical (build-breaking: non-exhaustive catch in a non-throwing function contradicts the reported green suite)", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["non-exhaustive error handling (compile-breaking) in RosterView.handleAdd", "exclusivity/aliasing risk from mutating rosters[i] while passing rosters as an argument in the same call", "leaky invariant enforcement / questionable aggregate boundary — LeagueRoster depends on every caller to supply a correct sibling snapshot rather than owning the collection itself", "unverified bypass path — diff does not show removal of the prior unguarded RosterStore.addPlayer", "report/reality mismatch: claimed full green suite vs. code that will not compile as shown"], "evidence_demanded": ["actual compiler/CI build log proving the project builds after this diff", "the corrected RosterView.handleAdd (throws context or catch-all) and proof it compiles", "an end-to-end test through RosterStore.addPlayerToCurrentRoster / addPlayer(toLeague:) that adds a player to two rosters in the same league and confirms no crash and correct rejection", "grep or build evidence that the prior unguarded RosterStore.addPlayer no longer exists or is unreachable", "confirmation LeagueRoster has no other pre-existing mutating method that writes activePlayers without the checking invariant"]}
```
