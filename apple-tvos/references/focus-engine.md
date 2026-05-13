# tvOS SwiftUI Patterns

tvOS uses a focus engine instead of touch. That changes several SwiftUI
patterns from the rest of the platform family — composition, animation,
and scroll all have tvOS-specific caveats that don't show up on iOS or
macOS.

## tvOS-F01 — Composition: No `.focusable()` on Containers

Applying `.focusable()` to a container that wraps focusable children
blocks focus from reaching the children. The focus engine stops at the
outer wrapper. Apply `.focusable()` only to leaf views.

```swift
// WRONG — focus stops at the row; cards inside never receive focus
HStack {
    ForEach(cards) { ItemCard(card: $0) }
}
.focusable()

// CORRECT — focus reaches each card
HStack {
    ForEach(cards) { card in
        ItemCard(card: card)
            .focusable()
            .focused($focusedID, equals: card.id)
    }
}
```

## tvOS-F02 — POD Views + `@FocusState`

POD views (no property wrappers) get SwiftUI's `memcmp` fast-path
diffing, but on tvOS pure-POD focusable rows risk **focus identity loss
on parent redraw** — when the row's identity changes from SwiftUI's
perspective, the focus engine sees a new element and may move focus
elsewhere.

Always pair focusable POD children with `@FocusState` + `.focused(_:equals:)`
in the parent:

```swift
struct Grid: View {
    @FocusState private var focusedID: Card.ID?

    var body: some View {
        LazyVGrid(columns: cols) {
            ForEach(cards) { card in
                CardView(card: card)               // POD, fast diffing
                    .focused($focusedID, equals: card.id)
            }
        }
    }
}
```

This gives the focus engine a stable identity anchor independent of the
view's POD identity.

## tvOS-F03 — Animation: Focus Hover Conflict

tvOS has a built-in focus hover effect — a ~200ms perspective lift with
specular shine — applied to every focusable element. Custom `.animation()`
modifiers on the focusable view itself can fight this animation,
producing visible jitter on real hardware.

**Mitigation:** scope custom animation to **child content** inside the
focusable element, not to the focusable element itself.

```swift
// WRONG — custom animation fights focus hover on the card
Button { tap() } label: {
    CardContent(card: card)
}
.animation(.spring, value: card.isHighlighted)  // fights focus animation

// CORRECT — animation scoped to inner content
Button { tap() } label: {
    CardContent(card: card)
        .animation(.spring, value: card.isHighlighted)  // child-only
}
```

If you still see jitter, wrap the animated content in a `Group` with its
own `.animation()` inside an `.overlay()`, leaving the card's focus
animation completely untouched.

## tvOS-F04 — Animation: Focus Settle Delay

For animations that should only run **after** focus has fully settled
(thumbnail playback, detail loading, expensive content reveal), use a
token-based delay pattern. Without it, swiping rapidly through cards
starts and immediately cancels animations on every card the user passes,
causing visible noise.

```swift
@State private var focusSettled = false
@State private var focusToken = 0

.onChange(of: isFocused) { _, newValue in
    focusToken += 1
    let token = focusToken
    if newValue {
        focusSettled = false
        Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(200))
            guard token == focusToken else { return }  // stale — user moved on
            focusSettled = true
        }
    } else {
        focusSettled = false
    }
}
```

The counter ensures that if the user moves focus quickly, only the
final focused element actually triggers its expensive animation. Every
intermediate focus change increments `focusToken` and invalidates
already-scheduled work.

## tvOS-F07 — Animation: Simulator vs Hardware

The tvOS Simulator does **not** replicate focus animations faithfully —
the hover effect curve, perspective lift, and specular shine all behave
differently than on Apple TV hardware. Always verify focus animations on
real hardware before declaring an animation issue solved.

## tvOS-F05 — Scroll: Focus-Driven Scrolling

On tvOS, users don't free-scroll. Scrolling happens because focus moved
to a focusable child that was off-screen, and the framework scrolls to
bring it into view. **If a `ScrollView` contains no focusable elements,
it is completely unscrollable.**

```swift
// WRONG on tvOS — Text is not focusable, ScrollView won't move
ScrollView {
    ForEach(items) { item in
        Text(item.name)
    }
}

// CORRECT on tvOS — focusable leaves drive scrolling
ScrollView {
    LazyVStack {
        ForEach(items) { item in
            Text(item.name)
                .focusable()
                .focused($focusedID, equals: item.id)
        }
    }
    .focusSection()
}
```

## tvOS-F06 — Scroll: `.viewAligned` over `.paging`

`.scrollTargetBehavior(.paging)` works on tvOS but full-page jumps on a
1920x1080 display feel visually jarring. `.viewAligned` gives smoother
focus-to-focus navigation that matches what users expect from the
platform.

```swift
ScrollView(.horizontal) {
    LazyHStack { ForEach(items) { ItemCard(item: $0) } }
        .scrollTargetLayout()
}
.scrollTargetBehavior(.viewAligned)   // preferred on tvOS
```

## Motion Tokens

Use the motion tokens from the `swiftui-design-tokens` skill rather than
hardcoding spring/duration values. Platform-branched focus springs and
reduce-motion alternatives live there.

## Cross-References

- [references/accessibility.md](accessibility.md) — `.onExitCommand` Menu
  dismissal, destructive dialog default focus, VoiceOver on tvOS
- [references/design-regressions.md](design-regressions.md) — modal focus
  containment, manual focus reassertion anti-pattern, glass-on-glass,
  button-style focus-ring, tvOS focus-traversal QA checklist
- `xctest-ui-testing` `references/tvos.md` — XCUITest focus assertions,
  Siri Remote API, focus reachability audit; typed-enum identifier
  conventions; `AccessibilityMarkerView` for tvOS root markers
- `swiftui-design-tokens` `references/motion-tokens.md` —
  platform-branched spring tokens and reduce-motion alternatives
