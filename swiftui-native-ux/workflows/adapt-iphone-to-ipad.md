# Workflow: Adapt iPhone UI To iPad

Use this workflow when converting an iPhone SwiftUI layout into an iPad-ready layout.

## Goal

Avoid stretched iPhone UI. Preserve the task while using iPad space for context, selection, editing, keyboard, pointer, and windowing.

## Step 1: Identify The Existing iPhone Model

Determine:

- top-level structure
- primary task
- content type
- navigation path
- collection/detail relationship
- edit flows
- modals
- settings
- search/filter behavior
- primary and secondary actions

## Step 2: Choose iPad Structure

Choose:

- `TabView` for flat peer sections
- `NavigationSplitView` for collection/detail or hierarchy
- two columns for collection/detail
- three columns for true global hierarchy
- `.inspector` for secondary editing
- `.sheet` for bounded tasks

Do not choose based only on device idiom.

## Step 3: Preserve Data Views

Reuse leaf content where possible.

Separate:

- data rows
- detail content
- editor sections
- empty/loading/error states

from:

- iPhone navigation wrapper
- iPad navigation wrapper

Same data view, different presentation.

## Step 4: Add Selection State

For collection/detail:

- create explicit selection
- use stable IDs
- provide placeholder detail when nil
- restore sensible selection when appropriate
- avoid stale detail content

Example:

```swift
@Observable
final class NavigationModel {
    var selectedItemID: Item.ID?
    var columnVisibility: NavigationSplitViewVisibility = .automatic
}
```

## Step 5: Replace Sheets With Inspectors Where Appropriate

Use inspector when:

- editing selected item properties
- toggling metadata
- showing secondary controls
- filtering within current context
- keeping content visible matters

Keep sheet when:

- task is bounded
- user needs Cancel/Done
- creation/import flow is separate
- modal focus is desirable

Reject full-screen property editing.

## Step 6: Add Keyboard And Pointer Behavior

For repeated document/app commands:

- add keyboard shortcuts
- ensure toolbar commands are visible
- provide context menus
- provide hover feedback for custom interactive regions

Do not add keyboard shortcuts for every minor button.

## Step 7: Test Widths

Test:

- compact width around iPhone size
- 1/3 split
- half screen
- full screen
- large Dynamic Type
- dark mode
- Reduce Transparency

Reject layouts that only work full screen.

## Step 8: Audit Density

Use iPad space for:

- persistent context
- larger preview
- editing controls
- split navigation
- keyboard workflows

Do not use iPad space for:

- more decorative cards
- giant margins
- dashboard clutter
- tiny desktop controls
- always-visible secondary panels

## Step 9: Output Adaptation Plan

Template:

```md
## Existing iPhone Structure

...

## iPad Structure

...

## State Changes

...

## Sheet vs Inspector Changes

...

## Keyboard/Pointer Additions

...

## SwiftUI Adaptation Sketch

\`\`\`swift
...
\`\`\`

## Compact Width Survival

...
```

## Common Fixes

Replace:

```swift
NavigationStack {
    List(items) { item in ... }
}
```

With:

```swift
NavigationSplitView {
    List(items, selection: $model.selectedItemID) { item in
        NavigationLink(value: item.id) {
            ItemRow(item: item)
        }
    }
} detail: {
    if let id = model.selectedItemID {
        ItemDetail(id: id)
    } else {
        ContentUnavailableView(
            "Select an Item",
            systemImage: "sidebar.left",
            description: Text("Choose an item from the sidebar.")
        )
    }
}
```

## Failure Conditions

Revise if:

- iPad is just wider iPhone
- no compact-width fallback
- selection is unclear
- property editing blocks context
- no keyboard path for repeated commands
- pointer interactions are ignored
