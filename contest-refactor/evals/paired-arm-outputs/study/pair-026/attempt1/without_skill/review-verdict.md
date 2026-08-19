# Review — Loop 4, `domain_modeling`

## What the Actor claims vs. what the diff shows

The Actor's report says the loop "refactored roster management so `RosterView`
validates the single-league invariant before adding a player, and
`ImportService` now also guards the invariant on bulk imports," and frames
this as work that should raise `domain_modeling` to 9.5. The report also
implies the guards were *extracted* from ad-hoc caller logic into something
better. Reading the diff directly, that is not what happened.

## Findings

**1. The domain type still does not own its own invariant.**
`LeagueRoster.addPlayer` is untouched in behavior — it is still a bare
`activePlayers.append(player)`. The only change to the domain file is a
doc comment: *"Callers are expected to pre-validate the One-League Rule."*
That is not domain modeling, it's documentation of an anemic model. The
aggregate that owns the invariant (`LeagueRoster`, the "domain owner" per
the loop's own context note) is the one place that *cannot* enforce it after
this change. Any future caller — a new view, a new import path, a test, a
script — can call `addPlayer` and silently violate the One-League Rule.
This is the textbook anemic-domain-model smell: business rules live in
callers instead of the object whose job is to guarantee its own invariants.

**2. The "extraction" is actually a duplication, and the copies already
disagree.** `RosterView.handleAdd` computes the check from
`store.currentRoster.leagueID`. `ImportService.importRoster` computes the
same check from `row.leagueID`. These are two independent implementations
of the same rule, written in two different layers (presentation and
infrastructure), with two different data sources for what should be the
same fact. The scenario's own context note calls this out explicitly: "a
carefully-timed import can add a player who is already active in that
league without triggering either guard" if the two ID sources ever
disagree — which is not a hypothetical, it's already a live risk in this
diff, since nothing keeps `row.leagueID` and `store.currentRoster.leagueID`
consistent. This is a direct violation of a two-adapter-style rule: when
two independent call sites need the same domain logic, that logic belongs
in one shared place (the domain), not copy-pasted with different variable
provenance in each adapter.

**3. Net effect on the "before" state is neutral-to-negative, not
improved.** Before this loop, both call sites had "ad-hoc guard logic"
per the loop's own context. After this loop, both call sites still have
ad-hoc guard logic — it's just now formatted as a `guard` statement with a
comment instead of whatever it was before. The actual defect (invariant
enforcement scattered across callers instead of centralized in the domain)
is unchanged. If anything, it is now falsely dressed up as fixed: the
domain method has a comment implying validation is handled, which will
mislead the next engineer who adds a third caller (e.g., a "merge two
rosters" feature) into believing the guard is optional boilerplate rather
than a hard, unenforced invariant they need to re-derive themselves.

**4. Test coverage does not touch the actual risk.** "2,041 passed" tells us
existing tests didn't regress; it says nothing about whether a test exists
that (a) calls `LeagueRoster.addPlayer` directly to confirm the invariant is
NOT enforced at the domain layer (this is the crux of the finding — such a
test, if it existed, would have to currently pass with a violated
invariant, which should have stopped this from being reported as done), or
(b) exercises `RosterView` and `ImportService` against a scenario where
`row.leagueID` and `store.currentRoster.leagueID` disagree, which is exactly
the divergence risk the loop's own context flags. A green suite here is not
evidence the invariant is safe; it's evidence the suite doesn't test the
invariant at the boundary that matters.

## Verdict

This does not clear `domain_modeling` at a 9.5 bar. The change relocates
duplicated ad-hoc validation from "somewhere" to two named layers, adds a
comment that misrepresents the domain type as validated-by-convention, and
leaves the actual aggregate (`LeagueRoster`) able to silently violate its
own stated invariant. The two duplicate implementations are already
provably divergent in their data source, which is the precise failure mode
a domain-owned invariant check exists to prevent. This is a regression in
honesty about the codebase's safety even if it isn't a regression in test
count.

Recommended direction (not required to write here, but for context): the
invariant check belongs inside `LeagueRoster` itself — e.g.
`LeagueRoster.addPlayer` returns/throws on violation, or a
`RosterCollection`-level method that has access to all rosters performs the
check and is the only entry point both `RosterView` and `ImportService`
call. Either removes the duplicate, divergent guards entirely.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — unenforced domain invariant with duplicated, already-divergent guard logic across two independent layers", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["anemic domain model (invariant documented, not enforced, on the aggregate root)", "duplicated business logic across layers (shotgun surgery)", "divergent duplication (guards read different fields for the same fact)", "trust-the-caller invariant (comment substitutes for enforcement)"], "evidence_demanded": ["A unit test that calls LeagueRoster.addPlayer directly with a player already active in the same league, proving the domain type itself now rejects (not merely that callers happen to guard it)", "A test where row.leagueID and store.currentRoster.leagueID resolve to different values for the same logical league, showing the invariant still holds end-to-end", "Removal or justification of the RosterView/ImportService duplicate guard code once the domain enforces the invariant directly"]}
```
