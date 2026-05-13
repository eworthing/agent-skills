# Liquid Glass + tvOS Design-Review Rules

Design-review concerns specific to Liquid Glass material usage and tvOS
focus behavior. These regressions rarely fail unit tests but break the
user-facing UX in ways code review on a flat iPhone screenshot will not
catch.

## Liquid Glass: Chrome Only

Use glass materials only on **chrome surfaces** — the persistent toolbar,
navigation bar, tab bar — and never on modal content stacked on top of an
already-glass surface.

### Glass-on-Glass Anti-Pattern

```swift
// WRONG — glass button inside a modal that already has a glass background
.fullScreenCover(isPresented: $showSettings) {
    VStack {
        Button("Apply") { /* ... */ }
            .buttonStyle(.glass)           // visual artifact: glass on glass
    }
    .glassBackgroundEffect()
}

// CORRECT — solid bordered buttons inside a glass-backed modal
.fullScreenCover(isPresented: $showSettings) {
    VStack {
        Button("Apply") { /* ... */ }
            .buttonStyle(.borderedProminent)
            .tint(Palette.brand)
    }
}
```

The glass-on-glass case produces double blur and saturation; the foreground
button reads as muddy and loses legibility under bright backgrounds.

### Button-Style Selection by Container

| Container                           | Primary             | Secondary |
|-------------------------------------|---------------------|-----------|
| Persistent toolbar (chrome)         | `.glassProminent`   | `.glass`  |
| Modal / sheet / `.fullScreenCover` content | `.borderedProminent` | `.bordered` |
| Content rows                        | `.plain`            | `.plain`  |
| tvOS focusable cards                | `.card`             | —         |

Apply `.tint(Palette.brand)` to bordered buttons on non-tvOS for brand
consistency. On tvOS, the focus engine renders its own emphasis — do not
also tint.

### Why Not `.plain` With Custom Styling On tvOS

`.buttonStyle(.plain)` + custom glass/rounded styling on focusable buttons
*compiles fine* but loses the focus engine's automatic focus-ring handling.
Symptoms on real tvOS hardware:

- Focus rings clipped by enclosing `ScrollView` containers
- Focus rings overlapped by adjacent rows
- Developer adds manual spacing tweaks (`.padding(.vertical, 16)`) trying
  to compensate, which never fully fixes the visual artifacts and breaks
  layout density

```swift
// WRONG on tvOS — manual styling loses focus ring management
Button(action: tap) {
    HStack { /* content */ }
        .background(.regularMaterial, in: .rect(cornerRadius: 12))
}
.buttonStyle(.plain)   // focus ring now clips against ScrollView

// CORRECT on tvOS — let the system own focus rendering
Button(action: tap) {
    HStack { /* content */ }
}
.buttonStyle(.bordered)   // automatic focus ring + Liquid Glass on focus
```

`.bordered` and `.borderedProminent` integrate with the focus engine: ring
spacing, clipping prevention, and (on tvOS 26+) Liquid Glass focus
treatment are all handled automatically. The plain-style escape hatch is
only safe for non-focusable content rows, where there is no focus ring to
render in the first place.

## tvOS Modal Focus Containment

On tvOS, focus must be **trapped** inside an open modal until it
dismisses. `.sheet()` does not reliably trap focus on older tvOS versions —
press right repeatedly and focus may leak to elements behind the sheet.

```swift
// WRONG on tvOS — focus can leak out
.sheet(isPresented: $showModal) { ModalContent() }

// CORRECT on tvOS — full-screen cover traps focus, dismisses via Menu
.fullScreenCover(isPresented: $showModal) { ModalContent() }
```

When reviewing a UI change that adds a new modal on tvOS, verify focus
containment in the manual-QA pass: open the modal, press right (or down,
depending on layout) 5+ times, and confirm focus stays inside.

## Anti-Pattern: Manual Focus Reassertion

If a tvOS focus regression appears, the wrong fix is to add a manual focus
reset loop:

```swift
// WRONG — fights the focus system; breaks VoiceOver and Switch Control
DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
    isFocused = true
}
```

The right fix is **focus containment**: use `.fullScreenCover()` for
modals, scope `@FocusState` to the smallest possible region, and let the
tvOS focus system handle focus on view appear/disappear. Manual reassertion
hijacks focus events that VoiceOver and Switch Control expect to control
themselves.

## tvOS Manual QA Checklist (Design-Review)

When a UI change ships on tvOS, walk through:

- **Toolbar focus traversal**: focus moves left and right across toolbar
  items without skipping or wrapping unexpectedly.
- **Default focus on entry**: opening a screen places focus on the
  expected element (usually the first content item or a primary action).
- **Overlay dismiss path**: pressing the Menu button on the Siri Remote
  dismisses overlays and returns focus to the trigger element (or a
  sensible fallback if the trigger is gone).
- **Focus on appear**: focus is set deterministically on appear — no
  flicker between two elements competing for focus.

## macOS Design-Review Notes

macOS is keyboard- and pointer-driven, so design-review checks differ from
iOS:

- **Window resize down**: drag the window to its minimum width. Critical
  toolbar actions must remain visible (no truncation to dot-dot-dot menus
  for primary actions).
- **Keyboard shortcut collisions**: new `.keyboardShortcut(...)` modifiers
  must not collide with existing app shortcuts or system shortcuts
  (`Cmd+W`, `Cmd+Q`, `Cmd+,`, etc.). Run with the Keyboard menu open and
  scan for duplicates.
- **Form style adaptivity**: settings views should use
  `.formStyle(.automatic)` (see `swiftui-design-tokens`). Forcing
  `.grouped` produces an iOS-looking dialog on macOS that feels foreign.

## Severity

For tvOS-supporting apps, focus regressions are **severity-1** even when
all tests pass. A test suite that exercises only iOS will silently miss:

- A modal that lets focus leak to elements behind it
- A manual focus reset loop that breaks VoiceOver on Apple TV
- A button style that produces glass-on-glass artifacts

Surface these in the design-review note even if CI is green.
