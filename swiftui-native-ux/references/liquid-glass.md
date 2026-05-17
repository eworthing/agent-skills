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

## Minimal Examples

Scope: these snippets show *where* glass belongs in iOS 26 SwiftUI. For full API surface (`GlassEffectContainer`, `glassEffectID` morph, tint/interactive variants, layer-order rules), defer to `swiftui-expert-skill` `references/liquid-glass.md`.

### Floating Toolbar / Control Bar

```swift
HStack(spacing: 12) {
    Button(action: previous) { Image(systemName: "backward.fill") }
    Button(action: playPause) { Image(systemName: "play.fill") }
    Button(action: next) { Image(systemName: "forward.fill") }
}
.padding(.horizontal, 20)
.padding(.vertical, 12)
.glassEffect(in: .capsule)
.padding(.bottom, 24)
```

Reduce Transparency variant (system swaps material for solid automatically; no manual branching needed when using `.glassEffect`). Verify with the Accessibility Inspector's Reduce Transparency toggle that the bar stays legible.

### Map / Image Overlay Controls

```swift
ZStack(alignment: .topTrailing) {
    Map(position: $position)
        .ignoresSafeArea()

    VStack(spacing: 8) {
        Button(action: recenter) { Image(systemName: "location.fill") }
        Button(action: toggleLayers) { Image(systemName: "square.3.layers.3d") }
    }
    .padding(8)
    .glassEffect(in: .rect(cornerRadius: 14))
    .padding(.trailing, 16)
    .padding(.top, 16)
}
```

Glass sits on top of content. The control cluster — not the map — carries the glass.

### Tab Bar Background (system-provided)

```swift
TabView {
    LibraryView().tabItem { Label("Library", systemImage: "books.vertical") }
    SearchView().tabItem  { Label("Search",  systemImage: "magnifyingglass") }
    ProfileView().tabItem { Label("Profile", systemImage: "person.crop.circle") }
}
```

Do not re-apply `.glassEffect()` to the tab bar — the system already does. Stacking glass on glass is the most common regression.

### Anti-Pattern: Glass on Content

```swift
// REJECT — glass on a reading card.
VStack(alignment: .leading) {
    Text(article.title).font(.title3.bold())
    Text(article.body)
}
.padding(16)
.glassEffect()  // ✗ violates "glass is for controls, not content"
```

Use a solid system background (`.background(.regularMaterial)` only if the card sits over imagery; otherwise plain `Color(.secondarySystemBackground)`).

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
