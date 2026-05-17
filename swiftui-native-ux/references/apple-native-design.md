# Apple Native Design

Use this reference when generating or critiquing native Apple feel, system materials, controls, SF Symbols, tactile feedback, and visual restraint.

## Core Principle

A SwiftUI interface feels native when its structure, behavior, motion, typography, and affordances match the platform before decoration is added.

Native feel is not a paint job. It is the product of:

- correct navigation containers
- predictable gestures
- semantic controls
- system typography
- system colors
- SF Symbols
- accessibility resilience
- state honesty
- restraint

## Prefer Native Structure First

Prefer:

- `NavigationStack`
- `NavigationSplitView`
- `TabView`
- `List`
- `Form`
- `Section`
- `LabeledContent`
- `.toolbar`
- `.searchable`
- `.swipeActions`
- `.contextMenu`
- `.confirmationDialog`
- `.sheet`
- `.inspector`
- `.refreshable`

Reject:

- custom navigation bars
- custom tab bars
- custom search fields when `.searchable` fits
- custom row-swipe behavior
- custom modal chrome
- hamburger menus on iPhone
- Material Floating Action Buttons
- hand-rolled dashboard grids

## Content Before Chrome

Content must stay readable, tappable, and understandable before visual styling is added.

Prefer:

- opaque or readable content surfaces
- native grouped lists
- system backgrounds
- semantic color
- layout hierarchy

Reject:

- blur behind primary reading text
- decorative gradient backgrounds carrying hierarchy
- text on busy imagery without a protective overlay
- glassy content cards
- shadow stacks pretending to be depth

## Concentricity

When using rounded containers and controls, nested shapes should feel geometrically related.

Prefer:

- capsules for touch-friendly controls
- rounded rectangles for dense rows or desktop-style controls
- inner radius that respects parent radius and padding
- system button styles when possible

Reject:

- random corner radii
- mismatched rounded cards and buttons
- tiny pills inside giant rounded cards with no geometric relationship

## Materials And Depth

Use system materials as functional layers, not visual glitter.

Prefer:

- Liquid Glass or material effects for toolbars, tab bars, sidebars, floating controls, and accessories
- solid system backgrounds for dense content
- material depth only when it clarifies layering

Reject:

- glass-on-glass
- glass list rows
- glass content cards
- material backgrounds behind long-form text
- arbitrary drop-shadow stacks

## SF Symbols

Prefer SF Symbols for app UI iconography.

Use:

- `Image(systemName:)`
- `.symbolRenderingMode(.hierarchical)` for most controls
- `.symbolRenderingMode(.palette)` only when extra semantic distinction matters
- `.symbolVariant()` when the selected state can be expressed natively

Reject:

- emoji icons as primary app iconography
- PNG icons for standard platform concepts
- custom icon sets that fight Apple metaphors
- unlabeled icon-only buttons

Every icon-only interactive element needs an accessibility label.

Example:

```swift
Button {
    addItem()
} label: {
    Image(systemName: "plus")
}
.accessibilityLabel("Add item")
```

## Typography

Prefer semantic Dynamic Type styles.

Use:

- `.largeTitle`
- `.title`
- `.title2`
- `.title3`
- `.headline`
- `.body`
- `.callout`
- `.subheadline`
- `.footnote`
- `.caption`
- `.caption2`

Reject:

- hard-coded body font sizes by default
- tiny secondary text as a web-list reflex
- ultra-light type for functional text
- all-caps letter-spaced web labels
- centered body copy in ordinary app screens

Explicit font sizes are allowed only for rare brand or display moments, and they require accessibility review.

## Color

Prefer semantic system colors.

Use:

- `.primary`
- `.secondary`
- `.tint`
- `.accentColor` where project convention requires it
- `Color(uiColor: .systemBackground)`
- `Color(uiColor: .secondarySystemBackground)`
- `Color(uiColor: .systemGroupedBackground)`
- `Color(uiColor: .secondarySystemGroupedBackground)`

Reject:

- hard-coded black/white for body text
- neutral-zinc/slate web palettes as default app personality
- color as the only state indicator
- custom palettes that fail light/dark or contrast testing

## Physicality

Native Apple UI can feel tactile without becoming noisy.

Use `.sensoryFeedback(_:trigger:)` at meaningful inflection points:

- workflow completion
- destructive confirmation
- selection commit
- failed validation
- hardware-like discrete adjustment

Prefer:

- `.success` for completed multi-step flows
- `.selection` for discrete picker-like changes
- `.impact(weight: .light)` for refinement gestures
- `.error` for validation failure

Reject:

- haptics on every button tap
- haptics that fire during passive scrolling
- haptics that compensate for weak visual feedback
- noisy tactile feedback in forms

## Brand Expression

Brand expression belongs inside native structure, not in replacement of it.

Prefer brand through:

- copy tone
- accent color
- illustration in empty/onboarding states
- custom row content
- domain-specific symbols
- preferences
- tasteful animation at completion

Reject brand through:

- custom navigation routers
- custom tab bars
- nonstandard back behavior
- hiding system affordances
- custom controls where system controls fit

## Native Delight

Delight should reward progress or clarify interaction.

Prefer:

- completion animations
- subtle symbol transitions
- tactile confirmation
- contextual menus
- smart defaults
- recoverable mistakes

Reject:

- infinite shimmer
- decorative bounce
- animation that blocks input
- motion without meaning
- celebratory effects for routine taps

## Good Native Smells

A screen likely feels native when:

- the navigation container is obvious
- system gestures work
- rows align and scale with Dynamic Type
- actions are discoverable
- hierarchy is clear without borders everywhere
- iconography comes from SF Symbols
- controls use native styles
- empty/error states explain recovery
- iPad layout is not a stretched iPhone view

## Bad Native Smells

Flag and revise:

- custom back button
- card grid home screen
- dashboard metrics on iPhone
- Material FAB
- hero CTA header
- glass background under content
- gradient blob carrying hierarchy
- emoji icons for main UI
- fixed small text
- custom search
- custom row swipe
- hover-only affordance
