# Anti-Web-Smells

Use this reference when reviewing generated SwiftUI, rewriting web-style UI, or detecting React/Tailwind/SaaS/dashboard residue.

This file is the attack dog. It should bark early.

## Core Principle

Most LLM-generated SwiftUI smells like a generic web dashboard unless forced otherwise.

If the screen could be a React admin template with Swift syntax, reject the structure before polishing details.

## The AI-Generated App Silhouette

If three or more of these appear together, reject and regenerate from structure upward:

- card-grid home screen
- emoji icons as primary app iconography
- neutral zinc/slate palette
- hero header with CTA
- dashboard metric cards
- right-rail AI assistant
- Material Floating Action Button
- generic motivational copy
- decorative gradient blob background
- hover-only controls
- hard-coded tiny gray secondary text

Do not patch surface details. Rebuild the native container and task flow.

## Layout Smells

Hard reject:

- hero section inside an app workflow
- marketing feature grid as home screen
- dashboard grid on iPhone
- three or four metric cards across compact width
- Material FAB
- stretched iPhone layout on iPad
- right-rail AI assistant glued onto an app
- desktop SaaS density on touch UI

Likely wrong:

- card-on-card-on-card nesting
- horizontal card carousel as primary navigation
- giant decorative illustration pushing action below fold
- huge gradient blob as visual identity
- layout built from arbitrary fixed frames

Prefer:

- `List`
- `Form`
- `Section`
- `NavigationStack`
- `NavigationSplitView`
- `TabView`
- `.sheet`
- `.inspector`
- `.safeAreaInset`

## Navigation Smells

Hard reject:

- hamburger menu on iPhone
- custom tab bar
- custom back button
- breadcrumb trail
- custom router replacing native navigation
- hidden sidebar toggle without replacement
- modal dialog made from custom `ZStack`

Likely wrong:

- toolbar with many unlabeled icons
- multiple primary actions
- destructive action next to confirmation action
- long-press as only path to important action

Prefer:

- native navigation containers
- native toolbar placements
- swipe actions
- context menus
- confirmation dialogs
- alerts only for true interruption

## Typography Smells

Hard reject:

- `.font(.system(size: 12))` for essential body content
- thin or ultra-light functional text
- tiny gray metadata carrying essential information
- all-caps letter-spaced micro labels
- clipped primary labels
- hard-coded line limit on important content

Likely wrong:

- centered body copy
- multiple custom fonts in one screen
- display font in dense UI
- web-style text hierarchy copied directly

Prefer:

- semantic Dynamic Type
- SF system font
- clear primary and secondary text
- multiline resilience

## Color And Material Smells

Hard reject:

- glass-on-glass
- glass content cards
- glass list rows
- thin text over glass
- gradient blob as hierarchy
- stacked shadows pretending to be depth
- forced dark mode without user setting
- hard-coded black/white text
- color-only status

Likely wrong:

- neutral zinc/slate default palette
- too many accent colors
- custom colors without dark-mode variants
- image background under text without overlay

Prefer:

- semantic system colors
- native materials only where functional
- solid content backgrounds
- status color plus symbol/text

## Spacing Smells

Hard reject patterns:

- `.padding(11)`
- `.padding(15)`
- `.frame(width: 327)`
- fixed row heights with text
- random `Spacer().frame(height:)` stacking

Likely wrong:

- Tailwind scale translated without reason
- arbitrary magic-number layout
- many nested `GeometryReader`s
- fixed-width buttons with localizable text

Prefer:

- native padding
- named spacing scale
- system list/form spacing
- flexible layout
- `ViewThatFits` when appropriate

## Interaction Smells

Hard reject:

- hover-only affordances
- tooltip required for primary information
- icon-only buttons without labels
- tap targets under 44 pt
- long-press as only key-action path
- haptic on every routine tap
- animation that blocks input

Likely wrong:

- "Tap here" prompts
- gestures without visible signifiers
- custom scroll physics
- custom row swipe

Prefer:

- visible affordances
- native controls
- swipe actions plus context menu
- meaningful haptics at inflection points
- Reduce Motion fallback

## AI Feature Smells

Hard reject:

- global AI chatbox stapled to every screen
- right-rail AI assistant as default
- AI output with no review/accept/reject affordance
- AI replacing native task flow
- AI suggestions blocking primary content

Likely wrong:

- generic sparkle button everywhere
- AI action detached from selected context
- no provenance for generated content
- no undo for AI changes

Prefer:

- contextual AI affordances
- inline suggestions
- inspectors for selected context
- sheets for bounded generation tasks
- accept/reject/undo
- visible scope

## iPad Smells

Hard reject:

- stretched iPhone layout
- no compact-width survival
- no keyboard support for repeated document/app commands
- no pointer consideration
- custom right rail instead of inspector
- three columns with no real hierarchy

Likely wrong:

- giant empty margins
- detail pane with no placeholder
- selection hidden in local row state
- sheet for secondary property editing

Prefer:

- `NavigationSplitView`
- explicit selection
- `.inspector`
- keyboard shortcuts for core commands
- pointer feedback where useful
- compact and regular previews

## SwiftUI Maintainability Smells

Hard reject:

- networking inside `View.body`
- persistence mutation inside `View.body`
- singletons mutated from views
- massive one-file screen with all subviews inline
- user-facing strings hard-coded without localization plan
- Combine-era observation introduced into new code without reason

Likely wrong:

- `GeometryReader` for simple alignment
- custom design tokens scattered in view bodies
- repeated literal paddings/colors/fonts
- view model doing navigation, networking, and formatting all at once

Prefer:

- small composable views
- `@Observable` for new UI state
- `@Bindable` where editing model state
- style modifiers or style structs
- previews for risky states
- localized strings

## Imported Skill Smells

These are common in cross-platform UI prompt packs and should be rejected for native SwiftUI apps:

Hard reject:

- Hero-Centric + Social Proof app screen
- CTA above the fold inside app workflow
- dashboard-first information architecture
- Tailwind spacing translated to SwiftUI
- Material FAB
- generic web design system as source of truth

Prefer:

- native task structure
- one primary action
- list/detail
- system navigation
- native controls
- platform semantics

## Rewrite Rule

When a web smell is detected:

1. Identify the web pattern.
2. Name the native Apple equivalent.
3. Replace structure before styling.
4. Remove decoration.
5. Rebuild hierarchy with system components.
6. Recheck accessibility and iPad adaptation.
