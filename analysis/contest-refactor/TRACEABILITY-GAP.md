# Changed-Line Traceability Gap — contest-refactor vs P0 competitors

> **CURRENT-STATE (2026-06-28):** DEFERRED — file-level tie-back already works (`loop_result.targeted_finding_status` + routing `priority_1_finding_id` + G22 commit subject); per-hunk `changed_hunks[]` = plan W3 defer (refinement, not a missing capability). See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.
> Gate numbers **G37+** cited below are UNBUILT proposals — G33–G36 have since SHIPPED (2026-06-29); the live catalog (`contest-refactor/canon/validation-gates.toml`) now stops at **G36**. *(Re-verified 2026-06-30.)*

Compares contest-refactor's traceability machinery (per-finding `evidence[]` + `blast_radius`, per-loop `loop_result.changed_paths[]` + `targeted_finding_id`, `LOOP_STATE.pre_step3_blob_shas`, G22 commit subject pattern, `findings_registry.json` cross-loop occurrences) against:

- **pr-agent** (`refs/competitors/pr-agent/`) — qodo-ai/pr-agent, ~11k★, mature PR diff reviewer
- **aider** (`refs/competitors/aider/`) — Aider-AI/aider, ~45k★, terminal pair-programming with repo-map + auto-commit
- **anthropic pr-review-toolkit** (`refs/competitors/anthropic-claude-code/plugins/pr-review-toolkit/`) — 6-agent PR report-generation plugin

Missed-on-first-pass comparator worth folding into this analysis: **levnik-skills**, which added explicit `file`, `line_start`, and `line_end` review-schema fields in its review-suggestion schema v2.

## Baseline: contest-refactor today

**Per-finding (Critic side):**
- `evidence[]` — array of `file:line` strings (Source in evidence chain)
- `blast_radius{change[], avoid[]}` — **predicted** touch list + forbidden paths
- `stable_id` cross-loop identity

**Per-loop (Actor side):**
- `loop_result.changed_paths[]` — from `git diff --name-only HEAD` post-edit (file-level only)
- `loop_result.what_changed` — prose paragraph
- `loop_result.targeted_finding_id` + `targeted_finding_status` (`resolved | carried_forward`)
- `loop_result.unintended_regression` — when reviewer rejected
- `LOOP_STATE.pre_step3_blob_shas{path: blob_sha}` per-file restore source

**Implementation Review:**
- Reviewer subagent runs three checks (reality / honesty / regression) on the diff
- Verdict enum: `approved | conditional | rejected`
- Rejected → narrow revert via `pre_step3_blob_shas`

**Cross-loop:**
- `findings_registry.json` occurrences[] include `sha` (commit when status changed) + `attempted_remedy_hash`
- G22 commit subject pattern: `loop N: <verb>; finding F<n> (stable_id F-NNN) <status> [registry: +<n> findings, ~<n> occurrences]`

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent, **n/a** = doesn't apply.

| Mechanism | contest-refactor | pr-agent | aider | pr-review-toolkit |
|---|:--:|:--:|:--:|:--:|
| Finding line anchor | partial (`file:line` single points in evidence[]) | ✓ `relevant_file + start_line + end_line` | n/a (no findings) | partial (`[file:line]` string) |
| **Hunk-level diff parsing** | **— (file-level only)** | ✓ `@@ -start,size +start,size @@` regex | partial (per edit-format) | — |
| **Per-line / per-range finding traceability** | **—** | ✓ ranges in suggestions | — | partial |
| Per-file changed list | ✓ `loop_result.changed_paths[]` | partial (in compression) | ✓ `edited: set` | partial |
| **Predicted blast radius BEFORE edit** | ✓ `blast_radius{change[], avoid[]}` | — | — | — |
| **Pre-edit blob shas for narrow revert** | ✓ `pre_step3_blob_shas` per-FILE | — | — | — |
| Per-hunk revert | — | partial (suggestion-level reject) | — | — |
| **Commit ↔ finding linking** | ✓ G22 commit subject | — (PR-level only) | — (intent in conv history only) | — |
| **Cross-loop stable_id ↔ commit mapping** | ✓ `findings_registry.occurrences[].sha` | — | — | — |
| Reviewer verdict gate (reality / honesty / regression) | ✓ approved/conditional/rejected | partial (self-reflection score 0-10) | — | — |
| Dynamic context expansion | — | ✓ `allow_dynamic_context` flag | partial (repo-map) | — |
| PR compression algorithm | n/a | ✓ token-aware sort + drop | partial (repo-map ranking) | — |
| Multi-edit-format support | — (LLM writes files freely) | n/a | ✓ whole / diff / udiff / patch | — |
| Repo-wide symbol map (PageRank or similar) | — | — | ✓ tree-sitter + NetworkX PageRank | — |
| Inline PR comments | n/a | ✓ multi-provider | — | — |
| Re-review on push (changed-since tracking) | ✓ (better than PR-Agent — fingerprint-based, not file-set) | ✓ `unreviewed_files_set` | — | — |
| Lint/test feedback loop | partial (Step 1 build/test) | — | ✓ auto-lint + auto-test → LLM | — |
| Self-reflection / validator filter | — (proposed in Schema Gap) | ✓ 2nd LLM, score 0-10, threshold filter | — | — |

## Strategic insight

Contest-refactor leads on **causal traceability**: every commit ties back to a stable_id via the G22 subject pattern; every finding ties to an Actor outcome via `targeted_finding_status`; every loop carries a predicted `blast_radius` BEFORE edit. That prediction claim should be stated carefully: the sampled PR-review tools are mostly post-hoc, but Aider does plan changes conversationally before editing. The stronger and source-backed claim is that contest-refactor already records a **structured predicted touch list** (`blast_radius`) rather than leaving the prediction implicit in chat.

What contest-refactor lags is **per-hunk / per-line resolution**. Today `loop_result.changed_paths[]` is file-only. PR-Agent's hunk-level model lets each suggestion carry `start_line + end_line`. The doc's P0 ask is verbatim:

> *"Every changed line maps to a finding ID, validation failure, or explicit scoped cleanup."*

Contest-refactor satisfies this **at file granularity** via `targeted_finding_id` + Implementation Reviewer prose. At hunk granularity, there's nothing structured — the reviewer's prose might say "the rename in Foo.swift was justified by F3 but the type-narrowing in Bar.swift was scope creep," but there's no field to record this so a downstream consumer (or the next loop) can audit.

## P0 GAPS — what to import

### Gap A: Per-hunk changed_hunks[] with finding tie-back (the doc's verbatim P0)

Closes the "every changed line maps to a finding ID" gap structurally.

**Schema** (additive, `schema_version: 4` — default-fill row per [SCHEMA-GAP § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5)):

```jsonc
// CURRENT_REVIEW.json.loop_result
{
  "changed_paths": [...],  // existing, kept

  // NEW
  "changed_hunks": [
    {
      "hunk_id": "h1",                          // canonical hunk identifier within this loop
      "path": "src/Domain/Order.swift",
      "old_start": 42, "old_size": 5,           // from `git diff -U0 HEAD`
      "new_start": 42, "new_size": 8,
      "changed_line_count": 8,                  // DETERMINISTIC: computed by Python orchestrator from `git diff -U0` hunk header (+size minus -size context), passed to Implementation Reviewer as READ-ONLY. NEVER asked of the LLM (per Gemini Pro round 2 N1 — LLMs are unreliable at patch offset math). G34 enforces this count vs reviewer's hunk-tie decisions; reviewer must not author this field.
      "ties_to_finding_id": "F3",                // local id this loop, or null for "while I was here"
      "ties_to_stable_id": "F-007",              // optional cross-loop link
      "tie_kind": "remedy",                      // enum: remedy | regression_fix | follow_on_cleanup | mechanical | unmapped
      "rationale": "Narrowed Optional<Order> to Order at Two-adapter rule boundary"
    }
  ]
}
```

**New gate G34:**

> When `loop_result.changed_hunks[]` is non-empty, every hunk MUST have `hunk_id`, `tie_kind`, and `changed_line_count` populated. Hunks with `tie_kind ∈ {"remedy", "regression_fix", "follow_on_cleanup"}` MUST set at least one of `ties_to_finding_id` or `ties_to_stable_id`. Hunks with `tie_kind: "unmapped"` MUST carry a non-empty `rationale`, and total `changed_line_count` for unmapped hunks must be ≤ 5% of the total changed-line count **unless** `loop_result.unmapped_hunks_explanation` is present.

Implementation Reviewer's job extends naturally: it already runs three checks; now it also populates `changed_hunks[].tie_kind` from the diff + finding evidence. Adapting PR-Agent's hunk-parsing regex (`@@ -start,size +start,size @@`) is ~50 lines of Python in the Reviewer's prompt template. Semantic adequacy of an `unmapped_hunks_explanation` belongs to reviewer/validator judgment; G34 itself stays structural.

Pairs with HALT-STATE-GAP Gap C (per-hunk partial-accept) — both share the same hunk-parsing layer.

### Gap A.1: Refactoring-pattern canonical vocabulary

rohitg00's `refactoring-specialist.md:20` (full path: `refs/competitors/rohitg00-toolkit/agents/developer-experience/refactoring-specialist.md`) recommends "naming the specific refactoring pattern applied" in commit messages but doesn't formalize. (Earlier draft cited `:9` — that line is part of the YAML frontmatter; the commit-pattern rule lives at line 20 in the numbered Process section.) Combined with arXiv:2511.04824's empirical finding (Change Variable Type 11.8% / Rename Parameter 10.4% / Rename Variable 8.5%), there's a clear case for a canonical Fowler-derived enum.

**Adopt** new canon file `canon/refactoring-patterns.toml`:

```toml
# Canonical refactoring-pattern vocabulary. Derived from Fowler's Refactoring
# catalog (2nd ed.) + arXiv:2511.04824 empirical observations.
# Used by:
#   - loop_result.changed_hunks[].refactoring_pattern (NEW field — optional per hunk)
#   - loop_result.refactoring_types[] (NEW audit aggregate — see ARXIV-AGENTIC-REFACTORING-GAP)
#   - G22 commit-subject pattern extension: `loop N: [<PATTERN>] <verb>; finding F<n> ...`

refactoring_patterns = [
    # Composing methods
    "Extract Method",
    "Inline Method",
    "Extract Variable",
    "Inline Variable",
    "Change Function Declaration",
    "Encapsulate Variable",

    # Renaming + retyping (most common per arXiv)
    "Rename Variable",
    "Rename Parameter",
    "Change Variable Type",
    "Rename Function",
    "Rename Field",

    # Moving features
    "Move Function",
    "Move Field",
    "Move Statements Into Function",
    "Move Statements To Callers",
    "Replace Inline Code With Function Call",

    # Organizing data
    "Split Variable",
    "Replace Magic Literal",

    # Simplifying conditional logic
    "Decompose Conditional",
    "Consolidate Conditional Expression",
    "Replace Nested Conditional With Guard Clauses",
    "Replace Conditional With Polymorphism",

    # Refactoring APIs
    "Separate Query From Modifier",
    "Parameterize Function",
    "Remove Flag Argument",
    "Preserve Whole Object",
    "Replace Parameter With Query",

    # Dealing with inheritance
    "Pull Up Field",
    "Pull Up Method",
    "Push Down Field",
    "Push Down Method",
    "Replace Subclass With Delegate",
    "Replace Type Code With Subclasses",

    # Cross-module reorganization
    "Replace-don't-layer",                   # contest-refactor-specific (test_failed enum)
    "Collapse Hierarchy",
    "Move Adapter",                          # contest-refactor-specific (Two-adapter rule remedy)

    # Removal
    "Remove Dead Code",
    "Remove Unused Parameter",
    "Remove Duplicate Code",
]
```

**Schema additions** (additive, `schema_version: 4` — default-fill row per [SCHEMA-GAP § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5)):

```jsonc
{
  "loop_result": {
    "changed_hunks": [
      {
        "hunk_id": "h1",
        "refactoring_pattern": "Extract Method",   // NEW; optional; null when hunk doesn't map to a named pattern
        // ... existing changed_hunks fields ...
      }
    ],
    "refactoring_types": [                        // NEW audit aggregate (pairs with ARXIV-AGENTIC-REFACTORING)
      {"type": "Extract Method", "count": 2},
      {"type": "Rename Variable", "count": 4},
      {"type": "Change Variable Type", "count": 1}
    ]
  }
}
```

**G22 commit subject extension** (additive):

```
loop <N>: [<PATTERN>] <verb-phrase>; finding F<n> (stable_id F-<NNN>) <status> [registry: ...]

Examples:
  loop 3: [Extract Method] collapse repository-theater seam in OrderIntake; finding F3 (stable_id F-007) resolved [registry: +0 findings, ~1 occurrence]
  loop 3: [Rename Variable + Change Variable Type] tighten Order intake types; finding F2 (stable_id F-005) resolved [registry: +0 findings, ~1 occurrence]
```

The `[<PATTERN>]` prefix is OPTIONAL — required only when `loop_result.changed_hunks[].refactoring_pattern` is populated for ≥80% of hunks. Multi-pattern commits use `[Pattern1 + Pattern2]` syntax.

**Validation gate G43** (sub-gate of G34): When `loop_result.refactoring_types[]` non-empty, every entry's `type` MUST exist in `canon/refactoring-patterns.toml`. Unknown pattern names = G43 failure.

**Downstream value**: aggregated `refactoring_types[]` data in `REVIEW_HISTORY.json` lets users measure their contest-refactor runs against arXiv:2511.04824's baseline (per ARXIV-AGENTIC-REFACTORING-GAP). High rename/retype ratio per fixture #5 from SKILL-TDD-FIXTURES-GAP would falsify "contest-refactor manufactures structural findings."

**Adoption order**: ship after Gap A (changed_hunks) lands. Gap A is prerequisite — `refactoring_pattern` is a per-hunk field on `changed_hunks[]`.

### Gap F: Self-reflection scoring (pairs with Schema Gap validator)

Schema Gap Analysis recommended a per-finding validator subagent with `confidence` field. PR-Agent's pattern is the concrete implementation reference: second LLM call scores 0-10, validates `existing_code` matches the referenced lines, filters below threshold (8 = critical).

**Cross-link only.** No new work here beyond what Schema Gap already proposed; flag the PR-Agent prompts at `pr_agent/settings/code_suggestions/pr_code_suggestions_reflect_prompts.toml` as the reference implementation when the validator ships.

### Gap B: Dynamic context-window in evidence[] (small optimization, defer)

PR-Agent's `allow_dynamic_context` flag auto-expands a hunk to its enclosing function. Contest-refactor's Critic reads source on demand. Could add `evidence[].context_window` field carrying `start_line - 10 .. end_line + 10` so Implementation Reviewer doesn't re-derive — but this is plumbing, not a capability gain.

**Defer.** Revisit if Reviewer subagent is wasting tokens re-reading.

### Gap D: Per-provider edit-format adapter (Aider's pattern, defer)

Aider supports whole / diff / udiff / patch and picks per model (Claude prefers search/replace; o4 prefers udiff). Contest-refactor lets Critic+Actor write files however. For cross-provider robustness, `references/provider-adapters.md` could specify preferred edit format per provider.

**Defer.** Not a traceability issue — an edit-quality issue. Adopt only if specific provider edits fail.

### Gap E (P1, PROMOTED from defer): Repo-map via tree-sitter PageRank for cross-file traceability

**Promoted from defer per Gemini Pro peer review (round 1, B2):** the same model-bias-against-deterministic-structural-context that affected GOVERNANCE Gap D applies here. Aider's tree-sitter + NetworkX PageRank gives the Critic whole-codebase orientation no amount of on-demand `Read` calls can match in a 500-file repo. For traceability specifically: the repo-map identifies WHICH files are structurally central, informing `blast_radius` predictions and `changed_hunks[]` impact analysis.

**Adopt** as Step 0 sub-step 7d, sharing the AST infrastructure from GOVERNANCE Gap D (sub-step 7c). Both are post-lens activities (renumbered per Gemini round 2 B2):

```
7d. Build repo-map (mandatory when codebase >50 files OR --enable-repo-map flag). Renumbered per Gemini Pro round 2 (B2 chronological paradox): post-lens-detection activity belongs after sub-step 6 + 7 in contest-refactor SKILL.md Step 0 ordering.
    - Reuses tree-sitter parsers + AST graph from GOVERNANCE Gap D sub-step 7c
    - Computes PageRank over the symbol call-graph (Aider's algorithm)
    - Personalization weights: files referenced in CURRENT_REVIEW.json (prior loop) + files in working_tree_dirty_paths get 100/N boost
    - Output: top-50 ranked symbols/files written to `.contest-refactor/repo-map.md` (single mutable file; cache key per Codex round 1 B2 = same incremental scheme as GOVERNANCE Gap D import-graph; do NOT key on HEAD_SHA, would invalidate every loop)
    - Token budget: capped at 8192 tokens (Aider's 8x default when no files in chat)
    - Cache: same incremental key scheme as GOVERNANCE Gap D import-graph (per Codex round 2 N1 — earlier "HEAD SHA + personalization-set hash" was stale wording). Key = sha256(source-root file content) + sha256(personalization-set: files referenced in CURRENT_REVIEW.json prior loop + working_tree_dirty_paths). Incremental recompute on changed_paths[]; full rebuild on --rebuild-repo-map flag. NO HEAD_SHA in key.
```

**Schema additions** (additive, `schema_version: 4` — default-fill row per [SCHEMA-GAP § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5)):

```jsonc
{
  "governance_context": {                       // durable cross-loop container (per Codex round 1 N1 — repo-map is NOT first-loop-only)
    "repo_map_path": ".contest-refactor/repo-map.md",
    "repo_map_top_symbols": [
      {"symbol": "AppReducer.reduce", "path": "src/Reducer/AppReducer.swift", "rank": 0.087},
      {"symbol": "NavigationStore", "path": "src/Core/NavigationStore.swift", "rank": 0.064}
    ],
    "repo_map_fidelity": "ast",
    "repo_map_cache_key": "src_a8f3..."          // incremental cache key per Codex round 1 B2
  }
}
```

**Critic Phase consumes repo-map at Step 1 Method step 3** ("Review architecture. Module graph, Seams, Adapter variation, costume layers."). The repo-map is loaded into Critic's context as orientation, NOT authority. Findings can cite repo-map rank as supporting evidence (`"AppReducer is rank-1 by PageRank, touched by 17 callers"`) but the deletion-test + Two-adapter-rule + Authority-Map disciplines remain the actual rubric.

**Traceability win**: when populating `blast_radius{change[], avoid[]}` (per Step 1 emit), Critic uses repo-map's caller/callee graph to identify what `change[]` will ripple into. The current `blast_radius.avoid[]` field is Critic-judgment-only; repo-map makes it semi-mechanical.

**Validation gate** (no new G needed): G34 already covers `changed_hunks` accuracy; repo-map informs but doesn't enforce.

**Honest caveats preserved**: repo-map misses dynamic dispatch, reflection, runtime registration. Same as GOVERNANCE Gap D — the graph is **necessary not sufficient** orientation, never authority. Use `Cannot find 'X' in scope`-style narrow searches against actual source for high-stakes findings, not repo-map alone.

**Cost**: shares AST infrastructure with GOVERNANCE Gap D (one-time investment, two consumers). PageRank computation is O(N × iterations); subsecond on repos < 10k symbols.

## What contest-refactor already wins (do not regress)

1. **`blast_radius{change[], avoid[]}` predicted BEFORE edit** — stronger than the sampled PR-review tools' post-hoc traceability, and more structured than Aider's conversational planning.
2. **`pre_step3_blob_shas{path: blob_sha}` per-file narrow revert** — reviewer rejection restores exactly the loop's touched files, never user's pre-existing unstaged edits. Aider has no revert; PR-Agent only suggests.
3. **G22 commit subject with stable_id + status + registry summary** — every commit is parseable: `loop N: <verb>; finding F<n> (stable_id F-NNN) <status> [registry: +<n>, ~<n>]`. None of the three produce structured commit subjects.
4. **`findings_registry.json` occurrences[].sha + attempted_remedy_hash** — cross-loop causal chain ("F-007 was attempted at sha abc12, rejected; attempted again at sha def34, resolved"). Unique.
5. **Implementation Reviewer's three structured checks** (reality / honesty / regression) with verdict gate — stronger than PR-Agent's confidence-only self-reflection.
6. **Cross-loop fingerprint > file-set for re-review** — PR-Agent's `unreviewed_files_set` is file-based; contest-refactor's `fingerprint{claim_consequence_hash, evidence_paths_hash}` keys on the finding itself, not the file. Re-running on a modified file doesn't lose registry continuity.
7. **`targeted_finding_status` per loop** — explicit causal link finding→action→outcome. Aider's commit links to conversation, which decays on `/clear`.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Aider's chat-history-as-commit-context | Contest-refactor's G22 structured subject + CURRENT_REVIEW.md/.json artifacts are explicit; chat narrative decays. Don't trade structure for narrative. |
| PR-Agent's whole-PR compression algorithm | Designed for entire-PR-in-context constraint; contest-refactor's subagent-per-loop reads source on demand. Compression is unnecessary. |
| pr-review-toolkit's `[file:line]` string anchors | String parsing for line numbers is fragile and lossy. Contest-refactor's evidence[] structured strings are fine today; adding `start_line + end_line` (Gap A) is the right direction. |
| Aider's "edit means commit" auto-commit pattern | Contest-refactor's commit-after-Implementation-Reviewer pattern is safer. Aider trusts edits without verification — that's a feature for pair-programming, a bug for autonomous loops. |
| Inline GitHub PR comments | Contest-refactor is loop-driven, not PR-driven. PR integration would be opt-in P2; core stays local-first. |
| Aider's repo-map per session | Re-computing PageRank per loop is wasteful. If repo-map ever adopted (Gap E), it belongs in Step 0 once like lens selection — same lifecycle. |
| PR-Agent's incremental `unreviewed_files_set` | Contest-refactor's fingerprint-based registry is strictly more robust. Don't downgrade. |

## Adoption order

1. **Gap A (`changed_hunks[]` + canonical `hunk_id` + `tie_kind` enum + G34)** — closes the doc's P0 "every changed line maps to a finding ID" verbatim. New schema field + new gate. This is also the prerequisite shared hunk layer for HALT-STATE-GAP Gap C (per-hunk partial-accept). **Biggest single traceability win.**
2. **Gap F (cross-link PR-Agent's scoring as Schema Gap validator reference)** — zero new work; flag PR-Agent prompts as implementation reference when validator subagent ships.
3. **Gap B (`evidence[].context_window`)** — defer; revisit if Reviewer wastes tokens re-reading.
4. **Gap D (per-provider edit format)** — defer; provider-adapter polish.
5. **Gap E (repo-map)** — P1, PROMOTED from defer per Gemini Pro peer review (round 1, B2). Ships with GOVERNANCE-GAP Gap D (shared AST + tree-sitter infrastructure, one-time investment for two consumers). Critic loads as orientation NOT authority; blast_radius prediction becomes semi-mechanical via PageRank caller-graph.

## Minimal Step 3 diff for Gap A (the immediate win)

Today SKILL.md Step 3 sub-step 6 populates `loop_result.changed_paths[]` from `git diff --name-only HEAD`. Add sub-step 6.5:

> 6.5. **Populate `loop_result.changed_hunks[]`** by parsing `git diff -U0 HEAD` for the canonical hunk headers (`@@ -<old_start>,<old_size> +<new_start>,<new_size> @@`). For each hunk, the Implementation Reviewer subagent (already spawned in sub-step 6) assigns:
> - `hunk_id`: canonical per-loop hunk handle (`h1`, `h2`, ...) so later review / revert logic can reference the same unit.
> - `ties_to_finding_id`: the finding (this loop's `loop_local_id`) whose `evidence[]` or `minimal_correction_path` justifies this hunk. `null` if no finding justifies it.
> - `ties_to_stable_id`: optional cross-loop link via `findings_registry.json`.
> - `tie_kind`: enum (`remedy | regression_fix | follow_on_cleanup | mechanical | unmapped`).
> - `changed_line_count`: deterministic count used for the unmapped-percentage rule.
> - `rationale`: one sentence linking the hunk's diff to the tie. Required when `tie_kind ∈ {remedy, follow_on_cleanup, unmapped}`.
>
> Reviewer's regression-check explicitly enumerates hunks with `tie_kind: unmapped`. G34 (new) enforces ≤ 5% of changed-line count as `unmapped` unless `unmapped_hunks_explanation` is present.

Schema additions (additive, `schema_version: 4` — default-fill row per [SCHEMA-GAP § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5)):

```jsonc
{
  "loop_result": {
    // ... existing fields ...
    "changed_hunks": [
      {
        "hunk_id": "h1",
        "path": "src/Foo.swift",
        "old_start": 42, "old_size": 5,
        "new_start": 42, "new_size": 8,
        "changed_line_count": 8,
        "ties_to_finding_id": "F3",
        "ties_to_stable_id": "F-007",
        "tie_kind": "remedy",
        "rationale": "Collapsed redundant Optional-Adapter; matches F3 Two-adapter rule remedy."
      }
    ],
    "unmapped_hunks_explanation": null
  }
}
```

New `canon/tie-kinds.toml`:

```toml
# Hunk-to-finding tie kinds for loop_result.changed_hunks[].tie_kind.
tie_kinds = [
    "remedy",              # implements the targeted finding's minimal_correction_path
    "regression_fix",      # repairs a regression caused by this loop's remedy hunks
    "follow_on_cleanup",   # tied to a backlog (non-priority-1) finding
    "mechanical",          # rename/format/import-reorder forced by remedy
    "unmapped",            # not tied; requires hunk rationale and may need unmapped_hunks_explanation (≤5% of changed lines per G34)
]
```
