# Critic Review — Loop 3, `framework_idioms`

## Independent re-derivation (Method Step 1)

Per the anchor-to-source rule, this scorecard is derived from the diff and report in
`scenario.md` directly, not from the Actor's framing. The Actor proposes `framework_idioms` →
9.5 on the strength of: extracting a haptic-feedback call out of `NowPlayingView` into a new
`Haptics` enum, guarding the iOS-only `UIImpactFeedbackGenerator` API behind `#if os(iOS)`, and
a green build/test matrix across iOS, macOS, tvOS, plus the iOS Simulator suite.

## Authority Map (Method Step 2)

Nothing mutable is introduced. `Haptics.tap()` is a stateless static call into a hardware API
(`UIImpactFeedbackGenerator`); there is no stored field, no writer/reader pair, no persistence
seam, no async entry point. No state-authority concerns apply here.

## Architectural Tests (rubric §Architectural Tests)

- **Two-Adapter Rule / Unified Seam Policy**: not triggered. `Haptics` is a plain `enum`
  namespace around a static function, not a protocol-backed Interface with Adapters — there is
  nothing to justify under (a) or (b). If it *were* treated as a Seam, (b)(iii) platform
  isolation (hardware-bound API, no test harness) would justify a single Adapter cleanly. Either
  way, no violation.
- **Deletion test**: this is where the case is thin. The diff shows exactly **one** call site
  (`NowPlayingView`'s play button). Deleting `Haptics` and inlining the four-line `#if os(iOS)`
  block back at that one site does not make complexity "vanish across N callers" — it just moves
  four lines to one place. At N=1, the extraction is closer to code organization than to a
  friction-proven module (Method meta-rule 3: seams need proven friction — "callers bounce
  across tiny modules" — not demonstrated here from the evidence given).
- **Cross-platform compile correctness** (Method Step 5, Apple lens): this *is* satisfied. The
  refactor touches `#if os`-gated code and moves it across files, and the Actor's report shows
  build success on all three declared platform destinations (iOS, macOS, tvOS), not just the
  iOS Simulator test run. That is exactly the executable evidence meta-rule 4 asks for when a
  fix crosses a conditional-compilation risk boundary. No finding here.

## Primary finding — Claim/Source mismatch (Evidence Chain)

**Claim**: the Actor's report states "Reduced `NowPlayingView` by 22 lines," implying a
multi-site consolidation across the view.

**Source**: the diff attached (`scenario.md`, the "Diff" section) shows only one edited call
site in `NowPlayingView.swift` — a four-line `#if os(iOS) ... #endif` block replaced by one line
(`Haptics.tap()`). That is a net **-3 lines**, not -22.

**Consequence**: this is a direct instance of what the task instructions and the Method
explicitly warn against — accepting the Actor's report instead of independently verifying
against current source (Method Step 1: "Inspect current code only... require current source
proof"; rubric's *Fake-clean reward* smell: scoring up because a narrative — "the view stays
declarative," a large stated line count — looks tidy while the shown evidence doesn't back it).
Two explanations are possible, and neither clears the loop at 9.5 as currently evidenced:

1. The diff shown is incomplete, and there are more call sites in `NowPlayingView` (and possibly
   elsewhere) that still contain the raw inline `#if os(iOS)` / `UIImpactFeedbackGenerator`
   pattern, not yet migrated to `Haptics.tap()`. If so, that is a live *duplicate-pattern* smell
   (smoke-list: duplicate abstractions) — the codebase would now have two competing idioms for
   the same platform-isolation concern, which is a regression on `framework_idioms`, not a clean
   win.
2. The report's stated impact is simply inflated relative to the actual change made.

Either way, the chain (Claim → Source) does not close on the evidence given, so per the Evidence
Chain rule ("If the chain cannot be shown, downgrade the claim... or omit it") the Actor's
proposed 9.5 cannot be certified as-is. The single shown call site is a genuinely clean,
correctly-guarded, behavior-preserving extraction — that part of the work is sound — but the
loop's own characterization of its scope is unverified and should not be taken at face value.

## Minor cosmetic note

`Haptics.swift` does `import SwiftUI` to reach `UIImpactFeedbackGenerator`, which is a UIKit
type. The idiomatic form is an explicit `import UIKit` (itself guardable, since UIKit doesn't
exist on macOS/tvOS) rather than relying on SwiftUI's transitive re-export. The reported green
iOS build confirms this resolves as written, so it is not blocking — Cosmetic for contest, not
scored down on its own.

## Simplify Pressure Test on the fix itself

Q1–Q4 pass on the evidence shown: it fixes a real (if small) platform-leakage concern, is a
minimally-sized change, adds no duplicate layer, and preserves runtime behavior (same generator
style, same call). Q5 (leverage) is the open question: at the one call site shown, the leverage
is thin; if the Actor's "-22 lines" claim reflects real additional call sites, leverage is much
stronger. This is exactly the gap the evidence-demand below is meant to close.

## Verdict

Conditional. The structural pattern shown (isolating a hardware/platform-bound API behind a
small, correctly `#if os`-guarded helper, validated by a full-matrix build) is a legitimate,
idiomatic fix and would be uncontroversial at a high score on its own. It is not certified at
9.5 because the Actor's own stated impact is not reconcilable with the diff provided, and that
gap could be hiding either an inflated report or un-migrated duplicate call sites — both of
which bear directly on `framework_idioms`. Close the gap and this clears easily; as submitted,
it does not.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "Noticeable weakness",
  "dimension_scores": {"framework_idioms": 9.0},
  "flagged_smells": ["fake-clean reward", "duplicate abstractions"],
  "evidence_demanded": [
    "Full diff or repo-wide grep for UIImpactFeedbackGenerator confirming no remaining call sites still use the raw inline #if os(iOS) pattern outside Haptics.swift",
    "Reconciliation of the reported '-22 lines' NowPlayingView reduction against the actual diff (either the complete diff showing every affected site, or a corrected report)"
  ]
}
```
