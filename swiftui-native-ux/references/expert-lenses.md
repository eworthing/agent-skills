# Expert Lenses

Use this reference for targeted critique passes.

Each lens is a short way to re-read a design from a specific expert perspective. Practitioner lenses sharpen judgment. They do not overrule Apple platform behavior.

## How To Use

Invocation pattern:

```md
Apply the [Lens Name] lens.
```

Return:

- 1 to 3 observations
- severity
- concrete fix
- whether the issue belongs in code, structure, copy, or visual treatment

## Apple Platform Lens

Question:

Does this use the platform's native containers, controls, gestures, typography, materials, and accessibility behavior before inventing custom UI?

Look for:

- correct navigation container
- native controls
- semantic toolbar placement
- system gestures
- system colors
- SF Symbols
- accessibility variants

Fix:

Replace custom UI with native SwiftUI structures first.

## Norman Lens

Question:

Are affordances, signifiers, mapping, feedback, constraints, and error recovery clear?

Look for:

- visible signifiers
- clear cause/effect
- recoverable mistakes
- obvious control purpose
- no hidden primary gestures

Fix:

Make the action visible, feedback immediate, and recovery clear.

## Nielsen Lens

Question:

Does the UI satisfy basic usability heuristics without sacrificing native platform behavior?

Look for:

- visibility of system status
- match to user expectations
- user control and freedom
- consistency
- error prevention
- recognition over recall
- flexibility
- minimalism
- recovery
- help only when needed

Fix:

Reduce cognitive burden and improve predictability.

## Tognazzini Lens

Question:

Does the interaction respect latency, Fitts' Law, autonomy, defaults, anticipation, and discoverability?

Look for:

- small targets
- distant primary actions
- slow blocking animations
- poor defaults
- hidden commands
- no keyboard path

Fix:

Improve target size, responsiveness, defaults, and command access.

## Wroblewski Lens

Question:

Would this work one-handed, in portrait, under partial attention?

Look for:

- top-heavy primary actions
- too much navigation chrome
- dense controls
- dashboard grids
- difficult thumb reach

Fix:

Move high-frequency actions into reachable/native positions and prune content.

## Viticci Lens

Question:

Does this respect the iPad as a real computer?

Look for:

- stretched iPhone layout
- no split view
- no inspector
- no keyboard support
- no pointer consideration
- poor window resizing
- weak selection state

Fix:

Use iPad space for structure, not just scale.

## de With Lens

Question:

Is the interface physically coherent, restrained, tactile, and exciting without intimidation?

Look for:

- material used structurally
- haptics at meaningful moments
- controls that feel responsive
- delight that does not slow the task
- no fake decorative depth

Fix:

Make interaction tactile and restrained. Remove theatrical polish.

## Arment Lens

Question:

Can a person with reading glasses, progressives, or sensitivity to blur still read this?

Look for:

- blur under text
- glass behind dense content
- low contrast
- thin text
- busy backgrounds
- chrome that requires content blur to be visible

Fix:

Use solid/tinted surfaces and keep content readable.

## Byrne-Haber Lens

Question:

Does this assume dark mode, thin text, or translucency is automatically accessible?

Look for:

- forced dark mode
- halation risk
- thin light text over dark material
- no user choice
- low contrast
- transparency dependence

Fix:

Support user choice, stronger text, and opaque variants.

## Appleton Lens

Question:

Are AI features scoped to the user's task, or bolted on as a generic chatbox?

Look for:

- right-rail AI assistant
- global chatbot
- sparkle button everywhere
- AI with no accept/reject
- AI not tied to selection

Fix:

Use contextual affordances, inline suggestions, sheets, or inspectors with review/undo.

## Litt Lens

Question:

Is AI making the app more malleable, or just adding another panel?

Look for:

- AI sidecar glued onto existing UI
- no human review loop
- no scoped context
- no reversibility
- automation that hides consequences

Fix:

Keep humans in control with clear scope, preview, accept, reject, undo.

## Hudson Lens

Question:

Are the SwiftUI navigation containers used correctly?

Look for:

- wrong container
- hidden sidebar toggle
- custom back behavior
- bad split-collapse behavior
- navigation state in the wrong place

Fix:

Rebuild around `NavigationStack`, `NavigationSplitView`, `TabView`, sheets, and inspectors.

## Tidwell Lens

Question:

What is the pattern name, and is it the right one?

Look for:

- unnamed invented patterns
- web pattern where native pattern exists
- dashboard used as catch-all
- filters acting like tabs
- cards acting like lists

Fix:

Name the pattern and map it to the native Apple equivalent.

## Refactoring UI Lens

Question:

Is hierarchy clear through size, weight, color, spacing, and grouping without decorative noise?

Look for:

- weak hierarchy
- too many borders
- too many shadows
- arbitrary spacing
- poor grouping
- decorative gradients

Fix:

Work in grayscale mentally. Use fewer visual variables. Translate away Tailwind implementation.

## Evidence Discipline Lens

Question:

Is this rule backed by the right source tier?

Use:

- Apple sources for platform behavior
- empirical research for model failure modes
- practitioner sources for taste lenses
- web sources only after translation

Fix:

Downgrade unsupported hard claims into heuristics.
