# Architecture Rubric

Vocabulary, smells, severity anchors, and score anchors. Adopted from `/improve-codebase-architecture` (ICA) and the iOS Swift contest review prompt. Use these terms exactly. Reject "component," "service," "API," "boundary" — overloaded, drift-prone. Consistent vocabulary keeps scorecard deltas honest across loops.

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
- **Fake-clean reward** — scoring up because names, folders, comments, previews, or test count look tidy while ownership, seams, or tests are weak. **Sub-pattern: aggregate-test-count-as-test-strategy.** Loop sees N passing tests, scores `test_strategy` ≥ 9 without auditing which surfaces have direct test files. Authority Map cross-check (lens-apple.md, method.md Step 8) is the corrective: walk each concern, confirm a direct test file exists. Shell seams (`AppRuntime`, root scene, URL guard) and contest-relevant feature flows (multi-branch entry views) need direct tests, not transitive coverage from deep reducer tests.
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

Calibrate every score against these. The scorecard has 9 dimensions; each has explicit anchors below. Apply consistently across the full scorecard.

### 9.5+ Threshold (the contest target)

A score of **9.5+** (and < 10) on a category requires:

1. The dimension's **9-anchor** is met in current source.
2. The text identifies **the residual local issue blocking 10** (one specific file:line / symbol / Module). If no residual issue can be named, the correct score is 10.
3. The residual is dispositioned in one of two ways:
   - **Accepted** — documented inline in the Scorecard reason with rationale (e.g., framework constraint, deliberate carve-out tied to ADR). Compatible with `HALT_SUCCESS` if every category reaches this state.
   - **Queued** — added to the Improvement Backlog. While any category has a queued residual, system flag stays `CONTINUE`; `HALT_SUCCESS` is unreachable.

A 9.5 without an identified residual is fake-clean reward. Downgrade to 9.

`HALT_SUCCESS` requires every scorecard category at 10, OR at 9.5+ with an **accepted** residual. Any **queued** residual blocks `HALT_SUCCESS`.

Terminal normalization rule: before any HALT emit, a category at 9 cannot mean
"excellent but I did not account for the last local concern." If the 9-anchor is
met and no Noticeable-or-worse fix remains, promote the category to 9.5 with an
accepted residual, or to 10 if no source-backed residual can be named. Keep a
category below 9.5 at halt only when the review names a source-backed blocker
showing the 9-anchor is not met and explains why that blocker is not a valid
backlog item.

### Architecture quality
- **10** — Module graph enforced by source. Every Seam either has real Adapter variation or encodes policy, failure isolation, or platform isolation that survives the deletion test. No pass-through wrappers. No costume layers. No Repository theater. No Protocol soup. Ownership of every mutable concern traceable from one Module. A senior reviewer cannot identify a structural improvement that preserves behavior and improves Leverage or Locality.
- **9** — Contest-grade. Module graph enforced by source, not convention. Interfaces have Depth. Seams either have real Adapter variation or encode policy/failure isolation. Deletion tests leave little pass-through structure.
- **7** — Good but not winning. Main ownership clear, but some seams shallow, lifecycle authority spread, or one or two wrapper Modules fail the deletion test.
- **5** — Middling. Architecture traceable, but callers must learn too many files, navigation or presentation ownership drifts, multiple seams exist mostly for testability.
- **3** — Compromised. Multiple writers own the same concern, framework policy leaks into domain, Module names imply boundaries that writes ignore.

### State management and runtime ownership
- **10** — One owner per mutable concern, proven by source. Runtime, persisted, navigation, presentation state separated by Module, not by convention. Every writer explicit and reachable from the owner. No hidden state machines. No duplicated state across layers. No invalid state combinations representable.
- **9** — One owner per mutable concern, including process lifetime. Writers explicit. Runtime, persisted, navigation, presentation state separated.
- **7** — Domain state ownership strong, but lifecycle, presentation, or task lifetime authority spread across several Modules.
- **5** — State mostly understandable but relies on convention, broad mutable access, or duplicated UI/domain state.
- **3** — Multi-writer state, hidden state machines, or stale authority remain alive.

### Concurrency and runtime safety
- **10** — Actor isolation, task lifetime, cancellation, Sendable boundaries explicit and enforced by the type system. No unstructured Task without a documented owner and a cancellation path. Async tests prove ordering deterministically. No reentrancy hazards. Strict concurrency checking passes without suppression.
- **9** — Actor isolation and task lifetime explicit. Cancellation owned. Async tests prove ordering without sleeps. No unstructured Task without documented ownership.
- **7** — Isolation mostly right, but some fire-and-forget tasks, lifecycle gaps, or timing-based tests remain.
- **5** — Async flows work by convention. Cancellation or reentrancy behavior requires reading scattered code.
- **3** — Racing async flows, unclear actor isolation, or unsafe shared mutable state likely.

### Test strategy and regression resistance
- **10** — Tests target real Interfaces and survive refactor. Failure paths, cancellation, async ordering covered without sleeps or timing hacks. Stateful Modules have meaningful tests at the right surface. Suite would catch a contest-relevant regression introduced by a future change. Authority Map cross-check passes: every concern with `verdict: Single and clear` has at least one test exercising its mutation paths through the Interface; every shell seam (`AppRuntime`, root scene, URL/scene-phase bridges) has a direct test file; every contest-relevant feature flow has feature-surface tests for present/dismiss + cancel + branch coverage.
- **9** — Tests target real Interfaces, assert outcomes, avoid sleeps, cover failure paths, protect architecture boundaries. Authority Map cross-check passes for every concern; at most one named shell seam or feature-flow gap remains and it is documented as accepted residual.
- **7** — Tests hit useful surfaces, but timing waits, shallow coverage, or implementation-mirroring tests reduce trust. OR Authority Map cross-check finds 2+ shell-seam / feature-flow gaps not flagged in Findings.
- **5** — Tests exist but mostly verify glue, snapshots, or mocks rather than product behavior and ownership.
- **3** — Stateful domain or runtime Modules lack meaningful tests.

**Anti-anchor**: a passing test count is not test strategy. Aggregate count → score is fake-clean reward. The 9-anchor requires the Authority Map cross-check from `method.md` Step 8 / `lens-apple.md § Authority-Map test-surface cross-check`. If shell seams or contest-relevant feature flows lack direct tests, the score ceiling is 8 regardless of how many reducer-level tests pass.

### Overall implementation credibility
- **10** — Code earns its architecture at every layer. No honesty leaks. No fake-clean reward available. A senior reviewer reading the code in source order would find architectural claims confirmed at every Seam, owner, and lifecycle boundary.
- **9** — Code earns its architecture. Few honesty leaks. Remaining issues local and subtractive.
- **7** — Strong shape, but several known leaks or shallow wrappers prevent top-tier confidence.
- **5** — Works as an app, but architecture requires reviewer charity.
- **3** — Contest story does not survive source inspection.

### Domain modeling
- **10** — Domain types make impossible states unrepresentable. Discriminated unions where facets are mutually exclusive. Names match `CONTEXT.md` vocabulary. Domain layer free of framework imports. Invariants enforced at construction (smart constructors / validated values), not by convention. No `?? "Unknown"` patterns hiding type weakness.
- **9** — Domain types prove most invariants by construction. Names align with documented vocabulary. One or two parallel-fields cases remain but are documented.
- **7** — Domain types model the happy path well, but some impossible combinations are representable and rely on reducer discipline. Vocabulary drift between code and `CONTEXT.md`.
- **5** — Anemic types: data bags with logic in services. Booleans/optionals encode hidden state. Names reflect framework concerns more than domain.
- **3** — Domain absent or indistinguishable from persistence/transport types.

### Data flow and dependency design
- **10** — Dependency graph is a DAG enforced by source/build (boundary checks, module visibility). Each Module's inputs and outputs are explicit. No back-channels via singletons or globals. Effects/side-effects are typed and threaded through the data flow, not summoned from ambient scope. A new feature can be wired in by reading types alone.
- **9** — DAG enforced. Effects typed. One or two ambient-context dependencies remain documented.
- **7** — Dependencies acyclic in practice but enforced by convention; ambient state (singletons, env globals) reachable from multiple Modules.
- **5** — Dependencies require reading multiple files to trace. Some cycles or back-channels.
- **3** — Cyclic graph or service-locator pattern dominant.

### Framework / platform best practices
- **10** — Stack idioms used naturally; no costume layers cargo-culted from other ecosystems. Framework affordances (lifecycle hooks, type-system features, build/test tooling) used where they fit; bypassed where they don't with documented reason. No domain-policy leakage of framework types. Stack-specific lens (`lens-apple.md` / `lens-generic.md`) checklist passes in full.
- **9** — Stack idiomatic in primary surfaces. One or two non-idiomatic carve-outs are documented.
- **7** — Mostly idiomatic, but several places force generic patterns onto the stack at the cost of clarity.
- **5** — Visible mismatches between stack idioms and code structure; framework features under-used or worked around.
- **3** — Framework treated as transport layer; idiomatic features avoided or fought.

### Code simplicity and clarity
- **10** — Each Module is the simplest honest implementation. No ceremony, no premature abstraction, no pass-through wrappers. Naming carries the contract. A reader can predict behavior from interface alone.
- **9** — Few simplifications remaining; remaining complexity earns its keep per deletion test.
- **7** — Generally clear, but several Modules carry unjustified ceremony or shallow wrappers.
- **5** — Reader must consult multiple files to understand a single behavior; abstraction layers exceed Leverage.
- **3** — Costume-layer architecture, repository theater, or protocol soup dominates.

A drop here from prior loop = the previous refactor over-engineered. Revert.

## CONTEXT.md / docs/adr Awareness

Read `CONTEXT.md` (or `CONTEXT-MAP.md` + per-context `CONTEXT.md`) and `docs/adr/` in Step 0 if present.
- Use domain vocabulary in evidence: "Order intake module," not "OrderHandler."
- Findings contradicting an existing ADR must say so explicitly: _"contradicts ADR-0007 — but worth reopening because…"_. Do not silently propose forbidden refactors.
- Decisions logged in ADRs are not re-litigated unless friction is real enough to warrant it.

If neither file exists, proceed silently. Do not flag absence or suggest creating them upfront.
