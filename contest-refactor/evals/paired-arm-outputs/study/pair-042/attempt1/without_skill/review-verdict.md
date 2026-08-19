# Review: Loop 4 — `domain_modeling`

## What the Actor claims

The Actor reports extracting the One-League Rule invariant checks out of ad-hoc caller
logic and into a consistent enforcement point, with the full 2,041-test suite green, and
proposes raising `domain_modeling` to 9.5.

## What the diff actually shows

It does the opposite of what "extracting a guard into the domain" should mean.

1. **The domain type is untouched except for a comment.** `LeagueRoster.addPlayer` gained
   a doc comment — "Callers are expected to pre-validate the One-League Rule" — but no
   code. It is still a bare `activePlayers.append(player)` with zero enforcement. A
   documented expectation is not an invariant; it's a wish. Nothing stops any future
   caller (a test helper, an undo/redo path, a sync-merge routine, a "quick add" button
   two sprints from now) from calling `addPlayer` directly and silently violating the
   rule the domain is supposed to own.

2. **The guard logic is duplicated, not shared.** `RosterView.handleAdd` and
   `ImportService.importRoster` each grew their own independent `filter { ... }` check
   over `store.allRosters`. Same rule, two implementations, zero code reuse between them.
   This is the textbook anemic-domain-model failure mode: the object that should own the
   invariant (`LeagueRoster`) is a passive data bag, and every caller reimplements the
   business rule around it.

3. **The two duplicates have already diverged.** `RosterView` keys off
   `store.currentRoster.leagueID`; `ImportService` keys off `row.leagueID`. The scenario's
   own context section calls this out directly: if those two ever resolve a league
   differently (an alias, a stale cache, an ID remap), the invariant silently breaks
   through the import path while the UI path stays intact — a real data-integrity bug
   introduced by "fixing" this exact invariant, in the same loop that claims to have
   fixed it. That's not a hypothetical edge case; it's the direct, near-term consequence
   of having two independent implementations of the same safety rule.

4. **Net architectural change vs. before is negative.** Before this loop, both callers had
   "ad-hoc guard logic" per the context. After this loop, both callers still have ad-hoc
   guard logic — just now dressed up with a misleading doc comment on the domain type
   that implies the invariant is handled, when it isn't. If anything this loop reduces the
   chance the invariant gets audited again, because the domain method now reads as if it
   documents an already-enforced contract.

5. **No test evidence for the new behavior.** The diff touches exactly three files, none
   of them a test file. "2,041 tests, 0 failed" tells us the change didn't break anything
   pre-existing; it says nothing about whether the invariant is actually exercised now —
   e.g., a test that imports a CSV row for a player already active in the same league and
   asserts `ImportError.playerAlreadyInLeague` is thrown, or a test that calls
   `LeagueRoster.addPlayer` directly (bypassing both call-site guards) and asserts it's
   rejected. Given the whole point of this loop was invariant enforcement, the absence of
   any invariant-focused test in the diff is itself a red flag — the green suite is not
   evidence the fix works, only that it didn't collide with anything else.

## Judgment

This is not a `domain_modeling` improvement; it's a relocation of the same anemic-model
problem into two places instead of one, with a comment that overstates what was actually
done and a newly introduced divergence bug documented in the scenario's own framing. The
correct fix — the one the Actor's report implies was done — is for `LeagueRoster` (or a
dedicated domain service/factory it owns) to enforce the invariant internally, so there is
exactly one implementation and it cannot be bypassed by construction. That did not happen
here.

I am rejecting the `domain_modeling` → 9.5 claim. This blocks acceptance at the 9.5
threshold: a domain invariant enforced by convention in two divergent call sites, with the
domain object itself left mutable and unguarded, is a canonical anemic-domain-model /
duplicated-business-rule defect, not a 9.5-grade domain model.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["anemic domain model", "duplicated business logic (shotgun surgery)", "divergent duplication of a safety invariant", "comment-only contract / unenforced precondition", "bypassable invariant"], "evidence_demanded": ["LeagueRoster.addPlayer (or a dedicated domain factory/service it owns) enforces the One-League Rule internally, so the invariant cannot be violated by any caller including ones not yet written", "A single shared implementation of the invariant check used by both RosterView and ImportService, replacing the two independent filter blocks", "A regression test that calls LeagueRoster.addPlayer directly, bypassing both UI and ImportService guards, and asserts the invariant still holds", "A test exercising the exact divergence scenario described in the context: an import row whose leagueID resolution differs from store.currentRoster.leagueID for the same real-world league", "At least one new test in the diff demonstrating the invariant is actually exercised (e.g. ImportError.playerAlreadyInLeague thrown on duplicate import), not just an unchanged green count on the existing 2,041 tests"]}
```
