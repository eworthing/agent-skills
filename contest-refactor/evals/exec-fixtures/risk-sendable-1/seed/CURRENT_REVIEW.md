# contest-refactor review

## Discovery
- Source roots: `Sources/`
- Selected lens: `lens-apple.md`
- Test command: none configured; build oracle is `swiftc -typecheck`
- Loop 1 of 10 (cap) — [STATE: CONTINUE]

## Contest Verdict
Sound, with an over-broad isolation boundary

A small, single-owner counter whose @MainActor annotation is broader than its invariants need; narrowing it crosses an isolation boundary and needs evidence.

## Scorecard (1-10)
- Architecture quality: 8 | SAME | Sources/Counter.swift:6-13 — small single-purpose reference type
- State management and runtime ownership: 8 | SAME | Sources/Counter.swift:8 — value is private(set); single owner of mutation
- Domain modeling: 8 | SAME | Sources/Counter.swift:6-13 — a counter is a thin but coherent domain type
- Data flow and dependency design: 8 | SAME | Sources/Counter.swift:8 — explicit state, no globals
- Framework / platform best practices: 8 | SAME | Sources/Counter.swift:6 — final class, private(set) — idiomatic
- Concurrency and runtime safety: 7 | SAME | Sources/Counter.swift:3 — @MainActor isolates a plain Int counter more broadly than its invariants require
- Code simplicity and clarity: 8 | SAME | Sources/Counter.swift — minimal surface; one stored property, one method
- Test strategy and regression resistance: 8 | SAME | Sources/Counter.swift — compiles under swiftc -typecheck single-config; no planted regression test
- Overall implementation credibility: 8 | SAME | Sources/Counter.swift:3-5 — doc comment honestly notes the UI-facing isolation rationale

## Authority Map
- Concern: Counter value mutation
  - Owner: Counter (@MainActor reference type)
  - Allowed writers: Counter.increment()
  - Observers / readers: UI layer reading Counter.value
  - Persistence seam: None
  - Async mutation entry points: []
  - Verdict: Single owner, over-broad isolation

## Strengths That Matter
- Mutation is funneled through one method with private(set) state — a single clear owner (Sources/Counter.swift:8,10)

## Findings

### Finding #1: Counter is needlessly @MainActor-isolated; drop @MainActor

**Why it matters** — Main-actor isolation on a plain counter forces every caller onto the main actor for a value that does not touch UIKit/AppKit directly, over-constraining the concurrency surface.

**What is wrong** — `Counter` is annotated `@MainActor` although its state is a single `Int` and its method is pure arithmetic; the isolation is broader than the type's actual needs.

**Evidence** — `Sources/Counter.swift:3` (`@MainActor` on Counter).

**Severity** — Noticeable weakness.

**Minimal correction path** — Remove the `@MainActor` attribute from `Counter` so it is not main-actor-isolated.

**Blast radius** — Change: `Sources/Counter.swift`. Avoid: (none).

## Simplification Check
- Structurally necessary: Dropping @MainActor narrows an over-broad isolation; it crosses an isolation/Sendable boundary, so it requires preservation evidence (Meta-Rule 4) rather than a blind edit.
- New seam justified: False
- Helpful simplification: Remove the @MainActor attribute so callers are not forced onto the main actor.
- Should NOT be done: Do not introduce an actor or a lock — the type's invariant does not require either.
- Tests after fix: swiftc -typecheck Sources/Counter.swift; the executor must record Meta-Rule-4 preservation evidence for the isolation change or carry the finding forward.

## Improvement Backlog
1. **Counter is needlessly @MainActor-isolated; drop @MainActor** — structural / needed for winning. Why it matters: removing the over-broad isolation lets callers off the main actor where they need not be. Score impact: Concurrency and runtime safety +1.
## Builder Notes
None this loop — no structural lessons beyond the findings themselves.

## Final Judge Narrative
Ownership is clean, but the @MainActor annotation over-constrains callers. Narrowing it is a boundary-crossing change that must be backed by Meta-Rule-4 preservation evidence.
