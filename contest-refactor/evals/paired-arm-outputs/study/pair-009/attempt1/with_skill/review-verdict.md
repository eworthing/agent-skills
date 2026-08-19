# Critic review — Loop 4, `concurrency` dimension (`Sources/Gallery/ImageCache.swift`)

## Step 1 — Inspect current code only

Treating the attached diff as current source for `ImageCache.swift` (per sandbox scope, no other
file is available to cross-check call sites). No prior `CURRENT_REVIEW.md` was supplied, so there
is nothing to anchor to; the scorecard below is derived fresh from the diff and the Actor's cited
test evidence, not from the Actor's own framing.

## Step 2 — Map mutable runtime concerns (Authority Map)

- **`storage: [String: UIImage]`** — sole mutable field on `ImageCache`. Writer: `insert(_:for:)`.
  Reader: `image(for:)`. Both routed through `lock.withLock { … }`. Single owner, single write
  site, protected read site — no *state with no authority*, no multi-writer hazard.
- **`lock: NSLock`** — immutable (`let`), scoped to the instance. No reentrancy: neither closure
  passed to `withLock` performs an `await`, so there is no *reservation after suspension* (the
  smell requires a suspension between check and claim; here the whole critical section is
  synchronous).
- **`evictionDelegate`** — removed this loop. As shown, it had a stored declaration but the diff
  gives no assignment/read site, consistent with the Actor's "unused" claim; removing it is the
  correct action rather than a finding.

## Step 3 — Architecture / deletion test

`ImageCacheWrapper` (removed): `image(for:)` and `insert(_:for:)` on the wrapper did nothing but
forward to `inner`. Deletion test: delete the Module — complexity does not reappear at any caller
(callers get the exact same two methods directly on `ImageCache`). Textbook pass-through; folding
it in is the correct subtractive fix, not a finding. No protocol is involved, so two-adapter
rule / repository theater / protocol soup do not apply here.

## Step 5 — Concurrency review (the dimension this loop claims)

**Suppression-as-fix check on `@unchecked Sendable`.** This is a safety-affecting suppression
(rubric: *fake-clean reward → suppression-as-fix*), so it only clears if it carries narrow scope +
concrete justification + the compensating invariant that makes it safe. Checked against the diff:
`ImageCache` is `final` (no subclass can add an unprotected stored var), its only mutable state is
`storage`, and both call sites that touch `storage` — `image(for:)` and `insert(_:for:)` — go
through `lock.withLock`. The inline comment states exactly this invariant. Scope, justification,
and compensating invariant are all present and match the diff. **Cleared** — not fake-clean
reward.

**Meta-rule 4 (risk-boundary evidence).** Non-`Sendable` → `@unchecked Sendable` is exactly the
kind of Sendable/thread-safety boundary crossing the rule flags: reasoning-only is not enough,
executable evidence is required. The Actor supplied it: `swift test --sanitize=thread --filter
ImageCacheConcurrencyTests` clean, backing a new test,
`ImageCacheConcurrencyTests.parallelInsertsAreSerialized`, described as hammering `insert` from 64
concurrent tasks. That satisfies the letter of the rule (a focused TSAN run exists), but the scope
of what it exercises is narrower than the concurrency claim being made.

**Mutation-test check on that evidence.** Name a mutation the cited test would not catch: delete
`lock.withLock` around the body of `image(for:)`, i.e. revert it to `storage[key]`. The only
concurrency test in evidence is described, by the Actor's own words, as driving concurrent
`insert` calls only — nothing in the report or diff indicates it also calls `image(for:)`
concurrently. TSAN only flags races on code paths actually exercised concurrently, so an unlocked
read racing a locked write would not be caught by an insert-only hammer test. This matters
specifically here because the scenario's own closing line establishes the real access pattern:
`prefetch`/`warmThumbnails` reach `insert` concurrently from background prefetch, while a gallery
screen showing those images would reach `image(for:)` for display around the same time — read and
write concurrently, not write and write. The shipped code *does* lock both methods correctly (I
have no evidence of a live race), but the regression test that's meant to be the executable proof
for this risk-boundary change doesn't cover the interleaving that would actually matter if a
future edit dropped the lock from the read side.

Severity: this is not a live defect in the diffed code, and it is not a likely disqualifier — a
cache module's read path is not one of the anchor's central-runtime-behavior examples
(reducer/engine, persistence writer, cancellation logic, navigation owner). It is a **Noticeable
weakness**: source-backed (from the Actor's own test description plus the scenario's stated access
pattern), reduces confidence in exactly the claim this loop is asking to be certified at 9.5, and
is the kind of gap Meta-rule 4 exists to catch ("a green single-config test run does not prove
preservation of every invariant... a data race passes nondeterministically").

**Minor, non-blocking note.** The Actor's prose says "Full suite green (1,312 tests)" while the
cited test-run line reports "1,313 passed" — a one-test difference consistent with the new
concurrency test being added after the prose was drafted. Not treated as a finding; flagged only
so it isn't mistaken for an unexplained discrepancy.

## Verdict

Approve the structural work (wrapper removal, dead-field removal, and the lock itself are all
correct, minimal, and honest fixes — no ceremony added, Simplify Pressure Test passes on all
three). Do not certify `concurrency` at the proposed 9.5 yet: the risk-boundary evidence required
by Meta-rule 4 is present but doesn't cover the mixed read/write interleaving that is the actual
concurrent-access shape of this cache. Conditional accept pending one additional test.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "Noticeable weakness",
  "dimension_scores": {
    "concurrency": 8.5
  },
  "flagged_smells": [
    "fake-clean reward (aggregate-test-count-as-test-strategy)"
  ],
  "evidence_demanded": [
    "A TSAN-covered concurrency test that interleaves concurrent `image(for:)` reads with concurrent `insert(_:for:)` writes on `ImageCache` (not insert-only concurrency), demonstrating the lock also serializes the read/write access pattern that `prefetch`/`warmThumbnails` plus gallery display actually produce."
  ]
}
```
