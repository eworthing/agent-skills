# Visual Hierarchy

Use this reference when polishing spacing, typography, grouping, density, empty states, loading states, and overall visual clarity.

## Core Principle

Good visual hierarchy makes the next useful thing obvious without decorative noise.

Use fewer signals better.

## Hierarchy Variables

Use these variables deliberately:

- size
- weight
- color
- opacity
- spacing
- alignment
- grouping
- position
- material
- motion

Do not pile all variables onto one element.

If something is larger, bolder, colored, boxed, shadowed, and animated, the design is shouting.

## One Variable Rule

Prefer changing one major hierarchy variable at a time.

Examples:

- primary title: larger size
- secondary text: secondary color
- selected row: system selection state
- destructive action: destructive tint
- grouped content: sectioning

Reject:

- bold plus color plus box plus shadow for the same emphasis
- noisy "polish" stacked on weak IA
- decorative hierarchy

## Typography

Prefer semantic text styles.

Use:

- `.largeTitle` for major screen titles when useful
- `.title` and `.title2` for major sections
- `.headline` for row or card headers
- `.body` for primary readable text
- `.subheadline` or `.callout` for supporting text
- `.footnote` and `.caption` only for nonessential metadata

Reject:

- tiny gray essential information
- hard-coded 12 pt body content
- web-style uppercase micro labels
- all-centered app screens
- custom fonts for dense controls without testing

## Spacing

Use rhythm, not random numbers.

Prefer:

- native `.padding()`
- named spacing tokens
- 4 pt grid
- system list/form spacing
- section grouping

Example named scale:

```swift
enum AppSpacing {
    static let xsmall: CGFloat = 4
    static let small: CGFloat = 8
    static let medium: CGFloat = 12
    static let large: CGFloat = 16
    static let xlarge: CGFloat = 24
}
```

Reject:

- `.padding(11)`
- `.padding(15)`
- random spacer heights
- layout fixed by magic numbers
- Tailwind-like translation without platform reason

## Grouping

Prefer native grouping.

Use:

- `Section`
- `List`
- `Form`
- `LabeledContent`
- `DisclosureGroup`
- system grouped backgrounds

Reject:

- every group wrapped in a custom card
- borders around every cluster
- shadows as group separators
- nested cards
- dashboard metric tiles by default

## Lists

Lists should be scannable.

Good row hierarchy:

- primary label
- useful secondary detail
- optional status/accessory
- clear action affordance

Reject:

- three metadata rows in tiny gray text
- ambiguous icons
- row height fixed against Dynamic Type
- essential data hidden in trailing tiny labels

## Cards

Use cards sparingly.

Cards can be useful for:

- previewing rich objects
- media thumbnails
- grouped actions
- dashboard-like summaries on iPad only when the product truly needs them

Cards are wrong for:

- ordinary settings
- plain item collections
- iPhone navigation
- every row
- fake depth

If a `List` would work, start there.

## Empty States

A good empty state includes:

- one symbol or simple visual
- one concise explanation
- one primary next action
- optional secondary action

Pattern:

```swift
ContentUnavailableView(
    "No Tracks",
    systemImage: "music.note.list",
    description: Text("Add local audio to build your first board.")
)
```

Reject:

- decorative mascots as the main content
- marketing copy
- multiple CTAs
- empty state with no recovery path
- illustration that pushes action below the fold

## Loading States

Prefer:

- skeleton/redacted list when content shape is known
- progress view when operation blocks interaction
- cached content while refreshing
- optimistic updates only with rollback

Reject:

- spinner for every small load
- infinite shimmer for simple operations
- layout jumping when content arrives
- loading state that hides navigation

## Error States

Error hierarchy:

1. what happened
2. why it matters
3. what the user can do
4. retry/recover action

Reject:

- raw error text
- blame language
- generic "Oops"
- alert storms
- unrecoverable dead ends

## Color

Use color sparingly for meaning.

Prefer:

- semantic system colors
- tint for action identity
- destructive color only for destructive actions
- status colors paired with text/icon

Reject:

- color as the only differentiator
- decoration gradients
- many accent colors
- custom palette that ignores dark mode

## Motion

Motion should clarify cause and effect.

Prefer:

- short transitions
- selection feedback
- completion feedback
- Reduce Motion fallback

Reject:

- looping decorative motion
- shimmer as personality
- animation that delays input
- motion used to hide weak hierarchy

## Reductionist Pass

Ask:

If this element disappeared, would the user lose meaning, structure, navigation, feedback, or confidence?

If not, remove it.

Apply this to:

- gradients
- shadows
- borders
- background blobs
- decorative cards
- ornamental icons
- animations
- dividers
- labels
- helper text

## Visual Hierarchy Review Checklist

Ask:

- What is the first thing the user should notice?
- What is the second?
- Is hierarchy carried by one signal or five?
- Are sections doing grouping work?
- Would this still read in grayscale?
- Would this still read at large Dynamic Type?
- Are cards actually needed?
- Does every visual element earn its place?
