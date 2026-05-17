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

Look for:

- hero section
- dashboard grid
- card grid
- Material FAB
- custom tab bar
- hamburger menu
- right-rail AI panel
- Tailwind spacing
- glass content cards
- neutral SaaS palette
- emoji icons
- hover-only controls

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

Score 1 to 5:

1. Native Apple feel
2. Task clarity
3. Information hierarchy
4. Navigation fit
5. iPhone ergonomics
6. iPad adaptation
7. Accessibility resilience
8. Visual restraint
9. State coverage
10. SwiftUI maintainability
11. Reductionist pass

Any score below 3 needs a concrete fix.

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

## Output Template

```md
## Verdict

...

## Rubric Scores

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

## Serious Findings

### 1. ...
- Evidence:
- Why it matters:
- Fix:

## Quick Wins

- ...

## Rewrite Plan

1. ...
```

## Review Tone

Be precise. Do not flatter. Do not bury serious structure problems under visual polish.

Prefer:

"Replace the card dashboard with a grouped List because this is scannable item content."

Avoid:

"Maybe make it more native."
