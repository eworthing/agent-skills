# Automated Accessibility Auditing (`performAccessibilityAudit`)

## Contents

- Why the Audit
- The One Call
- Where and When to Run It
- Audit Types
- Suppressing Expected Issues
- Per-Platform Relevance
- CI Gating: a Dedicated Audit Class
- Sources

> Reference for the parent `xctest-ui-testing` skill. See the SKILL.md
> *Accessibility Auditing* section for the summary.

## Why the Audit

Most of XCUITest sees **structure, not pixels** — you assert on `frame`,
`isHittable`, `label`, and identifiers. That is exactly why hand-rolled tests
*cannot* catch a low-contrast label or a too-small tap target, and why teams
wrongly conclude those defects are "not mechanically checkable."

`performAccessibilityAudit` is the exception: it runs the same engine as Xcode's
Accessibility Inspector against the **rendered** view and throws (failing the
test) on each issue. Its audit types map one-to-one onto the defect classes that
otherwise slip through — contrast, hit-region size, clipped text, missing
element descriptions. Reach for it *before* writing per-control label/frame
assertions; those are defense-in-depth, not the primary net.

The audit walks the live accessibility tree, so it needs **no** accessibility
identifiers on the screen — it works before you have wired any up.

## The One Call

```swift
@MainActor
func testProfileHasNoAccessibilityRegressions() throws {
    guard #available(iOS 17.0, macOS 14.0, tvOS 17.0, *) else {
        throw XCTSkip("performAccessibilityAudit requires iOS 17 / macOS 14 / tvOS 17")
    }
    let app = XCUIApplication()
    app.launchArguments += ["-uiTest", "-uiTestPresent", "profile"]
    app.launch()

    // Settle first: audit the real screen, never the launch / half-built hierarchy.
    XCTAssertTrue(app.otherElements["Profile_Root"].waitForExistence(timeout: 10))

    try app.performAccessibilityAudit()   // for: .all by default
}
```

Set `continueAfterFailure = true` in `setUp()` when you want one run to surface
*every* issue rather than stopping at the first.

## Where and When to Run It

- **Per screen**, as its own test method — not folded into an interaction flow.
- **After the settle marker** (see SKILL.md *Settle Before Asserting*). Auditing a
  launch screen or mid-transition hierarchy produces noise, not signal.
- Scope the audit types to the screen's real risks (below), or pass `.all`.

## Audit Types

`XCUIAccessibilityAuditType` is an `OptionSet`; combine cases with array literals
(`[.contrast, .hitRegion]`) or use `.all`.

| Case | Checks |
|------|--------|
| `.contrast` | Text / background color contrast ratios |
| `.hitRegion` | Interactive elements meet minimum tap-target size |
| `.sufficientElementDescription` | Elements expose a usable description (catches icon-only buttons) |
| `.textClipped` | Text truncated or clipped rather than shown in full |
| `.dynamicType` | Text supports Dynamic Type scaling |
| `.elementDetection` | Elements are correctly detected as accessibility elements |
| `.trait` | Accessibility traits are assigned correctly |
| `.parentChild` | Parent/child accessibility relationships are valid |
| `.action` | Interactive actions are accessible |
| `.all` | Every audit type (convenience) |

## Suppressing Expected Issues

The optional `issueHandler` closure receives each `XCUIAccessibilityAuditIssue`
and returns a `Bool`:

- Return **`true`** to mark the issue **handled** — it is *suppressed* and does
  not fail the test.
- Return **`false`** (or omit the handler entirely) to let it **fail**.

Suppress only a *specific, triaged, ticketed* issue — never a blanket ignore.
This mirrors the SKILL.md *Retry: Diagnose, Don't Mask* ethos: a suppressed issue
is a tracked exception, not a way to turn the audit green.

```swift
try app.performAccessibilityAudit(for: .all) { issue in
    // Keep first-failure evidence visible.
    let shot = XCTAttachment(screenshot: app.screenshot())
    shot.name = "a11y-\(issue.auditType)"
    shot.lifetime = .keepAlways
    add(shot)

    // Grandfather ONE known, ticketed exception; fail on everything else.
    if issue.auditType == .contrast,
       issue.element?.identifier == "Legal_Disclaimer" {
        return true   // JIRA-1234: brand-mandated low-contrast fine print, tracked
    }
    return false
}
```

`XCUIAccessibilityAuditIssue` exposes `.auditType`, `.element`,
`.compactDescription`, and `.detailedDescription` for matching and logging.

## Per-Platform Relevance

Availability floor: iOS 17+ / iPadOS 17+ / Mac Catalyst 17+ / macOS 14+ /
tvOS 17+ / visionOS 1+ / watchOS 10+ (Xcode 16.3+).

- **iOS / iPadOS / macOS**: all types meaningful.
- **tvOS**: focus-driven and has no touch or UIKit Dynamic Type, so `.hitRegion`
  and `.dynamicType` are largely moot; `.contrast`, `.elementDetection`,
  `.sufficientElementDescription`, and `.trait` still apply. Prefer a scoped
  `[.contrast, .sufficientElementDescription, .elementDetection, .trait]` set
  over `.all` on tvOS to avoid irrelevant failures.

## CI Gating: a Dedicated Audit Class

Group audits into their own test class (e.g. `AccessibilityAuditTests`), the same
way tvOS reachability audits live in `FocusReachabilityAuditTests` (see
[tvos.md](tvos.md)). This lets CI run a fast "accessibility gate" job — one audit
per key screen — separately from long interaction flows, so an a11y regression
fails a focused, obviously-named job.

## Sources

- `XCUIApplication.performAccessibilityAudit(for:_:)` — Apple Developer
  Documentation:
  <https://developer.apple.com/documentation/xctest/xcuiapplication/performaccessibilityaudit(for:_:)>
- `XCUIAccessibilityAuditType` — Apple Developer Documentation:
  <https://developer.apple.com/documentation/xctest/xcuiaccessibilityaudittype>
- WWDC23 — "Perform accessibility audits for your app" (session 10035).
