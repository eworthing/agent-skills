# Critique Rubric

Use this reference when reviewing existing SwiftUI UI or self-reviewing generated UI.

Score each dimension from 1 to 5.

Any score below 3 requires a concrete fix.

Target score: 4 or higher across all dimensions.

## Scoring Scale

1 = fail
2 = weak
3 = workable
4 = strong
5 = native, polished, resilient

## 1. Native Apple Feel

1: Could be a React/Tailwind port. Custom chrome everywhere.
3: Uses some native containers but visual treatment feels foreign.
5: Feels structurally and behaviorally Apple-native.

Check:

- native navigation
- native controls
- native gestures
- system typography
- system colors
- SF Symbols
- no custom chrome without reason

## 2. Task Clarity

1: User cannot tell what to do next. Multiple competing CTAs.
3: Main task is present but cluttered.
5: Primary task is obvious in under two seconds.

Check:

- one primary action
- clear screen purpose
- supporting actions demoted
- no hero/marketing clutter
- useful empty/error recovery

## 3. Information Hierarchy

1: Flat, noisy, contradictory.
3: Basic hierarchy exists but uses too many signals.
5: Hierarchy is clear through restraint, grouping, typography, and placement.

Check:

- primary/secondary content
- grouping
- spacing rhythm
- text weight and size
- color discipline
- no decorative hierarchy

## 4. Navigation Fit

1: Custom or web-style navigation.
3: Native container used but imperfectly.
5: Container matches task topology.

Check:

- `TabView` for flat peer sections
- `NavigationStack` for drill-down
- `NavigationSplitView` for collection/detail
- sheets for bounded tasks
- inspectors for secondary editing
- alerts only for interruption

## 5. iPhone Ergonomics

1: Primary actions unreachable, dense, or tiny.
3: Usable but not thumb-friendly.
5: Reachable, readable, compact, task-focused.

Check:

- primary action placement
- tap target size
- list-first layout
- no dashboard grids
- no wide tables
- limited toolbar clutter
- search via `.searchable`

## 6. iPad Adaptation

1: Stretched iPhone layout.
3: Has iPad layout but breaks in some window sizes.
5: Uses iPad space for structure, selection, inspectors, keyboard, and pointer.

Check:

- compact and regular width
- `NavigationSplitView` where appropriate
- `TabView` when flat sections fit
- inspector for secondary editing
- explicit selection
- keyboard shortcuts for repeated commands
- pointer affordances
- useful empty detail state

## 7. Accessibility Resilience

1: Breaks with Dynamic Type, VoiceOver, contrast, motion, or transparency.
3: Basic labels and contrast, but weak variants.
5: Accessibility variants are part of design.

Check:

- Dynamic Type
- VoiceOver order
- icon labels
- Reduce Motion
- Reduce Transparency
- Increase Contrast
- dark/light mode
- color independence
- localization/RTL

## 8. Visual Restraint

1: Gradients, shadows, cards, glass, and animation used as fake polish.
3: Mostly restrained but one noisy area.
5: Every visual layer earns its place.

Check:

- no decorative gradients
- no card grid by default
- no shadow stacks
- no glass content cards
- no ornamental motion
- system materials do structural work

## 9. State Coverage

1: Happy path only.
3: Empty/loading/error exist but generic.
5: State coverage explains recovery and preserves user confidence.

Check:

- empty
- loading
- content
- error
- offline
- permission
- saving
- destructive confirmation
- undo where appropriate

## 10. SwiftUI Maintainability

1: Massive view, side effects in body, scattered literals.
3: Reasonable structure but outdated or inconsistent.
5: Small, semantic, previewable, and state-honest.

Check:

- small views
- `@Observable` for new state
- legacy observation justified
- no networking in body
- style centralized
- localized strings
- preview variants
- no magic numbers

## 11. Reductionist Pass

1: Decorative elements added for polish.
3: Some decoration remains but does not break use.
5: Every element carries meaning, structure, navigation, feedback, or confidence.

Ask:

If this visual element disappeared, would the user lose meaning, structure, navigation, or feedback?

If not, remove it.

Apply to:

- gradients
- shadows
- borders
- blobs
- decorative icons
- animations
- dividers
- cards
- helper text
- badges

## Required Review Output

When reviewing, output:

```md
## Verdict

One paragraph.

## Scores

| Dimension | Score | Fix Required |
|---|---:|---|
| Native Apple feel |  |  |
| Task clarity |  |  |
| Information hierarchy |  |  |
| Navigation fit |  |  |
| iPhone ergonomics |  |  |
| iPad adaptation |  |  |
| Accessibility resilience |  |  |
| Visual restraint |  |  |
| State coverage |  |  |
| SwiftUI maintainability |  |  |
| Reductionist pass |  |  |

## Serious Issues

- ...

## Concrete Fixes

- ...

## Suggested Rewrite Plan

1. ...
```

## Automatic Revision Rule

If any score is below 3:

- name the failure
- propose the smallest fix
- revise before presenting final generated UI when generating code
