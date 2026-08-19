# Critic Review — Loop 4, `domain_modeling`

## Step 1 — Inspect current code only

The Actor's report claims the One-League Rule now lives exclusively inside
`LeagueRoster.addPlayer(checking:)`, both call sites route through it, and the
full suite (2,041 tests) is green. Per method.md Step 1, that report is a
historical claim, not proof — the diff itself is re-derived from source below,
and the finding stands or falls on the code shown, not on the aggregate test
count.

## Finding 1 — the new enforcement point likely cannot run on either call path (Likely disqualifier)

**Claim.** `RosterStore.addPlayerToCurrentRoster` and `RosterStore.addPlayer(_:toLeague:)`
each call a `mutating func` on a single array element while passing the *same*
array as a plain argument in the same expression:

```swift
try rosters[currentRosterIndex].addPlayer(player, checking: rosters)
...
try rosters[idx].addPlayer(player, checking: rosters)
```

**Source.** `Sources/Application/RosterStore.swift`, the two new methods added
in this diff (`addPlayerToCurrentRoster(_:)` and `addPlayer(_:toLeague:)`).

**Consequence.** This is the textbook shape of a Swift exclusivity violation —
the same shape used as the canonical example in Apple's own "Memory Safety"
documentation (`array[i].mutatingCall(array)`): the mutating call on
`rosters[idx]` requires exclusive (write) access to the storage behind
`rosters` for the duration of the call, while the `checking: rosters` argument
requires a simultaneous read of the *same* storage — not a distinct index,
the *whole array*, so there is no aliasing ambiguity for the compiler/runtime
to resolve in the code's favor. Depending on how the compiler resolves this
for a `@Published` array property, the realistic outcomes are: (a) a compile
error ("overlapping accesses to 'rosters', but modification requires
exclusive access"), which would mean the target never built and "2,041
passed, 0 failed" could not have been produced against this diff; or (b) it
builds and traps at runtime with "Simultaneous accesses to 0x…, but
modification requires exclusive access" the first time either method
executes — which is precisely the primary flow this loop targets
(`RosterView.handleAdd` → `addPlayerToCurrentRoster`, `ImportService.importRoster`
→ `addPlayer(toLeague:)`). Either way, the single authoritative enforcement
point this loop was built to install is either unbuildable or unusable from
both of its real call sites. This is a core architectural property (the
One-League Rule's sole enforcement point) broken at runtime *or* build time,
reachable from both primary flows that exercise it — the rubric's own
"Likely disqualifier" anchor.

This also exposes a test-strategy gap feeding directly into the
`domain_modeling` claim: the report cites only the aggregate suite count
("2,041 passed"), never a specific test file/line that calls
`addPlayerToCurrentRoster` or `addPlayer(toLeague:)` and asserts the
`.playerAlreadyInLeague` branch. That is the rubric's named
**Fake-clean reward → aggregate-test-count-as-test-strategy** sub-pattern:
scoring `domain_modeling` up because a global test count looks tidy, without
confirming a direct test exercises the very method the score is about. Absent
that citation, I cannot tell whether the suite even reaches this code, which
would be the only way the reported green run and my exclusivity concern are
both simultaneously true.

**Remedy (smallest honest fix).** Materialize the read *before* taking the
mutating access, e.g.:

```swift
let allRosters = rosters
try rosters[idx].addPlayer(player, checking: allRosters)
```

This breaks the overlapping-access pattern with a single extra `let` — no new
abstraction, no seam, consistent with "prefer subtractive/smallest fixes."

## Finding 2 — non-exhaustive catch in `RosterView.handleAdd` (Serious, needs confirmation)

**Claim.** The new `handleAdd` body:

```swift
do {
    try store.addPlayerToCurrentRoster(player)
} catch RosterError.playerAlreadyInLeague(let p, _) {
    store.presentError(.playerAlreadyInLeague(p))
}
```

catches only one case of `RosterError`, which the same diff shows has at
least a second case (`RosterError.leagueNotFound`, thrown elsewhere in
`RosterStore`). `handleAdd` is not itself `throws`. Unless there is a trailing
catch-all not shown in this hunk, Swift will not treat this `do/catch` as
exhaustive, and this will not compile ("errors thrown from here are not
handled"). I'm flagging this at lower confidence than Finding 1 only because
the diff hunk could in principle be eliding a trailing `catch` that already
existed — but as shown, it reads as the complete new body.

**Consequence.** Same category as Finding 1: a second, independent reason the
reported green build/test run is hard to reconcile with the diff as shown.

**Remedy.** Add a trailing `catch { store.presentError(.unexpected(error)) }`
(or the domain-appropriate fallback), or switch to typed throws with an
exhaustive `switch` over `RosterError`'s cases.

## Finding 3 — old authority may still be alive (Noticeable, unresolved)

**Claim.** The diff shows `RosterView.handleAdd` used to call `store.addPlayer(player)`
(the old, presumably-ungated method), and `ImportService` used to call
`await store.addPlayer(player)`. Neither hunk shows this old `RosterStore.addPlayer(_:)`
being deleted — only that these two call sites stopped using it. If it still
exists on `RosterStore` and any other caller still reaches it, the One-League
Rule has more than one entry point, contradicting "the invariant check
executes once, in the domain type, regardless of which entry path is used."

**Consequence.** Canon smell **old authority still alive** — a superseded
write path left reachable alongside the new authoritative one.

**Remedy.** Confirm the old `addPlayer(_:)` was deleted from `RosterStore`, or
that it now forwards to `addPlayerToCurrentRoster`/`addPlayer(toLeague:)`
rather than mutating `rosters` directly.

## What I'm not flagging

The underlying design is the right shape for `domain_modeling`: `activePlayers`
is `private(set)` and declared in the same file as the new `addPlayer(_:checking:)`,
so the setter is genuinely inaccessible outside `LeagueRoster.swift` — this
isn't a convention-only guard, it's type-system-enforced single-writer
ownership, and both real call sites (view + import) were rewired to go
through the domain method rather than duplicating the guard. If Findings 1–2
turn out to be non-issues on the real compiler/toolchain (e.g. if `@Published`'s
accessor synthesis avoids the overlap in a way I can't fully verify from a
diff alone), this would be a clean, well-targeted `domain_modeling` fix. That
uncertainty is exactly why this is a `rejected`/evidence-demanded verdict
rather than a silent pass-through, per Meta-Rule 4: a green single-config test
run doesn't prove this, and the fix is cheap enough (one `let`) that there's
no honest reason not to require the build/test evidence before crediting 9.5.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"domain_modeling": 4.0}, "flagged_smells": ["old authority still alive", "Fake-clean reward: aggregate-test-count-as-test-strategy"], "evidence_demanded": ["Compiler build log (or equivalent) for Sources/Application/RosterStore.swift showing addPlayerToCurrentRoster and addPlayer(_:toLeague:) compile without an exclusivity/overlapping-access diagnostic", "Specific test file:line that calls addPlayerToCurrentRoster and/or addPlayer(_:toLeague:) and asserts both the success path and the .playerAlreadyInLeague conflict path, proving the methods execute without a runtime 'Simultaneous accesses' trap", "Full RosterError case list plus the complete handleAdd do/catch body, confirming the catch is exhaustive or a trailing catch-all exists", "Confirmation that the pre-existing ungated RosterStore.addPlayer(_:) was deleted or now forwards through the new domain-checked methods, so no second entry point to the One-League Rule remains"]}
```
