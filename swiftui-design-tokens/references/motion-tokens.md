# Motion Tokens

Motion tokens centralize animation timing so interactions feel consistent
across the app. Define them once in your `DesignTokens.swift` and reference
the tokens from view code -- never inline raw `.spring(...)` or
`.easeOut(duration:)` calls in views.

## Timed Animations

```swift
enum Motion {
    static let fast = Animation.easeOut(duration: 0.12)      // Quick transitions
    static let focus = Animation.easeOut(duration: 0.15)     // Focus changes
    static let emphasis = Animation.easeOut(duration: 0.20)  // Emphasis effects
    static let standard = Animation.easeOut(duration: 0.20)
}
```

Pick `fast` for micro-interactions (chip selection, small reveals),
`focus`/`emphasis` for state changes, and `standard` for most general view
transitions.

## Spring Animations

Springs feel more natural for physical interactions (drag, drop, focus
movement, overlay appearance):

```swift
extension Motion {
    static let spring = Animation.spring(response: 0.30, dampingFraction: 0.8)

    // Drag interaction springs
    static let lift = Animation.spring(response: 0.35, dampingFraction: 0.9)   // Pickup (high damping)
    static let drop = Animation.spring(response: 0.4, dampingFraction: 0.85)   // Drop (slight settle)
}
```

Higher damping (`0.9+`) feels controlled and precise -- right for pickup.
Slightly lower damping (`0.85`) gives a small natural settle on drop.

### Platform-Specific Focus Springs

tvOS users navigate by focus, so the platform expects a playful spring on
focus change. iOS/macOS focus indicators should be subtler:

```swift
extension Motion {
#if os(tvOS)
    static let focusSpring = Animation.bouncy(duration: 0.3, extraBounce: 0.1)
#else
    static let focusSpring = Animation.spring(response: 0.25, dampingFraction: 0.85)
#endif
}
```

`.bouncy()` is iOS 17 / tvOS 17+. On older OS versions, fall back to
`.spring(response: 0.3, dampingFraction: 0.75)` for a similar feel.

## Reduce Motion Alternatives

When `@Environment(\.accessibilityReduceMotion)` is true, replace springs
with short fades. Define dedicated tokens so view code doesn't need a
ternary at every animation site:

```swift
extension Motion {
    static let liftReduced = Animation.easeOut(duration: 0.15)
    static let dropReduced = Animation.easeOut(duration: 0.15)
}
```

Usage:

```swift
@Environment(\.accessibilityReduceMotion) private var reduceMotion

.animation(
    reduceMotion ? Motion.liftReduced : Motion.lift,
    value: isDragging
)
```

## Motion Token Selection Guide

| Interaction         | Normal              | Reduce Motion         |
|---------------------|---------------------|-----------------------|
| Drag pickup         | `Motion.lift`       | `Motion.liftReduced`  |
| Drag drop           | `Motion.drop`       | `Motion.dropReduced`  |
| Focus change        | `Motion.focusSpring`| `Motion.focus`        |
| Overlay appear      | `Motion.spring`     | `Motion.fast`         |
| Chip / row toggle   | `Motion.fast`       | `Motion.fast`         |
| Modal present       | `Motion.spring`     | `Motion.standard`     |

The Reduce Motion column should never use a spring -- springs are what the
accessibility setting is asking the app to avoid.

## Anti-Patterns

```swift
// WRONG -- inline animation, scattered timing
.animation(.spring(response: 0.32, dampingFraction: 0.82), value: x)
.animation(.easeOut(duration: 0.13), value: y)

// CORRECT -- named token, single source of truth
.animation(Motion.spring, value: x)
.animation(Motion.fast, value: y)
```

```swift
// WRONG -- no Reduce Motion variant
.animation(Motion.lift, value: isDragging)

// CORRECT
.animation(reduceMotion ? Motion.liftReduced : Motion.lift, value: isDragging)
```

For SwiftUI animation mechanics (implicit vs explicit animations,
`Animatable`, transitions, phase/keyframe animators) see the
`swiftui-patterns` skill -- this file is only the token catalog and
selection guide.
