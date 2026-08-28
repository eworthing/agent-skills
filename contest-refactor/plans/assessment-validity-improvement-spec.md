# Contest-Refactor Assessment Validity Improvement Spec

**Status:** Revised after the 47-repository competitor comparison
(2026-08-28); implementation blocked on user review and approval

**Date:** 2026-08-28

**Bound repository revision:** `784eeb5cc6b9bac7f057b86dff972f191e8b26cb`

**Research basis:**
[`docs/contest-refactor-assessment-validity-research-2026-08-28.md`](../../docs/contest-refactor-assessment-validity-research-2026-08-28.md)

**Target artifact version:** `CURRENT_REVIEW.json` schema version 6

## Decision

Extend the existing review artifact into one source-bound assessment model.
Do not add a second evidence store, a new headline grade, or a parallel trust
mechanism.

Schema version 6 supports a report-only **Refactor Quality** assessment. It
makes constructs, claim ceilings, applicability, coverage, provenance,
pipeline failures, decision roles, cost, and finding projections explicit.
Certification and aggregation remain unavailable until separate calibration
evidence supports them.

The implementation adds:

- one `assessment` object to `CURRENT_REVIEW.json`;
- one grouped assessment vocabulary canon;
- one assessment validator module;
- two validation gates;
- construct projections nested under existing canonical findings;
- assessment-policy fields in the existing candidate fingerprint.

It reuses existing source revision, skill revision, provider/model, discovery,
finding identity, residual, history, challenge, and candidate-fingerprint
mechanisms.

The 47 repositories under `refs/competitors/contest-refactor/` were triaged
and the mature relevant subset compared against the seven accepted gaps on
2026-08-28 (see the research report's Competitor analysis section for method,
evidence, and coverage). The comparison simplified this design — see
"Competitor-derived changes" below — and confirmed that no competitor
implements judge calibration, a pipeline-stage failure taxonomy, or
adoption-grade cost accounting, so those mechanisms remain novel work. The
frozen construct and claim boundaries are preserved. Implementation remains
blocked on user review of this revision.

## Competitor-derived changes

Eleven changes to the provisional design, each forced by competitor
evidence. The full records — method, executed tests, verbatim source reads,
the negative catalog, and the considered-and-rejected simplification
ledger — live in the research report's Competitor analysis section; this
table carries only the decision and its primary citation.

| # | Decision | Primary source |
| --- | --- | --- |
| 1 | `status` deleted; `validity` derived and G51-recomputed | alibaba `manifest.go` derived terminal state + construction-time partition invariant |
| 2 | Constant per-artifact policy fields deleted; report-only policy is structural (see Certification semantics) | agentlint's derived `score_scope` — constants do no work |
| 3 | Measures canon-registered with declared scales; off-scale output invalidates, never clamps | opendatahub score-range enforcement vs three shipped coercion counter-examples |
| 4 | Coverage separates "checked, none" from "never checked"; missing coverage names `errored` vs `skipped`; mandatory policy kept | opendatahub `_unavailable_reason`; aws-agent-skill-eval's executed coverage-loss-raises-grade counter-example |
| 5 | Residual disposition/lifecycle derived; empty rationale never accepts; stale residuals close for audit | archgate reason-or-no-effect suppressions; center-audit re-validation enum via `repair_revalidation_outcomes` |
| 6 | Cost record = whole-run measurements with per-quantity provenance; adoption constants declarative in canon | harness-eval `CostSource`; crucible judge-cost fold-in; opendatahub substrate cap |
| 7 | Calibration key includes harness + executor model; agreement attributed; per-design power floors; frozen-hash grading prompt; sampling deferred wholesale | skilllens ICC(1,1)=0.486 recomputed; dsh-skill-eval byte-frozen instrument |
| 8 | Failure taxonomy seeded with the four measured modes (three as v6 fixtures); an invalid result never advances a convergence counter | five infra-failure→substantive-score instances across three teams; crucible `optimize.ts` |
| 9 | Enforcement leans on registry-drift and consumer-agreement selftest families | agentlint registry consistency; opendatahub shared-case-table consumer tests |
| 10 | The handoff text itself carries the coverage ceiling | alibaba SARIF notification injection |
| 11 | Binding transitions explicit-or-invalid; `unverifiable` typed separately from `mismatch` | alibaba `resume_identity.go` |

## Objectives

1. Prevent architecture quality from being presented as general assurance.
2. Make every supported conclusion no stronger than its evidence.
3. Make missing applicability or coverage visibly invalidate affected claims.
4. Keep one canonical finding identity across all affected constructs.
5. Make decision role and pipeline failure machine-checkable for every
   artifact-recorded mechanism; make whole-run cost machine-checkable and
   adoption-cost metadata declarative in canon.
6. Preserve current workflow compatibility while removing certification-like
   user-facing language.
7. Establish a measurable entry gate for any future aggregate or certificate.

## Non-goals

- No general release-readiness judgment.
- No production correctness, security, accessibility, reliability, or
  performance certification.
- No composite score, weighted severity total, or average headline grade.
- No semantic duplicate-finding detector. Existing stable-ID and fuzzy-match
  mechanisms continue to own identity.
- No separate assessment database, certificate registry, or policy-digest
  service.
- No new model calls or analyzers merely to populate the schema.
- No `issued` certification state until a later specification is justified by
  measurement evidence.

## Normative language

`MUST`, `MUST NOT`, `SHOULD`, and `MAY` are normative. Examples are
illustrative unless a rule says otherwise.

## Design constraints

### One artifact, four projections

`CURRENT_REVIEW.json` remains the canonical per-loop artifact. Its evidence is
projected into four logical reports:

1. Refactor Quality;
2. Source Quality Audit;
3. Assurance Gates;
4. Measurement Reliability.

These names do not create four stores or four independent findings lists.

### Applicability first

Applicability and coverage are evaluated before grading, gating,
certification, or aggregation. A missing required evidence universe cannot be
hidden by a high score or high confidence.

### Claims are ceiling-bound

Every assessment and every construct projection states a supported claim and
explicitly excluded stronger claims. Confidence can describe trust in the
evidence; it cannot raise the claim ceiling.

### Existing trust bindings are extended

The existing `candidate_fingerprint` is the binding mechanism. Schema version
6 extends its payload. It does not introduce an assessment fingerprint.

### Default deny

Unrecognized schema values, missing required applicability, missing critical
coverage, an absent or malformed enclosing binding, or an unavailable
policy revision makes
the affected assessment invalid. The validator does not infer permissive
defaults.

## Canonical schema

For `schema_version >= 6`, `CURRENT_REVIEW.json` MUST contain the following
top-level `assessment` object. The surrounding top-level fields remain as
defined by schema version 5.

```jsonc
"assessment": {
  "profile": {
    "id": "refactor-quality",
    "version": 1
  },
  "provenance": {
    "model_version": null,
    "toolchain": [
      {
        "name": "python",
        "version": "3.11.9",
        "configuration_sha256": null
      }
    ],
    "rule_set_sha256": "sha256:70990e5821af2cae5e805f0de4d7d9da07425d31961014f9f30bcf51802c5065",
    "grading_prompt_sha256": null,
    "grading_configuration_sha256": null,
    "evaluation_corpus_sha256": null,
    "limitations": [
      {"fields": ["model_version"], "reason": "Hosted model build identifier was unavailable."},
      {"fields": ["toolchain[0].configuration_sha256"], "reason": "The Python invocation had no separate configuration file."},
      {"fields": ["grading_prompt_sha256", "grading_configuration_sha256", "evaluation_corpus_sha256"], "reason": "No semantic grading or evaluation corpus contributed to this example."}
    ]
  },
  "validity": "valid",
  "claim_ceiling": {
    "supported": "The evaluated source satisfies the declared Refactor Quality profile within the recorded scope and coverage.",
    "excluded": [
      "release_readiness",
      "runtime_correctness",
      "security_assurance",
      "accessibility_assurance",
      "runtime_reliability_performance"
    ]
  },
  "confidence": {
    "level": "moderate",
    "basis": "Source and validator evidence are reproducible, while semantic judgment is not calibrated.",
    "evidence_refs": ["measurement:semantic-repeatability"]
  },
  "uncertainty": [
    {
      "id": "uncertainty-semantic-judgment",
      "statement": "Semantic dimension scores vary materially between repeated judges.",
      "effect": "The scorecard remains advisory and cannot support certification.",
      "evidence_refs": ["measurement:semantic-repeatability"]
    }
  ],
  "applicability": [
    // One decision per profile-declared construct (all nine in profile v1);
    // the remaining eight are elided from this exemplar only.
    {
      "id": "app-runtime-performance",
      "construct": "runtime_reliability_performance",
      "status": "not_applicable",
      "basis": "The profile evaluates source structure and has no runtime workload.",
      "required_for": ["refactor_quality"],
      "evidence_refs": []
    }
  ],
  "coverage": [
    // One record per required coverage dimension (six in profile v1);
    // the remaining five are elided from this exemplar only.
    {
      "id": "cov-production-source-roots",
      "construct": "refactor_quality",
      "dimension": "source_roots",
      "status": "sufficient",
      "critical": true,
      "included": ["Sources/App"],
      "excluded": ["Vendor"],
      "exclusion_basis": "Third-party code is outside the refactor target.",
      "required_for": ["refactor_quality"],
      "evidence_refs": ["discovery:production_roots", "coverage_ledger:production"]
    }
  ],
  "observations": [],
  "assurance_results": [],
  "residuals": [],
  "measurements": [
    {
      "id": "semantic-repeatability",
      "measure": "score_mean_abs_gap",
      "value": 1.22,
      "unit": "points",
      "scale": [0.0, 10.0],
      "sample_size": 3,
      "attempted": 3,
      "status": "informational",
      "claim_ceiling": {
        "supported": "Repeated judges differed by a mean 1.22 points under the bound configuration.",
        "excluded": ["The scorecard is calibrated for decision use."]
      },
      "evidence_refs": ["skill_source:contest-refactor/evals/README.md#L1397-L1417"]
    }
  ],
  "pipeline_failures": [],
  "cost": {
    "duration_ms": 183420,
    "model_calls": 9,
    "tool_calls": 41,
    "input_tokens": null,
    "output_tokens": null,
    "cost_usd": null,
    "sources": {
      "duration_ms": "measured",
      "model_calls": "measured",
      "tool_calls": "measured"
    },
    "limitations": [
      {"fields": ["input_tokens", "output_tokens", "cost_usd"], "reason": "Provider token totals and priced cost were unavailable."}
    ]
  }
}
```

Revision and fingerprint bindings do not appear in the exemplar because the
envelope carries no copies of them — they live at the artifact's top level
(see Enclosing bindings below). Collections elided from the exemplar
are marked with comments — a real `validity: "valid"` artifact contains one
applicability decision per profile construct and all six required coverage
dimensions in full, and every evidence reference in it must resolve (here,
`measurement:semantic-repeatability` resolves to the record shown). The
`assessment envelope` restraint fixture, not this exemplar, is the normative
complete artifact.

### Profile

- `id` MUST be `refactor-quality` in schema version 6.
- `version` MUST be `1`.
- The policy revision IS the artifact's top-level `skill_rev` — referenced,
  not copied; the envelope carries no `policy_revision` field.

Using `skill_rev` deliberately over-invalidates when unrelated skill files
change. It is the smallest safe binding. A narrower profile digest is deferred
until over-invalidation becomes a measured operational problem.

### Enclosing bindings (no copies)

The envelope carries NO copies of enclosing bindings: `source_rev`,
`candidate_fingerprint`, `skill_rev`, `provider`, and `model` are read from
the artifact's top level, where they already live and are already validated.
There is no duplicate field to diverge — stronger than the equality check it
replaces (`validity`, by contrast, is store-and-recompute because its
derivation is the decision surface G51 must audit). Default-deny rejects an
envelope that re-declares any of them,
and a missing or malformed enclosing binding makes `validity: "valid"`
impossible.

### Provenance

`provenance` carries only assessment-specific bindings absent from the
artifact's top level. `model_version` records the exact hosted build when
exposed; it MAY be `null` only when the limitation is named.

`toolchain` is non-empty and lists every load-bearing tool by `name`, exact
`version`, and configuration digest. A missing configuration digest requires a
limitation. `rule_set_sha256` is required and binds the applicable rules and
canon. Grading prompt, grading configuration, and evaluation-corpus digests are
required when that evidence contributes to the assessment; otherwise each MAY
be null only with a named limitation. Every non-null digest uses
`sha256:<64 lowercase hexadecimal>` and hashes the exact bytes of the named
file at the bound revision.

`limitations` is structured, not prose-matched: each entry is
`{"fields": [<dotted field paths>], "reason": <non-empty string>}`, and
G51's null-with-limitation checks match on `fields`, never on wording. A
"load-bearing tool" is any tool whose output enters the artifact as evidence
(reachable via a `command:` or `discovery:` reference); its
`configuration_sha256` hashes the configuration file the invocation actually
read, or is null with a `fields`-matched limitation when none exists.

Digest inputs are defined, single-file and bundle alike. A single-file
digest hashes the exact bytes of the named file at the bound revision. A
bundle digest (`rule_set_sha256`, or any digest naming a set of files)
hashes a canonical manifest: one line per member file, formed as the
NFC-normalized UTF-8 repo-relative path with forward slashes, one tab, the
member's 64-hex byte digest, one `\n` — lines sorted bytewise by path, no
trailing content — and the digest is sha256 over the concatenated lines.
Each bundle's file MEMBERSHIP is declared in `canon/assessment-model.toml`
beside the vocabularies (the rule-set bundle enumerates the canon files and
gate registry), so membership and encoding are both canon-owned, never
inferred.

### Validity (derived)

`validity` is one of `valid`, `invalid`, or `not_evaluated`, and it is a
DERIVED value (competitor-derived change 1). The derivation rule, in order:

1. `not_evaluated` when the profile never started: no applicability
   decisions, no coverage records, AND no pipeline failures exist. A run
   that started and failed before applicability records its failures and
   derives `invalid` under rule 2 — never `not_evaluated`;
2. `invalid` when any applicability decision required by the profile is
   `unknown` or absent, any applicable critical coverage is `missing` or its
   required record is absent, the profile's policy revision (top-level
   `skill_rev`) is unavailable, any pipeline failure invalidates a
   canon-declared required logical report (profile v1 requires
   `refactor_quality`), or any required enclosing binding is absent or
   malformed, or any `target_source:`/`skill_source:` reference outside the
   closed-for-audit exemption fails verification;
3. `valid` otherwise.

The emitter stores the derived value; G51 recomputes it from the same records
and rejects the artifact on disagreement, so validity and its inputs cannot
diverge (the pattern alibaba's manifest enforces at construction). There is no
separate `status` field.

A failure BEFORE applicability has exactly one permitted representation
(fixture- and selftest-pinned): the emitter records the pipeline failure;
every canon-declared FIXED construct keeps its canon-fixed decision
(profile v1: `runtime_reliability_performance` stays `not_applicable`, and
its coverage records `not_applicable` per the applicability↔coverage
invariant); every undecided construct's decision is emitted `unknown` with
the failure record in its `evidence_refs`; and the remaining required
coverage keys are emitted `missing` with `evidence_refs` naming the failure
record. Everything then derives `invalid` under rule 2 while EVERY G52
invariant — cardinality, declared-fixed matching, and the
applicability↔coverage rule — holds simultaneously; an interaction fixture
runs full G52 against exactly this artifact.

A `not_evaluated` assessment has a defined shape, not a free pass. The canon
field tables carry a per-validity-variant requiredness column for envelope
fields; the `not_evaluated` row is: `profile`, `provenance`, `validity`,
`claim_ceiling` (run-state template), and `cost` required; `confidence` and
`uncertainty` forbidden (there is no evidence to trust or qualify); every
record collection empty. `valid` and `invalid` share the ran-variant row:
all envelope fields required, `uncertainty` non-empty. G52's
one-decision-per-construct requirement applies only to an assessment that
ran. Default-deny still applies to every field each variant does carry.

An invalid assessment MAY retain observations and measurements. It MUST NOT
support a profile-satisfied claim, and it MUST NOT advance any convergence or
plateau counter in the surrounding loop (competitor-derived change 8).

### Claim ceiling

The envelope claim ceiling is mechanical, not free prose. `supported` MUST
exactly equal the canon-declared template rendering for the assessment's
state, selected in strict precedence order: the `not_evaluated` run-state
template first; then the `invalid` run-state template; then — only when
`validity` is `valid` — the limited-coverage template (naming the limited
dimensions, rendered from the coverage records) when any applicable
critical coverage is `limited`; otherwise the profile-satisfied template.
An invalid assessment with limited coverage renders the invalid template,
never the limited one, and an invalid run structurally cannot claim
satisfaction (unverified source evidence derives `invalid`, so no separate
template exists for it). `excluded` is a non-empty,
duplicate-free list of canon claim IDENTIFIERS (display text lives in
canon), and it MUST include the profile's required excluded set.

Load-bearing records — those carrying a claim about the subject — are the
assessment envelope, observations, assurance results, measurements,
residuals, and finding projections; each carries its own claim ceiling.
Applicability and coverage records are scope declarations and carry none.
This is the record set G51/G52's claim-ceiling checks enumerate. Only the
ENVELOPE ceiling is template-bound; record-level ceilings remain emitter
prose — shape-checked and swept by the prohibited-claims scan, but
informational. G52's mechanical guarantees are scoped to the envelope
ceiling and user-facing output.

### Confidence and uncertainty

`confidence` describes trust in the recorded evidence. `level` is `low`,
`moderate`, or `high`; `basis` is non-empty; and `evidence_refs` is non-empty.

`uncertainty` is a non-empty array for any assessment that ran (validity
`valid` or `invalid`). Each record has
a unique `id`, non-empty `statement` and `effect`, and non-empty
`evidence_refs`.

Confidence and uncertainty remain separate from applicability and coverage.
Confidence MUST NOT widen `claim_ceiling.supported`, remove an excluded claim,
or turn insufficient evidence into a satisfied assurance result.

## Assessment records

All record IDs are non-empty strings unique within their collection. Every
record contains `evidence_refs`, an array of one or more resolvable references
unless its status is `not_applicable`. The reference grammar is
`<namespace>:<id>`. Artifact-local namespaces are short forms of the
record-types vocabulary — `observation` → `observation`, `assurance` →
`assurance_result`, `applicability` → `applicability_decision`, `coverage` →
`coverage_record`, `residual` → `residual`, `measurement` →
`measurement_result`, `failure` → `pipeline_failure` — and MUST resolve to a
record ID inside the assessment envelope. `finding:<stable_id>` resolves to
the artifact's top-level `findings[]` collection (inside the artifact,
outside the envelope). The remaining namespaces resolve against the state
file or artifact section that owns them:
`target_source:<path>#L<start>-L<end>`,
`skill_source:<path>#L<start>-L<end>`,
`command:<id>`, `coverage_ledger:<key>`, `challenge:<member>`,
`discovery:<key>`, `scorecard:<key>`, and `corpus:<key>` (an evaluation
corpus named in provenance). The namespace vocabulary and the
local-to-record-type mapping are declared in `canon/assessment-model.toml`
and covered by the registry-drift selftest in both directions. G51 verifies
that every reference uses a declared namespace, that artifact-local
references resolve, and that a `finding:<stable_id>` reference resolves
against the artifact's top-level `findings[]`. A `corpus:<key>` reference
resolves against the corpus registration under `evals/` whose identity
`provenance.evaluation_corpus_sha256` binds. `provenance` is a singleton
section, not a collection, and has no reference namespace.

Resolution is table-declared: for each namespace, canon declares its owning
store and its check level. Artifact-local namespaces and `finding:` are
`resolved` — G51 fails an unresolvable reference. `coverage_ledger:`,
`discovery:`, `scorecard:`, and `challenge:` resolve against the named
sections and state files of the same artifact and are `resolved`. `command:`
resolves against the artifact's recorded command evidence and is `resolved`.
`corpus:` is `resolved` as stated above. Source references carry their owner
in the namespace — `target_source:<path>#L<start>-L<end>` resolves
`source_rev` in the repository under validation (the working directory's
repository); `skill_source:<path>#L<start>-L<end>` resolves `skill_rev` in
the skill's own repository (the validator's `SKILL_ROOT`) — so resolver
routing is explicit and path text is never asked to disambiguate two
repositories holding the same relative path. Both are `bound-verified`: G51
validates the grammar, that the path is repo-relative, and existence plus
line-range bounds at the bound revision in the owning repository. This is
fail-closed: a source reference that does not verify (unresolvable revision,
missing path, out-of-range lines) derives `validity: "invalid"` — a
limitation cannot convert unavailable evidence into evidence, and there is
no narrowed-claim escape. Fixtures either use resolvable references
(`skill_source:` and artifact-local namespaces) or exercise the invalid
branch deliberately. A residual whose `lifecycle` is `closed_for_audit` is
exempt from source-reference resolution — the dangling source IS the closure
evidence, and the exemption covers the residual's `source` and its retired
`scorecard:` evidence references alike; the audit trail is the
`REVIEW_HISTORY.json` snapshot of the loop where they last resolved.

### Applicability decision

```jsonc
{
  "id": "app-runtime-performance",
  "construct": "runtime_reliability_performance",
  "status": "not_applicable",
  "basis": "The profile evaluates source structure and has no runtime workload.",
  "required_for": ["refactor_quality"],
  "evidence_refs": []
}
```

`status` is `applicable`, `not_applicable`, or `unknown`. `unknown` makes every
named `required_for` report invalid. `not_applicable` requires a non-empty
`basis` but permits empty `evidence_refs`.

Every construct named by the profile MUST have exactly one applicability
decision on an assessment that ran; a `not_evaluated` assessment has none.

### Coverage record

```jsonc
{
  "id": "cov-production-source-roots",
  "construct": "refactor_quality",
  "dimension": "source_roots",
  "status": "sufficient",
  "critical": true,
  "included": ["Sources/App"],
  "excluded": ["Vendor"],
  "exclusion_basis": "Third-party code is outside the refactor target.",
  "required_for": ["refactor_quality"],
  "evidence_refs": ["discovery:production_roots", "coverage_ledger:production"]
}
```

`status` is `sufficient`, `limited`, `missing`, or `not_applicable`.

- The required coverage set is profile-declared as explicit
  `(construct, dimension)` keys in `canon/assessment-model.toml` — six keys
  in profile v1 — with exactly one coverage record per declared key. An
  absent record for a declared key counts as `missing` in the Validity
  derivation.
- Applicable critical coverage MUST be `sufficient` for the unqualified
  profile-satisfied claim; the invalidity consequence of `missing` critical
  coverage is owned by the Validity derivation above, not restated here.
- `limited` coverage permits only a narrower claim that states the
  limitation. `limited` on applicable critical coverage does NOT make the
  assessment invalid; it bars the profile-satisfied sentence — G52 requires
  the supported claim to name the limitation and rejects the unqualified
  profile-satisfied form.
- Applicability↔coverage consistency is a named per-record G51 invariant: a
  coverage record has `status: "not_applicable"` if and only if the
  applicability decision for its `construct` is `not_applicable`.
- Exclusions MUST name their basis. An unexplained exclusion makes coverage
  `missing`.
- A `missing` record MUST reference, via `evidence_refs`, the applicability
  decision or pipeline-failure record explaining the absence, and that record
  distinguishes `errored` from `skipped` as the cause (competitor-derived
  change 4). "Checked, none found" and "never checked" are never
  representable by the same state.
- A coverage universe follows the partition rule: every enumerated item lands
  in exactly one terminal set (covered, excluded-with-basis, or
  missing-with-cause); a partition mismatch is a G51 failure.
- The universe is not emitter prose: a coverage record over an enumerable
  universe (source roots, production code, tests, callers, persistence)
  MUST reference, via `coverage_ledger:`/`discovery:` evidence, the
  coverage-ledger snapshot that supplies the enumerated universe and its
  terminal sets, and G51's partition check runs over those recorded sets. A
  dimension with no enumerable universe (`runtime_evidence` in a
  source-only profile) declares its universe directly in
  `included`/`excluded`.

Coverage dimensions are profile-declared strings; profile v1's six declared
keys span `source_roots`, `production_code`, `tests`, `persistence`,
`callers`, and `runtime_evidence`. Declaring a key does not require it to be
applicable.

The per-scanner discovery vocabulary `hotspot_scan.status`
(`ok | partial | absent | not_applicable`,
`references/output-format-json.md`) remains the scanner-grain coverage
signal; the construct-grain statuses here map onto it (`sufficient`↔`ok`,
`limited`↔`partial`, `missing`↔`absent`,
`not_applicable`↔`not_applicable`). The mapping is declared beside the
vocabularies in `canon/assessment-model.toml`, and the existing
canon/reference consistency check in `validate-repo.py` owns the
no-independent-drift rule.

### Observation

```jsonc
{
  "id": "obs-build-success",
  "constructs": ["correctness_regression"],
  "statement": "The recorded build command exited successfully.",
  "claim_ceiling": {
    "supported": "The recorded command succeeded in the bound environment.",
    "excluded": ["All supported build configurations succeed."]
  },
  "evidence_refs": ["command:build-1"]
}
```

Observations hold evidence that is not a defect: successful executions,
source-root inclusion or exclusion, tool versions, an absence established by
an executable oracle, or scorer disagreement. They MUST NOT be converted into
findings solely to fit the model. There is no `kind` field: `constructs`,
`statement`, and `evidence_refs` already identify an observation, and a
type tag returns only when a validator or renderer actually branches on it.

### Assurance result

```jsonc
{
  "id": "assurance-security-s2",
  "gate": "security-s2",
  "construct": "security_privacy",
  "status": "not_evaluated",
  "role": "delegate",
  "claim_ceiling": {
    "supported": "No security conclusion was evaluated by this profile.",
    "excluded": ["Security Gate S2 satisfied."]
  },
  "evidence_refs": ["applicability:app-security-profile"]
}
```

`status` is `satisfied`, `not_satisfied`, `not_applicable`, or
`not_evaluated`.
Schema version 6's Refactor Quality profile MUST NOT emit `satisfied` for a
security, privacy, accessibility, migration, concurrency, runtime reliability,
or runtime performance assurance gate unless a separately named executable
gate supplied the evidence. Executable gates are enumerated by ID in the
canon profile declaration, and a `satisfied` result MUST carry
`evidence_refs` resolving to that gate's recorded evidence. Profile v1
declares none, so `satisfied` is unreachable in schema version 6 — the
eligibility flag fixture pins that.

### Measurement result

```jsonc
{
  "id": "measure-reviewer-agreement",
  "measure": "weighted_kappa",
  "value": 0.71,
  "unit": "coefficient",
  "scale": [-1.0, 1.0],
  "sample_size": 80,
  "attempted": 84,
  "status": "informational",
  "claim_ceiling": {
    "supported": "Observed agreement on the bound corpus was 0.71.",
    "excluded": ["Future grading decisions are calibrated."]
  },
  "evidence_refs": ["corpus:reviewer-baseline-2026-08"]
}
```

`status` is `informational`, `meets_threshold`, `misses_threshold`, or
`invalid`. Measurement records do not grant certification eligibility unless
the profile policy explicitly names the measure and threshold.

Additional rules (competitor-derived changes 3 and 7):

- Measures are canon-registered, not emitter-declared:
  `canon/assessment-model.toml` carries a measurement registry keyed by
  `measure`, declaring its unit, inclusive scale, and any threshold. The
  record's `unit` and `scale` MUST equal the registry entry — an emitter
  cannot widen its own scale — and an unregistered `measure` is default-deny
  rejected. A value outside the registered scale makes the record `invalid`
  and emits a judgment-stage pipeline failure; it is never clamped, rounded,
  or coerced into vocabulary.
- `sample_size` counts valid trials only. `attempted` counts every trial
  including invalid ones, and each invalid trial is a pipeline-failure record
  whose `affected_record_refs` names this measurement. G51 checks the
  arithmetic: `attempted >= sample_size`, and `attempted - sample_size`
  equals the count of linked failures — so a denominator stripped during
  serialization (the persistence-stage seed fixture) fails on the persisted
  artifact itself.
- The calibration-mode repetition shape (k≥3 samples, median as `value`,
  every sample persisted with a per-sample error flag) is a requirement of
  the future calibration proposal, not of schema version 6: no v6 file ships
  calibration logic, so v6 declares no `samples` field and default-deny
  rejects one until that proposal lands (see Explicit deferrals; the
  repetition shape is recorded in the research report's measurement plan).
  Per-loop production scoring never repeats.

## Finding identity and projections

The existing top-level `findings[]` collection remains the canonical finding
collection. Each schema version 6 finding MUST add a non-empty
`construct_projections` array.

```jsonc
{
  "stable_id": "F-021",
  "title": "Authorization policy has independent owners",
  "severity": "critical",
  "construct_projections": [
    {
      "construct": "refactor_quality",
      "consequence": "Duplicate authority weakens change locality.",
      "logical_report": "refactor_quality",
      "decision_target": "refactor-quality",
      "claim_ceiling": {
        "supported": "Two policy owners were found in the evaluated source.",
        "excluded": ["A runtime authorization bypass occurred."]
      },
      "role": "gate"
    },
    {
      "construct": "security_privacy",
      "consequence": "Divergent policy ownership creates bypass risk.",
      "logical_report": "assurance_gates",
      "decision_target": "security-review",
      "claim_ceiling": {
        "supported": "The source condition warrants security review.",
        "excluded": ["A security vulnerability is proven."]
      },
      "role": "delegate"
    }
  ]
}
```

Rules:

- One evidence-backed condition keeps one `stable_id`.
- A finding MAY have multiple construct projections.
- Each `(stable_id, construct, logical_report, decision_target)` tuple MUST be
  unique.
- The `refactor_quality` projection MUST exist. A projection never restates
  the finding's severity: the active profile's severity IS the parent
  finding's `severity`, read from the finding. A projection MAY carry a
  `severity` only when a separately named profile owns that scale — none in
  schema version 6, so the field is absent.
- Each projection carries a `role` from the decision-role vocabulary,
  restricted to the subset `report`, `gate`, `delegate`, `defer` — one
  vocabulary for "what does this claim do to eligibility", not a parallel
  blocking enum. `report` exposes the consequence without eligibility
  effect; `gate` makes it non-compensatory for the profile or gate named by
  `decision_target`; `delegate` routes it to the authority named by
  `decision_target`; `defer` parks it under a canonical residual, and a
  `defer` projection MUST carry a `residual_ref` that G51 resolves.
- A projection carries no `evidence_refs`: its evidence IS the parent
  finding's Evidence Chain, inherited whole. Its claim ceiling bounds
  consequences of that same evidence, so a load-bearing projection never
  needs — and MUST NOT carry — an evidence list of its own.
- No schema version 6 calculation may count a finding's severity more than
  once across its projections.
- Separate findings remain justified only by independently remediable causes,
  distinct evidence chains, or different source identities. This semantic
  judgment is not mechanically inferred by G51.

## Canonical residuals and legacy projection

`assessment.residuals[]` becomes the canonical residual collection for schema
version 6.

```jsonc
{
  "id": "res-architecture-1",
  "source": {
    "kind": "scorecard_dimension",
    "dimension": "architecture",
    "finding_stable_id": null,
    "construct": "refactor_quality"
  },
  "disposition": "accepted",
  "lifecycle": "open",
  "accepted_by": "user",
  "rationale": "The remaining boundary is imposed by the host API.",
  "evidence_refs": ["scorecard:architecture.residual_evidence"],
  "review_trigger": "Host API boundary changes.",
  "expires": null,
  "review": null,
  "blocking_profiles": [],
  "claim_ceiling": {
    "supported": "The named source-bound residual is accepted for this profile.",
    "excluded": ["The residual is harmless in all runtime contexts."]
  }
}
```

`source.kind` is `scorecard_dimension` or `finding_projection`, and each kind
closes its own shape: `scorecard_dimension` requires a non-null `dimension`
and a null `finding_stable_id`; `finding_projection` identifies its
projection by the full unique tuple — `finding_stable_id`, `construct`,
`logical_report`, `decision_target`. `accepted_by`
is `user`, `profile`, or `null`, and MUST be null whenever the derived
`disposition` is `queued` (no stale authority rides on a reopened residual).

`review` is `null` until a re-validation has happened, otherwise
`{"outcome": <repair_revalidation_outcomes value>, "note": <string|null>}`.
The outcome vocabulary REUSES `repair_revalidation_outcomes` from
`canon/remediation-fields.toml` (`INVARIANT_HOLDS`, `INVARIANT_DRIFTED`,
`INVARIANT_REPLACED`, `CONTRACT_REJECTED`, `AUDIT_MOOT`) — the same
center-audit-derived enum this repo already adopted for repair
re-validation — rather than minting a second spelling of the same decision.
`note` is required for any outcome other than `INVARIANT_HOLDS`. `AUDIT_MOOT`
is the stale close: the source was resolved or removed and nothing is left to
resolve.

`review` holds the LATEST re-validation outcome only. Earlier outcomes are
never erased — `REVIEW_HISTORY.json` snapshots every loop's full artifact, so
the trail is the ordinary history mechanism, append-only by construction.
Re-acceptance after a reopening is therefore a defined path, not a dead end:
the emitter nulls `accepted_by` (forced by the rule above), re-binds or
repairs the source, runs a fresh re-validation, and when that lands
`INVARIANT_HOLDS` records it with a fresh rationale and authority — the
derivation below then yields `accepted` again. `review` is never reset to
null to force a state.

Two residual fields are DERIVED — stored by the emitter and recomputed by G51,
exactly as `validity` is (competitor-derived change 1, applied one level
down):

- `disposition` is `accepted` iff `rationale` is non-empty, `accepted_by` is
  non-null, and `review` is null or its outcome is `INVARIANT_HOLDS`;
  otherwise `queued`. This one definition carries archgate's
  reason-or-no-effect rule (an empty rationale can never yield `accepted`)
  and the reopening rule (any non-`INVARIANT_HOLDS` outcome forces `queued`
  until re-accepted with a fresh rationale).
- `lifecycle` is `closed_for_audit` iff (`review.outcome` is `AUDIT_MOOT`
  OR `CONTRACT_REJECTED`) AND the `source` reference no longer resolves;
  otherwise `open`. A closed-for-audit residual is retained as the audit
  trail but is exempt from `blocking_profiles` and projection blocking, and
  is reported in the residual count as closed.

Staleness (competitor-derived change 5): an `open` residual whose `source`
reference no longer resolves fails G52 — the emitter must re-bind the source
when a live target exists, or close the residual (`AUDIT_MOOT` /
`CONTRACT_REJECTED` review with note) when none does; the loop can never
ping-pong. Stale detection is the automatic review trigger.
`blocking_profiles` lists the profile ids that MUST treat this residual as
profile-blocking while its `disposition` is `queued` and its `lifecycle` is
`open`; an empty list blocks nothing beyond the projections that reference
the residual.

Existing scorecard residual fields remain in schema version 6 as a compatibility
projection. The scorecard↔canonical field mapping — which scorecard residual
field derives from which canonical field — is a table in
`canon/assessment-model.toml`, and G51 enforces one-to-one, field-by-field
equality per that table between each scorecard residual and the
`assessment.residuals[]` records with `lifecycle: "open"`; a
closed-for-audit residual's scorecard entry is retired together with its
source while the assessment record remains as the audit trail. Emitters MUST
build the assessment record first and derive the scorecard fields from it.
The same canonical-first rule governs the residual work docket
(`docs/audits/contest-refactor-residuals-<run_id>.md`, the adopt-or-falsify
intake shipped 2026-08-25): once v6 emits, docket rows derive from the
canonical records with `lifecycle: "open"` and `disposition: "accepted"`,
never from the scorecard projection. The compatibility fields may be removed
only by a later schema migration.

## Decision roles

Every proposed or executed mechanism recorded by the assessment MUST have one
role:

- `detect` — produce a condition or observation;
- `score` — assign a value within a declared scale;
- `gate` — make a non-compensatory decision;
- `report` — expose evidence without changing eligibility;
- `delegate` — route a claim to a different profile or authority;
- `defer` — postpone until evidence or cost permits evaluation;
- `exclude` — explicitly remove an inapplicable mechanism or claim.

Roles MUST NOT be inferred from prose. Role enforcement has exactly two
machine-checked surfaces:

- artifact-recorded mechanisms carry their role in the record itself —
  `assurance_results[].role`, projection `role`, and
  `pipeline_failures[].downstream_disposition` — validated by G51;
- profile-declared mechanisms (the two gates, the semantic judge, and any
  delegated profile) are enumerated by mechanism ID in the profile
  declaration in `canon/assessment-model.toml`; the mechanism table is keyed
  by those IDs and declares each one's role and a typed cost ceiling
  (`{metric, value, unit}`), checked by `validate-repo.py`.

A prose-only role claim satisfies neither surface and counts as undeclared.

## Pipeline failures

`pipeline_failures[]` gives existing stage-specific failures a common envelope.

```jsonc
{
  "id": "failure-coverage-1",
  "stage": "applicability",
  "failure_type": "required_root_unclassified",
  "visibility": "user",
  "invalidates": ["refactor_quality"],
  "affected_record_refs": ["coverage:cov-production-source-roots"],
  "downstream_disposition": "gate",
  "evidence_refs": ["coverage_ledger:unclassified"]
}
```

`stage` is one of:

- `collection`;
- `applicability`;
- `normalization`;
- `identity`;
- `judgment`;
- `calibration`;
- `aggregation`;
- `gating`;
- `persistence`;
- `reporting`.

`visibility` is `internal` or `user`. `downstream_disposition` is a decision
role. `failure_type` values are stage-scoped closed vocabularies declared in
canon, seeded from the measured failure modes; extending one is a canon
edit. `affected_record_refs` names the assessment records a failure
invalidates at record grain (using the evidence-reference grammar),
complementing `invalidates`' logical-report grain — it is how measurement
denominator arithmetic links back to its failures. Existing detailed error
enums remain authoritative within their stage; this envelope does not
replace them. Stage-scoped causes are single-grain in v6; the
run-level/item-level class split (alibaba's two-enum pattern) is deferred
until a validator or report actually consumes the distinction (see Explicit
deferrals).

A failure that invalidates a canon-declared REQUIRED logical report
(profile v1 requires `refactor_quality`) always requires
`validity: "invalid"`. v6's logical reports are always-present projections —
there is no separate omitted-report state — so a failure whose `invalidates`
names a non-required report keeps validity, and the envelope's `excluded`
list MUST then include the claim identifier the canon report→claim mapping
assigns to that report (declared in the profile declaration): deterministic,
representable, and distinguishable from "the report ran and found nothing".
An invalid result MUST NOT advance a convergence or plateau counter
(competitor-derived change 8) — concretely, a loop whose assessment is
`invalid` MUST NOT record a qualifying pass in the existing G43
convergence-pass records, and G51 cross-checks that pair.

The fixture seed set covers three of the four failure modes competitors paid
for (competitor-derived change 8): a judgment-stage off-scale value; a
persistence-stage denominator lost during serialization (the gate must still
fire on the persisted artifact); and reporting-stage consumer drift (a render
surface disagreeing with the record it renders). The fourth — an
aggregation-stage shrinking denominator presented as clean — has no live v6
code path (v6 never aggregates and defers calibration-mode sampling), so its
fixture ships with the proposal that introduces the computation.

## Cost record

Cost is required for adoption decisions, not for scoring source quality. The
artifact's cost record carries RUN MEASUREMENTS only; per-mechanism adoption
constants (`cost_ceiling`, `enforcement`, `engineering_effort`,
`maintenance_burden`) live in the canon mechanism table introduced in the
Decision roles section, checked once by `validate-repo.py` rather than
regenerated every loop (the change-2 constants-to-canon pattern applied to
cost).

Artifact record rules:

- `duration_ms`, `model_calls`, and `tool_calls` are non-negative integers
  (field names follow the repo's existing `duration_ms` / `token_usage`
  precedent; `total_tokens` is derivable and deliberately not stored).
- `input_tokens` and `output_tokens` are non-negative integers or `null`.
- `cost_usd` is a non-negative number or `null`.
- A null measurement requires a `fields`-matched structured limitation (the
  same `{"fields", "reason"}` shape provenance uses).
- `sources` maps each non-null quantity to `measured`, `provider_reported`,
  or `estimated` — per quantity, not one value for the record, because one
  run legitimately measures duration, takes tokens from the provider, and
  estimates dollars (competitor-derived change 6). Null quantities are
  omitted from `sources`. An estimated figure is always labelled estimated;
  a "measured" label that the record's own `cost.limitations` contradict is
  a G51 failure.
- The artifact's cost record measures the WHOLE RUN. v6 declares no
  per-mechanism run-cost records, so mechanism-grain ceilings are
  adoption-time declarations only (see the canon rules below); a mechanism
  needing runtime enforcement uses `substrate`.
- A judge's cost is part of the run that invoked it — evaluation overhead is
  never accounted outside the run's own record.

Canon mechanism-table rules (declarations, not runtime enforcement):

- `cost_ceiling` is a typed bound: `{metric, value, unit}` (typed so a
  future consumer CAN compare it; nothing compares it in v6).
- `enforcement` is `none`, `report`, or `substrate` — `substrate` means a
  pre-execution budget cap enforced by the provider invocation itself, and
  it is the only runtime enforcement v6 claims, because v6 declares no
  per-mechanism usage records to check a ceiling against. Mechanism-grain
  ceiling checking arrives only with a proposal that adds the consuming
  usage record.
- `engineering_effort` and `maintenance_burden` are `low`, `moderate`, or
  `high`.
- `validate-repo.py` checks the table's shape and completeness; it compares
  no run costs.

Cost alone does not make evidence invalid.

## Canonical vocabulary

Add one file, `canon/assessment-model.toml`. It contains the closed
vocabularies below and the Refactor Quality profile declaration.

| Vocabulary | Schema version 6 values |
| --- | --- |
| record types | `observation`, `finding`, `assurance_result`, `applicability_decision`, `coverage_record`, `residual`, `measurement_result`, `pipeline_failure`, `provenance` |
| decision targets (profile v1) | `refactor-quality`, `security-review` |
| evidence-reference namespaces | `observation`, `assurance`, `applicability`, `coverage`, `residual`, `measurement`, `failure` (local, mapped to record types), `finding`, `target_source`, `skill_source`, `command`, `coverage_ledger`, `challenge`, `discovery`, `scorecard`, `corpus` |
| decision roles | `detect`, `score`, `gate`, `report`, `delegate`, `defer`, `exclude` |
| constructs | `refactor_quality`, `source_quality`, `correctness_regression`, `security_privacy`, `accessibility`, `migration_data_loss`, `concurrency_preservation`, `runtime_reliability_performance`, `measurement_reliability` |
| logical reports | `refactor_quality`, `source_quality_audit`, `assurance_gates`, `measurement_reliability` |
| validity (derived) | `valid`, `invalid`, `not_evaluated` |
| applicability | `applicable`, `not_applicable`, `unknown` |
| coverage | `sufficient`, `limited`, `missing`, `not_applicable` |
| confidence | `low`, `moderate`, `high` |
| assurance result | `satisfied`, `not_satisfied`, `not_applicable`, `not_evaluated` |
| pipeline stages | `collection`, `applicability`, `normalization`, `identity`, `judgment`, `calibration`, `aggregation`, `gating`, `persistence`, `reporting` |
| pipeline failure causes | stage-scoped closed lists |
| mechanism enforcement | `none`, `report`, `substrate` |
| mechanism effort/burden | `low`, `moderate`, `high` |
| measurement status | `informational`, `meets_threshold`, `misses_threshold`, `invalid` |
| cost source (per quantity) | `measured`, `provider_reported`, `estimated` |
| residual disposition (derived) | `accepted`, `queued` |
| residual source kinds | `scorecard_dimension`, `finding_projection` |
| residual accepting authority | `user`, `profile` |
| failure visibility | `internal`, `user` |
| projection roles (named subset) | `report`, `gate`, `delegate`, `defer` |
| residual review outcome | reuses `repair_revalidation_outcomes` from `canon/remediation-fields.toml` — no second spelling is added |
| residual lifecycle (derived) | `open`, `closed_for_audit` |

The canon file also carries, beside the vocabularies: a per-record FIELD
TABLE for every object shape (required, optional, nullable, and forbidden
keys — the SSOT that G51's default-deny shape checks and the registry-drift
selftest are driven from), the namespace resolution table, the measurement
registry, the claim templates and required excluded-claim identifiers, the
scorecard↔residual field mapping, and the prohibited-claim list G52
enforces. A shape rule that exists only in this document's prose and not in
those tables is a registry-drift selftest failure.

Field tables use one normative shape — per object, one table of keys, each
declaring type, requiredness, nullability, and (for enums) the owning
vocabulary; nested objects and arrays name a sub-schema with its own table:

```toml
[records.residual.fields]
id          = { type = "string", required = true }
rationale   = { type = "string", required = true, nonempty = true }
accepted_by = { type = "enum",   vocabulary = "residual_accepting_authority", nullable = true }
expires     = { type = "string", format = "date", nullable = true }
review      = { type = "object", schema = "residual_review", nullable = true }
```

Omitted attributes default to `required = false`, `nullable = false`,
`nonempty = false`, and no `format` constraint, so independent readings of
a table agree. "Every object shape" is literal: the envelope itself,
`profile`, `provenance`, toolchain entries, limitation entries,
`claim_ceiling`, each collection record, residual `source` and `review`,
construct projections, and `cost` each have a table, and a
fixture-exercised key with no table entry fails the registry-drift
selftest.

The record-types vocabulary names the typed record kinds of the model: the
envelope's collections, plus `finding` (the artifact's top-level findings
collection, which carries the construct projections) and `provenance` (a
singleton section). The evidence-reference namespaces map onto it via the
canon-declared mapping in the Assessment records section, and G51's
per-collection dispatch is keyed on it. `decision_target` values are
profile-declared, and the registry-drift selftest checks every vocabulary —
including the namespace vocabulary — in both directions (canon value without
an enforcing branch, and validator branch accepting a value absent from
canon, both fail).

Do not add dormant `issued`, `certified`, or aggregate score values. Their
absence is intentional validator enforcement, not missing scaffolding.

The profile declaration defines:

- `id = "refactor-quality"`;
- `version = 1`;
- required construct applicability decisions (all nine canonical constructs
  in profile version 1);
- the required coverage keys — explicit `(construct, dimension)` pairs with
  criticality (six in profile v1);
- the required logical reports (profile v1: `refactor_quality`), and the
  report→claim mapping naming, for every logical report, the claim
  identifier its invalidation excludes;
- the measurement registry (`measure` → unit, inclusive scale, optional
  threshold);
- the claim templates and the required excluded-claim identifiers;
- constructs with fixed applicability: schema version 6 fixes
  `runtime_reliability_performance` to `not_applicable` with its declared
  basis, so the artifact's decision for a declared-fixed construct MUST
  match canon (G52) instead of being re-decided each loop;
- each profile-declared mechanism's decision role, cost ceiling,
  enforcement, engineering effort, and maintenance burden (the mechanism
  table checked by `validate-repo.py`);
- the exact user-facing completion label and its derived scope line.

## Certification semantics

Schema version 6 never issues certification. The policy is structural,
keyed directly on schema version 6 plus profile version 1: no issuance
fields exist anywhere in the schema (default-deny rejects them), and G52
enforces the consequences on every artifact — no prohibited affirmative
certification claim in user-facing output, and no assurance result claiming
`satisfied` outside its delegation rules. No disposition, reason enum, or
policy switch is stored anywhere: a constant nobody consumes is deleted,
not centralized (competitor-derived change 2, taken to its conclusion).

No output may display an unqualified `certified` status. Internal names such as
`panel_certification` remain compatibility identifiers; user-facing text MUST
describe what the mechanism actually established.

G52's language check is mechanical, not semantic: canon enumerates the
prohibited AFFIRMATIVE claim forms (`certified`, `certification passed`,
`ship ready`, `production safe`, `approved for release`, plus the aggregate
headline forms the Aggregation section bans), and the check matches those.
The required completion label's own "no certification issued" is a negative
disclaimer, exempt by construction — it is the label's sole permitted use of
the word. The broader "or a semantic equivalent" prose binds the EMITTER;
the enumerated list is the machine-checked surface, extended by canon edit
when a new evasion is observed.

## Aggregation semantics

Schema version 6 never aggregates: no aggregate fields exist anywhere in
the schema (default-deny rejects them), the same structural policy applies,
and G52 enforces the consequence: no headline average or composite in
user-facing output. As with certification, no disposition, reason enum, or
switch is stored.

The scorecard vector remains available as advisory evidence and as an internal
workflow input. The mean score, `9.5/10`, or another composite MUST NOT appear
as the user-facing assessment result. Where an unmeasured construct would
otherwise need a number, the value is null, never zero (skilllens's
null-never-zero convention), and the output carries a derived scope line
naming what was actually covered (agentlint's `score_scope` pattern).

## Workflow and handoff semantics

`HALT_SUCCESS` remains an internal state name in schema version 6 to avoid an
unnecessary state-machine migration. It means only that the active loop met
its internal completion conditions.

On a valid Refactor Quality run, the user-facing handoff MUST say:

> Refactor Quality assessment completed; no certification issued.

followed by a derived scope line stating the evaluated universe and any
limited or excluded coverage — generated from the coverage records by a
deterministic template declared in `output-format-markdown.md` (same
records, same string), not hand-written — so the ceiling travels in the text
a consumer actually reads, not only in the JSON (competitor-derived
change 10). G52's coupling check recomputes the rendering from the coverage
records and requires exact string equality, never semantic comparison. It MAY then report the
profile, source revision, open residuals, and advisory scorecard vector. It
MUST NOT say `certified`, `ship ready`, `production safe`, or a semantic
equivalent. The completion label and derived scope line are carried in the
existing `halt_handoff` object — the surface G35 already validates — so
G52's coupling check reads them from the artifact itself; for terminal states
with no handoff object the check is exercised by fixtures and the selftest.
The handoff text and the assessment record it renders are bound by that
G35-style coupling check plus fixtures (competitor-derived change 9): a
handoff claiming full coverage over a record showing limited coverage is a
validation failure.

Progress lines replace an average-grade headline with:

- profile ID and version;
- derived validity;
- finding counts by canonical finding, not projection;
- critical coverage status;
- residual count.

## Candidate fingerprint and invalidation

For schema version 6, extend the existing architecture payload in
`scripts/candidate_fingerprint.py` with normalized values for:

- profile ID and version (the policy revision enters as the top-level
  `skill_rev`, already fingerprint-adjacent through the existing binding —
  and the claim templates with it, so the ENVELOPE claim ceiling is
  deliberately NOT fingerprinted: its rendering varies with run outcome,
  and binding it would invalidate a challenge merely because a run failed);
- stable candidate SCOPE only: the profile's canon coverage keys and the
  deliberate exclusions with their bases. Run-result statuses (`unknown`,
  `missing`, `limited`), failure references, and per-run decisions are NOT
  fingerprinted — G51/G52 own run outcomes — so a transient collection
  failure cannot change candidate identity; the fingerprint fixture proves
  the same source yields the same fingerprint before and after a
  pre-applicability failure;
- each finding's construct projections;
- canonical residuals.

Derived validity is not fingerprinted, and not because its inputs are all
listed above (pipeline failures and enclosing-binding health are derivation
inputs and are deliberately absent): validity is execution-derived state —
what a particular run established — while the fingerprint binds candidate
identity, what the candidate IS. The report-only policy is bound through
the canon profile declaration, which the top-level `skill_rev` covers.

Do not include volatile cost measurements or free-form provenance
limitations in the fingerprint. They describe execution, not candidate
identity.

Preserve the schema version 5 fingerprint payload byte-for-byte. Version 6
normalization MUST sort set-like arrays and preserve ordered evidence where
order has meaning. Existing fingerprint tests gain one version 6 fixture
that changes each enumerated payload field and proves the fingerprint
changes.

Any change to a fingerprint-bearing field invalidates an earlier challenge and
assessment binding through the existing candidate mismatch path. Two
refinements from alibaba's resume-identity rules (competitor-derived
change 11), both scoped to EXISTING machinery — provider and model live only
at the artifact's top level (the envelope carries no copies) and are not
part of the fingerprint payload; these rules govern the cross-loop binding
check, not the fingerprint:

- a provider, model, or tool change is acceptable across a binding boundary
  only when explicitly requested. Intent evidence is the shipped four-value
  model-source table: `user_flag` is an explicit request; an `inherited` or
  `default` value changing across the boundary is configuration drift and
  invalidates. The lineage record is the ordinary `REVIEW_HISTORY.json`
  snapshot — no new fields;
- a binding that cannot be verified (missing or schema-incompatible prior
  record) is diagnosed `unverifiable`, distinct from `mismatch` — two typed
  causes on the existing candidate-mismatch diagnostic, not new artifact
  state; neither reuses prior evidence, but they are reported as different
  causes.

## Validation gates

Add only two gates to `canon/validation-gates.toml`.

### G51 — Assessment model integrity

For `schema_version >= 6`, G51 validates:

- required assessment shape and closed enums, driven by the canon field
  tables (default-deny);
- the no-copy rule: the envelope re-declaring any enclosing binding is
  rejected, and required enclosing bindings are present and well-formed;
- exact toolchain, rule-set (bundle-manifest digest),
  grading-configuration, and model-version binding, or a `fields`-matched
  structured limitation where a field is legitimately unavailable;
- derived-validity recomputation: the stored `validity` equals the value
  derived from applicability, coverage, pipeline failures, enclosing-binding
  health, policy availability, and source verification;
- coverage partition integrity, the declared `(construct, dimension)` key
  set, and missing-coverage cause references;
- per-record applicability↔coverage consistency (owned by the Coverage
  record section);
- measurement-registry equality (unit and scale), the
  invalidate-don't-clamp rule, and the
  `attempted`/`sample_size`/linked-failure arithmetic (owned by the
  Measurement result section);
- claim-ceiling shape;
- confidence and uncertainty shape and separation from claim ceilings;
- unique record IDs and evidence references per the canon resolution table
  (closed-for-audit residuals exempt from source resolution);
- the validity↔G43 convergence-pass cross-check (no counter advance on an
  invalid assessment);
- finding projection presence, uniqueness, the no-restated-severity rule,
  and the projection role subset (`defer` resolves its `residual_ref`);
- canonical residual shape, recomputation of the derived `disposition` and
  `lifecycle` values, and open-residual scorecard equality (see Canonical
  residuals);
- pipeline failure shape, stage-scoped cause membership, and invalidation
  consistency;
- cost shape, per-quantity `sources`, and null-with-structured-limitation
  rules;
- version 6 candidate-fingerprint recomputation over the payload fields
  listed in the candidate-fingerprint section (source state enters through
  the enclosing artifact's top-level bindings, not the assessment payload).

G51 does not judge whether two findings are semantically duplicates.

### G52 — Assessment eligibility

For `schema_version >= 6`, G52 validates:

- exactly one applicability decision per profile-declared construct on an
  assessment that ran (`not_evaluated` has none, per the Validity section);
- applicability decisions for declared-fixed constructs match the
  canon-declared status and basis;
- required coverage dimensions and criticality;
- invalidity on unknown applicability or missing critical coverage;
- limited-coverage claim narrowing (limited applicable critical coverage
  bars the unqualified profile-satisfied sentence);
- envelope claim-template conformance and the required excluded-claim set;
  record-level claim ceilings shape-checked;
- Refactor Quality's assurance delegation boundaries;
- residual staleness: an `open` residual whose source reference no longer
  resolves fails the gate (rule owned by the Canonical residuals section);
- handoff coupling: the user-facing completion text and derived scope line
  agree with the assessment record they render — exact recomputed-rendering
  equality for the scope line;
- absence of a user-facing aggregate or unqualified certification claim,
  matched against the canon-enumerated prohibited-claim list with the
  completion label's negative disclaimer exempt;
- pre-handoff validation evidence on completion handoffs: the validation
  entry is REQUIRED (a null entry rejects in ordinary strict mode), and the
  linked attested run's recorded digest must match the recomputed
  self-excluding digest (see Pre-handoff validation evidence below).

G52 does not certify the assessment. It proves only that the version 6 artifact
obeys the declared report-only policy.

### Pre-handoff validation evidence

No new attestation field exists — a hash and a "pass" written by the
untrusted emitter would prove nothing. The pre-handoff strict validation is
instead invoked THROUGH the existing trusted path, `attested_run.py` + G47
(the execution-evidence machinery this repo already ships):

- The wrapper's ledger entry — written by the wrapper, outside the
  artifact — records the exact validator command, its exit code, and the
  canonical payload digest of the artifact as validated, in a new literal
  ledger field `input_sha256` (`sha256:<64 hex>`). Producer and consumer
  hash IDENTICAL bytes by construction: `attested_run.py --input <path>`
  parses the artifact JSON, sets `execution_evidence.validation` to null,
  serializes with the same canonical JSON encoder G52 uses (reusing
  `candidate_fingerprint.py`'s encoding: sorted keys, UTF-8, no
  insignificant whitespace), and hashes those canonical bytes — before
  spawning the child and again after exit, treating a mismatch as degraded
  under its existing mid-run-edit rule. The command pin G52 accepts is the
  shlex-canonical PRE-LINKAGE invocation
  (`python3 -B contest-refactor/scripts/validate-artifact.py <artifact>
  --mode strict --pre-linkage`, per the wrapper's existing command-pin
  mechanism), and the `--input` operand MUST be the same normalized path as
  the child command's artifact argument — a mismatch is degraded, so the
  wrapper cannot hash artifact A while its child validates artifact B.
- The artifact links the entry through the existing `execution_evidence`
  surface under the reserved key `validation` — exactly one such entry —
  whose fields follow the existing G47 ledger-linkage schema plus one new
  field, the input-payload digest. The shipped `attested_run.py` records
  the command pin and per-stream digests but no input-payload digest, so
  that field is added to the wrapper and the ledger schema (see the change
  map). G52's handoff check verifies via the G47 linkage rules that the
  entry exists, names the strict-validation command, recorded exit code
  zero, and that its payload digest equals the recomputed self-excluding
  digest.
- Ordinary strict validation ALWAYS rejects a completion handoff whose
  validation entry is null — null is never a pass state for a completed
  artifact. The one legal null context is the producer's separately defined
  pre-linkage operation,
  `python3 -B contest-refactor/scripts/validate-artifact.py <artifact>
  --mode strict --pre-linkage`, which skips exactly one check (the
  circular linkage-presence requirement) and is the exact operation the
  ledger pins. The artifact already contains its handoff content when the
  pre-linkage run hashes it — linking the entry afterward is the single
  permitted mutation, excluded from the digest — and ordinary strict
  validation after linkage then requires the non-null entry, the digest
  match, and the pinned pre-linkage command in the ledger.
- Trust ceiling, stated plainly: this inherits G47's Tier-1 wrapper trust
  model — detectability against the register's measured forgetting failure,
  not tamper resistance — and adds no parallel trust mechanism.

Both gates are wired through the existing `validate-artifact.py` dispatcher.
New checks live in one module, `scripts/_artifact_assessment.py`, because
`_artifact_core.py` is already near the repository's module-size ceiling.
The new module has its own declared size budget: target under the 600-line
soft warning, and split into cohesive `_artifact_assessment_*` helpers
before the 800-line hard cap rather than taking a waiver.

Closure discipline (the review register's convention): G51 and G52 close
their gaps AT THE VALIDATOR LEVEL. Whether the production loop is guaranteed
to invoke `validate-artifact.py` is the register's open Tier-3 boundary
decision, out of scope here — this specification claims no live-path
enforcement beyond what the loop already runs, and its acceptance criteria
are validator-and-fixture criteria by design.

## File-level change map

### Add

- `contest-refactor/canon/assessment-model.toml`
- `contest-refactor/scripts/_artifact_assessment.py`
- `contest-refactor/scripts/_assessment_model_selftest.py`

### Modify

- `contest-refactor/SKILL.md` — preserve the structural boundary and replace
  certification-like completion wording.
- `contest-refactor/canon/validation-gates.toml` — register G51 and G52.
- `contest-refactor/scripts/_canon.py` — load the one new canon file.
- `contest-refactor/scripts/validate-artifact.py` — dispatch G51 and G52,
  and add the `--pre-linkage` flag that skips exactly the linkage-presence
  check; ordinary strict validation always requires the linked entry on a
  completion handoff.
- `contest-refactor/scripts/attested_run.py` and the G47 linkage — add the
  `--input <path>` flag and the `input_sha256` ledger field (the shipped
  wrapper records command pin and per-stream digests only), and extend
  G47's linkage validation to check it.
- `contest-refactor/scripts/candidate_fingerprint.py` — extend only the schema
  version 6 payload.
- `contest-refactor/scripts/validate-repo.py` — require canon/reference
  consistency, reject unauthorized certificate/aggregate vocabulary, and
  check the profile declaration's mechanism role and cost-ceiling entries
  (the second enforcement surface in the Decision roles section).
- `contest-refactor/references/output-format-json.md` — define version 6.
- `contest-refactor/references/output-format-migrations.md` — define v5 to v6
  default-deny migration.
- `contest-refactor/references/output-format-markdown.md` — define the four
  logical projections and completion label.
- `contest-refactor/references/output-format-state-schemas.md` — state that
  history preserves full version 6 artifacts and finding registry IDs remain
  canonical.
- `contest-refactor/references/method.md` and
  `contest-refactor/references/method-critic.md` — enforce the required research
  sequence and claim ceilings.
- `contest-refactor/references/architecture-rubric-scoring.md` — mark the
  scorecard advisory and non-certifying.
- `contest-refactor/references/validation.md` and
  `contest-refactor/references/validation-sources.md` — document G51/G52 and
  their authorities.
- `contest-refactor/references/halt-handoff.md` — distinguish internal
  `HALT_SUCCESS` from user-facing completion.
- `contest-refactor/evals/README.md` — correct the stale gold-corpus count from
  25 to the validator-observed 26.
- `docs/README.md` and `docs/contest-refactor-review-register.md` — index the
  research report and record this specification as register-owned work (the
  register owns certification, cost, and process; this work is its subject
  matter and currently sits outside its cross-reference web).

Do not create a report renderer, assessment database, certificate file, or
additional canon files in this change.

## Migration and compatibility

### Reader behavior

- Schema versions 3 through 5 continue under their existing rules.
- Version 5 artifacts are not retroactively certified or reinterpreted.
- Version 6 is opt-in until the emitter, validators, fixtures, and references
  ship together.
- A reader that does not understand version 6 must reject it, not downgrade it.

### Emitter behavior

The version 6 emitter populates the canonical assessment records first, then
derives compatibility projections. It may reuse already collected evidence;
it MUST NOT fabricate applicability, coverage, provenance, or cost values.

If a required value is unavailable, it emits `invalid` or `not_evaluated` with
the limitation. It does not fall back to version 5 merely to obtain a passing
artifact.

### State behavior

`REVIEW_HISTORY.json` stores the full version 6 snapshot as it does existing
artifacts. `findings_registry.json` retains one registry record per stable
finding. Construct projections do not create registry entries.

## Fixtures and self-tests

Add nine flag/restraint fixture pairs to the existing fixture system:

| Pair | Flag must fail | Restraint must pass |
| --- | --- | --- |
| assessment envelope | missing claim ceiling | complete bound report-only envelope |
| finding projection | duplicate projection tuple | two distinct projections under one stable finding |
| assessment eligibility | valid with missing critical coverage | limited coverage with an explicitly narrowed claim |
| completion language | unqualified certified/aggregate wording in user-facing text | required completion label plus derived scope line |
| handoff coupling | handoff claiming full coverage over a limited-coverage record | handoff scope line matching the coverage records |
| judgment invalidation | off-scale score clamped into range | off-scale score recorded invalid with a judgment-stage failure |
| evidence reference | unresolvable artifact-local reference | references resolving across collections |
| stale residual | `open` residual with a dangling source | closed-for-audit residual (`review.outcome: "AUDIT_MOOT"` with note, scorecard entry retired) |
| pre-handoff validation evidence | completion handoff with a null validation entry or a digest mismatch (ordinary strict mode) | null-entry artifact passing under `--pre-linkage`, then the linked attested run matching under ordinary strict validation |

The standalone self-test covers branches that do not need full artifact
fixtures:

- derived-validity recomputation on agreeing and disagreeing inputs;
- coverage partition mismatch against recorded ledger sets;
- the per-record applicability↔coverage iff invariant on agreeing and
  disagreeing inputs;
- absent or re-declared enclosing bindings, plus the explicit-vs-implicit
  binding transition and the unverifiable-vs-mismatch distinction;
- measurement-registry mismatch (widened scale, unregistered measure) and
  the attempted/linked-failure arithmetic;
- an unverified `target_source:`/`skill_source:` reference deriving
  `invalid` (and the closed-for-audit exemption leaving it untouched);
- the pre-applicability failure representation: fixed constructs keeping
  their canon decisions, undecided constructs `unknown`, caused `missing`
  coverage — deriving `invalid` with full G52 green (the interaction case);
- pre-handoff validation-evidence linkage: self-excluding digest
  recomputation on matching, mismatched, and null-entry inputs, verified
  through the G47 linkage rules, a mismatched `--input`/child-operand path
  pair degrading, plus one END-TO-END case running wrapper invocation
  (pre-linkage pin) → ledger entry → artifact linkage → final ordinary
  strict G52 verification;
- envelope claim-template conformance on each validity state;
- null digest and token counts with and without `fields`-matched structured
  limitations;
- residual compatibility mismatch, derived disposition/lifecycle
  recomputation on agreeing and disagreeing inputs, and staleness;
- failure invalidation mismatch and the no-counter-advance rule;
- a projection restating severity is rejected;
- mechanism-table typed-ceiling/enforcement validation and per-quantity
  `sources` consistency;
- registry drift, table-driven: G51's dispatch and shape checks are keyed on
  the canon field tables and vocabularies, and the selftest asserts the
  dispatch tables cover canon in both directions — a canon value or field
  rule without an enforcing table entry fails, and a validator table entry
  absent from canon fails (agentlint's registry-consistency pattern, without
  branch inference);
- the rule-to-test matrix: the implementation ships a matrix mapping every
  G51/G52 checklist item to at least one fixture or selftest case AND the
  diagnostic id that case must produce, so a case cannot pass on an
  unrelated failure — including `not_evaluated`, unknown applicability,
  structured-limitation matching, assurance delegation, per-quantity cost
  sources, and each namespace resolver — and an unmapped checklist item
  fails the selftest;
- grading-prompt frozen-hash binding: the routed grading prompt files hash to
  the pinned values, so prompt identity in `grading_prompt_sha256` cannot
  drift silently (dsh-skill-eval's instrument-fidelity pattern);
- version 5 fingerprint stability and version 6 fingerprint sensitivity.

The smallest required validation set is:

```bash
python3 -B contest-refactor/scripts/_assessment_model_selftest.py
python3 -B contest-refactor/scripts/validate-fixtures.py contest-refactor/evals/fixtures
python3 -B contest-refactor/scripts/validate-gold-corpus.py contest-refactor/evals/gold-corpus
python3 -B contest-refactor/scripts/validate-repo.py
python3 contest-refactor/scripts/token-budget.py --check
python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py contest-refactor
ruff check contest-refactor/scripts
ruff format --check contest-refactor/scripts
git diff --check
```

The token-budget check is not optional bookkeeping: the change map's
reference-document edits (`method.md`, `validation.md`, the output-format
set) spend loop-path token ceilings. The prose delta is measured at
implementation time, and any ceiling bump follows the house rule — dated,
sized against the new measured actual, landed in the same commit as the
prose it pays for. The same edits are agent-loaded prose, so the
implementation pass also runs the repo's writing-for-agents checks (context
pointers, co-location, no-op detection) on every touched SKILL.md and
reference file — the standing house rule — in addition to `eval-skill.py`.

## Rollout sequence

### Release 1 — Semantics and default-deny reader

Land the canon, schema references, G51/G52, fingerprint extension, fixtures,
and self-test together. Keep version 5 emission as the default until all
version 6 validation passes.

Release-1 acceptance: the full smallest-validation-set (including the
token-budget check) is green; every new flag fixture fails and every
restraint fixture passes for its specified reason; the version 5 fingerprint
stability fixture passes; version 5 emission remains the observable default.

### Release 2 — Version 6 emitter and compatibility projection

Enable version 6 emission, canonical residual-first construction, logical
report output, and new handoff language. Verify that no version 5 behavior or
fingerprint changed.

Release-2 acceptance: one real emitted version 6 artifact passes strict
validation end to end, including the handoff coupling check against its own
rendered scope line; all version 3–5 fixtures pass unchanged; the version 5
fingerprint fixture still proves byte-stability. Additionally, the emitted
artifact MUST link a matching attested validation run (protocol in the
Pre-handoff validation evidence section), proven by that fixture pair.
This does not create guaranteed invocation — that remains the register's
Tier-3 decision — but it makes an unvalidated or post-validation-mutated
completion detectable instead of silent.

### Release 3 — Measurement only

Run the existing reviewer harness against assessment claim ceilings,
applicability, projection identity, and eligibility decisions. Record results
as measurement evidence. Do not enable certification or aggregation in this
release.

Release-3 acceptance and discipline: the protocol is preregistered before
dispatch (cases, repetitions, decision rule), and runs one case per fresh
context — the 2026-08-26 harness measurement showed batch composition and
order move results more than prose does (a control swung 5/5 to 2/5 on
identical inputs) — with results recorded as measurement records carrying
`attempted` accounting. This release stays inside the 2026-08-26 stop
decision's boundary: it measures the new assessment machinery against the
existing harness and authorizes no new pack harvesting and no prose-clause
measurement.

This sequence is a release boundary, not permission to implement later stages
before the prior acceptance criteria pass.

## Future certification and aggregation entry criteria

Both remain deferred. The measured entry criteria live in the research
report's measurement plan
(`docs/contest-refactor-assessment-validity-research-2026-08-28.md`
§ Measurement results and next work). A later proposal MUST name its exact
certificate object or aggregate construct, MUST be profile-, claim-,
evidence-, and revision-bound, and may not add a general `certified` state.

## Acceptance criteria

The improvement is complete only when:

1. every schema version 6 artifact has one bound assessment envelope;
2. G51 and G52 fail closed on every specified invalid fixture;
3. all restraint fixtures and existing version 3 through 5 fixtures pass;
4. findings retain one stable identity across construct projections;
5. finding severity cannot be double-counted across projections because no
   aggregate exists and projections never restate it;
6. missing critical coverage prevents a valid completed profile claim;
7. claim ceilings are present on the assessment and all load-bearing evidence;
8. confidence and uncertainty are explicit and cannot widen a claim ceiling;
9. version 6 candidate fingerprints change when any enumerated
   fingerprint-payload field changes, while version 5 fingerprints remain
   unchanged;
10. residual compatibility fields exactly match the canonical residual
    records whose `lifecycle` is `open`;
11. every artifact-recorded mechanism carries its role field (checked by G51)
    and every profile-declared mechanism has a role and cost ceiling in the
    canon profile declaration (checked by `validate-repo.py`);
12. user-facing output contains neither a headline average nor an unqualified
    certification claim;
13. the exact completion label is emitted for a valid report-only assessment;
14. repository, fixture, gold-corpus, evaluator, Ruff, token-budget, and diff
    checks pass;
15. documentation reports the validator-observed gold-corpus count.

## Explicit deferrals

The following are omitted from this specification because current evidence
does not justify them:

- certificate issuance;
- a headline aggregate;
- a profile-specific policy digest narrower than `skill_rev`;
- a semantic finding-deduplication algorithm;
- a new report-rendering program;
- additional analyzers or model calls;
- a separate evidence or certificate store;
- the `samples` array and its calibration-mode machinery (k≥3, median,
  persisted per-sample error flags) plus the aggregation-stage seeded
  fixture — all deferred to the future calibration proposal together;
  v6 default-deny rejects a `samples` field until then, and per-loop
  repetition would triple judge cost for a scalar the design keeps advisory;
- per-failure retry metadata (`retryable`, retry counts) — returns with the
  retry policy that consumes it; stage-local retry behavior stays governed
  by the existing stage rules;
- the run-level/item-level failure-class split and its mapping table —
  returns when a validator or report consumes the distinction;
- factor-level variance attribution (ANOVA-style analysis, per
  opendatahub's module) — delegate to a separate opt-in if variance
  attribution across factors is ever needed.

Add any one of them only when a measured failure of this smaller design makes
it necessary.
