# Critic Review — Loop 3, `framework_idioms`

## Step 1: Inspect current code only

Per Method Step 1, the Actor's report is a claim, not proof — I re-derive from the diff in `scenario.md` rather than adopting `loop_result` at face value.

**What actually changed:** a 4-line, single-call-site `#if os(iOS)` haptics block moved out of `NowPlayingView`'s Play button action into a new `enum Haptics { static func tap() }` in `Sources/Soundboard/Haptics.swift`, with the call site replaced by `Haptics.tap()`.

## Findings

### Finding 1 — Actor's line-count claim is not supported by the diff shown
- **Claim:** The Actor reports "Reduced `NowPlayingView` by 22 lines," but the diff attributes to `NowPlayingView.swift` a mechanical net change of roughly −3 lines (4 lines removed — `#if os(iOS)` / `let generator = …` / `generator.impactOccurred()` / `#endif` — replaced by 1 line, `Haptics.tap()`).
- **Source:** `scenario.md` diff hunk, `Sources/Soundboard/NowPlayingView.swift` (before/after shown above the fence); `loop_result` narrative text quoting "Reduced `NowPlayingView` by 22 lines."
- **Consequence:** Per Meta-Rule 6 ("Honesty beats polish") and the task instruction to independently assess rather than echo the report, an unreconciled order-of-magnitude mismatch between the self-reported delta and the visible diff undermines trust in the rest of the `loop_result` narrative (including the claimed green build/test matrix), and it is exactly the shape of "tidy-looking report, weak evidence" the rubric calls fake-clean reward.
- **Remedy:** Reconcile the claim against the actual diff (either the diff shown is incomplete and a fuller diff should be attached, or the "22 lines" figure is wrong and should be corrected to match reality) before the dimension score is accepted.

### Finding 2 — New `Haptics` Module does not clear the Deletion Test / Friction Proof bar
- **Claim:** `Haptics.tap()` is introduced as a new Module with exactly one caller (the Play button) and no dedicated test cited for the branch.
- **Source:** `Haptics.swift` (whole new file, one static func, one `#if os(iOS)` body); `NowPlayingView.swift` diff hunk shows the single call site; `loop_result` cites only the pre-existing 1,312-test suite in aggregate, with no test named against `Haptics.tap()`.
- **Consequence:** Under the Deletion Test (architecture-rubric.md § Architectural Tests #1), deleting `Haptics` and inlining its body back at the one call site makes the "module" vanish without complexity reappearing anywhere else — N=1, so it has not yet earned Leverage or Locality. Friction Proof Before Seam Recommendation requires source evidence of friction (multiple callers, tests reaching past the interface, seam misplacement) before crediting a new Module; none is shown. Simplify Pressure Test Q5 ("does the product improve — measurably, and by more than the item you are declining") is not satisfied: the actual framework idiom in use (guarded `UIImpactFeedbackGenerator` call) is unchanged, only relocated, so this loop's real contribution to `framework_idioms` is a cosmetic move, not a fixed idiom violation.
- **Consequence severity:** contained and local (Noticeable weakness) — nothing is broken, ownership is clear (the enum is the sole writer of nothing, holds no state), but it does not on its own justify moving `framework_idioms` to the 9.5 anchor.
- **Remedy:** Either cite a second real (existing or concretely planned) call site / a dedicated test at the new interface to establish Leverage, or score this loop as a minor stylistic cleanup rather than a dimension-moving structural fix.

### Finding 3 (Cosmetic) — reliance on SwiftUI's transitive UIKit re-export is unlabeled
- **Claim:** `Haptics.swift` writes `import SwiftUI` only, then references `UIImpactFeedbackGenerator` (a UIKit type) inside the `#if os(iOS)` guard.
- **Source:** `Haptics.swift`, full file body.
- **Consequence:** On iOS this resolves today because SwiftUI's iOS overlay re-exports UIKit, so it is not a compile break — but nothing marks that this file depends on that transitive re-export rather than an explicit import, so a reader (or a future SDK change) has no local signal of the real dependency.
- **Remedy:** Add an explicit `import UIKit` under the same `#if os(iOS)` guard for clarity/robustness. Cosmetic — does not affect the verdict.

## Architectural tests applied
- **Deletion test:** fails to show earned keep (Finding 2) — single caller, no reappearing complexity.
- **Two-adapter rule / Unified Seam Policy:** not applicable — `Haptics` is a concrete static enum, not a protocol-backed Seam with swappable Adapters; no seam-policy violation to cite.
- **Shallow module test:** Interface (`tap()`) ≈ Implementation (4 lines) — shallow, consistent with Finding 2.
- **Cross-platform compile correctness (Meta-Rule 4, risk boundary = `#if os` conditional compilation):** satisfied on the evidence given — the Actor reports building all three declared platform destinations (iOS/macOS/tvOS), which is exactly the executable evidence the meta-rule asks for when a fix touches conditional compilation. This one item in the report is corroborated by the diff's continued platform guard and is not in question.

## Scorecard

`framework_idioms`: the underlying framework usage (guarded haptics API, correct platform gating) is and remains correct. What this loop adds is a relocation whose Leverage is unproven and whose self-report contains an unreconciled factual gap. That combination is enough to withhold the proposed 9.5 this loop, without treating the change as harmful or reverting it.

## Verdict rationale

Nothing here is a runtime-reachable architectural break on a primary flow — this stays well short of "Likely disqualifier." But Findings 1 and 2 are each source-backed, non-cosmetic-on-their-own concerns that together block confident certification of the top anchor for `framework_idioms` this loop. Recommending `conditional`: keep the code (it is not wrong), withhold the 9.5, and require the evidence listed below before re-scoring.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Noticeable weakness", "dimension_scores": {"framework_idioms": 8.5}, "flagged_smells": ["fake-clean reward", "polished shallow structure"], "evidence_demanded": ["Reconcile the claimed '22 lines' NowPlayingView reduction against the diff, which shows roughly -3 lines", "Cite a second real or concretely planned call site for Haptics.tap(), or a test at the new interface, to establish Leverage under the Deletion Test", "Confirm (or add an explicit import UIKit for) Haptics.swift's dependency on UIImpactFeedbackGenerator, since only import SwiftUI is present"]}
```
