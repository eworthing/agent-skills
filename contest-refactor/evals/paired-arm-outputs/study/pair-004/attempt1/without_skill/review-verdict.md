# Critic review — Loop 3, `framework_idioms`

## What the diff actually does

The Actor moved a 4-line inline haptic call out of `NowPlayingView.swift` into a new
`Sources/Soundboard/Haptics.swift`, replacing the inline body with a call to
`Haptics.tap()`. Both the old and new code wrap the haptic call in
`#if canImport(UIKit) ... #endif`. The call site inside the view is otherwise unchanged.

## Findings

**1. The platform guard was carried over unfixed, and the report overstates what was done.**
The Actor's report says: *"guarded the platform-specific bit with a conditional import."*
That guard — `#if canImport(UIKit)` — already existed in the code before this loop; it was not
added or corrected here, it was copy-pasted into the new file. More importantly, it is the
*wrong* guard for this API. `Package.swift` declares three platforms: `.iOS(.v17)`, `.macOS(.v14)`,
and `.tvOS(.v17)`. tvOS also `canImport(UIKit)` (tvOS apps are built on UIKit), but
`UIImpactFeedbackGenerator` and the rest of the `UIFeedbackGenerator` family are documented as
iOS/iPadOS/Mac Catalyst only — they do not exist on tvOS. So `Haptics.swift` as written will fail
to compile on the tvOS target that this same package declares. This bug predates this loop, but
this loop is specifically graded on `framework_idioms` (correct, idiomatic platform-conditional
code), and it both (a) claims credit for "guarding" platform-specific code without actually fixing
the guard, and (b) takes a bug that was previously confined to one inline call site and promotes
it into a shared module, which is more likely to get reused/trusted as-is by future callers on
other platforms.

**2. The only test evidence given is iOS-only, on a package that declares three platforms.**
The test command run is `xcodebuild test -scheme Soundboard -destination 'platform=iOS
Simulator,name=iPhone 15'`. Nothing here builds or tests the tvOS or macOS targets that
`Package.swift` declares as supported. "1,312 passed, 0 failed" tells us nothing about whether
`Haptics.swift` even compiles on tvOS — and per finding 1, there's good reason to think it
doesn't. A green iOS suite is being used to imply the platform-conditional work is safe across
the package's full platform matrix; it isn't evidence of that.

**3. The Actor's line-count claim doesn't match the diff.**
The report claims *"Reduced `NowPlayingView` by 22 lines."* The diff shown for
`NowPlayingView.swift` replaces a 4-line block (`#if` / `let generator = ...` /
`generator.impactOccurred()` / `#endif`) with a 3-line block (`#if` / `Haptics.tap()` /
`#endif`) — a net reduction of 1 line in that file, not 22, and the change is offset by a
brand-new 10-ish-line file (`Haptics.swift`), so total lines in the package went up, not down.
Unless there's a large unshown portion of the diff, this specific, checkable quantitative claim
in the Actor's report is false. That's independent of the platform-guard issue and on its own is
reason not to take the rest of the report's characterization at face value.

**4. The extraction itself is minor.**
Pulling a single 2-line body used at exactly one call site into its own file/module is a
plausible cleanup, but it's a thin justification for a `framework_idioms` win on its own — there's
no second call site shown, no protocol/testability benefit demonstrated, and no indication this
was blocking anything. Not blocking by itself, but it doesn't carry much weight toward 9.5 either.

## Verdict rationale

Findings 1 and 2 are a real correctness gap on a platform this package explicitly supports,
misdescribed as "guarded" work product of this loop — that's a `framework_idioms`-dimension
defect, not a tangential one. Finding 3 is a factual discrepancy between the Actor's report and
the diff evidence provided. Together these are enough to block acceptance at 9.5 and to reject
this loop's report as-is rather than accept it conditionally on a quick patch, since the report's
own accounting can't currently be trusted without corroborating evidence.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": null, "dimension_scores": {"framework_idioms": 3.5}, "flagged_smells": ["incorrect platform-availability guard: #if canImport(UIKit) is treated as iOS-only, but tvOS also imports UIKit and lacks UIImpactFeedbackGenerator", "multi-platform target unverified: Package.swift declares tvOS and macOS but only iOS Simulator tests were run", "actor report vs diff mismatch: claimed -22 lines in NowPlayingView.swift, diff shows a net -1 line in that file plus a wholly new file added", "trivial single-call-site extraction promoted to a shared module with no demonstrated reuse"], "evidence_demanded": ["a tvOS build log (e.g. xcodebuild build -destination 'platform=tvOS Simulator,name=Apple TV') proving Haptics.swift compiles, or a corrected guard such as #if os(iOS) before re-claiming the platform work is done", "a macOS build log confirming the no-op degradation under #if canImport(UIKit) on macOS is intentional", "a reconciled line-count / full diff accounting for the claimed -22 lines in NowPlayingView.swift", "justification for extracting Haptics into its own module absent a second call site"]}
```
