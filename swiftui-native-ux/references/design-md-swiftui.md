# DESIGN.md for SwiftUI-Native Apps

Google Stitch and AI design tools may use DESIGN.md to represent design tokens and design guidance. For SwiftUI, DESIGN.md must be treated as visual guidance, not architecture.

When project-specific design tokens already exist, defer to the `swiftui-design-tokens` sibling skill before extending DESIGN.md. This file describes the generic shape; project tokens override it.

## Recommended Files

Use one or both:

```
DESIGN.md
DESIGN-swiftui.md
```

- `DESIGN.md` may hold broad design-system tokens.
- `DESIGN-swiftui.md` should hold Apple-native interpretation rules.

## Token Categories

Recommended token categories:

- semantic colors
- typography roles
- spacing scale
- corner radius scale
- materials
- shadows
- icon style
- motion
- accessibility fallbacks
- platform container rules

## Color Rules

Prefer semantic roles over raw visual names.

Examples:

```yaml
colors:
  accent:
    value: systemBlue
    swiftui: Color.accentColor
    use: Primary actions and selection state
  backgroundPrimary:
    value: systemBackground
    swiftui: Color(.systemBackground)
    use: Root screen background
  backgroundGrouped:
    value: secondarySystemGroupedBackground
    swiftui: Color(.secondarySystemGroupedBackground)
    use: Grouped forms and inset sections
  textPrimary:
    value: label
    swiftui: Color(.label)
    use: Essential text
  textSecondary:
    value: secondaryLabel
    swiftui: Color(.secondaryLabel)
    use: Supporting text only
```

Avoid:

- fixed low-contrast gray for essential text
- brand colors as the only semantic signal
- gradient backgrounds behind dense text
- transparent text surfaces

## Typography Rules

Map typography to Dynamic Type roles.

```yaml
typography:
  largeTitle:
    swiftui: .largeTitle
    use: Screen-level title only
  title2:
    swiftui: .title2
    use: Section-level emphasis
  headline:
    swiftui: .headline
    use: Row title or primary item label
  body:
    swiftui: .body
    use: Main readable content
  subheadline:
    swiftui: .subheadline
    use: Supporting row text
  footnote:
    swiftui: .footnote
    use: Metadata only
```

Do not encode typography as fixed pixels.

## Spacing Rules

Use an 8-point rhythm unless a native component dictates otherwise.

```yaml
spacing:
  xs: 4
  sm: 8
  md: 16
  lg: 24
  xl: 32
```

## Radius Rules

Prefer native continuous rounded corners.

```yaml
radius:
  rowGroup: 10
  card: 16
  prominentControl: 18
```

Do not make every element a rounded card.

## Material Rules

```yaml
materials:
  navigation:
    allowed: true
    use: navigation bars, tab bars, toolbars
  contentCard:
    allowed: false
    reason: Content surfaces must remain readable and opaque
  denseText:
    allowed: false
    reason: Transparency harms readability
```

## SwiftUI Translation Rules

Translate DESIGN.md tokens into SwiftUI extensions or theme helpers.

Do not:

- create a giant global style object that fights SwiftUI
- override native controls unnecessarily
- create custom tab bars
- create custom navigation bars
- bake fixed sizes that break Dynamic Type

## Required Accessibility Fallbacks

Document:

- Reduce Transparency fallback
- Increase Contrast behavior
- Dark mode colors
- Dynamic Type expansion behavior
- VoiceOver order assumptions
- Differentiate Without Color alternatives

See `references/accessibility.md` for the canonical SwiftUI accessibility checklist.
