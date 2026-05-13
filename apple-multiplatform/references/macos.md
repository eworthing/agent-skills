# macOS Gotchas

macOS SwiftUI is AppKit-backed; many iOS-shaped APIs are unavailable or behave
differently.

## TabView

`.page` style is **unavailable on macOS**. Use `.automatic` (sidebar tabs) or
design a different navigation surface.

```swift
TabView {
    /* ... */
}
#if os(macOS)
.tabViewStyle(.automatic)
#else
.tabViewStyle(.page)
#endif
```

## Modal Presentation

`.fullScreenCover` is **unavailable on macOS** (not merely a HIG mismatch — the
modifier does not exist). Use `.sheet`, or branch with `#if os(macOS)` if a
per-platform modal style is needed.

```swift
view
#if os(macOS)
.sheet(isPresented: $show) { ModalContent() }
#else
.fullScreenCover(isPresented: $show) { ModalContent() }
#endif
```

## Toolbar Placement

`.topBarLeading` / `.topBarTrailing` do not exist on macOS. Use `.navigation`,
`.primaryAction`, `.automatic`, or `.principal`. Map per platform if needed.

## `@CommandsBuilder` — `ForEach` Composition

Result builders for menus require explicit, statically-known children.
`ForEach` either does not compile or composes unreliably depending on SDK.
The portable workaround is to flatten the list into a `Menu`:

```swift
// FRAGILE — composition depends on SDK, may not compile
.commands {
    CommandGroup(after: .newItem) {
        ForEach(recentItems) { item in
            Button(item.title) { open(item) }
        }
    }
}

// PORTABLE — flatten into a Menu
.commands {
    CommandGroup(after: .newItem) {
        Menu("Recent") {
            ForEach(recentItems) { item in
                Button(item.title) { open(item) }
            }
        }
    }
}
```

## `NavigationSplitView` Defaults

Sidebar visibility heuristic differs from iOS. Often set `columnVisibility`
explicitly on macOS:

```swift
@State private var columns: NavigationSplitViewVisibility = .all

NavigationSplitView(columnVisibility: $columns) { /* ... */ }
```

## Keyboard Shortcuts

`Cmd` is canonical, not `Ctrl`. After adding or changing any
`.keyboardShortcut(...)` modifier, audit the codebase for collisions across
every surface that can register a shortcut (Commands, toolbar buttons, menu
items, focused-view modifiers):

```bash
rg -n 'keyboardShortcut\(' YourApp
```

If two actions bind the same key combination, resolve it in the Commands
layer (where shortcut ownership is centralized) or by changing the shortcut
on one of the colliding actions. A duplicate binding produces silent
non-determinism — whichever view installs its modifier later wins, and the
loser fails silently. Verify no collision with system shortcuts (`Cmd+W`,
`Cmd+Q`, `Cmd+,`, `Cmd+H`).

## Window Resize-Down Stability

Drag the window to its minimum width. Critical toolbar actions must remain
visible (no truncation to overflow menus for primary actions).

## Settings Form Style

Use `.formStyle(.automatic)` (see `swiftui-design-tokens`). Forcing `.grouped`
produces an iOS-looking dialog on macOS that feels foreign.

## Related Skills

- `swiftui-design-tokens` — design tokens including form style
- `swiftui-expert-skill` — `references/macos-scenes.md`, `references/macos-window-styling.md`
