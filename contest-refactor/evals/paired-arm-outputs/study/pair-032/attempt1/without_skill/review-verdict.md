# Independent review — Loop 3, `framework_idioms` dimension

## What the diff actually does

The Actor extracted the haptic-feedback call out of `NowPlayingView.swift` into a new
file, `Sources/Soundboard/Haptics.swift`, containing:

```swift
#if canImport(UIKit)
import UIKit

enum Haptics {
    static func tap() {
        let generator = UIImpactFeedbackGenerator(style: .light)
        generator.impactOccurred()
    }
}
#endif
```

and replaced the inline call site in `NowPlayingView.swift` with `Haptics.tap()`, still
wrapped in the same `#if canImport(UIKit)` guard. That much is a reasonable, idiomatic
Swift pattern on its own — a stateless namespace `enum` for a small platform helper is a
common and accepted idiom, and pulling incidental platform-conditional code out of a view
body is a legitimate readability win.

The problem is what the extraction did *not* fix, and what the report claims that the
diff does not support.

## Finding 1 (blocking): the platform guard is wrong for a package that ships tvOS

`Package.swift` (given, unchanged this loop) declares three platforms:

```swift
platforms: [.iOS(.v17), .macOS(.v14), .tvOS(.v17)],
```

`canImport(UIKit)` evaluates **true on tvOS**, not just iOS — tvOS's UI layer is built on
a variant of UIKit, so `import UIKit` is legal there. But `UIImpactFeedbackGenerator` (and
the other `UIFeedbackGenerator` subclasses) are documented as iOS/Mac-Catalyst-only APIs;
there is no haptic engine on Apple TV hardware and the type is not present in the tvOS
SDK. That means `#if canImport(UIKit)` is the wrong granularity of guard for this specific
API — the idiomatic guard for an iOS-only symbol is `#if os(iOS)`, reserving
`canImport(UIKit)` for "does this platform have UIKit at all" checks (e.g. excluding
Linux/Windows or, historically, watchOS).

Critically, this is **not a new bug the Actor introduced** — the removed lines show the
exact same `#if canImport(UIKit)` guard was already around the inline
`UIImpactFeedbackGenerator` call before this loop. But the loop under review is explicitly
scoped to the `framework_idioms` dimension, and the Actor is asking for `framework_idioms
→ 9.5` on the strength of this exact change. Moving a platform-availability bug into its
own file, unchanged, is not evidence that framework idioms were fixed — it's evidence the
underlying idiom problem was carried forward untouched, in the one loop whose job was to
address exactly that class of issue. Whether or not this loop introduced it, it cannot
be the basis for a 9.5 in *this* dimension.

## Finding 2: "tests green" doesn't cover two of the three declared platforms

The cited test run is `xcodebuild test -scheme Soundboard -destination 'platform=iOS
Simulator,name=iPhone 15'` — iOS only. Given `Package.swift` declares macOS and tvOS as
supported platforms, and given this change specifically touches platform-conditional
compilation (`#if canImport(UIKit)`), an iOS-only test run is not sufficient evidence that
the change builds cleanly across the package's declared platform matrix. It's exactly the
kind of change where a tvOS-only compile failure (per Finding 1) would be invisible to the
cited test command and still ship green.

## Finding 3: the report's own numbers don't reconcile with the diff shown

The Actor's report claims "Reduced `NowPlayingView` by 22 lines." The diff shown for
`NowPlayingView.swift` removes 4 lines and adds 3, a net change of **-1 line**, not -22.
Even counting the new `Haptics.swift` file (12 added lines), the change is a net
*increase* in total source lines, not a reduction. This may be because the diff excerpt
given here is abbreviated (the `@@` hunk headers carry no line-range data, so I can't
confirm this is the complete diff), but as presented, the report's headline metric is not
supported by the evidence attached to it. A review that just accepted the Actor's stated
delta without checking the diff would have missed this.

## Finding 4 (minor): "its own Haptics module" overstates the change

`Package.swift` defines a single target (`Soundboard`). The diff adds a new *file* and a
new *type* within that same target — not a new Swift module/product. Calling it "its own
module" overstates the boundary that was actually introduced. Minor on its own, but it's
part of a pattern in this report (see Finding 3) of describing the change in stronger
terms than the diff supports.

## Verdict rationale

The extraction itself (pulling a small platform helper into a namespaced enum) is a
reasonable shape and I'm not asking for it to be reverted. But the loop is scored on
`framework_idioms`, and the one framework-idiom issue actually present in the touched code
— gating an iOS-only API behind `canImport(UIKit)` instead of `os(iOS)`, in a package that
explicitly ships tvOS — was carried forward unchanged, and the test evidence offered
wouldn't catch it if it does break the tvOS build. Combined with a headline metric (line
count) that doesn't reconcile against the attached diff, I can't sign off on `9.5` for
this dimension from what's here. This is fixable with a small, mechanical change
(`#if os(iOS)` in both files, or explicit platform-scoping of the call site) plus real
evidence the other two declared platforms still build — hence "conditional" rather than a
flat rejection of the extraction itself.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "critical — plausible compile break on a declared target platform (tvOS), gated by the wrong conditional-compilation directive for an iOS-only API",
  "dimension_scores": {"framework_idioms": 5},
  "flagged_smells": [
    "wrong platform guard: #if canImport(UIKit) used to gate UIImpactFeedbackGenerator, an iOS-only API, in a package that also targets tvOS (which also imports UIKit)",
    "test-evidence/platform-matrix mismatch: iOS-only xcodebuild run cited as blanket 'tests green' for a package declaring iOS+macOS+tvOS",
    "report metric does not reconcile with diff: claimed 22-line reduction vs. a shown net change of -1 line (view file) / net increase overall",
    "module-boundary overclaim: 'own Haptics module' when Package.swift has a single target — this is a new file/type, not a new module"
  ],
  "evidence_demanded": [
    "a tvOS build (or test) log showing Haptics.swift and its NowPlayingView.swift call site compile cleanly under the tvOS SDK, or a corrected guard (#if os(iOS)) with that build re-run",
    "a macOS build log for the same files, to confirm no regression there either",
    "a corrected line-count accounting for the claimed 22-line reduction against the actual diff hunks, or the full untruncated diff (the given hunks carry no @@ line-range data so completeness can't be confirmed)"
  ]
}
```
