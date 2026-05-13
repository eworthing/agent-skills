---
name: swiftui-design-tokens
author: eworthing
description: >-
  Applies project design tokens for colors, spacing, typography, motion, and
  button styling in SwiftUI on iOS, macOS, and tvOS. Use when adding or
  changing visual styling, defining or extending spring/timed motion tokens,
  choosing reduce-motion alternatives, replacing hardcoded padding, font, or
  color values, picking platform-appropriate button styles, applying macOS
  form styling, or sizing modal frames with tokens.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Design System Patterns

## Overview

A well-structured iOS app centralizes visual values into design tokens --
named constants for colors, spacing, typography, and motion. This prevents
hardcoded "magic numbers" scattered across views and ensures visual consistency.

## When to Use

- Adding new colors or styling to views
- Adjusting spacing or typography
- Implementing button styles
- Fixing hardcoded color or spacing violations
- Setting up a design token system for a new project

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
    static let grid: CGFloat = 8         // Base unit
    static let spacingXS: CGFloat = 8    // grid * 1
    static let spacingSm: CGFloat = 16   // grid * 2
    static let spacingMd: CGFloat = 24   // grid * 3
    static let spacingLg: CGFloat = 32   // grid * 4
    static let spacingXL: CGFloat = 40   // grid * 5

    static let rSm: CGFloat = 8         // Small corner radius
    static let rMd: CGFloat = 12        // Medium corner radius
    static let rLg: CGFloat = 16        // Large corner radius
}
```

Why an 8pt grid: it aligns with iOS point sizes, ensures consistent
visual rhythm, and makes spacing decisions mechanical rather than subjective.

## TypeScale (Typography)

Define a type scale with semantic names:

```swift
enum TypeScale {
    static let h1 = Font.system(size: 48, weight: .bold)
    static let h2 = Font.system(size: 34, weight: .bold)
    static let h3 = Font.system(size: 22, weight: .semibold)
    static let body = Font.body
    static let bodySmall = Font.subheadline
    static let caption = Font.caption
    static let footnote = Font.footnote
}
```

Prefer Dynamic Type-compatible fonts (`Font.body`, `.title`, etc.) where
possible so text scales with user accessibility settings.

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

## Button Styles

### Context-Based Selection

Choose button styles based on where the button appears, not what it does:

| Context | Primary | Secondary |
|---------|---------|-----------|
| Persistent toolbar | `.borderedProminent` | `.bordered` |
| Modal/sheet content | `.borderedProminent` | `.bordered` |
| Content rows | `.plain` | `.plain` |
| Inline actions | `.borderless` | `.borderless` |

### Tinting

Apply brand tint to bordered buttons for visual consistency:

```swift
Button("Action") { }
    .buttonStyle(.borderedProminent)
    .tint(Palette.brand)
```

## Modal Backgrounds

Use system materials for modal/overlay backgrounds instead of hardcoded
opacity values. Materials adapt to light/dark mode and accessibility settings:

```swift
// Preferred
ZStack {
    Color.clear
        .background(.regularMaterial)
        .ignoresSafeArea()
    ModalContent()
}

// Avoid -- hardcoded opacity doesn't adapt
ZStack {
    Color.black.opacity(0.6)
        .ignoresSafeArea()
    ModalContent()
}
```

## Form Styling (macOS)

Let SwiftUI pick the platform-default form style instead of forcing a
specific look. `.formStyle(.automatic)` tracks Apple's current design
direction (currently column-style on macOS) and adapts as the platform
evolves:

```swift
Form {
    Section("Appearance") { /* ... */ }
}
#if os(macOS)
.formStyle(.automatic)
.scenePadding()
#endif
```

`.scenePadding()` produces the recommended spacing around the root view
of a macOS window. Apple's Settings documentation pairs `.automatic` with
`.scenePadding()` for the same reason -- both adapt to platform context
automatically.

Avoid hardcoding `.formStyle(.grouped)` unless you specifically want the
iOS-style grouped look on macOS.

## Modal Sizing

Use sizing tokens for modal frames instead of magic numbers. Define a
namespace such as `ScaledDimensions` (or extend `Metrics`) so window sizes
stay consistent and adapt to Dynamic Type or accessibility scaling:

```swift
enum ScaledDimensions {
    static let modalWidth: CGFloat = 1200
    static let modalHeight: CGFloat = 860
}

// Use the token
.frame(maxWidth: ScaledDimensions.modalWidth,
       maxHeight: ScaledDimensions.modalHeight)

// Avoid -- magic numbers, drift across modals
.frame(maxWidth: 1200, maxHeight: 860)
```

If you need different sizes per platform, branch inside the token
definition rather than at every callsite.

## View Modifiers

Create reusable modifiers for common patterns:

```swift
struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(Metrics.spacingMd)
            .background(Palette.surface)
            .clipShape(.rect(cornerRadius: Metrics.rLg))
    }
}

extension View {
    func card() -> some View { modifier(CardStyle()) }
}
```

## Common Patterns

### Text Hierarchy

```swift
VStack(alignment: .leading) {
    Text("Title")
        .font(TypeScale.h3)
        .foregroundStyle(Palette.text)
    Text("Subtitle")
        .font(TypeScale.bodySmall)
        .foregroundStyle(Palette.textDim)
}
```

### Spacing

```swift
VStack(spacing: Metrics.spacingSm) {
    // 16pt spacing between items
}
.padding(Metrics.spacingMd)  // 24pt padding
```

## Auditing for Hardcoded Values

Find hardcoded colors in view files:

```bash
rg 'Color\.(black|white|gray|red|blue|green|orange|yellow|pink|purple)\.opacity\(' --glob '*.swift' YourApp/Views/
rg 'Color\((red:|white:|hue:)|Color\(#|UIColor\(' --glob '*.swift' YourApp/Views/
```

Common false positives to ignore:
- Token definition files (`Design/` directory)
- SwiftUI previews
- `Color.clear` layout spacers
- Shadow definitions in style files

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

See the `swiftui-deprecated-apis` skill for deprecated API replacements (e.g., `foregroundColor` -> `foregroundStyle`).
