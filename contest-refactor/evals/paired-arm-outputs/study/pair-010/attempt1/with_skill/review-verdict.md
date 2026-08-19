# Review — Loop 4, `domain_modeling`

## What the Actor claims vs. what the diff shows

The Actor reports the One-League Rule is now validated in `RosterView` (UI add) and
`ImportService` (bulk CSV import), suite green at 2,041 tests, and proposes `domain_modeling`
→ 9.5. Independently walking the diff, the claim does not hold. The domain owner still isn't
the owner, and the "fix" adds a new correctness hazard on top of the ownership problem it fails
to solve.

## Finding 1 — the domain owner still doesn't own the invariant (weak domain model / framework leakage)

`CONTEXT.md` §3 names the One-League Rule as a hard domain invariant, and the scenario itself
identifies `LeagueRoster` as "the domain owner." After this loop, `LeagueRoster.addPlayer` is
untouched except for a doc comment:

```swift
/// Adds a player. Callers are expected to pre-validate the One-League Rule.
mutating func addPlayer(_ player: Player) {
    activePlayers.append(player)
}
```

Applying the **shallow module test**: the domain owner's Interface (`addPlayer`) is still
exactly equal to its Implementation (`append`). No Depth was added. The invariant that defines
the domain — the entire reason `LeagueRoster` exists as a modeled type — is explicitly pushed
out to callers by comment, not enforced by the type.

Instead of centralizing in one authority (most plausibly `RosterStore`, since the invariant
spans *all* rosters in a league, not one `LeagueRoster` instance — `LeagueRoster` structurally
cannot see sibling rosters, so it was never going to be able to hold this rule alone), the loop
implements the same check twice, independently:

- `RosterView.handleAdd`: `store.allRosters.filter { $0.leagueID == store.currentRoster.leagueID && $0.activePlayers.contains(player) }`
- `ImportService.importRoster`: `store.allRosters.filter { $0.leagueID == row.leagueID && $0.activePlayers.contains(player) }`

This is domain policy (the One-League Rule) leaking into the presentation layer and the
infrastructure layer, propagating through the codebase in two structurally-similar but
independently-maintained copies (canon smoke terms: **weak domain model**, **framework
leakage**, **duplicate abstractions** — graduated to findings here because the diff's own
description supplies concrete harm, not speculation: *"a carefully-timed import can add a
player who is already active in that league without triggering either guard."* That is the
author's own admission of a drift hazard, not a hypothetical I am inventing).

**Simplify Pressure Test** on this fix: Q2 (smallest honest fix) fails — the smallest honest fix
is one authoritative method called from both sites, not two hand-written copies keyed off
different fields (`store.currentRoster.leagueID` vs. `row.leagueID`). Q3 (avoid duplicate
layers) fails outright — that is exactly what happened.

## Finding 2 — the fix itself introduces a check-then-claim race (reservation after suspension)

`ImportService` is an `actor`, and both `store.allRosters` and `store.addPlayer` are awaited,
which means `store` (`RosterStore`) is itself actor-isolated — each call is a **separate**
suspension point into that isolation domain:

```swift
let activeRosters = await store.allRosters   // hop 1: check
    .filter { ... }
guard activeRosters.isEmpty else { throw ... }
await store.addPlayer(player)                // hop 2: claim — separate suspension
```

The same pattern exists in `RosterView.handleAdd` against the same `store`. Per the rubric's
**reservation after suspension** smell: "a check-then-claim flow that suspends (`await`)
between 'this slot/resource/work item is available' and 'this attempt owns it' is reentrant."
The carve-out only excuses this "when the actual authority rechecks and atomically claims in
one transactional / actor-isolated / unique-constraint step" — here the check and the claim are
two separate actor hops, so the carve-out does not apply. A concurrent UI add and CSV import
(or two concurrent imports) targeting the same player/league can each pass the check before
either commits, and both then call `addPlayer`, corrupting the exact invariant this loop was
supposed to establish. This is not a pre-existing condition the loop merely failed to fix — it
is newly written by this diff, in code whose stated purpose is invariant enforcement.

## Severity

Both findings map to the **Likely disqualifier** anchor on its own terms: "domain-policy
framework leakage propagating through the codebase" (Finding 1) and "racing async flows that
can corrupt user-visible state" (Finding 2) are both listed verbatim as Likely-disqualifier
examples. The harm is reachable from both of the app's primary flows for roster
management — adding a player via the UI and bulk CSV import — which is the entirety of what
this application does with rosters. This is not a contained, local hazard a judge could route
around; it is the central domain rule, unowned, duplicated, and now racy.

## Test evidence

The Actor's only test evidence is aggregate suite count ("2,041 tests... 0 failed"), which is
**aggregate-test-count-as-test-strategy** (canon fake-clean-reward sub-pattern) applied to
justify a domain-modeling claim it cannot support. No test is cited that exercises the
divergence/race scenario described in the diff's own commentary, and per the mutation-test
mental model, deleting either per-call-site guard would very plausibly not be caught by the
existing 2,041 tests (no citation says otherwise) — that is itself a Noticeable-or-worse gap on
a primary flow, separate from the ownership defect above.

## Verdict

Reject. The loop does not earn 9.5 on `domain_modeling`; it does not even net-positive the
dimension over doing nothing, because the duplicate, non-atomic guards create a false sense of
safety while leaving the actual authority (a single owner that atomically checks-and-claims)
unbuilt. The minimal correction path: give `RosterStore` (or an explicit domain service with
visibility across all rosters) one throwing method that atomically checks and claims the
One-League Rule in a single actor-isolated step; have both `RosterView` and `ImportService` call
it; delete both ad hoc guards; add a test that fails if that method's check is removed, and
ideally a concurrency test proving two racing callers cannot both succeed.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["weak domain model", "framework leakage", "duplicate abstractions", "reservation after suspension"], "evidence_demanded": ["A single authoritative method (e.g. RosterStore.addPlayer(_:to:) or an explicit domain service) that owns the One-League Rule check-and-claim as one atomic actor-isolated step, called by both RosterView and ImportService, replacing the two duplicated guards", "Proof the check-and-claim is atomic under concurrent callers — a concurrency test firing a UI add and a CSV import for the same player/league concurrently asserting only one succeeds, or an equivalent actor-isolation argument", "A test that fails if either existing guard (or its replacement) is deleted or weakened, per the mutation-test mental model — not aggregate suite-green counts", "Removal of the redundant per-call-site guards once ownership is centralized"]}
```
