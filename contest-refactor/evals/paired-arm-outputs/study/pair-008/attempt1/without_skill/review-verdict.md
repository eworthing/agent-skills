# Review — Loop 4, `domain_modeling` (One-League Rule centralization)

## What the Actor claims

`LeagueRoster.addPlayer(_:checking:)` becomes the sole enforcement point for the One-League
Rule; `RosterView` and `ImportService` are rewired to call through `RosterStore` into that
domain method instead of guarding themselves. Actor reports 2,041/2,041 tests green and
proposes `domain_modeling` → 9.5. I reviewed the diff against that claim rather than accepting
the report at face value, and I do not believe the claim holds up.

## Finding 1 — the diff as shown does not compile (blocking)

```swift
private func handleAdd(_ player: Player) {
    do {
        try store.addPlayerToCurrentRoster(player)
    } catch RosterError.playerAlreadyInLeague(let p, _) {
        store.presentError(.playerAlreadyInLeague(p))
    }
}
```

`handleAdd` is not `throws`, and this `do`/`catch` only matches one specific error pattern.
Swift requires an exhaustive `do`/`catch` (a trailing unconditional `catch { }`) whenever the
enclosing function is non-throwing — a `catch` that only matches one case of `any Error` does
not satisfy that, and the compiler rejects it with "errors thrown from here are not handled
because the enclosing catch is not exhaustive." Nothing in the shown hunk adds a catch-all, and
the diff represents this as the *entire* new function body (it replaces the whole old one-line
body), so there's no elided catch-all sitting in unchanged context either.

This directly contradicts "Full suite green (2,041 tests)." Code that doesn't compile can't run
a test suite. Either the diff shown is not what was actually built (there's an unshown
catch-all, or `handleAdd` is actually `throws`), or the test claim is false. Either way, the
report is not verifiable from the evidence given, and that alone is enough to block acceptance
— I can't independently confirm the loop's central claim ("tests green") against the artifact
I was handed.

## Finding 2 — likely runtime exclusivity trap on the new call sites

```swift
try rosters[currentRosterIndex].addPlayer(player, checking: rosters)
...
try rosters[idx].addPlayer(player, checking: rosters)
```

`rosters` is a class-owned, `@Published` stored-property `Array` of a **struct** type. Calling
a mutating method on `rosters[idx]` opens an exclusive (write) access to the whole `rosters`
storage for the duration of the call (Array's subscript mutation is implemented via a `modify`
accessor over the backing buffer, not a narrow per-element access). Evaluating the `checking:
rosters` argument *inside that same call* re-reads the same storage while the exclusive access
is still open. This is the same shape as the canonical Swift exclusivity violation ("passing a
collection into a mutating call on one of its own elements"), and in my experience this pattern
reliably produces a runtime trap — `Fatal error: Simultaneous accesses to 0x..., but
modification requires exclusive access` — rather than silently working, because Swift's dynamic
exclusivity enforcement is on by default in both debug and release (`-enforce-exclusivity=checked`
is the default; only `unchecked` disables it, which is not something to assume here).

I'm not at 100% certainty on this one without actually running it — Swift's static exclusivity
diagnostics don't reliably catch this shape at compile time, so it may not be visible from
source alone — but it is exactly the pattern this failure mode is known for, and it sits in
both of the loop's headline integration points (`addPlayerToCurrentRoster`,
`addPlayer(toLeague:)`). Given how central these two call sites are to the loop's claim, this
needs to be ruled out with an actual run, not asserted away.

## Finding 3 — "single authoritative enforcement point" is not demonstrated

The diff shows `RosterView` and `ImportService` rewired to call the two new `RosterStore`
methods, replacing `store.addPlayer(player)`. It does **not** show the old `RosterStore.addPlayer`
(the unguarded one both call sites used before) being deleted. If that method — or any other
path that appends to `rosters` or to a `LeagueRoster.activePlayers` — still exists anywhere in
the codebase, the "invariant lives exclusively inside `LeagueRoster.addPlayer(checking:)`" claim
is false; it just lives there *for these two callers*. This is a shotgun-surgery pattern
(rewire known call sites, leave the old unguarded path standing) dressed up as centralization.

Related: `LeagueRoster` is a `struct`. Unless its memberwise/custom initializer is private and
`activePlayers` genuinely has no other in-file mutator, Swift gives structs a synthesized
memberwise initializer that can set `activePlayers` directly at construction time, fully
bypassing `addPlayer`. Nothing in the diff shows this door is closed.

## Finding 4 — the invariant is caller-discipline-enforced, not type-enforced

`LeagueRoster.addPlayer(_:checking:)` takes an `allRosters: [LeagueRoster]` parameter that the
caller must supply correctly for the check to mean anything. The doc comment says "the store
passes `self.rosters`," but nothing in the type system requires that — any caller (present or
future) can pass `[]`, a stale snapshot, or an unrelated array and the method will happily
append the player with no error. For a *domain* invariant enforcement point, this is a weaker
guarantee than the report implies: it's "correct if used correctly," not "correct by
construction." A stronger domain model would put this method on the type that actually owns the
full roster collection (e.g. an aggregate root / `RosterStore`-level enforcement, or a
dedicated `LeagueRosterCollection` type), so there's no way to call it with the wrong data.

## Finding 5 — conflict detection depends on unverified `Player` equality

`allRosters.first { ... $0.activePlayers.contains(player) }` relies on `Player: Equatable`.
If that conformance is structural/full-value (e.g. compiler-synthesized) rather than
identity/ID-based, two `Player` values representing the same person with any differing field
(a re-fetched or slightly stale copy, for instance) would fail to match, and the "hard domain
invariant" would silently pass through a real conflict. `Player`'s equality semantics aren't in
this diff and need to be confirmed before this check can be trusted.

## Verdict

This loop does not clear `domain_modeling` at 9.5, or arguably at all in its current form. The
compile-error finding alone means the "tests green" claim can't be taken at face value, and the
remaining findings (unproven single-enforcement-point claim, caller-trust invariant, unverified
equality) mean that even a compiling version of this diff wouldn't fully deliver what the Actor
report describes. This should go back for rework, not be accepted with conditions — the gap
between the claimed and demonstrated state is too large to conditionally approve.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — unverifiable/contradicted test claim (non-exhaustive catch in a non-throwing function) plus unproven single-enforcement-point claim", "dimension_scores": {"domain_modeling": 2}, "flagged_smells": ["non-exhaustive catch in non-throwing function (compile error)", "possible Swift exclusivity runtime trap (array self-aliasing in mutating call)", "shotgun surgery — old unguarded mutator not shown removed", "caller-trust invariant enforcement (not type-enforced)", "unverified Equatable semantics for conflict detection", "struct memberwise initializer may bypass invariant"], "evidence_demanded": ["Full, current source of RosterView.swift and RosterStore.swift proving the do/catch actually compiles (e.g. an unshown catch-all or handleAdd marked throws)", "A test/run log showing addPlayerToCurrentRoster and addPlayer(toLeague:) execute without an exclusivity trap against a non-empty rosters array", "Repo-wide confirmation that the prior unguarded RosterStore.addPlayer(_:) is deleted or unreachable, and that no other write path to rosters or activePlayers exists", "Player's Equatable conformance definition", "LeagueRoster's full initializer surface, confirming activePlayers cannot be set outside addPlayer"]}
```
