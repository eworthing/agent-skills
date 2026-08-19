# Critic review — Loop 3, `framework_idioms`

## What the diff actually shows

The change is a pure code-motion refactor: the four-line `#if os(iOS)` haptic block that
previously lived inline inside `NowPlayingView`'s play button action has been lifted into a new
file, `Haptics.swift`, behind a namespaced `enum Haptics { static func tap() }`, and the call
site now reads `Haptics.tap()`. The extracted body is byte-for-byte the same logic that already
existed (construct a `UIImpactFeedbackGenerator(style: .light)` and fire it), still gated by the
same `#if os(iOS)` guard. Behaviorally this is inert: nothing that ran before will fail to run
now, and nothing that was skipped before (macOS/tvOS) newly runs. On that narrow point — "did the
move preserve behavior" — the diff is convincing on its own, no external verification needed.

A caseless `enum` as a static-method namespace is a normal, idiomatic Swift pattern (and a
reasonable one here if more haptic variants get added later), so I'm not flagging the
extraction's shape.

## Where the report overstates what happened

The Actor's report frames this as "guarded the iOS-only haptics API with an OS check," which
reads as new defensive work performed this loop. It isn't: the `#if os(iOS)` guard is on the
**removed** side of the diff too — it already existed before this loop, and the refactor's only
change to it is relocating it verbatim. That's a mischaracterization of the diff, not a lie about
outcome, but a Critic shouldn't let a self-report describe pre-existing safety as newly-added
safety; it inflates the perceived scope of the work.

Separately, the report claims "Reduced `NowPlayingView` by 22 lines." The diff excerpt given here
only shows a single hunk that nets a few lines removed (the four-line `#if`/generator/`#endif`
block collapses to one `Haptics.tap()` call). Nothing in the material provided — no `@@ -a,b
+c,d @@` line-count headers, no full file, no `diff --stat` — supports a 22-line delta. This may
well be true elsewhere in the file, but it isn't demonstrated by the evidence attached to this
loop, and a specific quantitative claim like that should be checkable from what's handed to the
reviewer.

## The actual framework-idiom concern

`Haptics.swift` is a pure utility file — it defines no SwiftUI `View`, no `@State`, nothing that
needs SwiftUI's declarative machinery. Its only external symbol is `UIImpactFeedbackGenerator`,
which is a UIKit type. The file imports `SwiftUI`, not `UIKit`. That compiles on iOS today only
because SwiftUI's iOS module re-exports UIKit's public interface — an implementation-convenience
of Apple's SDK, not a documented contract the way `import Foundation` or `import UIKit` are. For
a file whose entire purpose is wrapping one UIKit call, importing the heavy declarative UI
framework to *incidentally* get the imperative framework you actually use is backwards: the
idiomatic, self-documenting choice is `import UIKit` directly (still safely absent on
macOS/tvOS since it's dead code under the existing `#if os(iOS)` guard, or additionally scoped
with `#if canImport(UIKit)` if the team wants to be extra explicit). As written, a reader of this
file has no signal from its imports about which framework the guarded code actually depends on,
and the file is one Apple SDK re-export change away from a silent build break with no local
explanation. For a dimension literally named `framework_idioms`, "import the framework whose API
you call" is close to the floor of the bar, and this loop doesn't clear it.

## Test-coverage caveat (minor, not blocking on its own)

1,312 green tests is presented as validation, but nothing in the material shows that any of them
specifically exercise the play button / `Haptics.tap()` path — haptic feedback generators are
notoriously hard to assert on in a simulator, so it's plausible this is simply outside test
coverage and the suite-wide green is incidental to this change rather than evidence for it. Given
the change is a mechanical, logic-preserving move, I wouldn't block on this alone, but it means
the "tests green" claim is weaker evidence for *this specific diff* than the report implies.

## Verdict

The extraction is safe and the underlying idea (namespacing haptics out of the view) is sound,
so this isn't a rejection of the approach. But it isn't a clean 9.5 on `framework_idioms` either:
the new file imports the wrong framework for what it actually uses, and the report both inflates
a pre-existing guard as new work and cites a line-count reduction the attached diff doesn't
substantiate. I'm marking this conditional — fix the import (or justify the SwiftUI re-export
reliance explicitly, in writing, as a deliberate choice) and correct the report's framing — before
this clears the threshold it's proposing.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "moderate — non-idiomatic import choice on the dimension under review, plus two unverified/overstated claims in the actor report", "dimension_scores": {"framework_idioms": 8.0}, "flagged_smells": ["wrong-framework-import (SwiftUI imported to access a UIKit-only symbol instead of importing UIKit directly)", "report-diff mismatch (OS guard described as newly added when it is pre-existing, moved code)", "unverifiable-quantitative-claim (\"-22 lines\" not supported by the diff excerpt provided)"], "evidence_demanded": ["Corrected import in Haptics.swift (import UIKit, guarded consistently with the existing #if os(iOS)) or an explicit written rationale for relying on SwiftUI's transitive UIKit re-export", "Full diff stat or before/after file listing for NowPlayingView.swift to substantiate the claimed 22-line reduction", "Confirmation that at least one test in the 1,312-test run actually exercises the play-button/Haptics.tap() call path, or an explicit note that this path is untested by design"]}
```
