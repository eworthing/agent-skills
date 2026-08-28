# Research Prompt — Contest-Refactor Assessment Validity

## Objective

Research whether `contest-refactor` can support valid, calibrated,
profile-specific assessment claims without conflating structural refactoring
quality with broader assurance or release readiness. Verify the current state
first, then recommend the smallest evidence model, profiles, gates, validators,
and measurements that the evidence justifies.

This is a research task. Do not modify repository files or implement the
recommendations. Produce an evidence-backed research report and a bounded
adoption recommendation.

## Scope boundary

The current `contest-refactor` skill evaluates architecture: ownership, seams,
depth, simplicity, and test strategy. Its existing result is structural, not a
ship-readiness certificate. Preserve that boundary unless a separately named
assessment profile carries sufficient evidence for a separately named claim.

Treat these as distinct constructs until evidence establishes a valid
relationship:

- refactoring quality;
- source quality;
- correctness and regression resistance;
- security and privacy;
- accessibility;
- migration and data-loss safety;
- concurrency preservation;
- runtime reliability and performance;
- measurement reliability.

Do not infer one construct from another. Do not treat a green build, passing
tests, static analysis, a semantic score, or an adversarial challenge as broader
proof than its evidence permits.

## Research ground truth

Bind the research to the exact repository state examined. Record:

- repository and source revision;
- dirty-worktree state and relevant diff, if any;
- `contest-refactor` candidate fingerprint when the evaluated artifact has one;
- assessment profile or grading configuration;
- toolchain, analyzer, validator, and rule-set versions;
- model and grading-prompt versions for semantic judgments;
- evaluation corpus, exclusions, and invalid trials.

Inspect the live skill, its routed references, canon files, validators,
self-tests, fixtures, evaluation documentation, raw evaluation records, and
relevant plans. Current source outranks older plans or reports. Treat a claimed
absence as established only when an executable oracle or exhaustive bounded
inventory supports it.

Use primary sources for external research where available. Separate:

- verified current-state fact;
- inference;
- external research result;
- proposed design;
- unresolved uncertainty.

## Priority gaps to verify

Do not assume these gaps are present merely because they are listed. Verify,
refine, split, merge, downgrade, or reject each one against current source and
current evaluation evidence.

| Priority | Gap |
|---|---|
| P0 | Refactoring quality and assurance quality can be conflated. |
| P0 | Semantic grading is insufficiently calibrated for certification-bearing decisions. |
| P0 | Applicability, scope, or coverage can omit relevant evidence without making the assessment invalidity sufficiently visible. |
| P1 | The residual model is architecture-specific and partly manual. |
| P1 | Proposed mechanisms lack an explicit detect/score/gate/report/delegate/defer/exclude disposition. |
| P1 | Pipeline failures lack a shared taxonomy. |
| P2 | Evaluation cost is not a required adoption field. |

Coverage belongs at P0. A perfectly calibrated grader evaluating the wrong
evidence universe produces a precisely measured invalid conclusion.

## Gap acceptance record

Create one record for every retained gap. A gap is accepted only when its record
is evidence-backed and complete:

1. **Gap and construct** — the verified problem and the construct whose validity
   is at risk.
2. **Current-state evidence** — exact source, evaluation, or executable-oracle
   evidence establishing the gap at the bound revision.
3. **Applicability and scope** — when the gap applies, the evaluated universe,
   and explicit exclusions.
4. **Coverage requirement** — the dimensions of coverage needed and the
   conditions that make missing coverage assessment-invalidating.
5. **Existing mechanism** — current `contest-refactor` machinery that can be
   reused, narrowed, or generalized.
6. **Proposed mechanism** — the smallest mechanism needed beyond current
   behavior.
7. **Decision role** — exactly one primary role from `detect`, `score`, `gate`,
   `report`, `delegate`, `defer`, or `exclude`; name secondary roles only when
   necessary.
8. **Required evidence** — evidence needed to operate and validate the proposed
   mechanism, including an executable oracle where absence is claimed.
9. **Calibration and validity plan** — how reliability, discrimination,
   restraint, uncertainty, and threshold validity will be measured.
10. **Pipeline failure handling** — the failure stage, visibility, invalidation
    behavior, retry or exclusion rule, and downstream effect.
11. **Evaluation and adoption cost** — expected runtime, model/tool calls,
    engineering effort, maintenance burden, and the cost ceiling for adoption.
12. **Residual risk and invalidation** — known residuals, expiry or re-evaluation
    triggers, and changes that invalidate prior evidence.
13. **Claim ceiling** — the strongest conclusion the proposed mechanism may
    support, plus the stronger conclusions it explicitly cannot establish.

Reject or defer a mechanism whose evidence, validity, or adoption-cost record is
insufficient. Do not fill missing fields with aspirational prose.

## Preferred design direction

The preferred design direction is profile-based grading with:

- non-compensatory, profile-applicable gates for critical correctness,
  security, privacy, data-loss, and accessibility failures;
- calibrated bands for architecture, maintainability, regression resistance,
  failure-handling quality, performance discipline, and platform fit;
- runtime reliability and performance claims only when separate, sufficient
  runtime evidence supports them;
- separate applicability, coverage, confidence, and uncertainty;
- evidence bound to the exact source revision, candidate fingerprint,
  toolchain, rule set, grading configuration, and model version.

Treat this as a direction to test, not a conclusion to preserve. Prefer omission
over a profile, dimension, score, or gate that cannot be made valid at reasonable
cost.

## Certification semantics

Certification is always profile-specific, claim-specific, evidence-bound, and
revision-bound.

“Certified” means only that a named assessment profile satisfied its declared
gates, coverage requirements, evidence thresholds, and calibration requirements
at the bound source revision.

Every certification must name its object, for example:

- Refactor Quality profile satisfied;
- Security Gate S2 satisfied;
- Migration Safety profile satisfied;
- Concurrency Preservation profile satisfied.

Never emit or display an unqualified “certified” status.

Certification never implies general release readiness, product correctness,
security, accessibility, reliability, performance, or any assurance claim not
explicitly named by the certificate.

A change to source, assessment profile, critical evidence, tool configuration,
or candidate-fingerprint-bearing fields invalidates the prior certification
unless the profile explicitly defines a narrower validity rule.

## Canonical assessment evidence model

Use one canonical, source-bound assessment evidence model. Do not design it
solely around defects or findings.

The model should support a shared envelope and typed records including:

- observation;
- finding;
- assurance_result;
- applicability_decision;
- residual;
- measurement_result;
- provenance.

Examples of evidence that must fit without being disguised as findings include:

- successful test or build execution;
- source-root inclusion or exclusion;
- analyzer and tool versions;
- benchmark calibration results;
- an absence established by an executable oracle;
- a not-applicable decision;
- an accepted residual;
- scorer disagreement;
- an invalid or excluded trial.

The four logical reports—Refactor Quality, Source Quality Audit, Assurance
Gates, and Measurement Reliability—are projections of this canonical model,
not separate sources of truth.

## Claim-strength discipline

Every conclusion must distinguish:

- observation;
- supported claim;
- unsupported stronger claims.

Example:

Observation:
Static ownership appears coherent in the evaluated source.

Supported claim:
No conflicting owner was found within the evaluated source and scope.

Unsupported stronger claims:
- no race exists;
- runtime ordering is correct;
- production execution is safe.

A report, score, gate, or certificate must not exceed the weakest claim ceiling
of its load-bearing evidence.

Confidence cannot raise a claim ceiling. High confidence in static evidence does
not convert that evidence into runtime proof.

## Finding identity and construct projection

One underlying evidence-backed condition remains one canonical finding even
when it affects multiple constructs or logical reports.

Each canonical finding has one stable identity and may carry multiple
construct projections. A projection may describe:

- the affected construct;
- the consequence within that construct;
- the applicable report or gate;
- construct-specific severity;
- construct-specific claim ceiling;
- construct-specific residual or blocking effect.

Example:

Canonical condition:
Authorization policy has two independent owners that have drifted.

Possible projections:
- architecture: duplicate authority and weak change locality;
- correctness: inconsistent authorization outcomes;
- security: policy-boundary bypass risk.

Do not create three findings solely because the condition has three
consequences. Do not add the finding’s severity three times to a composite
calculation.

Separate findings are justified only when they have independently remediable
causes, distinct evidence chains, or different source identities.

## Required research sequence

Do not begin by designing a final rubric, adding dimensions, or selecting
scoring formulas.

Proceed in this order:

1. Verify every claimed contest-refactor gap against current source and current
   evaluation evidence.
2. Define the constructs and their boundaries.
3. Define claim ceilings.
4. Define applicability, scope, exclusions, and multidimensional coverage.
5. Inventory existing contest-refactor mechanisms that can be reused or
   generalized.
6. Identify claims the current evidence cannot support.
7. Define the additional evidence needed for each candidate claim.
8. Assign each proposed mechanism a decision role:
   detect, score, gate, report, delegate, defer, or exclude.
9. Decompose failures by pipeline stage.
10. Design the smallest necessary dimensions, profiles, validators, or
    benchmarks.
11. Measure and calibrate semantic judgment.
12. Only then determine whether aggregation, a headline grade, or any
    certification remains justified.

If earlier steps show that a proposed score or certification cannot be made
valid at reasonable cost, recommend omitting it.

## Research questions

Answer these in sequence, carrying unresolved uncertainty forward rather than
silently closing it:

1. Which listed gaps are present at the bound revision, which are not, and what
   exact evidence decides each disposition?
2. What are the operational definitions and boundaries of Refactor Quality,
   Source Quality Audit, Assurance Gates, and Measurement Reliability?
3. What is the maximum claim each current evidence type can support, and which
   existing scores, gates, reports, or terminal states exceed that ceiling?
4. How should applicability, source scope, exclusions, platform/language
   variance, test-surface coverage, analyzer coverage, runtime-path coverage,
   and evaluation-corpus coverage be represented? Which omissions invalidate a
   result rather than merely lower confidence?
5. Which current findings, residuals, scorecards, gates, validators, candidate
   bindings, histories, and evaluation records can be reused or generalized?
6. What minimum canonical envelope and typed records preserve provenance,
   identity, applicability, coverage, uncertainty, and invalidation without
   creating parallel sources of truth?
7. How should one canonical finding project into multiple constructs without
   identity drift, remediation drift, or double counting?
8. Which mechanisms should detect, score, gate, report, delegate, defer, or
   exclude, and why is that role the least powerful role that satisfies the
   need?
9. What shared pipeline-stage taxonomy makes collection, applicability,
   normalization, identity, judgment, calibration, aggregation, gating,
   persistence, and reporting failures visible and correctly fail-open or
   fail-closed?
10. What calibration design measures semantic-judge discrimination, restraint,
    repeatability, inter-rater disagreement, model/version drift, threshold
    uncertainty, and invalid trials without reusing evaluation data as proof of
    general validity?
11. Which assessment profiles and non-compensatory gates remain justified after
    applicability, coverage, evidence thresholds, calibration, and claim
    ceilings are applied?
12. What does each retained mechanism cost to evaluate, adopt, operate, and
    maintain, and when does that cost require delegation, deferral, exclusion,
    or omission?
13. Does any aggregation or headline grade survive the preceding analysis? If
    so, what construct does it measure, how is double counting prevented, and
    what named claim—no stronger—does it support?

## Required report

Produce one source-bound report with these sections:

1. **Executive decision** — what should remain, change, be measured, be deferred,
   or be omitted.
2. **Revision and provenance manifest** — every binding needed to reproduce the
   assessment.
3. **Verified gap register** — one complete 13-field acceptance record per
   retained gap; rejected gaps remain listed with rejection evidence.
4. **Construct map** — operational definitions, boundaries, overlaps, and
   prohibited inferences.
5. **Claim-evidence matrix** — observations, supported claims, unsupported
   stronger claims, claim ceilings, applicability, coverage, confidence, and
   uncertainty.
6. **Canonical evidence model** — the minimum shared envelope, typed records,
   canonical identity rule, projection rule, and invalidation semantics.
7. **Logical report projections** — Refactor Quality, Source Quality Audit,
   Assurance Gates, and Measurement Reliability derived from the canonical
   model.
8. **Profile and certification proposal** — named profiles, gates, coverage and
   evidence thresholds, calibration requirements, validity rules, and exact
   certificate wording; omit profiles that do not clear the evidence bar.
9. **Pipeline failure taxonomy** — stage, failure type, detection, visibility,
   retry/exclusion behavior, invalidation effect, and downstream disposition.
10. **Measurement plan and results** — existing evidence, additional benchmarks
    or experiments, calibration results where measurable now, stopping rules,
    and unresolved limitations.
11. **Adoption and cost decision** — smallest viable change set, reuse map,
    sequencing, evaluation cost, maintenance cost, and explicit deferrals.
12. **Aggregation decision** — justified named aggregate and claim ceiling, or a
    recommendation to omit aggregation, headline grading, and certification.

The four logical reports are projections in the research design and in any
recommended implementation. Do not author four independent evidence stores.

## Completion criteria

The research is complete only when:

- every listed gap has a verified disposition;
- every retained gap has all 13 acceptance fields;
- every construct and claim has an explicit boundary and claim ceiling;
- applicability, scope, exclusions, and multidimensional coverage are visible;
- every proposed mechanism has a decision role and adoption cost;
- every load-bearing conclusion is bound to reproducible evidence;
- canonical finding identity prevents construct-driven duplication and
  composite double counting;
- pipeline failures have explicit invalidation and downstream behavior;
- semantic grading claims include measured calibration and limitations;
- every certificate is named, profile-specific, claim-specific,
  evidence-bound, and revision-bound;
- no report, score, gate, or certificate exceeds the weakest load-bearing
  claim ceiling;
- aggregation is the last decision and is omitted when validity cannot be
  established at reasonable cost.

State unresolved gaps plainly. A smaller defensible assessment is a better
result than a comprehensive-looking invalid one.
