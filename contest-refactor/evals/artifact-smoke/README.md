# Artifact Smoke Corpus

Eleven minimal artifact directories exercising the load-bearing rules in
`scripts/validate-artifact.py`. Each fixture is the smallest possible artifact
set that triggers exactly one expected result.

Run a single fixture against the validator:

```bash
python3 scripts/validate-artifact.py evals/artifact-smoke/<fixture-id> --mode strict
```

Or run the full smoke pass via `scripts/_smoke_check.py` (PR1 development
helper; not part of the loop runtime).

## Fixtures

| Fixture id | Expected result | Expected validator message |
|---|---|---|
| `halt-success-clean/` | `pass` | `validate-artifact (strict): OK …` |
| `halt-success-with-unresolved-serious/` | `fail` | `[HALT_SUCCESS] HALT_SUCCESS with unresolved Serious-or-worse finding F1` |
| `halt-success-sub-95-score/` | `fail` | `[G21-scorecard] HALT_SUCCESS dimension 'data_flow' score=8.5 < 9.5 …` |
| `halt-stagnation-eligible-remains/` | `fail` | `[G30] Serious-or-worse finding F-500 (status='rejected_attempt') missing from halt_handoff.remaining_serious_findings_disposition[]` |
| `halt-stagnation-fully-retired/` | `pass` | `validate-artifact (strict): OK …` |
| `unresolvable-insufficient-attempts/` | `fail` | `[retirement] registry F-400 occurrence[1]: mechanical retirement rule failed: neither Branch A nor Branch B is satisfied` |
| `expired-residual/` | `fail` | `[HALT_SUCCESS] scorecard concurrency accepted residual expired (expires='2020-01-01')` |
| `branch-b-fake-resolve-not-a-validator-error/` | `pass` | `validate-artifact (strict): OK …` |
| `g37-cap-incoherent-blocker/` | `fail` | `[G37] HALT_LOOP_CAP dimension 'framework_idioms' score=7.0 < 9.5 cites promotion-trigger residual_blocker_kind='framework_constrained' …` |
| `g37-cap-structural-ok/` | `pass` | `validate-artifact (strict): OK …` |
| `g37-no-backlog-incoherent/` | `fail` | `[G37] HALT_STAGNATION/no_backlog dimension 'domain_modeling' score=6.5 < 9.5 cites promotion-trigger residual_blocker_kind='ceremony' …` |

## Notes per fixture

### `halt-success-clean/`

Every scorecard dimension is 10 or 9.5+ with an accepted residual whose `expires` is far in the future. No findings emitted. Validator passes.

### `halt-success-with-unresolved-serious/`

`state == HALT_SUCCESS` but `findings[]` contains an unresolved finding with `severity == "Serious deduction"`. The validator's HALT_SUCCESS gating rejects.

### `halt-success-sub-95-score/`

`state == HALT_SUCCESS` but the `data_flow` scorecard dimension scores 8.5 with `residual_disposition: null`. The validator's G21-scorecard rule rejects: every HALT_SUCCESS dimension must satisfy `score == 10` OR (`score >= 9.5` AND `residual_disposition == "accepted"`). Mirrors the production failure mode flagged by [validation.md § G21](../../references/validation.md).

### `halt-stagnation-eligible-remains/`

`state == HALT_STAGNATION` and `halt_subtype == "oscillation"` while a Serious finding (`F-500`, status `rejected_attempt`) is missing from `halt_handoff.remaining_serious_findings_disposition[]`. G30 rejects.

### `halt-stagnation-fully-retired/`

`state == HALT_STAGNATION` and `halt_subtype == "oscillation"`. Every Serious-or-worse finding is dispositioned. `F-600` was mechanically retired via Branch A: three identical 3-way hashes across two `rejected_attempt` occurrences plus the retiring `unresolvable` occurrence. Validator passes.

### `unresolvable-insufficient-attempts/`

`F-400` is marked `unresolvable` with only one prior `rejected_attempt`. Branch A needs ≥2 priors; Branch B needs ≥2 priors with an intervening `resolved`. Neither satisfied. Validator rejects.

### `expired-residual/`

`state == HALT_SUCCESS` with a scorecard dimension at 9.5+ whose accepted-residual `expires` date is in the past (`2020-01-01`). The validator rejects: an expired residual cannot satisfy HALT_SUCCESS.

### `branch-b-fake-resolve-not-a-validator-error/`

**Critic-owned seam (Risks item 10).** `F-200` retired via Branch B: two `open` occurrences with matching 2-way hashes, separated by an intervening `resolved` occurrence. The validator passes by design. The seam: the prior `resolved` could have been a premature mark (a "fake resolve") that lets the next reappearance qualify on the easier 2-hash path. The validator cannot catch a fake-resolve because correctness of `resolved` is a Critic/reviewer responsibility (Check 1 / Check 2), not a structural property. This fixture codifies the expected behavior so a future "make the validator stricter" PR can't accidentally start rejecting legitimate Branch B retirements.

### `g37-cap-incoherent-blocker/`

`state == HALT_LOOP_CAP` with an empty `backlog` and `framework_idioms` at 7.0 carrying `residual_blocker_kind: "framework_constrained"` — a promotion-trigger kind. G37 rejects: at a converged empty-backlog terminal the only kind that licenses a sub-9.5 score is `structural_anchor_unmet`; a framework/ceremony/cosmetic/ADR blocker means the 9-anchor is met and the dimension must be promoted to 9.5-accepted. This is the soundboard-snag failure mode (2026-06-30) that G23 — no_backlog-only and never mechanically enforced — silently skipped at the cap.

### `g37-cap-structural-ok/`

`state == HALT_LOOP_CAP`, empty `backlog`. The honest resolution: `framework_idioms` promoted to 9.5 with `residual_disposition: "accepted"`, and the one genuinely-thin dimension (`domain_modeling` 6.5) tagged `residual_blocker_kind: "structural_anchor_unmet"`. G37 passes — proving it does not over-reject a legitimately-converged scorecard.

### `g37-no-backlog-incoherent/`

`state == HALT_STAGNATION`, `halt_subtype == "no_backlog"`, `domain_modeling` 6.5 with `residual_blocker_kind: "ceremony"`. G37 fires on the EXISTING no_backlog terminal too (the terminal G23 always named) — mechanizing what was previously Critic-discipline-only prose.
