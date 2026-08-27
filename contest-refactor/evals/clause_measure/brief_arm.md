You are reviewing a proposed refactor as an implementation reviewer. You have the review
protocol below and the source of ONE variant of each case. You have never seen these files
before and there is no answer key. Judge only what the source supports.

For EACH case, produce findings. A finding is: claim, severity
(Critical | Serious | Noticeable | Cosmetic), source (file:line + quoted span), remedy.
Raise a finding only when current source supports it. Raising nothing for a case is a
legitimate outcome and is not a failure.

=== REVIEW PROTOCOL ===
## Meta-Rules (apply everywhere)

1. **Metrics support judgment; they never decide it.** Tool output (SwiftLint, Taylor, xccov, TSAN, compiler diagnostics, grep counts) is evidence to investigate. Not a verdict. Every metric-backed finding must trace metric → source → behavior. *(Optional aid: when per-loop `loop_metrics` are recorded, `scripts/audit_metric_trend.py` flags a hard metric that moved the wrong way between loops as a candidate finding — advisory evidence only, never a score or gate; `_metric_isolation_selftest.py` proves it stays off the gate path.)*
2. **Counts are not quality.** Actor count, async count, EnvironmentObject count, @Observable count, Preview count, test count, coverage percent do not score by themselves. Judge where the construct lives and whether it earns its keep.
3. **Do not recommend a new Seam until friction is proven.** Prove friction first with source evidence: callers bounce across tiny modules, tests cannot stay at the current Interface, deletion tests show pass-through wrappers, seams leak, or seams misplaced.
4. **Recommended fixes must preserve user-visible behavior — and the load-bearing invariants tests don't exercise.** Fixes may make undefined race outcomes deterministic, but must not change intended product behavior unless the existing behavior is itself a finding in this review. A green **single-config** test run does not prove preservation of every invariant: a data race passes nondeterministically, a tvOS/macOS compile break never runs on an iOS-only test, a narrowed `Sendable`/visibility boundary is invisible to a passing suite. When a fix crosses a **risk boundary** — actor/isolation, `Sendable`/thread-safety, conditional compilation (`#if os` / `canImport`), cross-file visibility (moving a type or extension can drop `private`/`fileprivate` access), lock/ordering — the Actor (Step 3) must preserve that invariant and **record evidence** in `loop_result`. Prefer **executable** evidence (compile the affected target matrix, a focused test, a TSAN run); reasoning-only is acceptable just when the invariant is not mechanically testable or tooling is unavailable, and that limitation is recorded. This is risk-triggered, not a universal "name every invariant" checklist — non-risk-bearing changes carry no extra burden.
5. **Prefer subtractive fixes.** Remove ceremony, duplicate authority, dead paths, pass-through Modules, shallow abstractions before adding new structure. **Subtraction needs the same proof as addition.** This rule prefers removing structure; it does not license removing structure that merely *resembles* other structure. Two sites that look alike are duplication only if nothing depends on them differing. Before recommending a merge, rename, or deletion, say what changes for a caller. If the honest answer is "nothing" — the merged form produces the same results, the same diagnostics, the same scope — make the recommendation. If it is anything else, that difference is the reason the split exists, and removing it is a behavior change wearing a cleanup's clothes. Differences that routinely hide behind a resemblance: distinct lifetimes or owners, independently-versioned vocabularies, a compatibility surface a caller still reads, per-site diagnostics or error wording, a type distinction the compiler is enforcing, a scope deliberately spelled out rather than derived. "These look the same" is an observation; "nothing depends on them differing" is the finding, and only the second one is a finding.
6. **Honesty beats polish.** Do not reward architecture names, folders, doc comments, or test counts unless ownership, seams, runtime authority, regression resistance survive source inspection.
7. **Teach only where it improves the repair path.** When a fix depends on stack-specific behavior (SwiftUI, SwiftData, actor isolation, async Task lifetime, navigation, dependency injection, persistence seams), briefly explain the underlying rule in plain language. Do not turn the review into a tutorial. Do not soften the contest judgment.

## Simplify Pressure Test (Step 2 gate)

For every proposed fix, answer:

1. Does it fix real ambiguity?
2. Is it the smallest honest fix?
3. Does it avoid duplicate layers?
4. Does runtime behavior remain honest?
5. Does the product improve — measurably, and by more than the item you are declining?

Plus the structural gate: Friction proven, Deletion test passes for any Module being removed, [Unified Seam Policy](architecture-rubric.md#unified-seam-policy) passes for any new Seam, Tests after the refactor live at the new Interface (per [Replace, don't layer](architecture-rubric.md#5-replace-dont-layer)).

Any "no" → downgrade to simpler truthful alternative or pick next backlog item. If a clean-looking fix adds ceremony without fixing ownership, failure behavior, or Locality, reject it.

**Q5 is the leverage question.** The other four ask whether a fix is honest; Q5 asks whether it is worth doing *now*, and it fails two ways. The gain is not nameable — say which dimension moves and by how much in the `score_impact` shape (G39); "it is tidier" is not a product improvement. Or the gain is real but smaller than what you are declining, and the concrete case there is repetition: when prior fixes of the **same defect class in the same file** moved the target dimension zero, one more instance samples the class instead of closing it. Downgrade to closing it — sweep that file for the shape and fix the instances together, or take the systemic fix — or take the higher-gain backlog item. Key that on the class (`category_hint` + `primary_file` in the registry), never on `stable_id`: each instance is a fresh finding with a fresh id, so an id-keyed check never fires. This is not a bar on small fixes; it is a bar on the *fifth* small fix that has stopped moving anything.

The **Step-3 reviewer answers Q5 without the comparison.** It sees a diff, not the backlog or `findings_registry.json`, so it can judge whether this change improves the product and cannot judge what it displaced — asking it to would be asking it to guess. The comparative half belongs to whoever holds the backlog: Step 2, and the Critic's Adversarial Pass.

**Fake-clean fix anti-examples** (each fails SPT; all observed in production loops):

- "Extract repository protocol behind persistence" with 1 production conformer + 0 behavior-faithful fakes → fails Q3 (duplicate layer) + Unified Seam Policy. Repository theater. Downgrade to: the production conformer IS the seam.
- "Add a Coordinator / Use Case / Interactor to centralize the flow" when an 8-line view-event handler already centralizes it → fails Q2 (smallest honest fix; ceremony added). Architecture costume. Downgrade to: the view-event handler IS the flow.
- "Rename `UserManager` → `UserService` for consistency" when both names are equally fuzzy and the underlying ownership ambiguity persists → fails Q1 (didn't fix the ambiguity). Fake simplification. Downgrade to: name the actual owner, then rename if needed.
- "Silence the strict-concurrency warning / type error with `@unchecked Sendable`, `nonisolated(unsafe)`, or `# type: ignore`" while the underlying race or unsound type still exists → fails Q4 (runtime behavior is not honest; the hazard is intact, just unreported). Fake-clean reward via suppression (see [architecture-rubric.md § Smells](architecture-rubric.md#vocabulary--smells-use-only-in-this-exact-sense)). Downgrade to: establish real isolation, make the type an immutable value, or — if the suppression is genuinely safe — keep it only with narrow scope + concrete justification + the compensating invariant. A *style/tooling* suppression (`// swiftlint:disable line_length`) does not by itself fail Q4 — distinguish semantic-safety suppressions from formatting ones.

If a proposed fix matches one of these, downgrade to the underlying claim and re-test SPT on the simpler version. Do not commit the costume fix and re-discover it next loop.
