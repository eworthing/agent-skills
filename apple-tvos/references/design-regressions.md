# tvOS Design-Regression Checks

tvOS design regressions rarely fail unit tests but break user-facing UX
in ways a code review on a flat iPhone screenshot will not catch. For
non-tvOS regression patterns (Dynamic Type clipping, keyboard shortcut
collisions, macOS window-resize stability, cross-platform parity),
review work belongs in the consuming project's PR template or
`AGENTS.md`. This file covers only tvOS-specific design regressions.

## Liquid Glass: Chrome Only on tvOS

Apply glass materials only on **chrome surfaces** (persistent toolbar,
navigation bar, tab bar). Never on modal content stacked on top of an
already-glass surface — the double blur produces muddy, low-contrast
foregrounds. Generic Liquid Glass adoption rules live in the
authoritative community `swiftui-expert-skill`
(`references/liquid-glass.md`); this section covers only the tvOS-focus
implications.

### Glass-on-Glass Anti-Pattern

```swift
// WRONG — glass button inside a modal that already has a glass background
.fullScreenCover(isPresented: $showSettings) {
    VStack {
        Button("Apply") { /* ... */ }
            .buttonStyle(.glass)           // glass-on-glass artifact
    }
    .glassBackgroundEffect()
}

// CORRECT — solid bordered buttons inside a glass-backed modal
.fullScreenCover(isPresented: $showSettings) {
    VStack {
        Button("Apply") { /* ... */ }
            .buttonStyle(.borderedProminent)
    }
}
```

### Button-Style Selection on tvOS

| Container | Primary | Secondary |
|---|---|---|
| Persistent toolbar (chrome) | `.glassProminent` | `.glass` |
| Modal / `.fullScreenCover` content | `.borderedProminent` | `.bordered` |
| Focusable content cards | `.card` | — |
| Non-focusable content rows | `.plain` | `.plain` |

On tvOS, the focus engine renders its own emphasis — do not also tint
bordered buttons. On iOS/macOS, apply `.tint(Palette.brand)` to bordered
buttons (see `swiftui-design-tokens`).

### Why Not `.plain` With Custom Styling On tvOS

`.buttonStyle(.plain)` + custom glass/rounded styling on focusable
buttons *compiles fine* but loses the focus engine's automatic focus
ring handling. Symptoms on real tvOS hardware:

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

`.bordered` and `.borderedProminent` integrate with the focus engine:
ring spacing, clipping prevention, and (on tvOS 26+) Liquid Glass focus
treatment are all handled automatically. The plain-style escape hatch is
only safe for non-focusable content rows.

## Modal Focus Containment

On tvOS, focus must be **trapped** inside an open modal until it
dismisses. `.sheet()` does not reliably trap focus on older tvOS
versions — press right repeatedly and focus may leak to elements behind
the sheet.

```swift
// WRONG on tvOS — focus can leak out
.sheet(isPresented: $showModal) { ModalContent() }

// CORRECT on tvOS — full-screen cover traps focus, dismisses via Menu
.fullScreenCover(isPresented: $showModal) { ModalContent() }
```

When reviewing a UI change that adds a new modal on tvOS, verify focus
containment in the manual-QA pass: open the modal, press right (or
down, depending on layout) 5+ times, and confirm focus stays inside.

## Anti-Pattern: Manual Focus Reassertion

If a tvOS focus regression appears, the wrong fix is to add a manual
focus reset loop:

```swift
// WRONG — fights the focus system; breaks VoiceOver and Switch Control
DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
    isFocused = true
}
```

The right fix is **focus containment**: use `.fullScreenCover()` for
modals, scope `@FocusState` to the smallest possible region, and let the
tvOS focus system handle focus on view appear/disappear. Manual
reassertion hijacks focus events that VoiceOver and Switch Control
expect to control themselves.

## tvOS Focus Traversal QA Checklist

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

## Severity

For tvOS-supporting apps, focus regressions are **severity-1** even when
all tests pass. A test suite that exercises only iOS will silently miss:

- A modal that lets focus leak to elements behind it
- A manual focus reset loop that breaks VoiceOver on Apple TV
- A button style that produces glass-on-glass artifacts
- A destructive dialog whose Delete button has default focus

Surface these in the design-review note even if CI is green.

## Cross-References

- [references/focus-engine.md](focus-engine.md) — focus mechanics
- [references/accessibility.md](accessibility.md) — Menu dismissal,
  destructive dialog focus matrix, VoiceOver on tvOS
- `swiftui-expert-skill` (`references/liquid-glass.md`) — generic
  Liquid Glass adoption rules (auth)
- `swiftui-design-tokens` — platform-branched motion springs, button
  tint tokens
