# Critic review — Loop 4, `domain_modeling`

## What the Actor claims

The Actor reports moving the One-League Rule invariant into a single authoritative
location, `LeagueRoster.addPlayer(_:checking:)`, with both `RosterView` and
`ImportService` now routing through `RosterStore` wrapper methods that call it,
"regardless of which entry path is used." Full suite claimed green (2,041/2,041).

## What I checked

I do not have the live repository or the test suite, only the diff and report in
`scenario.md`. To go beyond echoing the report, I reconstructed the touched types
from the diff exactly as written and ran them.

**First hypothesis, tested and rejected.** My first read of
`rosters[currentRosterIndex].addPlayer(player, checking: rosters)` raised a
suspicion of a classic Swift exclusivity violation (mutating access to
`rosters[idx]` overlapping a read of the same `rosters` array passed as an
argument in the same call). I did not take that on faith — I compiled and ran a
faithful minimal reconstruction (struct + mutating method + class-owned array,
both `-O` and `-Onone -enforce-exclusivity=checked`). It does **not** trap:
Swift evaluates the `checking:` argument before opening the mutating access on
the subscripted element, so the two accesses are sequential, not simultaneous.
I'm flagging that I tested and cleared this so it's not re-raised by another
reviewer without re-verification — the code is safe on this specific concern.

**Second check: does the invariant itself fire correctly?** I reconstructed
`LeagueRoster`, `RosterStore.addPlayerToCurrentRoster`, and
`RosterStore.addPlayer(_:toLeague:)` verbatim from the diff and ran a scenario
with two rosters (two teams) sharing one `leagueID`. Adding the same player to
both, via the two different call sites the diff wires up, is correctly blocked
with `playerAlreadyInLeague`. Credit where due: the cross-roster duplicate
check, as written, works.

**Third check — this is where it breaks.** `RosterStore.addPlayer(_:toLeague:)`
(the method `ImportService` calls) resolves its target roster with:

```swift
guard let idx = rosters.firstIndex(where: { $0.leagueID == leagueID }) else { ... }
```

`leagueID` alone does not identify a specific roster when a league has more than
one roster — which, per `CONTEXT.md`'s own rule text ("a player may not be
active on two rosters **in the same league**"), is not an edge case, it is the
normal case the whole rule exists for. I reproduced this directly: with two
rosters (`Team1`, `Team2`) both in `leagueID: 100`, calling
`store.addPlayer(player, toLeague: 100)` silently lands the player on `Team1`
every time, regardless of which team the CSV row was actually importing for,
because `addPlayer(_:toLeague:)` has no team/roster-level parameter — only
`leagueID`, and `firstIndex` picks whichever roster happens to be first in
`RosterStore.rosters`. No error is thrown; the write just goes to the wrong
aggregate. `ImportService.importRoster` has no way to hit the correct branch
here even for well-formed CSV data.

This does not defeat the One-League *duplicate-detection* check (that check
scans by `leagueID` across all rosters regardless of which one was selected as
the write target, so true duplicates are still caught). But it does defeat the
Actor's broader claim that "both `RosterView` and `ImportService` call through
the domain method" in a way that's correct "regardless of which entry path is
used." `ImportService`'s entry path can silently corrupt team assignment — a
player ends up rostered to the wrong team with no signal to the caller. Whether
`CSVRow` actually carries a team/roster identifier that's being discarded here,
or the import pipeline never had one, is not visible in the diff; either way,
the API shape merged in this loop (`toLeague leagueID:`) cannot express "this
specific team's roster," and the report does not surface that gap.

**Fourth observation — enforcement by convention, not by construction.** The
"single authoritative enforcement point" is only as strong as its callers'
discipline: `LeagueRoster.addPlayer(_:checking:)` trusts whatever `[LeagueRoster]`
it's handed. Both current callers happen to pass `self.rosters` correctly, but
nothing in the type signature prevents a future or third caller from passing a
stale snapshot, a filtered subset, or `[]`, and silently reopening the exact
violation this loop claims to close "exclusively." A design that encapsulated
`rosters` behind the aggregate that owns cross-roster invariants (so callers
structurally cannot supply the wrong collection) would be materially stronger
than a parameter-passing convention.

**Fifth — unverifiable coverage claim.** The diff touches no test file. "Full
suite green (2,041 tests)" is asserted, but nothing in what I was given shows a
test that actually exercises the cross-team-same-league conflict path or the
`addPlayer(_:toLeague:)` resolution path (as opposed to, say, only unit-testing
`LeagueRoster.addPlayer(checking:)` in isolation with a single-roster array,
which would never surface the ambiguity above). I can't take the count as
evidence the new code paths are covered.

**Sixth — silent behavior change.** `ImportService.importRoster` now aborts the
whole batch on the first `playerAlreadyInLeague` or `leagueNotFound` throw
(propagated via `async throws`), where the elided prior call
(`await store.addPlayer(player)`, non-throwing) evidently couldn't fail this
way. That may be the right semantics for a CSV import, but it's an undiscussed
change in fail-fast-vs-best-effort import behavior.

## Verdict

The centralization *pattern* is right, and the actual duplicate-invariant check
is verified correct. But one of the two entry paths the Actor explicitly
credits as "calling through the domain method" resolves its target aggregate
incorrectly in the normal (multi-roster-per-league) case, silently
misassigning data rather than raising an error — a domain-modeling defect, not
a style nit — and the claim of completeness ("regardless of which entry path
is used") is not true as shipped. Combined with no visible test coverage of
the new throwing paths, this doesn't clear a 9.5 bar for `domain_modeling`.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — silent data-integrity defect: aggregate/entity misidentification in the ImportService entry path (addPlayer(toLeague:) writes to an arbitrary roster sharing the leagueID rather than the intended one, with no error raised); no canon severity-anchor file was provided in this sandboxed review, so this label is a plain-language equivalent rather than a quoted rubric term", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["aggregate misidentification / wrong-entity write in addPlayer(toLeague:) (firstIndex(where: leagueID) is not a unique key when a league has >1 roster)", "invariant enforcement by caller convention, not by construction (checking: allRosters trusts any caller-supplied array; nothing prevents a stale or partial snapshot)", "unverified coverage claim (no test diff shown for the new throwing paths despite a specific 'green' count)", "silent behavior change in ImportService (batch import now fails fast on first conflict, previously non-throwing, undiscussed)"], "evidence_demanded": ["Confirm whether CSVRow carries a team/roster identifier distinct from leagueID; if so, fix addPlayer(toLeague:) to resolve the specific intended roster instead of firstIndex(where: leagueID); if not, explain how ImportService is supposed to target the correct team at all", "A test with two rosters sharing one leagueID where importRoster is asked to add a player to the second one, proving it lands on the correct roster (not just that a true duplicate is blocked)", "The actual test(s) — not just the 2,041 count — that exercise LeagueRoster.addPlayer(checking:) through both RosterStore call sites, including the conflict-thrown and leagueNotFound paths", "Confirmation of intended ImportService semantics on partial failure: abort-the-batch (current behavior) vs. best-effort with a per-row error report"]}
```
