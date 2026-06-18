# Navigation Patterns

Use this reference when choosing or critiquing SwiftUI navigation structure.

## Core Principle

Choose navigation by task topology, not by visual taste.

Style comes after structure.

## Decision Tree

### Flat Top-Level Destinations

Use `TabView`.

Good for:

- Home / Search / Library / Settings
- Today / Browse / Saved / Profile
- modes with peer status
- frequent switching

Reject:

- hamburger menu
- custom tab bar
- sidebar on compact iPhone
- dashboard grid as navigation

### Linear Drill-Down

Use `NavigationStack`.

Good for:

- list to detail
- settings subpages
- setup flows
- item creation with nested choices
- history to detail

Use typed destinations when possible.

### Collection / Detail

Use `NavigationSplitView` when width supports it.

Good for:

- sidebar plus detail
- item list plus detail
- document browser
- mail/notes/files-like interaction
- persistent selection

Collapse gracefully on compact width.

### Bounded Task

Use `.sheet`.

Good for:

- create item
- edit item
- settings subset
- picker
- import
- short multi-step task

Use detents when partial height fits.

### Secondary Editing

Use `.inspector()` on iPad and Mac.

Good for:

- metadata
- formatting
- properties
- filters
- advanced controls
- selected-object settings

### Destructive Or Mutually Exclusive Choice

Use `.confirmationDialog`.

Good for:

- delete confirmation with choices
- destructive row action
- choosing one of several actions

### Interruption

Use `.alert`.

Good for:

- unrecoverable error
- permission explanation
- destructive confirmation when a dialog is clearer
- important blocking decision

Reject alerts for routine feedback.

## NavigationStack Rules

Prefer:

- typed routes
- small route enums
- stable IDs
- navigation state outside leaf views when flow-wide
- `navigationDestination(for:)`

Reject:

- manual booleans for complex routing
- pushing arbitrary views without a model route
- custom breadcrumb trails
- custom back buttons
- navigation side effects inside row rendering

Example:

```swift
enum Route: Hashable {
    case item(Item.ID)
    case settings
}

@State private var path: [Route] = []

NavigationStack(path: $path) {
    ItemList()
        .navigationDestination(for: Route.self) { route in
            switch route {
            case .item(let id):
                ItemDetail(id: id)
            case .settings:
                SettingsView()
            }
        }
}
```

## NavigationSplitView Rules

Prefer:

- explicit selection
- placeholder detail when selection is nil
- column visibility state when user control matters
- compact fallback
- stable list IDs

Reject:

- split view with no meaningful detail
- empty detail pane without explanation
- hiding the sidebar toggle without replacement
- three columns for shallow data
- device-idiom-only branching

## TabView Rules

Prefer `TabView` for flat sections.

Tabs should be:

- few
- stable
- peer-level
- frequently used
- understandable by label and symbol

Reject:

- more tabs than the platform can handle cleanly
- tabs that are actually filters
- tabs as a replacement for segmented control
- custom tab bars

## Sheets

Use sheets for tasks with clear boundaries.

Prefer:

- Cancel/Done semantics
- detents when appropriate
- dismissal protection only when data loss is possible
- simple internal navigation if the task needs it

Reject:

- nested sheet towers
- full-screen cover for property editing
- pushing from a sheet into the main stack without clear model
- sheets used as fake right rails on iPad

## Inspectors

Use inspectors for secondary editing on regular width.

Prefer:

- togglable inspector
- selected-object property editing
- toolbar button to show/hide
- layout that preserves primary context

Reject:

- custom right rail
- always-visible clutter
- blocking sheet for context-preserving edits

## Confirmation Dialogs and Alerts

Match the Decision Tree: `.confirmationDialog` for a destructive or mutually
exclusive choice, `.alert` for a blocking interruption.

**SDK 27 — prefer data-driven presentation for per-item dialogs.** When the
dialog or alert acts on a *specific value* (the row the user tapped, the item
pending deletion), choose the `item:` overload (`confirmationDialog(_:item:)` /
`alert(_:item:)`) over a separate `isPresented` Bool paired with `presenting:`.
A single optional drives presentation and the unwrapped value flows to the
`actions` builder — fewer "showing the wrong item / stale flag" mismatches. This
is a presentation-shape choice; it requires the Xcode 27 SDK, so gate with
`if #available(iOS 27, *)` for older deployment targets.

```swift
@State private var photoToDelete: Photo?
// …
.confirmationDialog("Delete photo?", item: $photoToDelete) { photo in
    Button("Delete \(photo.name)", role: .destructive) { delete(photo) }
}
```

Prefer:

- `item:` overload when the prompt is about one specific value
- plain `isPresented:` for a routine, value-less confirmation

Reject:

- a synthesized `Binding<Bool>` + `presenting:` when one optional would do
- the legacy `Alert`-returning `alert(item:) { _ in Alert(...) }`

## Toolbar Placement

Prefer semantic placements:

- `.confirmationAction` for Save/Done/Create
- `.cancellationAction` for Cancel
- `.destructiveAction` for destructive actions where available
- `.primaryAction` for main toolbar command when appropriate
- `.topBarLeading` and `.topBarTrailing` when semantic placement is not enough
- `.bottomBar` for bottom actions in compact contexts

Reject:

- toolbar icon soup
- multiple competing primary actions
- unlabeled mystery icons
- destructive action beside primary action without separation

### Overflow and Minimization (SDK 27)

When items exceed the available width (narrow window, iPhone, resize), the
system moves the overflow into a trailing menu. SDK 27 lets you steer *what*
stays, overflows, or pins, and whether the bar minimizes on scroll. Requires
the Xcode 27 SDK; gate `if #available(iOS 27, *)` for older deployment targets.

- `visibilityPriority(.high)` / `.low` on a `ToolbarItem` / `ToolbarItemGroup` —
  higher-priority content stays in the bar; lower-priority overflows first.
- `ToolbarOverflowMenu { … }` — content that always lives in the overflow menu
  (iOS / visionOS 27).
- `ToolbarItem(placement: .topBarPinnedTrailing)` — never overflows
  (iOS / visionOS 27).
- `toolbarMinimizeBehavior(.onScrollDown, for: .navigationBar)` — minimize the
  bar as content scrolls.
- Status bar is now a placement: `toolbarVisibility(.hidden, for: .statusBar)`
  replaces `statusBarHidden(_:)` on iOS 27.

Prefer letting the system overflow, using priority to keep the one or two
most-used actions in the bar. Reject hand-rolled overflow menus and hiding
actions the system would surface for you.

```swift
.toolbar {
    ToolbarItem(placement: .topBarPinnedTrailing) { ShareButton() }
    ToolbarOverflowMenu {
        ExportButton()
        ClearAllButton()
    }
}
```

## Search

Use `.searchable`.

Prefer:

```swift
.searchable(text: $query, prompt: "Search")
```

Reject:

- custom search fields
- floating search bars that blend into content
- search hidden behind a menu when search is core

## Row Actions

Prefer:

- `.swipeActions` for common row operations
- `.contextMenu` for secondary row operations
- visible primary row tap target

Reject:

- hidden long-press as only path
- custom swipe implementation
- hover-only actions on touch

**SDK 27 — swipe outside `List`.** `.swipeActions` historically took effect only
inside a `List`. Mark a `ScrollView` + `LazyVStack` / `LazyVGrid` (or stack) with
`swipeActionsContainer()` and `.swipeActions` works on its rows — a native
alternative to `List` for swipeable grid / masonry layouts. Keep `.swipeActions`
on each row; add `swipeActionsContainer()` on the scroll container. Without it,
`.swipeActions` outside a `List` is inert. (iOS / macOS / watchOS / visionOS 27;
tvOS unavailable; gate for older deployment targets.)

```swift
ScrollView {
    LazyVStack {
        ForEach(stickers) { sticker in
            StickerRow(sticker)
                .swipeActions {
                    Button(role: .destructive) { delete(sticker) } label: {
                        Label("Delete", systemImage: "trash")
                    }
                }
        }
    }
}
.swipeActionsContainer()
```

## Navigation Review Checklist

Ask:

- What is the task topology?
- Is the native container obvious?
- Is custom navigation being invented?
- Does the compact layout preserve user location?
- Does iPad preserve selection and context?
- Are primary actions placed semantically?
- Are destructive actions confirmable or undoable?
- Do system gestures still work?
