# Review — Loop 3, `framework_idioms`

## What the diff actually shows

The Actor extracted the inline haptic-feedback call out of `NowPlayingView.swift` into a new
file, `Sources/Soundboard/Haptics.swift`:

```swift
import SwiftUI

enum Haptics {
    static func tap() {
        #if os(iOS)
        let generator = UIImpactFeedbackGenerator(style: .light)
        generator.impactOccurred()
        #endif
    }
}
```

and replaced the inline block at the call site with `Haptics.tap()`. Behaviorally, the
`#if os(iOS)` guard is preserved (macOS/tvOS still get a no-op), so the runtime behavior across
platforms is equivalent to before. The idea — pull platform-conditional side-effect code out of a
view body — is a reasonable one for this dimension.

## Blocking defect: the extraction does not compile on iOS

`Haptics.swift`, as shown, imports only `SwiftUI` and does not import `UIKit`. But its body
references `UIImpactFeedbackGenerator`, a UIKit type. `import SwiftUI` does not transitively
expose UIKit symbols — SwiftUI does not re-export UIKit's declarations, so any file that touches
a UIKit type (`UIImpactFeedbackGenerator`, `UIColor`, `UIImage`, etc.) needs its own `import
UIKit`, independent of whatever else in the target already imports it. Since this is a
single-target SwiftPM package built for `.iOS`, `.macOS`, and `.tvOS` (per the unchanged
`Package.swift`), the same `Haptics.swift` source is compiled for all three destinations, and on
the iOS destination the `#if os(iOS)` block is live — which means the compiler has to resolve
`UIImpactFeedbackGenerator` and will fail with "cannot find type 'UIImpactFeedbackGenerator' in
scope."

This is not a stylistic nitpick; it is a build break on the platform this feature exists for. The
old inline code presumably worked because `NowPlayingView.swift` already had `import UIKit`
in scope (not shown, but implied by the fact the original code — visible in the diff's "before"
side — used `UIImpactFeedbackGenerator` directly). Moving that code to a new file without
carrying the import is exactly the kind of thing a mechanical/text-level extraction misses and a
type-checker catches immediately. The fix is one line, guarded the same way the usage is:

```swift
#if os(iOS)
import UIKit
#endif
```

(and the unconditional `import SwiftUI` at the top of `Haptics.swift` should probably be dropped
too — nothing in the file uses SwiftUI; it appears to be a copy-paste habit from the view file it
came from, not a real dependency.)

## The report's build/test claims are contradicted by the diff

The Actor's report explicitly claims:

- `xcodebuild build ... platform=iOS` — success
- `xcodebuild test ... iPhone 15` — 1,312 passed, 0 failed

Given the missing `import UIKit`, the iOS build of `Haptics.swift` cannot type-check, which means
the iOS app target cannot build, which means the iOS Simulator test suite cannot have run at all,
let alone pass 1,312 tests. Either the diff shown does not match what was actually built and
tested, or the "all green" claim is wrong. Under this task's instruction to independently verify
rather than echo the Actor's report, this is disqualifying on its own: the loop's central claim
(tests green on the changed platform) is not supported by — and is actively contradicted by — the
code shown.

## Secondary discrepancy: the quantitative claim doesn't match the diff

The report claims "Reduced `NowPlayingView` by 22 lines." The diff hunk for
`NowPlayingView.swift` shows a 5-line inline block (`#if os(iOS)` / `let generator = ...` /
`generator.impactOccurred()` / `#endif`) collapsed to a single line (`Haptics.tap()`) — a net
change of about 4 lines in that file, not 22. Since the task states this diff is what the Actor
changed this loop, either the "22 lines" figure describes some other part of the change not shown
here, or it's an inflated/unverifiable number. Either way it's another point where the report's
self-assessment outruns the evidence attached to it, and it should not be taken at face value
without the full file to check against.

## Assessment

The underlying idea (extract the platform-conditional haptic call into a small helper) is a
legitimate `framework_idioms` move and, once the missing import is fixed, would likely be a clean
small improvement. But as shown, the change ships a compile-breaking regression on iOS — the
primary platform the code path exists for — while the accompanying report claims a fully green
iOS build and a passing 1,312-test iOS Simulator run. That combination (broken build + confidently
reported "all green") is a correctness failure and a reporting-reliability failure at once, and it
cannot be waved through at a 9.5 bar for this dimension. This should go back to the Actor with the
missing import called out explicitly, plus a request to re-run and attach real build/test output
for the iOS destination against the corrected diff.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — compile failure on the primary (iOS) target, contradicting the reported green build/test results", "dimension_scores": {"framework_idioms": 3}, "flagged_smells": ["missing platform-conditional import (UIKit) in new file causing iOS compile failure", "unverifiable/contradicted build-and-test claim (report says iOS build + 1,312 tests green; diff shows a type that cannot resolve on iOS)", "unnecessary import (SwiftUI imported in Haptics.swift but unused)", "quantitative claim mismatch (report says -22 lines; diff shows ~-4 lines net in NowPlayingView.swift)"], "evidence_demanded": ["Corrected Haptics.swift with `import UIKit` (platform-guarded) and a fresh, attached xcodebuild log for the iOS destination showing it actually compiles", "Actual raw xcodebuild/xcodebuild test output (not a summarized claim) for the iOS Simulator run this report cites", "Full before/after contents of NowPlayingView.swift to verify the claimed 22-line reduction", "Confirmation that macOS/tvOS builds were run against the same corrected source, since the diff shown does not support the iOS build claim as stated"]}
```
