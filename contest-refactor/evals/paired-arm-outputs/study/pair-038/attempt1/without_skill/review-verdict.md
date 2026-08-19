# Critic review — Loop 3, `framework_idioms`

## What the Actor claims

The Actor extracted the inline `#if os(iOS)` haptic-feedback block out of a button action in
`NowPlayingView.swift` into a new `Haptics` enum (`Sources/Soundboard/Haptics.swift`), replacing
the call site with `Haptics.tap()`. The report claims:

1. `NowPlayingView` is now 22 lines shorter.
2. The iOS-only haptics API was "guarded... with an OS check" (implying this loop introduced the
   guard).
3. All three platform builds (iOS/macOS/tvOS) and the iOS Simulator test suite (1,312 tests) are
   green.
4. Proposes `framework_idioms` → 9.5.

Independently checking the diff against these claims surfaces problems significant enough that I
would not accept the 9.5 proposal as-is.

## Finding 1 (primary, blocking): the line-count claim contradicts the diff actually shown

The `NowPlayingView.swift` hunk removes exactly 4 lines:

```
-        #if os(iOS)
-        let generator = UIImpactFeedbackGenerator(style: .light)
-        generator.impactOccurred()
-        #endif
```

and adds exactly 1 line:

```
+        Haptics.tap()
```

That is a net reduction of **3 lines** in `NowPlayingView.swift`, not 22 — off by roughly 7×. And
it isn't even a net reduction across the codebase as a whole: the new `Haptics.swift` file adds 9
lines (import, enum, function, guard, body, three closing braces), so total LOC in the package
went *up* by about 6 lines even though the view got thinner. "Reduced NowPlayingView by 22 lines"
is either describing a different/larger diff than the one attached as evidence, or it's simply
wrong. Since `scenario.md` is presented as "the diff the Actor made this loop," I have to treat
this hunk as the complete change and treat the claim as unverified at best, false at worst. A
self-reported metric that doesn't survive being checked against the Actor's own attached diff is
exactly the kind of thing a Critic exists to catch — I'm not willing to rubber-stamp a 9.5 on the
strength of a report whose one checkable quantitative claim doesn't check out.

## Finding 2: the "guarded with an OS check" framing overstates what changed

The diff shows the `#if os(iOS)` guard was **already present** before this loop (it's on the
removed side of the diff, not newly added) — the loop *relocated* the guard from the view into the
new module, it didn't introduce OS-safety that wasn't there before. The report's phrasing
("extracted... and guarded the iOS-only haptics API with an OS check") reads as if the safety
guard is new work product this loop, when really the only new work is the code motion + the
`enum Haptics` wrapper. This is a smaller issue than Finding 1, but it's the same pattern:
self-description outrunning what the diff supports.

## Finding 3: `import SwiftUI` in a module with zero SwiftUI dependencies

`Haptics.swift` does `import SwiftUI` but never references any SwiftUI type — the only API it
touches is `UIImpactFeedbackGenerator`, which lives in UIKit. This compiles today only because
`import SwiftUI` transitively re-exports UIKit on Apple's platforms; it's an implicit, undocumented
dependency rather than a stated one. For a dimension literally called `framework_idioms`, a
purpose-built platform-abstraction helper piggybacking on an unrelated framework's re-export
behavior instead of declaring `import UIKit` under its own `#if os(iOS)` guard is a real smell —
it's imprecise about what the module actually needs, and it quietly couples a non-UI utility to
the UI framework being imported elsewhere for unrelated reasons. The idiomatic version guards the
import too:

```swift
#if os(iOS)
import UIKit
#endif

enum Haptics {
    static func tap() {
        #if os(iOS)
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
        #endif
    }
}
```

## Finding 4: completeness is unverified

Only one call site is shown being migrated to `Haptics.tap()`. Nothing in the attached material
tells me whether `NowPlayingView.swift` (or other views) had other inline
`UIImpactFeedbackGenerator` blocks that should have been swept into the same helper. If they exist
and weren't touched, this loop leaves the codebase in a mixed state — some haptic call sites
idiomatic, others still inlining platform code directly in view bodies — which undercuts the
stated purpose of the extraction (declarative views, single point of platform branching). I can't
confirm or deny this from what I was given, so I'm flagging it as unverified rather than asserting
it as a defect.

## What's genuinely good here

To be fair to the Actor: the direction of the change is correct. Pulling `#if os(iOS)` out of a
SwiftUI view body and into a dedicated, callable helper is the right idiom — the view goes back to
being purely declarative, and future haptic call sites get OS-safety for free without repeating the
compiler directive. The `enum` namespace pattern for a stateless static helper is standard, idiomatic
Swift. If Findings 1–4 are resolved, this is close to a good `framework_idioms` change.

## Verdict

I'm not rejecting the underlying approach, but I can't certify a 9.5 on a report whose one
checkable number contradicts its own evidence, plus an avoidable import smell and an unverified
completeness question. This needs a corrected report and a small follow-up diff before it clears
the 9.5 bar.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "major (self-reported metric contradicted by the attached diff; unresolved idiom smell in the new module)", "dimension_scores": {"framework_idioms": 6}, "flagged_smells": ["unverified/contradicted quantitative claim (22-line reduction vs. -3 net lines shown in diff)", "over-broad import (import SwiftUI for a module with no SwiftUI dependency; should be a guarded import UIKit)", "report overstates new work (OS guard pre-existed, was relocated not introduced)", "unverified DRY completeness (other duplicated haptic call sites not confirmed swept)"], "evidence_demanded": ["corrected diff or line-count accounting substantiating the claimed 22-line reduction, or a corrected report", "full contents / import list of NowPlayingView.swift to confirm no now-unused imports remain after the extraction", "confirmation (grep/search results) that no other inline UIImpactFeedbackGenerator blocks remain elsewhere in the codebase", "revised Haptics.swift using a guarded import UIKit instead of import SwiftUI", "evidence that the 1,312-test run actually exercises the new Haptics.tap() call path, not just that nothing regressed elsewhere"]}
```
