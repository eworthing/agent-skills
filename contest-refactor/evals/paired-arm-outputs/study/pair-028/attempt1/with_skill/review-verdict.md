# Critic Review — Loop 3, `framework_idioms`

## What the Actor claims vs. what the diff shows

The Actor's report claims two things: (1) `NowPlayingView` was reduced by 22 lines, and (2) tests
are green (1,312 passed on iOS Simulator), justifying `framework_idioms → 9.5`. Per the task
framing, the Actor's report is not itself evidence — the diff is. Checking the diff against the
claim:

- `NowPlayingView.swift`'s hunk removes 2 lines (`let generator = ...`, `generator.impactOccurred()`)
  and adds 1 line (`Haptics.tap()`), inside the existing, unchanged `#if canImport(UIKit)` /
  `#endif` guard. That is a net **-1 line** change in the file shown, not -22. Either the "22
  lines" figure describes work not present in the submitted diff, or it is simply wrong. Per the
  Evidence Chain, a quantitative claim not backed by the attached source is not usable as scoring
  support, and an inflated improvement figure feeding a 9.5 proposal is exactly the shape of
  **Fake-clean reward** (scoring up on a claim source doesn't corroborate). This alone doesn't
  disqualify the loop, but it must be reconciled before the report's numbers are trusted for
  anything else.

## Architecture review — the `Haptics` seam

`Haptics` is a new one-method enum (`static func tap()`) with a single call site shown
(`NowPlayingView`'s play button). Applying the Two-Adapter Rule / Unified Seam Policy: there is
one Adapter (the UIKit implementation) and no behavior-faithful test fake, so path (a) fails. It
can still be justified under path (b)(iii) — platform isolation — since haptic feedback is a
hardware-bound API with no meaningful test harness, which is a defensible read. Deletion test: at
one call site the extraction currently returns no cross-call Leverage; it earns its keep only on
the platform-isolation argument, not on reuse. This is a **Noticeable weakness at most**, not
blocking — pulling a UIKit-specific call out of a declarative SwiftUI view body is a legitimate
`framework_idioms` move in direction, it just isn't "deep" yet (Interface ≈ Implementation — 2
lines of body, no params). Not a costume layer: it doesn't fake control it doesn't have, it's just
thin.

## The blocking finding — unverified cross-platform compile correctness

This is the substantive issue. `Package.swift` (unchanged this loop) declares three platforms:
`.iOS(.v17), .macOS(.v14), .tvOS(.v17)`, all built from the single `Soundboard` target. The
diff's only test evidence is:

> `xcodebuild test -scheme Soundboard -destination 'platform=iOS Simulator,name=iPhone 15'` — 1,312 passed

That is a single-platform (iOS Simulator) run. The change itself is precisely the trigger case the
method calls out: it moves `#if canImport(UIKit)`-gated code into a new file
(`Sources/Soundboard/Haptics.swift`), which is conditional-compilation territory — one of the
named risk boundaries ("actor/isolation, Sendable/thread-safety, conditional compilation (`#if os`
/ `canImport`), cross-file visibility ... lock/ordering"). The method is explicit that a
single-config green run does not prove preservation across this boundary: "a tvOS/macOS compile
break never runs on an iOS-only test," and when a fix crosses a risk boundary the Actor "must
preserve that invariant and record evidence in `loop_result`," preferring "executable evidence
(compile the affected target matrix ...)," with reasoning-only accepted "just when the invariant
is not mechanically testable ... and that limitation is recorded."

None of that happened here. The `loop_result` contains no macOS or tvOS build/compile evidence,
and no reasoning-only note explaining why that's unnecessary or unavailable. `canImport(UIKit)`
is true on both iOS and tvOS (tvOS's UI layer is built on UIKit), so `Haptics.swift`'s guarded body
— including `UIImpactFeedbackGenerator` — is compiled into the tvOS target, not skipped by the
guard the way it is on macOS. Whether `UIImpactFeedbackGenerator` is actually available in the
tvOS UIKit module is exactly the kind of platform-API-surface question the guard as written
(`canImport(UIKit)`, not a narrower iOS-specific check) does not settle, and it is unverified by
anything in this loop's evidence. I'm not asserting the tvOS build is broken — I don't have a
tvOS compile log, and the guard's logic is unchanged from what already shipped before this loop
(this loop moved the block, it did not author the platform condition). But the loop is claiming a
9.5 on `framework_idioms` — the dimension whose whole subject is idiomatic, correct platform API
usage — while a required piece of risk-boundary evidence for exactly that dimension is absent.
That gap is source-backed (Package.swift's platform list vs. the single-destination test command;
the moved `#if canImport` block), so it is a finding, not idle nagging: the Actor needs to build
(not just unit-test) the macOS and tvOS destinations, or supply the reasoning-only equivalent.

Severity: contained to one platform-conditional helper, not spread across the codebase, and the
Haptics extraction didn't change the guard condition — so this is a **Serious deduction**, not a
Likely disqualifier. A reasonable judge could still rank the loop's direction well; the entry just
can't be certified at 9.5 on `framework_idioms` on this evidence.

## Verdict

Conditional. The `Haptics` extraction is a reasonable, minor `framework_idioms` improvement, but
two things must be resolved before the dimension is certified at 9.5: the missing cross-platform
compile evidence for the risk boundary this loop touched, and the unreconciled line-count claim
in the Actor's report. Neither requires reverting the change; both require evidence the Actor
hasn't supplied.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"framework_idioms": 8.0}, "flagged_smells": ["Fake-clean reward"], "evidence_demanded": ["Executable build evidence for the macOS and tvOS destinations (e.g. xcodebuild build -scheme Soundboard -destination 'generic/platform=macOS' and the tvOS equivalent, or swift build for those triples) proving Haptics.swift's #if canImport(UIKit) block still compiles across the full Package.swift platform matrix (iOS, macOS, tvOS) -- the iOS Simulator test run alone does not cover this risk boundary", "A corrected diff or full before/after line count for NowPlayingView.swift reconciling the claimed 22-line reduction against the ~1-line net change shown in the submitted diff"]}
```
