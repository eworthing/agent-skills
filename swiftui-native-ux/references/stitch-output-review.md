# Stitch Output Review Rubric

Review every Stitch output before translating it to SwiftUI.

Score each category from 1 to 5.

- 1 = reject or major revision required.
- 3 = usable with revision.
- 5 = strong Apple-native fit.

See `references/anti-web-smells.md` for the full anti-pattern catalogue. This file adds Stitch-specific rejection conditions, a numeric rubric, and a house-rule severity scheme.

## House-rule severity scheme

The CSV at `data/stitch-negative-constraints.csv` carries a `severity` column with two values:

- `hard_reject` — automatic rejection. Do not implement. Revise the Stitch prompt to remove the pattern, or discard the variant.
- `revise` — flag and request a focused fix. May survive if the rest of the design is strong.

This severity scheme is a **house rule**, not part of Apple HIG. HIG describes platform conventions; it does not enumerate Stitch-specific rejection severities. The CSV header does not include this note because comment lines would break `csv.DictReader`. The note lives here instead.

## Rubric

### Native Apple Feel

5:

- Looks consistent with modern iOS/iPadOS app structure.
- Uses restrained hierarchy, native spacing, and familiar controls.

3:

- Some native elements, but mixed with generic web visual language.

1:

- Looks like a web dashboard, SaaS page, Material app, or Tailwind template.

### Navigation / Container Fit

5:

- Clearly maps to SwiftUI containers like NavigationStack, NavigationSplitView, TabView, List, Form, sheet, inspector, or toolbar.

3:

- Mostly mappable, but has unnecessary custom chrome.

1:

- Arbitrary floating div layout with no native equivalent.

### iPhone Ergonomics

5:

- Compact, single-column, reachable, safe-area aware, touch-friendly.

3:

- Usable, but dense or slightly stretched.

1:

- Requires mouse precision, uses tiny tap targets, hover affordances, or multi-column dashboard layout.

### iPad Adaptation

5:

- Uses regular width intelligently with sidebar/detail, inspector, or multi-pane layout.

3:

- Adds some width-aware layout but still feels mobile-first.

1:

- Just a stretched iPhone screen.

### Information Hierarchy

5:

- Primary user goal is obvious.
- Supporting information is clearly secondary.
- Visual weight matches task importance.

3:

- Understandable but visually noisy.

1:

- Everything competes equally or decorative elements dominate.

### Accessibility Resilience

5:

- Likely to survive Dynamic Type, VoiceOver order, Reduce Motion, Reduce Transparency, Increase Contrast, and light/dark mode.

3:

- Mostly accessible but has risks needing implementation review.

1:

- Fixed-height text, low contrast, tiny labels, transparency-dependent readability, color-only meaning, or motion-dependent meaning.

### Liquid Glass Restraint

Score against `references/liquid-glass.md`. Authoritative material placement lives there; this rubric category enforces it.

5:

- Used only for bars, overlays, controls, or accessory surfaces with clear fallback.

3:

- Some decorative material use, but not catastrophic.

1:

- Glass content cards, glass-on-glass, transparent dense text, or full-screen glass background.

### Anti-Web-Smell Pass

5:

- No web dashboard, hero, landing page, SaaS, Material, Tailwind, or right-rail chatbot patterns.

3:

- Minor web residue.

1:

- Strong web/SaaS/Material identity.

### SwiftUI Implementability

5:

- Can be implemented with standard SwiftUI containers and modifiers.

3:

- Requires some custom layout but remains reasonable.

1:

- Requires pixel-perfect absolute positioning, custom nav/tab bars, complex GeometryReader layout, or DOM-like nesting.

### State Coverage

5:

- Shows or clearly accommodates loaded, empty, loading, error, and permission/offline states where relevant.

3:

- Happy path plus one alternate state.

1:

- Happy path only when states were requested.

## Automatic Rejection Conditions

Reject or revise immediately if any are present. These echo the 10 non-negotiable rules from `workflows/stitch-design-handoff.md` plus the `hard_reject` rows of `data/stitch-negative-constraints.csv`:

- Material Floating Action Button.
- Hamburger menu on iPhone.
- Custom tab bar.
- Custom navigation bar.
- Dashboard grid as primary iPhone structure.
- Hero CTA inside app workflow.
- Website header/footer/breadcrumbs.
- Glass content cards.
- Glass-on-glass.
- Decorative gradient blob background.
- Tiny gray essential text.
- Hover-only affordances.
- Right-rail chatbot on iPhone.
- iPad design is only a stretched iPhone layout.
- Missing empty/error states when requested.
- Essential meaning conveyed only by color.
- Fixed-height text containers likely to break Dynamic Type.

Also reject:

- Stitch HTML/CSS hierarchy ported verbatim into SwiftUI view tree (house rule — no HIG rule against it; SwiftUI-implementability rationale).

## Review Output Format

When reviewing, produce:

```
Overall decision: accept / revise / reject

Scores:
- Native Apple feel:
- Navigation/container fit:
- iPhone ergonomics:
- iPad adaptation:
- Information hierarchy:
- Accessibility resilience:
- Liquid Glass restraint:
- Anti-web-smell pass:
- SwiftUI implementability:
- State coverage:

Fast-fail issues:
- ...

Accepted visual ideas:
- ...

Required Stitch revision prompt:
- ...

SwiftUI translation notes:
- ...
```
