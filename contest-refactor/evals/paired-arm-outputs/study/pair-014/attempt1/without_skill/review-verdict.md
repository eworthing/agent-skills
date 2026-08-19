# Review — Loop 4, `domain_modeling`, proposed 9.5

## What the Actor claims

The Actor reports that the One-League Rule invariant now "lives exclusively" inside
`LeagueRoster.addPlayer(_:checking:)`, that both call sites (`RosterView` and `ImportService`)
route through that single domain method with no guard logic of their own, and that the full
suite (2,041 tests) is green. I reviewed the diff on its own merits rather than accepting that
framing, and found problems serious enough that the "single authoritative enforcement point,
tests green" story does not hold up against what the diff actually shows.

## 1. The new `RosterView.handleAdd` almost certainly does not compile as shown

```swift
private func handleAdd(_ player: Player) {
    do {
        try store.addPlayerToCurrentRoster(player)
    } catch RosterError.playerAlreadyInLeague(let p, _) {
        store.presentError(.playerAlreadyInLeague(p))
    }
}
```

`handleAdd` is not declared `throws`. `addPlayerToCurrentRoster` is declared `throws` with the
default *untyped* `any Error` — there is no `throws(RosterError)` typed-throws annotation
anywhere in the diff. Under untyped throws, the compiler cannot prove that
`RosterError.playerAlreadyInLeague` is the only error that can reach this call site, so a
`do`/`catch` inside a non-throwing function is required to be exhaustive: it needs a trailing
catch-all (`catch { ... }`) or the enclosing function must itself be `throws`. Neither is present
in the diff, and this is the *entire* new function body (the surrounding signature and closing
brace are unchanged context lines, not elided), so there's no catch-all hiding outside the shown
hunk.

As written, this reads as a compile error ("errors thrown from here are not handled because the
enclosing catch is not exhaustive"), which directly contradicts "full suite green (2,041 tests)."
Either the diff doesn't faithfully represent what was actually built (e.g., a catch-all was
dropped when the diff was produced), or the tests didn't actually run against this code. I can't
settle which from a diff alone — that's exactly the kind of gap that should be closed with
evidence, not taken on the Actor's word.

## 2. No evidence the old bypass path was removed

The "before" lines show both call sites previously calling a single-argument `store.addPlayer(player)`.
The `RosterStore.swift` hunk only *adds* `addPlayerToCurrentRoster` and `addPlayer(_:toLeague:)` —
it never shows the old `addPlayer(_:)` being deleted. If that method still exists in
`RosterStore`, the "single authoritative enforcement point" claim is false on its face: there
would be two independent entry points into `rosters`, one of which (the old one) has no shown
connection to the new invariant check. Nothing in a green test run proves this away — passing
tests only show that *existing* tests don't happen to call the orphaned method, not that no code
path can. This is the central claim of the loop, and the diff simply doesn't demonstrate it.

## 3. The invariant is enforced by comment, not by construction

`LeagueRoster.addPlayer(_:checking:)` trusts whatever `allRosters` array the caller hands it. The
doc comment explains that `RosterStore` is expected to pass `self.rosters` — the authoritative
set — but nothing in the type system prevents a future (or already-existing, per point 2) caller
from passing a stale snapshot, a filtered subset, or an unrelated array, and silently defeating
the invariant while still type-checking cleanly. For a domain method whose entire purpose is to
be *the* place a hard invariant is enforced, requiring the caller to voluntarily supply correct
global state — enforced only by a comment — is a materially weaker guarantee than the "installs
a single authoritative enforcement point" framing implies. A tighter design would have the
aggregate that already owns `rosters` (i.e. something shaped like `RosterStore` or a dedicated
`LeagueRosterCollection`) own the mutating operation directly, rather than handing a single
`LeagueRoster` element a callback-shaped dependency on its own siblings.

## 4. Equality semantics of the conflict check are unverified

The check is `$0.activePlayers.contains(player)`, which depends on `Player: Equatable`. The doc
comment's intent is "already active in any roster" — which almost always means "same player
identity" (e.g. same `id`), not "same player struct, field-for-field." If `Player`'s `Equatable`
conformance is structural rather than identity-based, a `Player` value reconstructed from a CSV
row in `ImportService` (via `Player(csvRow: row)`) with any differing field could fail `contains`
and let a genuine duplicate through undetected. Nothing in the diff shows `Player`'s equality
semantics, so this can't be ruled out.

## 5. No test diff accompanies a hard-invariant claim

For a loop whose entire deliverable is "this invariant can no longer be bypassed," I'd expect to
see at least one new test exercising the conflict path through each of the two entry points
(UI add via `addPlayerToCurrentRoster`, import via `addPlayer(_:toLeague:)`) and asserting the
thrown error. The diff shows no test changes at all. "2,041 passed, 0 failed" tells me the suite
didn't regress on whatever it already covered — it does not tell me this invariant is now
covered.

## Verdict

Points 1 and 2 are, on their own, blocking: point 1 is a plausible compile-time defect that
undercuts the "tests green" claim outright, and point 2 means the diff never actually
demonstrates the loop's central architectural claim (single enforcement point). Points 3–5 are
real domain-modeling weaknesses on top of that. This does not clear a 9.5 bar for
`domain_modeling`, and I'm not confident it clears "done" at all without more evidence than the
diff provides.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — likely compile-breaking defect in the shown diff directly contradicts the reported green test run, and the diff never demonstrates removal of the pre-existing bypass entry point that the loop's central claim depends on", "dimension_scores": {"domain_modeling": 3.5}, "flagged_smells": ["non-exhaustive catch under untyped throws (likely compile error)", "dangling/orphaned bypass method not shown removed", "invariant enforced by comment/convention rather than by type", "unverified equality semantics for duplicate-player detection", "no regression test added for the invariant being claimed as fixed"], "evidence_demanded": ["Full current contents of RosterStore.swift confirming the old single-argument addPlayer(_:) method was deleted (or otherwise made unreachable) and is not still callable", "A build log or compiler output showing RosterView.swift's handleAdd actually compiles as diffed, or the corrected version if it doesn't", "A repo-wide search confirming no remaining call site invokes the old addPlayer(_:) signature", "At least one test that drives the conflict path through both addPlayerToCurrentRoster and addPlayer(_:toLeague:) and asserts RosterError.playerAlreadyInLeague is thrown", "Player's Equatable conformance (identity-based vs. structural) to confirm the contains(player) check matches the intended 'same player' semantics"]}
```
