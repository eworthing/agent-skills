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
