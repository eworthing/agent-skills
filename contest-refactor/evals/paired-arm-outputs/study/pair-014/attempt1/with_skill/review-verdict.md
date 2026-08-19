# Critic Review — Loop 4, `domain_modeling`

## Scope and method

Independently re-derived from the diff and Actor report in `scenario.md` only, per Method Step 1
("Inspect current code only... require current source proof"). The Actor's own "tests green,
propose 9.5" claim is treated as a claim to verify, not evidence.

## Cleared

- **Invariant scope is correct.** `LeagueRoster.addPlayer(_:checking:)` filters candidates with
  `$0.leagueID == leagueID`, matching CONTEXT.md §3's actual rule (no two rosters *in the same
  league*), not an over-broad "one roster anywhere" check. Correctly implemented as written.
- **No reservation-after-suspension.** `addPlayer(_:checking:)` is a synchronous, non-`async`
  mutating struct method; `addPlayerToCurrentRoster` / `addPlayer(_:toLeague:)` on `RosterStore`
  are likewise non-`async`. `ImportService`'s `await` is only the actor-hop onto `@MainActor`, not
  an internal suspension inside the check. There is no `await` between "check" and "claim," so the
  canon *reservation after suspension* smell does not apply here — the check-then-write is atomic
  once scheduled on the store's actor.
- **No new Seam.** This is a plain domain method on an existing struct, not a new
  protocol/port — Unified Seam Policy and the two-adapter rule are not triggered.
- **Sequential awaits in `ImportService.importRoster`'s loop are not a lens-efficiency finding.**
  Each row's conflict check depends on the mutation committed by the previous row (they all read
  the same `rosters`), so this is the "sequential *dependent* operations" carve-out, not D2's
  "sequential independent I/O."

## Finding 1 — exclusivity-violation crash risk on the primary add-player path (blocking)

**Claim.** Both new `RosterStore` methods call a mutating method on an element of `rosters` while
passing `rosters` itself as an argument to that same call — the classic Swift exclusivity-checker
trap ("Simultaneous accesses to ..., but modification requires exclusive access").

**Source.**
- `RosterStore.addPlayerToCurrentRoster`: `try rosters[currentRosterIndex].addPlayer(player, checking: rosters)`
- `RosterStore.addPlayer(_:toLeague:)`: `try rosters[idx].addPlayer(player, checking: rosters)`

`addPlayer(_:checking:)` is a `mutating func` on `LeagueRoster`. Invoking it on
`rosters[idx]` opens a formal exclusive "modify" access on the `rosters` storage that spans the
whole call (materialize element, yield inout, resume, write back — required whether `rosters` is
treated as a plain stored property or as the synthesized modify-accessor Swift generates for a
get/set-only property such as `@Published`'s `wrappedValue`). Evaluating the `checking: rosters`
argument happens *inside* that window and is a second, overlapping read of the same storage. Under
Swift's default (enforced) exclusivity checking this pattern traps at runtime with a fatal error,
not a silent bug — it does not merely misbehave, it crashes the process.

**Consequence.** This is not an edge case: it is the *only* route left to add a player anywhere in
the app after this loop. `RosterView.handleAdd` (manual add, the primary UI flow) and
`ImportService.importRoster` (CSV import) were both rewired this loop to go exclusively through
these two methods. If the trap fires as the pattern predicts, the One-League Rule enforcement this
loop exists to build is not merely imperfect — it is unreachable, because the app crashes before
the check can matter, on both primary flows named in the scenario. Per
`architecture-rubric.md` § Severity Anchors, "a core architectural property the contest rewards is
broken at runtime AND the harm is reachable from a primary user flow" is the definition of
**Likely disqualifier** — this qualifies on that language directly.

**Remedy.** Smallest behavior-preserving fix: snapshot before mutating so the read and the modify
target different storage —
```swift
let snapshot = rosters
try rosters[currentRosterIndex].addPlayer(player, checking: snapshot)
```
(same fix at the second call site). No design change required; the domain shape (one invariant,
one owning method) is otherwise sound.

**Evidence demanded before acceptance.** I cannot execute code in this sandboxed review — this is
reasoning from the diff, not an executable trace (Meta-rule 4's "prefer executable evidence"
carve-out for when reasoning-only is the best available). Require one focused test that actually
calls `addPlayerToCurrentRoster` or `addPlayer(_:toLeague:)` under normal (enforced) exclusivity
and confirms it does not trap.

## Finding 2 — "full suite green" does not evidence this loop's change (blocking, compounds Finding 1)

**Claim.** The diff adds zero test files or test modifications. The Actor's report cites "2,041
tests, 0 failed" as justification for `domain_modeling` → 9.5. This is the rubric's own named
**aggregate-test-count-as-test-strategy** sub-pattern of fake-clean reward: a passing count with no
audit of which surfaces have a direct test.

**Source.** Diff contains hunks for `LeagueRoster.swift`, `RosterStore.swift`, `RosterView.swift`,
`ImportService.swift` only — no `Tests/` hunk.

**Consequence.** Per Method Step 8's mutation-test mental model: I can name a mutation the current
suite would not catch — replace the entire body of `addPlayer(_:checking:)` with
`activePlayers.append(player)` (delete the invariant check outright) and, on the evidence
available, nothing in the cited 2,041 tests would fail, because nothing shown exercises either new
`RosterStore` entry point. That is squarely the anchor's "test absence around central mutable
runtime behavior with realistic regression risk" branch of Likely disqualifier, independent of
Finding 1: this loop's central claim (single enforced invariant) has no direct test proving the
conflict path throws, let alone that the happy path doesn't crash.

**Remedy.** Add tests at the new Interface (`RosterStore.addPlayerToCurrentRoster` /
`addPlayer(_:toLeague:)`, not just `LeagueRoster.addPlayer(checking:)` in isolation) that (a)
successfully add a player, (b) attempt a same-league double-add and assert
`RosterError.playerAlreadyInLeague` is thrown, and (c) run under default exclusivity enforcement
so a Finding-1 regression fails loudly.

## Finding 3 — prior entry point not shown removed (scope-limited, open question)

**Claim.** The Actor's report says the goal was routing "both `RosterView` and `ImportService`"
through the domain method "rather than performing their own guards," implying `RosterStore` had a
pre-existing `addPlayer(_:)` (or similar) that `RosterView` used to call directly
(`RosterView`'s diff shows `- store.addPlayer(player)`). The `RosterStore.swift` hunk only shows
two additions; it does not show that prior method's deletion.

**Source.** Diff hunk for `RosterStore.swift` is additive only (`+` lines, one `@@` context
block); no `-func addPlayer` is shown.

**Consequence.** Cannot confirm from the diff alone whether the prior entry point is dead code, is
still exported and reachable from an un-shown call site (bypassing the new invariant entirely), or
was in fact deleted outside the shown hunk. Labeled scope-limited per the Evidence Chain rule
("if scope is weak, label the claim") rather than asserted as a defect — this is the *old
authority still alive* smell at smoke level, not yet promoted to a finding.

**Evidence demanded.** Confirm (grep or full file diff) that no `RosterStore.addPlayer(_:)`
overload other than the two new ones remains, and that no other call site in the codebase still
calls a pre-refactor signature.

## Minor / non-blocking

`ImportService.importRoster`'s per-row loop has no rollback and no per-row reporting: a conflict on
row *k* leaves rows `1..k-1` already committed to `rosters` and aborts `k+1..end` with a single
thrown error, no report of which rows landed. Not attributable to this loop specifically (prior
behavior of `store.addPlayer(player)` is not shown), so this is a Noticeable-level open item, not
scored against this loop.

## Verdict

Findings 1 and 2 both independently satisfy the `Likely disqualifier` anchor and sit on the primary
flow this loop was built to protect. The domain *shape* (single owning method, correct
same-league scoping, no seam overreach) is sound and the fix is small and localized, but the
implementation as diffed is not acceptable at the 9.5 threshold, and "tests green" does not
evidence otherwise since no test shown exercises the changed paths. Rejected pending the Finding-1
remedy plus a passing test that actually calls the new methods, and pending Finding-3 confirmation.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {
    "domain_modeling": 4.0
  },
  "flagged_smells": [
    "fake-clean reward (aggregate-test-count-as-test-strategy)",
    "old authority still alive"
  ],
  "evidence_demanded": [
    "A focused test that calls RosterStore.addPlayerToCurrentRoster or addPlayer(_:toLeague:) under default (enforced) exclusivity checking and confirms no runtime trap ('Simultaneous accesses...') on the rosters[idx].addPlayer(player, checking: rosters) call shape",
    "A direct test exercising the same-league conflict path through the new RosterStore entry points, asserting RosterError.playerAlreadyInLeague is thrown (not just a unit test on LeagueRoster.addPlayer(checking:) in isolation)",
    "Confirmation that RosterStore's pre-refactor addPlayer(_:) (or equivalent) method and any other call sites of it have been removed, not left as dead code or a bypass"
  ]
}
```
