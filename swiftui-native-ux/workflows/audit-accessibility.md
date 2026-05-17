# Workflow: Audit Accessibility

Use this workflow when reviewing SwiftUI UI for accessibility and inclusive design.

## Goal

Treat accessibility as design quality, not a final checklist.

## Step 1: Identify UI Scope

Determine:

- screen/component
- primary task
- interactive elements
- text-heavy areas
- custom controls
- material/glass usage
- animations
- color-coded states
- image/icon usage
- iPhone/iPad targets

## Step 2: Load References

Load:

- `references/accessibility.md`
- `references/liquid-glass.md` if materials/glass are used
- `references/visual-hierarchy.md`
- `references/critique-rubric.md`

## Step 3: Dynamic Type Audit

Check:

- semantic fonts
- multiline support
- fixed row heights
- truncation
- clipped labels
- button width
- layout at accessibility sizes

Flag:

- hard-coded essential text
- tiny metadata
- fixed frames
- line limits on primary content

## Step 4: VoiceOver Audit

Check:

- icon-only button labels
- row reading order
- grouped elements
- custom control values
- hints where needed
- decorative images hidden
- meaningful labels

Flag:

- vague labels
- duplicate noise
- missing values
- inaccessible custom controls

## Step 5: Contrast And Color Audit

Check:

- light mode
- dark mode
- Increase Contrast
- color independence
- text over images
- text over glass
- disabled states

Flag:

- thin text over material
- gray essential text
- color-only meaning
- hard-coded black/white

## Step 6: Motion Audit

Check:

- custom animations
- transitions
- loading shimmer
- completion effects
- scroll effects
- Reduce Motion fallback

Flag:

- looping motion
- motion without meaning
- animation blocking input
- no reduced-motion path

## Step 7: Transparency Audit

Check:

- Liquid Glass
- material backgrounds
- blur
- text over translucent surfaces
- Reduce Transparency fallback

Flag:

- glass carrying hierarchy
- glass behind dense content
- blur required for readability
- no opaque fallback

## Step 8: Interaction Audit

Check:

- tap target size
- gestures
- long-press actions
- swipe actions
- keyboard shortcuts on iPad/Mac
- pointer behavior
- focus order

Flag:

- hover-only controls
- long-press as only key action
- tiny targets
- no keyboard path for repeated commands

## Step 9: Localization Audit

Check:

- long labels
- German-like expansion
- RTL
- dates/numbers/units
- fixed-width buttons
- hard-coded concatenated strings

Flag:

- clipped text
- English-only assumptions
- mirrored layout failures
- icon metaphors that do not localize

## Step 10: Output Findings

Use severity:

- critical
- serious
- moderate
- polish

Template:

```md
## Accessibility Verdict

...

## Findings

### 1. ...
Severity:
Evidence:
Impact:
Fix:

## Required Code Changes

- ...

## Suggested Preview Matrix

- compact
- regular
- dark mode
- accessibility Dynamic Type
- Reduce Motion
- Reduce Transparency
- RTL
```

## Failure Conditions

Do not pass if:

- icon-only buttons lack labels
- primary content clips at large Dynamic Type
- color alone carries status
- glass harms readability
- custom controls lack accessibility values/actions
- motion has no reduced path
- touch targets are too small
