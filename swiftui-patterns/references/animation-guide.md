# SwiftUI Animation Guide

Comprehensive animation reference for iOS apps.

## Table of Contents

- [Implicit vs Explicit Animations](#implicit-vs-explicit-animations)
- [Animation Placement](#animation-placement)
- [Selective Animation](#selective-animation)
- [Timing Curves](#timing-curves)
- [Animation Performance](#animation-performance)
- [Disabling Animations](#disabling-animations)
- [Transitions](#transitions)
- [Custom Transitions](#custom-transitions)
- [The Animatable Protocol](#the-animatable-protocol)
- [Phase Animations](#phase-animations)
- [Keyframe Animations](#keyframe-animations)
- [Transactions](#transactions)
- [Completion Handlers](#completion-handlers)
- [Debugging](#debugging)

---

## Implicit vs Explicit Animations

### Implicit: `.animation(_:value:)`

Animate when a specific value changes. Scoped to modifiers above in the view tree.

```swift
// GOOD - uses value parameter
Rectangle()
    .frame(width: isExpanded ? 200 : 100, height: 50)
    .animation(.spring, value: isExpanded)

// BAD - deprecated, animates all changes unexpectedly
Rectangle()
    .frame(width: isExpanded ? 200 : 100, height: 50)
    .animation(.spring)  // Deprecated!
```

### Explicit: `withAnimation`

For event-driven state changes (button taps, gestures).

```swift
Button("Toggle") {
    withAnimation(.spring) {
        isExpanded.toggle()
    }
}
```

### When to Use Which

- **Implicit**: Animations tied to specific value changes, precise view-tree scope
- **Explicit**: Event-driven animations (button taps, gestures, callbacks)

---

## Animation Placement

Place animation modifiers **after** the properties they animate:

```swift
// GOOD - animation after properties
Rectangle()
    .frame(width: isExpanded ? 200 : 100, height: 50)
    .foregroundStyle(isExpanded ? .blue : .red)
    .animation(.default, value: isExpanded)  // Animates both

// BAD - animation before properties
Rectangle()
    .animation(.default, value: isExpanded)  // Too early!
    .frame(width: isExpanded ? 200 : 100, height: 50)
```

---

## Selective Animation

Use multiple animation modifiers or scoped animation blocks to animate only specific properties:

```swift
// Multiple modifiers - animate size but not color
Rectangle()
    .frame(width: isExpanded ? 200 : 100, height: 50)
    .animation(.spring, value: isExpanded)  // Animate size
    .foregroundStyle(isExpanded ? .blue : .red)
    .animation(nil, value: isExpanded)  // Don't animate color

// iOS 17+ scoped animation block
Rectangle()
    .foregroundStyle(isExpanded ? .blue : .red)  // Not animated
    .animation(.spring) {
        $0.frame(width: isExpanded ? 200 : 100, height: 50)  // Animated
    }
```

---

## Timing Curves

### Built-in Curves

| Curve | Use Case | Notes |
|-------|----------|-------|
| `.spring` | Interactive elements, most UI | Default choice |
| `.easeInOut` | Appearance changes | Smooth feel |
| `.bouncy` | Playful feedback | `Animation.bouncy` (iOS 13+), `Spring.bouncy` (iOS 17+) |
| `.linear` | Progress indicators only | Feels robotic for UI |

**`.bouncy` usage:**
```swift
// CORRECT - Animation.bouncy (available iOS 13+)
withAnimation(.bouncy) { flag.toggle() }
.animation(.bouncy, value: flag)

// CORRECT - with parameters (iOS 17+)
withAnimation(.bouncy(duration: 0.4, extraBounce: 0.2)) { flag.toggle() }

// ALSO CORRECT - via Spring type (iOS 17+)
withAnimation(.spring(.bouncy)) { flag.toggle() }
```

### Modifiers

```swift
.animation(.default.speed(2.0), value: flag)  // 2x faster
.animation(.default.delay(0.5), value: flag)  // Delayed start
.animation(.default.repeatCount(3, autoreverses: true), value: flag)
```

---

## Animation Performance

### Prefer Transforms Over Layout

```swift
// GOOD - GPU accelerated
Rectangle()
    .scaleEffect(isActive ? 1.5 : 1.0)
    .offset(x: isActive ? 50 : 0)
    .rotationEffect(.degrees(isActive ? 45 : 0))
    .animation(.spring, value: isActive)

// BAD - layout changes are expensive
Rectangle()
    .frame(width: isActive ? 150 : 100, height: isActive ? 150 : 100)
    .padding(isActive ? 50 : 0)
```

### Narrow Animation Scope

```swift
// GOOD - scoped to specific subview
VStack {
    HeaderView()
    ExpandableContent(isExpanded: isExpanded)
        .animation(.spring, value: isExpanded)
    FooterView()
}

// BAD - animation at root
VStack { /* ... */ }
    .animation(.spring, value: isExpanded)  // Animates everything
```

### Gate Hot Paths

```swift
// GOOD - only animate when crossing threshold
.onPreferenceChange(ScrollOffsetKey.self) { offset in
    let shouldShow = offset.y < -50
    if shouldShow != showTitle {
        withAnimation(.easeOut(duration: 0.2)) {
            showTitle = shouldShow
        }
    }
}

// BAD - animating every scroll change
.onPreferenceChange(ScrollOffsetKey.self) { offset in
    withAnimation { self.offset = offset.y }  // Fires constantly!
}
```

---

## Disabling Animations

```swift
// Disable with transaction
Text("Count: \(count)")
    .transaction { $0.animation = nil }

// Disable from parent context
DataView()
    .transaction { $0.disablesAnimations = true }
```

---

## Transitions

Transitions animate views being **inserted or removed** from the render tree (not property changes on existing views).

### Critical: Animation Context Must Be Outside

```swift
// GOOD - animation outside conditional
VStack {
    if showDetail {
        DetailView()
            .transition(.slide)
    }
}
.animation(.spring, value: showDetail)

// GOOD - explicit animation
Button("Toggle") {
    withAnimation(.spring) { showDetail.toggle() }
}
if showDetail {
    DetailView()
        .transition(.scale.combined(with: .opacity))
}

// BAD - animation inside conditional (removed with view!)
if showDetail {
    DetailView()
        .transition(.slide)
        .animation(.spring, value: showDetail)  // Won't work on removal!
}
```

### Built-in Transitions

| Transition | Effect |
|------------|--------|
| `.opacity` | Fade in/out (default) |
| `.scale` | Scale up/down |
| `.slide` | Slide from leading edge |
| `.move(edge:)` | Move from specific edge |

### Combining and Asymmetric

```swift
// Parallel combination
.transition(.slide.combined(with: .opacity))

// Different insert/remove animations
.transition(.asymmetric(
    insertion: .scale.combined(with: .opacity),
    removal: .move(edge: .bottom).combined(with: .opacity)
))
```

### Identity and Transitions

View identity changes (`.id()` changes, conditional branches) trigger transitions, not property animations:

```swift
// Triggers TRANSITION - .id() changes identity
Rectangle().id(flag).transition(.scale)

// Triggers PROPERTY ANIMATION - same view, same identity
Rectangle().frame(width: isExpanded ? 200 : 100)
    .animation(.spring, value: isExpanded)
```

---

## Custom Transitions

### iOS 17+ Transition Protocol (Preferred)

```swift
struct BlurTransition: Transition {
    var radius: CGFloat

    func body(content: Content, phase: TransitionPhase) -> some View {
        content
            .blur(radius: phase.isIdentity ? 0 : radius)
            .opacity(phase.isIdentity ? 1 : 0)
    }
}

// Usage
.transition(BlurTransition(radius: 10))
```

### Pre-iOS 17 (ViewModifier + AnyTransition)

```swift
struct BlurModifier: ViewModifier {
    var radius: CGFloat
    func body(content: Content) -> some View {
        content.blur(radius: radius)
    }
}

extension AnyTransition {
    static func blur(radius: CGFloat) -> AnyTransition {
        .modifier(active: BlurModifier(radius: radius), identity: BlurModifier(radius: 0))
    }
}
```

---

## The Animatable Protocol

Enables custom property interpolation during animations.

### `@Animatable` Macro (Preferred)

The `@Animatable` macro automatically synthesizes `Animatable` conformance and
the `animatableData` property. Use `@AnimatableIgnored` for properties that should
not be animated (Booleans, integers, non-interpolatable types).

```swift
@Animatable
struct ShakeModifier: ViewModifier {
    var shakeCount: Double
    @AnimatableIgnored var color: Color

    func body(content: Content) -> some View {
        content.offset(x: sin(shakeCount * .pi * 2) * 10)
    }
}

@Animatable
struct ComplexModifier: ViewModifier {
    var scale: CGFloat
    var rotation: Double
    @AnimatableIgnored var label: String

    func body(content: Content) -> some View {
        content.scaleEffect(scale).rotationEffect(.degrees(rotation))
    }
}
```

### Manual Implementation (Legacy)

Only use manual `animatableData` if you need custom interpolation logic:

```swift
struct ShakeModifier: ViewModifier, Animatable {
    var shakeCount: Double

    var animatableData: Double {
        get { shakeCount }
        set { shakeCount = newValue }
    }

    func body(content: Content) -> some View {
        content.offset(x: sin(shakeCount * .pi * 2) * 10)
    }
}
```

**Missing `animatableData` = silent failure.** The animation jumps to its final value instead of interpolating.

### Multiple Properties with AnimatablePair (Legacy)

Only needed with manual implementation. The `@Animatable` macro handles this automatically.

```swift
struct ComplexModifier: ViewModifier, Animatable {
    var scale: CGFloat
    var rotation: Double

    var animatableData: AnimatablePair<CGFloat, Double> {
        get { AnimatablePair(scale, rotation) }
        set {
            scale = newValue.first
            rotation = newValue.second
        }
    }

    func body(content: Content) -> some View {
        content.scaleEffect(scale).rotationEffect(.degrees(rotation))
    }
}

// For 3+ properties, nest: AnimatablePair<AnimatablePair<A, B>, C>
```

---

## Phase Animations

Cycle through discrete phases automatically. Each phase change is a separate animation.

### Basic Usage

```swift
// Triggered animation
Button("Shake") { trigger += 1 }
    .phaseAnimator([0.0, -10.0, 10.0, -5.0, 0.0], trigger: trigger) { content, offset in
        content.offset(x: offset)
    }

// Infinite loop (no trigger)
Circle()
    .phaseAnimator([1.0, 1.2, 1.0]) { content, scale in
        content.scaleEffect(scale)
    }
```

### Enum Phases (Recommended)

```swift
enum BouncePhase: CaseIterable {
    case initial, up, down, settle
    var scale: CGFloat {
        switch self {
        case .initial: 1.0
        case .up: 1.2
        case .down: 0.9
        case .settle: 1.0
        }
    }
}

Circle()
    .phaseAnimator(BouncePhase.allCases, trigger: trigger) { content, phase in
        content.scaleEffect(phase.scale)
    }
```

### Custom Timing Per Phase

```swift
.phaseAnimator([0, -20, 20], trigger: trigger) { content, offset in
    content.offset(x: offset)
} animation: { phase in
    switch phase {
    case -20: .spring(.bouncy)
    case 20: .linear
    default: .smooth
    }
}
```

---

## Keyframe Animations

Precise timing control with multiple synchronized tracks running in parallel.

```swift
struct AnimationValues {
    var scale: CGFloat = 1.0
    var verticalOffset: CGFloat = 0
}

Button("Bounce") { trigger += 1 }
    .keyframeAnimator(initialValue: AnimationValues(), trigger: trigger) { content, value in
        content
            .scaleEffect(value.scale)
            .offset(y: value.verticalOffset)
    } keyframes: { _ in
        KeyframeTrack(\.scale) {
            SpringKeyframe(1.2, duration: 0.15)
            SpringKeyframe(0.9, duration: 0.1)
            SpringKeyframe(1.0, duration: 0.15)
        }
        KeyframeTrack(\.verticalOffset) {
            LinearKeyframe(-20, duration: 0.15)
            LinearKeyframe(0, duration: 0.25)
        }
    }
```

### Keyframe Types

| Type | Behavior |
|------|----------|
| `CubicKeyframe` | Smooth interpolation |
| `LinearKeyframe` | Straight-line interpolation |
| `SpringKeyframe` | Spring physics |
| `MoveKeyframe` | Instant jump (no interpolation) |

### KeyframeTimeline for Testing

```swift
let timeline = KeyframeTimeline(initialValue: AnimationValues()) {
    KeyframeTrack(\.scale) {
        CubicKeyframe(1.2, duration: 0.25)
        CubicKeyframe(1.0, duration: 0.25)
    }
}
let midpoint = timeline.value(time: 0.25)
```

---

## Transactions

The underlying mechanism for all SwiftUI animations.

```swift
// withAnimation is shorthand for withTransaction
withAnimation(.default) { flag.toggle() }

// Equivalent explicit transaction
var transaction = Transaction(animation: .default)
withTransaction(transaction) { flag.toggle() }
```

### Animation Precedence

**Implicit animations override explicit** (later in view tree wins):

```swift
Button("Tap") {
    withAnimation(.linear) { flag.toggle() }
}
.animation(.spring(.bouncy), value: flag)  // .bouncy wins!
```

### Custom Transaction Keys (iOS 17+)

```swift
struct ChangeSourceKey: TransactionKey {
    static let defaultValue: String = "unknown"
}

extension Transaction {
    var changeSource: String {
        get { self[ChangeSourceKey.self] }
        set { self[ChangeSourceKey.self] = newValue }
    }
}

// Use in view tree
.transaction { t in
    t.animation = t.changeSource == "server" ? .smooth : .spring(.bouncy)
}
```

---

## Completion Handlers

### With withAnimation (iOS 17+)

```swift
withAnimation(.spring) {
    isExpanded.toggle()
} completion: {
    showNextStep = true
}
```

### With Transaction (For Reexecution)

```swift
// Fires on EVERY trigger change
Circle()
    .scaleEffect(bounceCount % 2 == 0 ? 1.0 : 1.2)
    .transaction(value: bounceCount) { transaction in
        transaction.animation = .spring
        transaction.addAnimationCompletion {
            message = "Bounce \(bounceCount) complete"
        }
    }

// Without value parameter, completion only fires ONCE
```

---

## Debugging

```swift
#if DEBUG
// Slow motion for inspection
.animation(.linear(duration: 3.0).speed(0.2), value: isExpanded)
#else
.animation(.spring, value: isExpanded)
#endif
```

### Debug Animatable Values

```swift
struct AnimationDebugModifier: ViewModifier, Animatable {
    var value: Double
    var animatableData: Double {
        get { value }
        set {
            value = newValue
            print("Animation: \(newValue)")
        }
    }
    func body(content: Content) -> some View {
        content.opacity(value)
    }
}
```
