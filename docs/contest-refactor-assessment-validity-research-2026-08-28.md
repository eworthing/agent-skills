# Contest-Refactor Assessment Validity Research

**Date:** 2026-08-28

**Repository:** `/Users/Shared/git/agent-skills`

**Bound revision:** `784eeb5cc6b9bac7f057b86dff972f191e8b26cb`

**Research prompt:** [`contest-refactor/plans/assessment-research-prompt.md`](../contest-refactor/plans/assessment-research-prompt.md)

**Disposition:** seven gaps accepted; headline grading and certification omitted;
competitor comparison complete (47/47 repositories dispositioned 2026-08-28)

## Executive decision

`contest-refactor` can support a defensible source-bound **Refactor Quality**
assessment, but the current evidence does not support a headline grade or any
certification-bearing decision.

Preserve:

- the explicit architecture-only boundary;
- source-root discovery and preflight;
- the Evidence Chain;
- stable finding identity and history;
- source revision and candidate-fingerprint binding;
- strict artifact validation;
- trial-validity and no-silent-exclusion rules;
- the independent challenge as adversarial evidence.

Change:

- make constructs, claim ceilings, applicability, coverage, confidence, and
  uncertainty explicit;
- represent findings, successful executions, applicability decisions,
  residuals, measurements, and provenance in one assessment model;
- project one canonical finding into multiple constructs without cloning its
  identity;
- make every mechanism's role and cost explicit;
- give pipeline failures a shared stage and invalidation envelope;
- present `HALT_SUCCESS` as internal workflow completion, not certification.

Measure before adopting:

- semantic-judge reliability and restraint;
- cut-score validity;
- model, prompt, and corpus drift;
- multidimensional assessment coverage;
- enforceable runtime and token cost.

Defer or omit:

- Security, Migration Safety, Concurrency Preservation, accessibility,
  runtime-reliability, and performance certificates;
- a composite score or average as a headline grade;
- any unqualified `certified` output.

The current skill already says its result is structural rather than ship
readiness ([`SKILL.md:17`](../contest-refactor/SKILL.md#L17)). The problem is
not the boundary statement. The problem is that broader constructs still flow
through the same dimensions and terminal decision.

## Revision and provenance manifest

| Binding | Examined value |
| --- | --- |
| Repository | `/Users/Shared/git/agent-skills` |
| Branch | `main` |
| Source revision | `784eeb5cc6b9bac7f057b86dff972f191e8b26cb` |
| Initial research revision | `ffa40232b9b4a2e496f6c4918caab8c80ce07581` |
| Intervening change | SPT Q3 owner-count experiment shipped: 2/2 primary flips, 4/4 restraint clean |
| Effect of intervening change | Changes simplification-fix selection; does not change any assessment-validity gap or evidence below |
| Dirty state before this report | Untracked research prompt only |
| Research-prompt SHA-256 | `f49a6ac7e76ad693429a068359321ad20102d8d18d21c71998ee6cee54c353f4` |
| Candidate fingerprint | Not applicable; no terminal target artifact was assessed |
| Research profile | Assessment-validity research, not a production grading profile |
| Python | 3.11.9 |
| Git | 2.54.0 Apple |
| Ruff | 0.15.6 |
| Host | Darwin arm64 |
| Research model | Codex/GPT-5 family; exact hosted build not exposed |
| Code graph | 25,053 nodes, 46,786 edges, indexed at the bound revision |
| Graph limitations | Partial parse of `SKILL.md:225-238` and four Swift corpus ranges; direct source used for cited claims |
| Fixture validation | 102 artifact fixtures passed |
| Gold-corpus validation | 26 pack directories passed |
| Relevant self-tests | Coverage ledger, G5, G32 panel/coupling, G37, G40, G49, G50, and trial validity passed |

### Competitive-analysis checkpoint

The local corpus at `refs/competitors/contest-refactor/` contains 47 candidate
repositories. All 47 were dispositioned on 2026-08-28; the method, matrix,
adopted and rejected mechanisms, changed conclusions, and residual uncertainty
are in the [Competitor analysis](#competitor-analysis) section below. The
findings in this report remain current-source findings; the competitor section
records where external evidence amended them.

### Corpus discrepancy

The evaluation README still declares “25 packs: 12 Python, 13 Swift” and lists
12 Python packs ([`evals/README.md:8`](../contest-refactor/evals/README.md#L8)).
The bounded directory inventory and `validate-gold-corpus.py` both find 26
packs. `config-precedence-duplicate-authority` is the thirteenth Python pack.
The executable corpus is sound, but its prose inventory is stale. This is a
live example of why corpus coverage and corpus identity must be machine-bound.

### Source precedence

Current source and executable validation outrank older plans. Historical
measurements remain evidence only for the exact revisions, prompts, models,
and corpora they record. The panel result, for example, binds
`skill_rev 20bcf000...` and an older protocol digest; it is evidence about that
protocol, not current certification evidence.

## Competitor analysis

Completed 2026-08-28 against the frozen corpus at
`refs/competitors/contest-refactor/` (47 repositories). Citations below use
`repo@rev` with repository-relative paths; every cited revision is the
repository's HEAD in the local corpus.

### Selection method and coverage statement

Tiered by cheap maturity/relevance triage (layout, language, tests, releases,
assurance documents, executable validators — not popularity or name), then
promoted on evidence:

| Tier | Count | Repositories | Method |
| --- | --- | --- | --- |
| Deep-dive | 9 | crucible, dsh-skill-eval, harness-eval, skilllens, aws-agent-skill-eval, opendatahub-agent-eval-harness, alibaba-open-code-review, archgate-cli, agentlint | codebase-memory indexed (projects `cr-*`), graph + direct-source reads, index coverage checked for cited paths, smallest relevant tests executed where feasible |
| Medium | 5 | cloudflare-security-audit, anthropic-security-review, center-audit, logic-lens, prism | targeted schema/script reads; executable validators run where cheap |
| Escalated from triage | 3 | compound-engineering-plugin, code-quality-atlas, brooks-lint | full records with executed checks after triage found implemented mechanisms |
| Triage-rejected | 30 | remainder | README + layout + targeted file reads; one-to-two-line cited rejection each |

Executable verification actually performed: dsh-skill-eval full suite (51
assertions), opendatahub 67 enforcement tests, aws `test_unified_report` (54),
archgate 3 dependency-free engine test files (57), agentlint registry (99) +
scorer (21) tests plus a live scanner run (51 records), compound-engineering
bun suites (18 + 62) plus a live confidence-demotion demo, code-quality-atlas
pytest (90 + 9), brooks-lint benchmark (30/30), cloudflare
`validate-findings.cjs` live, center-audit jsonschema CI shapes live, and
standalone execution of extracted load-bearing functions from crucible
(9/9 of its own stats assertions plus a power probe), harness-eval (scoring),
dsh-skill-eval (contamination reproduction), and aws (weight redistribution).
Not executed: alibaba's Go tests (no Go toolchain on this host — source and
test-source reading only), skilllens (ships zero tests), and the full
crucible/harness-eval TypeScript suites (dependency installs declined).
Load-bearing citations and numbers were independently re-verified in this
session: `computeTerminal` and `validateLocked` read verbatim at the cited
lines, aws weight redistribution read verbatim, crucible `pass@k` confirmed
comment-only, and the skilllens ICC/severity numbers recomputed exactly from
the published CSV.

### Comparison matrix — accepted gaps × strongest competitor evidence

| Gap | Strongest implemented precedent | Relation to provisional design |
| --- | --- | --- |
| P0 construct conflation | skilllens two-axis rows (unmeasured construct = null, never zero; convention-only); code-quality-atlas floor/preference tier (tested, lens-grain); compound-engineering severity×confidence independence (schema + demotion code) | None cleaner than per-finding construct projections; conventions and lens-grain splits adopted as corroboration only |
| P0 semantic-judge calibration | **None in 47 repositories.** Zero calibration machinery anywhere (grep + read across all deep-dive repos). Closest methods: agentlint blind-tiered rank corpus; skilllens cross-config corpus (data, not machinery) | Gap is genuinely novel; eligibility gate kept, amended (see changed conclusions) |
| P0 applicability/coverage validity | alibaba run manifest (partition invariant, derived terminal state, ~40 tests); ODH `max_error_rate` + errored-vs-skipped (executed); center-audit schema-rejected "clean without disproof" (executed) | Strong mechanics adopted; every precedent is narrower or opt-in — mandatory policy retained |
| P1 residual model | archgate suppressions: reason-or-void + unused-waiver warning (29 tests, executed); center-audit `INVARIANT_DRIFTED/REPLACED` | Both adopted as refinements; no competitor records accepting authority or expiry |
| P1 decision roles | agentlint registry-drift contract test (99 assertions, executed); ODH consumer-agreement contract test (executed); ODH declared-not-inferred construct type | Role vocabulary kept; enforcement pattern shifts from gate logic to drift/coupling selftests |
| P1 failure taxonomy | **No stage taxonomy anywhere in 47 repositories.** alibaba two-enum run/item split is the closest partial | Novel; envelope kept, seeded with measured failure modes and the two-level cause split |
| P2 cost as adoption field | ODH substrate-level `--max-budget-usd` + fail-closed cost judge — the only real precedent; crucible vendor-cost gates + judge-cost fold-in; harness-eval `CostSource` provenance enum | Requirement confirmed novel at adoption grain; record slimmed, `cost_source` and fold-in rule adopted |

### Adopted mechanisms (evidence-backed)

1. **Derived validity, not stored status pairs.**
   alibaba-open-code-review@533f7367: `computeTerminal`
   (`internal/session/manifest.go:941-958`) derives
   complete/partial/failed/skipped purely from coverage sets plus a
   run-failure override; `validateLocked` (:841-874) enforces the partition
   invariant `|selected| = |completed|+|reused|+|failed|+|waived|`, rejects
   unclassified failures, and requires a reason on every waiver — at
   construction, so an invalid manifest never exists. Verified verbatim this
   session. Adopted: v6 stores one `validity` value that G51 recomputes from
   applicability, coverage, and pipeline failures; the status+validity pair
   and its allowed-pairs table are deleted.
2. **Coverage partition and reject-unclassified.** Same evidence. Adopted into
   the coverage model and failure rules: a selected-universe item must land in
   exactly one terminal set, and an unclassifiable failure is an error, never
   a downgraded default.
3. **Errored-vs-skipped cause disambiguation; unevaluable renders unevaluable.**
   opendatahub-agent-eval-harness@db0732c3: `_unavailable_reason`
   (`skills/eval-run/scripts/score.py:2501-2505`) distinguishes "errored on N
   cases" from "skipped for all cases", both gating;
   `tests/test_threshold_consumers.py:118-148` proves an unevaluable gate
   renders "Could not evaluate thresholds" and never PASS, and that the
   MLflow helper raises rather than tagging clean. Executed (67 tests green).
   Adopted into coverage/failure semantics: an empty breach set must mean
   "checked, none", never "never checked".
4. **Invalidate-don't-clamp with declared scales.** ODH:
   `tests/test_score_range_enforcement.py:32-143` — a judge value outside its
   declared `score_range` becomes an error sample (dropped from the mean,
   never clamped; NaN explicitly rejected), incrementing the error denominator
   that feeds the coverage gate. Executed. Adopted: scalar measurements
   declare a scale; off-scale or out-of-vocabulary judge output becomes a
   judgment-stage pipeline failure feeding coverage — never a coerced value.
   The mirror-image anti-patterns are recorded below.
5. **Consumer-agreement contract testing.** ODH
   `tests/test_threshold_consumers.py:32-66`: one shared case table asserted
   against the CLI gate, the HTML report, and the MLflow tagger, written after
   those consumers drifted in production. Adopted in house style as a
   G35-style coupling check plus fixtures: user-facing handoff/progress text
   must agree with the assessment record it renders.
6. **Registry-drift invariant testing.** agentlint@7a22cf6d:
   `tests/test-registry-consistency.js` (99 assertions, executed) binds
   evidence registry ↔ weights ↔ actual handler code, including
   "scope==extended iff dimension∈{extended}". Adopted as a selftest family:
   canon vocabulary tables must match validator dispatch, so a canon value
   without an enforcing branch fails the selftest.
7. **Not-run exclusion with a derived scope label.** agentlint
   `src/scorer.js:107-151` (tests executed): a dimension with no evidence is
   `not_run` with `score:null` — excluded from the denominator, never zero —
   and the output carries a derived `score_scope` label naming what the number
   covered. Adopted: null-never-zero for unmeasured constructs, and the
   user-facing completion output carries a derived scope line.
8. **Constant fields replaced by canon SSOT.** Within schema v6 the
   `certification:"not_issued"` and `aggregation:"omitted"` objects are fully
   determined by the schema version, so they carry no per-artifact
   information. Following the derivation evidence above (alibaba, agentlint),
   the disposition moves to the profile declaration in canon — still explicit
   and machine-readable, stated once — and G52 still rejects certification or
   aggregate language in user-facing output.
9. **Explicit-vs-implicit binding transitions; unverifiable ≠ mismatch.**
   alibaba `internal/session/resume_identity.go:50-128`: a provider/model
   change from an explicit flag is allowed and recorded as lineage; the same
   change arriving from config/env drift is rejected; a resume that cannot be
   verified (missing manifest, schema mismatch) is typed separately from a
   mismatch, and an empty-corpus false-pass guard is documented and enforced.
   Adopted into the fingerprint/invalidation rules.
10. **Ceiling injected into the consumer's own format.** alibaba
    `cmd/opencodereview/sarif.go:299-347`: every non-complete run attaches a
    SARIF notification carrying the coverage message so a consumer that
    ignores the side object still cannot read partial as clean. Adopted: the
    handoff markdown must carry the coverage/ceiling line itself, not only the
    JSON.
11. **Residual refinements.** archgate-cli@fa1086f4
    `src/engine/suppressions.ts:203-240` (tests executed): a waiver without a
    reason suppresses nothing (fails open toward reporting), and an unused
    waiver warns — a free, automatic review trigger. Adopted for v6
    residuals: empty rationale voids acceptance; a residual whose source no
    longer resolves is flagged stale. center-audit@b154fb0e's
    `INVARIANT_HOLDS/DRIFTED/REPLACED/CONTRACT_REJECTED` re-validation typing
    (schema-enforced, executed) is adopted as the disposition shape for
    residual review outcomes.
12. **Cost provenance and fold-in.** harness-eval@88146404
    `src/types.ts:193-198`: `CostSource =
    harness-reported|profile-priced|tokens-only`, badged in the report,
    "never a fabricated harness-reported figure". crucible@2be110b5
    `src/suite.ts:113`: the judge's own cost folds into the assessed unit's
    cost. ODH `agent_eval/agent/claude_code.py:136`: `--max-budget-usd` as a
    substrate-level pre-execution cap, plus a fail-closed cost judge (missing
    cost data fails, never skips). All three adopted into the slimmed cost
    record.
13. **Calibration measurement methods (for the G2 plan, not as calibration
    evidence).** dsh-skill-eval@8288582d `test/catalog-fidelity.test.mjs`:
    byte-frozen fixture pins the exact prompt the instrument sends, versioned
    in the filename — adopted as a frozen-hash selftest binding the grading
    prompt (house machinery exists). harness-eval `src/grading/judge.ts:162-193`:
    k=3 samples, median, every sample persisted — adopted as the required
    shape for calibration-mode scalar judgments. agentlint
    `tests/calibration/`: blind-tiered 15-repo corpus with rank analysis —
    method adopted with two corrections (bind results to the judge/scanner
    revision; report the separation the data supports, not monotonicity).
    crucible `src/stats.ts:77-113` (its own 9 test assertions re-executed
    standalone): a two-proportion significance gate needs ≈40 paired trials to
    detect a 60%→80% shift at 95% — the power floor any significance-based
    eligibility rule must budget for; crucible ships that gate with default
    k=3, which cannot satisfy it.

### Rejected mechanisms and negative catalog

Rejections that shaped the design:

- **Weight redistribution across missing constructs** —
  aws-agent-skill-eval@13b2277b `skill_eval/unified_report.py:42-66` (read
  verbatim; behavior executed): a skill evaluated on trigger precision alone
  grades A (90.0) while the same skill fully evaluated grades B (83.8) —
  losing coverage raises the grade; "nothing evaluated" and "measured and
  terrible" are both F. Its CI workflow defaults `GRADE="A"` and prints 100
  inside `except Exception` (`.github/workflows/skill-eval.yml:96-116`).
  Rejected and cited as the executed counter-example that makes G3's
  mandatory (not opt-in) policy load-bearing.
- **Measurement-infrastructure failure scored as substantive failure** — five
  instances across three unrelated teams: crucible `src/assertions.ts:195-197`
  (unparseable judge → fail), crucible `src/suite.ts:104,121-130`, dsh-skill-eval
  `runner.js:87` (null verdict counted as a valid "did not trigger" —
  reproduced executably: headline accuracy 0.75 contradicts the repo's own
  per-case correctness field, with a green test suite), harness-eval
  `src/grading/evaluator.ts:242-255` (evaluator budget exhaustion scored as
  step failure) and `src/grading/judge.ts:151-154` (judge budget exhaustion →
  0/10 enters the median). G3/G6 are upgraded from design inference to a
  demonstrated industry-wide defect class.
- **Silent normalization coercion** — alibaba
  `internal/tool/code_comment.go:128-142`: out-of-vocabulary category → 
  "other", severity → "low", pinned as intended by its own drift test — while
  the same codebase refuses to fabricate an unclassified *failure*. skilllens
  `judge_logic.py:589-605` launders an out-of-vocabulary verdict into a
  plausible one derived from a scalar. anthropic-security-review
  `findings_filter.py:298-306` keeps a finding with hardcoded confidence 10.0
  when its filter API call fails. All rejected; together they are the
  evidence for G6's normalization-stage invalidation path.
- **Scale guessing** — agentlint `src/scorer.js:51-60` infers the scale from
  the value's magnitude (≤1 fraction, ≤10 tenths, ≤100 percent), so "1 of 10"
  scores perfect. Rejected; declared scales only (ODH rule).
- **Assurance-case documents as assurance mechanisms** — both
  `ASSURANCE_CASE.md` (alibaba) and `ASSURANCE-CASE.md`/`APPROVAL_POLICY.md`
  (archgate) have zero enforcing code (grep-verified), and alibaba's cited
  line numbers have already drifted (`filereader.go:98` is a bare brace; the
  real checks sit at :101/:112). Rejected as mechanisms; alibaba's explicit
  per-threat "Not applicable" column maps onto v6's `applicability[]`.
- **Prompt-grep "evals"** — a recurring corpus-wide anti-pattern (ngmeyer,
  conorbronsdon, mhylle, tech-audit-skill, sentry/gstack partially):
  directories named `evals/` or `tests/` that grep the skill's own prose for
  required phrasing rather than measuring produced output. Named here so it
  is not mistaken for measurement infrastructure in future comparisons.
- **Considered-and-rejected simplifications**: replacing applicability[] and
  coverage[] with harness-eval's trial-grain `exclusions[]` + top-two
  `inconclusive` flag (wrong grain; returns no ceiling at n=1 — verified —
  which is contest-refactor's normal shape); collapsing G51/G52 into
  construction-time validation (there is no trusted constructor — the emitter
  is a model; the gates are the construction check); dropping revision binding
  because archgate persists no verdicts (contest-refactor persists artifacts,
  histories, and challenge bindings across loops, so the binding problem is
  real).

### Changed conclusions

Amendments to earlier sections of this report; the gap dispositions themselves
are unchanged (all seven remain accepted):

1. **G2 calibration key widened.** The skilllens published corpus
   (`docs/artifacts/data/aggregate.csv`, 1,732 rows) yields ICC(1,1) = 0.486
   across six harness×model configurations on 206 complete cases
   (recomputed and confirmed this session) for its most behaviorally grounded
   metric. Configuration dependence — not only rater subjectivity — is the
   threat, so the calibration key must include the harness and executor
   model, in addition to judge model, prompt, tools, policy, and corpus.
2. **Agreement must be attributed before it counts.** skilllens's security
   scores agree at r≈0.97 across configs because severity and existence come
   from one shared static scan and 32% of findings carry an imputed 0.6
   exploitability constant — the coefficient measures the shared input. A
   reliability estimate offered as calibration evidence must show the
   agreeing variance comes from independent measurement.
3. **A measured G1 failure cost.** 27 of 97 skilllens runs whose
   `overall_severity` is `H` score ≥90 on the 0-100 security scale (median
   78.8, max 99.4; recomputed this session): the headline number reads clean
   while a typed field on the same record says a high-severity risk exists.
4. **G2 remains genuinely novel.** No calibration machinery exists anywhere
   in the 47-repository corpus; no repo has run a human-agreement study. The
   eligibility gate cannot be borrowed or delegated. Its evidence bar gains
   the ≈40-paired-trial power floor for any significance-based rule, and the
   blind rank-criterion corpus becomes the preferred eligibility instrument —
   with agentlint's own honest reading as the caution: its corpus separates
   tier C from A/B decisively and does not separate A from B at all
   (means 69.0 vs 65.2), while its runner prints only "Monotonic: YES".
5. **G6 remains genuinely novel and gains seeds.** No shared stage taxonomy
   exists in the corpus. The taxonomy is seeded with four failure modes
   competitors paid for: judgment-stage off-scale values; aggregation-stage
   shrinking denominators; persistence-stage denominator loss (ODH's
   `test_max_error_rate_works_on_a_persisted_summary` exists because the
   denominator was stripped during serialization); reporting-stage consumer
   drift. Plus one loop rule from crucible's optimize path
   (`src/optimize.ts:545`): an invalid result must not advance a
   convergence/plateau counter.
6. **G7 confirmed near-null industry-wide.** agentlint adopted a 7-check AI
   surface with zero cost accounting; nobody records adoption-grade cost. The
   requirement stands; the record slims (see spec) and gains `cost_source`,
   the judge-cost fold-in rule, and a substrate-level ceiling option.
7. **Invalidation rules gain the explicit-transition distinction** (adopted
   mechanism 9): a binding change is acceptable only when explicitly
   requested; drift-induced change invalidates; unverifiable is typed
   separately from mismatch.

### Residual uncertainty (competitor scope)

- The 30 triage-rejected repositories were dispositioned on README, layout,
  and targeted reads only; a mechanism buried in an unexamined subsystem
  could have been missed. Spot-checks (e.g., trailofbits' 39 plugins sampled
  at ~6) support but do not prove the rejections.
- alibaba's Go tests were never executed (no toolchain); its ~40
  manifest-test claims rest on source and test-source reading, with two
  load-bearing functions independently re-read verbatim this session.
  alibaba's `internal/agent`, `internal/llmloop`, and budget subsystems went
  unread — its G7-relevant budget accounting exists but was not assessed.
- Unexamined subsystems in deep-dive repos include harness-eval's driver/
  provider/studio trees, ODH's Harbor/MLflow/ANOVA execution paths (ANOVA
  module never executed), aws's analyzer rule quality (~570 of 621 tests not
  run), skilllens's `run_record_parser.py` (the skill-usage detector its
  manipulation check depends on), and crucible's redteam/telemetry trees.
- Statistical caveats: the skilllens ICC treats non-crossed configs as
  exchangeable raters and its floored gain metric likely inflates agreement
  (0.486 is optimistic); agentlint's τ≈0.76 rests on 15 points, 31 tied
  pairs, one blind rater.
- Index coverage is best-effort: the indexer excluded `skills/*/scripts/` in
  ODH and `scripts/` in skilllens (claims there rest on direct reads plus
  executed tests), and `agentlint/src/scanner.sh` was parse-partial (claims
  there are behavioral, from a live run).

## Verified gap register

### P0 — Refactoring quality and assurance quality can be conflated

1. **Gap and construct.** The declared Refactor Quality construct excludes
   correctness, security, performance, and release readiness, but those
   constructs influence the same scorecard and terminal state.
2. **Current-state evidence.** The architecture-only boundary is explicit in
   [`SKILL.md:17`](../contest-refactor/SKILL.md#L17). The canonical dimensions
   nevertheless include “Concurrency and runtime safety” and “Test strategy
   and regression resistance”
   ([`scorecard-dimensions.toml:17-31`](../contest-refactor/canon/scorecard-dimensions.toml#L17)).
   The concurrency anchor makes ordering and runtime-safety claims, while the
   test anchor says the suite would catch a future regression
   ([`architecture-rubric-scoring.md:55-69`](../contest-refactor/references/architecture-rubric-scoring.md#L55)).
   Security findings score under `framework_idioms` or `credibility`
   ([`lens-security.md:1-3`](../contest-refactor/references/lens-security.md#L1));
   accessibility findings affect `framework_idioms` and `test_strategy`
   ([`lens-apple.md:207-218`](../contest-refactor/references/lens-apple.md#L207));
   efficiency findings map into the same structural scorecard
   ([`lens-efficiency.md:1-5`](../contest-refactor/references/lens-efficiency.md#L1)).
3. **Applicability and scope.** Applies whenever evidence about a
   non-architectural consequence changes a structural score or the common
   terminal decision.
4. **Coverage requirement.** Every load-bearing condition needs a construct
   projection. A broader assurance conclusion additionally needs its named
   profile's evidence and coverage.
5. **Existing mechanism.** Boundary prose, lenses, stable findings, Evidence
   Chain, candidate binding, and the HALT handoff disclaimer.
6. **Proposed mechanism.** Keep one finding identity; project its structural,
   correctness, security, accessibility, or other consequences separately.
7. **Decision role.** `gate`: reject a conclusion whose load-bearing evidence
   crosses a construct boundary.
8. **Required evidence.** Source-bound condition, consequence per construct,
   report/profile, claim ceiling, and profile-specific assurance evidence.
9. **Calibration and validity plan.** Test construct classification and false
   escalation on expert-adjudicated multi-consequence cases. Measure it
   separately from finding detection.
10. **Pipeline failure handling.** Missing or ambiguous projection invalidates
    the affected score or gate; it does not discard the underlying finding.
11. **Evaluation and adoption cost.** Moderate schema and reporting work; no
    inherent extra model call.
12. **Residual risk and invalidation.** One condition may legitimately affect
    several constructs. New consequences extend projections rather than
    create findings. Source, profile, rule, or critical-evidence changes
    re-evaluate affected projections.
13. **Claim ceiling.** “No profile-blocking structural condition was found in
    the evaluated scope.” It cannot establish correctness, security,
    accessibility, runtime reliability, performance, or release readiness.

**Disposition:** accepted.

### P0 — Semantic grading is insufficiently calibrated for certification-bearing decisions

1. **Gap and construct.** Current semantic scoring cannot support a reliable
   9.5 certification cut.
2. **Current-state evidence.** Independent passes differed by a mean 1.33
   points per dimension and as much as 3.0; `test_strategy` moved from 9.5 to
   6.5 ([`evals/README.md:1375-1387`](../contest-refactor/evals/README.md#L1375)).
   A controlled N=3 repeatability probe still had a mean gap of 1.22
   ([`evals/README.md:1397-1417`](../contest-refactor/evals/README.md#L1397)).
   Priming reduced apparent variance without establishing accuracy
   ([`evals/README.md:1427-1456`](../contest-refactor/evals/README.md#L1427)).
   Across 81 blind scores, none reached 9.5
   ([`evals/README.md:1482-1502`](../contest-refactor/evals/README.md#L1482)).
   The reanalysis reports single-rater ICC `0.166`, SEM `0.283`, and an
   impossible observed score of at least 10.06 to clear a true 9.5 at 95%
   confidence
   ([`evals/README.md:1504-1527`](../contest-refactor/evals/README.md#L1504)).
3. **Applicability and scope.** Every score, threshold gate, comparison, or
   certificate relying on semantic judgment.
4. **Coverage requirement.** Independent corpora, constructs, languages,
   model versions, near-threshold cases, positive controls, restraint cases,
   and invalid-trial accounting.
5. **Existing mechanism.** Score anchors, scorecard-coupling studies,
   noise-floor keying, challenger cases, panel gating, raw records, and trial
   validity.
6. **Proposed mechanism.** Keep scalar judgments advisory until a
   calibration-eligibility gate passes. Preserve source-backed findings
   independently of scalar severity.
7. **Decision role.** `gate`: no score-dependent certificate without current
   calibration for the exact model, prompt, tools, policy, and corpus.
8. **Required evidence.** Blinded repeat ratings, independent adjudication,
   held-out validation, exact judge configuration, variance and bias
   measurements, invalid trials, raw outputs, and enforceable cost limits.
9. **Calibration and validity plan.** Measure sensitivity, restraint false
   positives, test-retest reliability, inter-rater reliability, priming and
   position effects, model drift, discrimination, SEM, and interval
   uncertainty. Acceptance thresholds must be risk-derived and preregistered.
10. **Pipeline failure handling.** Excess disagreement, stale calibration,
    missing model identity, invalid corpus, or threshold uncertainty produces
    `uncalibrated` or `indeterminate`; it never becomes a pass by averaging.
11. **Evaluation and adoption cost.** High. The current panel record contains
    6,276,593 aggregate member tokens; individual member totals range from
    321,855 to 1,668,496. Its 1.2M cap was post-hoc and was exceeded.
12. **Residual risk and invalidation.** Judge, prompt, sampling, tools, rubric,
    or corpus changes invalidate the associated calibration key.
13. **Claim ceiling.** “This judge assigned this score under this bound
    configuration.” It does not establish an objective quality level or a
    valid certificate cut.

NIST recommends validating that a proxy measures its claimed construct,
defining operating conditions, and documenting variance and reliability
([AI RMF Playbook, Measure 2.5](https://airc.nist.gov/docs/AI_RMF_Playbook.pdf)).
LLM-judge research independently documents position, verbosity,
self-enhancement, and reasoning biases
([Zheng et al.](https://arxiv.org/abs/2306.05685)).

**Disposition:** accepted. Current certification fails this gap.

### P0 — Applicability, scope, or coverage can omit relevant evidence without sufficiently visible invalidity

1. **Gap and construct.** Source-root coverage is strong, but
   multidimensional coverage is not a terminal validity gate.
2. **Current-state evidence.** Source roots are enumerated and scoped claims
   disclosed ([`startup.md:25-30`](../contest-refactor/references/startup.md#L25)).
   Preflight checks root completeness and hotspot evidence
   ([`startup.md:41-52`](../contest-refactor/references/startup.md#L41)). The
   terminal ledger explicitly measures citations rather than files read and
   cannot distinguish uncited-clean from unread
   ([`halt-handoff.md:56-104`](../contest-refactor/references/halt-handoff.md#L56)).
   Partial or absent analyzer coverage remains legal. The gold-corpus prose
   count is already stale by one pack.
3. **Applicability and scope.** Source roots, platforms, configurations, test
   surfaces, analyzers, runtime paths, accessibility processes, and evaluation
   corpora.
4. **Coverage requirement.** A vector for source, platform/language, test
   surface, analyzer execution, runtime paths, named requirements/controls,
   and evaluation corpus. Missing applicable critical coverage invalidates the
   dependent claim.
5. **Existing mechanism.** Root enumeration, G40/G49/G50, preflight, typed tool
   statuses, citation ledger, full/incremental test distinction, and
   trial-validity denominators.
6. **Proposed mechanism.** Profile-owned applicability decisions and coverage
   requirements that produce an explicit assessment-validity state.
7. **Decision role.** `gate`.
8. **Required evidence.** Enumerated universe, inclusions/exclusions, N/A
   rationale, tool coverage, test/oracle mapping, runtime configuration,
   corpus identity, and executable absence oracles.
9. **Calibration and validity plan.** Seed omitted roots, platforms, analyzer
   failures, missing requirements, and corpus-registration drift. Verify that
   each invalidates only the dependent claim.
10. **Pipeline failure handling.** Unknown applicability or missing critical
    coverage becomes `not_evaluated` or `invalid`, never clean. Exogenous
    collection failures retain their denominator and follow bounded retry.
11. **Evaluation and adoption cost.** Mostly existing discovery and
    validators; no required new model call. Moderate engineering effort.
12. **Residual risk and invalidation.** New roots, features, platforms,
    controls, tests, corpus cases, or analyzer versions trigger recomputation.
13. **Claim ceiling.** Only the declared and adequately covered universe. No
    repository-wide or runtime-wide absence claim follows from citation
    coverage.

OWASP ASVS requires excluded requirements to carry a reason and states that
automated testing alone cannot complete verification
([OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)).
WCAG conformance similarly depends on full pages and complete processes
([WCAG 2.2](https://www.w3.org/TR/WCAG22/)).

**Disposition:** accepted.

### P1 — The residual model is architecture-specific and partly manual

1. **Gap and construct.** Residuals are attached to scorecard dimensions and
   can authorize `HALT_SUCCESS`, but they do not represent residual assurance
   risk across constructs.
2. **Current-state evidence.** A 9.5 score requires a named residual and
   accepted/queued disposition
   ([`architecture-rubric-scoring.md:9-31`](../contest-refactor/references/architecture-rubric-scoring.md#L9)).
   Inline expiry is optional, and the standard preset accepts a prose
   rationale. G5/G21/G37 validate structure and terminal consistency, not the
   truth of the risk or the authority accepting it.
3. **Applicability and scope.** Every condition intentionally left unresolved,
   accepted, deferred, expired, waived, or rendered not applicable.
4. **Coverage requirement.** Construct, profile, affected claim, evidence,
   acceptance authority, rationale, review trigger, and blocking effect.
5. **Existing mechanism.** Scorecard residual fields, path-pattern residuals,
   expiry, G5/G21/G37, and convergence passes.
6. **Proposed mechanism.** A typed canonical residual referenced by one or
   more construct projections. Existing scorecard fields become a derived
   compatibility projection during migration.
7. **Decision role.** `report`; the applicable profile determines whether the
   residual blocks.
8. **Required evidence.** Finding or scorecard source, construct projection,
   risk statement, accepting authority, evidence, review trigger, and affected
   profiles/claims.
9. **Calibration and validity plan.** Measure agreement on
   accept/queue/block, reopening rate, expiry behavior, and false acceptance on
   restraint cases.
10. **Pipeline failure handling.** Missing authority, evidence, ceiling, or
    review trigger makes the residual unaccepted and profile-blocking where
    applicable.
11. **Evaluation and adoption cost.** Low runtime; moderate migration work; no
    inherent new model call.
12. **Residual risk and invalidation.** Source or policy change, expiry, new
    evidence, or widened scope reopens the residual.
13. **Claim ceiling.** “This named risk was accepted for this profile and
    claim.” Acceptance does not prove that the underlying property holds.

**Disposition:** accepted.

### P1 — Proposed mechanisms lack an explicit decision role

1. **Gap and construct.** Mechanism authority is encoded inconsistently in
   prose and local fields.
2. **Current-state evidence.** Candidate tools use `promotion_allowed: false`;
   findings and residuals have local dispositions; provider routing delegates;
   plans defer mechanisms. A bounded search of all 22 canon files and the
   output contract found no shared `detect|score|gate|report|delegate|defer|exclude`
   role. [`remediation-fields.toml:70-73`](../contest-refactor/canon/remediation-fields.toml#L70)
   explicitly defers a broader disposition.
3. **Applicability and scope.** Every detector, metric, semantic judge,
   validator, gate, report, or delegated profile.
4. **Coverage requirement.** One primary role for every adopted mechanism;
   secondary roles only when a consumer inventory proves they are necessary.
5. **Existing mechanism.** `promotion_allowed`, validation-gate registry,
   delegation routing, residual dispositions, and advisory metric isolation.
6. **Proposed mechanism.** A closed role vocabulary used by assessment records
   and profile mechanism definitions.
7. **Decision role.** `gate`: a mechanism without a role is not adoption-ready.
8. **Required evidence.** Consumer inventory showing whether the mechanism
   affects detection, scores, gates, reports, or dispatch.
9. **Calibration and validity plan.** Mutation tests ensuring detectors cannot
   silently gate, reports cannot alter scores, and deferred/excluded mechanisms
   have no active decision consumer.
10. **Pipeline failure handling.** Missing or contradictory role fails
    configuration validation. The underlying evidence remains available but
    cannot affect a decision.
11. **Evaluation and adoption cost.** Small schema/validator change and a
    one-time mechanism inventory; no additional model calls.
12. **Residual risk and invalidation.** Consumer or authority changes require
    role review.
13. **Claim ceiling.** A role states how evidence is used. It does not establish
    that the evidence or resulting claim is valid.

**Disposition:** accepted.

### P1 — Pipeline failures lack a shared taxonomy

1. **Gap and construct.** Validity-relevant failures use unrelated
   vocabularies without a common stage or downstream invalidation model.
2. **Current-state evidence.** Evaluation trials use four exogenous invalid
   reasons ([`trial-validity.toml:7-56`](../contest-refactor/canon/trial-validity.toml#L7)).
   Reviewer retries use timeout, spawn error, and malformed JSON
   ([`output-format-json-rules.md:183`](../contest-refactor/references/output-format-json-rules.md#L183)).
   Panels add budget exhaustion; discovery uses partial/absent/not-applicable;
   attestations use consistency-check/unavailable; the state machine has
   separate resource-death transitions
   ([`states.toml:28-67`](../contest-refactor/canon/states.toml#L28)).
3. **Applicability and scope.** Collection through final reporting.
4. **Coverage requirement.** Every failure names stage, cause class, affected
   records/claims, visibility, retryability, exclusion, invalidation, and
   downstream disposition.
5. **Existing mechanism.** Keep every current domain-specific enum and map it
   into a shared envelope.
6. **Proposed mechanism.** One pipeline-failure record; no lossy replacement
   enum.
7. **Decision role.** `report`.
8. **Required evidence.** Raw error reference, stage, attempts, producer,
   affected subject/evidence, classification basis, and retry/exclusion result.
9. **Calibration and validity plan.** Fault injection at every stage. Verify
   that candidate/adherence failures remain counted while exogenous failures
   remain invalid and visible.
10. **Pipeline failure handling.** Stage-specific behavior is defined in the
    taxonomy below.
11. **Evaluation and adoption cost.** Low runtime; moderate schema and fixture
    work; no inherent model calls.
12. **Residual risk and invalidation.** New failure modes extend stage-local
    causes while preserving the common envelope.
13. **Claim ceiling.** Establishes pipeline validity and provenance, not source
    quality.

**Disposition:** accepted.

### P2 — Evaluation cost is not a required adoption field

1. **Gap and construct.** Cost is measured in selected experiments but is not
   required before every mechanism or profile is adopted.
2. **Current-state evidence.** Output records duration and panel token usage.
   The panel plan contains a cost model
   ([`rec1-panel-certification.md:356-380`](../contest-refactor/plans/rec1-panel-certification.md#L356)).
   The capability manifest correctly remains empty because cost cannot be
   enforced
   ([`panel-certification.toml:5-12`](../contest-refactor/canon/panel-certification.toml#L5)).
   No general adoption-cost requirement exists.
3. **Applicability and scope.** Every proposed detector, evaluator, judge,
   panel, profile, and recurring validator.
4. **Coverage requirement.** Runtime, calls, tokens, tools, engineering effort,
   maintenance, invalid/retry overhead, frequency, and enforceable ceiling.
5. **Existing mechanism.** Duration, token usage, `C_max`, budget exhaustion,
   capability manifest, and qualitative repair effort.
6. **Proposed mechanism.** Require a cost record before a mechanism moves
   beyond report-only experimentation.
7. **Decision role.** `gate`.
8. **Required evidence.** Representative measured cost and enforceable per-run
   and aggregate ceilings. Estimates remain labelled estimates.
9. **Calibration and validity plan.** Compare predicted and observed cost;
   record retry and invalid-trial overhead separately.
10. **Pipeline failure handling.** Unknown or unenforceable cost means `defer`.
    Exceeding a preregistered ceiling follows the profile's abort/exclusion
    rule.
11. **Evaluation and adoption cost.** Small bookkeeping overhead that prevents
    unbounded larger costs.
12. **Residual risk and invalidation.** Provider, model, prompt, corpus, tool,
    or execution-topology change invalidates cost evidence.
13. **Claim ceiling.** Cost evidence establishes feasibility only, not quality
    or assurance validity.

**Disposition:** accepted.

## Construct map

| Construct or report | Operational boundary | Prohibited inference |
| --- | --- | --- |
| Refactor Quality | Source-observable ownership, seams, depth, locality, simplicity, maintainability, and structural testability in declared roots | Structure alone proves behavioral preservation or correctness |
| Source Quality Audit | Inventory of source-observable conditions from inspection and analyzers across constructs | No finding proves absence without sufficient coverage and an oracle |
| Correctness and regression resistance | Behavior exercised by named tests/oracles in named configurations | Passing tests prove general correctness |
| Security and privacy | Named controls and threats assessed by profile-specific procedures | A static checklist proves product security or compliance |
| Accessibility | Named criteria assessed across applicable surfaces and processes | Source labels prove assistive-technology usability |
| Migration and data-loss safety | Versioned data fixtures, transitions, failure injection, rollback, and recovery | A clean build proves migration safety |
| Concurrency preservation | Compile-time isolation plus runtime evidence on applicable paths | Static ownership proves race freedom |
| Runtime reliability and performance | Runtime trials and benchmarks under stated workload/environment | Static efficiency observations prove production behavior |
| Assurance Gates | Non-compensatory results for separately named critical claims | One gate implies an unnamed assurance property |
| Measurement Reliability | Validity, reliability, bias, corpus, invalid-trial, version, and cost evidence for the instrument | High agreement proves construct validity |

NIST IR 8101 similarly requires a clear statement of what a test demonstrates
and distinguishes coverage from correctness
([NIST IR 8101](https://nvlpubs.nist.gov/nistpubs/ir/2016/NIST.IR.8101.pdf)).

## Claim-evidence matrix

| Evidence | Supported claim | Unsupported stronger claim |
| --- | --- | --- |
| Static ownership inspection | No conflicting owner was found in inspected source and scope | No race exists; runtime ordering is correct |
| Static analyzer clean result | No rule match occurred under the named tool/configuration and analyzed coverage | The defect class is absent everywhere |
| Successful build | Named targets compiled in the named configuration | Product correctness or release readiness |
| Passing tests | Named assertions passed on exercised inputs/platforms | General correctness or regression freedom |
| Strict-concurrency compile | Checked configuration satisfies those compiler rules | Race freedom on all runtime paths |
| Sanitizer/runtime concurrency test | No relevant failure was detected in executed paths | Global concurrency safety |
| Static security inspection | Named source-level control conditions were or were not observed in scope | Secure product or privacy compliance |
| Accessibility checks | Named criteria passed on evaluated surfaces/configurations | General accessibility conformance |
| Migration oracle | Named transitions preserved asserted invariants for fixtures | No production data loss |
| Benchmark | Observed distribution under stated workload/environment/repetitions | Production performance or reliability |
| Semantic score | Named judge assigned the score under the bound prompt | Objective interval-scale quality |
| Challenger held | Challenger failed to produce a qualifying break in recorded attempts | Candidate correctness or certification validity |
| Citation ledger | Files were cited as evidence | Files were read or comprehensively assessed |
| Fingerprint/provenance | Result is bound to the named subject/configuration | Evidence is true or sufficient |

Confidence stays inside these ceilings. It cannot upgrade static evidence into
runtime proof.

## Canonical assessment evidence model

Use `CURRENT_REVIEW.json` as the canonical live assessment artifact. Extend it
rather than create another evidence store. The shared model needs:

- subject binding: repository, revision, dirty-diff identity, candidate
  fingerprint;
- profile and policy binding;
- producer and semantic-judge configuration;
- applicability decisions and exclusions;
- multidimensional coverage;
- observations, findings, assurance results, residuals, measurements, and
  provenance;
- pipeline validity and failures;
- separate confidence and uncertainty;
- decision role, claim ceiling, and cost;
- explicit aggregation and certification disposition.

SLSA's Verification Summary Attestation is a useful structural precedent: it
binds a result to a subject digest, verifier, exact policy, input attestations,
and specifically named verified levels
([SLSA VSA](https://slsa.dev/spec/v1.2/verification_summary)). This is a data
model precedent, not a claim that `contest-refactor` supplies SLSA assurance.

### Finding identity and projection

- `stable_id` remains the canonical finding identity.
- One finding holds zero or more construct projections.
- Each projection names construct, consequence, report/gate, severity when the
  profile owns a severity scale, claim ceiling, and blocking effect.
- Aggregation, if ever enabled, deduplicates by `stable_id` before calculation.
- Separate findings require independent remediation, distinct evidence chains,
  or different source identities.
- Existing registry fuzzy matching remains the semantic duplicate-control
  mechanism; the validator must not pretend a hash can prove causal identity.

SARIF likewise uses stable result fingerprints and warns against absolute line
numbers as identity inputs
([SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html)).

### Invalidation

By default, dependent evidence is invalidated by changes to:

- source revision or bound dirty diff;
- candidate-fingerprint-bearing content;
- profile or policy;
- critical evidence;
- rule or tool configuration;
- analyzer or tool version;
- judge model, prompt, sampling, or allowed tools;
- corpus membership or adjudication.

A narrower rule is legal only when the profile declares it and an executable
impact oracle establishes that the change cannot affect the claim.

## Logical report projections

### Refactor Quality

Projects structural findings, structural claim ceilings, advisory scorecard
bands, residuals, applicability, and coverage. It does not inherit assurance
claims from other projections.

### Source Quality Audit

Projects source observations and findings from mechanical and semantic
inspection, including conditions that do not qualify for a gate. An empty
finding set is not an absence claim unless an executable oracle and required
coverage support it.

### Assurance Gates

Projects one result per applicable named control/profile:
`satisfied`, `not_satisfied`, `not_evaluated`, or `invalid`. Critical results
are non-compensatory and cannot be repaired by a high structural score.

### Measurement Reliability

Projects corpus identity, calibration, disagreement, bias, invalid trials,
version binding, uncertainty, and cost. It controls whether a semantic score
or certificate is eligible for decision use.

All four are views of the same records.

## Profile and certification decision

| Profile | Current disposition | Reason |
| --- | --- | --- |
| Refactor Quality | Report-only | Multidimensional coverage is incomplete and the 9.5 semantic cut is not calibrated |
| Source Quality Audit | Report-only | It is a heterogeneous inventory rather than one quality construct |
| Security Gate S2 | Deferred | Current security lens is source inspection, not a declared control assessment |
| Migration Safety | Deferred | No general migration corpus, rollback, recovery, or data-loss contract |
| Concurrency Preservation | Deferred | Static ownership, compilation, runtime tests, and semantic judgment are not separated into a profile |
| Runtime Reliability/Performance | Excluded from source-only assessment | Requires a runtime workload and measurement protocol |
| Measurement Reliability | Not satisfied | Current single-judge scoring evidence fails the certification bar |

Current user-facing wording should be:

> Refactor Quality assessment completed; no certification issued.

followed by a derived scope line naming the repository, revision, profile and
policy revision, and any coverage limitations (the exact label the
improvement spec fixes as normative text). Structural findings and semantic
scorecard entries apply only to the declared scope; the scorecard is
advisory.

Future wording, only after the profile's evidence and calibration gates pass:

> Refactor Quality profile satisfied for `<subject digest>` under `<profile id
> and policy revision>`. Within the declared source roots and applicability, no
> profile-blocking structural finding was detected and all required evidence,
> coverage, and calibration gates were satisfied. This does not establish
> product correctness, security, privacy, accessibility, reliability,
> performance, migration safety, or release readiness.

No unqualified `certified` output is valid.

## Pipeline failure taxonomy

| Stage | Representative failure | Required behavior |
| --- | --- | --- |
| Collection | Tool unavailable, artifact lost, command timeout | Retry only under declared policy; dependent claim invalid if evidence remains missing |
| Applicability | Unknown platform/control applicability, unjustified N/A | `not_evaluated`; fail closed for critical gates |
| Normalization | Malformed output, unsupported schema, lossy conversion | Preserve raw evidence; bounded retry if exogenous, otherwise invalidate |
| Identity | Collision, unstable fingerprint, stale source binding | Fail closed; do not merge or certify |
| Judgment | Judge non-adherence or substantive wrong result | Count against the mechanism; do not classify as exogenous |
| Calibration | Missing/stale calibration, excessive disagreement, corpus drift | Score advisory; certificate ineligible |
| Aggregation | Duplicate projection, incompatible constructs, weak ceiling | Omit aggregate |
| Gating | Wrong profile, stale policy, missing required evidence | `invalid`, not pass |
| Persistence | Write loss, truncation, history mismatch | Preserve denominator; exogenous invalid only when established |
| Reporting | Missing scope, ceiling, uncertainty, or invalidity | Reject certificate/report publication; retain records |

The shared failure envelope records stage, detailed cause, affected records and
claims, visibility, retryability, attempts, exclusion reason, invalidation
effect, and downstream disposition. Existing stage-local enums remain intact.

## Measurement results and next work

Current evidence establishes:

- source-backed findings reproduce better than scalar scores;
- per-dimension numeric repeatability is inadequate;
- priming can create apparent agreement without demonstrated accuracy;
- batch composition and presentation order move single-shot judgment
  measurements more than prose interventions do (2026-08-26 harness result:
  a control swung 5/5 to 2/5 on identical inputs), so calibration protocols
  must run one case per fresh context;
- the 9.5 cut is not reachable by examined blind judges;
- the panel passed its flag/restraint cases but is not recordable because its
  cost limit is post-hoc and its evidence binds an older protocol;
- trial-validity thresholds are explicitly unfitted;
- noise-floor machinery exists, but the documented A/A trial has not run
  ([`evals/README.md:292-319`](../contest-refactor/evals/README.md#L292));
- the corpus inventory can drift even while every pack oracle passes.

Required measurement sequence:

1. Adjudicate canonical conditions, projections, applicability, and claim
   ceilings with domain experts.
2. Split development/calibration and held-out validation corpora.
3. Include positive, negative, near-miss, mutant, and restraint cases across
   languages and constructs.
4. Run blinded repeat judges under exact model/prompt/tool keys — the key
   includes harness and executor model (competitor amendment 1), the grading
   prompt is bound by a frozen-hash fixture, and every sample is persisted.
5. Measure detection sensitivity and restraint false-positive rate separately
   from score reliability.
6. Measure test-retest reliability, inter-rater reliability, priming/position
   effects, SEM, confidence intervals, and model drift.
7. Run an exact-key A/A noise-floor experiment.
8. Preregister risk-derived acceptance thresholds and stopping rules — any
   significance-based rule budgets the measured ≈40-paired-trial power floor;
   a rank-criterion check on a blind-labeled corpus is the preferred
   eligibility instrument, reported as the separation the data supports; any
   agreement coefficient must be attributed to independent measurement.
9. Replicate on another corpus before enabling a certificate.
10. Treat any model, prompt, rule, tool, or corpus change as a new calibration
    key.

Certification entry additionally requires, measured on a versioned
representative corpus: applicability and critical-coverage decision accuracy
within predeclared thresholds; gate false-positive and false-negative rates
within predeclared limits; per-claim sufficient evidence with stated
ceilings; invalid and excluded trials visible in denominators; operational
cost within the declared adoption ceiling; and reproducible source, policy,
evidence, tool, model, and candidate bindings. Power floors are computed for
the actual design: a paired-design significance rule computes power on
discordant pairs (McNemar-style — the same basis as the repo's own
`required_n_for_power`), while crucible's ≈40-trial figure is the unpaired
two-proportion gate it ships (0.60→0.80, α=0.05, power 0.80).

No new semantic sample was justified during this research. Existing evidence
already rejects current certification; another unpowered sample would not
establish a valid replacement.

## Adoption and cost decision

Implement in this order:

1. Correct user-facing semantics: assessment completion, no certification or
   headline grade.
2. Extend the existing artifact with the shared envelope, projections,
   applicability, coverage, ceilings, and invalidation.
3. Reuse stable IDs, candidate binding, discovery, Evidence Chain, histories,
   validators, and trial validity.
4. Add decision roles and the shared failure envelope.
5. Require a measured, enforceable cost record for adoption.
6. Measure semantic calibration.
7. Consider a named profile certificate only if measurement clears it.

| Mechanism | Runtime/model cost | Engineering/maintenance |
| --- | --- | --- |
| Claim ceilings and projections | No required new model call | Moderate migration; low steady-state |
| Applicability/coverage gate | Mostly existing discovery and validators | Moderate |
| Decision-role validation | Negligible | Small |
| Pipeline-failure envelope | Negligible | Moderate |
| Cost records | Negligible | Small |
| Semantic calibration | High and recurring after invalidating changes | High |
| Assurance profiles | Project/profile-specific | High until bounded |

The current panel's theoretical one-profile gate ceiling is
`36 × 1.2M = 43.2M` tokens. Its staged measurement used about 6.28M tokens,
but the adapter could not stop before crossing the cap. It remains deferred.

## Aggregation decision

No aggregation survives the current evidence.

- The dimensions overlap.
- One finding can affect multiple dimensions.
- Per-dimension reliability is poor.
- A stable average already concealed severe dimension-level disagreement.
- Coverage does not establish one common evidence universe.
- The weakest load-bearing evidence caps any composite at an advisory semantic
  summary.

Keep the vector of findings, projections, coverage, gates, residuals, and
advisory scorecard entries. Omit composite severity sums, average grades,
`9.5 certified`, and general certification.

A future Refactor Quality aggregate would need independent evidence that its
dimensions form one defensible construct, justified weighting or a justified
non-compensatory rule, and stable-ID deduplication. That evidence does not
exist.

## Research conclusion

The competitor comparison confirmed rather than weakened this conclusion: the
three P0 gaps have no complete implemented answer anywhere in the 47-repo
corpus (G2 and the failure taxonomy have none at all), while the comparison
supplied executed counter-examples that make the coverage gate's mandatory
policy load-bearing and several shipped patterns that make the design smaller
(derived validity, canon-held dispositions, a slimmer cost record).

The smallest defensible improvement is not another rubric layer. It is a
validity boundary around the evidence already present:

1. applicability first;
2. one source-bound assessment model;
3. claim-bounded construct projections;
4. explicit failure and cost semantics;
5. calibration before certification;
6. aggregation last, and currently omitted.

The implementation design is specified in
[`contest-refactor/plans/assessment-validity-improvement-spec.md`](../contest-refactor/plans/assessment-validity-improvement-spec.md).
