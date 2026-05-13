# tvOS Rule Index + Bypass Contexts

Canonical list of all `apple-tvos` headline rules with severity and
*Bypass / N/A* contexts. SKILL.md carries one-liners + a link here;
this file is the source of truth.

Severity:
- **1** — Data loss or focus break. Severity-1 rules have no bypass for
  destructive cases (see tvOS-A02, tvOS-A03).
- **2** — UX regression visible to users.
- **3** — Polish / consistency.

Machine-readable variant: [evals/rules.json](../evals/rules.json).

## Focus Engine — [focus-engine.md](focus-engine.md)

| ID | Rule | Severity |
|---|---|---|
| tvOS-F01 | No `.focusable()` on container wrappers | 1 |
| tvOS-F02 | Pair focusable POD rows with parent `@FocusState` | 1 |
| tvOS-F03 | Scope custom `.animation()` to child content, not focusable view | 2 |
| tvOS-F04 | Use token-based settle delay for focus-driven animations | 2 |
| tvOS-F05 | `ScrollView` needs focusable children to be scrollable | 1 |
| tvOS-F06 | Prefer `.scrollTargetBehavior(.viewAligned)` over `.paging` | 3 |
| tvOS-F07 | Verify focus animations on real Apple TV hardware | 2 |

**tvOS-F01.** No `.focusable()` on container wrappers. Focus stops at
the outer view; children never receive focus.
*Bypass / N/A:* Containers that intentionally act as a single focusable
unit (e.g., a card cluster behaving as one logical button). Use a real
`Button` instead.

**tvOS-F02.** Pair focusable POD rows with parent `@FocusState` to
anchor focus identity against parent redraws.
*Bypass / N/A:* Rows that are not POD (already hold `@State` /
`@Observable`) — SwiftUI tracks identity via the property wrapper.

**tvOS-F03.** Scope custom `.animation()` to child content, not the
focusable element. Custom animation on the focusable view fights the
built-in hover effect.
*Bypass / N/A:* `.animation(nil, ...)` to explicitly disable, or
animations on `@FocusState`-driven properties handled by the system.

**tvOS-F04.** Use token-based settle delay for long focus-change
animations to avoid noise during rapid swiping.
*Bypass / N/A:* Cheap, idempotent focus reactions (e.g., a color tint
change) that cancel cleanly without visible thrash.

**tvOS-F05.** `ScrollView` with no focusable children is unscrollable —
scroll is focus-driven on tvOS.
*Bypass / N/A:* Code branched `#if !os(tvOS)` for iOS-only content;
single-screen content that fits without scrolling.

**tvOS-F06.** Prefer `.scrollTargetBehavior(.viewAligned)` over
`.paging`.
*Bypass / N/A:* True full-screen pager UX (onboarding, slideshow) where
page boundaries are part of the design intent.

**tvOS-F07.** Verify focus animations on real Apple TV hardware —
Simulator does not replicate the hover curve.
*Bypass / N/A:* Animations that do not interact with focus (data-driven
content transitions). Still smoke-test once on hardware before shipping.

## Accessibility — [accessibility.md](accessibility.md)

| ID | Rule | Severity |
|---|---|---|
| tvOS-A01 | Dismiss modals via `.onExitCommand`, not visible Close button | 2 |
| tvOS-A02 | Destructive `confirmationDialog`/`alert` declares Cancel first | 1 |
| tvOS-A03 | Never manually reassert focus via `DispatchQueue.main.asyncAfter` | 1 |
| tvOS-A04 | Hide non-actionable focus helpers with `.accessibilityHidden(true)` | 2 |

**tvOS-A01.** Dismiss modals via `.onExitCommand`, not Close buttons.
Branch visible Close button with `#if !os(tvOS)`.
*Bypass / N/A:* Modals on iOS / iPadOS / macOS in shared code —
`.onExitCommand` also triggers on macOS Escape key (tvOS 13+, macOS
10.15+), no-op on iOS / iPadOS.

**tvOS-A02 (severity-1).** Destructive `confirmationDialog` / `alert`
declares Cancel first. tvOS focus engine puts default focus on first
declared button.
*Bypass / N/A:* Non-destructive confirmations where either choice is
safe. Never bypass for destructive (`role: .destructive`) actions.

**tvOS-A03 (severity-1).** Never manually reassert focus via
`DispatchQueue.main.asyncAfter` — hijacks VoiceOver and Switch Control.
*Bypass / N/A:* None. Use focus containment (`.fullScreenCover()`,
scoped `@FocusState`) instead.

**tvOS-A04.** Hide non-actionable focus helpers
(`Rectangle().fill(.clear)`) with `.accessibilityHidden(true)`, not
`.accessibilityAddTraits(.isButton)`.
*Bypass / N/A:* Helpers that are genuinely actionable (run code on
Select) — model them as a real `Button`.

## Design Regressions — [design-regressions.md](design-regressions.md)

| ID | Rule | Severity |
|---|---|---|
| tvOS-D01 | Use `.fullScreenCover()` for tvOS modals, not `.sheet()` | 1 |
| tvOS-D02 | No glass-on-glass (glass button inside glass-backed modal) | 2 |
| tvOS-D03 | No `.buttonStyle(.plain)` with custom styling on focusable views | 2 |
| tvOS-D04 | Walk tvOS QA checklist before merging | 2 |

**tvOS-D01.** Use `.fullScreenCover()` for tvOS modals, not `.sheet()`.
`.sheet()` focus containment is not reliable on tvOS; assume it leaks
unless verified on hardware for the specific tvOS deployment target.
*Bypass / N/A:* Non-modal pop-overs handled separately; cross-platform
code can use `.sheet()` on iOS branches and `.fullScreenCover()` on
tvOS.

**tvOS-D02.** No glass-on-glass. Glass button (`.buttonStyle(.glass)` /
`.glassProminent`) inside a glass-backed modal or chrome surface
produces muddy double-blur. Use `.bordered` / `.borderedProminent`
inside modal content.
*Bypass / N/A:* Glass surfaces on toolbar / nav bar / tab bar chrome
where the foreground itself is not glass.

**tvOS-D03.** No `.buttonStyle(.plain)` with custom styling on focusable
views. Loses automatic focus-ring management; rings clip against
`ScrollView` containers.
*Bypass / N/A:* Non-focusable content rows (e.g., a row that's never
the focus target — display only) can use `.plain` safely.

**tvOS-D04.** Walk the tvOS QA checklist before merging — toolbar
traversal, default focus on entry, Menu-button dismiss path, no focus
flicker.
*Bypass / N/A:* PRs that touch zero tvOS-rendered code (e.g., backend
data layer; iOS-only feature gated `#if !os(tvOS)`).
