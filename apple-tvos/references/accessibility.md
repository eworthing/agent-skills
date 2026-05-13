# tvOS Accessibility Deltas

tvOS replaces touch with the Siri Remote's focus engine. Modal dismissal,
default focus on dialogs, and VoiceOver traversal all diverge from
iOS/macOS. For generic VoiceOver, traits, Dynamic Type, and Reduce Motion,
defer to the authoritative community `swiftui-expert-skill`
(`references/accessibility-patterns.md`).

## tvOS-A01 — Modal Dismissal: Menu Button, Not Close Button

On iOS and macOS, modals usually carry an explicit Close / Cancel button.
On tvOS, the canonical dismissal is the **Menu button** on the Siri
Remote, surfaced in code via `.onExitCommand`.

```swift
// CORRECT on tvOS — Menu button dismisses; no visible Close button
.fullScreenCover(isPresented: $showModal) {
    SettingsContent()
        .onExitCommand { showModal = false }
}

// WRONG on tvOS — Close buttons clutter the layout and confuse focus
.fullScreenCover(isPresented: $showModal) {
    SettingsContent()
        .toolbar {
            Button("Close") { showModal = false }  // unfocusable in some layouts
        }
}
```

If a modal needs an explicit dismiss action visible on tvOS (e.g., a
confirmation step), make it a real focusable element inside the modal,
not chrome.

## Cross-Platform Dismiss Pattern

For shared modal content across iOS / macOS / tvOS, branch the close
affordance:

```swift
ModalContent()
    .onExitCommand { dismiss() }           // tvOS Menu button + macOS Escape key
#if !os(tvOS)
    .overlay(alignment: .topTrailing) {
        Button("Close") { dismiss() }
            .accessibilityIdentifier("MyScreen_CloseButton")
    }
#endif
```

Availability: `.onExitCommand` is **tvOS 13.0+ AND macOS 10.15+**. On
macOS it triggers on the Escape key — not a no-op. On iOS / iPadOS /
visionOS it has no effect, so the modifier is safe to apply
unconditionally. The visible Close button must be `#if !os(tvOS)` to
avoid the focus / layout collisions described above.

## tvOS-A02 — Destructive Confirmation Dialog Default Focus (Severity-1)

`confirmationDialog` / `alert` initial focus follows declaration order.
On tvOS this is **severity-1** — the focus engine puts initial focus on
the first declared button, and there is no pointer to override it. A
destructive button declared first is one Select press away from
accidental data loss.

```swift
// CORRECT on tvOS — Cancel declared first, gets default focus
.confirmationDialog("Delete All Items?", isPresented: $confirm) {
    Button("Cancel", role: .cancel) { }
    Button("Delete All", role: .destructive) { deleteAll() }
} message: {
    Text("This cannot be undone.")
}
```

### Button Ordering Matrix

| Dialog type | First button (default focus) | Second button |
|---|---|---|
| Destructive | Cancel / Keep | Delete / Remove |
| Confirmation | Cancel / No | Confirm / Yes |
| Discard changes | Keep Editing | Discard |

The same rule is good practice on iOS / macOS, but on tvOS it is enforced
by the physical interaction model — verify on real hardware.

## VoiceOver on tvOS

VoiceOver on tvOS uses focus traversal, not direct touch. Focus order
matters more than visual order — VoiceOver reads elements in the order
driven by `.focusable()` and `@FocusState`. Verify the focus path
covers every readable element.

### tvOS-A03 — No Manual Focus Reassertion

Setting `isFocused = true` from `DispatchQueue.main.asyncAfter` hijacks
events VoiceOver and Switch Control expect to handle themselves. Use
focus containment (modals via `.fullScreenCover()`, scoped
`@FocusState`) instead. See
[references/design-regressions.md](design-regressions.md#anti-pattern-manual-focus-reassertion-tvos-a03)
for the full anti-pattern callout.

### tvOS-A04 — Hide Non-Actionable Focus Helpers from VoiceOver

A zero-size `Rectangle().fill(.clear)` used purely to capture focus
should be `.accessibilityHidden(true)`, not
`.accessibilityAddTraits(.isButton)`. Otherwise VoiceOver announces a
spurious "Button" with no label.

## Cross-References

- [references/focus-engine.md](focus-engine.md) — focus mechanics
  (container `.focusable()`, POD identity, hover conflict, settle delay,
  scroll, simulator divergence)
- [references/design-regressions.md](design-regressions.md) — tvOS
  design-review checks including modal focus containment and the
  manual-focus-reassertion anti-pattern
- `xctest-ui-testing` — identifier-as-API-contract conventions and the
  `AccessibilityMarkerView` pattern for tvOS root markers
