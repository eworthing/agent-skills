# Workflow: Rewrite Web-Style UI Into Native SwiftUI

Use this workflow when SwiftUI looks like React, Tailwind, Material, or a SaaS dashboard.

## Goal

Replace web structure with native Apple structure before polishing visuals.

## Step 1: Identify Web Pattern

Name the web pattern:

- hero section
- dashboard card grid
- pricing-card layout
- feature grid
- right-rail assistant
- hamburger menu
- Material FAB
- Tailwind utility spacing
- custom card list
- web sidebar
- breadcrumb trail
- hover-first controls

Do not start by changing colors.

## Step 2: Identify Native Equivalent

Map to native structure:

| Web Pattern | Native SwiftUI Equivalent |
|---|---|
| Hero section | Navigation title plus focused content or onboarding screen |
| Dashboard cards | List, grouped sections, or iPad summary with real purpose |
| Hamburger menu | TabView or NavigationSplitView |
| Material FAB | Toolbar primary action, bottom bar, or safe-area inset |
| Right-rail assistant | Inspector, sheet, or contextual inline affordance |
| Pricing/feature cards | Onboarding, settings sections, or product-specific flow |
| Breadcrumbs | NavigationStack back behavior |
| Custom search | `.searchable` |
| Custom row swipe | `.swipeActions` |
| Hover menu | Toolbar, context menu, visible action |

## Step 3: Strip Decorative Chrome

Remove:

- gradient blobs
- arbitrary shadows
- borders around every card
- glass content surfaces
- emoji icons
- neutral SaaS palette
- excessive rounded rectangles
- marketing CTAs
- fake stats

Keep:

- task
- content
- primary action
- real hierarchy
- domain semantics

## Step 4: Choose Correct Container

Use:

- `TabView` for flat sections
- `NavigationStack` for drill-down
- `NavigationSplitView` for collection/detail on iPad
- `List` for scannable content
- `Form` for settings/editing
- `.sheet` for bounded tasks
- `.inspector` for secondary editing

## Step 5: Rebuild Hierarchy

Use:

- title
- section
- row
- primary/secondary text
- system symbols
- native controls
- semantic color
- system backgrounds

Avoid:

- card grid as IA
- custom CSS-like wrappers
- arbitrary spacing
- multiple CTAs
- decoration as structure

## Step 6: Restore Platform Behaviors

Add native affordances:

- `.searchable`
- `.refreshable`
- `.swipeActions`
- `.contextMenu`
- `.toolbar`
- `.confirmationDialog`
- `.sensoryFeedback` where meaningful
- `.keyboardShortcut` for repeated iPad/Mac commands

## Step 7: Accessibility And Adaptation

Check:

- Dynamic Type
- VoiceOver labels
- Reduce Transparency
- Reduce Motion
- contrast
- iPad compact and regular width
- localization

## Output Template

```md
## Web Smells Found

- ...

## Native Replacement

- ...

## Structure Rewrite

...

## SwiftUI Code

\`\`\`swift
...
\`\`\`

## Why This Is More Native

...

## Remaining Tradeoffs

...
```

## Example Rewrite

Bad web-style structure:

```swift
VStack {
    HeroHeader()
    LazyVGrid(columns: columns) {
        StatCard(...)
        StatCard(...)
        StatCard(...)
    }
    FloatingActionButton(...)
}
```

Native direction:

```swift
NavigationStack {
    List {
        Section("Today") {
            LabeledContent("Queued", value: "\(queuedCount)")
            LabeledContent("Ready", value: "\(readyCount)")
        }

        Section("Actions") {
            Button("Create Board") {
                createBoard()
            }
        }
    }
    .navigationTitle("Boards")
    .toolbar {
        ToolbarItem(placement: .primaryAction) {
            Button {
                createBoard()
            } label: {
                Image(systemName: "plus")
            }
            .accessibilityLabel("Create Board")
        }
    }
}
```

## Failure Conditions

Rewrite again if:

- it still looks like a web dashboard
- the primary action is a FAB
- cards remain the primary structure on iPhone
- custom nav remains
- Tailwind spacing remains
- accessibility got worse
