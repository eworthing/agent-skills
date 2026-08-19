# Review: Loop 4 — `domain_modeling` — One-League Rule centralization

## What the Actor claims

A single domain method, `LeagueRoster.addPlayer(_:checking:)`, now owns the One-League Rule
invariant. `RosterStore` exposes two thin wrappers (`addPlayerToCurrentRoster`,
`addPlayer(_:toLeague:)`) that both forward to it, and `RosterView` / `ImportService` no longer
carry their own guard logic. Actor reports 2,041/2,041 tests green and proposes `domain_modeling`
→ 9.5.

The *shape* of this is the right idea — one owner for the invariant, callers routing through it
instead of duplicating the check. That part I have no objection to. But the concrete
implementation shown in the diff has a defect that undermines the "this now correctly and
exclusively enforces the rule" claim, and the diff leaves open questions the Actor's report
doesn't address.

## Finding 1 (blocking): the two adoption call sites are a textbook Swift exclusivity violation

Both new `RosterStore` methods call the domain method the same way:

```swift
try rosters[currentRosterIndex].addPlayer(player, checking: rosters)
...
try rosters[idx].addPlayer(player, checking: rosters)
```

`LeagueRoster` is a `struct`, so `addPlayer(_:checking:)` being `mutating` means `rosters[idx]`
is passed as an implicit `inout self` for the duration of the call — an exclusive ("modify")
access to the `rosters` array's storage. The same call *also* passes `rosters` itself as the
`checking:` argument — a simultaneous read access to the same storage, opened while the modify
access is still in flight. This is structurally identical to Swift's own canonical bad example
(`balance(&scores[0], scores)` / `modify(&numbers[0], numbers)`) that the language's exclusivity
model exists specifically to forbid. `rosters` here is `@Published`, a property-wrapper-backed
property, so the compiler can't prove non-overlap statically and falls back to dynamic
enforcement — meaning this most likely doesn't fail to compile, it fails at **runtime**, with
`Fatal error: Simultaneous accesses to 0x..., but modification requires exclusive access.`

If that's right, both of the only two call sites that adopt the new domain method are broken —
not stylistically, but in the sense that invoking them at all is liable to crash the process. That
directly contradicts the premise of the loop, since the new method is supposed to be the
authoritative enforcement point and these are its only two callers.

This also casts doubt on "Full suite green (2,041 tests)": a runtime exclusivity trap aborts the
whole test process, it doesn't surface as one failed test among 2,041 passing ones. The more
consistent explanation is that no test in the suite actually exercises
`addPlayerToCurrentRoster` or `addPlayer(_:toLeague:)` — i.e., the green suite is silent on
exactly the code this loop added. I can't run the compiler or tests from here (I'm scoped to
`scenario.md` only), so I'm not 100% certifying the crash — but the access pattern as literally
written is the known-bad shape, and the burden should be on the Actor to show a passing,
targeted invocation of these two methods, not on the reviewer to disprove it.

## Finding 2: the diff doesn't show the old bypass path being removed

`RosterView.handleAdd` previously called `store.addPlayer(player)`, and `ImportService` previously
called `await store.addPlayer(player)` — both implying `RosterStore` had (has?) a plain,
presumably unguarded `addPlayer(_:)` method. The `RosterStore.swift` hunk in this diff only shows
two `+` additions; it never shows that old method being deleted or folded into the new one. The
Actor's report says the invariant now "lives exclusively inside `LeagueRoster.addPlayer(checking:)`,"
but exclusivity of enforcement requires the old unguarded entry point to be gone, not just
unused by these two call sites. If `RosterStore.addPlayer(_:)` still exists, it's a live,
undocumented bypass of the very invariant this loop claims to have centralized. This is
unverifiable from the material I was given, which is itself the problem for a 9.5 claim on this
dimension.

## Finding 3 (minor, same dimension-adjacent): batch-import failure semantics changed silently

`ImportService.importRoster` iterates rows with `try await store.addPlayer(...)` and no per-row
recovery. Since `addPlayer(_:toLeague:)` is newly throwing (the old call was plain `await`, no
`try`, implying it didn't throw), a conflict partway through a CSV import now aborts the rest of
the batch, with earlier rows already committed to `rosters`. That may be the desired behavior, but
nothing in the diff or the report indicates it was considered, and it's a user-visible behavior
change riding along with an "invariant enforcement" refactor.

## Assessment

The design intent is sound, but as shown the mechanism has a defect in its only two integration
points, no test evidence that those integration points were ever exercised, and an unverified gap
in whether the prior unguarded path was actually retired. That's not a 9.5 domain_modeling
submission — it's a plausible direction that needs the crash risk fixed (e.g., snapshot `rosters`
into a local `let` before indexing/mutating), a real test that calls both new `RosterStore`
methods and both their throw/success branches, and proof the old `addPlayer(_:)` bypass is gone.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "blocking / correctness-critical — likely runtime crash at the only two call sites adopting the new domain invariant method, unproven by the cited test run", "dimension_scores": {"domain_modeling": 3}, "flagged_smells": ["exclusivity violation: mutating array-element call sites pass the same array as a second argument (self + snapshot overlap)", "coverage theater: 'full suite green' claimed for a code path no cited test appears to exercise", "incomplete migration: old unguarded RosterStore.addPlayer(_:) not shown removed, so 'exclusive' enforcement is unverified", "silent behavior change: ImportService batch import now aborts mid-batch on first conflict with no rollback/recovery, unaddressed"], "evidence_demanded": ["A build/run log or targeted test proving RosterStore.addPlayerToCurrentRoster and RosterStore.addPlayer(_:toLeague:) can each be invoked (both throw and success paths) without an exclusivity trap", "The actual implementation of the checking: rosters call sites — confirm whether rosters is copied to a local before indexing/mutating, since the diff as shown passes it directly, which is the known-bad pattern", "A full-repo grep or diff hunk showing RosterStore's old unguarded addPlayer(_:) is deleted or now itself routes through the domain check, with no remaining caller of an unguarded path", "A stated decision (and test) for whether ImportService should stop, skip, or roll back on a mid-batch One-League conflict"]}
```
