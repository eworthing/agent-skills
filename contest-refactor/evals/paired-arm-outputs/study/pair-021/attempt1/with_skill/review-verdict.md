# Critic Review — Loop 4, `domain_modeling`

## Claim

The Actor's report says `RosterView` and `ImportService` now "validate/guard the single-league
invariant" and proposes `domain_modeling` → 9.5. Independently re-deriving from the diff (per
Method step 1's anchor-to-source warning: the Actor's report is a claim, not proof), the actual
change does not give the One-League Rule an owner. It gives it two owners.

`LeagueRoster` is named in the scenario as "the domain owner" of the invariant (CONTEXT.md §3,
a hard domain invariant, binding whether a player enters "through the UI or via a bulk CSV
import"). The diff to `Sources/Domain/LeagueRoster.swift` adds only a doc comment —
`/// Adds a player. Callers are expected to pre-validate the One-League Rule.` — the method body
is untouched (`activePlayers.append(player)`, no guard, no throw). The domain owner still trusts
its caller unconditionally. Enforcement instead lands as two independently-written, ad hoc guard
blocks:

- `Sources/Presentation/RosterView.swift` `handleAdd(_:)` — scopes the check via
  `store.currentRoster.leagueID`.
- `Sources/Infrastructure/ImportService.swift` `importRoster(from:)` — scopes the check via
  `row.leagueID`.

This is the textbook **weak domain model** (anemic domain type) smell from the rubric's smoke
list, promoted to a finding because source proves harm, not naming: the scenario's own
commentary states the two guards "silently diverge" if `row.leagueID` and
`store.currentRoster.leagueID` ever resolve differently, since nothing forces them to agree —
they are two separate implementations of the same domain rule, not one. That is also
**duplicate state / duplicate abstractions**: the invariant-check logic is duplicated rather than
shared, and a third call site added later (an admin bulk-edit tool, a trade-processing path) has
nothing to inherit from — it would have to reimplement the guard a third way, or skip it
entirely by calling `addPlayer` directly, since the domain object itself still accepts anything.

The doc comment on `LeagueRoster.addPlayer` is itself worth flagging as a **fake-clean reward**
sub-pattern: it reads as if the contract is now documented and handled, while the actual
enforcement mechanism the comment describes doesn't exist in the type it's attached to. A
compliance-shaped comment is not a compliance-shaped implementation.

## A second, sharper defect: the ImportService guard is reentrant

`ImportService.importRoster` is a plain `actor`, and `store` (a `RosterStore`) is accessed with
`await` at both call sites — `await store.allRosters` (the check) and, later, `await
store.addPlayer(player)` (the write). That `await` on a plain synchronous-looking property read
only makes sense if `store` is itself actor-isolated (elsewhere, `RosterView` — MainActor-bound —
calls `store.addPlayer(player)` with no `await`, consistent with `RosterStore` being
`@MainActor`). So the check and the write are two separate hops across an isolation boundary,
with a suspension between them and no atomic recheck at the write:

```
await store.allRosters.filter { ... }   // <-- suspend, check "is this available"
guard activeRosters.isEmpty else { throw ... }
await store.addPlayer(player)           // <-- suspend again, then claim, unconditionally
```

This is exactly the rubric's **reservation after suspension** smell: "a check-then-claim flow
that suspends between 'this is available' and 'this attempt owns it' is reentrant." The
carve-out ("the actual authority rechecks and atomically claims in one transactional /
actor-isolated step") does not apply — `LeagueRoster.addPlayer` is confirmed to be a plain,
unconditional append with no recheck. Two interleaved import batches, or an in-flight import
racing a UI `handleAdd`, can both pass the check on the MainActor hop before either commits the
write, and both then append the same player to the same league — corrupting exactly the
invariant this loop claims to have hardened, on the bulk-import path CONTEXT.md explicitly calls
out as a required enforcement point. This is not hypothetical future drift; it is live in the
diff as submitted.

## Architectural test applied

**Deletion test / correct-owner test**: delete both ad hoc guards. The complexity (the check)
reappears at both call sites the moment either needs to re-add it — proving the check is real,
not ceremony. But the *right* place for that complexity to reappear is not "reimplemented at
each caller," it's *inside the domain owner*, exactly once. The Actor treated this as "extract
guards to callers" when the correct move was "push guards into `LeagueRoster`/`RosterStore` and
have callers ask it, not decide for it" (Tell, Don't Ask — both current callers *ask* `store` for
data and *decide* independently, rather than *telling* the domain object to attempt the mutation
and letting it own the decision).

**Interface-is-test-surface**: the Actor's report cites only aggregate suite count ("2,041
passed"), not a specific test file/assertion at the new guard logic's interface, and no
`interface_test_coverage_path`. Per the rubric's mandatory mutation-test check: a nameable
mutation swapping which `leagueID` source `ImportService`'s guard reads (`row.leagueID` →
`store.currentRoster.leagueID`, matching `RosterView`'s expression) would not obviously fail any
test cited in the report — the two guards were never tested against each other for agreement.
That mutation sits on a primary flow (bulk CSV import, explicitly named alongside UI add as a
required enforcement surface), so per Method step 8 this is a Noticeable-or-worse missing-test
finding, not a Cosmetic one, and it compounds the ownership defect above.

## Severity

Both defects point the same direction, so I'm treating them together for the verdict:

- **Multi-writer authority over a primary domain concern** — the One-League Rule, a stated hard
  domain invariant, has two independent enforcement implementations and zero enforcement at its
  named domain owner. This is one of the rubric's own listed examples of a Likely disqualifier.
- **A racing async flow that can corrupt user-visible state** — the ImportService check-then-act
  sequence is reentrant across a real actor-isolation suspension, on the bulk-import primary
  flow, with no atomic recheck at the write. This is also one of the rubric's own listed examples
  of a Likely disqualifier, and it is present in the code as submitted, not speculative.

Both examples are drawn essentially verbatim from the rubric's own `Likely disqualifier` anchor
text. I'm not stretching "future drift" into a finding — the divergence risk is the *diff's own*
commentary, and the reentrancy is a structural read of the actor-isolation boundaries as written.

This is fully source-derivable (ownership/duplication/reentrancy are general design-correctness
properties, not a business rule CONTEXT.md would need to supply), so the context-sufficiency cap
doesn't apply here — there's no missing external decision blocking judgment, just a defect to
score.

## Verdict

Reject the proposed `domain_modeling` → 9.5. The loop made real forward progress (previously
`addPlayer` had *no* guard anywhere; now there is at least a check on both entry paths), but the
chosen shape is the wrong one for a domain invariant: duplicated, divergence-prone, ownerless at
the type that's supposed to own it, and — on the import path — actually reentrant. None of that
is dischargeable by the green suite; the suite doesn't exercise cross-path agreement or
concurrent execution.

Required before this dimension can be re-proposed at 9.5:

1. Move the check into a single validating/throwing entry point at the actual mutation authority
   (`RosterStore.addPlayer` or `LeagueRoster.addPlayer`), performed atomically within its own
   isolation domain — no suspension between "check" and "claim."
2. Delete both duplicated guard blocks in `RosterView` and `ImportService`; both become thin
   callers that catch/map the single thrown domain error.
3. A test that adds the same player to the same league via the UI path and via the import path
   against a pre-populated roster, asserting rejection *from the single domain entry point* — not
   from either caller's ad hoc logic — so a future third caller inherits the guarantee for free.
4. Either an executable concurrency proof (a focused test or TSAN-style race demonstration) that
   the closed version cannot double-admit under concurrent import/UI activity, or — if not
   mechanically testable — explicit reasoning-only evidence recorded in `loop_result` per Method
   meta-rule 4, since this change crosses an actor-isolation risk boundary.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"domain_modeling": 4.5}, "flagged_smells": ["weak domain model", "duplicate state", "duplicate abstractions", "fake-clean reward", "reservation after suspension"], "evidence_demanded": ["Single validating/throwing entry point for the One-League Rule at the actual mutation authority (RosterStore.addPlayer or LeagueRoster.addPlayer), checked and committed atomically within one isolation domain with no suspension between check and claim", "Deletion of the duplicated ad hoc guards in RosterView.handleAdd and ImportService.importRoster in favor of thin callers that catch/map the single thrown domain error", "A test exercising both the UI-add path and the bulk-import path against a pre-populated roster that asserts rejection from the single domain entry point, not from either caller's own logic", "Executable concurrency evidence (focused test or race-detector run) that concurrent import/UI activity cannot double-admit a player past the closed guard, or recorded reasoning-only justification per Method meta-rule 4 if not mechanically testable", "loop_result.interface_test_coverage_path citing the specific test file and assertion range that exercises the new domain-owned validating entry point"]}
```
