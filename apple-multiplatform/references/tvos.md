# tvOS Gotchas

tvOS imports `UIKit` (so `canImport(UIKit)` evaluates true) but disallows a
long list of UIKit APIs at the symbol level. **Always prefer `#if os(...)` for
API gating on tvOS** — `canImport(UIKit)` is insufficient.

For tvOS focus engine, accessibility deltas, and design regressions see the
dedicated `apple-tvos` skill. This file covers cross-platform compatibility
gating only.

## Trap Matrix

| Topic | Pattern | Wrong | Right |
|---|---|---|---|
| Drag-and-drop receiving | Wrap `.onDrop`, `DropDelegate`, `NSItemProvider` extraction in `#if !os(tvOS)` | `#if canImport(UIKit) /* .onDrop */` | `#if !os(tvOS) /* .onDrop */` |
| `editMode` | Wrap with `#if os(iOS)` | `#if !os(tvOS) /* @Environment editMode */` (still compiles on macOS, where editMode does not exist) | `#if os(iOS) /* @Environment editMode */` |
| Haptics (`UIImpactFeedbackGenerator`) | Requires `#if os(iOS)` | `#if canImport(UIKit) /* UIImpactFeedbackGenerator */` — compiles on tvOS, crashes at runtime | `#if os(iOS) /* UIImpactFeedbackGenerator */` |
| Focus | Use `.focusSection()`, `.focusable()`, `.onMoveCommand`, `.focused($state)` | Touch / hover modifiers | Focus-driven APIs |
| Pointer | No mouse / trackpad APIs | `.onHover`, `.cursor` | Skip; gate with `#if !os(tvOS)` |
| `Menu` button dismissal | Press the Menu button (`UIPressType.menu`) | n/a | `.onExitCommand` — see `apple-tvos` `references/accessibility.md` |

## Haptics — Right vs Wrong

```swift
// WRONG — compiles on tvOS, crashes at runtime
#if canImport(UIKit)
UIImpactFeedbackGenerator(style: .medium).impactOccurred()
#endif

// CORRECT — symbol excluded from tvOS at compile time
#if os(iOS)
UIImpactFeedbackGenerator(style: .medium).impactOccurred()
#endif
```

## editMode — Inline vs File-Level Guard

`@Environment(\.editMode)` exists only on iOS-family platforms (iOS, iPadOS,
Mac Catalyst). Pick one style consistently per file.

```swift
// Inline guard — keeps the property only on iOS
struct ItemList: View {
    #if os(iOS)
    @Environment(\.editMode) private var editMode
    #endif

    var body: some View { /* ... */ }
}
```

```swift
// File-level guard — entire view is iOS-only
#if !os(tvOS) && !os(macOS)
struct ItemList: View {
    @Environment(\.editMode) private var editMode  // safe: file excludes tvOS + macOS
    var body: some View { /* ... */ }
}
#endif
```

**Audit checklist** when a file references `editMode`:
1. File-level `#if os(iOS)` or `#if !os(tvOS) && !os(macOS)` wraps the type, **or**
2. Inline `#if os(iOS)` wraps the `@Environment` declaration AND every read site

Watch out for `#if !os(tvOS)` alone — that still compiles `editMode` on macOS,
where it does not exist.

## Related Skills

- `apple-tvos` — focus engine, accessibility deltas, design regressions
- `swiftui-drag-drop` — drag-and-drop architecture, including tvOS gating
