# Critic Review — Loop 3, `framework_idioms`

## Step 1 — Inspect current code only

The Actor's claim: extracting the haptic call out of `NowPlayingView` into a new `Haptics`
enum "keeps the view declarative," tests are green (1,312 passed, iOS Simulator only), and
`framework_idioms` should move to 9.5. I re-derive against current source (the diff + the
unchanged `Package.swift`) rather than accepting that report.

## Claim

The refactor moves `#if`-gated, platform-specific code (a `canImport(UIKit)` block wrapping
`UIImpactFeedbackGenerator`) from inline in `NowPlayingView.swift` into a new file,
`Haptics.swift`. Per Method Meta-Rule 4 and Step 5 ("Cross-platform compile correctness"),
any refactor that touches conditional-compilation code is a **risk-boundary crossing**: the
Actor must preserve compile correctness across the full declared target matrix and record
either executable evidence for that matrix or an explicit, labeled limitation. Neither is
present — the only test run cited is `xcodebuild test … -destination 'platform=iOS
Simulator,name=iPhone 15'`.

That matters here because `Package.swift` (unchanged this loop) declares three first-class
platforms: `.iOS(.v17), .macOS(.v14), .tvOS(.v17)`, and the single `Soundboard` target has no
platform-specific exclusions — the same source, including the new `Haptics.swift`, is compiled
for all three.

## Source

- `Package.swift:12` — `platforms: [.iOS(.v17), .macOS(.v14), .tvOS(.v17)]`, single target
  `Soundboard` with no per-platform source split.
- `Sources/Soundboard/Haptics.swift` (new) — the entire `enum Haptics` body, including
  `tap()`'s reference to `UIImpactFeedbackGenerator`, is wrapped in `#if canImport(UIKit)`.
- `NowPlayingView.swift` diff — the call site wraps `Haptics.tap()` in the same
  `#if canImport(UIKit)` guard.
- Framework-availability fact (platform-lens knowledge, not a file in this sandbox):
  `canImport(UIKit)` evaluates **true on tvOS** — tvOS ships UIKit as its UI framework — but
  `UIImpactFeedbackGenerator` (and its `UIFeedbackGenerator` siblings) are not available on
  tvOS; Apple TV's Siri Remote has no Taptic Engine and these APIs are scoped to
  iOS/iPadOS/Mac Catalyst. `canImport(UIKit)` is the classic wrong guard for "iOS-only" —
  `#if os(iOS)` is the correct one precisely because it excludes tvOS while `canImport(UIKit)`
  does not.

This means both the new `Haptics.swift` and the edited call site in `NowPlayingView.swift`
would attempt to compile a reference to a symbol that does not exist for a tvOS build,
because the guard that's supposed to exclude non-iOS platforms fails to exclude tvOS.

## Consequence

This is a live framework-idiom defect in the exact dimension under review: the refactor
did not introduce new platform logic, but it *moved and duplicated* the same wrong guard
(now present in two files instead of one) without validating it against the platform matrix
the Actor's own `Package.swift` declares. A single-platform (iOS-only) green suite is
structurally incapable of catching this — per Meta-Rule 4, that is exactly the failure mode
called out: "a tvOS/macOS compile break never runs on an iOS-only test." The Actor's report
treats "1,312 tests green" as sufficient evidence for a `framework_idioms` 9.5, which is the
**fake-clean reward** sub-pattern (aggregate test count standing in for verification at the
actual risk surface) — the green count says nothing about whether `Sources/Soundboard`
still builds for tvOS.

Whether this exact guard predates this loop (the diff shows the same `#if canImport(UIKit)`
wrapping in the "before" state of `NowPlayingView.swift`) does not rescue the score: the
review is against current source, not against loop-over-loop delta, and the loop's own diff
re-touched and duplicated the defective guard while proposing to close out
`framework_idioms` at 9.5 — a dimension whose entire subject matter is correct platform/
framework usage.

By the Architectural Tests: this is also a low-leverage extraction under the Deletion Test —
`Haptics.tap()` has exactly one caller. Deleting the new module and inlining its two lines
back into `NowPlayingView` would not cause complexity to reappear across N callers (N=1).
That alone would only be Cosmetic-for-contest (a minor SPT Q5 leverage question, not
disqualifying on its own), so it is noted but not load-bearing for the verdict — the
platform-guard defect is.

## Remedy

- Change the guard on both `Haptics.swift` and the `NowPlayingView.swift` call site from
  `#if canImport(UIKit)` to `#if os(iOS)` (or an explicit idiom/capability check), which is
  the smallest honest fix and does not touch runtime behavior on iOS/macOS.
- Produce executable evidence for the declared matrix, not reasoning alone: a tvOS build
  (`xcodebuild build … -destination 'platform=tvOS Simulator,name=Apple TV'` or equivalent)
  showing the target compiles clean after the guard fix, plus confirmation macOS still
  compiles (expected to no-op through the `#if`, as before).
- Only after that evidence exists does `framework_idioms` become eligible for re-scoring
  toward 9.5.

## Simplify Pressure Test (on the Actor's proposed fix)

1. Fixes real ambiguity? Partially — it addresses view/helper separation, but not the actual
   platform-guard defect it re-touched.
2. Smallest honest fix? No — a two-file extraction for a single call site, while the correct
   one-line guard fix (`canImport(UIKit)` → `os(iOS)`) wasn't made.
3. Avoids duplicate layers? The guard itself is now duplicated across two files.
4. Runtime/compile behavior honest? No — compile correctness on a declared platform (tvOS)
   is not demonstrated and is very likely broken given `UIImpactFeedbackGenerator`'s known
   unavailability there.
5. Product improvement over what's declined? Not assessable positively while (4) fails.

Net: the proposed fix fails Q2 and Q4. Downgrade from "accept at 9.5" to "reject; fix the
guard and prove the target matrix before re-proposing."

## Verdict

`framework_idioms` does not clear 9.5 this loop. A Serious, source-backed framework/platform
hazard (wrong conditional-compilation directive re-touched and duplicated by this loop,
untested against a declared non-iOS platform) blocks acceptance at the touched dimension.
This is contained to the haptics feature and has a small, well-scoped remedy, so it reads as
a Serious deduction rather than a full disqualifier — but it does block 9.5 as claimed, and
the loop's evidence (iOS-only green suite) cannot certify otherwise.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"framework_idioms": 6.0}, "flagged_smells": ["fake-clean reward", "framework leakage"], "evidence_demanded": ["tvOS build/compile run (e.g. xcodebuild build -destination 'platform=tvOS Simulator,name=Apple TV') for Sources/Soundboard after the guard fix, showing Haptics.swift and NowPlayingView.swift compile clean", "corrected guard: #if os(iOS) (or equivalent capability check) in place of #if canImport(UIKit) in both Haptics.swift and the NowPlayingView.swift call site", "if tvOS build verification is genuinely unavailable, an explicit recorded scope limitation in loop_result per Meta-Rule 4, not silence"]}
```
