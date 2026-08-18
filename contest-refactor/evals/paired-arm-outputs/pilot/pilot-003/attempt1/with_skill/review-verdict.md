# Review: Loop 8 — `architecture_quality`

## Scope

Reviewing the `Clock` consolidation diff against `architecture-rubric.md` and `method.md`, independent of the Actor's report. CONTEXT.md §5 says timestamps are UTC system-wide with no planned regional/per-feature variation this quarter — that rules out "future timezone support" as an implicit justification for a new seam, but the Actor never claimed that, and the choice here (whether this seam is architecturally sound) is determinable from source, not from an absent business rule. So the roadmap note is background only; it does not trigger the context-sufficiency cap and does not itself support or block the finding below.

## What the diff actually does

Introduces `protocol Clock { func now() -> Date }` and exactly one production conformer, `struct SystemClock: Clock { func now() -> Date { Date() } }`. Rewrites three call sites (Checkout, Shipping, Account) from `Date()` to `clock.now()`.

## Unified Seam Policy check (two-adapter rule)

This is a new Seam. Per the Unified Seam Policy it needs (a) at least two real Adapters (prod + behavior-faithful test fake), or (b) a named single-Adapter justification (policy / failure isolation / platform isolation).

- **(a) fails as shown.** Only `SystemClock` appears anywhere in the diff or the Actor's report. No `FakeClock`/`TestClock`/`MockClock` is introduced, and no test file or assertion is cited that exercises the injected clock. "Now test-injectable" is a capability claim, not a demonstrated one. Architectural Test #5's carve-out for transitively-tested Interfaces requires the loop to name a `target_symbol` and cite specific test file(s) + assertion ranges that would fail if `now()` were replaced with a no-op — nothing of the sort is offered.
- **(b) also fails.** `SystemClock.now()` is a bare `{ Date() }` — no retry, no rate limiting, no idempotency (rules out policy/(i)); there is no failure path to isolate (rules out failure isolation/(ii)); and unlike the rubric's platform-isolation examples (Spotify SDK, hardware-bound APIs with *no* test harness), `Date()` is trivially fakeable — that fakeability is the entire reason a DI seam would be worth building here, which cuts against invoking platform isolation/(iii), not for it.

Neither path holds. Per the rubric's own Unified Seam Policy text: *"If neither (a) nor (b) holds, the Seam fails the policy. Inline the implementation; merge the Module. Bare testability without behavior-faithful fake → protocol soup; reject."* That is exactly this diff's shape.

## Deletion test / shallow-module test

Delete `Clock`/`SystemClock`: the three call sites revert to `Date()`. No complexity reappears — `Date()` is already a one-line stdlib call, so this is a pass-through per the Deletion test ("Complexity vanishes → pass-through. Delete it."). Interface (`now() -> Date`) ≈ Implementation (`{ Date() }`): textbook shallow module (Architectural Test #3).

## Named smell: Repository theater

*"repository/protocol split with one real Adapter where the Interface adds no policy, failure isolation, replacement value, or Locality."* `SystemClock`'s Interface adds none of the four — the one candidate value (replacement for tests) is asserted by the Actor, not shown in the diff.

## Evidence-chain gap on the Actor's own claim

"Now injectable for tests" plus "Full suite green (1,940 tests)" is the *aggregate-test-count-as-test-strategy* sub-pattern of fake-clean reward: none of the 1,940 tests are shown or cited as exercising the new seam specifically. Per the Evidence Chain rule, a claim with no Source should be downgraded, not used to justify a score bump — "DRY, one owner, now injectable" reads as three claims, only the first of which (one owner / no duplicated `Date()` reads) is actually backed by the diff.

## Severity

**Serious deduction** — a real Seam-policy violation in a meaningful, cross-cutting module (Time, touching three flows), but contained: nothing breaks at runtime, the existing suite still passes, and the harm is to Leverage/credibility rather than to a primary-flow invariant. Not a Likely disqualifier — no runtime property is broken and no primary flow is corrupted.

## What would clear it

Either (1) land a behavior-faithful `FakeClock`/`TestClock` conformer plus at least one test per touched flow that would fail if `now()` returned a fixed or no-op value (satisfies the two-adapter rule and the Evidence Chain's Source requirement), or (2) supply the missing Unified Seam Policy path-(b) justification by name with source evidence. Absent either, the honest remedy is to inline `clock.now()` back to `Date()` at the three sites and drop the protocol — the seam is currently indirection without proven leverage.

## Verdict

The loop's proposed `architecture_quality → 9.5` does not hold. The consolidation itself is harmless (no regression, tests green), but the only claimed architectural gain — a testable seam — is unsupported by the diff, and the seam as built fails the rubric's own Unified Seam Policy test on both paths. This blocks the 9.5 threshold for `architecture_quality` this loop.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"architecture_quality": 7.5}, "flagged_smells": ["Repository theater", "fake-clean reward (aggregate-test-count-as-test-strategy)"], "evidence_demanded": ["A behavior-faithful FakeClock/TestClock conformer to Clock, distinct from SystemClock", "At least one test per touched flow (Checkout, Shipping, Account) that injects the fake clock and would fail if now() returned a fixed/no-op value", "Specific test file(s) + assertion line ranges citing the target_symbol (Clock.now() call sites) per Architectural Test #5's indirect-coverage carve-out", "OR an explicit Unified Seam Policy path-(b) justification naming which of policy/failure-isolation/platform-isolation applies to SystemClock, with source evidence"]}
```
