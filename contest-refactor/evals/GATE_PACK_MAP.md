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
