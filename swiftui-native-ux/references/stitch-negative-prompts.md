# Negative Prompt Experiments

Use these tests to check whether Stitch constraints are working. Each test starts from a deliberately drift-prone request, predicts what Stitch will likely return, supplies a focused counter-prompt, and names the rubric category that should reject the bad output.

## Test 1: "Modern Dashboard"

**Trigger:** Ask Stitch for a "modern analytics dashboard app."

**Likely bad output:** SaaS grid, web sidebar, desktop charts, drop-shadow cards.

**Counter-prompt:**

> Refactor this into a native iOS app. Replace the dashboard grid with a single-column List of grouped sections. Replace the web sidebar with TabView or NavigationStack. Remove heavy shadows. Use semantic grouped backgrounds.

**Review:** Reject if dashboard grid remains primary on iPhone.

## Test 2: "Glassmorphism App"

**Trigger:** Ask Stitch for a "glassmorphism weather app."

**Likely bad output:** Nested transparent cards, low contrast, decorative blur.

**Counter-prompt:**

> Remove glass from content. Use opaque content surfaces. Apply Liquid Glass only to navigation/toolbars/accessory controls. Preserve 4.5:1 contrast for essential text.

**Review:** Reject glass content cards and glass-on-glass.

## Test 3: "AI Assistant Interface"

**Trigger:** Ask Stitch for an "AI assistant interface."

**Likely bad output:** ChatGPT-like web layout, right rail, sidebar history, floating prompt box.

**Counter-prompt:**

> On iPhone, move assistant into a native sheet. On iPad, use inspector. Remove right rail and web sidebar. Keep main content readable.

**Review:** Reject right rail on iPhone.

## Test 4: "Mobile Productivity App"

**Trigger:** Ask Stitch for a "mobile productivity app."

**Likely bad output:** Material FAB, hamburger menu, Android visual grammar.

**Counter-prompt:**

> Remove the Floating Action Button. Place Add in the top trailing navigation toolbar. Replace hamburger menu with TabView or NavigationStack structure.

**Review:** Reject FAB and hamburger menu.

## Test 5: "Music Player With Beautiful Cards"

**Trigger:** Ask Stitch for a "music player with beautiful cards."

**Likely bad output:** Card carousel, hover states, decorative gradients, overdesigned surfaces.

**Counter-prompt:**

> Use native Now Playing structure. One artwork area, standard controls, readable queue/list. No hover interactions. No glass content cards.

**Review:** Reject hover-only controls and over-carded layout.
