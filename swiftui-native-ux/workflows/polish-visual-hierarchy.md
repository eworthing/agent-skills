# Workflow: Polish Visual Hierarchy

Use this workflow when a SwiftUI screen works but looks bland, noisy, generic, or unpolished.

## Goal

Improve clarity and polish by reducing noise, strengthening hierarchy, and using native Apple visual systems.

## Step 1: Freeze Structure

Before visual polish, confirm:

- navigation container is correct
- task is clear
- primary action is clear
- state coverage exists
- accessibility basics are not broken

Do not polish a structurally wrong screen. Rebuild structure first.

## Step 2: Identify Hierarchy

Name:

- first thing user should notice
- second thing user should notice
- primary action
- secondary action
- supporting metadata
- optional information

If everything is important, nothing is.

## Step 3: Remove Fake Polish

Remove or reduce:

- decorative gradients
- stacked shadows
- unnecessary cards
- extra borders
- random dividers
- animated decoration
- glass where content needs readability
- duplicate icons
- repeated labels

## Step 4: Use Native Hierarchy

Prefer:

- semantic text styles
- section grouping
- system backgrounds
- SF Symbols
- primary/secondary foreground styles
- native row/accessory patterns
- native button styles

## Step 5: Tune Typography

Check:

- screen title
- section title
- row title
- row subtitle
- metadata
- empty/error copy

Rules:

- use semantic type
- no tiny essential text
- no all-caps micro labels
- no hard-coded body fonts by default
- avoid centered body copy
- allow multiline where needed

## Step 6: Tune Spacing

Use:

- native list/form spacing
- `.padding()` where system default fits
- named spacing constants
- 4 pt rhythm

Reject:

- arbitrary magic numbers
- spacing as decoration
- forced fixed frames
- random `Spacer()` heights

## Step 7: Tune Grouping

Prefer:

- `Section`
- `LabeledContent`
- native separators
- grouped backgrounds
- concise rows

Reject:

- cards around everything
- cards inside cards
- shadows around rows
- border boxes replacing grouping

## Step 8: Tune Color

Use:

- `.primary`
- `.secondary`
- `.tint`
- semantic status colors
- system backgrounds

Reject:

- neutral web palette by default
- too many accents
- low-contrast metadata
- hard-coded light/dark colors
- color-only meaning

## Step 9: Tune Empty/Loading/Error

Empty state:

- symbol
- one sentence
- one action

Loading:

- redacted skeleton when shape known
- progress only when blocking

Error:

- explanation
- recovery action
- retry when useful

## Step 10: Reductionist Pass

Ask for every element:

Would the user lose meaning, structure, navigation, or feedback if this disappeared?

If no, remove it.

## Output Template

```md
## Hierarchy Diagnosis

...

## Removed Noise

- ...

## Polish Changes

- Typography:
- Spacing:
- Grouping:
- Color:
- States:

## Revised SwiftUI

\`\`\`swift
...
\`\`\`

## Reductionist Pass

...
```

## Failure Conditions

Do not call it polished if:

- hierarchy depends on gradients
- content depends on glass
- accessibility gets worse
- text truncates at large sizes
- the screen still reads like a SaaS dashboard
- visual noise remains because it "looks cool"
