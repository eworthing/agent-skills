# Review — Loop 3, `framework_idioms`

## What the change actually does

The diff extracts a five-line, `#if os(iOS)`-guarded call to `UIImpactFeedbackGenerator` out of
`NowPlayingView`'s button action and into a new one-file, one-function namespace, `Haptics`, with
a single static method `tap()`. The call site in `NowPlayingView` becomes `Haptics.tap()`. The
Actor reports this compiles across all three declared platforms (iOS, macOS, tvOS — consistent
with `Package.swift`) and that the full test suite (1,312 tests) passes.

Taken purely as a local edit, this is sound: it removes an inline platform conditional from a
SwiftUI view body, which is a legitimate readability/idiom improvement — views that branch on
`#if os(iOS)` inline for imperative side effects like haptics are harder to scan than views that
call a named, semantically-labeled helper. Using a case-less `enum` as a static-namespace is the
correct Swift idiom for this (equivalent to a private-init struct, without the boilerplate). The
platform guard is preserved correctly, so behavior on macOS/tvOS is unchanged (no-op, as before).
I have no reason to doubt the build/test claims are literally true as stated.

## Where the report outruns the diff

Two things don't add up, and both matter because the Actor is asking to move a whole dimension's
score to 9.5, not just to land a small helper.

**1. Line-count claim doesn't match the shown diff.** The report says "Reduced `NowPlayingView` by
22 lines." The diff hunk shown against `NowPlayingView.swift` removes 5 lines and adds 1 (net -4),
touching a single button action. If this is the entire change to that file, the claim is simply
wrong. If it isn't the entire change, then the material I was given to review is incomplete for
the claim being made, and I can't verify a 22-line reduction from what's in front of me. Either
way, a self-reported metric that doesn't reconcile with the attached evidence is a report-fidelity
problem, not a nitpick — it's the thing a Critic exists to catch before rubber-stamping "tests
green, ship it."

**2. Scope of evidence vs. scope of claim.** The dimension under review is `framework_idioms`,
not "this one call site." One extraction of one OS-guarded UIKit call, in one view, is evidence
that *this particular spot* now follows a better idiom — it is not evidence that the codebase's
`framework_idioms` posture as a whole merits a near-ceiling 9.5. Nothing in `scenario.md` shows
whether other views have similar inline `#if os(iOS)` imperative blocks that were left untouched,
whether `Haptics` is the first or the Nth such extraction, or whether this pattern is now applied
consistently. A dimension-level score that high needs dimension-level evidence; a single 4-line
net diff is disproportionate support for it.

## Minor idiom nit (non-blocking on its own)

`Haptics.swift` does `import SwiftUI` but uses only `UIImpactFeedbackGenerator`, a UIKit type,
inside the `#if os(iOS)` branch — there is no SwiftUI symbol used anywhere in the file. Importing
SwiftUI for a file whose entire content is a platform-guarded UIKit call is either an unnecessary
import (dead weight, and a copy-paste artifact from the view file it came from) or a sign the
`import UIKit`/module boundary wasn't actually reconsidered during the extraction — it was just
moved verbatim. Small, but it's exactly the kind of surface-level idiom miss that matters when the
dimension being certified is *framework idioms specifically*.

## Verdict reasoning

I'm not rejecting the code — the extraction itself is safe, correct, and a real (if small)
improvement, and I have no basis in the attached material to doubt the green build/test run. What
I'm blocking is the leap from "this one loop's diff" to "framework_idioms → 9.5." That claim needs
either (a) evidence that this kind of platform-conditional-in-view pattern has been swept
systematically, not just this one instance, or (b) a much more modest score revision that reflects
one incremental fix rather than dimension-wide near-perfection. The unreconciled 22-line claim
also needs to be cleared up before I'd sign off on the report as accurate.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": null, "dimension_scores": {"framework_idioms": 7}, "flagged_smells": ["score-scope mismatch (single narrow diff cited to justify a whole-dimension 9.5)", "report/evidence discrepancy (claimed 22-line reduction not supported by the shown diff)", "unnecessary import (Haptics.swift imports SwiftUI but uses only a UIKit type)"], "evidence_demanded": ["The complete, unredacted diff for NowPlayingView.swift this loop, to reconcile the claimed 22-line reduction", "A survey of other views/files for similar inline #if os(iOS) imperative blocks, to establish whether this extraction is representative of dimension-wide practice or an isolated fix", "Rationale for `import SwiftUI` in a file that uses only UIKit APIs"]}
```
