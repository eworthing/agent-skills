# Workflow: Critique Existing SwiftUI

Use this workflow when reviewing existing SwiftUI UI code or screenshots.

## Goal

Identify what makes the UI feel non-native, generic, inaccessible, hard to use, or hard to maintain. Provide concrete fixes.

## Step 1: Inventory The Screen

Identify:

- screen purpose
- primary user goal
- platform target
- navigation container
- main content shape
- primary action
- secondary actions
- state coverage
- custom components
- use of materials/glass
- accessibility modifiers
- preview coverage

## Step 2: Load References

Always load:

- `references/critique-rubric.md`
- `references/anti-web-smells.md`

Load as needed:

- `references/navigation-patterns.md`
- `references/iphone-layout.md`
- `references/ipad-layout.md`
- `references/visual-hierarchy.md`
- `references/accessibility.md`
- `references/liquid-glass.md`
- `references/generation-output-format.md`
- `references/expert-lenses.md`

## Step 3: Check Native Structure

Ask:

- Is the navigation container correct?
- Is custom navigation being invented?
- Is a web pattern driving structure?
- Is iPad layout intentionally adapted?
- Are sheets/inspectors used correctly?
- Are lists/forms used where native users expect them?

Flag severe structure issues before visual details.

## Step 4: Run Anti-Web-Smells

Run the full inventory in `references/anti-web-smells.md` (loaded in Step 2).

If three or more AI-generated silhouette smells occur, recommend regenerating from structure upward.

## Step 5: Run Accessibility Pass

Check:

- Dynamic Type
- VoiceOver labels and order
- icon-only buttons
- Reduce Motion
- Reduce Transparency
- contrast
- color independence
- localization
- touch targets

## Step 6: Run Visual Hierarchy Pass

Check:

- one primary action
- grouping
- typography
- spacing
- density
- decoration
- content readability
- empty/loading/error states

## Step 7: Score Rubric

Score all 11 dimensions using `references/critique-rubric.md` (loaded in Step 2).

## Step 8: Prioritize Findings

Order findings by severity:

1. likely disqualifier
2. serious deduction
3. noticeable weakness
4. polish issue

For each finding include:

- evidence from code or screenshot
- why it matters
- concrete fix
- affected file/component if known

## Step 9: Recommend Rewrite

If structure is wrong, do not suggest surface polish first.

Rewrite order:

1. navigation/container
2. state model
3. content grouping
4. actions
5. accessibility
6. visual polish
7. previews

## Output

Use the Required Review Output template in `references/critique-rubric.md`.
