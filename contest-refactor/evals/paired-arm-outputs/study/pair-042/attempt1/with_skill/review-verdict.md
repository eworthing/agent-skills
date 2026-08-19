# Critic Review — Loop 4 (`domain_modeling`)

## What the Actor claims vs. what the diff shows

The Actor reports the One-League Rule is now enforced on both the UI add-path (`RosterView`)
and the bulk-import path (`ImportService`), suite green (2,041 tests), and proposes
`domain_modeling` → 9.5.

Independently walking the diff (Method Step 1 — inspect current code, do not echo the report):
`LeagueRoster` is the declared domain owner of the One-League Rule (`CONTEXT.md` §3, per the
scenario). `LeagueRoster.addPlayer` is untouched behaviorally — the only change is a doc comment:

```
/// Adds a player. Callers are expected to pre-validate the One-League Rule.
mutating func addPlayer(_ player: Player) {
    activePlayers.append(player)
}
```

That is the finding in one line: the domain type that owns the invariant does not enforce it. It
is a plain, trusting mutation with a comment asking callers to be careful. The actual enforcement
was pushed *out* of the domain layer into two independent call sites:

- `RosterView.handleAdd` (Presentation) — filters `store.allRosters` by
  `$0.leagueID == store.currentRoster.leagueID`.
- `ImportService.importRoster` (Infrastructure) — filters `store.allRosters` by
  `$0.leagueID == row.leagueID`.

## Architectural tests applied

**Authority Map (Method Step 2).** The One-League Rule is a single mutable-runtime concern
(membership uniqueness per league). Its writers are now: `RosterView`'s ad hoc guard and
`ImportService`'s ad hoc guard — two independent implementations of the same policy, with no
single owner. `LeagueRoster.addPlayer`, the actual state mutator, has no write-time check at all.
This is a textbook **no single owner per mutable concern** violation (Method meta-rule 5 explicitly
calls for removing "duplicate authority" *before* adding structure — this loop did the opposite:
it added a second copy of the authority instead of consolidating the first).

**Shallow module test.** Interface (`LeagueRoster.addPlayer`) ≈ Implementation (`append`, no
validation) → shallow. The domain object should be the deep module here: small interface
(`addPlayer(_:) throws`), implementation absorbing the invariant, one place to change if the rule
changes. Instead the "interface ≈ implementation" shallowness has been preserved and the missing
depth was smeared across two callers in two different layers.

**Deletion test (on the two guard blocks).** Delete `RosterView`'s guard block: the check does not
reappear anywhere else for that call path (nothing catches a violating add from the UI).
Same for `ImportService`'s guard block. Each one, standing alone, is load-bearing — which is
exactly why duplicating it instead of centralizing it in `LeagueRoster` is the wrong shape: two
call sites are each independently responsible for reimplementing domain policy, and any third
caller of `addPlayer` (present or future) gets no protection at all.

**Interface-is-test-surface (Method Step 8 / Architectural Test 4).** Since `LeagueRoster.addPlayer`
still has no validation, no test on the domain type itself can be asserting the invariant — any
coverage of the One-League Rule is necessarily sitting on `RosterView`/`ImportService` tests, i.e.
past the Interface that should own it. 2,041 green tests do not establish that the domain layer
enforces its own core invariant; per Meta-Rule 2 ("counts are not quality") and the Authority-Map
test cross-check, the suite size is not evidence here — the specific test-at-the-right-Interface
question is unanswered by the report.

## Why this is not "contained"

The scenario itself supplies the concrete drift case, so this isn't speculative: `RosterView`
resolves the league via `store.currentRoster.leagueID`; `ImportService` resolves it via
`row.leagueID`. Those two resolutions are not guaranteed to agree, and nothing keeps them
in sync — they are two hand-written copies of "is this player already active in this league,"
not one owner. A future change that makes `row.leagueID` resolve differently (e.g. a multi-league
import, a stale row, a league-transfer edge case) silently reopens the exact hole this loop was
supposed to close, on the bulk-import path in particular, which is precisely the kind of path a
human isn't watching row-by-row.

This lands squarely in the rubric's **Likely disqualifier** anchor: a core architectural property
the rubric rewards for `domain_modeling` (an invariant is owned and enforced by the domain type)
is broken, and the harm is reachable from a primary flow — `RosterView.handleAdd` *is* the
primary "add a player" user flow, and `ImportService.importRoster` is a primary bulk-ingest flow.
It is not merely a style nit or something a reasonable judge could rank highly despite — the
invariant this whole loop was chartered to fix is, after the loop, still unenforced at its
rightful owner and instead exists as two divergent, unsynchronized copies. "Durable state
[ownership] written from multiple places with no owner" is one of the rubric's own disqualifier
examples, and duplicated *policy* enforcement with no single owner is the same shape one layer up.

## Named smells

- **Weak domain model** (promoted from smoke to finding — source evidence, not speculation: the
  domain type's own mutator has zero enforcement, and the comment admits it).
- **Duplicate abstractions** — the same guard logic reimplemented twice, in two different layers,
  with two different key derivations.
- **Unclear ownership** — no single writer/owner for the One-League Rule; the Authority Map
  cannot name one.
- **Fake-clean reward** — the Actor's report ("RosterView validates... ImportService now also
  guards... Proposing domain_modeling → 9.5") reads as complete because both known call sites
  currently pass, and the doc comment on `addPlayer` gives the appearance of an acknowledged
  contract. But per the rubric's own definition, this is exactly the pattern: score-up on
  comments/tidy-looking coverage while the actual ownership is unresolved. The `///` comment is
  not enforcement — it is documentation of a violated invariant standing in for a fix.

## What would need to change

Move the check into `LeagueRoster` itself — e.g. `addPlayer(_:) throws` (or a `Result`/validating
initializer) that checks the One-League Rule against its own state (or a passed-in cross-league
context if roster-crossing state genuinely can't live on `LeagueRoster` — the scenario doesn't
show enough to say which, and that's part of what's demanded below). `RosterView` and
`ImportService` should both become thin callers that surface the thrown/returned error, not
independent re-implementers of the policy. That also fixes the Interface-is-test-surface problem:
a test on `LeagueRoster` itself becomes possible and necessary, and it would be the one place a
future caller can't accidentally bypass.

This is a Simplify-Pressure-Test failure on the loop's own terms (Q3 — "does it avoid duplicate
layers?" — no; Q2 — "smallest honest fix?" — no, the domain method already existed as the natural
seam and this loop routed around it instead of into it) as well as a domain_modeling failure.

## Verdict

Not accepted at 9.5 for `domain_modeling`. The invariant this loop targeted is still not owned by
the domain type; it now exists as two divergent, layer-scattered copies instead of one ad hoc copy
scattered across callers before the loop — a lateral move, not the deepening the rubric asks for.
Rejecting with a concrete, minimal remedy (consolidate into `LeagueRoster`) rather than flagging as
conditional, since the defect and the fix are both fully determinable from the attached diff and
scenario context — no missing evidence is blocking judgment here, unlike a case that would need a
HALT for an undisclosed business rule.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"domain_modeling": 4},
  "flagged_smells": ["weak domain model", "duplicate abstractions", "unclear ownership", "fake-clean reward"],
  "evidence_demanded": [
    "LeagueRoster owns the One-League Rule check inside a single method (e.g. addPlayer(_:) throws / Result-returning), replacing the plain trusting mutation",
    "RosterView.handleAdd and ImportService.importRoster both route through that single domain-owned check instead of each re-deriving league membership independently",
    "A test exercising LeagueRoster directly (not RosterView/ImportService) that fails if the invariant check is removed or short-circuited — the Interface-is-test-surface requirement",
    "Removal of the two duplicated ad hoc guard blocks once the domain method absorbs the logic",
    "Confirmation (grep or enumeration) that no other current caller of LeagueRoster.addPlayer bypasses the new domain-owned check"
  ]
}
```
