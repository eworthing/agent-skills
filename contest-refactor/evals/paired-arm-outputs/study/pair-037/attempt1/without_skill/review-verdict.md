# Review — Loop 3, `framework_idioms`

## What the diff actually does

The Actor moved an inline, `#if os(iOS)`-guarded haptic call out of `NowPlayingView`'s play
button and into a new `enum Haptics { static func tap() }` in `Sources/Soundboard/Haptics.swift`.
The moved logic is byte-for-byte identical to what was inline before (same
`UIImpactFeedbackGenerator(style: .light)` call, same guard), so this is a pure extract-method
refactor with no behavior change. Build succeeds on all three declared platforms (iOS, macOS,
tvOS) and the existing 1,312-test iOS suite stays green. I take that build/test evidence at face
value — a verbatim move guarded the same way it was guarded before is low-risk, and three green
cross-platform builds is reasonable (if not exhaustive) proof the conditional still compiles out
correctly on macOS/tvOS.

So: the change itself is safe, small, and a genuine improvement over embedding a platform-specific
side effect directly in view body code. That part I'd clear without much argument.

## Where I don't clear it

**1. The 9.5 proposal is a whole-dimension claim resting on single-instance evidence.**
`framework_idioms` is scored as a property of the codebase, not of one call site. This loop shows
exactly one extraction, for exactly one button, in exactly one view. Nothing in `scenario.md`
tells me whether `NowPlayingView` (or any other view in the module) still has other inline
`#if os(...)`-guarded platform calls that weren't touched this loop. A single clean extraction is
consistent with "we fixed the one instance we looked at" and equally consistent with "there are
four more of these scattered through the codebase and we happened to do one." Proposing the
dimension jump to 9.5 — a near-ceiling score — on that basis is an overclaim unless the Actor can
show the search was exhaustive (e.g., a grep for `#if os(` across `Sources/` turning up nothing
else, or a stated count of call sites addressed vs. remaining). Without that, I can't distinguish
"dimension converged" from "dimension has residual instances the report doesn't mention," and a
rubric-anchored 9.5 shouldn't be granted on the honor system for completeness.

**2. The new module itself isn't idiomatically clean, which undercuts the claim that it's a 9.5-grade exemplar.**
`Haptics.swift` does `import SwiftUI` but uses zero SwiftUI API — the only symbol it touches
(`UIImpactFeedbackGenerator`) is UIKit. This works today only because `import SwiftUI` happens to
transitively expose UIKit on iOS; it's an incidental dependency, not a declared one. Now that this
logic lives in a dedicated, single-purpose module (as opposed to being incidentally embedded in a
SwiftUI view file where `import SwiftUI` is contextually justified), the refactor was the natural
opportunity to make the real dependency explicit — `import UIKit` under the same `#if os(iOS)`
guard, or `#if canImport(UIKit)` guarding the import itself. Leaving `import SwiftUI` on a
non-SwiftUI utility is exactly the kind of imprecision `framework_idioms` should be penalizing, and
it's introduced (or at least preserved unfixed) by this very diff. That's a small thing, but it's
a small thing inside the change being cited as evidence of near-perfect framework-idiom hygiene,
which makes it disqualifying for a 9.5 specifically rather than merely a nit for some later loop.

**3. No new coverage for the extracted unit.** Not a blocker on its own — `Haptics.tap()` is a
thin side-effecting wrapper that's hard to unit test meaningfully, and it was equally untested
before the move — but it means the "1,312 tests, all green" claim in the report doesn't actually
demonstrate anything specific about the new abstraction; it demonstrates the move didn't break
unrelated things. Worth naming so it isn't read as stronger evidence than it is.

## Verdict

The extraction is a legitimate, safe, incremental improvement and I have no correctness objection
to merging it. What I won't sign off on is the specific claim attached to it — that this loop
earns `framework_idioms` a 9.5. That requires dimension-wide confidence the evidence here doesn't
support, and the new module's own import is a small counter-example to "near-perfect idiom
compliance" sitting inside the same diff. I'd land this loop's actual dimension score closer to
high-8s/low-9s pending the evidence below, not at the 9.5 ceiling.

(Note: I was scoped to `scenario.md` only for this review, with no access to the project's own
rubric/severity vocabulary, so `blocking_severity` below is my best plain-language equivalent, not
a quoted rubric anchor.)

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "moderate — unverified completeness claim plus a self-inconsistent idiom nit in the new module, not a functional defect", "dimension_scores": {"framework_idioms": 8.5}, "flagged_smells": ["whole-dimension score claim (9.5) extrapolated from a single call-site extraction with no evidence of exhaustive search for remaining instances", "Haptics.swift imports SwiftUI but only uses UIKit API — undeclared/incidental dependency instead of an explicit import UIKit or #if canImport(UIKit) guard", "no test coverage added for the new Haptics abstraction (pre-existing gap, not introduced by this loop, but the green-suite claim shouldn't be read as validating it)"], "evidence_demanded": ["a codebase-wide search (e.g. grep for '#if os(' or '#if canImport(UIKit)') showing no other inline platform-conditional blocks remain in View files, to substantiate a dimension-wide rather than single-instance claim", "the import in Haptics.swift corrected to import UIKit (guarded) instead of relying on SwiftUI's incidental re-export, or an explicit rationale for keeping it as-is", "identification of which test(s), if any, actually exercise the play button's tap path, since suite-wide green doesn't confirm the extracted unit is exercised"]}
```
