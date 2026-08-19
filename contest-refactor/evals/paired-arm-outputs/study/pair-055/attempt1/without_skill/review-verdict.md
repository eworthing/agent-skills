# Review — Loop 4, `domain_modeling`

## What the diff actually does

The Actor's report frames this as "extracting" the One-League Rule so it's enforced
consistently. The diff does the opposite of what a domain-modeling refactor should do:

1. **`LeagueRoster.addPlayer` gained a doc comment, not a behavior change.** The only
   edit to the domain type itself is a `///` comment saying "Callers are expected to
   pre-validate the One-League Rule." The method body is untouched — it is still a bare
   `activePlayers.append(player)` with zero validation. The type that owns the invariant
   (per `CONTEXT.md` §3, `LeagueRoster` is explicitly named as the entity the rule
   governs) still cannot enforce it and still trusts every caller to have done the right
   thing beforehand. A comment is not an invariant.

2. **The actual guard logic was duplicated into two unrelated layers instead of
   consolidated into one.** `RosterView` (presentation) and `ImportService`
   (infrastructure) each independently reimplement "is this player already active in
   this league" with their own filter/guard blocks. That is strictly worse than the
   pre-loop state described in the context ("all callers performed ad-hoc guard
   logic") — before, there was ad-hoc duplication; after, there is the *same* ad-hoc
   duplication, now dressed up with comments and framed as if the invariant had been
   centralized. Nothing was extracted into the domain owner; two copies were written
   against two different call sites instead of one.

3. **The two copies are already inconsistent in a way that matters.** `RosterView`
   resolves the league via `store.currentRoster.leagueID`; `ImportService` resolves it
   via `row.leagueID`. The diff's own context notes these can diverge and a
   "carefully-timed import can add a player who is already active in that league
   without triggering either guard." That's not a hypothetical edge case introduced by
   my review — it's an acknowledged, live correctness gap in the submitted diff,
   sitting directly on the invariant this loop was supposed to harden.

4. **Any future caller of `addPlayer` gets none of this protection.** Because the
   check lives in two call sites rather than in the domain method, a third caller
   (a trade feature, an admin tool, a merge-roster operation, test fixtures, anything)
   silently reintroduces the bug. This is the textbook failure mode of an anemic
   domain model: invariants that should be structurally impossible to violate are
   instead "please remember to check first," scattered across layers that have no
   business owning that logic. Presentation code should not know how to evaluate a
   domain invariant; a background import actor should not either. Both now do, with
   different (and divergent) implementations.

## On the green test suite

2,041 passing tests tells us the two guard blocks work for the specific call paths
they were written against (UI add-flow, CSV import-flow). It says nothing about:
- a new/future caller of `LeagueRoster.addPlayer` that doesn't replicate either guard,
- the divergence between `store.currentRoster.leagueID` and `row.leagueID` under
  concurrent/racing conditions,
- whether `LeagueRoster` can be constructed or mutated in a way that violates its own
  documented invariant from anywhere other than these two call sites (e.g. directly in
  a unit test, in a future service, via `Codable` round-trip, etc).

A green suite around duplicated ad-hoc guards is exactly the kind of coverage that
looks reassuring but validates the symptom-fix, not the invariant.

## Verdict rationale

This is not a nitpick or a style preference — it is the central claim of the loop
(`domain_modeling`) failing on its own terms. The Actor's report asserts the invariant
is now "guarded on bulk imports" and proposes elevating `domain_modeling` to 9.5, but
the domain type that owns the invariant still cannot enforce it, and the enforcement
that does exist is duplicated and already demonstrably divergent per the diff's own
description. At a 9.5 bar, "the domain object trusts its caller and two different
layers reimplement the same business rule with different data sources" is disqualifying
for the dimension being scored, not a minor deduction.

I did not have the project's canonical severity/gate taxonomy available in this
sandbox (only `scenario.md` was provided), so `blocking_severity` below is my own
descriptive label rather than a quoted rubric ID — but the underlying finding (domain
invariant not enforced by its owning type; duplicated, divergent business logic) is a
blocking-class finding under any reasonable domain-modeling rubric, not a nice-to-have.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical (invariant enforcement lives outside its owning domain type, duplicated across layers with divergent implementations)", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["anemic domain model (LeagueRoster.addPlayer performs no validation)", "duplicated business rule across layers (RosterView + ImportService reimplement the same guard)", "divergent duplicate logic (store.currentRoster.leagueID vs row.leagueID)", "trust-the-caller invariant (doc comment substituted for enforcement)", "shotgun surgery risk for future callers of addPlayer"], "evidence_demanded": ["LeagueRoster.addPlayer (or a new throwing/validating entry point) itself rejects a second active membership in the same league, with no reliance on caller-side pre-validation", "Deletion of the duplicated guard blocks in RosterView and ImportService, replaced by calls into the single domain-level check", "A test that adds a player through a path other than RosterView or ImportService (e.g. directly via LeagueRoster, or a third hypothetical caller) and asserts the invariant still holds", "A test or resolution proving store.currentRoster.leagueID and row.leagueID cannot diverge for the same logical roster (or unification of how league identity is resolved)", "A regression test that fails if either presentation- or infrastructure-layer guard is deleted, proving the invariant is enforced at the domain layer and not merely duplicated at the edges"]}
```
