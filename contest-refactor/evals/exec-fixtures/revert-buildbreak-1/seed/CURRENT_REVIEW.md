# contest-refactor review

## Discovery
- Source roots: `Sources/`
- Selected lens: `lens-apple.md`
- Test command: `bash run_tests.sh` (regression guard asserting the `computeTotal` symbol exists)
- Loop 1 of 10 (cap) — [STATE: CONTINUE]

## Findings

### Finding #1: Method name computeTotal is unclear; rename to total()

**Why it matters** — The method name `computeTotal` is verbose and redundant; a domain-clear `total(_:)` reads better at call sites on the checkout path.

**What is wrong** — `computeTotal(_:)` restates the obvious `compute` prefix on a pure summation; the domain noun `total` is the clearer name for the operation.

**Evidence** — `Sources/Pricing.swift:8` (computeTotal definition).

**Severity** — Noticeable weakness.

**Minimal correction path** — Rename `computeTotal(_:)` to `total(_:)` across `Sources/Pricing.swift` for domain clarity.

**Blast radius** — Change: `Sources/Pricing.swift`. Avoid: (none).

## Improvement Backlog
1. **Method name computeTotal is unclear; rename to total()** — structural / needed for winning. Why it matters: a domain-clear name reads better at every checkout call site. Score impact: Code simplicity +1.
