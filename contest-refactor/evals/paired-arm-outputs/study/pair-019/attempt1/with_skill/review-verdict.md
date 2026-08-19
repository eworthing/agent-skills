# Critic Review — Loop 4, `domain_modeling`

## Scope note

Per sandbox constraints, this review is derived only from `scenario.md`, `architecture-rubric.md`,
and `method.md`. No live repository, git history, or other files were read. All evidence below
cites lines as shown in the diff in `scenario.md`; nothing beyond that diff was inspected.

## Authority Map (from diff only)

- **`activePlayers` on `LeagueRoster`** — owner: `LeagueRoster` (value type). Writer: `addPlayer(_:checking:)` (new, appends after invariant check). No other writer shown in the diff.
- **`rosters` on `RosterStore`** — owner: `RosterStore` (`@MainActor`, `@Published private(set)`). Writers: `addPlayerToCurrentRoster`, `addPlayer(_:toLeague:)` (both new). Readers: same two methods (pass `rosters` into the domain check), plus presumably SwiftUI observers via `@Published`. Single-owner, MainActor-serialized — the concurrency shape is sound in principle (see Finding 1 for why the *mechanism* undermines this).
- **Entry points**: `RosterView.handleAdd` (sync, main actor) and `ImportService.importRoster` (actor, `await`s into `RosterStore`). Both route through the store rather than performing local guards — this satisfies the stated intent of "single authoritative enforcement point."

The *design* — pushing the One-League Rule into `LeagueRoster.addPlayer(checking:)` and having both callers route through `RosterStore` rather than duplicating guards — passes the Deletion Test (delete the domain method, the guard logic reappears at both call sites) and is the right shape for this invariant. The problem is not the design; it is the concrete implementation of the two `RosterStore` entry points that are supposed to *be* the single authority.

## Finding 1 — Self-referential mutation crosses Swift's exclusivity boundary at the one and only enforcement point

**Claim.** Both new `RosterStore` methods call the mutating domain check by reading the same
property they are mutating, in the same expression, as a plain (non-`inout`) argument:

```swift
try rosters[currentRosterIndex].addPlayer(player, checking: rosters)
...
try rosters[idx].addPlayer(player, checking: rosters)
```

`rosters[i].addPlayer(...)` is a call to a `mutating func`, which requires an exclusive
(read-write) "modify" access to the base storage — here, the whole `rosters` array/property
(subscript mutation on `Array` is not proven element-disjoint by the compiler; the formal access
spans the base variable, not just index `i`). That access window is open for the duration of the
call, including argument evaluation. `checking: rosters` is a second, *read* access to that exact
same storage, evaluated while the modify access is still open. This is materially the same shape
Swift's own exclusivity documentation calls out as a conflict (`f(&x, x)` / `oscar.shareHealth(with:
&oscar)`): a mutating access and a same-call read of the identical storage overlap. Depending on
whether the compiler can statically prove the alias (harder here because `rosters` is a
`@Published` class stored property, which typically routes through get/set materialization rather
than a `_modify` on the property itself), this either fails to compile, or compiles and traps at
runtime with Swift's dynamic exclusivity check ("Simultaneous accesses to 0x..., but modification
requires exclusive access").

**Source.** `Sources/Application/RosterStore.swift`, both new bodies:
`addPlayerToCurrentRoster(_:)` — `try rosters[currentRosterIndex].addPlayer(player, checking:
rosters)`; `addPlayer(_:toLeague:)` — `try rosters[idx].addPlayer(player, checking: rosters)`. Both
are the *only* call sites that exercise `LeagueRoster.addPlayer(_:checking:)` — i.e., the only
paths that enforce the One-League Rule at all.

**Consequence.** This is not an edge case; it is the entire mechanism. If it doesn't compile, the
loop's diff cannot possibly have produced "2,041 passed, 0 failed" as claimed. If it compiles and
traps at runtime under dynamic exclusivity enforcement (the default for `swift test` debug builds),
then every real invocation of `addPlayerToCurrentRoster` or `addPlayer(toLeague:)` — i.e., every
add-a-player user action and every CSV import row — crashes the process. Either way, the "single
authoritative enforcement point" this loop set out to build is either unbuildable or unusable on
the two flows it was supposed to protect (`RosterView.handleAdd`, `ImportService.importRoster` —
both primary user flows for this domain). The claimed green suite is inconsistent with the diff as
shown: either the tests don't actually call these two methods (a coverage hole on the very
behavior the loop claims to have fixed), or the reported result does not reflect what this diff
does. This is a `Likely disqualifier` under the rubric ("core architectural property... broken at
runtime AND reachable from a primary user flow").

**Remedy.** Smallest behavior-preserving fix: snapshot `rosters` into a local `let` before the
mutating subscript call, e.g. `let snapshot = rosters; try rosters[idx].addPlayer(player, checking:
snapshot)`. This breaks the aliasing (the argument reads a separate copy made before the mutating
access begins) without changing the invariant semantics, since `checking:` only needs a
pre-mutation view of the roster set.

## Finding 2 — Non-exhaustive catch in `RosterView.handleAdd`

**Claim.** The new body catches one specific error case with no catch-all, inside a function not
declared `throws`:

```swift
private func handleAdd(_ player: Player) {
    do {
        try store.addPlayerToCurrentRoster(player)
    } catch RosterError.playerAlreadyInLeague(let p, _) {
        store.presentError(.playerAlreadyInLeague(p))
    }
}
```

`addPlayerToCurrentRoster` is declared plain `throws` (not typed `throws(RosterError)`), so the
compiler cannot prove the `do` block only ever throws `.playerAlreadyInLeague`. Swift requires
either an untyped catch-all or a `throws`-annotated enclosing function to cover the remaining
cases; neither is present.

**Source.** `Sources/Presentation/RosterView.swift`, `handleAdd(_:)`, as diffed above.

**Consequence.** As shown, this is very likely a second, independent build failure in the same
diff — again inconsistent with a claimed 2,041/2,041 green run. Even if a broader catch-all exists
outside the shown diff context (possible but not evidenced), the diff as presented does not
demonstrate it, and the Evidence Chain requires the claim to stand on shown source, not assumed
context.

**Remedy.** Add a catch-all (`catch { store.presentError(.unexpected(error)) }` or similar) or
declare `addPlayerToCurrentRoster` with typed throws (`throws(RosterError)`) if the domain
guarantees no other error type can escape.

## Finding 3 — Unresolved: `addPlayer(toLeague:)` resolves to the first matching roster, not a specific one (lower confidence, flagged as an open question)

**Claim.** `RosterStore.addPlayer(_:toLeague:)` resolves its target with `rosters.firstIndex(where:
{ $0.leagueID == leagueID })` — the first roster whose `leagueID` matches. The domain's own stated
invariant ("a player may not be active on two rosters in the *same league* simultaneously") only
makes sense if a league can legitimately contain more than one roster. If that's true here,
`ImportService.importRoster` — which only supplies `row.leagueID`, no roster-specific identifier —
will silently import into whichever roster happens to be first in `rosters` for that league, not
necessarily the roster the CSV row was meant for.

**Source.** `Sources/Infrastructure/ImportService.swift`: `try await store.addPlayer(player,
toLeague: row.leagueID)`; `Sources/Application/RosterStore.swift`: `rosters.firstIndex(where: {
$0.leagueID == leagueID })`.

**Consequence.** If leagues here do host multiple rosters, this is a real target-resolution bug
introduced by the refactor (the pre-refactor code isn't shown well enough to know if it had the
same or a different targeting mechanism). If in practice each league maps to exactly one roster,
this is a non-issue. I don't have enough evidence in the attached materials to resolve this either
way — flagging as an unresolved question rather than a scored finding.

**Remedy (if confirmed).** `ImportService`/`CSVRow` should carry an explicit roster identifier
rather than relying on league-level lookup; `addPlayer(toLeague:)` should fail loudly
(`RosterError.ambiguousRoster` or similar) when more than one roster matches, rather than silently
picking the first.

## Simplify Pressure Test / smell check

- **Design intent** passes the Deletion Test and the Two-Adapter framing isn't applicable (no new
  Seam/protocol was introduced — this is a plain domain method, correctly not over-built with a
  repository/protocol layer around it).
- **Fake-clean reward (aggregate-test-count-as-test-strategy sub-pattern)**: the Actor's report
  leans entirely on "Full suite green (2,041 tests)" as validation that the new invariant path
  works, without citing which specific test(s) exercise `addPlayerToCurrentRoster`,
  `addPlayer(toLeague:)`, or the two-roster-same-league conflict-throw path. Given Finding 1, this
  aggregate count cannot be taken as evidence the new code even runs, let alone that it's correct.
  This is exactly the sub-pattern the rubric names: scoring up on tidy-looking test totals instead
  of auditing the specific surface.

## Verdict

**Rejected.** Findings 1 and 2 are both source-backed, plausible build/runtime breaks in the *only*
code paths that implement this loop's claimed invariant, and both directly contradict the reported
"2,041 passed, 0 failed." The architectural idea (single authoritative enforcement point inside the
domain type, both callers routed through it, no local guards) is correct and exactly what this
dimension rewards — but a design that doesn't survive compilation or execution cannot be scored on
its intent alone (rubric: "Honesty beats polish... unless ownership, seams, runtime authority...
survive source inspection"). `domain_modeling` is capped well below the 9.5 threshold until the
exclusivity hazard is fixed and re-verified, and the catch-exhaustiveness issue is resolved.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"domain_modeling": 3.5},
  "flagged_smells": ["fake-clean reward"],
  "evidence_demanded": [
    "A successful build log for RosterStore.swift and RosterView.swift as diffed, proving rosters[idx].addPlayer(player, checking: rosters) and the non-exhaustive catch in RosterView.handleAdd actually compile",
    "If it compiles: a debug-configuration (dynamic exclusivity enforcement on) test/run log showing addPlayerToCurrentRoster and addPlayer(toLeague:) execute without a 'Simultaneous accesses... exclusive access' trap",
    "Specific test file(s) + test name(s) that exercise the two-roster-same-league conflict path end-to-end through RosterStore (not just LeagueRoster.addPlayer(checking:) unit-tested in isolation with a hand-built allRosters array)",
    "Confirmation of Player's Equatable conformance (identity-based vs structural) used by activePlayers.contains(player)",
    "Clarification on whether a league can hold multiple rosters, and if so how ImportService/CSVRow identifies which specific roster a row targets (vs. addPlayer(toLeague:) picking the first leagueID match)"
  ]
}
```
