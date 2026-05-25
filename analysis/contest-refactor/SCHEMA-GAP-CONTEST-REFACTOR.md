# Finding Schema Gap Analysis — contest-refactor vs P0 competitors

Compares `contest-refactor`'s **finding-level** schema (`CURRENT_REVIEW.json.findings[]` per `references/output-format-json.md`) against three P0 competitors verified by source inspection. Two caution flags for this comparison:

1. Some adjacent strengths in contest-refactor live outside `findings[]` (for example `findings_registry.json` occurrence statuses and scorecard fields like `residual_blocking_10`). Those are worth calling out, but they are not finding-local fields.
2. The checked Anthropic and CodeRabbit sources document workflows and thresholds more clearly than they document field names. Where the source proves a behavior but not a concrete JSON key, this doc now names the behavior, not an invented field.

Compared repos:

- **CodeRabbit Skills** (`refs/competitors/coderabbit-skills/`) — GitHub-thread native
- **Anthropic code-review plugin** (`refs/competitors/anthropic-claude-code/plugins/code-review/`) — parallel agents + confidence scoring
- **Trail of Bits** (`refs/competitors/trailofbits-skills/plugins/{fp-check,c-review,static-analysis}/`) — layered worker→judge pipeline + Stop-hook gates + SARIF

## Gap matrix

Legend: **✓** = present, **partial** = exists in a weaker form, **—** = absent.

| Mechanism | contest-refactor | CodeRabbit | Anthropic | Trail of Bits |
|---|:--:|:--:|:--:|:--:|
| Stable cross-loop ID | ✓ `stable_id "F-NNN"` | partial (`databaseId` is GitHub thread metadata, not a contest-refactor-style finding ID) | — | ✓ `id "<PREFIX>-NNN"` |
| Cross-loop status enum | partial (lives in `findings_registry.json`, not `findings[]`) | partial (`isResolved\|isOutdated`) | — | partial (`fp_verdict`) |
| Severity enum (4-tier) | ✓ contest-themed | partial (native review grouping is `critical/warning/info`; autofix remaps GitHub severities to CRITICAL/HIGH/MEDIUM/LOW) | partial (high-signal issue filtering, no checked enum schema) | ✓ CRITICAL/HIGH/MED/LOW |
| **Explicit reviewer confidence** | **—** | — | ✓ documented 0-100 confidence with ≥80 threshold | ✓ `confidence: High\|Medium\|Low` (worker) |
| **Validation pass with rejection authority** | partial (`validate-artifact.py` is structural, not semantic) | — | ✓ per-issue validator subagents | partial (Stop/SubagentStop completeness gates) |
| **Explicit severity / validation rationale field** | **—** | — | partial (validation step documented; concrete field names unverified in checked source) | ✓ `severity_rationale`, `fp_rationale` |
| **Critic/worker provenance** | **—** | — | implicit (subagent dispatch) | ✓ `worker` field |
| **Dedup metadata** (when multiple critics flag same issue) | **—** | — | implicit ("post one comment per unique issue") | ✓ `merged_into`, `also_known_as`, `locations[]` |
| Governance citation | ✓ `adr_conflicts[]` + `adr_reopen_justification` | — | partial (CLAUDE.md scoping and violation validation documented; concrete field names unverified) | partial (CWE optional) |
| Evidence chain | ✓ Claim → Source → Consequence → Remedy | partial (free-text body) | partial (issue description + reason flagged, no checked structured snippet field) | ✓ Source → Sink → Validation + reachability + math proof + PoC |
| Domain test taxonomy | ✓ `test_failed` (Deletion test \| Two-adapter \| Shallow module \| Interface-as-test-surface \| Replace-don't-layer) | — | partial (`reason it was flagged`, e.g. CLAUDE.md adherence / bug) | ✓ `bug_class` enum |
| Dependency classification | ✓ `dependency_category` (in-process \| local-sub \| remote-owned \| true-external) | — | — | — |
| Leverage/locality scoring | ✓ `leverage_impact` + `locality_impact` | — | — | — |
| Blast radius | ✓ `blast_radius{change[], avoid[]}` | — | — | ✓ reachability trace |
| Residual-blocking-10 (per scorecard dim) | partial (lives in scorecard, not `findings[]`) | — | — | — |
| Forced-completion gate (hook layer) | partial (`validate-artifact.py` G1–G29, no Stop hook) | — | — | ✓ Stop+SubagentStop hooks, 6 gates |
| SARIF interop | — | — | — | ✓ ingests + emits SARIF 2.1.0 |
| Cross-codebase fingerprint | partial (`scripts/_fingerprint.py`) | — | — | ✓ `partialFingerprints` (path-independent) |

## What contest-refactor already has that the sampled competitors do not all share

1. **ICA-grounded `test_failed` enum** — Deletion test, Two-adapter rule, Shallow module, Interface-as-test-surface, Replace-don't-layer. None of the sampled competitors exposes an equivalent architecture-test taxonomy at finding granularity.
2. **`leverage_impact` + `locality_impact` per finding** — stronger than the sampled competitors' issue descriptions because the structural payoff is mandatory, not implied.
3. **`dependency_category` 4-tier** (in-process / local-substitutable / remote-owned / true-external) — absent in the sampled competitor schemas.
4. **`adr_conflicts[]` + `adr_reopen_justification`** — stronger local-rule traceability than the sampled competitors' checked finding formats.
5. **Adjacent artifact strength:** contest-refactor also carries richer cross-loop state outside `findings[]` (registry occurrence statuses; scorecard `residual_blocking_10`), but those should not be confused with finding-local schema wins.

## P0 GAPS — what to import

### Gap 1: `confidence` field (Anthropic + Trail of Bits have explicit reviewer confidence; contest-refactor doesn't)

The checked Anthropic and Trail of Bits sources both expose explicit confidence in the review flow. CodeRabbit does **not** expose an equivalent field in the checked skill sources, so the right claim here is narrower than the first draft. Contest-refactor still lacks any explicit confidence field, which means emitted findings cannot be triaged as "confirmed" vs "suspect but worth watching" without adding ad hoc prose.

**Recommendation:** add `confidence: enum("high"|"medium")` to the finding schema. Default `high` for emitted findings; allow `medium` for things the Critic suspects but can't prove from evidence. Tie into `severity` orthogonally — a `Likely disqualifier` of `medium` confidence is a different artifact than one of `high`.

### Gap 2: `severity_rationale` (Trail of Bits proves the field; Anthropic proves the need for explicit validation)

Contest-refactor has `why_weakens_submission` (Consequence) but no field for *why this severity*. Trail of Bits proves the concrete field pattern. Anthropic's checked source proves a separate validation step and confidence threshold, which is enough to justify severity/validation audit trail even though the exact field names are not exposed in the checked plugin files.

**Recommendation:** add `severity_rationale: string` (required when severity ≥ `Serious deduction`). One sentence: which severity anchor matches, and what concrete evidence in the finding's `evidence[]` anchors it.

### Gap 3: Critic provenance (ToB has `worker`; contest-refactor doesn't)

Contest-refactor describes Critic Phase as a single role today. If the loop ever runs multiple Critic subagents (e.g., architecture-critic + concurrency-critic + tests-critic — parallel critic mode is already listed in `doc § 6 P1`), there's no provenance field to track which critic flagged which finding. ToB stamps every finding with `worker` and then runs a dedup-judge.

**Recommendation:** add `critic_source: string` (optional today, required when Critic Phase fans out). Even with one critic, recording `"critic_phase"` keeps the schema forward-compatible.

### Gap 4: Dedup metadata for parallel critics (ToB has `merged_into`/`also_known_as`/`locations[]`)

If P1 parallel critics land, deduplication becomes mandatory. ToB's three-field pattern is the cleanest: primary findings carry `also_known_as: ["BOF-002", "BOF-004"]` and `locations: ["src/a.c:10", "src/b.c:42"]`; absorbed duplicates carry `merged_into: "BOF-001"`.

**Recommendation:** reserve these field names now (optional) so the schema doesn't need a breaking change when parallel-critic mode ships.

### Gap 5 (optional, harder): validator subagent for semantic finding rejection

The real missing layer here is not "make Python stricter." It is "add a semantic validator that can reject or downgrade a finding even when the artifact is structurally well-formed." Anthropic's per-issue validator subagents are the clearest import pattern; Trail of Bits shows a separate completeness-gating layer, but its hooks are aimed at workflow completeness, not contest-refactor-style finding semantics.

**Recommendation:** if contest-refactor adopts a validator subagent, keep responsibilities split cleanly:

- `validate-artifact.py` stays deterministic and structural
- validator subagent handles "does this evidence actually support this claim at this severity?"
- `confidence` + `severity_rationale` become the handoff surface between Critic and validator

### Gap 6 (defer): SARIF interop (ToB only)

SARIF is useful when contest-refactor wants to plug into CI pipelines or ingest external static-analysis findings (CodeQL, Semgrep). Not core today; mention as Possible Future Lens.

### Gap 7 (P0): Positive-finding `[GOOD]` emission rule

Source-verified in `refs/competitors/grill-for-claude/codex/skills/grill-core/SKILL.md:18-26, 59-67`. xiaolai's grill skill ships a 5-tier severity enum `[CRITICAL] [HIGH] [MEDIUM] [LOW] [GOOD]` where `[GOOD]` is the positive-finding value emitted when a scan area was checked and is sound.

**Why this matters**: contest-refactor's Critic emits findings on weakness only. Silence on a topic = ambiguous (was it checked and clean, or skipped?). This pressures Critic to manufacture findings (Q3 fake-clean reward warns against this; existing `strengths[]` field is the partial mitigation but isn't per-area). grill's pattern forces Critic to emit `[GOOD]` evidence when nothing's wrong, breaking the pressure.

**Recommendation**: extend contest-refactor's existing `strengths[]` field discipline with per-area-checked semantics, OR add a new top-level `audited_areas[]` array recording what the Critic checked and didn't find findings against.

**Schema sketch** (additive):

```jsonc
{
  "audited_areas": [                         // NEW — what the Critic explicitly checked
    {
      "area": "concurrency",                 // string; matches scorecard dimension OR lens-registry lens id
      "audited": true,
      "verdict": "good",                     // enum: good | concerns_only_in_findings | not_applicable
      "evidence": "Reviewed AudioSessionConfigurator and SpotifyAdapter continuation patterns; all delegate writes per-attempt-token gated. SpotifyAdapter.swift:88-145, AudioSessionConfigurator.swift:34-90."
    },
    {
      "area": "security_secrets",
      "audited": true,
      "verdict": "not_applicable",
      "evidence": "No hardcoded secret patterns found via Layer 1 scan; no auth-touching paths in this refactor scope."
    },
    {
      "area": "domain_modeling",
      "audited": true,
      "verdict": "concerns_only_in_findings",   // findings cover this area; no [GOOD] needed
      "evidence": "See F2, F4."
    }
  ]
}
```

**Validation gate G41** (new): When any scorecard dimension is scored `>= 9`, `audited_areas[]` MUST contain an entry for that dimension with `verdict ∈ {good, concerns_only_in_findings}`. Skipped dimensions at high scores = G41 failure (forces Critic to substantiate the score with explicit audit evidence, not silence).

This pairs with TWO-LAYER-DETECTION-GAP's optional `excluded_candidates[]` field: `audited_areas[]` records what WAS checked at the area level; `excluded_candidates[]` records what was checked at the candidate level. Both close the silence-on-success ambiguity.

`strengths[]` field can stay (top-level, narrative); `audited_areas[]` is the per-area-machine-readable analog.

## Recommended schema diff

Minimal additions to `CURRENT_REVIEW.json.findings[]` (additive, no breaking change, can ship as schema_version 4):

```jsonc
{
  // ... existing fields unchanged ...

  // NEW (Gap 1) — required on every finding
  "confidence": "high",                          // enum: high | medium

  // NEW (Gap 2) — required when severity in {Serious deduction, Likely disqualifier}
  "severity_rationale": "Anchored by Two-adapter rule failure (evidence[0]); one Adapter would suffice without the Seam.",

  // NEW (Gap 3) — optional today, required when parallel critics ship
  "critic_source": "critic_phase",               // string; "critic_phase" today

  // NEW (Gap 4) — optional, reserved for parallel-critic dedup
  "merged_into": null,                           // string | null
  "also_known_as": [],                           // array of stable_ids
  "locations": []                                // array of "path:line" strings
}
```

Top-level CURRENT_REVIEW.json additions for Gap 7 (audited_areas) shown in Gap 7 section above.

Update `canon/` accordingly:

- `canon/confidence-levels.toml` — new file: `confidence_levels = ["high", "medium"]`
- `canon/area-verdicts.toml` — new file (Gap 7): `area_verdicts = ["good", "concerns_only_in_findings", "not_applicable"]`
- `canon/severity-anchors.toml` — unchanged
- `canon/finding-statuses.toml` — unchanged

Semantic rejection/downgrade logic does **not** belong in `validate-artifact.py`; it belongs in the future validator subagent discussed above.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Numeric `confidence_score 0-100` (Anthropic) | False precision. Two-bucket `high\|medium` matches contest-refactor's discrete severity anchors and avoids 80-vs-79 bikeshedding. |
| CodeRabbit's GitHub-thread native schema | Couples findings to PR-review-comment lifecycle; contest-refactor is loop-driven, not PR-driven. |
| ToB's `attack_vector` / `exploitability` / `bug_class` | Security-specific. Contest-refactor's `test_failed` enum is the architecture analogue. |
| ToB's mandatory PoC + math proof | Bug-finding analogue; not portable to architecture refactor. |
| SARIF emit (ToB) | Useful only if contest-refactor grows a CI-integration use case. Defer. |
| Anthropic's `code_snippet` field embedded in finding | Contest-refactor already requires `evidence[]` with `path:line`; embedding snippet bloats the artifact for marginal value. |

## Adoption order

1. **Gap 2 (severity_rationale)** — smallest finding-local audit-trail win, no breaking change.
2. **Gap 1 (confidence)** — small change, unlocks validator-subagent output without numeric pseudo-precision.
3. **Gap 7 (positive-finding `audited_areas[]`)** — directly counters Critic-pressure-to-manufacture-findings (Q3 fake-clean reward). One new top-level field + G41 gate. Pairs with grill-for-claude's source-verified `[GOOD]` pattern.
4. **Gap 5 (validator subagent)** — semantic rejection belongs here, not in Python structural validation.
5. **Gap 3 + Gap 4 (critic_source + dedup metadata)** — reserve when parallel critics move from P1 idea to actual design work.
6. **Gap 6 (SARIF)** — defer until a CI-integration consumer exists.
