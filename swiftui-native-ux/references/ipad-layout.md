# iPad Layout

Use this reference when designing, generating, or critiquing iPad UI, Mac-class layouts, or adaptive SwiftUI.

## Core Principle

Do not stretch iPhone UI.

iPad layouts should use space for structure, context, selection, editing, keyboard, pointer, and multiwindow behavior.

Design for:

- full screen
- half screen
- narrow windows
- Stage Manager style resizing
- external keyboard
- pointer
- multitasking
- persistent selection
- collection/detail workflows
- secondary editing without losing context

## Choose Structure By Task

Use `TabView` when the app has flat, top-level destinations.

Use `NavigationSplitView` when the app has collection/detail or hierarchy.

Use `.inspector()` for secondary editing or property panels.

Use `.sheet` for bounded tasks with cancel/done semantics.

Use `.fullScreenCover` only for truly immersive flows such as onboarding, capture, or authentication.

## NavigationSplitView

Prefer `NavigationSplitView` for:

- sidebar plus detail
- collection plus detail
- three-level hierarchy
- document browsers
- mail/notes/files-like flows
- admin lists on regular width

Two-column:

```swift
NavigationSplitView {
    Sidebar(selection: $selection)
} detail: {
    DetailView(selection: selection)
}
```

Three-column:

```swift
NavigationSplitView {
    Sidebar(selection: $section)
} content: {
    ItemList(section: section, selection: $item)
} detail: {
    ItemDetail(item: item)
}
```

Use three columns only when there is a true global hierarchy.

Reject three columns for shallow content.

## TabView On iPad

`TabView` can be correct on iPad.

Use `TabView` when:

- destinations are flat peers
- users switch modes often
- there is no persistent collection/detail relationship
- the iPhone and iPad mental model should stay aligned

Reject forced `NavigationSplitView` when tabs better match the product.

## Inspectors

Inspectors are the native container for secondary editing on regular width.

Use `.inspector()` for:

- metadata
- formatting controls
- properties
- filters that modify current context
- secondary settings for selected content
- detail adjustments

Prefer inspector when the user should keep seeing the primary content.

Use sheet when the user is entering a bounded task with Cancel/Done.

Reject:

- right-rail web sidebars
- blocking sheets for every property edit
- full-screen property editors
- permanent panels that cannot collapse

## Compact Width Survival

Every iPad layout must survive narrow width.

Do not branch only on `UIDevice.current.userInterfaceIdiom`.

Prefer:

- horizontal size class
- container width
- split-view column visibility
- adaptive content density
- compact previews

Test:

- about 375 pt width
- half screen
- full screen
- regular width
- large Dynamic Type

Reject:

- iPad-only layouts that break under compact width
- hard-coded widths that trap content
- hidden sidebar toggles
- detail panes that render empty without selection recovery

## Selection State

iPad often needs persistent selection.

Prefer:

- explicit selection binding
- stable IDs
- placeholder detail state
- restoring last selected item when safe
- clear empty detail message when nothing is selected

Reject:

- detail panes that silently show stale content
- selection hidden inside local row state
- no placeholder for empty selection

## Keyboard Support

On iPad and Mac, repeated document/app commands should have keyboard shortcuts.

Good candidates:

- New
- Save
- Search
- Delete
- Refresh
- Close
- Cancel
- Confirm
- Navigate between panes
- Toggle inspector
- Start/stop primary workflow when safe

Do not add shortcuts for every button.

Use:

```swift
.keyboardShortcut("n", modifiers: .command)
```

and native toolbar/menu placement where relevant.

## Pointer Support

Pointer affordances should clarify interactivity.

Prefer:

- visible hover feedback for custom interactive regions
- native controls where hover is automatic
- context menus for secondary actions
- clear selection state

Reject:

- hover-only actions
- invisible buttons revealed only on pointer hover
- web tooltip dependency
- custom hover effects that fight native pointer behavior

## Drag And Drop

Consider drag and drop when:

- reordering is core
- moving items between collections is core
- importing files/media matters
- iPad users benefit from spatial manipulation

Do not add drag and drop as decorative complexity.

## Multiwindow

For document-like apps, consider whether the UI should support multiple windows.

Ask:

- Can users work on two documents/items side by side?
- Does selection belong per window?
- Does navigation state restore per scene?
- Are sheets scoped to the correct scene?
- Are singleton UI states avoided?

## Density

iPad can show more, but density must be earned.

Prefer:

- multi-pane structure
- inspectors
- sidebars
- keyboard commands
- larger previews
- contextual secondary controls

Reject:

- desktop SaaS density pasted onto iPad
- giant empty margins
- stretched single-column forms
- iPhone tab content simply widened to 900 pt
- tiny controls because "there is more space"

## iPad Review Checklist

Ask:

- Is this just a stretched iPhone layout?
- Is `TabView` or `NavigationSplitView` the correct top-level model?
- Does collection/detail preserve context?
- Does secondary editing belong in an inspector?
- Does the layout work at compact iPad width?
- Are keyboard shortcuts provided for repeated document/app commands?
- Are pointer interactions considered?
- Is selection state explicit and restorable?
- Does the detail pane have a useful empty state?
