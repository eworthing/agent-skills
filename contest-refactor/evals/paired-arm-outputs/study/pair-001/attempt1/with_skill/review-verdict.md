# Critic Review — Loop 3, `framework_idioms`

## Scope and method

Per Method Step 1, this review re-derives the `framework_idioms` score from the current
source shown in `scenario.md` rather than accepting the Actor's self-report. The Actor's
claim ("Extracted the haptic-feedback helper... proposing `framework_idioms` → 9.5") is
treated as a claim to verify, not a verdict to echo. Inputs available: the diff, the
unchanged `Package.swift`, and the Actor's test-run citation (iOS Simulator only).

## What was cleared

- **Deletion test / shallow-module test on `Haptics.swift`**: the extraction moves a
  4-line UIKit call out of `NowPlayingView` into `enum Haptics { static func tap() }`.
  Interface ≈ Implementation here (one call, one line of body), so on a strict shallow-module
  reading this is borderline — but with a haptics call as an obvious candidate for reuse
  across other playback controls, and given the change is a plain code move (not a new
  protocol/Interface), I do not score this a structural finding. Noted as a **Cosmetic**
  observation only: at a single call site today, the module has not yet demonstrated
  Leverage (N callers > 1). Not blocking.
- **Two-Adapter Rule / Unified Seam Policy**: does not apply. `Haptics` is a concrete
  static-function namespace, not a protocol-based Seam with pluggable Adapters. No seam
  justification is owed here.
- **Cross-file visibility**: the move drops no `private`/`fileprivate` access — the
  generator call was not privacy-scoped in `NowPlayingView`, and `Haptics.tap()` is a plain
  internal API. No regression on that risk boundary.
- **Fake simplification**: the refactor does not hide ownership, failure behavior, or
  async lifetime — `UIImpactFeedbackGenerator.impactOccurred()` is a fire-and-forget call
  before and after the move. No behavior is obscured by the extraction itself.

## Blocking finding

**Claim.** The moved code is guarded by `#if canImport(UIKit)`, but `Package.swift`
declares three platforms: `.iOS(.v17), .macOS(.v14), .tvOS(.v17)`. `canImport(UIKit)`
evaluates **true** on tvOS — tvOS's UI framework is UIKit, not AppKit — but
`UIImpactFeedbackGenerator` (and the `UIFeedbackGenerator` family generally) is not part
of tvOS's UIKit surface; it is an iOS/iPadOS/Mac Catalyst-only API. `canImport` proves the
*module* imports, not that every *symbol* in it is available on the importing platform.
The correct idiom for this specific gate is `#if os(iOS)` (or, if broader UIKit access on
tvOS is intentionally wanted elsewhere, `#if canImport(UIKit) && !os(tvOS)` scoped to the
haptics call). This is exactly the pattern Method Step 5's Cross-platform compile
correctness check and Meta-Rule 4's "risk boundary: conditional compilation (`#if os` /
`canImport`)" clause exist to catch.

**Source.**
- `Package.swift`: `platforms: [.iOS(.v17), .macOS(.v14), .tvOS(.v17)]` — tvOS is a
  declared, in-scope target for this single-target package (no per-platform target split
  is shown), so this file is compiled into the tvOS build.
- `Sources/Soundboard/Haptics.swift` (new this loop): `#if canImport(UIKit) ... enum
  Haptics { static func tap() { let generator = UIImpactFeedbackGenerator(style: .light);
  generator.impactOccurred() } } #endif` — the diff hunk carries no line numbers, so this
  is cited by file + symbol + hunk rather than `file:line`; scope-limited on that basis,
  but the code itself is unambiguous.
- `Sources/Soundboard/NowPlayingView.swift`: the `Button` action calling
  `Haptics.tap()` inside the same `#if canImport(UIKit)` guard is the play button on the
  Now Playing screen — a primary user flow for a soundboard/playback app, not off-path
  helper code.
- **Test evidence gap**: the Actor's only cited run is `xcodebuild test -scheme Soundboard
  -destination 'platform=iOS Simulator,name=iPhone 15'`. No macOS or tvOS build/test
  evidence is cited anywhere in the report. Per Meta-Rule 4, a refactor that crosses a
  conditional-compilation risk boundary must record compile evidence for the affected
  target matrix, or explicitly record why that evidence is unavailable. Neither is present.

**Consequence.** If this reasoning holds, the tvOS target fails to *compile* — not a
runtime bug contained to one code path, but a build break on one of three platforms this
package declares support for. That is a stronger failure than most of the Severity
Anchors' own "broken at runtime" examples, since it never reaches runtime at all. It is
also directly reachable from a primary user flow (the play button), satisfying the second
half of the Likely-disqualifier anchor. It also means the Actor's "iOS Simulator suite
green, 1,312 tests" citation cannot, by itself, support a `framework_idioms` claim at 9.5
for a change that spans three declared platforms — single-config green is exactly the
"counts are not quality" / metrics-support-not-decide trap named in Meta-Rules 1–2.

**Remedy.** Smallest behavior-preserving fix: narrow the guard around the
`UIImpactFeedbackGenerator` call specifically to iOS (`#if os(iOS)`), leaving
`canImport(UIKit)` guards elsewhere (if any) untouched, then produce an executable tvOS
build (and ideally macOS build, for completeness against the declared platform list) as
the risk-boundary evidence Meta-Rule 4 requires.

I hold this to high but not certain confidence — I cannot execute a build from inside this
sandbox, and my knowledge of the exact `UIFeedbackGenerator` platform-availability table
is training-derived, not queried live. That uncertainty is exactly why this is an
evidence-demanded item rather than a silently-assumed rejection: the required artifact
(a tvOS compile) is cheap, mechanical, and would settle the claim either way.

## Non-blocking note

The Actor reports "Reduced `NowPlayingView` by 22 lines," but the attached diff hunk shows
only a few lines changed in that file (the inline generator call replaced by a single
`Haptics.tap()` line under the same guard). This may simply be because `scenario.md`
elides unrelated hunks — I cannot confirm or refute the claim from what's attached, so I
am not treating it as a finding, only flagging it as unverifiable from the given evidence
and adding it to the evidence I'd want before fully trusting the Actor's report.

## Verdict rationale

This is a pre-existing guard shape (the removed inline code used the identical
`#if canImport(UIKit)` gate), so the underlying platform-availability risk did not
originate this loop. But the Actor is asking this loop's review to certify
`framework_idioms` at 9.5 on the strength of *this* code, this loop touched and relocated
the exact conditional-compiled call the cross-platform check exists for, and did so
without producing (or even attempting) compile evidence for two of the package's three
declared platforms. Under Step 1's "inspect current code only" rule and Meta-Rule 4, that
is not certifiable at 9.5 as submitted. The fix is small and the extraction's overall
shape is otherwise sound, but I cannot pass the dimension without the platform guard being
corrected and the risk-boundary evidence Meta-Rule 4 requires.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"framework_idioms": 3}, "flagged_smells": ["cross-platform compile correctness violation — #if canImport(UIKit) guard around UIImpactFeedbackGenerator is true-but-wrong on tvOS, a declared Package.swift platform"], "evidence_demanded": ["tvOS build evidence for the Soundboard target (e.g. xcodebuild build -scheme Soundboard -destination 'platform=tvOS Simulator,name=Apple TV') proving Haptics.swift does or does not compile on tvOS", "macOS build evidence for the same target for completeness against the declared platform list", "if the tvOS build fails: a corrected guard (e.g. #if os(iOS)) re-verified by a passing tvOS build", "the full NowPlayingView.swift diff to confirm the Actor's reported '-22 lines' claim, unverifiable from the attached hunk alone"]}
```
