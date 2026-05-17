# Generation Output Format

Use this reference when generating SwiftUI code.

## Core Principle

Generated SwiftUI should be native, small, state-honest, previewable, and maintainable.

Do not only make it compile. Make it fit the platform.

## Required Generation Steps

Before code, state:

1. Platform target.
2. Task topology.
3. Native container choice.
4. State coverage.
5. iPhone behavior.
6. iPad behavior when relevant.
7. Accessibility risks.
8. Anti-web-smell checks.

Then generate code.

## Default Code Assumptions

For new iOS 26 / iPadOS 26 code, prefer:

- SwiftUI
- Observation
- `@Observable`
- `@Bindable`
- `@Environment`
- semantic typography
- semantic colors
- SF Symbols
- native containers
- localized user-facing strings
- small composable views
- previews for risky states

Allow legacy APIs only when the project already uses them:

- `ObservableObject`
- `@Published`
- `@StateObject`
- `@ObservedObject`
- `@EnvironmentObject`

Do not introduce Combine-era observation into fresh SwiftUI code without a stated compatibility reason.

## Persistence

Prefer SwiftData for simple local Apple-platform persistence only when it fits the project.

Do not override an existing persistence architecture.

Respect existing:

- Core Data
- SQLite
- GRDB
- files
- CloudKit
- repositories
- domain adapters
- app architecture boundaries

UI should not know persistence details unless the project pattern allows it.

## View Size

Keep views small.

Prefer:

- screen view
- section subviews
- row subviews
- empty/loading/error subviews
- style modifiers
- preview fixtures

Reject:

- giant single `body`
- deeply nested `VStack` and `ZStack`
- all states inline in one huge view
- formatting logic in body
- side effects in body

## State Placement

State should live at the lowest honest scope.

Use:

- `@State` for local view-only state
- `@Binding` for parent-owned value state
- `@Bindable` for editable observable model state
- `@Observable` for screen or flow state
- `@Environment` for system values
- domain/app state according to project architecture

Reject:

- global singletons mutated by views
- view models that own unrelated app state
- navigation state hidden in leaf rows
- async mutation in `View.body`

## Centralized Style Architecture

Do not scatter literal style decisions.

Prefer:

- semantic ViewModifiers
- style structs
- named spacing constants
- project tokens where they exist
- extensions for repeated patterns

Example:

```swift
private enum AppSpacing {
    static let small: CGFloat = 8
    static let medium: CGFloat = 12
    static let large: CGFloat = 16
}

private struct SecondaryDetailStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.subheadline)
            .foregroundStyle(.secondary)
    }
}

private extension View {
    func secondaryDetailStyle() -> some View {
        modifier(SecondaryDetailStyle())
    }
}
```

Reject:

- `.foregroundStyle(.gray)` everywhere
- `.padding(15)` scattered through views
- hard-coded colors in every row
- Tailwind utility-class thinking

## Localization

All user-facing strings should be localization-ready.

Prefer:

- `LocalizedStringResource` for stored labels where appropriate
- string literals only where project convention allows automatic extraction
- no hard-coded concatenated sentences
- formatting APIs for dates/numbers/units

Reject:

- fixed-width buttons
- hard-coded English-only copy in reusable models
- string concatenation with variables where grammar can change

## Accessibility In Generated Code

Every generated screen should include:

- labels for icon-only buttons
- semantic text styles
- no color-only meaning
- Dynamic Type resilience
- Reduce Motion consideration when custom animation exists
- Reduce Transparency consideration when material/glass exists
- touch targets large enough

## Preview Matrix

For generated reusable screens, include previews when practical:

- compact width
- regular width
- dark mode
- large Dynamic Type
- Reduce Transparency

For small leaf views, provide enough previews to cover layout risk.

Example:

```swift
#Preview("Compact") {
    ExampleScreen()
}

#Preview("Dark") {
    ExampleScreen()
        .preferredColorScheme(.dark)
}

#Preview("Large Type") {
    ExampleScreen()
        .environment(\.dynamicTypeSize, .accessibility3)
}
```

Use project conventions if previews are already standardized.

## State Fixtures

Preview important states:

- empty
- loading
- content
- error
- permission/offline when relevant

Do not preview only the happy path.

## Generated Output Template

Use this shape:

```md
## Native Structure

Chosen container and why.

## State Coverage

States covered.

## Accessibility Notes

Risks and mitigations.

## SwiftUI Code

\`\`\`swift
...
\`\`\`

## Preview Notes

Preview variants included or recommended.

## Self-Review

Rubric summary and anti-web-smell check.
```

## Do Not Generate

Reject by default:

- custom navigation bars
- custom tab bars
- Material FAB
- hero sections inside app screens
- dashboard grid iPhone home
- thin glass text
- hard-coded tiny font sizes
- arbitrary Tailwind paddings
- networking inside body
- persistence mutation inside body
- unlabeled image buttons
