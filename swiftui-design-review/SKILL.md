---
name: swiftui-design-review
author: eworthing
description: >-
  Non-regression UI review workflow for iOS, macOS, and tvOS apps. Catches
  design principle regressions tests miss: Dynamic Type clipping,
  accessibility identifier drift, button-style violations, glass material
  misuse, modal focus containment regressions on tvOS, macOS window-resize
  breakage, and keyboard-shortcut collisions. Use when reviewing UI/UX
  changes, toolbar or navigation refactors, modal/overlay additions,
  cross-platform parity work, or before merging view-heavy PRs.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# Design Regression Review

## Purpose

Catch "design principle regressions" that automated tests miss: subtle
layout breakage under Dynamic Type, accessibility identifier drift, button
style violations, and unintended visual changes across iPhone and iPad.

## When to Use

- Non-trivial UI/UX changes or refactors (especially toolbars/navigation/overlays)
- Adding or changing modal/overlay presentation
- Adjusting design tokens, button styles, or material usage
- "Cleanup" PRs that could unintentionally change visual behavior

Skip this for purely internal/model changes with no UI behavior impact.

## Workflow

### Step 1: Declare the Non-Regression Contract

Before making changes, write down what must NOT change:

- **Layout stability**: Existing views render correctly at standard and large Dynamic Type sizes
- **Accessibility identifiers**: No identifiers renamed or removed without a migration plan
- **Button style consistency**: Modal buttons use `.bordered`/`.borderedProminent`, not glass or plain
- **iPhone/iPad adaptivity**: Layout works on both form factors

Use the checklist at [references/non-regression-checklist.md](references/non-regression-checklist.md).

### Step 2: Validate Against Core UI Rules

Hard rules to verify:

- Modal/overlay buttons use `.bordered` or `.borderedProminent` (not glass or `.plain`)
- No hardcoded colors or spacing (use design tokens)
- `.accessibilityIdentifier()` applied to leaf elements only
- No identifiers on containers with `.accessibilityElement(children: .contain)`
- Materials used for modal backgrounds (not `Color.black.opacity(...)`)
- Glass materials limited to chrome surfaces; no glass-on-glass
- On tvOS, modal focus stays contained until the modal dismisses
- No manual focus reset loops anywhere in the diff

Glass material conventions, tvOS modal containment rules, the manual
focus-reassertion anti-pattern, and the tvOS focus-traversal QA list are
detailed in
[references/liquid-glass-and-tvos.md](references/liquid-glass-and-tvos.md).

#### Destructive Actions

When reviewing a UI change that introduces or modifies a destructive
action (delete, reset, clear, regenerate), apply this rule:

| Action Type | Confirmation Required? | Reason |
|-------------|------------------------|--------|
| Destructive + Undoable | No | User can undo (e.g. `clearList`, hide a row) |
| Destructive + NOT Undoable | Yes | Cannot recover (e.g. `permanentReset`, `regenerateAll`) |

Verify the action's destructiveness against its reversibility, not its
verb. A scary-sounding "Clear" with an undo stack does not need a
confirmation dialog; an innocuous-sounding "Regenerate" that wipes user
input does.

#### Keyboard Shortcut Collision Audit

After adding or changing any `.keyboardShortcut(...)` modifier, audit
the codebase for collisions across every surface that can register a
shortcut (Commands, toolbar buttons, menu items, focused-view modifiers):

```bash
rg -n 'keyboardShortcut\(' YourApp
```

If two actions bind the same key combination, resolve it in the Commands
layer (where shortcut ownership is centralized) or by changing the
shortcut on one of the colliding actions. A duplicate binding produces
silent non-determinism — whichever view installs its modifier later
wins, and the loser fails silently.

### Step 3: Manual QA (High-Risk Flows)

**iPhone:**
- Navigation flows work correctly (push/pop, sheet present/dismiss)
- Dynamic Type: no clipped labels or buttons in toolbars, menus, or compact views
- Large Dynamic Type sizes (AX1-AX5): critical content still readable

**iPad:**
- Multitasking: layout adapts to split view and slide over
- Popovers and sheets display correctly
- No content clipped or hidden in landscape orientation

**Both:**
- Dark mode: all text readable, no invisible elements
- VoiceOver: reading order makes sense, all interactive elements reachable
- Orientation changes: layout adapts without breakage

**macOS:**
- Window resize down: critical toolbar actions stay visible (no truncation
  to overflow menus for primary actions)
- Keyboard shortcuts: new `.keyboardShortcut(...)` modifiers don't collide
  with existing app shortcuts or system shortcuts (`Cmd+W`, `Cmd+Q`,
  `Cmd+,`, `Cmd+H`)
- Settings/preferences views use `.formStyle(.automatic)` not forced
  `.grouped`

**tvOS (if supported):**
- Toolbar focus traversal: focus moves left/right across items without
  skipping or wrapping unexpectedly
- Default focus on entry: opening a screen places focus on the expected
  element
- Overlay dismiss: Menu button on Siri Remote dismisses overlays and
  returns focus to the trigger element
- Modal focus containment: focus stays inside open modals (test by
  pressing right 5+ times)

**Cross-platform parity principle**: if the app supports tvOS, prefer
parity across platforms unless the platform genuinely diverges. tvOS has
no keyboard shortcuts, so a `Cmd+N` action on iOS/macOS will not have a
tvOS counterpart — that's a real divergence. A toolbar action available
on iOS but missing on tvOS without a stated reason is almost always an
oversight.

For tvOS-specific glass material and focus-containment rules, see
[references/liquid-glass-and-tvos.md](references/liquid-glass-and-tvos.md).

### Step 4: Provide Evidence for UI-Heavy Changes

Include one of:
- Before/after screenshots on iPhone and iPad
- A "visual diff" note explaining what changed and why
- Screenshots at both standard and large Dynamic Type sizes

### Step 5: Automated Validation

Run your project's test suite and linting:

```bash
# Build for both form factors
xcodebuild build -scheme YourApp -destination 'platform=iOS Simulator,name=iPhone 16'
xcodebuild build -scheme YourApp -destination 'platform=iOS Simulator,name=iPad Pro 13-inch (M4)'

# Run UI tests
xcodebuild test -scheme YourApp -destination 'platform=iOS Simulator,name=iPhone 16'

# Lint
swiftformat . --lint
swiftlint lint --quiet
```

## Common Mistakes

1. **Changing accessibility identifiers casually** -- breaks existing UI tests. Always migrate deliberately and update test identifier enums.
2. **Using hardcoded colors in modals** -- use design tokens and system materials so they adapt to dark mode and accessibility settings.
3. **Skipping Dynamic Type checks** -- layout regressions commonly hide at larger text sizes where content overflows containers.
4. **Assuming iPhone layout works on iPad** -- test both, especially for modals and popovers which behave differently.
5. **Breaking VoiceOver order** -- reordering views can change accessibility navigation. Verify reading order after layout changes.
6. **Manual focus reassertion on tvOS** -- using `DispatchQueue.main.asyncAfter` to set `isFocused = true` fights the focus system and breaks VoiceOver and Switch Control. Use focus containment instead (see references).
7. **Stacking glass over glass** -- glass material on a button inside an already-glass-backed modal produces muddy, low-contrast visuals. Use `.borderedProminent` inside modals.

## References

- `swiftui-design-tokens` skill -- Token patterns and button style rules
- `xctest-ui-testing` skill -- Accessibility identifier conventions and new component test checklist
