# Review — Loop 3, `framework_idioms`

## What the diff does

The Actor pulled the haptic-tap logic out of `NowPlayingView`'s button action and into a new
`Haptics.swift` file: a `#if canImport(UIKit)`-gated `enum Haptics` with a single static `tap()`
method that wraps `UIImpactFeedbackGenerator`. The call site now reads `Haptics.tap()` inside the
same `#if canImport(UIKit)` guard it had before. Mechanically this is a reasonable, idiomatic
extraction — a static-namespace enum for a stateless platform helper is a normal Swift pattern,
and the guard shape at the call site is preserved rather than silently dropped.

That said, two things in the materials given don't hold up, and both bear directly on the
dimension being scored.

## Finding 1 — the guard is the wrong proxy for platform availability (blocking)

`Package.swift` declares three target platforms for the single `Soundboard` library target:
`.iOS(.v17)`, `.macOS(.v14)`, `.tvOS(.v17)`. There's no per-platform target split, so every file
in `Sources/Soundboard/`, including the new `Haptics.swift`, must compile for all three.

`#if canImport(UIKit)` is true on iOS *and* tvOS (tvOS ships UIKit) — it is not an "iOS-only"
check, even though it's being used as one here. `UIImpactFeedbackGenerator` (and its sibling
feedback-generator classes) are iOS/Mac-Catalyst APIs; tvOS devices have no Taptic Engine and the
type is not available there. So on a tvOS build, `canImport(UIKit)` evaluates true, the guarded
branch compiles, and it references a type that doesn't exist on that platform — a build break for
one of the three platforms this package declares support for.

This exact guard already existed in the pre-refactor `NowPlayingView` code, so the loop didn't
introduce the bug — but it also didn't fix it, and the refactor was the natural point to notice
it (the code moved through the Actor's hands specifically for this reason). More importantly, the
only verification cited is `xcodebuild test -scheme Soundboard -destination 'platform=iOS
Simulator,name=iPhone 15'`. That's iOS only. Nothing in the report shows the macOS or tvOS build
was ever exercised, so "tests green" doesn't actually cover two of the three platforms
`Package.swift` claims to support. For a `framework_idioms` score, "does the platform-conditional
code use the right idiom for the API it's gating" is the dimension itself — `#if os(iOS)` (or an
`@available`/runtime check) would be the correct guard here, not `canImport(UIKit)`.

I'm not able to prove the tvOS build actually fails — I only have this diff and the Package
manifest, not a compiler — but the mismatch between the declared platform list, the gating
mechanism used, and the single-platform test run is a real, checkable gap, not a stylistic
nitpick.

## Finding 2 — reported impact doesn't match the diff shown

The Actor reports "Reduced `NowPlayingView` by 22 lines." The diff hunk against
`NowPlayingView.swift` shown here removes 4 lines and adds 3, for a net change of −1 line in that
file. Nothing else in the materials shows additional deletions from `NowPlayingView`. Either the
report is describing changes not represented in the diff I was given, or the "22 lines" figure is
simply wrong. Since the instructions are to assess the refactor independently rather than take the
Actor's report at face value, I'm flagging this as unverified rather than accepting it — a
9.5-caliber loop report shouldn't have a headline metric that the accompanying diff doesn't
support.

## Minor, non-blocking

Splitting a single three-line static method into its own file for one call site is a small
abstraction for not much payoff yet (no second caller shown). Not a rejection reason on its own —
"keep the view declarative" is a defensible rationale — but it's the kind of thing that only pays
for itself once a second call site shows up.

## Verdict reasoning

The extraction itself is clean, idiomatic Swift and doesn't regress anything visible. But the
dimension under review is `framework_idioms`, and the change carries forward (without fixing or
even flagging) a platform-availability guard that's wrong for one of the package's three declared
platforms, backed by a test run that only covers one of those three platforms. Combined with an
unsubstantiated line-count claim in the report, this isn't a 9.5-grade close-out yet. It's also not
a full rejection of the extraction pattern — the fix is narrow (swap the guard, or add a tvOS
build/test pass) rather than a redo.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "blocking — build-availability guard (`canImport(UIKit)`) is a false proxy for iOS-only API on a package that also targets tvOS (which imports UIKit but lacks UIImpactFeedbackGenerator); only iOS Simulator was tested", "dimension_scores": {"framework_idioms": 5}, "flagged_smells": ["canImport(UIKit) used as an iOS-only availability proxy when the package also declares tvOS", "test coverage (iOS Simulator only) doesn't match Package.swift's declared iOS/macOS/tvOS platform list", "actor report claims a 22-line reduction in NowPlayingView not supported by the diff shown (diff shows net -1 line)", "single-call-site extraction into a new file with no second consumer yet (minor)"], "evidence_demanded": ["a tvOS build/test run for the Soundboard scheme (or equivalent compiler evidence) proving Haptics.swift and its call site build clean on tvOS", "a macOS build run given Package.swift also declares .macOS(.v14)", "either the full diff or a reconciled line count supporting the claimed 22-line reduction in NowPlayingView.swift", "justification for canImport(UIKit) over #if os(iOS) / an availability check, or a fix swapping to the correct guard"]}
```
