# Efficiency Lens (opt-in)

This lens is **opt-in**, unlike `lens-security.md` (always-included). Step 0 does not load it by default; it is loaded only when the invocation passes `--force-lens efficiency` (see [startup.md § flag catalog](startup.md)), and it **adds** to whatever stack lens Step 0 already selected rather than replacing it. It covers two narrow structural-waste concerns that the architecture rubric's Ignore-list otherwise treats as out-of-scope "micro-optimizations" (see [architecture-rubric.md § Smell List](architecture-rubric.md#smell-list-smoke-not-findings)): a derivation computed more than once when one evaluation would do, and a sequential loop over independent I/O that could be concurrent. Findings here score under the existing `simplicity` dimension (D1) or the existing `concurrency` dimension (D2) — this lens never introduces a new scorecard dimension.

Every finding from this lens still carries the normal Evidence Chain: Claim → Source → Consequence → Remedy. Nothing below waives that.

## Contents

- [D1 — Recomputed derived value](#d1--recomputed-derived-value)
- [D2 — Sequential independent effects](#d2--sequential-independent-effects)

## D1 — Recomputed derived value

A pure derivation with no single evaluation owner, re-executed N× within one render/frame/request pass instead of being evaluated once and threaded through.

1. **Mechanical seed**: a computed property read ≥3 times by sibling sub-view computeds inside one SwiftUI `body` (or the equivalent idiom on other stacks — a pure function/getter invoked repeatedly within one logical pass instead of being evaluated once and threaded through). Hits: enumerate a view's computed properties (`grep -n '^\s*\(private \)\?var \w\+: .* {$' File.swift`), then count in-file references to each identifier (`grep -c '\bidentifierName\b' File.swift`); ≥3 non-definition occurrences reached from within the same `body` chain is the seed. For non-SwiftUI stacks: a pure function invoked ≥3× within one request-handling function or render pass, each call re-deriving the same output from unchanged inputs.
2. **Fix guardrail (load-bearing — state this explicitly in every D1 finding)**: stored derived values cross the reactivity risk boundary. Turning a computed property into a stored one produces a frozen/stale value if any of its inputs is `@Environment` or other observable state that can change without the stored value being invalidated. A D1 finding must name both the recomputation cost **and** the staleness risk of the obvious fix — never the cost alone. Where the inputs are provably static for the value's lifetime (no observable/`@Environment` input), name that explicitly as why the staleness risk does not apply here.
3. Maps into the existing `simplicity` dimension, framed as derivable-state duplication — **never a new scorecard dimension**.

## D2 — Sequential independent effects

A `for`/sequential-`await` loop over order-independent I/O whose loop bodies write only loop-local state (no shared mutable state read or written across iterations).

1. **Mechanical seed**: a sequential loop containing `await` calls that are independent of each other. Hits: `rg -n -A8 'for \w+ in ' Sources/ | rg 'await'` (or the loop-construct equivalent on other stacks) — then confirm no shared mutable var/array/dictionary is written by more than one iteration. A loop-local accumulator returned once after the loop completes is fine; concurrent writes into a shared collection are a separate accumulation-safety finding, not this one.
2. **Fix guardrail (load-bearing — state this explicitly in every D2 finding)**: adding concurrency here is exactly the risk boundary [method.md Meta-Rule 4](method.md#meta-rules-apply-everywhere) governs — a fix that crosses an actor/isolation, `Sendable`/thread-safety, or lock/ordering boundary must preserve that invariant and record evidence in `loop_result` (compile matrix, focused test, or thread sanitizer; reasoning-only only when the invariant is not mechanically testable). A D2 finding must name the correctness burden alongside the opportunity: bounded concurrency (never an unbounded fan-out), preserved back-off/retry semantics, preserved cancellation, and respect for any documented serial carve-outs in the codebase under review.
3. Maps into the existing `concurrency` dimension — **never a new scorecard dimension**.
