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

### Common Command Set

Match Apple's expected chords. Do not reinvent.

| Action | Shortcut | Modifier symbol |
|---|---|---|
| New | `.keyboardShortcut("n")` | ⌘N |
| New Window | `.keyboardShortcut("n", modifiers: [.command, .shift])` | ⇧⌘N |
| Save | `.keyboardShortcut("s")` | ⌘S |
| Close (window/tab) | `.keyboardShortcut("w")` | ⌘W |
| Find / Search | `.keyboardShortcut("f")` | ⌘F |
| Refresh | `.keyboardShortcut("r")` | ⌘R |
| Quit (Mac only) | `.keyboardShortcut("q")` | ⌘Q |
| Confirm primary | `.keyboardShortcut(.defaultAction)` | ⏎ |
| Cancel / dismiss | `.keyboardShortcut(.cancelAction)` | ⎋ |
| Delete | `.keyboardShortcut(.delete)` | ⌫ |

Modifier-less default; `.command` is implicit on `keyboardShortcut(_:)`.

```swift
Button("New Note", action: createNote)
    .keyboardShortcut("n")  // ⌘N

Button("Save", action: save)
    .keyboardShortcut("s")

Button("Delete", role: .destructive, action: delete)
    .keyboardShortcut(.delete)
```

### Split-Pane Navigation

For `NavigationSplitView`, support arrow-key navigation in the sidebar/content lists via `List(selection:)`. SwiftUI handles ↑/↓ automatically when the list has a binding selection; ensure focus reaches the list.

```swift
NavigationSplitView {
    List(items, selection: $selected) { item in
        Text(item.title).tag(item.id)
    }
} content: {
    // detail pane responds to selection change
} detail: {
    EmptyView()
}
```

### Menu Bar Commands (Mac Catalyst / Mac)

Surface shortcuts through `Commands` so they appear in the menu bar and accessibility-inspector keyboard tour, not just on the button.

```swift
.commands {
    CommandGroup(replacing: .newItem) {
        Button("New Note", action: createNote)
            .keyboardShortcut("n")
    }
    SidebarCommands()       // ⌃⌘S toggle sidebar
    InspectorCommands()     // toggle inspector
}
```

## Multiwindow

For document-like apps, consider whether the UI should support multiple windows.

### When To Adopt

Ask:

- Can users work on two documents/items side by side?
- Does selection belong per window?
- Does navigation state restore per scene?
- Are sheets scoped to the correct scene?
- Are singleton UI states avoided?

If two yeses → adopt `WindowGroup` with per-scene state. If zero → single window is correct; do not adopt multiwindow for symmetry alone.

### Scene Shape

```swift
@main
struct NotesApp: App {
    var body: some Scene {
        WindowGroup(for: Note.ID.self) { $noteID in
            NoteWindow(noteID: noteID)
        }
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Note") {
                    openNewWindow(for: Note.ID())
                }
                .keyboardShortcut("n", modifiers: [.command, .shift])
            }
        }
    }
}
```

`WindowGroup(for:)` gives each window its own document identity and isolated state. Opening a second window from `openWindow(value:)` produces a real second scene with independent selection.

### Per-Scene State

```swift
struct NoteWindow: View {
    let noteID: Note.ID?
    @SceneStorage("selectedSection") private var section: Section = .body
    @State private var inspectorPresented = false

    var body: some View {
        NavigationSplitView {
            SectionList(selection: $section)
        } detail: {
            NoteDetail(noteID: noteID, section: section)
        }
        .inspector(isPresented: $inspectorPresented) { Metadata(noteID: noteID) }
    }
}
```

`@SceneStorage` persists per scene, not per app. Two windows can have different sidebar selections. `@AppStorage` is global — wrong tool for per-window UI state.

### Pitfalls

Reject:

- singleton `@Observable` view-model used by every window — selection/scroll position will leak between scenes
- sheets attached to a top-level view that lives outside the scene's `NavigationSplitView` — wrong window gets the sheet
- `@AppStorage` for sidebar/section selection that should be per-window
- assuming `openWindow(id:)` opens a new scene when no `WindowGroup(for:)` data type is declared

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
