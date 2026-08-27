# Do the gold-corpus packs map to any gate? — 2026-08-27

The corpus's original intent was scenarios that map to gates and are hard to pass.
That is not what was built: **zero of the 26 packs reference a gate.** This is the
salvage analysis — which packs could be reused against which gates, and which gates
they cannot touch at all.

All 50 gates are accounted for below.

## Why most gates cannot take a pack

Gates check the **shape of emitted loop state**; packs check **review judgment**. A
pack is graded by executable oracles plus `must_find` / `must_not_find`, and never
produces a `loop_result`, so it cannot fail a schema gate by construction.

**No map — 30 gates.** Pure structure, schema, persistence, or multi-loop history:
G1, G2, G7, G9, G11, G14, G15, G16, G17, G18, G19, G20, G21, G22, G26, G27, G28,
G29, G30, G31, G32, G34, G35, G36, G38, G39, G40, G41, G42, G44, G45, G46, G47, G48.
Reusing a pack here would mean writing a loop emission by hand, at which point the
pack contributes nothing.

## Strong map — the pack already tests the judgment the gate enforces

These need a loop-emission wrapper around an existing pack, **not** new source. Each
listed gate currently has **zero** citing scenario fixtures.

| Gate | What it enforces | Packs that already are this |
| --- | --- | --- |
| **G33** risk_boundary_evidence (Meta-Rule-4 preservation evidence when a fix crosses actor/isolation, `Sendable`, `#if os`, visibility, or lock/ordering) | evidence recorded for a boundary-crossing fix | `strict-concurrency-fake-fixes` (two archetypes of a fake isolation fix), `auth-concurrent-login-storage` (lock granularity, lost update), `demand-signalling-state-machine` (actor isolation + cancellation), `swift-collections-platform-guard-scope` (`#if os` scope) |
| **G25** Continuation-bridge delegate audit (when concurrency ≥ 9: read delegate bodies for writes after the continuation resumed) | post-resume state writes | `demand-signalling-state-machine` — its central oracle is *every continuation resumed exactly once under cancellation*. This is the gate's own subject matter. |
| **G24** Authority Map test-surface cross-check (when test_strategy ≥ 9: every concern's mutation path exercised through the Interface) | a passing suite that proves nothing | `swiftnio-write-before-active` (**the suite certifies the defect** — a passing test asserts the wrong behaviour), `auth-concurrent-login-storage`, `config-precedence-duplicate-authority` (all four suites pass; every defect invisible to them) |
| **G12** Seam policy + friction proof (no new Seam without proven friction; two-adapter rule) | abstraction added or kept without friction proof | `store-core-composition-residual` (`Panel` composition vs type erasure), `swiftnio-registration-id-representation` (a real, shorter generalization that is still wrong), `pydantic-typing-extra` (dual registry), `swift-collections-ordered-replace-primitive` (shared move primitive vs delegating) |
| **G5** 9.5 residual / **G23**, **G37** residual accounting | a 9.5 dimension must carry a named residual; nothing stranded at a terminal | `store-core-composition-residual`, `pandas-groupby-plot-imperfect-gold`, `werkzeug-socket-lifecycle` — all three are literally *accept the change **and** name the residual*, and their manifests say "Accepting it and naming the residual are not in tension" |

## Close map — reusable with modification

| Gate | Gap to close | Packs |
| --- | --- | --- |
| **G49**, **G50** hotspot evidence + triage completeness | packs would need a scanner roster and triage rows | `streaming-decoder-error-state` — its declared role is *hotspot scanner restraint, state density*: a scanner is expected to nominate it and the Critic must dismiss the nomination. That is G50's subject with the emission missing. |
| **G10** Deepening Candidate purity | grade "is this deepening or just deleting a wrapper" | `swiftnio-registration-id-representation`, `swift-collections-ordered-replace-primitive` |
| **G3** Evidence chain | packs grade *whether* a finding was raised, not whether it carries Claim→Source→Consequence→Remedy | any pack, if grading asserted chain structure |
| **G13** Vocabulary discipline | assert the architectural label is used in canon's exact sense | the restraint packs, whose `must_not_find` already forbids mislabelling deliberate structure as ceremony/costume |
| **G6** 10 anchor justification, **G4**/**G8** score proof | packs emit no scorecard | would need scoring, which is most of a loop |

## What this is worth

Five gates with **zero scenario coverage** — G33, G25, G24, G12, G5 — have between
one and four packs each that already encode the exact judgment they gate. The
expensive half of a scenario (real source, sibling variants, executable oracles,
maintainer-derived ground truth) exists. The missing half is the cheap half: a loop
emission that carries the judgment into gate-checkable state.

That is the version of the original idea that was never built, and it does not need
new packs.

**Caveat, and it is not small.** Nothing here has been measured. The claim is that
these packs *could* be wired to those gates, not that doing so would find defects.
Given this session's record — a corpus that produced zero shipped run-path changes —
the honest next step is to wire **one** gate (G25 or G24 are the tightest fits) and
see whether it catches anything, before wiring five.

## Correction

Earlier notes in this session, including the strategy document sent to peer review,
described **G17 as a promotion bar counting adjudicated live-run datapoints**. That is
wrong. G17 is **Indirect coverage citation** (`validation.md:67`): when
`what_changed` contains a deepening keyword and the diff has no test changes,
`interface_test_coverage_path` must be non-null and structurally valid. The
"promotion bar" wording belongs to **G48**, whose title defers its Issue until an
instrumented-pass promotion condition is met, implemented in
`_artifact_run_identity.py`. Any earlier statement that "fixtures do not move G17 by
design" was reasoning from the wrong gate.

## Peer-review outcome — 2026-08-27 (codex `gpt-5.6-sol`, high)

`VERDICT: REVISE`. **The ranking does not change: C stays first, and gate wiring does
not earn its own programme of work.** Stop remains right for corpus harvesting and for
broad gate wiring.

**The reuse argument was called what it is.** Verbatim: *"Reusing the 26 packs is not
evidence of value; on its own, that argument is sunk-cost reasoning. Existing assets
reduce marginal cost, but they do not raise expected benefit."* The five-gate map above
is candidate discovery, not a payoff estimate, and the coverage counts must never be
used as the metric.

**What survives, and it is genuinely useful:** the mapping gives C's bounded live run a
concrete specimen. The recommended ordering is **C instantiated with a G24 probe** >
E > A > B > D, using `swiftnio-write-before-active`, because a passing suite that is
itself misleading evidence is G24's stated purpose — a real counterfactual rather than
an absent citation.

**The distinction that decides whether this is real work:** it is a different bet *only*
if the emission happens naturally through the production run path. Hand-authoring a
`loop_result` to satisfy the gate is the same bet relabelled — "another fixture whose
expected answer was encoded by its author".

**Coverage-theatre test, to be applied before claiming anything.** A real robustness gap
requires all three:

1. the normal emitter supplies the gate's inputs with **no** pack-specific adapters and
   no answer-key leakage;
2. the gate rejects the known-bad case while accepting a matched good sibling;
3. **bypassing the gate changes an observable loop decision** — continuation, promotion,
   or review disposition — not merely a coverage counter.

If the work requires manually filling the exact field the gate checks, or only shows the
predicate returns false, it is theatre; selftests already establish predicate behaviour.

**Terminal failure conditions for the probe** (any one stops gate wiring entirely, with
no substitution of another pack, gate, or adapter): emission needs hand-authoring or
pack-specific translation; G24 cannot separate the misleading-suite case from its
corrected sibling; the gate fires only after its expected answer was encoded into the
emission; enabling vs bypassing G24 changes no loop decision; or completing it requires
more than one pack, one gate, one live run.

Success justifies investigating **one** further integration gap. It does not justify
bulk-wiring compatible packs.

**On the G17 error:** it did not change the earlier ranking. It invalidates the specific
claim that fixtures categorically could not affect G17 and weakens that part of the
rationale, but the decisive objections were broader — no external value function,
repeated flat measurements, and the need for one bounded live run first.
