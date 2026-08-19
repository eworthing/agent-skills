# Critic Review — Loop 4, `domain_modeling`

## Scope and evidence available

This review covers the diff and Actor report in `scenario.md` only (Method Step 1: inspect current code, not the prior report). The Actor proposes `domain_modeling → 9.5` on the claim that the One-League Rule now lives exclusively inside `LeagueRoster.addPlayer(_:checking:)`, with `RosterView` and `ImportService` calling through it and no local guards remaining. I do not have the full contents of `RosterStore.swift`, `RosterView.swift`, or any test file — only the four hunks shown. Per the Evidence Chain, claims that would require material outside those hunks are flagged as evidence gaps rather than asserted either way.

## Step 2 — Authority map

`RosterStore.rosters` (`@Published private(set) var rosters: [LeagueRoster]`) is the only stored, authoritative membership set shown. Write access is contained to `RosterStore`'s file scope. The diff shows exactly two writers that route through the new check: `addPlayerToCurrentRoster` and `addPlayer(_:toLeague:)`. I cannot confirm from the diff alone that these are the *only* writers of `rosters` — the hunk headers (`@@`) show only the added methods, not the full type. The Actor's claim "the invariant check executes once, in the domain type, regardless of which entry path is used" asserts full writer coverage that the given evidence does not establish; per Step 4 ("map actual writers, do not infer from access control alone"), this needs verification against the complete file, not the diff.

## Step 3/4 — Architecture and ownership of the new domain method

`LeagueRoster.addPlayer(_:checking:)` is a `mutating` method on a `struct`, so it cannot itself hold the cross-roster invariant — it depends entirely on the caller supplying a correct, complete, current `allRosters` array. The Actor's doc comment ("checked against live state") is not accurate: `[LeagueRoster]` is a value type, so `checking: rosters` is copied at the call boundary — a snapshot, not a live reference. That distinction only stays harmless because both call sites read `rosters` and mutate it in the same synchronous, non-suspending `@MainActor` statement (`rosters[idx].addPlayer(player, checking: rosters)`), with no `await` between check and append. Nothing about the *type signature* enforces that discipline — a future caller that reads `rosters`, awaits, and only then calls `addPlayer(checking:)` would silently reopen the race the consolidation was meant to close, and the compiler would not catch it. This is a real but currently-dormant hazard, not a proven live bug today (no suspension point exists in either shown call site).

The doc comment's framing — that the domain method is now the sole authority — overstates what the code guarantees: the method is caller-cooperative (it trusts whatever `allRosters` it's handed), not caller-proof. That gap between the claimed guarantee and the actual mechanism is a **misleading abstractions** smell.

## Step 6 — Doc-vs-code / simplify pressure test

The consolidation direction is sound under the Simplify Pressure Test — it removes duplicate guard logic from `RosterView` and `ImportService` (Q1, Q3 pass) — but Q4 ("does runtime behavior remain honest") is undercut by the `RosterView` wiring below, and the doc-comment overclaim noted above.

**`RosterView.handleAdd` as shown does not compile.** `handleAdd` is not marked `throws`, and its `do/catch` has only one pattern-matched clause:

```swift
private func handleAdd(_ player: Player) {
    do {
        try store.addPlayerToCurrentRoster(player)
    } catch RosterError.playerAlreadyInLeague(let p, _) {
        store.presentError(.playerAlreadyInLeague(p))
    }
}
```

Swift requires `do/catch` inside a non-`throws` function to exhaustively handle `Error` — a single pattern-matched `catch` clause with no catch-all does not satisfy that, and the compiler rejects it ("errors thrown from here are not handled because the enclosing catch is not exhaustive"). `store.addPlayerToCurrentRoster` is declared `throws`, so this specific shape is a compile error, not a style nit. That directly contradicts the Actor's "Full suite green (2,041 tests)" — a non-compiling target cannot produce a passing test run. Either the hunk is missing a catch-all that exists in the real file, or the report's test claim is false; either way it is not verifiable from the given evidence, and the burden is on the Actor to show a green build, not on the reviewer to assume one.

## Step 8 — Tests

No test file appears in the diff. The new throwing Interface (`LeagueRoster.addPlayer(_:checking:)`) has no direct test shown for either the conflict-throws path or the success path, and no test demonstrating that `RosterStore`'s two entry points pass `rosters` (not a stale or filtered subset) into the check. Citing aggregate suite size ("2,041 tests... green") without a direct test at the new Interface is exactly the **aggregate-test-count-as-test-strategy** sub-pattern the rubric calls out under fake-clean reward — it is not itself proof the invariant behaves as claimed, especially given the build-error finding above.

## Findings (Evidence Chain)

**F1 — Consuming code as diffed does not compile, contradicting the reported green suite.**
- Source: `Sources/Presentation/RosterView.swift`, `handleAdd(_:)` — non-`throws` function, `do/catch` with only `catch RosterError.playerAlreadyInLeague(let p, _)`, no catch-all.
- Consequence: invalidates the Actor's central evidence for `domain_modeling → 9.5` (tests cannot be green over non-compiling code); the primary "add a player" user flow is unverified end to end.
- Remedy: add a catch-all (`catch { store.presentError(.unknown(error)) }` or similar) or mark `handleAdd` `throws` and handle upstream; then show a passing build/test log for this file.
- Severity: Likely disqualifier (breaks the primary add-player flow's verifiability; report's central claim is contradicted by its own diff).

**F2 — Invariant enforcement is caller-cooperative, not structurally guaranteed.**
- Source: `Sources/Domain/LeagueRoster.swift`, `addPlayer(_:checking:)` — takes `allRosters: [LeagueRoster]` as a plain value-type parameter with no constraint tying it to a single authoritative source.
- Consequence: nothing in the type system prevents a future or unseen call site from supplying a partial/stale array, silently reopening the exact defect this loop closes; doc comment claims a stronger guarantee ("live state") than the mechanism provides.
- Remedy: either scope the check so `RosterStore` is unambiguously the only path that can construct/pass `allRosters` (e.g., make the check `internal` to `RosterStore` or accept a store reference), or explicitly document the caller obligation and add a regression test that fails if a stale snapshot is passed.
- Severity: Serious deduction (contained today because both call sites are synchronous same-actor, but not proven for all writers).

**F3 — No direct test at the new Interface.**
- Source: diff contains no test-file hunks for `LeagueRoster.addPlayer(_:checking:)`.
- Consequence: the "single authoritative enforcement point" claim rests on aggregate suite size, not a test that would fail if the check were removed or defeated.
- Remedy: add a conflict-path test (throws `playerAlreadyInLeague`) and a success-path test directly against `LeagueRoster.addPlayer(_:checking:)`, plus one wiring test per `RosterStore` entry point.
- Severity: Serious deduction.

## Verdict

The consolidation direction is architecturally right — one domain method replacing duplicated guards is real Locality gain — but the loop's own diff appears to contain a compile-breaking consumer, the reported test-green status can't be reconciled with that, the enforcement is caller-cooperative rather than structurally guaranteed, and no direct test backs the new Interface. This does not clear 9.5 for `domain_modeling` this loop.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"domain_modeling": 6.5}, "flagged_smells": ["fake-clean reward", "misleading abstractions"], "evidence_demanded": ["A build/test log showing RosterView.swift (with handleAdd's do/catch) actually compiles, or a corrected catch-all/throws signature", "Direct unit tests at LeagueRoster.addPlayer(_:checking:) covering both the conflict-throw path and the success path", "Full current contents of RosterStore.swift (or an equivalent grep) proving no write path to `rosters` bypasses addPlayer(checking:)", "Confirmation that Player/LeagueRoster are Sendable-safe across the ImportService actor -> RosterStore @MainActor boundary introduced by addPlayer(toLeague:)"]}
```
