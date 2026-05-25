# Skill-TDD with Bad-Codebase Fixtures Gap — contest-refactor vs superpowers

Source: `refs/competitors/superpowers/skills/writing-skills/testing-skills-with-subagents.md` (385 lines) + `contest-refactor/evals/` (12 existing fixtures). Research flagged this as "major moat opportunity — almost nobody else ships fixtures + expected refactors as skill evals."

## Baseline: what each tool ships today

### Superpowers (methodology, NO fixtures)

**Verbatim skill-TDD doctrine** (`testing-skills-with-subagents.md:1-11`):

> **Testing skills is just TDD applied to process documentation.**
>
> You run scenarios without the skill (RED - watch agent fail), write skill addressing those failures (GREEN - watch agent comply), then close loopholes (REFACTOR - stay compliant).
>
> **Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill prevents the right failures.

Cycle:
- **RED** (`line 50`): "Run scenario WITHOUT skill — watch agent fail, document exact failures"
- **VERIFY RED** (`line 36`): "Capture rationalizations verbatim"
- **GREEN** (`line 82`): "Write skill addressing specific baseline failures"
- **VERIFY GREEN** (`line 86`): "Run same scenarios WITH skill. Agent should now comply"
- **REFACTOR** (`line 356`): "Continue REFACTOR cycle until no new rationalizations"

**Crucial gap in superpowers itself**: documents the methodology, **ships zero fixtures**. No `fixtures/` or `evals/` directories in any of the 14 skills. Testing is manual, scenario-driven, captured in prose.

### Contest-refactor (artifact validation, NO bad-codebase fixtures)

`contest-refactor/evals/` directory has 12 fixtures + `evals.json` + `artifact-smoke/` corpus. Each fixture is:

- `fixture.toml` (metadata, tested_rules, expected_result)
- `CURRENT_REVIEW.json` (machine-readable output)
- `CURRENT_REVIEW.md` (human-readable output)
- Optional: `REVIEW_HISTORY.json`, `findings_registry.json`, `LOOP_STATE.json`

Examples: `bootstrap-repo/`, `halt-success-bad/`, `stale-loop-state-with-halt/`.

**Crucial gap in contest-refactor**: fixtures test OUTPUT ARTIFACT SHAPE (does the JSON validate? does HALT_SUCCESS at 8.5 fail G21?), not BEHAVIOR (does running contest-refactor on a known-bad codebase produce the expected refactor?). Validates the validator; doesn't validate the loop.

### The combined moat

Nobody ships **bad codebase + expected loop behavior** as evals. The full skill-TDD chain for contest-refactor would require:

1. A bad codebase fixture (sample Swift/Rust/Python repo with known structural debt)
2. A baseline observation (what does Critic do without the skill loaded? — superpowers' RED phase)
3. An expected output (what should Critic identify + Actor fix? — superpowers' GREEN phase)
4. A loop trace (sequence of CURRENT_REVIEW.json files showing the loop converging to HALT_SUCCESS or HALT_STAGNATION)
5. A regression detector (does running contest-refactor on the fixture today match step 4?)

Superpowers ships #1 methodology and #2-3 doctrine (but no fixtures). Contest-refactor ships #5 validator but not #1-4 content. Together they'd compose a working skill-TDD harness; neither alone closes it.

## Strategic insight

Adopting skill-TDD with bad-codebase fixtures gives contest-refactor:

1. **Falsifiable claims**: "9.5+ scoring works" becomes testable. Without fixtures, the claim rests on author judgment.
2. **Regression safety**: schema bumps (current pace: 4 schema versions in development) risk breaking subtle behaviors. Fixtures catch schema-vs-behavior drift.
3. **Honest baseline against the arXiv falsifier** (`ARXIV-AGENTIC-REFACTORING-GAP.md`): fixtures let contest-refactor measure ITS OWN refactor-type distribution vs the arXiv 11.8%/10.4%/8.5% baseline.
4. **Onboarding**: new contributors run `python3 scripts/run-skill-tdd-eval.py` and see exactly what good output looks like.
5. **Cross-LLM testing**: same fixture run against Claude Code, Codex, opencode tests provider-adapters claims.

## Gap matrix

| Mechanism | contest-refactor | superpowers | what's missing |
|---|:--:|:--:|---|
| RED phase doctrine | partial (validate-artifact.py is implicit RED for schema) | ✓ explicit, prose-documented | bad-codebase RED for behavior |
| GREEN phase doctrine | ✓ Critic Method + validation gates | ✓ explicit | expected-refactor reference output |
| REFACTOR phase doctrine | ✓ Implementation Review + retry envelope | ✓ explicit | iterative skill improvement loop |
| Skill ships fixtures | partial (artifact-smoke fixtures) | — (zero fixtures) | bad-codebase + expected loop trace |
| Eval harness | ✓ `validate-artifact.py` + `_smoke_check.py` | — (manual scenario-running) | end-to-end loop-replay harness |
| Baseline-without-skill observation | — | ✓ doctrine | concrete baseline trace per fixture |
| Cross-model fixture replay | — | — | provider-adapter parametrized eval |
| Refactor-type distribution analysis | — | — | arXiv-baseline comparison per fixture |

## P0 GAPS — what to build

### Gap A (P0): Bad-codebase fixture format

**Adopt** new directory under `contest-refactor/evals/loop-fixtures/<fixture-id>/`. Each fixture contains:

```
loop-fixtures/auth-token-store-singleton/
├── fixture.toml                          # metadata + expected outcomes
├── codebase/                             # actual bad codebase to refactor
│   ├── Sources/Auth/TokenStore.swift     # has known structural debt
│   ├── Sources/UI/LoginView.swift        # touches TokenStore inappropriately
│   ├── Tests/AuthTests.swift             # weak test surface
│   └── Package.swift
├── baseline/                             # observed agent behavior WITHOUT contest-refactor
│   ├── claude-4.7.md                     # "What did Claude do when asked to refactor without the skill?"
│   ├── codex-gpt5.md                     # cross-provider baseline
│   └── opencode-default.md
├── expected/                             # reference output WITH contest-refactor
│   ├── loop-1-CURRENT_REVIEW.json        # expected Critic output, loop 1
│   ├── loop-1-CURRENT_REVIEW.md
│   ├── loop-2-CURRENT_REVIEW.json
│   ├── ...
│   ├── final-HALT_SUCCESS.json           # expected final state
│   └── expected-diff.patch               # the actual refactor diff
└── observations.md                       # human-readable notes (what makes this fixture useful)
```

### Gap B (P0): `fixture.toml` schema

```toml
id = "auth-token-store-singleton"
description = "Singleton TokenStore with multi-writer state pattern; tests live at view layer not Authority Map level"
language = "swift"
lens = "apple"
expected_outcome = "HALT_SUCCESS_AT_9.5_PLUS"     # enum: HALT_SUCCESS | HALT_STAGNATION/<subtype> | HALT_LOOP_CAP
expected_loop_count = 4                            # expected loops to convergence (±1 tolerance)
expected_findings_count = { loop_1 = 5, loop_4 = 0 }   # convergence shape

[[expected_findings.loop_1]]
stable_id_pattern = "F-001"
test_failed = "Two-adapter rule"
severity = "Serious deduction"
primary_file_pattern = "**/TokenStore.swift"

[[expected_findings.loop_1]]
stable_id_pattern = "F-002"
test_failed = "Interface-as-test-surface"
severity = "Noticeable weakness"

[[expected_refactoring_types]]
type = "Extract Method"
count_min = 1

[[expected_refactoring_types]]
type = "Move Field"
count_min = 1

[score_anchors_at_halt_success]
architecture_quality = { min = 9.5, max = 10 }
state_management = { min = 9.5, max = 10 }
test_strategy = { min = 9.0, max = 10 }      # allow weaker test_strategy if structural improvements dominate
# ... other 6 dimensions

[arxiv_baseline_check]
expected_low_level_ratio_max = 0.4           # fail if >40% of refactoring_types are rename/retype
# (gives the lens-hygiene specialty fixture a different threshold)

[regression_tolerance]
loop_count = "±1"                            # allow 3-5 loops instead of exact 4
finding_count = "±2"
score_per_dimension = "±0.5"
```

### Gap C (P0): Eval harness `scripts/run-skill-tdd-eval.py`

New script reads `loop-fixtures/<id>/fixture.toml`, runs:

1. **Baseline replay**: ensure `baseline/<provider>.md` exists for each provider being tested; if missing, skip baseline check (don't fail — just warn)
2. **Loop dispatch**: cd into `loop-fixtures/<id>/codebase/`, invoke contest-refactor with `--cap <expected_loop_count + tolerance>` + `--seed <fixture-id>` for reproducibility
3. **Artifact comparison**: after run, compare emitted `CURRENT_REVIEW.json` against `expected/loop-N-CURRENT_REVIEW.json` using tolerance windows from `regression_tolerance` block
4. **arXiv baseline check**: compute `refactoring_types[]` low-level ratio (Change Variable Type + Rename Parameter + Rename Variable counts) vs the fixture's `expected_low_level_ratio_max`
5. **Exit code**: 0 if within all tolerances; non-zero with summary of drift

```bash
python3 scripts/run-skill-tdd-eval.py loop-fixtures/auth-token-store-singleton
python3 scripts/run-skill-tdd-eval.py --all
python3 scripts/run-skill-tdd-eval.py --provider codex --only auth-token-store-singleton
```

### Gap D (P0): 5 initial fixtures (priority-ranked)

Ship in this order — each fixture targets a different scorecard dimension:

| # | Fixture id | Lens | Primary debt | Target dimension | Adapted from |
|---|---|---|---|---|---|
| 1 | `auth-token-store-singleton` | apple | Multi-writer singleton; tests at view layer | state_management + test_strategy | levnik ln-642 layer ownership + contest-refactor existing Authority Map fixture-shape |
| 2 | `n-plus-one-order-query` | generic | ORM N+1 with hidden lazy-load | data_flow + framework_idioms | levnik ln-651 query efficiency |
| 3 | `concurrency-continuation-leak` | apple | `withCheckedContinuation` paired with completion-handler delegate writes after resume | concurrency | contest-refactor G25 continuation-bridge audit + lens-apple existing rule |
| 4 | `god-class-order-coordinator` | apple | 850-LOC OrderCoordinator with mixed concerns | architecture_quality + simplicity | mattpocock deletion-test |
| 5 | `theater-rename-only` | generic | Codebase where ONLY low-level renames are needed; contest-refactor should HALT_SUCCESS at near-baseline, NOT manufacture structural findings | code_hygiene (proposed 10th dim) + anti-theater | arXiv baseline + Q3 fake-clean reward |

Fixture #5 is critical: it tests that contest-refactor doesn't INVENT findings when the codebase is honestly clean. The most-common-case agentic refactor per arXiv (low-level only) should NOT trigger architecture-theater on a clean codebase. This is a regression test against the most-watched failure mode.

### Gap E (P1): Cross-provider baseline traces

For each fixture, ship `baseline/<provider>.md` showing what each provider does WITHOUT contest-refactor. Generation process (manual or scripted):

1. `cd loop-fixtures/auth-token-store-singleton/codebase/`
2. Open in Claude Code, prompt: "refactor this codebase to remove architectural issues"
3. Save the resulting diff + verbatim agent reasoning to `baseline/claude-4.7.md`
4. Repeat with Codex, opencode

Baseline traces are READ but not failed-on by the eval harness — they're observed data, not assertions. Comparing baseline (without contest-refactor) to expected (with contest-refactor) is the falsification: if the deltas are tiny, contest-refactor isn't adding value.

### Gap F (P2): CI integration

GitHub Action runs `python3 scripts/run-skill-tdd-eval.py --all --provider claude-code` on PR. Failures block merge. Provider-matrix testing (running against Codex and opencode) runs nightly, doesn't block PR.

## What contest-refactor wins vs superpowers

- **Artifact validator** (`validate-artifact.py`): superpowers has no equivalent. Contest-refactor's existing fixture validator extends naturally to loop-fixture validation.
- **Schema versioning**: contest-refactor's `schema_version` discipline means fixtures can declare which schema_version they target; superpowers has no schema to anchor to.
- **Canonical enums**: contest-refactor's `canon/*.toml` files mean fixtures can assert against deterministic values; superpowers' free-text doctrine has no enum target.

## What superpowers wins vs contest-refactor

- **Explicit baseline-observation doctrine**: superpowers documents that you MUST watch the failure without the skill before writing the skill. Contest-refactor's evals jumped to "validate the validator" without ever observing baseline.
- **Adversarial scenario design** (`testing-skills-with-subagents.md:36`): "Capture rationalizations verbatim" — superpowers catches the failure mode where agents talk past the skill. Contest-refactor's validator can't catch agent-evasion.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Full superpowers skill-TDD harness (385 lines of doctrine) | Most of it is methodology contest-refactor doesn't need to restate. Cherry-pick the bad-codebase fixture + baseline observation patterns; skip the per-skill iteration scaffolding. |
| Bash-only baseline runner | Bash 3.2 compat (per `bash-macos` skill) constrains; use Python for cross-platform. |
| Massive fixture corpus | 5 initial fixtures is enough to anchor the methodology. Adding 50 fixtures dilutes signal + invites stale-fixture rot. |
| Per-provider expected outputs in `expected/` | Provider variation is real but not what fixtures should test. `expected/` holds rubric-correct output (provider-agnostic); per-provider drift gets recorded in `baseline/` but isn't asserted against. |
| Storing actual large fixture codebases in the repo | Sample codebases > 1MB inflate clone size. Use submodules OR ship synthetic minimal codebases that exhibit the structural debt in ~10 files. |

## Adoption order

**Cross-doc prerequisite chain (per Gemini Pro peer review round 1, N1):**

| Prereq doc | What ships first | Why fixture #5 needs it |
|---|---|---|
| TRACEABILITY-GAP Gap A (changed_hunks + hunk_id) | schema_version 4 with changed_hunks[] populated by Implementation Reviewer | fixture #5 asserts `[[expected_refactoring_types]]` — requires hunk-level refactoring_pattern field |
| TRACEABILITY-GAP Gap A.1 (canon/refactoring-patterns.toml) | Fowler-derived pattern enum | fixture #5 uses pattern names verbatim from canon |
| ROI-PRIORITIZATION-GAP Phase 3 (backlog.roi schema) | schema_version 4 with `backlog[].roi.tier` field | OPTIONAL for fixture #5; required for fixtures #1-4 if their fixture.toml asserts ROI tiers |
| SCHEMA-GAP Gap 1 (confidence) + Gap 2 (severity_rationale) | finding-level fields | fixture #5 expected/ JSON files reference these fields |

Phases below assume prereqs land first. Don't ship fixture phases that exercise un-shipped schema.

1. **Phase 1 (foundation)**: Define `fixture.toml` schema. Update `scripts/validate-fixtures.py` to validate loop-fixture shape distinct from artifact-smoke shape. NO dependency.
2. **Phase 2 (first fixture)**: Ship fixture #5 (`theater-rename-only`) FIRST — but ONLY after TRACEABILITY Gap A + Gap A.1 land. Most important regression: ensures contest-refactor doesn't manufacture findings. Smallest codebase. Pairs with arXiv-baseline check.
3. **Phase 3 (eval harness)**: Implement `scripts/run-skill-tdd-eval.py`. Ship with fixture #5 only initially.
4. **Phase 4 (4 more fixtures)**: Ship fixtures #1-4 in priority order. Each fixture's prereqs may include ROI-PRIORITIZATION-GAP Phase 3 (when fixture.toml asserts ROI tiers), CRITIC-INDEPENDENCE Gap A (when fixture asserts split-subagent provenance), etc. Document per-fixture dependency in its `fixture.toml § dependencies`.
5. **Phase 5 (baselines)**: Manually generate `baseline/<provider>.md` for at least Claude Code; defer cross-provider until CI matrix is built.
6. **Phase 6 (CI)**: Add GH Action gating PRs on Claude Code provider.

## Pairing with other gap docs

- **ARXIV-AGENTIC-REFACTORING-GAP**: fixture #5 + `arxiv_baseline_check` block in fixture.toml directly addresses the arXiv falsifier. Fixture #5 IS the proof contest-refactor doesn't manufacture findings on clean code.
- **SCHEMA-GAP `confidence` + `severity_rationale`**: fixtures should assert on these new fields once schema_version 4 ships.
- **TRACEABILITY-GAP Gap A `changed_hunks[]`**: fixtures should assert hunk-level traceability in `expected/loop-N-CURRENT_REVIEW.json`.
- **LEVNIK-AUDIT-SUITE-GAP specialty lens dispatch**: fixtures could parametrize lenses fired; e.g., `auth-token-store-singleton` should fire `lens-architecture-boundary` + `lens-test-quality`.
- **CRITIC-INDEPENDENCE-GAP**: cross-provider baseline traces (Gap E) double as evidence that single-model blindspot exists (and motivates cross-model adversarial critic per CROSS-MODEL-CRITIC-GAP).

## Why this is the "major moat"

Per landscape research, almost no public skill ships bad-codebase + expected-refactor fixtures. Reasons:

- Hard to write (each fixture is 100-500 LOC of intentionally-bad code with documented intent)
- Hard to maintain (codebase + expected output drift independently as the skill evolves)
- Slow to run (each loop-replay takes 30-180s)

Contest-refactor's existing canon/* TOML discipline + validator infrastructure means it's UNIQUELY positioned to add the fixture layer without rebuilding from scratch. The moat is the COMBINATION: contest-refactor's strict schema + bad-codebase fixtures + provider-matrix testing = falsifiable end-to-end claims no other skill ships.
