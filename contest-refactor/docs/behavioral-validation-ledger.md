# Behavioral validation ledger

## 2026-08-25 — item 14 reviewer risk-boundary cue (no ship)

Fresh-context, host-dispatched review experiment: `gpt-5.6-luna`, five
repetitions per arm and fixture (20 samples total). The control was the existing
reviewer prompt. The treatment added the proposed Honesty-check cue for diffs
touching isolation/visibility markers with null `risk_boundary_evidence`.

| Fixture | Definition | Control | Treatment |
|---|---|---|---|
| risk-bearing | `evals/reviewer-cases/missing-invariant-evidence-1`: removes class-level `@MainActor` with only reasoning evidence | 5/5 rejected at Regression; Honesty passed | 5/5 non-approved: 2/5 conditional through the new Honesty cue; 3/5 the same Regression rejection as control |
| benign visibility-adjacent | `public`/`internal`-only change that demonstrably crosses no boundary | 5/5 approved | 5/5 approved; zero false positives |

The control already detected the risk-bearing case in every repetition, so the
treatment added no correctness lift and only split routing in two of five runs.
Per the writing-skills micro-test rule, the Honesty cue is not shipped. The
existing Regression risk-boundary check remains the single source for this family;
this record does not add a mechanical gate.
