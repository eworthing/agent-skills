# Critic Review — Loop 3, `framework_idioms`

## Scope

Single-dimension loop. Actor extracted the haptic-tap side effect out of
`NowPlayingView`'s button action into a new `Haptics` enum in
`Sources/Soundboard/Haptics.swift`, and proposes `framework_idioms` → 9.5 on
the strength of "all green" builds (iOS/macOS/tvOS) plus a full iOS
Simulator test pass (1,312/1,312). Per Method Step 1, the prior report is a
claim to verify against current source, not a verdict to echo.

## Step 1–5 walk

**Architecture shape (Step 3).** No protocol/port is introduced — `Haptics`
is a caseless `enum` used as a static-function namespace, called directly.
The Unified Seam Policy (two-adapter rule / single-adapter policy-failure-
platform test) doesn't apply here because no Seam is being created; this is
a plain extraction, not an abstraction. Nothing in the shown diff reads as
Repository theater, Protocol soup, or a rule-driven sidecar.

**Deletion test (Architectural Tests §1).** The diff shows exactly one call
site rewired (`NowPlayingView`'s play button). At N=1 visible caller,
deleting `Haptics.tap()` and inlining the four lines back costs nothing —
technically a pass-through by the letter of the test. Whether that matters
depends entirely on the finding below: the Actor's own report claims a
**22-line reduction** in `NowPlayingView`, but the diff hunk shown accounts
for a net change of about **4 lines** (5 removed, 1 added) at a single call
site. Either `NowPlayingView` had several more haptic call sites that were
also rewired and simply aren't in the diff excerpt handed to this review, or
the reported magnitude is inflated. I can't resolve this from the attached
diff, so I'm not crediting the Leverage claim (multiple callers converging
on one owner) as proven — nor am I calling it a pass-through. It's
unresolved, and it's material: it's the difference between "well-justified
extraction" and "marginal but harmless stylistic move." Flagging as
`fake-clean reward`-adjacent (a headline number the source doesn't
substantiate) and demanding the full diff before crediting Leverage.

**Framework-idiom shape of the extraction itself, taken at face value.**
Pulling an imperative, platform-gated side effect out of a SwiftUI button
closure and into a named static helper is a legitimate, idiomatic move —
SwiftUI view bodies read better without `#if os(iOS)` branches embedded in
the action closure, and a caseless enum is the standard Swift idiom for a
stateless namespace. The `#if os(iOS)` guard moved with the code intact, so
`Haptics.tap()` correctly compiles to a no-op on macOS/tvOS. This part of
the change is sound and is exactly the kind of thing Meta-Rule 7 wants
rewarded when it's real.

**Cross-platform compile correctness (Step 5, risk-boundary evidence,
Meta-Rule 4) — this is where the loop fails.** `Haptics.swift`'s only import
is:

```swift
import SwiftUI
```

and its body calls `UIImpactFeedbackGenerator`. That type lives in UIKit,
not SwiftUI — `import SwiftUI` does not transitively expose it. Swift
resolves imports per file, not per module, and `Package.swift` shows a
single plain SPM library target with no bridging/umbrella mechanism that
would paper over a missing import. As shown, this file should fail to
compile on iOS with "cannot find type 'UIImpactFeedbackGenerator' in scope."

Two details sharpen this rather than soften it:
- `import SwiftUI` is otherwise unused in this file — nothing else in the
  10-line diff needs it. It reads like a copy-pasted view-file header rather
  than a considered import for what this file actually calls.
- The macOS/tvOS "success" results in the Test run section provide zero
  corroboration either way: `#if os(iOS)` strips `Haptics.tap()`'s body
  entirely on those platforms before the compiler ever needs to resolve
  `UIImpactFeedbackGenerator`, so those two builds would pass regardless of
  whether the import is correct. Only the iOS build result actually bears on
  this, and that's precisely the one line item this finding contradicts.

Per the sandbox framing, the "Test run" block is part of the Actor's own
attestation for this loop, not independently generated ground truth handed
to me separately — so it gets the same scrutiny as the prose report, not a
pass. Given the diff as shown, I do not believe the iOS build can have
succeeded as claimed, which undercuts the loop's central evidentiary basis
for the 9.5 proposal on a risk-boundary change (Meta-Rule 4 specifically
calls out `#if os` conditional-compilation moves as needing trustworthy
compiled evidence).

**Tests (Step 8).** No dedicated test targets `Haptics.tap()` directly, but
haptic feedback is UI-hardware side effect, off any primary domain flow in
the Severity Anchors' own sense ("untested helper code... not
disqualifying") — not a finding by itself, and moot if the compile issue
above is real, since no test in the 1,312-count could have run against code
that doesn't build.

## Verdict

Rejecting the 9.5 proposal for `framework_idioms`. The extraction pattern
itself is sound, but the loop's proof of correctness (an all-green iOS
build) is directly contradicted by the file it just added, and the
headline "22 lines reduced" claim isn't backed by the diff shown. Both are
fixable in the next loop: add `import UIKit` (or the combined import) to
`Haptics.swift` and rerun the iOS build/tests for real, and show the full
diff so the Leverage claim can be checked against the actual call-site
count.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"framework_idioms": 4.5}, "flagged_smells": ["fake-clean reward", "framework leakage"], "evidence_demanded": ["Raw xcodebuild compiler diagnostics (not just the pass/fail summary) for the iOS destination build of Haptics.swift, confirming whether UIImpactFeedbackGenerator resolves under `import SwiftUI` alone or whether the reported iOS build actually failed", "The complete diff for this loop: the shown hunk touches one call site (~4-line net change in NowPlayingView), but the Actor's report claims a 22-line reduction — need every rewired call site to verify the Leverage/deletion-test claim and confirm each one now delegates to Haptics.tap() correctly"]}
```
