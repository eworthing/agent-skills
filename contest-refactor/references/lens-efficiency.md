# Efficiency Lens (always-included)

This lens is **always-included** (like `lens-security.md`): Step 0 loads it unconditionally alongside the selected stack lens. It covers four structural-waste concerns the architecture rubric's Ignore-list distinguishes from out-of-scope "micro-optimizations" (see [architecture-rubric.md § Smell List](architecture-rubric.md#smell-list-smoke-not-findings)): a derivation computed more than once when one evaluation would do (D1), a sequential loop over independent I/O that could be concurrent (D2), blocking or per-item-repeated work on a startup or hot path (D3), and a long-lived closure retaining the scope it captured (D4). The Ignore-list still excludes true micro-optimizations: a seed without nameable cost — e.g., an O(1) accessor read three times — is not a finding. Findings here score under an existing scorecard dimension — `simplicity` (D1), `concurrency` (D2), `framework_idioms` (D3), or `state_management` (D4) — this lens **never** introduces a new scorecard dimension.

Every finding from this lens still carries the normal Evidence Chain: Claim → Source → Consequence → Remedy. Nothing below waives that.

## Contents

- [D1 — Recomputed derived value](#d1--recomputed-derived-value)
- [D2 — Sequential independent effects](#d2--sequential-independent-effects)
- [D3 — Hot-path / startup blocking work](#d3--hot-path--startup-blocking-work)
- [D4 — Closure-capture retention](#d4--closure-capture-retention)
- [Overlap rule (one defect, one finding)](#overlap-rule-one-defect-one-finding)

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

## D3 — Hot-path / startup blocking work

Blocking or per-item-repeated work on a startup or per-frame/per-request hot path, where one deferred, offloaded, or batched execution would do.

1. **Mechanical seed**: synchronous I/O or a heavy decode reachable from a startup entry point (`@main`, `application(_:didFinishLaunching:)`, root `App`/scene `init`; other stacks: module import time, server bootstrap before it starts listening) — hits: `rg -n 'Data\(contentsOf:|String\(contentsOf:|try! JSONDecoder' <startup files>`; OR a loop that issues one I/O call per element where a batch form exists (`IN (…)` query, bulk read) — hits: `rg -n -B3 'await|fetch|query|read' <loop bodies>`, then confirm a per-iteration call and an available batch equivalent. Seed only when the path is provably startup/hot, not a cold administrative path invoked on demand.
2. **Fix guardrail (load-bearing — state this explicitly in every D3 finding)**: name the cost (launch latency / watchdog exposure / N× round-trips, with N cited) **and** the fix risk. Deferring startup work reorders initialization — name which consumer reads the value and how readiness is awaited; a consumer reading not-yet-loaded state is a new bug. Batching changes failure semantics — per-item error isolation or retry must be preserved, or its loss named.
3. Maps into the existing `framework_idioms` dimension — the platform prescribes non-blocking startup and batched access (watchdog limits, event-loop stalls, N+1 access patterns); the finding is a platform-best-practice violation. **Never a new scorecard dimension**.

## D4 — Closure-capture retention

A closure stored in a long-lived home (static/singleton registry, cache, observer/timer token, escaping handler kept in a property) that captures the enclosing scope (`self`, a large collection, a request context) while using a fraction of it — keeping the whole scope alive for the closure's lifetime.

1. **Mechanical seed**: a closure assigned into a stored property / static collection / `NotificationCenter.addObserver` / `Timer.scheduledTimer` / callback registry whose body references `self` or a large enclosing local with no capture list narrowing it — hits (Swift): `rg -n -A4 'addObserver|Timer\.scheduledTimer|Handler\s*=\s*\{|callbacks\.(append|\[)' Sources/`, then check the bodies for `self.` with no `[weak self]`/value capture; other stacks: module-level registries/caches holding closures over scope-bound data. Requires **both** halves — a long-lived home AND a broad capture. A short-lived completion handler is not a seed.
2. **Fix guardrail (load-bearing — state this explicitly in every D4 finding)**: name the retention cost (which object/collection stays alive, roughly how large, for how long) **and** the fix risk. `[weak self]` changes behavior when the owner is gone (the closure no-ops or must handle `nil` — name which); capturing narrowed values freezes them at creation (D1's staleness rule in mirror form). Where the enclosing object is genuinely app-lifetime, name that explicitly as why retention does not apply.
3. Maps into the existing `state_management` dimension — a retaining closure is an undeclared owner; lifetime/ownership is exactly what runtime-ownership review scores. **Never a new scorecard dimension**.

## Overlap rule (one defect, one finding)

One defect produces one finding, never two across detectors. A sequential per-item `await` loop reports as **D3 when a batch API exists** (batch beats fan-out — the smaller, deeper remedy) and as **D2 otherwise**; never both. Cross-detector duplicates that share Source + Consequence + Remedy merge before scoring, per the findings registry's fuzzy-match spirit ([method.md Step 1.5](method.md)).
