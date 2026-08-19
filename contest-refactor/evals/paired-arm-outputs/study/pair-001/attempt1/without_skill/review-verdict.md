## Review — Loop 3, `framework_idioms`

**What changed.** The Actor pulled the inline haptic-feedback call out of the play button's
action closure in `NowPlayingView.swift` into a new `Haptics.swift` file: a `#if canImport(UIKit)`-gated
`enum Haptics` with a single `static func tap()` that wraps `UIImpactFeedbackGenerator`. The call site
now reads `Haptics.tap()` instead of constructing the generator inline, still wrapped in its own
`#if canImport(UIKit)` guard. The Actor reports a 22-line reduction in `NowPlayingView`, 1,312 passing
tests on iOS Simulator, and proposes `framework_idioms → 9.5`.

I'm reviewing only `scenario.md` (per the sandbox constraints for this task), so everything below is
checked against what that file actually shows — diff and `Package.swift` — not against the report's
narration of it.

**1. The reported line-count doesn't match the diff shown.** The Actor claims "Reduced `NowPlayingView`
by 22 lines." The diff hunk for `NowPlayingView.swift` shown in `scenario.md` removes 4 lines
(`#if canImport(UIKit)` / `let generator = ...` / `generator.impactOccurred()` / `#endif`) and adds 3
(`#if canImport(UIKit)` / `Haptics.tap()` / `#endif`) — a net change of **-1 line**, not -22. Either the
diff shown is incomplete (in which case it isn't sufficient evidence for the claim it's attached to), or
the report's quantitative claim is simply wrong. Either way, this is the one thing in the report I can
directly check against the provided evidence, and it fails the check. That's reason enough not to take
the rest of the report ("tests green," "1,312 tests") on faith.

**2. The extraction doesn't achieve the stated goal.** The Actor frames this as "so the view stays
declarative." But the call site in `NowPlayingView.swift` still carries the exact same
`#if canImport(UIKit) ... #endif` platform conditional directly inside the button's action closure —
only the three lines *inside* the guard changed. The view is not more declarative than before; the
platform-conditional compilation still leaks into SwiftUI view code verbatim. If the point of a `Haptics`
abstraction is to hide platform concerns from call sites, the module should expose an unconditionally
callable `Haptics.tap()` (with a no-op branch for platforms without UIKit), so `NowPlayingView` needs no
`#if` at all. As shipped, this is a rename/relocation of three lines, not an idiom improvement.

**3. The platform guard being preserved is itself wrong, and this package declares the platform it's
wrong for.** `Package.swift` declares `platforms: [.iOS(.v17), .macOS(.v14), .tvOS(.v17)]`. tvOS's UIKit
is importable (`canImport(UIKit)` is `true` on tvOS — it's tvOS's primary UI framework), but
`UIImpactFeedbackGenerator` is not available on tvOS (Apple's documented availability for
`UIFeedbackGenerator`/`UIImpactFeedbackGenerator` is iOS, iPadOS, Mac Catalyst, visionOS — not tvOS,
which has no Taptic-style feedback-generator API). Gating this call on `canImport(UIKit)` alone is a
classic misuse of that check as an iOS-only proxy; it isn't. That means `Haptics.swift`, as written, is a
real tvOS build-failure risk against a platform this package explicitly ships.

This exact guard already existed inline before this loop, so the defect predates the diff and wasn't
introduced by the Actor. But `framework_idioms` is precisely the dimension that should catch "gate this
API on the platform it's actually available on, not on an adjacent-but-different availability check," and
a loop that creates a dedicated `Haptics` module — whose entire job is to own this platform distinction —
and copies the same wrong guard into it, rather than correcting it, is not evidence of idiomatic mastery.
It's a missed opportunity dressed as a fix.

**4. The test evidence doesn't cover the platforms in play.** The cited run is
`xcodebuild test -scheme Soundboard -destination 'platform=iOS Simulator,name=iPhone 15'` — iOS only.
`Package.swift` declares macOS and tvOS as supported platforms too. For a change that touches a
platform-availability conditional specifically, "iOS tests are green" says nothing about whether the
tvOS (or macOS) target even compiles. At minimum a build (not necessarily full test pass) on the other
two declared platforms should accompany a `framework_idioms` claim that touches conditional compilation.

**Net assessment.** The extraction is small and directionally reasonable on iOS, and I have no evidence
it broke iOS behavior. But: the quantitative claim in the report is contradicted by the diff provided: the
refactor doesn't deliver the declarativeness it claims to; and it re-homes, without fixing, a
platform-availability guard that's very plausibly wrong for a platform this package ships, unverified by
any build/test evidence for that platform. That combination is enough to block acceptance of
`framework_idioms` at 9.5 this loop. This isn't a "redo everything" rejection — it's specific and fixable
— so I'm marking it conditional rather than outright rejected.

Note on `blocking_severity`: I only have `scenario.md` for this task and no access to this project's own
rubric/severity taxonomy, so I'm not going to invent a canon-specific anchor name. I've used a generic
label below and described the substance above instead.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "major", "dimension_scores": {"framework_idioms": 5}, "flagged_smells": ["report-diff mismatch (claimed 22-line reduction vs. -1 net line in shown diff)", "cosmetic extraction (call site still carries the platform conditional; no declarativeness gained)", "incorrect platform-availability gate (canImport(UIKit) used as iOS-only proxy but true on tvOS, which lacks UIImpactFeedbackGenerator)", "test coverage narrower than declared platform surface (iOS-only run against an iOS/macOS/tvOS package)"], "evidence_demanded": ["the full, unredacted diff for this loop so the claimed 22-line NowPlayingView reduction can be verified against actual content", "a tvOS build (or test) log for the Soundboard scheme, since Package.swift declares .tvOS(.v17) and this change touches a UIKit-availability conditional", "a macOS build/test log, or confirmation that Haptics is never reachable from macOS-targeted code paths", "either a corrected guard (e.g. excluding tvOS, or an explicit os(iOS) check) with rationale, or a no-op fallback inside Haptics.swift so call sites no longer need to repeat #if canImport(UIKit)"]}
```
