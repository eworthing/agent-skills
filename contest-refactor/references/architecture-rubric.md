# Architecture Rubric

Vocabulary, smells, severity anchors, and score anchors. Adopted from `/improve-codebase-architecture` (ICA) and the iOS Swift contest review prompt. Use these terms exactly. Reject "component," "service," "API," "boundary" — overloaded, drift-prone. Consistent vocabulary keeps scorecard deltas honest across loops.

## Contents

- [Vocabulary — Architecture](#vocabulary--architecture)
- [Vocabulary — Smells (use only in this exact sense)](#vocabulary--smells-use-only-in-this-exact-sense)
- [Smell List (smoke, not findings)](#smell-list-smoke-not-findings)
- [Architectural Tests](#architectural-tests)
- [Unified Seam Policy](#unified-seam-policy)
- [Dependency Categorization](#dependency-categorization)
- [Severity Anchors](#severity-anchors)
- [Score Anchors](#score-anchors)
- [CONTEXT.md / docs/adr Awareness](#contextmd--docsadr-awareness)

## Vocabulary — Architecture

- **Module** — interface plus implementation. Not merely a folder, file, target, or type. Scale-agnostic.
- **Interface** — everything a caller must know to use a Module correctly: types, invariants, error modes, ordering, config, performance characteristics.
- **Implementation** — code inside the Module.
- **Seam** (Feathers) — where an Interface lives. Place where behavior can be altered without editing in place.
- **Adapter** — concrete thing satisfying an Interface at a Seam. Role, not substance.
- **Depth** — leverage at the Interface. Deep = much behavior behind small Interface. Shallow = Interface ≈ Implementation.
- **Leverage** — what callers get from Depth. One Implementation pays back across N call sites + M tests.
- **Locality** — what maintainers get from Depth. Change, bugs, knowledge concentrate in one place.

Prefer these terms over vague phrases such as "clean code," "well structured," "decoupled," or "nice architecture."

## Vocabulary — Smells (use only in this exact sense)

- **Architecture costume layer** — folder, protocol, target, or naming scheme that suggests architecture but does not control writes, dependencies, or runtime authority. **Sub-pattern: rule-driven sidecar.** A `final class` whose body is `var x; var y; init() {}`, paired with another class that holds a `let` reference to the first and is the *only* writer; doc string explains the split as "the boundary rule says executors / handlers / managers must not own mutable stored vars." The mutable state still exists, still belongs to one writer, and is now spread across two files. Self-imposed style rules that produce 1:1 sidecars are themselves the costume layer — flag the sidecar AND the rule. The rule is purchasing nothing the type system can verify.
- **Repository theater** — repository/protocol split with one real Adapter where the Interface adds no policy, failure isolation, replacement value, or Locality.
- **Protocol soup** — many protocols with shallow Interfaces, one real Adapter each, justification limited to testability.
- **Fake simplification** — shorter code that hides ownership, failure behavior, state transitions, or async lifetime.
- **Fake-clean reward** — scoring up because names, folders, comments, previews, or test count look tidy while ownership, seams, or tests are weak. **Sub-pattern: aggregate-test-count-as-test-strategy.** Loop sees N passing tests, scores `test_strategy` ≥ 9 without auditing which surfaces have direct test files. Authority Map cross-check (lens-apple.md, method.md Step 8) is the corrective: walk each concern, confirm a direct test file exists. Shell seams (`AppRuntime`, root scene, URL guard) and contest-relevant feature flows (multi-branch entry views) need direct tests, not transitive coverage from deep reducer tests. **Sub-pattern: suppression-as-fix.** Resolving a finding by silencing its signal rather than fixing the structure. Two risk classes: **safety-affecting** suppressions (`@unchecked Sendable`, `nonisolated(unsafe)`, `# type: ignore` on a real type error, `#[allow(...)]` over an unsound op) count as fake-clean reward **unless** they carry narrow scope + concrete justification + the compensating invariant that makes them safe (plus a removal condition when temporary); **style/tooling** suppressions (`// swiftlint:disable line_length`, formatter ignores) are lower risk and need only narrow scope + justification. A safety suppression standing in for a real fix leaves the hazard intact and unreported — score the underlying finding, not the silenced warning.
- **Anchored-to-history confirmation** — fresh critic loop starts by reading the prior `CURRENT_REVIEW.md`, then writes a scorecard that "confirms" the prior verdict without re-deriving any dimension's score from current source. Prior `8.6 → 9.5` jumps with no diff between loops are the visible symptom. Cure is in `method.md` Step 1: re-derive the scorecard from source first, consult the prior review only after the independent score is written.

## Smell List (smoke, not findings)

Investigate as smoke. Do not turn into findings unless source evidence proves harm.

- unclear ownership
- multi-writer state
- hidden control flow
- hidden async behavior
- framework leakage
- persistence leakage
- misleading abstractions
- temporal coupling
- overbuilding
- weak domain model
- old authority still alive
- polished shallow structure
- fake simplification
- duplicate abstractions
- duplicate state
- unclear task lifetime
- unclear cancellation
- unclear actor isolation
- architecture costume layers

Prioritize: one owner per mutable concern, explicit data flow, honest failure behavior, maintainable seams, clear async runtime behavior, tests at the right surface, Leverage, Locality.

Ignore: stylistic concerns, tiny naming nits, micro-optimizations, generic filler, unsupported speculation.

## Architectural Tests

Every "remove this abstraction / extract this seam / collapse this layer" finding cites which test failed.

### 1. Deletion test
Imagine deleting the Module.
- Complexity vanishes → pass-through. Delete it.
- Complexity reappears across N callers → earning its keep. Leave it.

### 2. Two-adapter rule (one of two seam-justification paths)
- One Adapter = hypothetical seam. Indirection.
- Two Adapters (typically prod + behavior-faithful test fake) = real Seam.

A protocol/port with one production impl and zero behavior-faithful test fakes fails this rule on its own. It can still be justified under the alternate path (single-Adapter policy/failure/platform isolation) — see **Unified Seam Policy** in `SKILL.md` Step 2 for the full decision rule. Bare protocol conformance for testability without a behavior-faithful fake = protocol soup; reject.

### 3. Shallow module test
Compare Interface complexity to Implementation complexity.
- Interface ≈ Implementation → shallow. Inline it or deepen the Implementation.
- Implementation >> Interface → deep. Healthy.

### 4. Interface-is-test-surface
Tests live at the deepened Module's Interface. If a test changes when the Implementation changes, the test was past the Interface. Wrong shape.

### 5. Replace, don't layer
When a refactor deepens a Module, old unit tests on the now-shallow Modules become waste. Delete them. Write new tests at the new Interface. Refactors that accumulate tests at both levels score lower on regression resistance.

**Indirect Interface coverage carve-out**: when the deepened Module is reached transitively through an already-tested upstream Interface (e.g., a private helper consolidated inside a reducer arm; the reducer-arm tests then constitute the test-at-new-Interface), the rule is satisfied iff:

(i) the upstream Interface is itself tested with assertions that cover the transitively-deepened behavior;
(ii) the loop's `loop_result.interface_test_coverage_path` cites specific test file(s) and assertion line ranges; AND
(iii) each cited assertion both **references the `target_symbol`** AND **asserts behavior that distinguishes the deepened code path from a no-op** (e.g., the assertion would fail if the `target_symbol`'s body were replaced with `fatalError()`).

`target_symbol` = either a newly-introduced symbol OR an existing symbol whose behavior was materially deepened this loop. Inlining and flattening refactors that deepen an existing symbol satisfy the carve-out when assertions exercise the deepened existing symbol; they need not introduce a new identifier.

The loop subagent identifies `target_symbol` from `loop_result.what_changed` (must be a single specific identifier; if multiple symbols were deepened, list them all). Bare "the reducer tests cover it" without specific symbol+behavior citation fails the carve-out.

## Unified Seam Policy

<!-- CANONICAL: Unified Seam Policy lives here. Other files MUST reference, not restate. -->

A new or restructured Seam is justified iff at least one of the following is true:

(a) **Two-adapter rule met** — at least two real Adapters will exist (typically prod + behavior-faithful test fake or local substitutable). A recording stub that only records calls without simulating behavior does NOT count as the second Adapter (see ADR pattern from `BenchHypeTestSupport/Doubles/`). Bare protocol conformance does not count.

(b) **Single-Adapter policy / failure / platform isolation** — the single Adapter encodes one of:
- (i) a policy decision (rate limiting, retry, idempotency)
- (ii) failure isolation that the deletion test confirms would otherwise spread across N callers
- (iii) platform isolation (an SDK with no test harness, e.g. Spotify SDK, hardware-bound APIs)

The finding cites which of (i) / (ii) / (iii) applies.

If neither (a) nor (b) holds, the Seam fails the policy. Inline the implementation; merge the Module. Bare testability without behavior-faithful fake → protocol soup; reject.

## Dependency Categorization

Each Coupling & Leakage finding tags the dependency category. Determines correct seam strategy.

| Category (display) | Machine enum | Description | Seam strategy |
|---|---|---|---|
| **In-process** | `in-process` | Pure computation, in-memory state, no I/O | No seam needed. Merge modules, test through new interface. |
| **Local-substitutable** | `local-substitutable` | Real dep with local test stand-in (PGLite, in-memory FS, recording double) | Internal seam. Stand-in runs in test suite. No port at external interface. |
| **Remote-owned** | `remote-owned` | Own services across network (microservices, internal APIs) | Define port at seam. HTTP/gRPC/queue adapter for prod, in-memory adapter for test. |
| **True-external** | `true-external` | Third-party (Stripe, Twilio, Spotify SDK) | Inject port. Mock adapter for test. |

**Rule**: machine enum strings (right column) are the only allowed values in JSON `dependency_category` fields and in Findings markdown. Display strings (left column) appear only in section headings.

## Severity Anchors

Use these anchors to assign finding severity. Drives backlog priority and verdict.

- **Likely disqualifier** — A core architectural property the contest rewards is broken at runtime AND the harm is reachable from a primary user flow. Examples: multi-writer authority over a primary domain concern; racing async flows that can corrupt user-visible state; durable state written from multiple places with no owner; domain-policy framework leakage propagating through the codebase; **test absence around central mutable runtime behavior with realistic regression risk** (e.g. reducer/engine, persistence writer, cancellation logic, navigation owner). Untested helper code or off-path utilities are not disqualifying — keep this severity for the modules whose breakage would change product behavior on a primary flow.
- **Serious deduction** — A real ownership, Seam, state, data-flow, or concurrency hazard exists in a meaningful Module, but it is contained or local. A reasonable judge could still rank the entry highly with this present.
- **Noticeable weakness** — A source-backed concern that does not threaten contest standing on its own but reduces credibility, Leverage, Locality, or regression resistance when combined with other issues.
- **Cosmetic for contest** — Real but minor. Worth fixing, but it will not affect verdict or score unless part of a larger pattern.

## Score Anchors

Moved to [architecture-rubric-scoring.md](architecture-rubric-scoring.md) — the 9.5+ threshold, strictness presets, terminal normalization, and the nine per-dimension anchors. Critic scoring reference (Step 1); kept out of the Step-3 reviewer's read (it does not re-score).

## CONTEXT.md / docs/adr Awareness

Read `CONTEXT.md` (or `CONTEXT-MAP.md` + per-context `CONTEXT.md`) and `docs/adr/` in Step 0 if present.
- Use domain vocabulary in evidence: "Order intake module," not "OrderHandler."
- Findings contradicting an existing ADR must say so explicitly: _"contradicts ADR-0007 — but worth reopening because…"_. Do not silently propose forbidden refactors.
- Decisions logged in ADRs are not re-litigated unless friction is real enough to warrant it.

If neither file exists, proceed silently. Do not flag absence or suggest creating them upfront.
