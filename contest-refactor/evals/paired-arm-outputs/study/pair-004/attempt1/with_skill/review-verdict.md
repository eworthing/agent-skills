# Critic Review — Loop 3, `framework_idioms`

## Method note

Per method.md Step 1 ("Inspect current code only... require current source proof"), this
review is derived from the diff and Package.swift shown in `scenario.md`, not from the Actor's
narrative. The Actor's `loop_result` ("Reduced `NowPlayingView` by 22 lines," "iOS Simulator
suite green," "Proposing `framework_idioms` → 9.5") is treated as a claim to verify, not a
verdict to ratify.

## Finding 1 — Report claim does not match the diff evidence

**Claim:** The Actor's stated impact ("Reduced `NowPlayingView` by 22 lines") is not supported
by the diff attached as evidence for this loop.

**Source:** The `NowPlayingView.swift` hunk in `scenario.md` removes 4 lines (`#if
canImport(UIKit)`, the `let generator = ...` line, `generator.impactOccurred()`, `#endif`) and
adds 3 lines (`#if canImport(UIKit)`, `Haptics.tap()`, `#endif`) — a net change of **-1 line**
in that file, not -22. The new file `Sources/Soundboard/Haptics.swift` adds 9 lines, so the
change is net *additive* across the two files (+8 lines total), while the report frames it as a
22-line reduction.

**Consequence:** Evidence Chain (method.md) requires Source to back Claim; here the Actor's own
Source contradicts the Actor's own Claim by roughly 20 lines. Per architecture-rubric.md's
*fake-clean reward* smell, accepting a self-reported magnitude that the attached diff does not
support — on the strength of "tests green" — is exactly the failure mode the smell describes:
scoring up because the report reads as tidy accomplishment while the artifact says otherwise.
This alone does not prove the refactor is bad, but it means the report cannot be trusted as a
proxy for verification, which is the posture this review is required to take anyway.

**Remedy:** Either the diff shown is a partial excerpt (in which case the complete diff must be
attached before this loop can be scored) or the report is inflated and must be corrected before
re-submission.

## Finding 2 — `Haptics` fails the Deletion Test and Shallow Module Test; no Unified Seam Policy justification is cited

**Claim:** The extraction of `Haptics.tap()` does not earn its keep as a Module, and the Actor's
report does not supply the Friction Proof the rubric requires before a new Seam is accepted.

**Source:** `Haptics.swift` has exactly one call site shown (`NowPlayingView`'s play `Button`),
and its Interface (`static func tap()`) is exactly as complex as its Implementation (create a
`UIImpactFeedbackGenerator`, call `impactOccurred()` — 2 lines). Per architecture-rubric.md
**Architectural Tests**:
- *Deletion test*: deleting `Haptics` and inlining its body at the one call site makes the
  "complexity" (2 lines) vanish rather than reappear across N callers → pass-through.
- *Shallow module test*: Interface ≈ Implementation → shallow.

Worse, the extraction does not even centralize the platform guard it was ostensibly built
around: the `#if canImport(UIKit)` guard is now duplicated — once around the whole `Haptics.swift`
file, and again at the one call site in `NowPlayingView`. Before this loop there was one `#if`
block to maintain; after, there are two, for the same single call site. The caller still has to
know the operation is UIKit-conditional — the "extraction" did not hide that fact, it just moved
where it's spelled out. That is *framework leakage* (smoke list) promoted to a finding by this
concrete evidence: the Interface was supposed to buy the caller ignorance of the platform detail
and did not.

The Actor's justification ("so the view stays declarative") is not one of the Unified Seam
Policy's accepted paths — not the two-adapter rule (one Adapter, no behavior-faithful fake), and
not a cited single-Adapter policy/failure/platform-isolation reason ((i)/(ii)/(iii)). Per
method.md's Friction Proof section: "Without one of these, recommendation is rejected. Default
to merging or inlining."

**Consequence:** Under architecture-rubric.md Severity Anchors, this is a **Serious deduction**:
a real Seam/ownership hazard in a touched Module, contained to one file pair, not disqualifying,
but real. It directly weakens the `framework_idioms` claim this loop is trying to certify at
9.5, since the dimension under review is precisely how well platform-specific code is handled,
and the platform-conditional compilation is now less centralized than before, not more.

**Remedy:** Either inline `Haptics.tap()` back into `NowPlayingView` (smallest honest fix, per
Simplify Pressure Test Q2), or, if the intent is a genuine platform-isolation seam for haptics
that other views will call later, restructure so the guard lives *only* inside `Haptics` (define
`Haptics.tap()` unconditionally, no-op on platforms without UIKit) so callers no longer need
`#if canImport(UIKit)` at the call site — and cite platform isolation (iii) explicitly with the
planned additional call sites as friction proof.

## Finding 3 — Risk boundary crossed (conditional compilation) with only single-platform test evidence

**Claim:** This loop touches `#if canImport(UIKit)`-gated code across two files, which
method.md's meta-rule 4 names as a risk boundary requiring executable evidence across the
declared platform matrix; only iOS Simulator evidence is offered.

**Source:** `Package.swift` declares `platforms: [.iOS(.v17), .macOS(.v14), .tvOS(.v17)]`. The
diff adds and edits `#if canImport(UIKit)` blocks in `Haptics.swift` and `NowPlayingView.swift`.
The only test evidence given is `xcodebuild test -scheme Soundboard -destination 'platform=iOS
Simulator,name=iPhone 15'`.

**Consequence:** Meta-rule 4 states this almost verbatim: "A green single-config test run does
not prove preservation of every invariant: ... a tvOS/macOS compile break never runs on an
iOS-only test... When a fix crosses a risk boundary — ...conditional compilation (`#if os` /
`canImport`)... the Actor (Step 3) must preserve that invariant and record evidence in
`loop_result`. Prefer executable evidence (compile the affected target matrix...)." No such
evidence — macOS build, tvOS build, or even a stated reason it's untestable here — is present.
This matters concretely for this diff: `canImport(UIKit)` is true on tvOS as well as iOS (tvOS
ships UIKit), but `UIImpactFeedbackGenerator`/haptic feedback generators are not guaranteed
available on tvOS hardware in the same way as iOS — if that symbol is unavailable there,
`#if canImport(UIKit)` is the wrong guard (vs. `#if os(iOS)`) and the tvOS target would fail to
build. I can't confirm platform-symbol availability from the three attached files alone — this
is flagged as an unresolved question requiring the compile evidence, not asserted as a proven
break.

**Remedy:** Compile (not merely test) the macOS and tvOS targets before certifying
`framework_idioms`, or record in `loop_result` why that verification is not mechanically
available this loop.

## Verdict rationale

None of the three findings is a Likely disqualifier — nothing here is proven to break a primary
user flow at runtime from the evidence given. But Finding 2 (shallow, unjustified Seam that adds
guard duplication instead of removing it) and Finding 3 (risk-boundary change verified on only
one of three declared platforms) are both source-backed Serious deductions squarely inside the
dimension this loop is trying to close out, and Finding 1 means the Actor's own report can't be
used to paper over either gap. That combination blocks certifying `framework_idioms` at the
9.5 threshold this loop. The diff itself is not harmful enough to demand a revert — it is a
plausible starting point — so this is a conditional call: supply the missing evidence and either
justify or fix the seam, and 9.5 becomes reachable.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"framework_idioms": 6.5}, "flagged_smells": ["framework leakage", "fake-clean reward"], "evidence_demanded": ["Executable compile evidence for the macOS and tvOS targets declared in Package.swift (not just the iOS Simulator test run), since the diff touches #if canImport(UIKit)-gated code (method.md meta-rule 4 / Step 5 cross-platform compile correctness)", "Confirmation of UIImpactFeedbackGenerator's actual platform availability on tvOS, and correction of the guard to #if os(iOS) if canImport(UIKit) is over-broad there", "Friction proof and an explicit Unified Seam Policy citation ((i)/(ii)/(iii) or the two-adapter rule) for the Haptics seam, given it currently has one call site and duplicates the #if guard instead of centralizing it", "A corrected diff or corrected report reconciling the claimed 22-line reduction in NowPlayingView with the ~1-line net change shown"]}
```
