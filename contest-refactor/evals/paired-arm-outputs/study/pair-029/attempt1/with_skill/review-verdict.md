# Critic Review — Loop 4, `domain_modeling`

## Step 1 — Independent read of current diff (not the Actor's framing)

The Actor's report claims the One-League Rule invariant now lives "exclusively" inside
`LeagueRoster.addPlayer(checking:)`, that both call sites route through it, and that the
full suite (2,041 tests) is green. Per Method Step 1 ("Inspect current code only... require
current source proof") and the Anchor-to-source warning, I re-derive from the diff itself
rather than accepting the report.

## Finding 1 — the new enforcement path traps at runtime (Likely disqualifier)

**Claim.** The two new call sites that are supposed to be the "single authoritative
enforcement point" for the One-League Rule will crash with a Swift exclusivity-violation
fatal error the first time either is actually invoked, not silently degrade — a hard trap.

**Source.**
- `Sources/Application/RosterStore.swift`, `addPlayerToCurrentRoster`:
  `rosters[currentRosterIndex].addPlayer(player, checking: rosters)`
- `Sources/Application/RosterStore.swift`, `addPlayer(_:toLeague:)`:
  `rosters[idx].addPlayer(player, checking: rosters)`

Both lines call a `mutating func` on `rosters[someIndex]` — which requires an exclusive
(`inout`) formal access to the whole `rosters` array for the duration of the call — while
simultaneously passing `rosters` itself as the `checking:` argument, which requires an
overlapping *read* access to the same storage. This is structurally identical to Swift's own
canonical exclusivity-trap example (`modify(&numbers[0], by: numbers)` from the SE-0176
exclusivity-enforcement documentation), which is documented to fail at runtime with
"Simultaneous accesses to 0x…, but modification requires exclusive access." `rosters` is a
`@Published` stored property on a `final class`, so this access is enforced *dynamically*
(at runtime), not statically — the code will compile, then trap the first time a caller
actually reaches either method.

**Consequence.** This directly undermines the loop's own claim. `RosterView.handleAdd` (a
primary user flow — adding a player from the UI) and `ImportService.importRoster` (the CSV
import flow) both now route through this trap. The "single authoritative enforcement point"
this loop set out to install is not functional as diffed; it is a crash waiting on the
happy path, not an edge case. This meets the rubric's **Likely disqualifier** anchor
directly: "a core architectural property the contest rewards is broken at runtime AND the
harm is reachable from a primary user flow."

This also contradicts "Full suite green (2,041 tests)." If any of those 2,041 tests actually
called `addPlayerToCurrentRoster` or `addPlayer(_:toLeague:)`, the process should have
aborted with a fatal trap, not reported a clean pass. The more likely explanation — and the
one I'd want confirmed before accepting anything at 9.5 — is that no test in the suite
exercises these two new methods yet, and the aggregate "2,041 passed" count is being offered
as proof of a code path it never touched. That is the same shape as the rubric's
*fake-clean reward* pattern (aggregate test count standing in for direct evidence at the
changed surface), just applied to `domain_modeling` instead of `test_strategy`.

**Remedy.** Smallest behavior-preserving fix: snapshot `rosters` into a local `let` before
the mutating subscript call so the read and the mutation are no longer the same formal
access, e.g. `let snapshot = rosters; try rosters[idx].addPlayer(player, checking: snapshot)`.
Then add a test that actually calls `addPlayerToCurrentRoster` / `addPlayer(_:toLeague:)`
end-to-end (both the success path and the conflict-throw path) to prove the fix runs to
completion rather than trapping.

## Finding 2 — old, unguarded write path not shown as removed (evidence gap, unresolved)

**Claim.** Before this diff, `RosterView` called `store.addPlayer(player)` and
`ImportService` called `await store.addPlayer(player)` — an un-suffixed, non-throwing
`RosterStore.addPlayer(_:)` that must have existed prior to this loop. The diff hunk for
`RosterStore.swift` shows only additions (`addPlayerToCurrentRoster`, `addPlayer(_:toLeague:)`)
— it does not show that prior method being deleted or redirected.

**Source.** `scenario.md` diff, `Sources/Application/RosterStore.swift` hunk: two `+`-only
methods added; no `-` lines removing the previously-called `addPlayer(_:)`.

**Consequence.** On the evidence given, I cannot confirm the invariant check is actually
*exclusive*. If the old unguarded entry point is still present and reachable from anywhere
else in the codebase (other views, other services, existing tests), the One-League Rule has
two write paths into `rosters` — one checked, one not — which is exactly the "old authority
still alive" / multi-writer smell the rubric asks to rule out before crediting "single
authoritative enforcement point." I'm not promoting this to a scored finding on its own
(the diff excerpt genuinely may not show a same-file deletion that happened elsewhere), but
per Method's guidance to label weak-scope claims rather than invent them, this is an
unresolved question that blocks full credit for the "exclusively" claim in the Actor's
report.

## Other checks (cleared)

- **No reservation-after-suspension**: neither `addPlayerToCurrentRoster` nor
  `addPlayer(_:toLeague:)` contains an `await` between the conflict check and the append —
  the whole check-then-mutate sequence runs synchronously once entered, so (setting Finding 1
  aside) there is no cross-task reentrancy window here. `ImportService`'s per-row `await
  store.addPlayer(...)` calls are awaited sequentially in the loop, not fired concurrently.
- **No new Seam/protocol introduced** — this is a subtractive/consolidating change in shape
  (moving a guard into the domain type), not a costume layer, repository theater, or protocol
  soup candidate. The two-adapter rule and Unified Seam Policy don't apply; nothing here fails
  them.
- **Doc comments are honest about intent** (checking against "live state, not a caller
  snapshot") — that framing is accurate for what the code *intends*; the defect is in how the
  intent is implemented (Finding 1), not in the doc's honesty about ownership.

## Verdict rationale

The architectural *direction* is correct — collapsing the invariant into
`LeagueRoster.addPlayer(checking:)` and routing both callers through it is the right shape for
this domain rule. But the implementation as diffed traps at runtime on the exact paths it
claims to have fixed, the "tests green" claim is not credible given that defect, and the
diff doesn't establish that the prior unguarded path is actually gone. None of that clears
before a 9.5 acceptance on `domain_modeling`, and the runtime-trap finding alone is a Likely
disqualifier on a primary user flow. Rejected, not merely conditional — the code as shown
needs a real fix (not just more evidence) before conditional-then-approve would apply.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"domain_modeling": 3.0},
  "flagged_smells": ["fake-clean reward", "old authority still alive"],
  "evidence_demanded": [
    "A fix removing the simultaneous inout+read access on `rosters` in both `addPlayerToCurrentRoster` and `addPlayer(_:toLeague:)` (e.g., snapshot `rosters` into a local `let` before the mutating subscript call)",
    "A direct test that calls `addPlayerToCurrentRoster` and `addPlayer(_:toLeague:)` end-to-end (both success and the `playerAlreadyInLeague` conflict-throw branch) and runs to completion without a runtime exclusivity trap",
    "Confirmation (diff or grep) that the prior un-suffixed, unguarded `RosterStore.addPlayer(_:)` entry point was removed or now routes through the same domain check, so no remaining call site can add a player without the One-League check"
  ]
}
```
