# Two-Layer Detection Gap — contest-refactor vs levnik audit-suite

> **CURRENT-STATE (2026-06-28):** PARTIALLY-COVERED — the Evidence Chain already mandates grep→source-verify in prose (`method.md:18-30,36,71`); residual = a named mandatory procedure + a gate proving Layer-2 verification occurred + optional excluded-candidate trail. See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.
> Gate numbers **G37+** cited below are UNBUILT proposals — G33–G36 have since SHIPPED (2026-06-29); the live catalog (`contest-refactor/canon/validation-gates.toml`) now stops at **G36**. *(Re-verified 2026-06-30.)*

Source: `refs/competitors/levnik-skills/shared/references/audit_worker_core_contract.md` (verbatim quote in LEVNIK-AUDIT-SUITE-GAP).

## Baseline: contest-refactor today

Critic's Method (`references/method.md`) requires Evidence Chain (Claim → Source → Consequence → Remedy) but doesn't formalize a detection workflow. Critic is free to:

- Grep candidate patterns + emit findings without context verification (false-positive risk)
- Read code in any order
- Verify candidates after emitting them (rare)

G3 (Evidence chain) checks fields are populated; doesn't check Layer 2 verification happened. Critic discipline is enforced via prose ("EVERY finding must follow Claim → Source → Consequence → Remedy") not via process step.

## What levnik does (verbatim, `audit_worker_core_contract.md`)

> ## Execution Rules
>
> - Report only unless fixes are explicitly allowed.
> - **Verify Layer 1 candidates before reporting.**
> - Use precise `file:line` locations when available.
> - **Apply worker-specific false-positive filters.**

And in every L3 specialist worker (e.g., `ln-621-security-boundary-auditor`):

> Detection policy: use two-layer detection (candidate scan, then context verification); load `references/two_layer_detection.md` only when the verification method is ambiguous.
>
> Workflow:
> 2) **Scan Codebase (Layer 1):** Run security checks using Glob/Grep patterns
> 3) **Analyze Context (Layer 2):** For each candidate, read surrounding code to classify…
> 4) **Collect Findings:** Record confirmed violations

Mandatory across all 35+ workers. **Layer 1 grep alone never emits a finding**; Layer 2 context read precedes every emit. Each worker also ships worker-specific false-positive filters (e.g., security worker downgrades hardcoded secrets when path matches `**/test/**`).

## Strategic insight

Two-layer detection directly counters two failure modes contest-refactor doc § 7 warns against:

1. **Metric-only finding**: "metric appears as supporting evidence only, mapped to source + behavior" (Q4). Layer 1 grep produces metric-shaped candidates; Layer 2 verification forces source+behavior mapping.
2. **Tool-output theater**: "raw lint dump without interpretation" (Q6). Layer 1 grep IS the raw lint dump; Layer 2 verification is the interpretation.

It also mitigates the metric-worship critique raised by earlier research: per-finding two-layer discipline is harder to anchor-drift than composite scoring, because each finding requires Layer 2 evidence that survives independently.

## Gap matrix

| Mechanism | contest-refactor | levnik |
|---|:--:|:--:|
| Evidence Chain canonical (Claim → Source → Consequence → Remedy) | ✓ Method | n/a (different framework) |
| **Layer 1 candidate scan vs Layer 2 context verify discipline** | partial (implicit) | ✓ MANDATORY in core contract + every worker |
| **Worker-specific FP filters** | partial (lens-specific guidance, no formal filters) | ✓ per-worker FP filters |
| Validation gate on Layer 2 evidence presence | — | partial (DoD check: "checks completed") |
| Trigger condition for Layer 2 method file load | — | ✓ "load only when verification method is ambiguous" |

## P0 GAP — what to import

### Gap A (P0): Formalize two-layer detection as Method rule + validation gate

**Method addition** in `references/method.md` § Meta-Rules (apply everywhere):

> ## Two-Layer Detection (mandatory)
>
> Every finding MUST result from two-layer detection:
>
> **Layer 1 (Candidate Scan)**: Grep/glob/regex/AST scan produces candidate locations. May be wide (catches false positives). Layer 1 alone NEVER emits a finding.
>
> **Layer 2 (Context Verification)**: For every Layer 1 candidate, read surrounding code (typically ±10 lines, or to the enclosing function/type boundary). Classify per the lens's verification rubric:
>
> - **True positive** → emit finding with Layer 2 cited in `evidence[]`
> - **Downgrade target** (e.g., test fixture, code generator output, third-party vendored) → either skip or emit at `Cosmetic for contest` severity with explicit downgrade reason in `severity_rationale`
> - **False positive** → skip; do NOT emit
>
> Each lens ships its own Layer 2 verification rubric in `lens-*.md § Verification Rules`. When the verification method for a candidate is ambiguous, load `references/two-layer-detection.md` (this file) for guidance.

**New `references/two-layer-detection.md`** with verification rules per finding category:

- **Hardcoded secrets**: Layer 2 reads file path + surrounding 20 lines. Downgrade if path matches `**/test/**`, `**/fixtures/**`, `**/__mocks__/**`, OR value matches placeholder pattern (`xxx`, `replaceme`, `your-key-here`). True positive only when value matches credential entropy + path is in production source.
- **SQL injection**: Layer 2 reads call site + reads the method body two frames up. Downgrade if value is constant string OR comes from an ORM call returning `Bound`/`Parameterized` type. True positive only when value path traces to network/user input AND construction is concat.
- **Layer crossing**: Layer 2 reads import statement + imported symbol's declaration. Downgrade if imported symbol is a type alias OR re-export. True positive only when symbol is a live concrete dependency.
- **Dead code candidate**: Layer 2 runs `git log -S "<symbol>"` + checks test/integration suite uses. Downgrade if symbol is exported public API OR has explicit `@unused` annotation OR has reflection/serialization usage. True positive only when zero callers + zero string-key references + zero serialization round-trip use.

(File grows over time as new finding categories are added.)

**New validation gate G42** (G34 reserved by TRACEABILITY-GAP for `changed_hunks` unmapped-ratio check; this doc takes the next free slot).

Per Codex round 1 N2 — original phrasing relied on "byte-range exceeds Layer 1 grep match" which a deterministic Python validator cannot prove without explicit structured fields. Strengthening the schema (preferred over weakening the gate):

**New schema fields per finding** (additive, `schema_version: 4` — default-fill row per [SCHEMA-GAP § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5)):

```jsonc
{
  "layer1_candidate": {                          // NEW — what Layer 1 scan matched
    "pattern": "secrets-grep:hardcoded_token",   // string: scanner ID + rule name
    "match_path": "src/Auth/TokenStore.swift",
    "match_line": 142,                           // single line from grep
    "match_byte_range": [4521, 4567]             // optional, file byte offsets
  },
  "layer2_context": {                            // NEW — what Layer 2 read
    "path": "src/Auth/TokenStore.swift",
    "start_line": 135,                           // structured range, not free-form
    "end_line": 155,
    "byte_range": [4290, 4910],                  // optional
    "lines_read_count": 21                       // deterministic: end_line - start_line + 1
  },
  "layer2_verdict": "true_positive",             // existing per earlier section
  "layer2_rationale": "..."                      // existing
}
```

**G42 (revised) — deterministic Python check**:

> **G42 Two-layer detection evidence (pre-emit)** — Every finding (excluding the carve-out below) MUST populate both `layer1_candidate` and `layer2_context`. Validator checks:
> 1. `layer2_context.lines_read_count >= 5` (Layer 2 must read multi-line context, not single line)
> 2. `layer2_context.start_line <= layer1_candidate.match_line <= layer2_context.end_line` (Layer 2 range CONTAINS Layer 1 match)
> 3. `layer2_context.path == layer1_candidate.match_path` (same file)
> 4. `layer2_rationale` non-empty string ≥ 20 chars
>
> Any field missing OR check failing = G42 failure. Deterministic Python; no LLM judgment required.
>
> **Carve-out**: suspended for findings with `severity: "Cosmetic for contest"` AND `lens_source == "n/a"` (mechanical findings like trailing-whitespace where Layer 1 = Layer 2 by construction).

**Schema addition** (additive, `schema_version: 4` — default-fill row per [SCHEMA-GAP § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5)):

```jsonc
{
  "findings": [
    {
      "loop_local_id": "F1",
      "evidence": [
        "src/Auth/TokenStore.swift:142",           // Layer 1 candidate (existing)
        "src/Auth/TokenStore.swift:135-155"        // Layer 2 context (NEW — required by G42)
      ],
      "layer2_verdict": "true_positive",          // NEW enum: true_positive | downgraded | false_positive_excluded
      "layer2_rationale": "Token value is concatenated from network response at line 148; verified by reading initializer at 135-155. Not test fixture; path is production source.",
      // ... existing fields ...
    }
  ]
}
```

The `layer2_verdict: "false_positive_excluded"` value is permitted only for findings that were considered then dropped (recorded in a new `excluded_candidates[]` array, NOT in `findings[]`). This gives the Critic an audit trail of what was checked but not emitted.

### Optional additions

- New `excluded_candidates[]` top-level field in `CURRENT_REVIEW.json` documenting Layer 1 candidates that failed Layer 2 verification. Each entry: `{candidate_pattern, file_lines_checked, exclusion_reason}`. Caps at 20 entries to bound the artifact size.

## Pairing with other gap docs

- **SPECIALTY-LENS-DISPATCH-GAP**: each `lens-*.md` ships its own Layer 2 verification rules; this gap formalizes the protocol all lenses follow
- **SCHEMA-GAP `confidence` field** (canon: 2-value `high|medium`, per [SCHEMA-GAP-CONTEST-REFACTOR.md § Confidence enum canon](SCHEMA-GAP-CONTEST-REFACTOR.md#confidence-enum-canon-sc1-resolution)): Layer 1 alone = not emitted (Layer-1-only candidates go into `excluded_candidates[]`, not `findings[]`, so `confidence: low` is intentionally absent from the canon); Layer 2 weak verification (single evidence pointer) = `confidence: medium`; Layer 2 strong verification (multi-evidence or cross-checked) = `confidence: high`
- **CRITIC-INDEPENDENCE Gap C (validator subagent)**: validator can refuse to confirm findings without Layer 2 evidence; pairs with G42
- **Q4 + Q6 (quality passes)**: two-layer detection HARDENS these from quality-pass to validation-gate

### Adjacent reasoning contract (logic-lens, added 2026-05-25 per Codex Class 2 MC2)

`refs/competitors/logic-lens/AGENTS.md:25` defines an **Iron Law** for every emitted finding: must use `Premises → Trace → Divergence → Trigger → Remedy` (5-stage reasoning chain anchored in `skills/_shared/common.md`). This is a stricter pre-remedy reasoning contract than contest-refactor's `Claim → Source → Consequence → Remedy` (4-stage) at `references/method.md`.

**Comparison**:
- contest-refactor `Claim → Source → Consequence → Remedy` — anchors the assertion + cites evidence + ties to architectural impact + proposes fix
- logic-lens `Premises → Trace → Divergence → Trigger → Remedy` — separates the premises (what assumptions the reasoning rests on) from the trace (the path of logic) from the divergence (where actual behavior departs) from the trigger (the executable case that proves it) from the remedy

**Difference that matters**: logic-lens's `Trigger` field is an **executable case** — a specific input or condition that would reproduce the divergence. contest-refactor's chain has no analog; `evidence[]` is observational, not causal. Adopting `trigger:` as an optional finding-level field would harden the architecture findings most likely to be "subjectively obvious" into falsifiable claims.

**Adoption recommendation** (P2 deferred): not a Layer-1/Layer-2 augmentation per se — it's a per-finding *reasoning contract* refinement that pairs more naturally with [SCHEMA-GAP-CONTEST-REFACTOR.md § Gap 2 (severity_rationale)](SCHEMA-GAP-CONTEST-REFACTOR.md). Defer until at least 3 finding categories where causal-trigger is meaningfully testable (e.g., the `seam_violation` family). Tracking here because logic-lens's contract was missed in prior research; the full Iron Law belongs in a future per-domain protocol doc, not in the schema canon.

## What contest-refactor wins vs levnik

- **Evidence Chain Claim → Source → Consequence → Remedy is broader** than levnik's `verify Layer 1 before reporting` — contest-refactor's chain forces Consequence + Remedy fields too, not just verified Source
- **Per-finding `evidence[]` array** is structurally identical to levnik's `file:line` requirement; both win

## What NOT to import

| Tempting | Why skip |
|---|---|
| Two-layer detection as an LLM-judged predicate | Layer 2 is determined by content read, not by an LLM judging "is this two-layer." G42 checks byte-range presence (deterministic); doesn't ask LLM whether reading was sufficient. |
| Mandatory Layer 2 for every finding regardless of severity | Mechanical findings (`severity: "Cosmetic for contest"` + `lens_source: "n/a"` like trailing-whitespace) don't need verification. Carve-out documented in G42. |
| levnik's worker-specific FP filter as embedded code | FP filters belong in each `lens-*.md § Verification Rules` (data), not in scripts. Keeps `scripts/` deterministic + schema-validator-only. |

## Adoption order

1. **Phase 1**: Write `references/two-layer-detection.md` with verification rules for the 4 most common false-positive categories (secrets, SQL injection, layer crossing, dead code)
2. **Phase 2**: Update `references/method.md` Meta-Rules section + each `lens-*.md § Verification Rules`
3. **Phase 3**: Add G42 to `references/validation.md` + implement in `scripts/validate-artifact.py`
4. **Phase 4** (optional): Add `excluded_candidates[]` top-level field for audit trail

Small, contained, high-impact change. No cross-cutting refactor required.
