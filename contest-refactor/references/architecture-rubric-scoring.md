# Architecture Rubric — Score Anchors (Critic scoring; Step 1 only)

The 9.5+ threshold, strictness presets, terminal normalization, and the nine per-dimension score anchors. Used by the **Critic** (Step 1) to score the scorecard. Carved out of [architecture-rubric.md](architecture-rubric.md) so the Step-3 implementation reviewer — which does **not** re-score (see [implementation-reviewer.md](implementation-reviewer.md)) — does not carry it. The Critic reads both files per the `SKILL.md` Reference Load Matrix; vocabulary, smells, architectural tests, the Unified Seam Policy, and the Severity Anchors stay in [architecture-rubric.md](architecture-rubric.md).

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

Accepted residuals come in two tiers with different expiry rules — keep them distinct:

- **Inline scorecard residual** (the per-dimension disposition above): justified by its `residual_rationale_or_backlog_ref`. `residual_expires` is **optional** — a permanent framework carve-out (e.g. a language constraint that will never change) needs no date and is a valid `HALT_SUCCESS`. If an inline residual *does* carry `residual_expires` and that date has passed, the Critic reconsiders it as active and it cannot satisfy `HALT_SUCCESS` unless current evidence shows it no longer applies.
- **`.contest-refactor.toml` `[[accepted_residuals]]`** (repo-level path-pattern policy): `reason`, `accepted_on`, and a **mandatory** `expires` (see [project-config.md](project-config.md)). These broad suppressions must lapse; an undated or expired toml residual is a validator error and cannot satisfy `HALT_SUCCESS`.

`HALT_SUCCESS` requires every scorecard category at 10, OR at 9.5+ with an **accepted** residual (inline rationale; any `residual_expires` present is not past). Any **queued** residual blocks `HALT_SUCCESS`. Any **expired** residual — inline or toml — blocks `HALT_SUCCESS`.

**Strictness presets (`--strictness`, recorded as `CURRENT_REVIEW.json.strictness`).** The preset tunes the *evidence* an inline residual must carry to be `accepted` — it does **not** move the 9.5 threshold, the `HALT_SUCCESS` criteria, or the optional-expiry rule above (those are identical under every preset; `validate-artifact.py` gates read only score + disposition, proven by `scripts/_strictness_isolation_selftest.py`).

- `standard` (default): today's bar — an accepted inline residual is justified by its `residual_rationale_or_backlog_ref` (prose rationale tying it to a framework constraint, carve-out, or ADR).
- `aggressive`: an accepted inline residual must cite **source-backed evidence** in its rationale — a concrete `file:line`/symbol, a named framework/language constraint, or an ADR ref — not bare prose. If the only justification is prose with no citable source, the residual is **queued, not accepted** (which keeps the flag `CONTINUE`). This is a conditional on an observable predicate (`strictness == "aggressive"`), and it raises the evidence bar *only*: a permanent carve-out that cites its framework constraint still passes with **no** `residual_expires` date (the C6 optional-expiry rule is untouched — `aggressive` demands a citation, never a date).

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
