# Applying Tokens — Recipes

How to apply design tokens in specific UI contexts. The SKILL.md body covers the
token *system* and the Diagnostic Recipes lookup table; these are the concrete
application patterns it points to.

## Contents

- Modal Backgrounds
- Form Styling (macOS)
- Modal Sizing
- View Modifiers
- Text Hierarchy

## Modal Backgrounds

Use system materials for modal/overlay backgrounds instead of hardcoded opacity
values. Materials adapt to light/dark mode and accessibility settings:

```swift
// CORRECT
ZStack {
    Color.clear
        .background(.regularMaterial)
        .ignoresSafeArea()
    ModalContent()
}

// WRONG -- hardcoded opacity doesn't adapt
ZStack {
    Color.black.opacity(0.6)
        .ignoresSafeArea()
    ModalContent()
}
```

On the iOS 27 SDK, Liquid Glass is the system default for many surfaces (the
`UIDesignRequiresCompatibility` opt-out is ignored), but `.regularMaterial`
remains correct for a modal backdrop. Glass *adoption* itself (`glassEffect`,
material hierarchy) is owned by `swiftui-expert-skill` (`references/liquid-glass.md`)
and `apple-multiplatform` — this skill only covers applying it via tokens.

## Form Styling (macOS)

Let SwiftUI pick the platform-default form style instead of forcing a specific
look. `.formStyle(.automatic)` tracks Apple's current design direction (currently
column-style on macOS) and adapts as the platform evolves:

```swift
Form {
    Section("Appearance") { /* ... */ }
}
#if os(macOS)
.formStyle(.automatic)
.scenePadding()
#endif
```

`.scenePadding()` produces the recommended spacing around the root view of a
macOS window. Apple's Settings documentation pairs `.automatic` with
`.scenePadding()` for the same reason -- both adapt to platform context
automatically.

API reference: [`FormStyle`](https://developer.apple.com/documentation/swiftui/formstyle)
and [`scenePadding(_:)`](https://developer.apple.com/documentation/SwiftUI/View/scenePadding(_:)).

Avoid hardcoding `.formStyle(.grouped)` unless you specifically want the
iOS-style grouped look on macOS.

## Modal Sizing

Use sizing tokens for modal frames instead of magic numbers. Define a namespace
such as `ScaledDimensions` (or extend `Metrics`) so window sizes stay consistent
and adapt to Dynamic Type or accessibility scaling. The numbers below are
illustrative (macOS-window scale); size tokens to your own layouts and platform:

```swift
enum ScaledDimensions {
    static let modalWidth: CGFloat = 1200
    static let modalHeight: CGFloat = 860
}

// CORRECT -- use the token
.frame(maxWidth: ScaledDimensions.modalWidth,
       maxHeight: ScaledDimensions.modalHeight)

// WRONG -- magic numbers, drift across modals
.frame(maxWidth: 1200, maxHeight: 860)
```

If you need different sizes per platform, branch inside the token definition
rather than at every callsite.

## View Modifiers

Create reusable modifiers for common patterns so token application stays in one
place:

```swift
struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(Metrics.spacingMD)
            .background(Palette.surface)
            .clipShape(.rect(cornerRadius: Metrics.rLG))
    }
}

extension View {
    func card() -> some View { modifier(CardStyle()) }
}
```

## Text Hierarchy

Compose `TypeScale` and `Palette` tokens for consistent text hierarchy:

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
