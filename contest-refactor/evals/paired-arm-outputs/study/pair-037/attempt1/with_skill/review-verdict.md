# Critic Review — Loop 3, `framework_idioms`

## Scope

The Actor's claim: extracted the inline `#if os(iOS)` haptic-feedback block out of
`NowPlayingView`'s button action into a new `Haptics` enum (`Sources/Soundboard/Haptics.swift`),
called `Haptics.tap()` from the view, reduced `NowPlayingView` by 22 lines, built green on all
three declared platforms (iOS/macOS/tvOS), and ran 1,312 passing iOS Simulator tests. Proposed
score: `framework_idioms` → 9.5.

Per Method Step 1 ("Inspect current code only... require current source proof") this review
re-derives the assessment from the diff itself rather than accepting the Actor's report, and per
the task instructions treats the Actor's `loop_result` as a claim to verify, not a verdict.

## Finding 1 — missing `import UIKit` in the new module (blocks 9.5)

**Claim.** `Haptics.swift` is a brand-new file (`/dev/null` → `Sources/Soundboard/Haptics.swift`);
the diff shows its full contents. It declares only `import SwiftUI`, then inside `#if os(iOS)`
references `UIImpactFeedbackGenerator`, a UIKit type:

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

`import SwiftUI` does not transitively expose UIKit symbols to a file — Swift's import model is
per-file, and SwiftUI does not `@_exported import UIKit`. Any file that names
`UIImpactFeedbackGenerator` (or `UIColor`, `UIApplication`, etc.) directly needs its own
`import UIKit`. This file has none. The prior inline version in `NowPlayingView.swift` may have
compiled only because that file already carried an `import UIKit` elsewhere (not shown in the
hunk); the new file inherits none of that context — imports do not travel with an extracted
symbol.

**Source.** `Sources/Soundboard/Haptics.swift`, full new-file diff, lines 1 (`import SwiftUI`) and
5–6 (`UIImpactFeedbackGenerator(...)`, `.impactOccurred()`), inside the `#if os(iOS)` guard added
at lines 4/7.

**Consequence.** On the `generic/platform=iOS` build — the one destination where the `#if
os(iOS)` body is not preprocessed away — this is a "cannot find type 'UIImpactFeedbackGenerator'
in scope" compile error. That directly contradicts the Actor's own reported evidence:
`xcodebuild build ... destination 'generic/platform=iOS' — success` and the follow-on
`1,312 passed, 0 failed` on the iOS Simulator, since a target that fails to compile cannot run
its test suite at all. On macOS/tvOS the `#if os(iOS)` body is stripped, so those two builds
plausibly do succeed as reported — which is consistent with a scenario where the Actor's build
matrix was not actually exercised end-to-end on iOS, or the reported log does not match this
diff.

This lands squarely on `framework_idioms`: Meta-Rule 4 and Method Step 5's cross-platform
compile-correctness check exist exactly for this shape of change (a refactor that moves code
across a `#if os`-gated boundary). The rule requires the Actor to preserve and *evidence* the
risk-boundary invariant with executable proof; the diff as shown is not self-consistent with the
"green on iOS" evidence offered, which fails that bar rather than meeting it.

**Remedy.** Smallest honest fix: gate the import alongside the code that needs it —

```swift
import SwiftUI
#if os(iOS)
import UIKit
#endif
```

— then re-run the iOS build/test destinations and attach the actual log.

**Severity.** Likely disqualifier. This is a build-breaking defect on the platform the app is
primarily shipped and tested on (1,312-test iOS Simulator suite implies iOS is the primary
surface); if the build doesn't compile, no user flow — haptic or otherwise — is reachable on
iOS at all, which is at least as severe as the anchor's "broken at runtime, reachable from a
primary flow" framing, not less.

## Finding 2 — reported line delta doesn't match the shown diff (credibility, non-blocking on its own)

The Actor's report claims "Reduced `NowPlayingView` by 22 lines." The `NowPlayingView.swift` hunk
shown removes 4 lines (`#if os(iOS)`, the `let generator =`, `generator.impactOccurred()`,
`#endif`) and adds 1 (`Haptics.tap()`) — a net of −3, not −22. This may simply reflect a larger
unshown diff elsewhere in the file, but as presented it's another place the Actor's self-report
doesn't reconcile with the evidence attached to it. Severity: Noticeable weakness on its own
(evidence-chain hygiene) — it reinforces, rather than independently drives, the verdict below.

## Not promoted to a finding

The `Haptics` enum's Interface (`tap()`) is close in size to its Implementation (3 lines), and
only one call site is shown in this diff, which is smoke for a possible shallow-module /
single-caller extraction (deletion test: complexity reappears at N=1 caller shown, not proven
to be N>1). I'm not promoting this — the scope given is only this loop's diff, not the whole
repo, so I can't rule out other `Haptics.tap()` call sites elsewhere that would justify the
Seam under the deletion test. Flagging as a scope-limited/drift-hazard note for the next loop
to check, not a scored finding here.

## Simplify Pressure Test (on the extraction itself)

Design intent passes SPT: it fixes a real (if minor) ambiguity (UIKit ceremony inside a
declarative view body), is a small honest-looking fix, adds no duplicate layers, and doesn't
change intended runtime behavior. It fails on execution, not intent — Q4 ("does runtime
behavior remain honest") is undercut because the code as shipped this loop most likely doesn't
run on iOS at all.

## Verdict determination

Finding 1 is source-backed (full new-file diff, well-established Swift/UIKit import semantics),
directly on the touched dimension, and contradicts the Actor's own "green" evidence rather than
being a stylistic nit. That's a `blocks_95` condition at Likely-disqualifier severity per the
Severity Anchors, so `framework_idioms` cannot be certified at 9.5 this loop. The underlying
directional idea (pull platform-gated UIKit calls out of the view into a small platform-aware
helper) is sound and the fix is a one-line `import UIKit` addition — but as reported, with the
evidence given, this loop does not get accepted.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"framework_idioms": 3}, "flagged_smells": ["Fake-clean reward"], "evidence_demanded": ["Verbatim xcodebuild log for the 'generic/platform=iOS' build (not a bare success/fail summary) showing Haptics.swift compiling cleanly with the UIImpactFeedbackGenerator reference resolved", "Current full contents of Sources/Soundboard/Haptics.swift confirming whether an import UIKit line exists beyond what this diff shows", "Reconciliation of the claimed 22-line reduction in NowPlayingView.swift against the ~3-line net diff shown in this hunk", "Any additional Haptics.tap() call sites elsewhere in the codebase, to support the extraction's leverage claim beyond the single call site shown"]}
```
