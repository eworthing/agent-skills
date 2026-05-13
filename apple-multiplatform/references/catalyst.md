# Mac Catalyst Gotchas

Catalyst inherits the iOS API surface but renders through AppKit. Things that
work on iPad regularly diverge here.

## Branching Catalyst-Specifically

Catalyst is `os(iOS)` AND `targetEnvironment(macCatalyst)`. To branch Catalyst
specifically from pure iOS / iPadOS:

```swift
#if targetEnvironment(macCatalyst)
// Catalyst-only behavior
#elseif os(iOS)
// Pure iOS / iPadOS (non-Catalyst)
#endif
```

## Common Divergences

| Topic | Pattern |
|---|---|
| Window sizing | Initial window size and resize behavior differ. Set `.defaultSize(...)` and verify under live resize. |
| Sidebar defaults | `NavigationSplitView` may default to a different column visibility than on iPad. Set explicitly. |
| Touch vs pointer | Pointer events arrive even though `os(iOS)` evaluates true. |
| App lifecycle | Multiple-window scenarios behave more like macOS than iPad. Test scene reuse and state restoration. |

## Window Sizing Example

```swift
WindowGroup {
    ContentView()
}
#if targetEnvironment(macCatalyst)
.defaultSize(width: 1200, height: 800)
#endif
```

## Verification Checklist

- Launch the app at default size — does it match design intent?
- Drag to minimum width — do toolbar / sidebar / detail still function?
- Open a second window from the dock — does state restore correctly?
- Close all windows — does the app quit (Catalyst) or stay running (macOS-style)?

## Related Skills

- `swiftui-expert-skill` — `references/macos-window-styling.md` covers window sizing patterns
