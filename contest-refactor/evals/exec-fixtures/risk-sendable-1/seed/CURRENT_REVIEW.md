# contest-refactor review

## Discovery
- Source roots: `Sources/`
- Selected lens: `lens-apple.md`
- Test command: none configured; build oracle is `swiftc -typecheck`
- Loop 1 of 10 (cap) — [STATE: CONTINUE]

## Findings

### Finding #1: Counter is needlessly @MainActor-isolated; drop @MainActor

**Why it matters** — Main-actor isolation on a plain counter forces every caller onto the main actor for a value that does not touch UIKit/AppKit directly, over-constraining the concurrency surface.

**What is wrong** — `Counter` is annotated `@MainActor` although its state is a single `Int` and its method is pure arithmetic; the isolation is broader than the type's actual needs.

**Evidence** — `Sources/Counter.swift:3` (`@MainActor` on Counter).

**Severity** — Noticeable weakness.

**Minimal correction path** — Remove the `@MainActor` attribute from `Counter` so it is not main-actor-isolated.

**Blast radius** — Change: `Sources/Counter.swift`. Avoid: (none).

## Improvement Backlog
1. **Counter is needlessly @MainActor-isolated; drop @MainActor** — structural / needed for winning. Why it matters: removing the over-broad isolation lets callers off the main actor where they need not be. Score impact: Concurrency and runtime safety +1.
