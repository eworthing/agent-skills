# Specialty Lens Dispatch Gap — contest-refactor vs levnik + agentlint + claude-bouncer + trailofbits

> **CURRENT-STATE (2026-06-28):** DEFERRED — static single-stack-lens + always-included security by design; no risk-triggered dispatch table. See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.
> Gate numbers **G37+** cited below are UNBUILT proposals — G33–G36 have since SHIPPED (2026-06-29); the live catalog (`contest-refactor/canon/validation-gates.toml`) now stops at **G36**. *(Re-verified 2026-06-30.)*

Merges what was originally split between "Risk-Triggered Lenses" (per landscape doc § 6 P1) and "Specialty-Lens-Dispatch" (per LEVNIK-AUDIT-SUITE-GAP Gap C). Same architectural mechanism viewed from two angles: contest-refactor's monolithic lens system (`lens-apple.md` | `lens-generic.md`) needs to gain risk-triggered specialty packs.

## Baseline: contest-refactor today

- 2 lenses total: `references/lens-apple.md` (~340 lines) | `references/lens-generic.md` (~85 lines)
- Selection mechanism: Step 0 stack detection, `--force-lens <apple|generic>` CLI override, recorded in `discovery.lens`
- ALWAYS-ON: selected lens loaded once at Step 0, used by every loop's Critic in Step 1
- No trigger-based specialty dispatch (e.g., "if auth code touched, load security lens")
- No category-specific anchor packs beyond the apple/generic split
- 5 risk-triggered hard gates exist but are validation-time, not lens-loading-time:
  - G24 (Authority Map test-surface cross-check, fires when `test_strategy >= 9`)
  - G25 (Continuation-bridge delegate audit, fires when `concurrency >= 9`)
  - G26 (Anchor-to-source check, fires every loop after loop 1)

## Trigger-predicate patterns in the wild (source-confirmed)

### levnik audit-suite (`refs/competitors/levnik-skills/plugins/codebase-audit-suite/`)

**Pattern**: stack-detection-triggered. PHASE_1_DISCOVERY detects project type/language/framework; coordinator skips inapplicable workers. **Hardcoded worker list** (ln-621 through ln-629) — no per-finding risk triggers.

**Strength**: applicability filter at known boundary (start of run).
**Weakness**: doesn't react to risks discovered mid-loop (e.g., agent touches concurrency code mid-refactor → ln-628 doesn't auto-dispatch).

### claude-bouncer (`refs/competitors/claude-bouncer/`)

**Pattern**: per-tool-call pattern matching. PreToolUse hooks fire on every tool invocation; match against regex/glob (`rm -rf`, `:(){ :|:& };:`, etc.); block + emit dialog.

**Strength**: triggers at the exact moment risk surfaces (tool-call boundary). Tight latency.
**Weakness**: only blocks/allows. Doesn't load additional analytical context. Suited for safety enforcement, not specialty analysis.

### agentlint (`refs/competitors/agentlint/`)

**Pattern**: dimension-gated static checks. All 51 core checks run every invocation; file-existence gates entire dimensions (no hooks.json → Harness dimension skipped). 

**Strength**: deterministic, exhaustive coverage when files exist.
**Weakness**: not risk-responsive within a session. Once started, all applicable checks run.

### trailofbits (`refs/competitors/trailofbits-skills/`)

**Pattern**: marketplace of specialty plugins (fp-check, c-review, differential-review, static-analysis, variant-analysis, semgrep-rule-creator, supply-chain). User installs by category; each plugin owns its own SKILL.md + agents + references.

**Strength**: clean plugin packaging per specialty.
**Weakness**: user-chosen scope, no automatic risk-trigger. Adding a plugin = enabling a category always-on.

## Strategic insight

Contest-refactor needs a HYBRID of all four:

- **claude-bouncer's tool-call timing** (react when code is touched)
- **levnik's stack-detection** (which lenses are even applicable to this repo)
- **agentlint's file-existence gating** (don't run hooks-lens if no hooks)
- **trailofbits' plugin packaging** (each specialty owns its references file)

Default model = **explicit predicate registry** loaded at Step 0; dispatched in Step 1 Method step 5 ("Stack lens checklist") AND mid-loop when triggers fire.

## Proposed design: lens-registry.toml + trigger predicates

### New canonical file: `references/lens-registry.toml`

```toml
# Each lens is a markdown rule pack OR a script.
# Lenses are RULE PACKS loaded into Critic's context, NOT subagent dispatches.
# Multiple lenses can fire in one loop.

[[lens]]
id = "apple"
kind = "stack"                         # always-on per-stack lens
applicability = ["swift", "ios", "macos"]
references = "lens-apple.md"

[[lens]]
id = "generic"
kind = "stack"
applicability = ["rust", "go", "python", "node", "java", "kotlin", "ruby"]
references = "lens-generic.md"

[[lens]]
id = "concurrency_hazards"
kind = "specialty"                     # risk-triggered specialty lens
references = "lens-concurrency.md"     # NEW file (adapted from levnik ln-628)
trigger.scoring = "concurrency >= 9"   # fires when Critic considers high concurrency score
trigger.touched_paths = ["**/concurrent/**", "**/async/**", "**/*Actor*"]
trigger.code_patterns = ["withCheckedContinuation", "Task.detached", "async let", "Mutex", "RwLock"]

[[lens]]
id = "security_boundaries"
kind = "specialty"
references = "lens-security.md"        # NEW file (adapted from levnik ln-621 + anthropic-security-review)
trigger.touched_paths = ["**/auth/**", "**/crypto/**", "**/secrets/**", "**/network/**"]
trigger.code_patterns = ["execSql", "raw(", "innerHTML", "dangerouslySetInnerHTML", "process.env"]
trigger.evidence_keywords = ["secret", "credential", "token", "password", "api_key"]

[[lens]]
id = "persistence_efficiency"
kind = "specialty"
references = "lens-persistence.md"
trigger.touched_paths = ["**/db/**", "**/queries/**", "**/repo*/**"]
trigger.code_patterns = ["JOIN", "FETCH", "@OneToMany", "lazy = ", "for .* in .*.query"]

[[lens]]
id = "test_isolation_oracle"
kind = "specialty"
references = "lens-test-quality.md"
trigger.scoring = "test_strategy >= 9"
trigger.touched_paths = ["**/test*/**", "**/spec*/**", "**/*_test.*", "**/*Tests.*"]

[[lens]]
id = "architecture_boundary"
kind = "specialty"
references = "lens-architecture-boundary.md"
trigger.layer_crossing_detected = true   # populated by boundary-rule check (GOVERNANCE-GAP Gap C)
trigger.touched_paths = ["**/Domain/**", "**/UI/**"]

[[lens]]
id = "dead_code"
kind = "specialty"
references = "lens-dead-code.md"
trigger.refactor_kind = "removal"        # set by Step 2 plan
```

### Lifecycle integration

**Step 0 (Discovery)**:
1. Detect stack → select one stack lens (`apple` or `generic`); record in `discovery.lens`
2. Load `lens-registry.toml`; record applicable specialty lenses in `governance_context.specialty_lenses_available[]`
3. Evaluate which specialties have triggers that COULD fire this run (based on repo content, not just paths touched yet) → record in `governance_context.specialty_lenses_armed[]`

**Step 1 (Critic Phase)**:
1. Method step 5 ("Stack lens checklist") loads stack lens (existing behavior)
2. **NEW Method step 5a (Specialty trigger evaluation)**:
   - For each lens in `governance_context.specialty_lenses_armed[]`, evaluate trigger predicates against:
     - `discovery.working_tree_dirty_paths[]` (paths agent touched)
     - prior loop's `loop_result.changed_paths[]` (recent agent activity)
     - source code patterns (grep for `trigger.code_patterns`)
     - current loop's scoring intent (`trigger.scoring` predicates)
     - boundary-rule check output (`trigger.layer_crossing_detected`)
     - Step 2 plan if reading (`trigger.refactor_kind`)
   - Load lens references for every triggered lens
   - Record fired triggers in `CURRENT_REVIEW.json.lenses_fired[]`

**Step 1 emit**:
- New CURRENT_REVIEW.json field: `lenses_fired: ["apple", "concurrency_hazards"]`
- Findings authored under a specialty lens carry `lens_source: "concurrency_hazards"` field
- Pairs with SCHEMA-GAP `critic_source` field (both populate provenance)

### Schema additions (additive, `schema_version: 4`)

*Default-fill row per [SCHEMA-GAP § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5) — heading text + anchor preserved for backward link compatibility.*

```jsonc
{
  "discovery": {
    "lens": "apple"                               // existing — stays here (first-loop discovery field)
  },
  "governance_context": {                         // durable cross-loop container per Codex round 1 N1 + GOVERNANCE-GAP prerequisite
    "specialty_lenses_available": [               // NEW — what could fire; cross-loop persistent
      "concurrency_hazards", "security_boundaries", "persistence_efficiency",
      "test_isolation_oracle", "architecture_boundary", "dead_code"
    ],
    "specialty_lenses_armed": [                   // NEW — armed by repo content (subset of available)
      "concurrency_hazards", "security_boundaries", "test_isolation_oracle"
    ]
  },
  "lenses_fired": ["apple", "concurrency_hazards"],   // NEW — which lenses fired this loop
  "findings": [
    {
      "loop_local_id": "F1",
      "lens_source": "concurrency_hazards",       // NEW per-finding — which lens authored
      // ... existing fields ...
    }
  ]
}
```

### New validation gates

**G35: Lens-source attribution**. Every finding carrying `lens_source != null` MUST appear in `lenses_fired[]` for this loop AND `lens_source` MUST equal a lens id in `references/lens-registry.toml`. Findings authored by the always-on stack lens (`apple` or `generic`) MUST set `lens_source` to the stack lens id, not null.

**G36: Specialty lens trigger evidence**. For every specialty lens in `lenses_fired[]`, `CURRENT_REVIEW.md` must include a `## Lens Trigger Evidence` subsection citing which trigger predicate fired (e.g., "concurrency_hazards fired: working_tree_dirty_paths overlap `**/concurrent/**`").

## Initial specialty-lens content sources

For each new `lens-*.md` file, port rules verbatim from inspected competitors:

| Lens | Primary source | Key rules to port |
|---|---|---|
| `lens-concurrency.md` | levnik ln-628-concurrency-correctness-auditor + contest-refactor's existing G25 | async races, TOCTOU, deadlocks, blocking-in-async, resource contention, cross-process races, continuation-bridge audit |
| `lens-security.md` | levnik ln-621-security-boundary-auditor + anthropic-security-review's 17 enumerated exclusions (16 unique; source has a duplicated `16.` numbering typo, per Codex SM1 fix) + claude-bouncer pattern list | hardcoded secrets (prod vs test), SQL injection with ORM context, XSS with framework auto-escape, sensitive env defaults, input validation, dangerous Bash patterns when shell-out detected |
| `lens-persistence.md` | levnik ln-650 + ln-651 | N+1 detection, query plan analysis, transaction correctness, cartesian products, missing indexes |
| `lens-test-quality.md` | levnik ln-635 + ln-638 + contest-refactor's existing G24 | test isolation (shared state detection), oracle effectiveness (assertion specificity), flakiness markers |
| `lens-architecture-boundary.md` | levnik ln-642 + GOVERNANCE-GAP boundary rules (Gap C) | transaction-boundary ownership, session DI vs local, flat orchestration depth, layer-import violations |
| `lens-dead-code.md` | levnik ln-626 + contest-refactor's existing `test_failed: "Deletion test"` | deletion-test verbatim from mattpocock, dead-import detection, dead-branch (always-false condition) |

## Gap matrix

| Mechanism | contest-refactor | levnik | claude-bouncer | agentlint | trailofbits |
|---|:--:|:--:|:--:|:--:|:--:|
| Stack-detection lens selection | ✓ (apple/generic) | ✓ (stack discovery) | — | partial (file-gated dimensions) | ✓ (plugin per category) |
| **Risk-triggered specialty lens dispatch** | **—** | partial (DISCOVERY only) | partial (tool-call only) | — | — (user-selected) |
| Tool-call-time evaluation | — | — | ✓ PreToolUse | — | — |
| Mid-loop trigger evaluation (after Discovery) | — | — | — | — | — |
| Per-finding lens-source attribution | — | partial (worker field) | — | partial (check_id) | partial (skill id) |
| Trigger predicate registry | — | hardcoded in coordinator | inline shell regex | hardcoded in scanner.sh | none |
| Lens packaging | references/ markdown | full subagent per worker | shell script per hook | static checks | full plugin per category |

## What NOT to import

| Tempting | Why skip |
|---|---|
| levnik's full L3-Worker subagent dispatch per specialty | Spawning a subagent for every triggered specialty is expensive. Contest-refactor's lens system loads markdown rule packs into the Critic's context — cheaper and composable. Reserve subagent dispatch for parallel critic mode (CRITIC-INDEPENDENCE Gap B). |
| Hardcoded worker list per coordinator (levnik pattern) | `lens-registry.toml` is data, not code — projects can extend specialty lenses without forking the skill. Don't bake the list into Critic prose. |
| claude-bouncer's hard-block PreToolUse for lens loading | Lens loading is informational, not safety-critical. Blocking the agent mid-tool-call to load a lens makes the agent unable to make progress. Lenses load at Step 1, not at PreToolUse. |
| agentlint's all-checks-every-time model | Specialty lens triggers must be CONDITIONAL — running concurrency checks on a pure-config refactor wastes tokens. Risk-trigger predicates exist to PREVENT always-on overhead. |
| trailofbits' user-installs-plugins-by-hand | Contest-refactor's lens registry is loaded automatically; user opts OUT of specific lenses via `--disable-lens` flag if desired, not opt-in per-skill. |
| Per-finding LLM-judged trigger (recompute every time) | Trigger predicates are deterministic: glob match, regex match, scoring threshold. Keep them in `validate-repo.py`-validatable TOML, not LLM-evaluated prose. |

## Adoption order

1. **Phase 1 (foundation)**: Create `lens-registry.toml` + 6 specialty lens markdown files (port rules from cited sources). Wire Step 0 to load registry. Add `governance_context.specialty_lenses_available[]` + `governance_context.specialty_lenses_armed[]`. NO trigger evaluation yet; just inventory.
2. **Phase 2 (trigger predicates)**: Wire Step 1 Method step 5a trigger evaluation. Implement glob/regex/scoring predicates in `_canon.py` or a new `scripts/_lens_trigger.py`. Add `lenses_fired[]` + per-finding `lens_source`.
3. **Phase 3 (validation gates)**: Add G35 + G36 to `references/validation.md` + `scripts/validate-artifact.py`.
4. **Phase 4 (per-lens content)**: Iterate per specialty lens. Start with `lens-security.md` (highest risk-of-miss; security findings have the most asymmetric cost). Then `lens-concurrency.md`. Then others.

## Pairing with other gap docs

- **GOVERNANCE-GAP Gap C (boundary_rules)**: feeds `trigger.layer_crossing_detected` for `architecture_boundary` lens
- **SCHEMA-GAP Gap 3 (critic_source)**: `lens_source` is orthogonal but related; both populate finding provenance
- **CRITIC-INDEPENDENCE Gap B (parallel critic mode)**: each parallel critic can be a triggered specialty lens

## Adoption-signal augmentation: adaptive specialist gating (gstack, added 2026-05-25 per Codex Class 2 MC1)

`refs/competitors/gstack/review/SKILL.md:1301-1313` ships an **adaptive specialist gating** layer that sits *after* scope-based trigger evaluation: each specialist is tagged `[GATE_CANDIDATE]` (0 findings in 10+ dispatches → auto-skip) or `[NEVER_GATE]` (insurance-lens like security/data-migration; always dispatch regardless of hit rate). Force flags (`--security`, `--all-specialists`) override gating.

**Why interesting for contest-refactor**: contest-refactor's proposed `lens-registry.toml` trigger predicates are static (glob/regex/scoring threshold per Adoption-order Phase 2 above). gstack adds a **dynamic gating layer** based on per-lens hit-rate history. For lenses with provably low-yield on a given project, auto-suppression reduces token spend without losing safety: `[NEVER_GATE]` reserves the bypass for high-asymmetric-cost categories (security, data migration).

**Adoption recommendation** (P2, not P1): defer until contest-refactor has shipped 6+ lenses AND has at least 10 cross-project hit-rate samples to draw on. Premature gating with sparse data would over-suppress. When added, store hit-rate metadata in `governance_context.lens_hit_history{lens_name: {dispatches: N, findings_emitted: M}}` and apply `[GATE_CANDIDATE]` only when `dispatches >= 10 AND findings_emitted == 0`. `[NEVER_GATE]` annotation lives in `lens-registry.toml` per-lens (`insurance_lens = true` field).
- **LEVNIK-AUDIT-SUITE-GAP Gap A (two-layer detection)**: rule applies inside each specialty lens
- **TWO-LAYER-DETECTION-GAP**: this lens-dispatch mechanism is the carrier; two-layer-detection is the rule applied within

## Risk flags

1. **Trigger overshoot**: too-permissive predicates load too many specialty lenses → token bloat. Mitigation: each specialty lens has hard token budget (≤2000 tokens loaded); over-budget fires only the highest-priority lens (priority field in `lens-registry.toml`).
2. **Trigger undershoot**: predicate doesn't fire on a real risk → silent miss. Mitigation: `governance_context.specialty_lenses_armed[]` is broader than `lenses_fired[]`; Critic must explain in `## Lens Trigger Evidence` why an armed-but-not-fired lens was skipped this loop.
3. **Lens content drift**: porting rules from levnik/anthropic/etc. means tracking upstream changes. Mitigation: each `lens-*.md` cites source repo+ref at top; `validate-repo.py` checks citation freshness annually.
4. **Specialty-Critic disagreement**: stack lens (`apple`) and specialty lens (`concurrency_hazards`) may disagree on the same finding. Mitigation: priority order in `lens-registry.toml`; specialty lenses inherit from stack lens unless explicitly overriding.
