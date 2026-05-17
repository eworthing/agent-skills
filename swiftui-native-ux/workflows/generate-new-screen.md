# Workflow: Generate New SwiftUI Screen

Use this workflow when asked to create a new SwiftUI screen or component.

## Goal

Generate a native Apple SwiftUI screen that fits the task, device, platform conventions, accessibility requirements, and project architecture.

## Step 1: Identify Context

Determine:

- platform: iPhone, iPad, universal, Mac-class
- task type: browse, detail, edit, create, capture, search, settings, onboarding, dashboard-like summary
- data shape: collection, item, hierarchy, form, media, status
- user goal
- primary action
- secondary actions
- risk: destructive, permission, offline, privacy, payment, irreversible

Do not start with visual styling.

## Step 2: Load References

Load as needed:

- native structure: `references/navigation-patterns.md`
- iPhone: `references/iphone-layout.md`
- iPad: `references/ipad-layout.md`
- visual polish: `references/visual-hierarchy.md`
- accessibility: `references/accessibility.md`
- Liquid Glass: `references/liquid-glass.md`
- output code contract: `references/generation-output-format.md`
- anti-web-smells: `references/anti-web-smells.md`

## Step 3: Choose Native Structure

Choose one primary structure:

- `TabView` for flat top-level sections
- `NavigationStack` for linear drill-down
- `NavigationSplitView` for collection/detail or hierarchy on regular width
- `.sheet` for bounded tasks
- `.inspector` for secondary editing on iPad/Mac
- `Form` for settings/editing
- `List` for scannable collections

Write the choice and reason before code.

## Step 4: Define State Coverage

Define needed states:

- empty
- loading
- content
- error
- offline
- permission
- saving
- validation
- destructive confirmation

Do not generate happy-path-only UI.

## Step 5: Define Accessibility Risks

Check:

- Dynamic Type
- VoiceOver labels/order
- contrast
- Reduce Motion
- Reduce Transparency
- color independence
- localization expansion
- touch target size
- iPad keyboard/pointer when relevant

## Step 6: Detect Web Gravity Before Code

Reject if the initial idea includes:

- hero section
- dashboard card grid
- Material FAB
- hamburger menu
- right-rail AI assistant
- Tailwind spacing
- decorative gradient blob
- custom tab bar
- custom back button
- glass content cards

Replace with native structure.

## Step 7: Generate Component Plan

Produce:

- screen view
- state model
- row components
- section components
- empty/loading/error views
- style modifiers
- previews

Keep views small.

## Step 8: Generate Code

Use:

- semantic typography
- system colors
- SF Symbols
- native containers
- localized strings according to project convention
- `@Observable` for new UI state where needed
- `@State` for local state
- `@Binding` or `@Bindable` for editing
- no side effects in `body`

## Step 9: Add Previews

When practical, include:

- compact
- regular
- dark mode
- large Dynamic Type
- Reduce Transparency
- empty/loading/error states

For small leaf views, include only previews that cover real layout risk.

## Step 10: Self-Review

Use `references/critique-rubric.md`.

Report:

- anti-web-smell result
- accessibility risks
- iPad adaptation note
- any justified deviations

## Output Template

```md
## Native Structure

...

## State Coverage

...

## Accessibility Notes

...

## SwiftUI Code

\`\`\`swift
...
\`\`\`

## Preview Coverage

...

## Self-Review

...
```

## Failure Conditions

Regenerate before final if:

- structure is web-first
- custom navigation is unnecessary
- content depends on glass for readability
- iPhone layout is dashboard-like
- iPad layout is stretched
- accessibility labels are missing
- Dynamic Type would break layout
