# Contest Refactor Review History


--- Loop 1 (UTC 2026-08-05T15:09:40.945365Z) ---

### Discovery
- Source roots: `contest-refactor/`
- Test command: `validate-repo.py`; `validate-fixtures.py`; `_smoke_check.py`; every `_*_selftest.py`; Ruff check and format check
- Build command: none — stdlib-only Python skill
- ADRs found: none
- Domain terms: Critic, Architect, Actor, finding, halt, gate, canon
- Selected lens: Generic, plus Security and Efficiency

### Loop Counter
Loop 1 of 1 (cap)

### System Flag
[STATE: CONTINUE]

---

## Contest Verdict

Functionally solid, but structurally compromised.

The deterministic gate suite is green and the core vocabularies have clear owners. The skill still exempts its own 2,255-line trust gate from the repository's module-size enforcement, carries one dead validation branch, and duplicates a measured-eval contract across two scripts.

## Scorecard (1-10)

- Architecture quality: `7.0 | SAME | contest-refactor/scripts/validate-artifact.py:143-2255; .githooks/pre-commit:30-39` — unrelated gate families share one oversized module that is outside the existing size gate.
- State management and runtime ownership: `9.0 | SAME | contest-refactor/references/output-format-state-schemas.md:81-222; contest-refactor/scripts/validate-artifact.py:666-703` — current review, history, and registry files have distinct persistence roles and append checks.
- Domain modeling: `9.0 | SAME | contest-refactor/canon/scorecard-dimensions.toml:1-29; contest-refactor/scripts/_canon.py:72-222` — canonical vocabulary is data-owned and loaded into an immutable value.
- Data flow and dependency design: `8.0 | SAME | contest-refactor/scripts/validate-artifact.py:2157-2197; contest-refactor/scripts/_advisory_baseline_selftest.py:98-189` — orchestration is explicit, but validation rules collect in one fan-out hub and one eval contract is duplicated.
- Framework / platform best practices: `9.0 | SAME | contest-refactor/scripts/_canon.py:1-255; contest-refactor/scripts/validate-artifact.py:2200-2255` — stdlib parsing, `argparse`, `pathlib`, and immutable mappings are used consistently.
- Concurrency and runtime safety: `9.0 | SAME | contest-refactor/scripts/validate-artifact.py:185-230; contest-refactor/scripts/validate-fixtures.py:298-357` — the CLIs are intentionally sequential and subprocess results are bounded and collected before mutation.
- Code simplicity and clarity: `7.0 | SAME | contest-refactor/scripts/validate-artifact.py:1-2255; contest-refactor/scripts/validate-fixtures.py:265-294; contest-refactor/scripts/_advisory_baseline_selftest.py:98-189; contest-refactor/scripts/_principal_baseline_selftest.py:52-156` — one monolith, one dead branch, and one cross-file clone remain.
- Test strategy and regression resistance: `8.0 | SAME | contest-refactor/evals/README.md:6-18; contest-refactor/scripts/validate-fixtures.py:265-294; .githooks/pre-commit:30-39` — the layered suite is strong, but the dormant branch has no fixture and the skill is absent from module-size enforcement.
- Overall implementation credibility: `8.0 | SAME | common/scripts/check_module_size.py:60-83; .githooks/pre-commit:30-39; contest-refactor/scripts/validate-artifact.py:1-2255` — all documented checks pass, yet applying the repository's checker to this scope reports a hard-cap violation.

## Authority Map

### Current loop review state
- Owner: `CURRENT_REVIEW.json` under the output-format schema
- Allowed writers: Step 1 Critic emit; Step 3 result and implementation-review update
- Observers / readers: `validate-artifact.py`, `render_report.py`, resume routing
- Persistence seam: repository-root `CURRENT_REVIEW.json` and `REVIEW_HISTORY.json`
- Async mutation entry points: none
- Verdict: Single and clear

### Finding identity and occurrence history
- Owner: `findings_registry.json` under `_fingerprint.py` hashes
- Allowed writers: Step 1 stable-id assignment; Step 3 registry append
- Observers / readers: `validate-artifact.py`, resume routing, SARIF export
- Persistence seam: repository-root `findings_registry.json`
- Async mutation entry points: none
- Verdict: Single and clear

### Canonical states, enums, and gate identifiers
- Owner: `contest-refactor/canon/*.toml`, loaded by `_canon.py`
- Allowed writers: maintainer edits to canon TOML
- Observers / readers: artifact, repository, fixture, and selftest validators
- Persistence seam: `contest-refactor/canon/*.toml`
- Async mutation entry points: none
- Verdict: Single and clear

## Strengths That Matter

- Canonical vocabulary has one frozen loader used by the repository, artifact, fixture, and halt-tail checks — `contest-refactor/scripts/_canon.py:72-222`.
- The strict path composes independently named gates in one deterministic run, and the full documented baseline passed — `contest-refactor/scripts/validate-artifact.py:2157-2197`.
- Finding hashes have one algorithm owner and the live validator recomputes snapshots instead of trusting stored digests — `contest-refactor/scripts/_fingerprint.py:65-83`; `contest-refactor/scripts/validate-artifact.py:611-665`.

## Findings

### Finding #1: Artifact validation is a 2,255-line unchecked monolith

**Why it matters** — The skill's trust gate must remain locally understandable as new halt and history rules are added.

**What is wrong** — `validate-artifact.py` owns JSON loading, registry retirement, history checks, provider attribution, checkpoint freshness, halt semantics, scorecard rules, and CLI output in one 2,255-line file, while the repository's module-size gate scans only `quorum-review` and `peer-plan-review`.

**Evidence** — `contest-refactor/scripts/validate-artifact.py:143-2255`; `contest-refactor/scripts/validate-artifact.py:2157-2196`; `.githooks/pre-commit:30-39`; `common/scripts/check_module_size.py:60-83`.

**Architectural test failed** — Shallow module.

**Dependency category** — n/a.

**Leverage impact** — Every selftest that imports a gate depends on the same oversized module even though the gate families are independent.

**Locality impact** — Each new rule edits the same hotspot and requires reasoning across unrelated registry, provider, halt, and CLI code.

**Metric signal, if any** — 2,255 physical lines; 25 commits in current history; the repository checker reports one hard-cap violation at 800 lines when applied to `contest-refactor/scripts`.

**Why this weakens submission** — The skill enforces structural rigor on targets while exempting its own most change-prone correctness module from the same guard, increasing cross-gate regression risk.

**Severity** — Serious deduction.

**ADR conflicts** — none.

**Minimal correction path** — Move existing pure checks unchanged into three private modules grouped by core schema, registry/history, and halt/runtime concerns; keep `validate-artifact.py` as the thin re-exporting CLI expected by selftests; add `contest-refactor/scripts` to the existing pre-commit module-size loop. Do not add classes, a plugin registry, or generated validators.

**Blast radius** — Change `.githooks/pre-commit`, `contest-refactor/scripts/validate-artifact.py`, and new `_artifact_core.py`, `_artifact_history.py`, `_artifact_halt.py`. Strictly avoid `contest-refactor/SKILL.md`, `references/`, `canon/`, and `evals/`.

### Finding #2: Unused fixture files contract accepts paths outside the fixture

**Why it matters** — A deterministic fixture validator should not contain an unexercised path rule that can be satisfied by unrelated filesystem content.

**What is wrong** — The optional `files` array is absent from every `fixture.toml`, yet `_validate_one_fixture` joins each supplied value directly to `fixture_dir` and checks only `exists()`, so absolute paths and parent traversal are accepted as declared fixture files.

**Evidence** — `contest-refactor/scripts/validate-fixtures.py:265-294`; no current `contest-refactor/evals/fixtures/*/fixture.toml` defines `files`.

**Architectural test failed** — Deletion test.

**Dependency category** — n/a.

**Leverage impact** — No current caller receives value from the optional contract.

**Locality impact** — Keeping it creates a new input-validation obligation inside the fixture parser without serving the current corpus.

**Metric signal, if any** — Zero fixture sidecars define `files`; 30 lines implement the dormant branch.

**Why this weakens submission** — Dead validation code both enlarges the parser and advertises a guarantee it does not safely enforce.

**Severity** — Noticeable weakness.

**ADR conflicts** — none.

**Minimal correction path** — Delete the optional `files` branch and its comment. Do not add path-normalization machinery until a real fixture needs this contract.

**Blast radius** — Change only `contest-refactor/scripts/validate-fixtures.py`; avoid the fixture corpus and artifact validator.

### Finding #3: Replication contract is copy-pasted across two baseline validators

**Why it matters** — Measured evaluation evidence is only credible when its shared artifact rules have one implementation.

**What is wrong** — The advisory and principal baseline selftests independently implement the same replication-block fields, five-slot accounting, invalid-count check, floor ordering, and valid-result requirements; the clone detector reports 0.89 similarity across roughly 92 lines, while arm and contamination rules are the only material differences.

**Evidence** — `contest-refactor/scripts/_advisory_baseline_selftest.py:98-189`; `contest-refactor/scripts/_principal_baseline_selftest.py:52-156`.

**Architectural test failed** — Two-adapter rule.

**Dependency category** — n/a.

**Leverage impact** — Both callers must understand and maintain the same low-level replication shape.

**Locality impact** — Changing a shared replication invariant requires synchronized edits in two standalone scripts and can silently diverge.

**Metric signal, if any** — `audit_clones.py` reports similarity 0.89 across the two functions.

**Why this weakens submission** — The evaluation layer can disagree with itself about whether recorded measurements are valid, weakening the evidence used to judge the skill.

**Severity** — Noticeable weakness.

**ADR conflicts** — none.

**Minimal correction path** — Extract only the shared replication shape and terminal-attempt checks into one private helper used by both selftests; leave advisory arm selection and principal contamination/retry policies local.

**Blast radius** — Change `_replication_validation.py` and the two baseline selftests; avoid all manifests and replication JSON.

## Simplification Check

- Structurally necessary: split the validator without changing gate behavior so the Shallow module failure is removed and the repository's 800-line policy covers this skill.
- New seam justified: false; these are private file moves behind the existing CLI, not a new dependency seam.
- Helpful simplification: delete the unused `files` branch; later consolidate only the genuinely shared replication assertions.
- Should NOT be done: do not build a validator class hierarchy, gate plugin registry, code generator, or generic path-sandbox abstraction.
- Tests after fix: keep the existing 31 standalone selftests and strict fixture/smoke runs; add no parallel replacement suite. Run the existing module-size checker against `contest-refactor/scripts`.

## Improvement Backlog

1. `F-001` — Split the artifact validator and enforce its size cap. Structural; needed for winning. The core trust gate currently violates the repository's own hard threshold and remains outside enforcement. Score impact: `architecture_quality +1.0; simplicity +0.5; credibility +0.5`.
2. `F-002` — Delete the dormant fixture `files` contract. Simplification; helpful. Deletion removes unused parser code and unsafe path semantics without reducing current coverage. Score impact: `simplicity +0.5; test_strategy +0.5; credibility +0.5`.
3. `F-003` — Share the common replication validation rules. Simplification; helpful. One implementation prevents the two measured baseline validators from drifting on shared evidence rules. Score impact: `simplicity +0.5; test_strategy +0.5`.

## Deepening Candidates

### `validate-artifact.py` gate cluster
- Source friction proven: Finding F1 — 2,255 lines, 26 direct `run_checks` callees, and a failing 800-line module check.
- Why shallow or misplaced: unrelated schema, history, provider, checkpoint, and halt policies share one importable file.
- Behavior to move behind Interface: cohesive pure check families behind the existing CLI, preserving exported function names for selftests.
- Dependency category: `in-process`.
- Test surface after change: existing gate selftests import the compatibility surface; strict fixtures and smoke exercise the CLI.
- Smallest first step: move registry/history checks unchanged, then the remaining families until every module is below 800 lines.
- What not to do: no gate objects, registration decorators, or generated code.

### Replication validation helper
- Source friction proven: Finding F3 — two measured-baseline validators carry a 0.89-similar replication check.
- Why shallow or misplaced: shared attempt-shape rules live in each caller while caller-specific policies are interleaved with them.
- Behavior to move behind Interface: required fields, terminal-slot selection, invalid counts, and valid-result presence; return failure strings.
- Dependency category: `in-process`.
- Test surface after change: the advisory and principal baseline selftests remain the two consumers.
- Smallest first step: extract byte-for-byte common assertions and keep every divergent rule local.
- What not to do: do not merge baseline formats or invent a generalized evaluation framework.

## Builder Notes

1. **A policy gate exempted its own largest target.** Recognize this by running a repository checker against every sibling tool directory, not only the hook's current list. Smallest rule: apply an existing limit uniformly before adding a waiver or a new checker.
2. **An optional validation feature had no users.** Search every producer before hardening a parser branch. Smallest rule: delete dormant contracts; add them back with their first real fixture and one negative check.
3. **Cross-file clones need semantic comparison.** The clone report's selftest boilerplate and fixture-source pairs were falsified as test structure; only the replication pair carried the same behavior. Smallest rule: share the common assertions and keep divergent policy local.

### Scorecard humility check

`state_management` 9.0 at `output-format-state-schemas.md:81-222` may over-credit a state machine still orchestrated in prose; `concurrency` 9.0 at `validate-fixtures.py:298-357` is mostly an applicability judgment and was not stress-tested under parallel invocations; Finding F3's Noticeable severity at the two replication selftests may be high if their formats intentionally continue diverging. These are the first challenge targets for a non-dry-run follow-up; none was promoted to 9.5.

## Final Judge Narrative

Place, not win. The baseline is green and runtime ownership is mostly trustworthy, but the skill's central trust gate is an unenforced 2,255-line hotspot and the evaluation layer retains avoidable dead and duplicated validation. Concurrency risk is low in these sequential CLIs; tests reduce regressions strongly but miss the module-policy and dormant-path gaps. The next change should be a mechanical split, not a new validation framework.

## Loop 1 Result

Split the artifact validator into core, history, and halt Modules while retaining the existing CLI and re-export Interface; extended the existing module-size hook to `contest-refactor/scripts`. `validate-repo.py`, all 50 strict fixtures, all 11 smoke fixtures, every standalone selftest, Ruff, and the 800-line module-size gate passed. Finding F1 is resolved. The cross-file move is covered by the focused import/re-export selftests; no unintended scorecard regression was observed.

## Loop 1 Implementation Review

Reviewer ran inline because provider detection was `unknown`; verdict requires manual confirmation. Approved: Reality, Honesty, and Regression checks passed. The 2,255-line shallow Module is gone, the CLI and imported test Interface remain intact, no costume Seam was added, and the focused full validator/selftest suite covers the cross-file move.

--- Loop 2 (UTC 2026-08-05T15:14:17.632110Z) ---

### Discovery
- Source roots: `contest-refactor/`
- Test command: full validator, fixture, smoke, standalone-selftest, and Ruff suite
- Lens: Generic + Security + Efficiency
- Working-tree dirty paths: `contest-refactor/references/method.md` (non-overlapping user edit)

### Loop Counter
Loop 2 of 10.

### System Flag
[STATE: CONTINUE]

## Contest Verdict

Functionally solid, with one small subtractive weakness remaining.

## Scorecard (1-10)

Architecture quality 9; State management 9; Domain modeling 9; Data flow 9; Framework idioms 9; Concurrency 9; Simplicity 8; Test strategy 8; Credibility 9.

## Authority Map

Review artifacts, finding identity, and canon values each retain one documented writer and persisted Interface. The validator split changes locality, not authority.

## Strengths That Matter

- The full gate is green after the split.
- The CLI remains the stable Interface while private gate families are bounded by the existing 800-line policy.

## Findings

### Finding #1: Unused fixture files contract accepts paths outside the fixture

Stable ID: `F-002`. Severity: Noticeable weakness. `validate-fixtures.py:265-294` implements an optional `files[]` contract that no current fixture uses, and joins supplied values directly to the fixture directory. The smallest honest remedy is deletion, not path-normalization machinery.

F-003 disposition: withdrawn from the Improvement Backlog. Current source has two similar baseline validators but no behavioral drift, duplicated runtime/domain authority, or three-site synchronized maintenance; under `method.md` this is Cosmetic, not Noticeable.

## Simplification Check

Deleting the dormant branch passes the Deletion test and adds no Seam. Do not touch fixtures or add path handling.

## Improvement Backlog

1. `F-002` — delete the dormant fixture `files[]` contract. Expected impact: `simplicity +0.5; test_strategy +0.5; credibility +0.5`.

## Deepening Candidates

None.

## Builder Notes

- Dormant optional contract: no fixture supplies `files[]`; delete unused input contracts until a real caller needs them.
- Candidate clone without severity evidence: two similar sites with no current drift remain Cosmetic.
- Bounded private validation Modules: split by existing responsibility; do not add registries or protocols.

### Scorecard humility check

`test_strategy` 8 may under-credit the complete fixture corpus; `domain_modeling` 9 depends on validator-enforced JSON invariants rather than construction-time types; `architecture_quality` 9 assumes the 779-line history Module remains locally coherent.

## Final Judge Narrative

Place, close to the bar. The validator split is honest and fully covered; one dead fixture-input branch remains a cheap subtractive fix. F-003 is withdrawn from the backlog because similarity alone does not establish Noticeable severity.

## Loop 2 Result

Deleted the unused optional fixture `files[]` contract. The full validator, fixture, smoke, standalone-selftest, and Ruff suite passed; F-002 is resolved with no unintended regression.

## Loop 2 Implementation Review

Reviewer ran inline because provider detection was `unknown`; verdict requires manual confirmation. Approved: Reality, Honesty, and Regression checks passed. The dormant branch is gone, no replacement layer was added, and no used fixture contract changed.
