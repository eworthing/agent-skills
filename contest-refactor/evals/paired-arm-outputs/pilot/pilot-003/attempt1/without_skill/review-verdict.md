# Review — Loop 8, `architecture_quality`

## What the diff actually shows

The Actor introduces a `Clock` protocol + `SystemClock` conformer in a new file, and replaces one
direct `Date()` read (in `CheckoutFlow.swift`) with `clock.now()`. The report claims two more call
sites (shipping, account) were changed "the same way," but those diffs are not shown — only
asserted in prose. Full suite green (1,940 tests) is reported, but that number is the *existing*
suite; nothing in the diff shows a new test that actually exercises the new abstraction.

## Considered and ruled out

CONTEXT.md flags a Q4 rollout of region-specific notification rules (EU opt-in/audit, Region A
SMS-only, Region B push-first). It would be easy to pattern-match "region-specific" against a
time-handling change and demand the new `Clock` support per-region time zones. I checked that
instinct against the text: CONTEXT.md states directly that "timestamps are UTC system-wide with no
planned regional or per-feature variation" and that no other subsystems are changing this quarter.
That forecloses the concern — the notification work is about opt-in/channel routing, not clock
semantics, and the context explicitly denies any coming timezone requirement. I'm not raising this
as a finding; doing so would be scope-creep speculation the excerpt was written to rule out.

## Real gaps

1. **Diff is incomplete for the claim being made.** The report says three call sites were unified
   "the same way," but only one (`CheckoutFlow`) is shown. At a 9.5 bar the reviewer needs to see
   all touched call sites, plus — critically — where `clock` itself comes from on each type
   (constructor parameter? stored property with a default? a shared singleton reached for
   internally?). None of that wiring is in the diff. "One owner, one path" is only true if the
   injection is real DI and not a `Clock.shared`-style global smuggled in under a new name; the
   diff as given cannot distinguish the two.

2. **The headline benefit is asserted, not demonstrated.** The entire stated rationale for this
   refactor is "now injectable for tests" — but no test in the diff uses a fake/mock `Clock`. The
   1,940 passing tests only prove the code still compiles and behaves as before with `SystemClock`;
   they say nothing about whether the abstraction is actually reachable/overridable in a test
   context. A refactor whose stated value proposition is testability needs at least one test that
   exploits that testability (e.g., a `FakeClock` pinning `now()` and asserting checkout/shipping
   behavior at a boundary time). Without it, "injectable for tests" is a claim about intent, not a
   verified property of the code.

3. **Single-conformer protocol.** `Clock` currently has exactly one implementation in the diff,
   `SystemClock`. Introducing a protocol for one concrete type is premature abstraction unless a
   second conformer (a test double) already exists — which would also close gap #2. As written, the
   diff doesn't show that second conformer, so the protocol boundary is speculative rather than
   load-bearing.

4. **Naming collision risk.** Swift's standard library has shipped its own `Clock` protocol since
   SE-0329 (`ContinuousClock`, `SuspendingClock`, etc.). Declaring a top-level `protocol Clock` in
   an app module risks shadowing/ambiguity anywhere `Swift.Clock` or Swift Concurrency's clock APIs
   are also in scope, and is at minimum a confusing name to grep for. This isn't fatal (fully
   qualifying with `Swift.Clock` resolves it), but for a change whose selling point is "one owner,
   no ambiguity," picking a name that collides with a stdlib protocol is a real quality ding, not a
   nitpick.

## Bottom line

The underlying idea — one seam for reading current time instead of scattered `Date()` calls — is a
legitimate, low-risk, standard piece of architecture, and I'm not objecting to the direction. But
the evidence bundle for a 9.5 claim is thin: two of three call sites are asserted rather than shown,
the wiring mechanism is invisible, the one claimed benefit (test-injectability) has no test proving
it's true, and the abstraction currently has a single conformer. None of these are exotic asks —
they're the minimum evidence a "unify time access, DRY, injectable" claim should carry. I'd expect
this loop to close the gap with (a) the full diff for all three call sites including the injection
wiring, (b) a test using a fake clock, and (c) either a rename or an explicit note that the
`Swift.Clock` collision was considered and is safe.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "major — claimed benefit (test-injectability) and claimed scope (3 call sites) are asserted but not evidenced in the diff", "dimension_scores": {"architecture_quality": 7.5}, "flagged_smells": ["speculative single-implementation abstraction (protocol with one concrete conformer, no test double shown)", "unverified testability claim (no test exercises the new Clock seam)", "incomplete/redacted diff (2 of 3 call sites asserted, not shown; injection wiring not shown)", "naming collision risk with stdlib Swift.Clock protocol (SE-0329)"], "evidence_demanded": ["Full diff for the shipping and account call sites, not a prose summary", "The actual wiring showing how each type obtains its `clock` (constructor injection vs. default property vs. shared singleton)", "At least one test using a fake/mock Clock that pins `now()` and asserts behavior, substantiating the 'injectable for tests' claim", "Justification for a protocol with a single conformer, or evidence of the test-side second conformer", "Confirmation that `protocol Clock` does not collide with Swift's stdlib Clock protocol (SE-0329) in files that also touch Swift Concurrency"]}
```
