---
name: swiftui-design-tokens
description: >-
  Applies project design tokens for colors, spacing, typography, motion, and
  button styling in SwiftUI on iOS, macOS, and tvOS. Use when adding or
  changing visual styling, defining or extending spring/timed motion tokens,
  choosing reduce-motion alternatives, replacing hardcoded padding, font, or
  color values, picking platform-appropriate button styles, applying macOS
  form styling, or sizing modal frames with tokens. Skip pure animation
  mechanics, backend or data logic, UIKit/AppKit-only layout, and non-Apple
  platforms.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# SwiftUI Design Tokens

## Contents

- Overview
- Load References As Needed
- When to Use
- Do NOT Use For
- Token Architecture
- Palette (Colors)
- Metrics (Spacing)
- TypeScale (Typography)
- Motion (Animation)
- Button Styles
- Applying Tokens (Recipes)
- Diagnostic Recipes
- Auditing for Hardcoded Values
- Sibling Skills (Defer When)
- Exemptions (Not Violations)

## Overview

A well-structured iOS app centralizes visual values into design tokens --
named constants for colors, spacing, typography, and motion. This prevents
hardcoded "magic numbers" scattered across views and ensures visual consistency.

## Load References As Needed

| Topic | Reference |
|-------|-----------|
| Full motion catalog — spring/`lift`/`drop`/`focusSpring`, reduce-motion alternatives, per-interaction selection guide | [references/motion-tokens.md](references/motion-tokens.md) |
| Token-file template — placeholder Palette/Metrics/TypeScale/Motion values to copy into a new project | [references/token-values.md](references/token-values.md) |
| Applied recipes — modal backgrounds/sizing, macOS form styling, reusable `ViewModifier` styles, text hierarchy | [references/application-recipes.md](references/application-recipes.md) |

## When to Use

- Adding new colors or styling to views
- Adjusting spacing or typography
- Implementing button styles
- Fixing hardcoded color or spacing violations
- Setting up a design token system for a new project

## Do NOT Use For

Animation mechanics, platform gating, deprecated-API migration, and tvOS focus
belong to sibling skills — see [Sibling Skills (Defer When)](#sibling-skills-defer-when).
This skill owns only the project's token *vocabulary* and how to apply it.

## Token Architecture

Organize tokens in a dedicated directory (e.g., `Design/`):

| File | Purpose |
|------|---------|
| `DesignTokens.swift` | Palette, Metrics, TypeScale, Motion |
| `Styles.swift` | Reusable view modifier styles (CardStyle, PanelStyle) |
| `Theme.swift` | Theme definitions (if app supports theming) |

See [references/token-values.md](references/token-values.md) for a template
showing how to structure token files with placeholder values.

## Palette (Colors)

### Dynamic Colors

Use semantic color names that adapt to light/dark mode:

```swift
enum Palette {
    static let bg = Color("Background")          // App background
    static let surface = Color("Surface")        // Cards, panels
    static let surfHi = Color("SurfaceHighlight") // Highlighted surface
    static let text = Color("PrimaryText")       // Primary text
    static let textDim = Color("SecondaryText")  // Secondary text
    static let brand = Color("Brand")            // Brand accent
}
```

Define these in an Asset Catalog with light/dark variants, or use
`Color(light:dark:)` initializers.

### Category Colors

When your app has color-coded categories (tiers, tags, labels), centralize
the mapping:

```swift
enum Palette {
    static func categoryColor(_ id: String, from overrides: [String: String]) -> Color {
        // 1. Check user overrides (custom hex)
        if let hex = overrides[id] { return Color(hex: hex) }
        // 2. Check built-in defaults
        if let color = defaultColors[id] { return color }
        // 3. Fallback
        return defaultCategoryColor
    }
}
```

This pattern ensures consistent colors everywhere and makes user
customization straightforward.

## Metrics (Spacing)

Use an 8pt grid system. Define semantic spacing tokens rather than
sprinkling raw numbers:

```swift
enum Metrics {
    static let grid: CGFloat = 8         // 8pt base unit
    static let spacingSM: CGFloat = 16   // grid * 2 — XS/MD/LG/XL follow the grid
    static let rMD: CGFloat = 12         // corner radii: rSM / rMD / rLG
}
```

Full enum (all `spacing*` and `r*` tokens) is in
[references/token-values.md](references/token-values.md). Why an 8pt grid: it
aligns with iOS point sizes, ensures consistent visual rhythm, and makes spacing
decisions mechanical rather than subjective.

## TypeScale (Typography)

Define a type scale with semantic names:

```swift
enum TypeScale {
    static let h1 = Font.system(size: 48, weight: .bold)
    static let body = Font.body
    static let caption = Font.caption   // full scale (h1–h3, bodySmall, footnote) in token-values.md
}
```

Prefer Dynamic Type-compatible fonts (`Font.body`, `.title`, etc.) where
possible so text scales with user accessibility settings.

API reference: [`Font`](https://developer.apple.com/documentation/swiftui/font)
and [`ScaledMetric`](https://developer.apple.com/documentation/swiftui/scaledmetric).

### Font Weight

Prefer `.bold()` over `.fontWeight(.bold)` -- `.bold()` lets the system
choose the correct weight for the current context (e.g., accessibility
bold text setting).

### Dynamic Type Support

When defining custom font sizes, use `@ScaledMetric` to ensure they
scale with user accessibility settings:

```swift
@ScaledMetric(relativeTo: .body) private var customSize: CGFloat = 18
```

## Motion (Animation)

_Last verified: 2026-07-04 (iOS 27 SDK). Availability is tagged per token, not
locked to a global baseline._

### Token Examples

```swift
enum Motion {
    static let fast = Animation.easeOut(duration: 0.12)
    static let standard = Animation.easeOut(duration: 0.20)
    static let spring = Animation.spring(response: 0.30, dampingFraction: 0.8)
}
```

### Reduce Motion

Always provide alternatives when `accessibilityReduceMotion` is true:

```swift
@Environment(\.accessibilityReduceMotion) var reduceMotion

.animation(reduceMotion ? Motion.fast : Motion.spring, value: isExpanded)
```

For the full motion token catalog -- spring tokens (`lift`, `drop`,
platform-branched `focusSpring`), reduce-motion alternatives
(`liftReduced`, `dropReduced`), and the per-interaction selection guide
table -- see [references/motion-tokens.md](references/motion-tokens.md).

See Apple's [HIG Motion guide](https://developer.apple.com/design/human-interface-guidelines/motion)
for platform-level motion principles. The [`Spring` API docs](https://developer.apple.com/documentation/swiftui/spring)
document `response` and `dampingFraction` semantics; for tvOS
[`.bouncy()`](https://developer.apple.com/documentation/SwiftUI/Animation/bouncy(duration:extraBounce:))
see the `Animation` documentation.

## Button Styles

### Context-Based Selection

Choose button styles based on where the button appears, not what it does:

| Context | Primary | Secondary |
|---------|---------|-----------|
| Persistent toolbar | `.borderedProminent` | `.bordered` |
| Modal/sheet content | `.borderedProminent` | `.bordered` |
| Content rows | `.plain` | `.plain` |
| Inline actions | `.borderless` | `.borderless` |

API reference: [`buttonStyle(_:)`](https://developer.apple.com/documentation/swiftui/view/buttonstyle(_:))
and the [`PrimitiveButtonStyle`](https://developer.apple.com/documentation/swiftui/primitivebuttonstyle)
values (`.borderedProminent`, `.bordered`, `.plain`, `.borderless`).

### Tinting

Apply brand tint to bordered buttons for visual consistency:

```swift
Button("Action") { }
    .buttonStyle(.borderedProminent)
    .tint(Palette.brand)
```

## Applying Tokens (Recipes)

Concrete patterns for applying tokens in specific UI contexts — modal
backgrounds (system materials vs. hardcoded opacity), modal sizing, macOS form
styling (`.formStyle(.automatic)` + `.scenePadding()`), reusable `ViewModifier`
styles (`CardStyle`), and text hierarchy — live in
[references/application-recipes.md](references/application-recipes.md). The
Diagnostic Recipes table below indexes the symptoms these recipes address.

## Diagnostic Recipes

When visual issues surface, use this table to identify likely token misuse:

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Inconsistent corner radii across cards | Raw numbers instead of `Metrics.rSM`/`rMD`/`rLG` | Replace with `Metrics.r*` tokens |
| Headings vary in size across screens | Mixing raw `Font.system(size:)` with `TypeScale` | Use only `TypeScale.h1`/`h2`/`h3` |
| Animation feels harsh with accessibility | No reduce-motion gate on spring animations | Add `reduceMotion ? Motion.fast : Motion.spring` ternary |
| Uneven spacing between sections | Raw padding values instead of `Metrics.spacing*` | Switch to semantic spacing tokens |
| Colors don't adapt in dark mode | Hardcoded `Color.white`/`.black` | Use semantic `Palette.*` colors with Asset Catalog variants |
| Button looks wrong for its context | Wrong button style for that UI region | Check Button Styles context table above |
| Modal has missing or excessive padding on macOS | Missing `.scenePadding()` | Add `#if os(macOS)` `.scenePadding()` block |
| Drag animation feels jittery | No `lift`/`drop` token, raw `.spring()` inline | Use `Motion.lift`/`Motion.drop` tokens |
| Focus animation too bouncy on iOS | tvOS `.bouncy()` used without platform branch | Wrap in `#if os(tvOS)` with iOS fallback |
| Text doesn't scale with accessibility settings | Raw `Font.system(size:)` without `@ScaledMetric` | Use `@ScaledMetric` or Dynamic Type fonts |

## Auditing for Hardcoded Values

Run the bundled audit script across a source tree. It flags hardcoded colors,
raw `Font.system(size:)`, and magic padding literals, emits
`DTOKEN-FAIL <category> <file>:<line>`, and exits nonzero on findings
(CI-friendly). Files under a `Design/` directory are skipped as token definitions:

```bash
scripts/audit-hardcoded-tokens.sh YourApp/
```

For quick interactive spot-checks, these ripgrep one-liners cover the color cases:

```bash
rg 'Color\.(black|white|gray|red|blue|green|orange|yellow|pink|purple)\.opacity\(' --glob '*.swift' YourApp/Views/
rg 'Color\((red:|white:|hue:)|Color\(#|UIColor\(' --glob '*.swift' YourApp/Views/
```

Common false positives to ignore:
- Token definition files (`Design/` directory)
- SwiftUI previews
- `Color.clear` layout spacers
- Shadow definitions in style files

## Sibling Skills (Defer When)

This skill owns the project's design-token vocabulary and how to apply it. Defer
the following to their owners:

| Trigger | Skill |
|---------|-------|
| Animation mechanics — implicit vs explicit, transitions, `matchedGeometryEffect`, phase/keyframe animators | `swiftui-animation`, `swiftui-expert-skill` |
| `#if os()` platform gating; "Cannot find X in scope" errors that reproduce on one platform | `apple-multiplatform` |
| tvOS focus behavior; focus-context Liquid Glass regressions | `apple-tvos` |
| Deprecated-API replacement (e.g. `foregroundColor` → `foregroundStyle`) | `swiftui-expert-skill` (`references/latest-apis.md`) |
| Generic Liquid Glass adoption (`glassEffect`, materials) beyond token application | `swiftui-expert-skill` (`references/liquid-glass.md`), `apple-multiplatform` |

## Exemptions (Not Violations)

### User-Selectable Color Presets

Curated color picker options are intentionally hardcoded as presets:

```swift
// Acceptable -- user-selectable preset options
private let colorOptions: [(String, String)] = [
    ("Red", "#FF0037"),
    ("Orange", "#FFA000"),
]
```

### Dynamic Color Computations

RGB channel calculations in color pickers are functional, not design violations:

```swift
// Acceptable -- color picker component logic
var color: Color { Color(red: r / 255, green: g / 255, blue: b / 255) }
```
