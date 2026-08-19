# Review: Loop 3 — `framework_idioms` (Haptics extraction)

## Scope

Reviewing only what `scenario.md` gives me: the Actor's diff (new `Sources/Soundboard/Haptics.swift`, edited `Sources/Soundboard/NowPlayingView.swift`), the attached `Package.swift`, and the Actor's own report/test citation. Applying `architecture-rubric.md` and `method.md` against that source rather than the Actor's narrative.

## Finding 1 — Cross-platform compile correctness unverified for a `#if`-gated move (Serious deduction)

**Claim:** The refactor relocates `#if canImport(UIKit)`-gated code (construction of a `UIImpactFeedbackGenerator`) out of `NowPlayingView.swift` into a new file, `Haptics.swift`, under the same guard, and rewrites the call site to also live inside a fresh `#if canImport(UIKit)` block. `method.md` Step 5 ("Cross-platform compile correctness") and Meta-rule 4 both require that a refactor which "moves/splits files or touches `#if`-gated code" confirm it still compiles across the *declared* target matrix — a single-platform test run does not prove that.

**Source:** The attached `Package.swift` declares `platforms: [.iOS(.v17), .macOS(.v14), .tvOS(.v17)]` — three targets, one library target, no per-platform exclusion. The Actor's only cited verification is `xcodebuild test -scheme Soundboard -destination 'platform=iOS Simulator,name=iPhone 15'` — iOS only. No macOS or tvOS build evidence appears anywhere in the report.

**Consequence:** `canImport(UIKit)` is true on iOS **and tvOS** (tvOS ships UIKit for its view-controller stack), but `UIImpactFeedbackGenerator` is an iOS/Mac Catalyst haptics API with no tvOS counterpart — Apple TV hardware has no haptic engine. That gap predates this loop, but this loop is precisely the one that touched and relocated the `#if`-gated block, which is the named trigger condition for demanding target-matrix evidence, not just an iOS test run. Nothing in the report shows the tvOS or macOS target was attempted after the move. Citing "1,312 tests, 0 failed" as blanket proof for a change whose entire payload is new conditional-compilation surface is the aggregate-test-count-as-proof pattern the rubric flags under **fake-clean reward** — the passing count says nothing about the two platforms it didn't run on.

**Remedy:** Require build (not test) evidence for the macOS and tvOS targets — e.g. `xcodebuild build -scheme Soundboard -destination 'generic/platform=tvOS'` and the macOS equivalent — before crediting the loop. If `UIImpactFeedbackGenerator` is confirmed unavailable on tvOS, the guard needs tightening (e.g. `#if os(iOS)` or `#if canImport(UIKit) && !os(tvOS)`), or, per Meta-rule 4's reasoning-only carve-out, the limitation must at minimum be recorded — neither exists today.

## Finding 2 — Actor's stated line-delta is not supported by the diff shown (Noticeable weakness)

**Claim:** The Actor reports "Reduced `NowPlayingView` by 22 lines." The diff hunk shown for `NowPlayingView.swift` removes 4 lines (`#if canImport(UIKit)` / `let generator = ...` / `generator.impactOccurred()` / `#endif`) and adds 3 (`#if canImport(UIKit)` / `Haptics.tap()` / `#endif`) — a net change of **-1 line**, not -22.

**Source:** `scenario.md` diff for `Sources/Soundboard/NowPlayingView.swift`.

**Consequence:** Per Meta-rule 6 ("Honesty beats polish") and the instruction to independently assess rather than echo the Actor's report, a self-reported magnitude the attached diff doesn't back up is exactly what this review is supposed to catch. Either "22 lines" references changes not included in this diff — in which case the diff I was given is incomplete and the loop's real footprint is unverified — or the figure is simply wrong.

**Remedy:** Demand the full diffstat for the loop before crediting the stated reduction; treat "22 lines" as unverified in the meantime.

## What I cleared

- The extraction itself — a one-call-site `Haptics.tap()` static helper — is a thin seam by the two-adapter rule (only one production Adapter, no test fake), but it plausibly clears the **Unified Seam Policy**'s single-Adapter path (b)(iii): platform/hardware isolation. Haptics generators are a hardware-bound API with no meaningful test harness, the same category the policy names for SDKs like Spotify's. I'm not flagging this as protocol soup or an architecture-costume layer — a real justification path exists even though the Actor's report doesn't cite it explicitly (a process gap, not a structural one).
- "The view stays declarative" is a mild overclaim — the call site still carries a bare `#if canImport(UIKit)` block inside the button closure — but it's a wording nit, not a finding on its own.

## Verdict

Finding 1 is source-backed, maps directly to a named method.md check (cross-platform compile correctness) that this loop's own diff triggers, and has zero evidence offered against it — that blocks certifying `framework_idioms` at 9.5 as written. Finding 2 compounds it as a credibility gap. Neither requires unwinding the extraction itself; both require evidence the Actor didn't provide. This is conditional, not a rejection of the approach.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"framework_idioms": 7.5}, "flagged_smells": ["fake-clean reward"], "evidence_demanded": ["xcodebuild build evidence for the macOS target (Package.swift declares .macOS(.v14))", "xcodebuild build evidence for the tvOS target (Package.swift declares .tvOS(.v17)), or a tightened guard (e.g. #if os(iOS)) if UIImpactFeedbackGenerator is confirmed unavailable on tvOS", "full diffstat reconciling the claimed '22 lines' reduction in NowPlayingView.swift against the -1 net line shown in the hunk"]}
```
