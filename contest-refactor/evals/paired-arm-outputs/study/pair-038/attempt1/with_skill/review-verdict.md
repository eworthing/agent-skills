# Critic Review — Loop 3, `framework_idioms`

## Scope

Single change this loop: a 5-line UIKit haptic-feedback call is moved out of
`NowPlayingView`'s button action into a new `Haptics.swift` (`enum Haptics { static func tap() }`),
still gated by the pre-existing `#if os(iOS)` conditional. The call site is
updated to `Haptics.tap()`. Actor proposes `framework_idioms` → 9.5 on the
strength of a green multi-platform build plus a green 1,312-test iOS
Simulator run.

## Architectural Tests applied

**Unified Seam Policy.** This is a new Seam (a call boundary moved to its own
type). It does not satisfy the two-adapter path — there is exactly one
caller and one concrete implementation shown, no fake/local-substitutable
counterpart. It does, however, satisfy the single-Adapter path, branch
(b)(iii) — **platform isolation**: `UIImpactFeedbackGenerator` is a
hardware-bound, iOS-only API with no cross-platform equivalent and no test
harness (haptic hardware feedback is not something a unit test can assert
against). On tvOS/macOS the body compiles to an empty stub. That is a
textbook platform-isolation Adapter, not Repository theater or Protocol
soup. The Actor's `loop_result` doesn't name this justification path
explicitly, but the code shape matches it, so I'm not treating "only one
caller" as a friction-proof failure here — (b)(iii) doesn't require N
callers the way the two-adapter path does.

**Shallow module test.** Interface (`Haptics.tap()`) is close to Implementation
(3 lines) — by itself that reads shallow. But depth isn't the right lens for
a platform-isolation Seam; the value is containment of a hardware/OS-gated
call at one Seam, not amortizing complexity across N callers. Not a finding.

**Deletion test.** Deleting `Haptics` and inlining the 5 lines back into
`NowPlayingView` removes no meaningful complexity and re-mixes a UIKit
side-effect into the view body — consistent with, not contradicting, the
Actor's stated rationale ("stays declarative"). No finding.

## Risk-boundary / cross-platform compile correctness (Meta-rule 4)

This change touches `#if os(iOS)`-gated code and moves it across a file
boundary — exactly the risk class method.md flags as needing **executable**
evidence, not reasoning-only, because a single-platform test run can hide a
one-platform compile break. The Actor supplied that evidence directly:
`xcodebuild build` against all three declared destinations in
`Package.swift` (iOS, macOS, tvOS) plus the iOS Simulator test suite, all
green. That is the correct evidence for this risk boundary — no gap here,
and I'm crediting it rather than re-deriving suspicion about the `#if`
guard's correctness.

## Findings

**F1 — Wrong import for the API actually used.**
- *Claim:* `Haptics.swift` imports `SwiftUI` but never references a SwiftUI
  symbol; the only API it calls, `UIImpactFeedbackGenerator`, is UIKit.
- *Source:* `Sources/Soundboard/Haptics.swift` diff — `import SwiftUI` at the
  top, `UIImpactFeedbackGenerator(style: .light)` inside the `#if os(iOS)`
  block, no `import UIKit` anywhere in the shown hunk.
- *Consequence:* on a dimension literally scoped to framework-idiom
  correctness, importing the wrong framework for the dependency actually
  used — and having it work only because SwiftUI happens to carry UIKit
  along on iOS — is exactly the kind of incidental-dependency idiom gap this
  dimension exists to catch. It also means the file's stated dependency
  (SwiftUI) doesn't match its real dependency (UIKit hardware API), which
  will mislead the next person who edits it.
- *Remedy:* `import UIKit` instead of `import SwiftUI` (or in addition to,
  if a future non-iOS branch genuinely needs SwiftUI types — nothing in this
  diff does).

**F2 — Report claims a guard was added; the diff shows it was only moved.**
- *Claim:* `loop_result` says the Actor "guarded the iOS-only haptics API
  with an OS check," which reads as new defensive work.
- *Source:* the removed lines in `NowPlayingView.swift` already contained
  `#if os(iOS) ... #endif` around the identical haptics call, before this
  loop. The diff relocates that guard verbatim into `Haptics.swift`; it adds
  no new conditional-compilation logic.
- *Consequence:* Cosmetic on its own, but per "Honesty beats polish" a
  self-report that overstates what changed should be corrected before being
  used as the basis for a dimension score — the reviewer, not just the
  Actor, is the backstop here.
- *Remedy:* restate as "relocated the existing OS guard," not "guarded ...
  with an OS check."

**F3 — Unreconciled line-count claim.**
- *Claim:* "Reduced `NowPlayingView` by 22 lines."
- *Source:* the only `NowPlayingView.swift` hunk shown removes 5 lines and
  adds 1 (net −4) in the button action.
- *Consequence:* I can't independently confirm 22 lines from the material
  given — the diff excerpt may be partial — but an unreconciled 5.5x gap
  between the claimed and shown delta is exactly the kind of metric claim
  Meta-rule 1 says to trace to source, not accept at face value.
- *Remedy:* Actor supplies the full file diff or diffstat so the claim is
  checkable.

## Severity

All three findings are **Cosmetic for contest** individually under the
rubric's own carve-out — haptic feedback is off-path, presentation-only
code, not a primary user flow, so nothing here approaches "Likely
disqualifier" or "Serious deduction." Taken together, though, they form a
small pattern of *report accuracy* problems (F2, F3) plus one *on-dimension*
correctness nit (F1) sitting directly on the axis being certified. Per the
rubric's own language, that combination is enough to keep this from a clean
9.5 today without being wrong about the underlying architecture — I'm
calling the aggregate a **Noticeable weakness**: it doesn't threaten
contest standing, but it reduces confidence in the report as the basis for
certification, and F1 is a real (if small) framework-idiom miss on the
exact dimension in question.

## Verdict

The structural work is sound — legitimately justified as a platform-isolation
Seam, correctly evidenced across the full build matrix for the risk boundary
it touches. It should not be rejected or unwound. But it also shouldn't be
certified at 9.5 as submitted: fix the import, correct the two report
claims (or supply the diffstat backing them), and it clears cleanly.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Noticeable weakness", "dimension_scores": {"framework_idioms": 9.0}, "flagged_smells": [], "evidence_demanded": ["Haptics.swift corrected to import UIKit (the API it actually calls) instead of/in addition to import SwiftUI", "loop_result language corrected to describe the OS guard as relocated, not newly added", "full NowPlayingView.swift diff or diffstat reconciling the claimed 22-line reduction against the 5-line removal shown"]}
```
