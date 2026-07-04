# Design Token Values Template

This template shows how to structure a design token reference file for your app.
Replace placeholder values with your actual design system values.

## Contents

- Color Palette
  - Semantic Colors
  - Category Colors (if applicable)
- Metrics (Spacing Values)
- TypeScale (Typography)
- Modal Sizing
- Motion Tokens

---

## Color Palette

### Semantic Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `bg` | `#FFFFFF` | `#000000` | App background |
| `surface` | `#F2F2F7` | `#1C1C1E` | Cards, panels |
| `surfHi` | `#E5E5EA` | `#2C2C2E` | Highlighted surface |
| `text` | `#000000` | `#FFFFFF` | Primary text |
| `textDim` | `#3C3C43` | `#EBEBF5` | Secondary text (with opacity) |
| `brand` | `#007AFF` | `#0A84FF` | Brand accent |

### Category Colors (if applicable)

| Category | Hex | Color |
|----------|-----|-------|
| Category A | `#E11D48` | Rose |
| Category B | `#F59E0B` | Amber |
| Category C | `#22C55E` | Green |
| Category D | `#06B6D4` | Cyan |
| Default | `#6B7280` | Gray |

---

## Metrics (Spacing Values)

```swift
enum Metrics {
    static let grid: CGFloat = 8         // Base unit (8pt grid)
    static let rSM: CGFloat = 8          // Small corner radius
    static let rMD: CGFloat = 12         // Medium corner radius
    static let rLG: CGFloat = 16         // Large corner radius

    // Semantic spacing
    static let spacingXS: CGFloat = 8    // grid * 1
    static let spacingSM: CGFloat = 16   // grid * 2
    static let spacingMD: CGFloat = 24   // grid * 3
    static let spacingLG: CGFloat = 32   // grid * 4
    static let spacingXL: CGFloat = 40   // grid * 5

    // Component-specific
    static let cardPadding: CGFloat = 24
    static let sectionSpacing: CGFloat = 32
}
```

---

## TypeScale (Typography)

```swift
enum TypeScale {
    static let h1 = Font.system(size: 48, weight: .bold)      // Hero
    static let h2 = Font.system(size: 34, weight: .bold)      // Large title
    static let h3 = Font.system(size: 22, weight: .semibold)  // Section title
    static let body = Font.body                                 // Body text
    static let bodySmall = Font.subheadline                    // Secondary body
    static let caption = Font.caption                           // Captions
    static let footnote = Font.footnote                         // Footnotes
}
```

Use Dynamic Type-compatible fonts where possible so text scales with
accessibility settings.

---

## Modal Sizing

For iPad, consider using `ScaledDimensions` tokens for modal frames:

Values below are illustrative — size them to your own layouts, and branch inside
the token definition if a platform needs different dimensions.

```swift
enum ScaledDimensions {
    static let modalWidth: CGFloat = 600
    static let modalHeight: CGFloat = 500
    static let largeModalWidth: CGFloat = 800
    static let largeModalHeight: CGFloat = 650
}

// Usage
.frame(maxWidth: ScaledDimensions.modalWidth, maxHeight: ScaledDimensions.modalHeight)

// Avoid magic numbers
// .frame(maxWidth: 600, maxHeight: 500)
```

---

## Motion Tokens

This is a minimal starter set. The full motion catalog — spring tokens
(`lift`, `drop`, platform-branched `focusSpring`), dedicated reduce-motion
alternatives (`liftReduced`, `dropReduced`), and the per-interaction selection
guide — lives in [motion-tokens.md](motion-tokens.md). Reduce-motion columns
never use a spring.

```swift
enum Motion {
    static let fast = Animation.easeOut(duration: 0.12)
    static let standard = Animation.easeOut(duration: 0.20)
    static let spring = Animation.spring(response: 0.30, dampingFraction: 0.8)
}
```

| Interaction | Normal | Reduce Motion |
|-------------|--------|---------------|
| Overlay appear | `spring` | `fast` |
| Content transition | `standard` | `fast` |
| Drag interaction | `spring` | `standard` |
