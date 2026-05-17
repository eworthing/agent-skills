# Liquid Glass

Use this reference when applying, reviewing, or removing Liquid Glass and material effects.

## Core Principle

Liquid Glass is a functional layer for controls and navigation, not a decorative texture for content.

Content must remain readable before glass is added.

## Where Liquid Glass Belongs

Prefer Liquid Glass or system material effects for:

- toolbars
- tab bars
- sidebars
- navigation layers
- floating controls
- accessory surfaces
- transient controls over content
- compact controls that need to feel physically layered

Use glass to clarify an interactive layer above content.

## Where Liquid Glass Does Not Belong

Reject Liquid Glass for:

- content cards
- list rows
- dense reading areas
- full-screen backgrounds
- dashboard tiles
- form fields
- long text
- table rows
- ordinary grouped settings
- decorative panels
- glass-on-glass stacks

If the user must read it, do not make glass the thing carrying readability.

## Readability Rule

Never blur content purely to make a control readable.

If glass does not stand out:

- increase opacity
- use a tinted/frosted variant
- use a solid system background
- move the control
- simplify the background
- reduce visual noise beneath it

Do not sacrifice content to rescue chrome.

## Reduce Transparency First

Design the Reduce Transparency variant as the ground truth.

The default glass treatment is an enhancement.

Ask:

- Does the UI still make sense without transparency?
- Is hierarchy still clear?
- Are controls still visible?
- Is content still readable?
- Is selection still obvious?

## Contrast

Text over material must remain readable over worst expected backgrounds.

Prefer:

- `.primary` text
- body weight or stronger for readable content
- thicker material when needed
- solid background when text matters
- protective overlay for text over imagery

Reject:

- thin text over glass
- gray text over glass
- ultra-light type over dark material
- text over busy imagery without overlay
- assuming the system will rescue every contrast failure

## Motion

Liquid Glass may imply motion, morphing, or physicality.

Use motion only when it clarifies state or transition.

Prefer:

- short transitions
- user-triggered transitions
- Reduce Motion fallback
- no animation dependency for comprehension

Reject:

- looping glass shimmer
- bouncing controls without meaning
- elastic motion on routine tasks
- animation blocking interaction

## Glass Coordination

When multiple glass elements are near each other, coordinate them.

Prefer:

- one coherent glass layer
- grouped morphing where appropriate
- visual separation between content and controls

Reject:

- stacked glass panes
- overlapping translucent controls
- glass elements fighting for attention
- random glass badges

## Shapes

Prefer:

- capsules for touch controls
- rounded rectangles for dense desktop-like controls
- shapes that respect concentricity
- system button/control styles when possible

Reject:

- arbitrary glass blobs
- mismatched radii
- decorative glass ornaments

## Safe Uses

Good uses:

- floating playback/control bar
- compact tab bar
- toolbar background
- sidebar material
- map overlay controls
- camera control cluster
- temporary accessory palette

Risky uses:

- translucent form background
- glass card grid
- glass settings panels
- glass detail page
- glass behind paragraphs
- glass over photos with text

## Liquid Glass Review Checklist

Ask:

- Is glass on a control/navigation layer?
- Is content still readable?
- Does the Reduce Transparency variant work?
- Is contrast safe over worst-case background?
- Is there any glass-on-glass?
- Is text weight strong enough?
- Does motion honor Reduce Motion?
- Would solid background be clearer?
- Is glass doing structural work or decoration?
