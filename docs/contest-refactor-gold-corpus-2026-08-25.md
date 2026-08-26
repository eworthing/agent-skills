# `contest-refactor` external gold-corpus proposal — validated 2026-08-25

**Provenance.** External review feedback (ChatGPT) proposing that the skill's eval suite
graduate from hand-authored synthetic fixtures to a **gold corpus derived from real,
expert-reviewed Swift refactoring changes**, with adversarial siblings (RED / GREEN /
NEAR-MISS / MUTANT) cut from each case. This document validates that feedback against
(a) the current skill and eval architecture at HEAD, and (b) the upstream sources
themselves — every PR, repo, and benchmark named in the feedback was checked against its
primary source on 2026-08-25. A **second review round** (ChatGPT, same day) audited this
document; its corrections — one material (#814 causality reversed), the schema's
gold-as-provenance reframe, leakage controls, and per-pack executable-oracle upgrades —
are folded in and marked where they changed the plan. A **third round** (same day)
settled the two decisions round two left open — canonical schema vocabulary with the
first-round names demoted to rejected aliases, and `provenance_labeled` as a batch
contamination assay rather than a per-pack arm — and sharpened #814's framing to
*longitudinal resolution evidence*, naming the #837 chain it belongs to. The proposal
is **adopted as a plan, adapted in one load-bearing way**: it is framed as *fixture
and calibration material for the axes that have measurably paid* (restraint,
calibration, execution, scanner controls), **not** as a reopening of the
detection-prose programme closed 2026-08-22 — see
[Relationship to the closed detection programme](#relationship-to-the-closed-detection-programme--read-before-building)
before building anything.

**Boundary.** This document owns *what the eval corpus should be made of*. The two
registers it sits between are cross-referenced, never duplicated: the
[detection-domain register](contest-refactor-detection-domains.md) owns whether the skill
can find a class of defect at all; the [review register](contest-refactor-review-register.md)
owns the eval architecture (trial validity, paired lift, noise floor, layers) this corpus
would run inside. Fixture construction happens under `contest-refactor/evals/`; nothing
here proposes loop-path prose.

## Contents

- [Validation verdict](#validation-verdict)
- [Repo consistency cleanup](#repo-consistency-cleanup)
- [The proposal, validated](#the-proposal-validated)
- [Ranked source register](#ranked-source-register)
- [Per-source fixture plans](#per-source-fixture-plans)
- [Python track — second language](#python-track--second-language)
- [Mapping to the existing eval layers](#mapping-to-the-existing-eval-layers)
- [Relationship to the closed detection programme — read before building](#relationship-to-the-closed-detection-programme--read-before-building)
- [Benchmark methodology borrowings](#benchmark-methodology-borrowings)
- [Performance gates](#performance-gates)
- [Corpus structure and provenance schema](#corpus-structure-and-provenance-schema)
- [The first fixture packs, adapted](#the-first-fixture-packs-adapted)
- [Open owner decisions](#open-owner-decisions)
- [Items not independently verified](#items-not-independently-verified)

## Validation verdict

**The feedback's characterization of the current architecture is accurate on every
architectural claim it rests on** — trial validity, paired lift, the tautology screen,
the promotion bar, and the zero-lift record all check out, in the form described. Two
repo-consistency defects the second review surfaced alongside them are real and are
recorded (and fixed) in [Repo consistency cleanup](#repo-consistency-cleanup) below;
they do not change any architectural claim, but they were fogging the record the corpus
must run inside. Each architectural premise exists, in the form it describes:

| Feedback's claim about the suite | Verified at |
| --- | --- |
| Deterministic vs model-dispatched layers | `evals/README.md` — Layer 1 (artifact-rule, mechanical, no model) vs Layers 2–6 (host-dispatched) |
| Invalid/exogenous trials tracked separately from failures | `evals/README.md` § Trial validity; `canon/trial-validity.toml`'s closed exogenous-only `invalid_reasons` enum; adherence failures are counted, never voided |
| Paired lift computed only over outcome criteria | `criterion_class: "outcome" \| "skill_contract"`; `compute_lift()` reads `outcome`-classed assertions only, signed and unfloored |
| Tautology screen against "with-skill wins by using our vocabulary" | `screen_criteria()` + `DECLARED_TAUTOLOGY_EXCEPTIONS`, wired into `validate-repo.py` (70 declared, 0 undeclared) |
| Detection-domain promotion discipline: bare Critic ≤1/5, treatment ≥4/5, restraint controls | Detection-domain register § Detection-domain promotion bar — criterion 2 "at most 1 of 5 reps", criterion 3 "at least 4 of 5", criterion 4 "at least 2 near-miss fixtures … zero false positives" |
| Repeated evidence that checklist prose on a legible defect yields zero recall lift | Six independent measurements recorded in the register (advisory program ×2, W3.2, June lens, DD-02/DD-04, DD-08, DD-14 — the last four legible 5/5) |

**All twelve primary external sources and all four benchmarks exist and match their
descriptions**, with the corrections and enrichments recorded per-source below. Three
facts discovered during validation materially improve the proposal and are folded into
the plans — including one where the **second review round caught this document's own
error**:

1. **SwiftNIO #2959 is a contested accepted patch, not proven-bad gold.** Three weeks
   after merge, its author opened #2980 ("Revert the `@preconcurrency Sendable` changes
   on main from #2959, #2955, and #2953") and pushed a full revert of the #2959 merge
   commit to his fork — but #2980 was a **closed, unmerged draft** (closed 2024-11-21).
   The correct reading: the migration was contested from inside, never adjudicated
   against — which makes it *better* material for the imperfect-gold theme (the same
   theme as TCA #3460→#3845) and a caution against treating any merged patch as ground
   truth, without licensing the opposite claim that the revert was right.
2. **The #814 downstream-regression claim in the first draft of this document had the
   causality backwards.** Kitura/Kitura-NIO#81 (`testBadRequestFollowingGoodRequest`,
   intermittent response loss) was opened 2018-08-28 — six months *before* #814 merged —
   and its closing comment (2019-03-07) reads: "This issue has been fixed per
   apple/swift-nio#600 through apple/swift-nio#837 and apple/swift-nio#814." The parser
   restructure was part of the **fix**, not the cause. The second review flagged the
   citation as not proving causation; fetching the issue's comments proved the stronger
   correction. **#814 did not close it alone**, and the third round drew the line:
   it *participates in a resolution chain*. #837 ("B2MD: Don't deliver data after
   error", merged 2019-02-25 — verified upstream) introduced the error state that stops
   `ByteToMessageDecoder` calling decode functions after a user-thrown error; #814 moved
   the HTTP decoder onto that machinery. Fixture and grading prose says *participates in
   the resolution chain*, never *#814 fixed it*. #814's role in the corpus survives and
   sharpens: the parser complexity is *load-bearing*, carrying **longitudinal resolution
   evidence** — so a Critic that flags "parser states should be flattened" is not merely
   over-refactoring, it is arguing against complexity with downstream behavioral
   validation on record. **Naming rule:** call this *longitudinal resolution evidence* or
   *downstream behavioral validation*. The phrase "longitudinal defect story" is banned
   in this corpus's vocabulary — it still reads as "the merged change caused a later
   bug," which is the exact error this fact corrects.
3. **The feedback's two sharpest restraint cases are external-provenance upgrades of
   pairs the suite already runs.** Swift Collections #298 (`canImport(Darwin)` near-miss)
   is the same defect class as `crossplat-flag`/`crossplat-restraint` (#13/#15 —
   `#if canImport(UIKit)` on a tvOS target); SwiftNIO #2959's fake-fix variants
   (`@unchecked Sendable` without an invariant) are the same class as
   `suppression-flag`/`suppression-restraint` (#12/#14 — bare `@unchecked Sendable` vs
   `NSLock` + TSAN). This is the strongest validation signal in the whole review: the
   external corpus confirms the existing corpus's *coverage choices* while offering real
   provenance and harder variants — and it constrains expectations: these packs upgrade
   evidence, they do not add new capability domains.

## Repo consistency cleanup

Two defects the second review surfaced; both fixed in this pass (selftest, repo
validation, and lint green after the fix):

- `contest-refactor/evals/README.md` opened by describing the directory as having "two
  layers" while its own body documents Layers 1–6 — stale wording from before Layers
  3–6 existed. Fixed to "six layers".
- `contest-refactor/scripts/_paired_baseline.py`'s docstring still described the 165
  `evals.json` assertions as "today, all unclassified," while the classification landed
  in commit `de02426` (151 `outcome`, 14 `skill_contract`, none unclassified). The
  docstring now records the classification and keeps `unclassified` described as what it
  is — the safety-net default for assertions authored without a class, never a steady
  state.

**Terminology correction.** Two named concepts the feedback maps fixtures against are
its own labels, not current skill vocabulary, and fixture grading specs must translate:
"Native Leverage" ≈ `lens-apple.md`'s idiomatic-framework-use question ("Does code use
Swift, SwiftUI, platform frameworks idiomatically?", lens-apple.md:250) plus the
`framework_idioms` scorecard dimension; "micro-deletion hypothesis" ≈ Meta-Rule 5
("Prefer subtractive fixes", references/method.md:40) plus the deletion test
(architecture-rubric.md § 1). Meta-Rule 4 (references/method.md:39) — user-visible
behavior plus load-bearing invariants tests don't exercise, with enumerated risk
boundaries including `#if os`/`canImport`, actor isolation, and `Sendable` — is the
exact rule three of the twelve sources exercise, by name.

## The proposal, validated

The design change the feedback leads with, confirmed as sound and adopted:

> **Use real expert-reviewed changes as the source of truth, then derive adversarial
> variants from them.** For every good real-world fixture, derive at least three
> siblings — RED (the original defect/inferior implementation), GREEN (the
> expert-accepted implementation), NEAR-MISS (looks metrically cleaner but is
> semantically worse) — and for especially valuable cases a MUTANT (one tiny regression
> injected into GREEN). One high-quality historical PR then tests recall, restraint,
> scoring, execution, regression resistance, semantic preservation, and Goodhart
> behavior at once — far denser than fifty unrelated synthetic scenarios.

Three additions this repo's own measurement history imposes on that design:

- **Minimize and de-contaminate.** These are famous public patches; models have seen
  them. A reviewer handed the verbatim #2486 diff may recognize it and parrot the commit
  message instead of reasoning (and for the oracle-trap case, contamination makes the
  trap *easier* to escape — an optimistic bias that must be disclosed, not hidden).
  Follow the feedback's own Swift-project-derived rule — *derive minimal repro fixtures
  from real PRs; one fixture proves one behavioral distinction* — and additionally
  rename types/symbols so provenance survives in `provenance.json` rather than in the
  fixture text. This matches the existing suite's scenario-authoring discipline
  ("must not encode the defect as the visible diff delta; must not hand over the audit
  legwork").
- **The negative oracle is the point.** The feedback's `must_not_claim` field (canonical
  name `must_not_find`; the first-round spelling is a rejected alias — see
  [below](#corpus-structure-and-provenance-schema)) is the
  single best idea in the review and matches this repo's measured history: the detection
  programme's one shipped prose change (DD-13) was restraint, not recall, and the
  honest summary on record is that the sweep found reach gaps *in the prose* while
  measurement found none *in the reviewer*. A corpus built only from RED cases would
  re-buy six zero-lift results; a corpus built RED+GREEN+NEAR-MISS+MUTANT measures the
  axis where the suite actually earns its keep.
- **Licensing/provenance discipline.** All source repos are permissively licensed
  (Apache 2.0 for the apple/* repos, MIT for TCA and Vapor), so committed minimized
  derivatives are fine with attribution carried in `provenance.json`. The gitignored
  `refs/competitors/` clone pattern is *not* the right home for these: fixtures must be
  committed so validators and graders can run offline.

## Ranked source register

Every row verified against upstream on 2026-08-25. "Fit" is the corrected mapping to
this suite's actual axes (see [layer mapping](#mapping-to-the-existing-eval-layers)).

| # | Source | Verified state | Why it is unusually valuable | Fit |
| --- | --- | --- | --- | --- |
| 1 | apple/swift-collections #688 | Merged 2026-08-11 (1.7.0); author inju2403, reviewer lorentey | Pure behavior-preserving refactor with explicitly documented rejected alternative (direct `replace` call) and an expert improvement (`exchange(_:with:)`) layered on top | Layer 2 twins + Layer 3 case + Layer 6 calibration anchor |
| 2 | apple/swift-nio #2486 | Merged 2023-07-31 | A prior refactor introduced a semantic regression **and a test approving it**; fix removes both the guard and the test | Test-oracle trap: Layer 2 pair + Layer 5 exec fixture |
| 3 | apple/swift-collections #298 | Closed (rejected) 2023-06-22 | Plausible `canImport(Darwin)` simplification rejected as not semantically equivalent; maintainer names the module-naming and visionOS reasons | Restraint twin — external upgrade of existing pair #13/#15 |
| 4 | apple/swift-nio #2959 | Merged 2024-10-31; **contested accepted patch** — revert draft #2980 (closed, unmerged) + revert commit on author's fork | Real strict-concurrency lock-in across production and tests; contested from inside within weeks | Fake-fix mutants (Layer 2) + imperfect-gold calibration |
| 5 | pointfreeco/swift-composable-architecture #3460 + #3845 | Merged 2025-03-27 / 2026-02-18 | Accepted major architecture refactor whose `DefaultIsolation` actor was never referenced and removed 11 months later | Residual-accounting + 9.5-vs-10 + loop-replay staging |
| 6 | apple/swift-nio #1801 | Merged 2021-04-23 | "Instead of manual shifting / masking we can write the whole registration ID code normally in Swift" — representation over bit-twiddling; spawned #1807 (generic bit packing) | Representation/idiom pair (Layer 2) |
| 7 | apple/swift-async-algorithms #185 | Merged 2022-10-10 | Genuine concurrent state machine (one task + child tasks, demand signalling, cancellation, continuations); removes a `Sendable` constraint and per-demand `Task` creation | Scanner/Critic restraint control |
| 8 | apple/swift-nio #814 | Merged 2019-03-06 (2.0.0); **longitudinal resolution evidence** — Kitura-NIO#81 closed as fixed through the #837 + #814 chain, #814 participating rather than fixing alone | HTTP decoder becomes a real `ByteToMessageDecoder`; parser states and branches *are the domain* — and were load-bearing (part of the chain that closed a six-month-old downstream failure) | Scanner/Critic restraint control + load-bearing-complexity evidence |
| 9 | apple/swift-collections #488 | Merged 2025-10-02 (1.4.0) | `_Chunk` ditches `String` backing for a CoW UTF-8 managed buffer — locally more complex, globally better (stable chunk identity, diff precision, benchmark attached) | Representation restraint twin (false-positive control) |
| 10 | vapor/vapor `AuthenticationTests.swift` | Verified at `main` | Rich observable auth contracts incl. **concurrent login race** (1000-iteration task-group test), empty-password-is-valid, error-detail preservation, chained authenticators, session semantics | Security/error/concurrency mutants (Layer 2) |
| 11 | swift-org/swift regression-test methodology | Not independently fetched (see [below](#items-not-independently-verified)); consistent with known practice | Focused regression tests at the nearest abstraction level, cross-platform correctness | Fixture-authoring rule (already adopted in this doc) |
| 12 | Swift Benchmark package / swift-collections benchmark | Exists (swift-collections benchmarks use the benchmark harness); not deeply inspected | Measured performance preservation | Performance gates (see [below](#performance-gates)) |

Benchmarks: [Swift Anvil](https://github.com/AfterQuery/swift-anvil) (verified: PR-derived
tasks, base-commit SHAs, gold patches, oracle agent, Xcode+XCTest eval — 2 stars, young,
exactly as described), [microsoft/RefactorBench](https://github.com/microsoft/RefactorBench)
(verified: ICLR 2025, 100 handcrafted multi-file Python tasks, 22% agents vs 87%
time-constrained human), [CodeTaste](https://github.com/logic-star-ai/codetaste)
(verified: ICML 2026, human-refactoring ground truth, containers, tests + static checks,
test suite rerun up to 5× for flakiness, alignment score that "only rewards rule
compliance when tests are valid"), and SWE-Refactor (verified via its abstract: 1,099
developer-written pure refactorings, 18 Java projects, 922 atomic / 177 compound,
validated by compilation + tests + refactoring detectors). All four are real and
characterized accurately; borrowings are scoped in
[Benchmark methodology borrowings](#benchmark-methodology-borrowings).

## Per-source fixture plans

Condensed from the feedback, corrected where validation found drift, and re-aimed at the
axes this suite can actually measure. Per-pack grading specs live with the fixtures when
built; this section is the plan of record.

### 1. Swift Collections #688 — canonical refactoring fixture family

**Verified facts.** `OrderedDictionary.replaceElement` and `OrderedSet.replace` each
inlined the same append→swap→remove step. The merged change factors only that mechanical
step into an internal `OrderedSet._replaceNew(at:with:in:)`, deliberately **not** routing
the dictionary through the public `replace` API, and the PR documents why in a table:
direct `replace` would change trap diagnostics (`Duplicate element`/`Index out of
bounds` vs `Duplicate key`/`Index out of range`) and re-run the `_find` hash lookup.
Reviewer lorentey then added a second commit switching the value overwrite to
`exchange(_:with:)` ("to avoid copying the old value"). No new tests — behavior-
preserving by design; existing suite passes with and without
`-DCOLLECTIONS_INTERNAL_CHECKS`.

**Four fixtures** (the feedback's A–D, confirmed buildable):

- **RED** — the pre-#688 duplicated implementations. Expected: genuine semantic
  duplication recognized, sharing proposed at the correct altitude (internal primitive,
  matching `_appendNew`/`_removeExistingMember` precedent), no invented public
  abstraction.
- **GREEN** — the merged implementation. Expected: **no finding**; `_replaceNew` earns
  its existence; the unchecked low-level primitive is legitimate because callers
  maintain their own preconditions. This is the calibration anchor: a Critic that
  flags GREEN is over-flagging exactly the way DD-13's near-miss A measured (5/5).
- **NEAR-MISS** — `replaceElement` calls `replace(at:with:)` directly. Looks simpler;
  is semantically worse (diagnostics change, redundant lookup). Expected: rejected with
  both reasons named. This is the anti-overgeneralization case — maximal reuse is not
  maximal quality — and it exercises the Simplify Pressure Test's fake-simplification
  direction.
- **ALTERNATE GOLD** — the `exchange` improvement. Expected: detected as a small
  legitimate improvement without escalating into generic stdlib fetishism.

**Second-round upgrade — make both rejection reasons executable, not prose-graded.** The
RED/GREEN distinction must not be "was a helper extracted?" but four checkable
properties: preserves dictionary-specific diagnostics, does not re-run the key lookup,
keeps the unchecked internal primitive behind caller-owned preconditions, and does not
flag GREEN as an unjustified abstraction. Concretely:

- A trap-message oracle asserts the diagnostics contract (near-miss must *fail* it):
  replacing at a duplicate key traps with the dictionary's own message, not the set's.
- A counting probe (a `ProbeIndex`-shaped test double exposing `lookups`) asserts the
  lookup contract: one hash lookup per replace, not two — the near-miss's redundant
  `_find` re-run becomes a failing assertion, not a reviewer's opinion.

These two hidden oracles move the pack's grading from "did the Critic say the right
words" to "does the variant the Critic blessed pass the contract tests" — the same
oracle-verifies-harness move Swift Anvil uses, aimed at the grader instead of the actor.

**Covers:** reuse, locality, semantic duplication, altitude, error-context preservation,
efficiency, behavior preservation, abstraction justification, Goodhart resistance —
and, as a GREEN-side anchor, the 9.5-vs-10 discipline. Follow-up #703 (open) extends
`exchange` to the equal-key path and is a second, free ALTERNATE GOLD candidate.

### 2. SwiftNIO #2486 — the test-oracle fixture

**Verified facts.** Merged PR text, verbatim: the fail-writes-before-activation check
"was added in a refactor to use an internal state machine, and while we had a test that
this happened, it didn't protect us from anything"; Modifications include "Remove a
check that failed writes if we weren't active. **Remove a test that validated that we
did that.**"; the governing contract is "a cardinal NIO rule: writes should never be
lost."

**Fixture set:**

- **Test-oracle RED:** wrong implementation + passing test asserting the wrong
  behavior. The reviewer must *not* discharge on "tests green ⇒ intentional"; it must
  reason from the stronger contract. Grading must distinguish a reviewer that cites the
  contract from one that merely distrusts tests reflexively — the reflexive variant
  over-flags the restraint twin, so pair it.
- **Fake-green restraint twin:** legitimate code with high line coverage and green
  tests that must **not** be flagged for oracle weakness.
- **Regression MUTANT (Layer 5):** start from the pre-regression implementation, apply
  a simplified version of the historical refactor that passes existing tests but changes
  write semantics; the implementation-reviewer must catch it. This is Step-3 /
  Meta-Rule 4 material — "a green single-config test run does not prove preservation of
  every invariant" is that rule's own worked example shape.
- **Oracle MUTANT:** mutate the test itself from asserting the right contract to
  asserting the wrong one; the suite's DD-01-adjacent machinery (the mutation-test
  mental model at method.md:89) should recognize the oracle no longer discriminates.

**Second-round upgrade — build it as a toy channel lifecycle, not NIO internals.** A
minimal `BufferedChannel` with an `initialized/active/closed` lifecycle: pre-activation
writes append to `pendingWrites`; `activate()` flips the state and drains. Variants:
wrong implementation rejects pre-activation writes; bad oracle test asserts that
rejection; correct hidden test writes before activation, activates, and asserts the
bytes arrive; oracle mutant approves the wrong behavior. The contract ("writes are
never lost") is observable at the toy boundary — the judge gets no room to say "tests
pass, ship it" — and the fixture stays runnable without dragging NIO into the harness.

**Caution:** the oracle-trap domain is DD-01's, parked 2026-08-21 *on the candidate's
own retraction* — a quantifier gap, not a capability gap. This pack does not reopen it;
it supplies the harder, real-world-shaped fixture the park never had. If the bare-rubric
control misses the oracle trap on this fixture where it caught the synthetic one, *that*
is the behavioural miss the register says would justify reopening — record it either way.

### 3. Swift Collections #298 — near-miss restraint

**Verified facts.** The PR proposed replacing `#if os(macOS) || os(iOS) || os(watchOS)
|| os(tvOS)` with `#if canImport(Darwin)`. Maintainer lorentey closed it: the workaround
"only matters for macOS, iOS, watchOS and tvOS. It does not apply to visionOS…
`canImport(Darwin)` is not an exact equivalent"; separately, "might return true if the
project being built includes an unrelated module that coincidentally happens to be
named Darwin"; suggested `#if _runtime(_ObjC)` for the one site where a runtime test
was wanted.

**Fixture:** original / rejected-simplification, expected judgment = rejection with the
predicate-change reason (the abstraction changes the predicate being expressed), plus a
restraint record that the *original* four-OS condition is itself not a finding. This is
an external-provenance upgrade of existing pair #13/#15 — build it as a variant of that
pair, not as a new domain. Meta-Rule 4's enumerated risk boundary names
`#if os`/`canImport` exactly (references/method.md:39).

**Second-round upgrade — encode the predicate as data, not compiler directives.**
Actual `#if` fixtures are awkward to run across platforms; instead encode the platform
predicate as a `needsFoundationWorkaround(_ platform: Platform)` function over an enum
(`macOS/iOS/watchOS/tvOS/visionOS/linux/linuxWithLocalDarwinModule`), with the near-miss
being a `platform.canImportDarwin`-shaped shortcut. Hidden tests then assert the two
discriminating rows directly — `visionOS` and the local-Darwin-module case both answer
`false`, which the near-miss gets wrong. The real semantic lesson (an apparently
equivalent predicate quietly changes what is being expressed) survives; the fixture
needs no zoo of Swift SDK targets.

### 4. SwiftNIO #2959 — Swift 6 concurrency corpus

**Verified facts.** "With our earlier big refactors, NIOCore is now currently strict
concurrency clean. Let's lock in the win by adopting the relevant Swift settings and
fixing up the tests" — production `Sendable` changes plus test cleanup, merged the same
day it was opened. Three weeks later #2980 attempted to revert the
`@preconcurrency Sendable` changes from #2959/#2955/#2953 (closed), and a full revert of
the merge commit exists on the author's fork.

**Fixture set:** production RED (pre-migration warnings), GOLD (merged state), and
four fake-fix archetype siblings, each a tiny standalone case rather than one giant
migration fixture:

| Fake-fix archetype | Expected reviewer behavior |
| --- | --- |
| `@unchecked Sendable` around mutable state | Reject unless a stated invariant *and* synchronization mechanism exist |
| Blanket `@MainActor` | Reject if it changes execution topology or cascades isolation through unrelated APIs |
| `nonisolated(unsafe)` | Reject as diagnostic silencing unless a clear external invariant exists |
| Real primitive (`NIOLockedValueBox` / `ManagedAtomic`) | Accept when it actually protects the shared state |

The accept row is grounded in the source change, not invented: the #2959 diff moves
test state to `ManagedAtomic` (ByteBufferTest, DispatchQueue+WithFutureTest) and
`NIOLock`/`NIOLockedValueBox` (ChannelOptionStorageTest). Precision note for grading
specs: those moves are in the PR's *test* files — its production-side changes are the
`Sendable`/`@preconcurrency` annotations — so the accept archetype's provenance is
test-side, and the fixture must not claim NIO migrated production state to
`NIOLockedValueBox` in this PR. The existing #12/#14 pair covers the first variant's
shape; this pack adds the migration-shaped framing and the blanket-`@MainActor` cascade
case. **Use the revert story as calibration material:** a reviewer handed
GOLD-with-`@preconcurrency` should treat it as *contested*, not as clean — #2980 was a
closed unmerged draft, so the record supports "contested accepted patch," neither
pristine nor disproven — the imperfect-gold discipline the TCA pair teaches, available
here as a second instance.

### 5. TCA #3460 + #3845 — the longitudinal fixture

**Verified facts.** #3460 (merged 2025-03-27) replaced type-erased `RootStore`/`ToState`
with generic-preserving `Core` protocol composition, motivated by safer key-path
handling and a marginal benchmark win. The `DefaultIsolation` actor it introduced "has
never been referenced anywhere in the codebase" (removal commit's own words) and was
deleted in #3845 (merged 2026-02-18).

**Fixture chain:** before → accepted-refactor (+`DefaultIsolation`) → residual-only →
final. Three capabilities tested, exactly as the feedback frames them: architecture
recognition (prefer the bigger `Core` architecture), restraint (do not undo it for
having more types — protocol-count is not a finding, per Meta-Rule 2), and residual
discovery (find the one dead actor *after* accepting the architecture — the
micro-deletion / subtractive-fixes axis, and the concrete test of "9.5 vs 10" and the
no-fake-clean-reward smell). An imperfect gold patch is worth more than a pristine pair;
this is the pack that grades the *judge*, not just the critic.

### 6. SwiftNIO #1801 — representation over bit-twiddling

**Verified facts.** "Instead of manual shifting / masking we can write the whole
registration ID code normally in Swift… Result: Nicer code." Reviewed into shape over
multiple passes; #1807 factored out generic integer bit packing mid-review. The
adversarial triple stands as proposed: manual masks/shifts vs an opaque clever bit
helper vs explicit domain representation (`SelectorRegistrationID`, `EPollUserData`)
with packing confined to the OS boundary — gold is the third, not whichever is shorter.
Maps to the idiom/representation axis (`framework_idioms`), not to line-count
simplification.

### 7. Async Algorithms #185 + NIO #814 — scanner/Critic restraint controls

**#185 verified facts.** One task per iterator with a child task per upstream, demand
signalling on `next`, a new synchronizing state machine, continuation-heavy
cancellation; motivation was simultaneously removing a `Sendable` constraint and
per-demand `Task` creation; reviewer thread includes the lock-across-continuation
safety debate. **#814 verified facts.** HTTP decoder becomes a real `ByteToMessageDecoder`
once re-entrancy protection existed; semver-major; allocation limits were *raised* to
merge it (a disclosed, measured trade); and the six-month-old Kitura-NIO#81 downstream
failure was closed as **fixed** through the #837 + #814 chain — the restructure was
part of the resolution, not the cause (see [Validation verdict](#validation-verdict),
fact 2). #837 ("B2MD: Don't deliver data after error", merged 2019-02-25) supplied the
error state that stops `ByteToMessageDecoder` calling decode after a user-thrown error;
#814 put the HTTP decoder on it. Grading prose says *participates in the resolution
chain* — never *#814 fixed it*, and never "longitudinal defect story," which inverts the
causality this pack exists to record.

**Role:** deliberately nasty code that must **not** trigger a simplification spree.
Scanner (`audit_hotspots.py`, G49/G50 triage) nominates; Critic inspects; the finding is
"not automatically reduce state/nesting" — the scanner-doctrine distinction the
hotspot pipeline already encodes (method.md Step 6: triage `confirm`/`contextualize`/
`dismiss`; "nesting mirroring genuine case structure is not a finding"). A parser's
states and branches are the domain — and in #814's case load-bearing enough to be part
of a real downstream fix. If the hotspot pipeline turns either fixture into an
automatic complexity finding, scanner/Critic integration has failed — this pack is
the regression test for that failure mode. #814's raised-allocations detail is a free
efficiency-lens restraint case (a disclosed, benchmarked trade is not structural waste).

**Grading shape (second round):** these packs are graded primarily through the negative
oracle, not through findings the reviewer must produce:

```json
{
  "must_not_find": [
    "state machine is inherently over-engineered",
    "nested branches are a smell without a semantic duplicate",
    "parser states should be flattened for readability"
  ],
  "must_find_if_present": [
    {
      "evidence_id": "missing-error-state-transition",
      "applies_to_variants": ["mutant-missing-error-state"],
      "required_finding": "decoder must enter an error state and suppress later decode callbacks",
      "not_required_in": ["green", "complexity-restraint"]
    },
    {
      "evidence_id": "missing-cancellation-transition",
      "applies_to_variants": ["mutant-dropped-cancellation"],
      "required_finding": "cancellation must resume every pending continuation exactly once",
      "not_required_in": ["green", "complexity-restraint"]
    }
  ]
}
```

`must_find_if_present` is deliberately conditional, and **structured at schema level**
(third round) rather than left as a bare list of strings: each entry names the variants
it applies to and the variants it explicitly does not. That shape is what stops the
grader from either over-requiring the finding on GREEN — where the real #185 and #814
code contains no such defect — or treating a seeded mutant as optional fog. The pristine
fixtures demand restraint; the injected variants (`mutant-missing-error-state` is the
#837 error state deleted back out, `mutant-dropped-cancellation` its #185 analogue)
demand the finding. Same pack, two contracts, no ambiguity about which applies where.

### 8. BigString #488 — local simplicity lost, global quality won

**Verified facts.** `_Chunk` "ditches the string instance for the storage
representation and instead makes `_Chunk` a CoW managed buffer of UTF8 bytes," buying
stable chunk identity for diffing — the PR body's own numbers: leaf-only identity
meant "at most 2550 UTF-8 code units" of worst-case diff granularity; per-chunk
identity brings it to "at worst case a 255 UTF-8 code unit diff without looking into
the strings at all." Benchmark chart attached; merged into 1.4.0.

**Role:** false-positive control against "fewer custom data structures = always
better" — a naive implementation-quality critic reverts it to `String` because the code
is shorter. Exercises the deletion test, module depth, and representation axes in the
*restraining* direction.

**Second-round upgrade — oracle rewards stable identity, not data-structure
cleverness.** The hidden tests must not grade "did you keep the managed buffer"; they
grade what the buffer buys: after replacing one chunk in a 10-chunk rope, the diff
touches exactly one chunk, and worst-case compared UTF-8 units stay ≤ 255. A `String`
revert fails the first assertion (identity collapses to leaves); gratuitous
data-structure invention fails the restraint record. The PR's benchmark chart lives in
`provenance.json` as supporting evidence, not in the grading path — performance gates
apply only where the historical case carries a performance contract
([Performance gates](#performance-gates)).

### 9. Vapor AuthenticationTests — security/error/concurrency mutants

**Verified facts** (file read at `main`): missing-credential 401s with correct
`WWW-Authenticate` challenges; valid/invalid Bearer and Basic; error-detail preservation
test capturing reason/challenge/identifier/source through middleware; chained
authenticator ordering; **empty password deliberately authenticates a matching
authenticator**; session persistence incl. no-cookie-doesn't-create-session; logout
replacement semantics; and **`Test Concurrent Logins Are Not Lost`** — 1000 iterations
of a task group racing two `login`s, observable loss, zero tolerated.

**Mutants, as proposed and confirmed buildable:** fail-open (authenticator error →
permit), error-context discard (rethrow without original reason/source), concurrent
state (unsynchronized dictionary for auth storage — the shipped race test is the oracle
it must fail), and the restraint case: empty-password-is-valid is product policy, not a
vulnerability — the reviewer must not invent "empty password must be rejected."

**Second-round upgrade — split the file into four mini-packs, one contract each:**

1. `auth-challenge-preservation` — missing-credential 401s carry the correct
   `WWW-Authenticate` challenge; mutants strip or garble it.
2. `auth-error-detail-preservation` — reason/challenge/identifier/source survive
   middleware round-trips; mutants discard the original error context.
3. `auth-concurrent-login-storage` — the 1000-iteration task-group race is the hidden
   oracle; an unsynchronized storage mutant must fail it.
4. `auth-empty-password-policy-restraint` — the policy-restraint case on its own, so it
   cannot be averaged away inside a broader fixture: the correct reviewer finds nothing,
   and the graded behavior is the *absence* of an invented vulnerability finding.

One fixture proves one behavioral distinction; four small packs also let the
manifest validator demand a negative oracle per pack instead of per file.

**Caution:** fail-open posture is DD-03's domain and authorization is DD-05's — both
parked on class evidence, not measured. Same rule as pack #2: these are fixture
material under the existing posture, and a bare-rubric miss here is the recorded,
reversible trigger the park explicitly invites.

### 10. Fluent/persistence material — Tier 2, explicitly deferred

The feedback itself ranks server-side persistence fixtures below the first eight
("less cleanly behavior-preserving"). Agreed, and doubly so here: persistence and
transaction correctness is DD-04's domain, measured legible 5/5 on the hardest
available sub-domain (transaction-boundary ownership). Do not build until the first
eight packs have reported.

## Python track — second language

Everything above is Swift. All 12 ranked sources are Apple-ecosystem, and nothing in this
document said so, because being monolingual was never a decision anyone made. The owner
directed adding Python as a **full parallel track** — a first-class language in the
register, not a single control pack — **sequenced after the Swift triangle** (packs 1–3
of [the adopted build order](#the-first-fixture-packs-adapted)).

### What a second language buys that a fourth Swift pack does not

`references/lens-apple.md` is **252 lines** of Swift-specific review guidance.
`references/lens-generic.md` is **85 lines** shared across Rust, Go, Python, Node, Java,
Kotlin and Ruby, of which roughly two bullets are Python-specific. Every measurement this
project has ever taken was Swift, under the deep lens.

So the Python track is the first chance to separate **"the skill is good"** from **"the
Apple lens is good."** That is a real, never-measured question and it rides along free.

It is also a confound: a Python pack that underperforms could be the model, the language,
*or* the thin lens, and nothing in the pack distinguishes them. **Therefore the
bare-rubric control is not optional on the Python track** — it is the only way to
attribute a gap. Where the [open decisions](#open-owner-decisions) leave the bare-rubric
arm optional for the Swift packs, it is required here, and a lens-attributable gap is a
finding about `lens-generic.md`, not about Python.

### Harvesting rules, learned while building this register

- **pandas `REF:` is a systematic harvest.** pandas prefixes pure-refactor PR titles with
  `REF:` and labels them `Refactor`. That turns "find expert-reviewed behavior-preserving
  refactors" into a query. The Swift corpus has no equivalent and was assembled by
  archaeology. Prefer repos with an explicit refactor convention.
- **Exclusion rule: no lint-shaped cleanups.** Do not seed from mechanical sweeps
  (`dict.update({k: v})` → assignment, unused-import removal). They are real refactors and
  they are the wrong lesson: they train the Critic to chase surface idioms. This project
  already measured that failure — advisory evals #35–#48 produced **zero recall lift**
  because the seeded defects were too legible. Fixtures must separate judgment, not
  eyesight.
- **`is:unmerged` is unreliable on externally-reviewed repos.** SQLAlchemy PRs
  #12534/#12535/#12537/#12538 all read `merged=NO` on GitHub and look like a cluster of
  rejected drive-by refactors. They are not: SQLAlchemy reviews on Gerrit and mirrors to
  GitHub, so PRs close as "unmerged" even when the change lands (#12537's final comment is
  *"Gerrit review … has been **merged**"*). Any rejected-PR harvesting must exclude repos
  with external review systems, or the restraint corpus fills with accepted work.

### Ranked Python source register

Every row verified against upstream with `gh` on 2026-08-25 — state, author, merge date,
and diff size all checked, not taken from the proposal that suggested them.

| # | Source | Verified state | Why it is unusually valuable | Fit |
| --- | --- | --- | --- | --- |
| P1 | python/cpython #126408 + #132351 (`gh-125038` / `gh-127682`) | #126408 **closed unmerged** 2025-05-25 (efimov-mikhail, **+530/−318 across 17 files**, adds a `CHECK_ITERABLE` bytecode); #132351 **merged** 2025-04-11 (markshannon, core dev, **+27/−15 across 5 files** — of which the production change is `Python/codegen.c` **+1/−4**, the rest being tests and a NEWS entry) | The **same structural goal**, pursued at ~20× the size and rejected, then achieved in a one-line production edit and merged. Core-dev sobolevn's rejection is on the record: *"changing where the error happens is not safe in terms of backward compatibility."* The only case in either language where RED and GREEN are the same edit | Restraint spine — Layer 2 twins + Layer 3 case; recall cannot solve it |
| P2 | pandas-dev/pandas #65927 + #66027 | #65927 **merged** 2026-06-27 (jbrockmendel, +36/−3), labeled `Refactor`, body: *"This is a pure refactor (no behavior change)"*; #66027 **merged** 2026-07-15 (Saihritesh, +49/−5) | A core dev's behavior-neutrality **claim in its own PR body** that was false. #66027 opens: *"Following the `_python_apply_plot` refactor (#65927) … grouped `DataFrame` objects are no longer given a `.name` attribute"* — silently broke `GroupBy.plot.scatter(legend=True)`, corrected 18 days later with a regression test | Imperfect gold — does the reviewer *verify* a neutrality claim or *accept* it? Maps onto Reality/Honesty/Regression |
| P3 | pandas-dev/pandas #66091 | **Merged** 2026-06-30 (jbrockmendel, +26/−3, 1 file), labeled `Refactor`,`Reshaping` | `get_dummies` stops depending on `select_dtypes`' internal `ArrowDtype.numpy_dtype` unwrap; expresses the intended column set as a local `_is_encodable` predicate. Equivalence claimed across numpy, masked, Arrow string/dictionary, categorical, object | Canonical pure refactor — dtype truth table (Layer 2) |
| P4 | pandas-dev/pandas #66112 | **Merged** 2026-07-08 (jbrockmendel, +64/−30, 1 file), labeled `Refactor`; body: *"Behavior-neutral refactor… No user-visible change."* | Per-dtype predicate callables combined with `any`, replacing one frozenset-matched `dtype_predicate` — explicit groundwork for planned behavior-*changing* follow-ups | Predicate-equivalence pair + error/warning preservation |
| P5 | python/cpython #136815 | **Merged** 2025-07-22 (anistark, +19/−15, 9 files) | Normalizes `is_emscripten` / `is_wasi` under a shared `is_wasm32` flag — the Python analogue of Swift Collections #298's platform-conditional near-miss, where "these two checks are the same" is true in most cells and false in one | Platform truth table — restraint twin |
| P6 | pytest-dev/pytest #8913 | **Merged** 2021-08-01 (nicoddemus, +298/−173, 9 files) | String/`scopenum` scope handling replaced by a `Scope` enum while `FixtureRequest.scope` stays a `str` for public compatibility; the API trap is documented in the PR | Representation quality with a public/private boundary trap |
| P7 | pallets/werkzeug #2517 | **Merged** 2022-10-13 (TomiBelan, +42/−67, 2 files) | Three distinct socket `ResourceWarning` cases; PR argues why a naive `detach()` is *less* elegant and why consolidating through `make_server()` removes duplication without changing behavior | Resource-lifecycle refactor — warning-emission oracle |
| P8 | pydantic/pydantic #10725 | **Merged** 2024-11-08 (Viicos, +452/−268, 15 files) | Centralizes runtime typing checks across `typing` vs `typing_extensions`, `Annotated[ClassVar]`, stringified annotations; PR notes bugs fixed along the way | Runtime-typing zoo (Layer 2) |
| P9 | django/django `tests/auth_tests` | Verified at `main` | Backend, forms, decorator, handler and basic-auth surfaces — the Python counterpart to the Vapor auth material, drawn from the test surface rather than one PR | Security/policy mutants, four mini-packs |

### Python build order and what carries the signal

**P1–P4 are the Python triangle** and carry nearly all the judgment signal:
*refuse fake simplicity* (P1), *verify the neutrality claim* (P2), *refactor when it is
right* (P3, P4). Build P1 first.

P6 and P8 are the two largest diffs on the list (+298/−173 and +452/−268). Big diffs make
diffuse oracles and expensive construction — the Swift track's best value came from its
*smallest* pack (#298). They sort last and are the first candidates to cut if the track is
trimmed.

### Why P1 leads

Every near-miss the Python proposal originally offered was **synthetic** — authored by us,
then graded by us. The Swift track's cheapest and highest-signal pack, #298, is a
*maintainer-rejected* PR: a real human near-miss with the reasoning on the record. P1
restores that property and sharpens it, because RED and GREEN are the same edit:

- **RED** — #126408: the "redundant" `GET_ITER` removed via a new bytecode instruction,
  +530/−318 across 17 files, rejected. The redundancy was real; removing it that way was
  still wrong.
- **GREEN** — #132351: the same removal at +27/−15 across 5 files, of which the production
  change is a single `codegen.c` hunk (`+1/−4`) and the remainder is tests plus a NEWS
  entry — justified as restoring pre-3.12 behavior and making genexprs consistent with all
  other generators.
- **Test-oracle trap** — #132351 deletes a doctest from `Lib/test/test_genexps.py` that
  reads *"Verify that the outermost for-expression makes an immediate check for
  iterability"*, asserting `(i for i in 6)` raises `TypeError` at creation. The suite
  actively certified the wrong behavior, so **"tests pass" was worthless as an oracle** —
  the regression was found externally, by Nuitka's author using CPython as ground truth
  (issue #127682).
- **Mutant floor** — the original `gh-125038` crash repro
  (`g.gi_frame.f_locals['.0'] = range(20); list(g)`) must stay fixed. Naive guard removal
  **segfaults**: a hard, unmissable oracle no grader can argue with.

### Schema and validator

`contest-refactor/scripts/validate-gold-corpus.py` (shipped `e357a80`) is
**language-neutral** — it checks manifest shape, `variant_roles`, and hidden-mode
provenance leaks, never source language. **A Python pack needs no validator change to be
valid.**

If per-language axis fields (`python_axes`, `hidden_oracles`) are adopted, they are a
schema change to that validator **and** `_validate_gold_corpus_selftest.py`, done RED-first
as its own step *before* any pack is authored — so no pack is ever written against a schema
the validator rejects. Note the shipped schema already requires `variant_roles` over the
closed set `red`/`green`/`alternate_green`/`near_miss`/`mutant`; new fields must compose
with it rather than duplicate it.

**The leak check binds harder here.** Hidden-mode candidate-visible files must not carry
original PR numbers, SHAs, or upstream symbol names. `GET_ITER`,
`codegen_comprehension_iter`, `_python_apply_plot` and `select_dtypes` are exactly the
needles check 7 hunts, so every Python pack needs renaming before it goes candidate-visible.

### Cost

At this document's ~500k-per-pack anchor, nine Python packs is **~4.5M** — three times the
Swift tranche, and a second corpus rather than a second language. Two things should pull
the real figure down, and both are assumptions until measured:

- Python oracles are pure-Python asserts. No Swift toolchain, no SDK/platform matrix, no
  fixture-regeneration branch — the largest per-pack cost on the Swift side.
- P1–P4 come from two repos with one build story each.

**Build P1 and price the rest off its actuals.** If P1 lands materially under 500k the
track is cheaper than the Swift tranche despite having more packs; if it does not, cut to
P1–P4 and re-decide.

### What this track does *not* buy

Adding Python here **does not close the G17 promotion bar's second-language condition.**
That bar counts **adjudicated datapoints from live production runs against target repos**,
not eval fixtures — its live tally is 4/5 applicable runs, 0/2 restraint cases, and 1 of 2
required languages. Fixtures and run-adjudications are different evidence reaching the bar
through different mechanisms. Closing G17's language gap needs a **Python target repo in an
instrumented production run**, which is separate, much cheaper, and worth scheduling on its
own.

## Mapping to the existing eval layers

The feedback's layer table, corrected to this suite's actual six layers
(`evals/README.md`):

| Layer / mechanism | Best external cases | Notes |
| --- | --- | --- |
| Layer 1 — artifact-rule | — | No fit, by design: these are judgment cases, not gate rules. Provenance/manifest validators for the corpus itself are the only deterministic additions. |
| Layer 2 — refactoring-judgment (scenarios) | #688 twins, #298 (upgrade of #13/#15), #2959 fake-fixes (upgrade of #12/#14), Vapor mutants, #1801 triple, #488 restraint, #2486 oracle pair | Every pack lands here first; all follow the flag/restraint-pair discipline and the de-leak authoring rule. |
| Layer 3 — reviewer-judgment (reviewer-cases) | #688 NEAR-MISS, #2486 regression diff, TCA residual-only | `{targeted finding, diff} → verdict` grain; reference verdicts written from the upstream resolution. |
| Layer 4 — loop-replay | TCA staged chain (before → refactor → residual → final) | Heaviest pack; needs loop fixtures, so it is Tier-2 despite the signal value. |
| Layer 5 — execution-grain (Step 3 isolation) | #2486 regression MUTANT, #688 NEAR-MISS as an Actor task | "Does Step 3 catch the semantics regression the suite blesses" — the direct Meta-Rule 4 execution test. |
| Layer 6 — scorecard coupling | #688 GREEN, TCA accepted-refactor, #298 rejection | Scorecard-anchoring: clean expert code scores without deduction; imperfect gold holds at 9.5, not 10. |
| Step-0 hotspot scanner + G49/G50 triage | #185, #814 (+ #488 as a non-hotspot control) | Scanner nominates / Critic dismisses — the restraint regression test for the pipeline. |
| Step-3 risk-boundary evidence (Meta-Rule 4) | #2959 mutants, #298, #2486 | Each crosses an enumerated risk boundary; evidence-recording behavior is gradeable. |
| Actor execution at scale | RefactorBench/Anvil borrowings | Out of near-term scope — borrow harness structure only (see below). |

## Relationship to the closed detection programme — read before building

The single largest correction to the feedback, and the reason this document exists as a
plan rather than a work order:

The detection programme is **closed** (2026-08-22): fourteen candidates disposed, four
measured and all four legible 5/5, five parked on class evidence, one shipped prose
change (44 tokens, restraint). The register's own summary: "the sweep found real reach
gaps in the *prose*, and measurement found none of them in the *reviewer*."

The feedback, reading the register from outside, treats the corpus primarily as
*detection* material ("Critic domain recall" rows, RED-first framing). Built that way it
would predictably re-buy zero-lift: these real defects are, if anything, *more* legible
than the synthetic ones — they are the exact defect classes famous PRs exist to fix.

Built the adapted way, the corpus serves what the measurements say pays:

1. **Restraint** — the only axis where added prose measurably paid (DD-13), and the
   axis the feedback itself calls "your biggest risk now." GREEN and NEAR-MISS siblings
   are restraint instruments; the register's 15-reps-zero-false-positives control-arm
   hygiene note says exactly why real near-misses beat synthetic ones: "a clean
   *surrounding* change is an easier near-miss than a pattern that genuinely resembles
   the defect."
2. **Calibration** — scorecard anchoring on expert-accepted code (#688 GREEN, TCA,
   #298's rejection), which no current fixture provides from external provenance.
3. **Execution** — Layer-5 MUTANTs testing whether Step 3 catches what its own Meta-
   Rule 4 promises, with the implementation reviewer rather than a grader as the
   instrument.
4. **Pipeline regression controls** — scanner/hotspot restraint (#185, #814) guarding
   an integration that currently has no negative control.
5. **Closure hardening** — packs #2/#9 are real-world-shaped fixtures for the parked
   DD-01/DD-03/DD-05 classes. The parks are explicitly reversible ("ask for the run and
   it gets one"); if a bare-rubric control misses where it caught the synthetic
   fixture, that is the behavioural miss that reopens the row. Run them as controls,
   report either way, and let the register — not this document — record the outcome.

Cost discipline, priced from the register's own runs: a measurement run is ~500k
subagent tokens; a five-rep two-arm pack is that order. The first three packs (~1.5M
tokens) buy the triangle the feedback correctly identifies as the core muscle — *know
when to refactor (#688), know what behavior must survive (#2486), know when not to
(#298)* — and every pack after that should justify itself against those three.

## Benchmark methodology borrowings

Scoped to what transfers; nothing here imports another benchmark's tasks as gold.

- **Swift Anvil** — borrow the harness shape only: `base_commit` / task provenance /
  gold patch / visible tests / hidden adversarial tests / oracle verification /
  N attempts, with the objective changed from "implement the request" to "critic
  judgment / refactoring preference / behavioral preservation." Anvil itself is young
  (2 stars); its task quality is not authoritative. The oracle-agent concept — apply
  the gold patch, everything must pass, harness is thereby verified — is directly
  reusable for MUTANT fixtures: apply the mutant, the targeted test must *fail*.
- **RefactorBench** (ICLR 2025) — Actor-execution regressions: multi-file tracking,
  blast-radius reasoning, stateful loop behavior, adherence to compound instructions.
  Correctly deprioritized for Critic judgment: its tasks already prescribe the refactor.
- **CodeTaste** (ICML 2026) — the closest philosophy to this suite's: human-refactoring
  ground truth, test suite + static checks in containers, 5× flakiness reruns, and an
  alignment score that "only rewards rule compliance when tests are valid" — the same
  tautology guard this suite's `criterion_class` axis implements. Borrow: instance
  selection discipline, patch scoring shape, flaky-test handling. Note its own finding
  mirrors this repo's: agents execute specified refactorings far better than they
  *discover* the human choice — the discovery gap is the open question both suites
  share.
- **SWE-Refactor** — language is wrong for the primary path, but the dataset
  construction methodology is the strongest on record and matches what this corpus
  should do: real commit → pure-refactor filtering → base revision → developer patch →
  compilation verification → test verification → atomic vs compound taxonomy.

## Performance gates

Adopted with the feedback's own constraint, which matches the skill's existing posture
(Meta-Rule 1 — metrics support judgment, never decide it): attach benchmark
preservation **only** where the historical case itself carries a performance contract —
TCA #3460 (its PR cites a benchmark win), #1801, BigString #488 (benchmark chart
attached), Async Algorithms #185 (author-reported throughput). For those cases only:
tests pass + architecture improves + benchmark within tolerance. Never a universal
gate; efficiency-lens D1–D4 reasoning is unaffected.

## Corpus structure and provenance schema

Under `contest-refactor/evals/gold-corpus/` (committed, unlike gitignored
`refs/competitors/`), one directory per case, each carrying the feedback's four-state
shape:

```text
evals/gold-corpus/
  swift-collections-688/
    provenance.json
    red/ (red)  gold/ (green)  near-miss-direct-replace/ (near_miss)  alternate-gold-exchange/ (alternate_green)
    grading.md
  swiftnio-2486/
    provenance.json
    wrong-contract/ (red)  fixed/ (green)  oracle-trap/ (near_miss)  regression-mutant/ (mutant)
    grading.md
  …
```

(role tags in parens are illustrative — the real value lives in each pack's `variant_roles`,
below; the two examples deliberately use unrelated directory names for the same roles.)

`provenance.json`, per case — second-round schema, which demotes "gold" from a crown to
a provenance tag (`accepted_*` + `gold_confidence` instead of `gold_sha`; merged code
is *what was accepted*, never *what is true*):

```json
{
  "source_repo": "apple/swift-collections",
  "source_pr": 688,
  "base_sha": "…",
  "accepted_sha": "…",
  "accepted_state": "merged | rejected | reverted | contested | superseded",
  "gold_confidence": "high | contested | longitudinally_corrected",
  "subsequent_correction": {
    "pr": 3845,
    "sha": "…",
    "kind": "residual_cleanup"
  },
  "prompt_exposure": "provenance_hidden",
  "fixture_role": "semantic_duplication",
  "variant_roles": {
    "red": "red",
    "gold": "green",
    "near-miss-direct-replace": "near_miss",
    "alternate-gold-exchange": "alternate_green"
  },
  "expected_judgment": "…",
  "candidate_visible_files": [],
  "grader_only_files": ["provenance.json"],
  "must_find": [],
  "must_not_find": [],
  "allowed_findings": [],
  "residual_findings": [],
  "must_find_if_present": [
    {
      "evidence_id": "…",
      "applies_to_variants": ["…"],
      "required_finding": "…",
      "not_required_in": ["…"]
    }
  ],
  "hidden_oracles": [
    {
      "name": "duplicate_diagnostic_preserved",
      "variant_expected_to_fail": "near-miss-direct-replace"
    }
  ],
  "behavior_contract": [],
  "restraint_reason": null,
  "applicable_domains": [],
  "license": {
    "spdx": "Apache-2.0",
    "attribution": "Derived from apple/swift-collections#688"
  },
  "contamination": {
    "renamed": ["…"],
    "minimized_from": "…",
    "why": "…"
  }
}
```

Field semantics the fixtures rely on:

- **`accepted_state` / `subsequent_correction`** carry the imperfect-gold theme as
  data: #2959 is `merged` + `contested` (its revert draft exists, unmerged); TCA #3460
  is `merged` + a `subsequent_correction` pointing at #3845 (`residual_cleanup`);
  #298 is `rejected` — its *rejection* is the fixture.
- **`prompt_exposure`** implements the leakage split — renaming symbols is not enough
  when the source PRs may live rent-free in model weights:

  | Mode | Candidate sees | Purpose |
  | --- | --- | --- |
  | `provenance_hidden` | minimized, renamed fixture only | Measures actual judgment |
  | `provenance_labeled` | source repo/PR context allowed | Measures how much public context helps |

  **Run-mode policy (settled, third round).** `provenance_hidden` is the primary build
  *and* run mode: every pack is built hidden and its hidden baseline is taken first.
  `provenance_labeled` is a **contamination-sensitivity assay**, not the main eval — it
  answers "do provenance leaks change behavior," and it runs **once, as a batch
  calibration pass over the finished packs**, promoted to per-pack routine only if that
  batch shows a meaningful and stable difference. Running it per-pack across builds 1–8
  would double cost before any hidden baseline exists and muddy the question the packs
  are built to ask, while the fixtures are still being hardened. One exception: a pack
  whose whole purpose *is* provenance reasoning ("recognize an imperfect accepted patch
  from longitudinal history") may treat labeled mode as a first-class variant — none of
  the first eight qualify.
- **`must_not_find` is mandatory on every case** — the negative oracle is the point.
  **Vocabulary (settled, third round):** `must_find`, `must_not_find`,
  `allowed_findings`, `residual_findings` are canonical. The first-round names
  `must_notice` / `must_not_claim` survive only as **rejected legacy aliases** — the
  manifest validator fails on them with migration text (`Use must_find, not
  must_notice.` / `Use must_not_find, not must_not_claim.`) rather than quietly
  accepting either spelling. Grading specs written against the old names must translate.
- **`variant_roles`** is a required map from each variant directory name to its role —
  `red`, `green`, `alternate_green`, `near_miss`, or `mutant`, the closed set the
  role-dependent manifest checks below (RED/GREEN/NEAR-MISS/MUTANT) key off. Directory
  naming is per-case, not a convention: the two worked examples above use entirely
  different names for the same five roles, so the checks need an explicit tag rather
  than a naming guess. The manifest validator requires this field and fails a pack that
  omits it.
- **`must_find_if_present`** is the conditional half of the same contract, and the one
  field with structure instead of strings: `evidence_id`, `applies_to_variants`,
  `required_finding`, `not_required_in`. It exists for scanner-restraint packs (#185,
  #814) where the pristine fixture must produce *no* finding while a seeded mutant
  sibling must produce a specific one. Schema-level so neither half can drift into the
  other's variants.

**Manifest validator (Layer-1 territory — deterministic, no model):** a small script
the corpus ships with, which fails the build when:

- any pack lacks at least one RED and one GREEN-or-accepted variant;
- any NEAR-MISS lacks at least one `must_not_find` entry;
- any pack uses the rejected legacy aliases `must_notice` / `must_not_claim` (the
  validator emits the migration text, never an accepted synonym);
- any `must_find_if_present` entry names a variant directory that does not exist, or
  lists the same variant in both `applies_to_variants` and `not_required_in`;
- any MUTANT lacks a hidden test or static oracle that demonstrably fails the mutant;
- any `provenance.json` is candidate-visible unless the pack explicitly declares
  `prompt_exposure: "provenance_labeled"`;
- in hidden mode, any candidate-visible file contains original PR numbers, commit
  SHAs, or real upstream symbol names (the leak check that makes renaming auditable
  rather than aspirational).

Tiny gatekeeper, big goblin net — and it is the one part of this corpus that belongs to
Layer 1's artifact-rule grain, not to any model-dispatched layer.

## The first fixture packs, adapted

Second-round build order, adopted (deltas from the first draft: #298 and #2486 swap —
#298 is the cheapest build, reusing the #13/#15 template; #488 enters the ordered list
gated on its stable-identity tests existing first; #185/#814 sit explicitly at the
scanner-control slot; TCA is last, tied to Layer-4 machinery):

1. **Swift Collections #688** — highest signal, purest refactor, best calibration
   anchor; executable oracles (trap message + lookup count) land with it.
2. **Swift Collections #298** — platform-conditional restraint (upgrade of #13/#15);
   cheapest — nearly free given the template, truth-table encoded.
3. **SwiftNIO #2486** — the test-oracle trap, built as a toy channel lifecycle state
   machine; the contract is observable and the judge has no "tests pass" escape.
4. **SwiftNIO #2959** — concurrency fake-fix archetypes (upgrade of #12/#14) +
   contested-gold calibration.
5. **SwiftNIO #1801 + #1807** — representation over bit-twiddling, with round-trip
   boundary tests.
6. **Swift Collections #488** — representation restraint; only after the
   stable-identity oracles (touched-chunk-count, ≤255 compared units) are written.
7. **Vapor AuthenticationTests mini-packs** — four small packs
   (challenge/error-detail/concurrent-login/empty-password restraint).
8. **Async Algorithms #185 + NIO #814** — scanner/Critic restraint controls, graded
   through the negative oracle.
9. **TCA #3460/#3845** — heaviest (architecture + residual accounting + micro-
   deletion); lands with Layer 4 once the harness is proven on packs 1–8.

Packs 1–3 first: they are the triangle — *refactor when it is right (#688), refuse fake
simplicity (#298), know what behavior must survive (#2486)* — they upgrade existing
pairs (cheapest integration), and pack 2 is nearly free given #13/#15 exist as the
template. Every pack after that justifies itself against those three.

**Then the Python track, P1–P9** — see [Python track — second
language](#python-track--second-language) for its register, rationale, and cost. It is
sequenced deliberately after the Swift triangle so the harness is proven on Swift before a
second language is added, and its own build starts with **P1**
(`cpython-genexpr-iterability`), whose actuals price the rest of that track. Note the
Python triangle is P1–P4, not P1–P3: Python contributes a fourth shape the Swift set has no
instance of — *a pure-refactor claim, made by an expert in the PR body, that was false*.

**Then, once — not per pack.** After the hidden baselines exist for the packs that got
built, the `provenance_labeled` batch calibration pass runs as its own step (see the
[run-mode policy](#corpus-structure-and-provenance-schema)). It is a step in this plan,
not a second arm bolted onto every pack, and it earns per-pack promotion only by showing
a meaningful, stable difference in that batch.

## Open owner decisions

Two that stood open after round two are **settled** and now live where they are
enforced, not here: the `provenance_labeled` arm's timing (hidden is the primary run
mode; labeled is one batch assay afterwards) and the schema vocabulary (`must_find` /
`must_not_find` canonical, first-round names rejected as aliases) — both in
[Corpus structure and provenance schema](#corpus-structure-and-provenance-schema). What
remains open:

- **Spend.** ~500k tokens per pack-order-of-magnitude; first three packs ≈ 1.5M.
  Same approval shape as a detection-programme measurement run, but aimed at fixture
  construction + control runs rather than prose lift. **The cost objection itself is
  settled (owner, 2026-08-25): 1.5M is small against a production run at ~20M+ resident
  context, so spend is not the binding constraint.** What remains open is the Python
  track's ~4.5M at the same anchor — decided by measuring P1 and pricing the rest off its
  actuals, not by estimate; see [Cost](#cost).
- **Bare-rubric control — settled for Python, still open for Swift.** The control is
  **required** on the Python track, because a thin shared `lens-generic.md` (85 lines
  across seven languages) versus a deep `lens-apple.md` (252 lines) means an unattributed
  gap could be the model, the language, or the lens. It stays optional on the Swift packs
  as described below.
- **Closure-hardening runs (packs 3 and the Vapor mini-packs).** Run the bare-rubric
  control on the real-world fixtures for the parked DD-01/DD-03/DD-05 classes? The
  parks are reversible by design; this is the cheapest possible way to stress them,
  and either outcome is publishable in the register.
- **Where GREEN anchors score.** Confirm the calibration rule: expert-accepted GREEN
  fixtures are expected to score 9–9.5 *without* zero findings if the case carries a
  documented residual (TCA, #2959) — the 9.5-vs-10 distinction needs a written rule
  before grading, or graders will invent one per-case. `gold_confidence:
  "contested"` and `"longitudinally_corrected"` are the two states that force this
  rule to actually get written.
- **Anvil/RefactorBench harness borrowings.** Deferred here; adopting any external
  harness machinery is its own plan with its own review, not part of pack construction.

## Items not independently verified

Recorded so a later pass knows what rests on what:

- **Swift project regression-test methodology** (focused regression tests at the
  nearest abstraction level, cross-platform suites): consistent with the swift-org
  contributing guidance as commonly cited; the CONTRIBUTING.md itself was not fetched.
  The *rule* is adopted into fixture authoring regardless — it matches the suite's
  existing one-fixture-one-distinction discipline.
- **Apple's Swift 6 migration guidance** (per-module complete checking, resolve, then
  Swift 6; keep major refactors separate from concurrency migration): consistent with
  Apple's published "Adopting strict concurrency" articles; not re-fetched. NIO's own
  #2959→#2980 sequence is the verified instance of exactly this discipline being hard
  to hold.
- **Fluent transaction-isolation discussion** (isolation settings are connection-local;
  queries may run on another connection without explicit ownership): plausible and
  matches Fluent's API shape; not fetched. Tier-2 material anyway.
- **The "real migration writeup"** backing the blanket-`@MainActor` bad-strategy seed:
  unnamed in the feedback; the failure mode itself (errors disappear, architecture
  cascades) is widely reported and the mechanism is sound, so the seed stands on the
  mechanism, not the citation.

## Related

- [`contest-refactor-detection-domains.md`](contest-refactor-detection-domains.md) —
  the closed detection programme this corpus must not silently reopen; the promotion
  bar any reopened row must clear; the restraint-is-what-pays finding that sets this
  corpus's priorities.
- [`contest-refactor-review-register.md`](contest-refactor-review-register.md) — the
  eval architecture (trial validity, paired lift, noise floor, discriminating power)
  the packs run inside.
- `contest-refactor/evals/README.md` — the six layers and the flag/restraint authoring
  discipline every pack inherits.
- Upstream sources: [swift-collections#688](https://github.com/apple/swift-collections/pull/688),
  [#298](https://github.com/apple/swift-collections/pull/298),
  [#488](https://github.com/apple/swift-collections/pull/488),
  [swift-nio#2486](https://github.com/apple/swift-nio/pull/2486),
  [#2959](https://github.com/apple/swift-nio/pull/2959) (+[#2980](https://github.com/apple/swift-nio/pull/2980)),
  [#1801](https://github.com/apple/swift-nio/pull/1801),
  [#814](https://github.com/apple/swift-nio/pull/814),
  [swift-async-algorithms#185](https://github.com/apple/swift-async-algorithms/pull/185),
  [TCA#3460](https://github.com/pointfreeco/swift-composable-architecture/pull/3460) /
  [#3845](https://github.com/pointfreeco/swift-composable-architecture/pull/3845),
  [Vapor AuthenticationTests](https://github.com/vapor/vapor/blob/main/Tests/VaporTests/AuthenticationTests.swift),
  [Swift Anvil](https://github.com/AfterQuery/swift-anvil),
  [RefactorBench](https://github.com/microsoft/RefactorBench),
  [CodeTaste](https://github.com/logic-star-ai/codetaste).
