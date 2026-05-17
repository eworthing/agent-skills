# iPhone Layout

Use this reference when designing, generating, or critiquing compact-width iPhone SwiftUI UI.

## Core Principle

iPhone UI should be fast to understand, reachable, readable, and forgiving under distraction.

Design for:

- one-handed use
- partial attention
- small vertical space
- Dynamic Type
- portrait-first behavior
- short sessions
- obvious primary actions
- native list/detail expectations

## Default Containers

Prefer:

- `NavigationStack` for linear drill-down
- `TabView` for flat top-level sections
- `List` for scannable collections
- `Form` for settings and structured editing
- `Section` for grouping
- `.sheet` with detents for bounded tasks
- `.confirmationDialog` for action choices
- `.alert` for true interruption
- `.safeAreaInset(edge: .bottom)` for reachable primary action bars when appropriate

Reject:

- dashboard grids
- wide tables
- web sidebars
- hamburger menus
- custom tab bars
- multi-column layouts
- persistent right rails
- dense inline filters
- hero sections inside workflows

## Primary Actions

High-frequency primary actions should be reachable and obvious.

Prefer:

- bottom safe-area primary action
- toolbar confirmation action for form save
- form footer action for long forms
- visible row actions for repeated operations
- one primary action per screen

Reject:

- primary action only in a distant top corner when frequent
- multiple competing primary buttons
- sticky web CTAs
- Floating Action Buttons
- unlabeled icon-only primary actions

Example:

```swift
ScrollView {
    content
}
.safeAreaInset(edge: .bottom) {
    Button("Start") {
        start()
    }
    .buttonStyle(.borderedProminent)
    .controlSize(.large)
    .padding()
    .background(.bar)
}
```

## Search

Prefer `.searchable`.

Reject custom search bars unless the project has a documented reason.

Use search when:

- list has more than a small handful of items
- users know what they are looking for
- filtering is faster than browsing

Do not stack search, filters, sort, view toggles, bulk actions, and chips at the top of a compact screen unless all are genuinely core to the task.

## Lists Beat Cards

For iPhone, scannable content usually belongs in lists.

Prefer:

- `List`
- `.listStyle(.insetGrouped)` for settings/grouped content
- `.listStyle(.plain)` for feeds or dense collections
- `LabeledContent` for key/value rows
- swipe actions for common row operations
- context menus for secondary row operations

Reject:

- card grid as the default
- metric cards as navigation
- cards inside cards
- shadows on every row
- rows with tiny gray metadata that carries essential meaning

## Forms

Use `Form` for settings, preferences, structured editing, and grouped input.

Prefer:

- native `TextField`, `Picker`, `Toggle`, `Stepper`, `DatePicker`
- grouped sections
- inline validation
- clear save/cancel semantics
- keyboard-aware layout

Reject:

- custom input chrome
- web-like field cards
- placeholder-only labels for important fields
- form submit hidden only in top toolbar when the form is long

## Sheets

Use sheets for bounded tasks.

Prefer:

- `.presentationDetents([.medium, .large])` for partial tasks
- `.presentationDetents([.large])` for substantial forms
- `.interactiveDismissDisabled()` only when data loss risk is real
- explicit Done/Cancel for editing flows

Reject:

- `.fullScreenCover` for ordinary editing
- modal sheets for every minor control
- nested sheets
- pushing deeper navigation from a sheet when dismissing first is clearer

## Empty States

A good iPhone empty state has:

- one clear icon or symbol
- one sentence explaining the state
- one primary recovery action
- optional secondary explanation

Reject:

- mascot-first empty states
- marketing copy
- giant illustrations that push action below the fold
- empty states with three CTAs

## Loading States

Prefer:

- `.redacted(reason: .placeholder)` for list-like content
- progress indicator for blocking work
- optimistic UI only when rollback is clear
- clear disabled state for actions in progress

Reject:

- infinite shimmer everywhere
- layout jump after loading
- loading state with no cancel/retry when the operation can fail

## Error States

Errors should explain recovery.

Prefer:

- what happened
- what the user can do
- retry action when appropriate
- offline state when network failure is likely
- permission recovery path when permission is blocked

Reject:

- raw exception messages
- generic "Something went wrong"
- alert storms
- hidden error banners that vanish too quickly

## Ergonomic Red Flags

Flag and revise:

- top-heavy UI with all useful actions in the nav bar
- dense controls stacked above content
- horizontal card carousels as primary navigation
- tables with multiple columns
- tiny touch targets
- long-press as the only path to key action
- hover-only explanations
- toolbar icon soup

## iPhone Review Checklist

Ask:

- What is the one primary action?
- Is it reachable?
- Can the user understand the screen in two seconds?
- Does the screen still work at large Dynamic Type?
- Does the view avoid dashboard gravity?
- Are list rows scannable?
- Are destructive actions confirmed or undoable?
- Does every icon-only action have a label?
- Are empty, loading, and error states designed?
