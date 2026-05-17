# Accessibility As Design Quality

Use this reference when generating, reviewing, or auditing SwiftUI UI for accessibility resilience.

## Core Principle

Accessibility is structural design quality, not a checklist added after code generation.

A screen that fails Dynamic Type, VoiceOver, Reduce Motion, Reduce Transparency, localization, or contrast is not polished.

## Design Variants To Consider

Always consider:

- light mode
- dark mode
- large Dynamic Type
- accessibility Dynamic Type
- VoiceOver
- Reduce Motion
- Reduce Transparency
- Increase Contrast
- Bold Text
- Differentiate Without Color
- RTL layout
- text expansion
- narrow iPad windows

## Dynamic Type

Prefer semantic typography.

Use:

- `.font(.body)`
- `.font(.headline)`
- `.font(.subheadline)`
- `.font(.caption)` only for nonessential text
- multiline text where needed
- flexible layout
- `ViewThatFits` when useful

Reject:

- fixed-height rows
- essential tiny text
- hard-coded line limits on primary content
- truncating primary labels
- absolute font sizes without justification

Dynamic Type is an information-architecture test.

If the layout breaks at large sizes, the hierarchy was probably too fragile.

## VoiceOver

VoiceOver order should match user intent.

Prefer:

- meaningful labels
- useful values
- hints only when needed
- grouped accessibility elements when the visual group is one concept
- explicit sort priority only when layout order is misleading

Examples:

```swift
.accessibilityLabel("Delete track")
.accessibilityHint("Removes this track from the board")
```

```swift
.accessibilityElement(children: .combine)
```

Reject:

- image-only buttons without labels
- row content read in nonsense order
- decorative images announced as content
- controls with vague labels like "Button"
- labels that repeat visible text without adding meaning

## Touch Targets

Interactive controls should be at least 44 by 44 pt.

Prefer:

- native controls
- comfortable row heights
- larger tap areas
- `contentShape(Rectangle())` when visual target is smaller than logical target

Reject:

- tiny icon targets
- crowded toolbar icons
- controls that become untappable at large Dynamic Type
- hidden gestures as the only path

## Color And Contrast

Use semantic colors.

Prefer:

- `.primary`
- `.secondary`
- `.tint`
- system backgrounds
- status icon plus text
- contrast checked in light and dark mode

Reject:

- color-only meaning
- low-contrast secondary text carrying essential information
- hard-coded black/white
- text over busy images
- thin text over translucent material

## Dark Mode Is Not Automatically Accessible

Do not assume dark mode helps everyone.

Some users benefit from dark mode. Others experience blur, halation, or fatigue, especially with thin light text on dark or translucent backgrounds.

Prefer:

- support both light and dark
- let the user choose when appropriate
- avoid forcing `.preferredColorScheme(.dark)`
- avoid thin/ultra-light text over dark or glassy material

Reject:

- forced dark mode without a user setting
- "dark mode equals accessibility" reasoning
- low-weight text over glass

## Reduce Transparency

Design the opaque variant first.

When transparency is reduced:

- content should remain readable
- hierarchy should still work
- controls should remain distinct
- glass should not be required to understand structure

Use:

```swift
@Environment(\.accessibilityReduceTransparency) private var reduceTransparency
```

Prefer solid system backgrounds when `reduceTransparency` is true.

Reject UI where blur is required for legibility.

## Reduce Motion

Motion must be optional.

Use:

```swift
@Environment(\.accessibilityReduceMotion) private var reduceMotion
```

When Reduce Motion is enabled:

- remove bounce
- remove parallax
- shorten transitions
- prefer opacity or instant state changes
- avoid looping motion

Reject:

- animation that blocks task completion
- celebratory motion on routine actions
- infinite shimmer
- motion without meaning

## Differentiate Without Color

Status must not depend on color alone.

Prefer:

- symbol plus text
- badge plus label
- pattern plus label
- explicit state text

Reject:

- red/green only distinction
- color-only charts
- color-only validation

## Localization And Text Expansion

Design for text expansion.

Test with:

- German-like longer labels
- Arabic/Hebrew RTL
- multiline labels
- long names
- long dates
- long units

Reject:

- fixed-width buttons
- hard-coded line counts for primary text
- clipped labels
- icons replacing text when clarity matters

## Accessibility Labels For Icon Buttons

Required for icon-only controls.

Example:

```swift
Button {
    refresh()
} label: {
    Image(systemName: "arrow.clockwise")
}
.accessibilityLabel("Refresh")
```

If the visible label is text, do not duplicate unless needed.

## Custom Controls

Custom controls must provide:

- label
- value
- adjustable action when value changes
- traits
- keyboard/pointer consideration when relevant

Example:

```swift
.accessibilityLabel("Volume")
.accessibilityValue("\(volumePercent) percent")
.accessibilityAdjustableAction { direction in
    switch direction {
    case .increment:
        increaseVolume()
    case .decrement:
        decreaseVolume()
    @unknown default:
        break
    }
}
```

Reject custom controls without accessibility behavior.

## Accessibility Review Checklist

Ask:

- Does it work at accessibility Dynamic Type sizes?
- Does VoiceOver read in the right order?
- Are icon-only buttons labeled?
- Is color never the only signal?
- Does it work with Reduce Motion?
- Does it work with Reduce Transparency?
- Does it work in light and dark mode?
- Does it avoid thin text over glass?
- Are touch targets large enough?
- Does localization break the layout?
