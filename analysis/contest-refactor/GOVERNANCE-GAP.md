# Executable Governance Ingestion Gap — contest-refactor vs P0 competitors

Compares contest-refactor's governance ingestion (Step 0 Context Discovery + `.contest-refactor.toml` + lens system + ADR awareness per `references/method.md`) against:

- **brooks-lint** (`refs/competitors/brooks-lint/`) — 12-book grounded analysis with `.brooks-lint.yaml` config + module graph from grep
- **architecture-review-mcp** (`refs/competitors/architecture-review-mcp/`) — MCP server with AST-based NetworkX dependency + class graphs
- **archgate-cli** (`refs/competitors/archgate-cli/`, 38★, Apache-2.0) — **operational prior art** for executable governance: markdown ADRs (`.archgate/adrs/DOMAIN-NNN-title.md`) paired 1:1 by basename with `.rules.ts` companion files that export `RuleSet` objects checked at CI / pre-commit. Added 2026-05-25 per CLAIM-DELTA after user-surfaced miss. Materially affects Gap C framing below.

## Baseline: contest-refactor today

**Step 0 Context Discovery (first loop only, main agent):**
1. Scans CWD for source roots
2. Finds test/build commands from manifests (package.json, Makefile, Cargo.toml, Package.swift, pyproject.toml, etc.)
3. Reads `CONTEXT.md` / `CONTEXT-MAP.md` → records domain vocabulary; findings must use domain terms ("Order intake module", not "OrderHandler")
4. Enumerates `docs/adr/` → ADR titles; findings that contradict an ADR must populate `adr_conflicts[]` + `adr_reopen_justification`
5. Detects stack → loads `references/lens-apple.md` or `references/lens-generic.md`

**`.contest-refactor.toml`:**
- `defaults` (lens, loop_cap, test_command)
- `ignore[]` globs (downgrade findings on generated/vendored)
- `[[accepted_residuals]]` with **MANDATORY** `expires` date; validators enforce; expired residuals can't satisfy HALT_SUCCESS

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent.

| Mechanism | contest-refactor | brooks-lint | architecture-review-mcp | archgate-cli |
|---|:--:|:--:|:--:|:--:|
| Project config file | ✓ `.contest-refactor.toml` | ✓ `.brooks-lint.yaml` | — | ✓ `.archgate/` dir |
| Domain vocabulary from CONTEXT.md | ✓ enforced in findings | partial (CLAUDE.md implied) | — | partial (ADR `domain` field, kebab-case enum) |
| ADR enumeration | ✓ `docs/adr/` | — | — | ✓ `.archgate/adrs/DOMAIN-NNN-*.md` (YAML frontmatter required) |
| **Per-finding ADR citation + reopen justification** | ✓ `adr_conflicts[]` + `adr_reopen_justification` | — | — | partial (violation cites `adrId` + `ruleId`; no reopen-justification field) |
| **Accepted-residual with MANDATORY expiry** | ✓ validator-enforced | partial (suppressions with `expires`) | — | — |
| Trend-tracking history | partial (REVIEW_HISTORY.json loop-keyed) | ✓ `.brooks-lint-history.json` time-keyed | — | — |
| Stack detection → lens | ✓ apple / generic | partial (language detection) | partial (parser per lang) | — (language-agnostic) |
| Package manifest read | ✓ (test/build commands) | ✓ (lang + top deps) | — | — |
| **Lint config ingestion** (`.swiftlint.yml`, `.eslintrc`, `ruff.toml`, etc.) | **—** | **—** | — | — |
| **CI workflow ingestion** (`.github/workflows/`) | **—** | **—** | — | partial (CI is consumer of archgate, not ingester) |
| **Boundary-rule config** (declared layers / forbidden imports) | **—** | — (heuristic only) | — (hard-coded "circular = bad") | **✓ executable** — `.rules.ts` companion per ADR; `RuleSet` exports async `check(ctx)` functions; sandboxed APIs: `ctx.glob/grep/readFile/readJSON`, `ctx.scopedFiles`, `ctx.changedFiles` |
| Import-graph construction | — (Critic reasons mentally) | partial (greps first 200/lang) | ✓ AST-based, NetworkX | — (rules use grep/regex; no whole-repo graph) |
| Class-graph construction | — | — | ✓ inheritance + composition | — |
| Call-graph construction | — | — | — | — |
| Circular dependency detection | — | ✓ Mermaid dotted edges, R5 | ✓ NetworkX SCC | partial (project must encode as a `.rules.ts` check) |
| Fan-out > N threshold warning | — | ✓ > 5 | — | partial (project must encode as a `.rules.ts` check) |
| Per-violation citation to **local rule source** | partial (ADR title) | — (book only) | — (module names only) | **✓ structured** — `{file, line, endLine, endColumn, ruleId, adrId, severity, fix}` JSON output |
| Hard-coded book/lens citation | ✓ lens .md | ✓ 12 books | — | — (ADRs ARE the rules; no separate canon) |
| Machine-readable output | partial (CURRENT_REVIEW.json) | — | — | ✓ `--json` (structured `results[]`) + `--ci` (GH Actions annotations) |
| CI / pre-commit integration | partial (autonomous loop, not hook-driven) | — | — | ✓ `archgate check` (CI) + `archgate check --staged` (pre-commit); exit 0/1/2/130 disciplined |
| LICENSE | ✓ MIT (this repo) | — | — | ✓ Apache-2.0 |

## Strategic insight

Contest-refactor leads on **rule-of-record citation discipline plus reopen-justification + expiring-residual machinery**: `adr_conflicts[] + adr_reopen_justification` + validator-enforced `[[accepted_residuals]].expires` are absent in every competitor including archgate. Brooks-lint cites Fowler/Hunt/Beck but never cites `.brooks-lint.yaml` line N or `architecture-guide.md § 2 Rule 6` — its findings have no local-rule traceback. The first draft also overstated the architecture-review-mcp comparison: the checked source stores `line_number` on dependency edges from parsed imports, so "never the import line that closes the cycle" was too strong.

**archgate-cli (added 2026-05-25) is operational prior art for executable governance** — it implements the doc § 1 P0 ask verbatim, in production, with CI + pre-commit + agent integration. The Gap C section below was rewritten to reflect this: contest-refactor is NOT inventing executable governance, it is choosing between two strategies — adopt archgate's `.rules.ts` companion-file pattern (executable TS, sandboxed APIs) OR consume archgate output as a Step 0 ingestion source. The "executable" half is solved; contest-refactor's remaining contribution is rule-citation + reopen-justification + expiring-residual + accepted-residual discipline layered over enforcement output.

Where contest-refactor lags is in **the breadth of project artifacts it ingests**. The doc's `§ 1` P0 ask spells this out: *"Parse ADRs, CI, boundary scripts, package graphs, lint configs, and rule files."* Today contest-refactor parses ADRs + manifests-for-test-commands only.

## P0 GAPS — what to import

### Prerequisite: persistent `governance_context` container (before A/B/C)

Do **not** put new governance payloads under `discovery`. In the checked schema, `discovery` is required on loop 1 and `null` on later loops. Any field that needs to survive across loops (`local_lint_overrides`, `ci_binding_rules`, `boundary_rules`, future gate overrides) needs a separate top-level durable container, for example:

```jsonc
{
  "governance_context": {
    "local_lint_overrides": {},
    "ci_binding_rules": [],
    "boundary_rules": []
  }
}
```

Step 0 seeds this once; later loops carry it forward unless repo config changes are detected. Without this prerequisite, Gaps A/B/C all break existing lifecycle invariants.

### Gap A: Lint config ingestion (Critic-noise reducer)

When `.swiftlint.yml` says `disabled_rules: [trailing_whitespace]` or `.eslintrc.json` says `"no-console": "off"`, those are **executive decisions by the project**. A Critic flagging trailing whitespace or `console.log` against an explicitly-disabled rule is adversarial noise.

**Adopt:** Step 0 reads, per active lens:

- **Apple lens:** `.swiftlint.yml`, `.swiftformat`, `Package.swift` (test products)
- **Generic lens:** `.eslintrc.*` / `eslint.config.*`, `biome.json`, `ruff.toml`, `pyproject.toml [tool.ruff]`, `.rubocop.yml`, `.golangci.yml`, `clippy.toml`

Record the disabled-rule list in `CURRENT_REVIEW.json.governance_context.local_lint_overrides`.

Two important limits:

1. Mere `evidence[] = ["path:line"]` is not enough for a deterministic Python validator to prove "this finding only matches a locally-disabled lint rule."
2. If contest-refactor wants machine-checkable linkage here, findings need an explicit rule reference such as `lint_rule_id` / `governance_rule_ref`.

So the immediate win is **ingestion + reviewer/validator guidance**, not a new hard Python gate. A future validator subagent can decide whether a finding escalates beyond a disabled local lint rule.

**Cost:** Step 0 addition plus a durable governance container. Small parser lift; medium schema/lifecycle lift.

### Gap B: CI workflow ingestion (severity-escalation signal)

`.github/workflows/*.yml` (and `.gitlab-ci.yml`, `azure-pipelines.yml`) declare what the project considers binding. If CI runs `swift test --enable-thread-sanitizer` but the loop's local test_command doesn't, a concurrency finding should **escalate** severity — the local pass is a weaker oracle than the CI gate.

**Adopt:** Step 0 reads workflow files; extracts:
- which CI jobs run lint / test / build / security-scan
- which flags are mandatory (sanitizers, strict modes, fail-on-warning, fail-on-vuln)
- which steps are blocking vs advisory (`continue-on-error: true` markers)

Record in `CURRENT_REVIEW.json.governance_context.ci_binding_rules[]`. Step 0.4 test_command validation can warn if the local command lacks mandatory CI flags, but any severity promotion still belongs to Critic/validator reasoning rather than `validate-artifact.py`.

**Cost:** YAML parser + per-provider config-extractor (GH Actions vs GitLab CI) + durable governance container.

### Gap C: Boundary-rule config (executable governance — archgate prior-art reframing per CLAIM-DELTA 2026-05-25)

**Prior-art reframing**: the original draft positioned this as the doc § 1 P0 "flagship invention" for contest-refactor. archgate-cli (38★, Apache-2.0) ships this mechanism in production. The decision is no longer **whether** to adopt executable governance, but **how**: build TOML-declarative rules in contest-refactor's own config, OR consume archgate's `.rules.ts` output, OR adopt archgate's pattern verbatim.

**Reference mechanism (archgate)** — sourced from `refs/competitors/archgate-cli/src/formats/rules.ts:67-90` + `src/formats/adr.ts:31-45` + `src/commands/check.ts:22-157`:

- ADR markdown at `.archgate/adrs/DOMAIN-NNN-title.md` with required YAML frontmatter (`id`, `title`, `domain`, `rules:bool`, optional `files[]` glob array, optional `respectGitignore:bool`); body free-form
- Companion file `.archgate/adrs/DOMAIN-NNN-title.rules.ts` paired by exact basename, exports `RuleSet`:
  ```typescript
  export type RuleSet = { rules: Record<string, RuleConfig> };
  interface RuleConfig {
    description: string;
    severity?: "error" | "warning" | "info";  // default "error"
    check: (ctx: RuleContext) => Promise<void>;
  }
  ```
- `RuleContext` provides sandboxed APIs: `projectRoot`, `scopedFiles` (frontmatter `files[]` resolved), `changedFiles` (auto-detected branch diff; with `--staged`, staged only), `glob(pattern)`, `grep(file, RegExp)`, `readFile(path)`, `readJSON(path)`. **No exec / spawn** — rules cannot run shell commands (sandbox limit documented at `src/formats/rules.ts`).
- Violations reported via side-effect: `ctx.report.violation({message, file?, line?, endLine?, endColumn?, fix?})` (also `warning` + `info`).
- Output: `--json` (structured `results[]` with `{file, line, ruleId, adrId, message, severity, fix}`) or `--ci` (GitHub Actions annotations) or default human-readable.
- Exit codes: 0 pass / 1 violations / 2 internal error / 130 SIGINT (disciplined per archgate ADR ARCH-002).
- CI: `archgate check`. Pre-commit: `archgate check --staged`.

**Decision-fork for contest-refactor** — user directive 2026-05-25: minimize external prereqs. Default = **C.2 TOML-declarative** (no archgate dep). C.3 hybrid = opt-in interop only; C.1 full-adopt = dropped.

| Strategy | Pros | Cons | Verdict |
|---|---|---|---|
| ~~C.1: Adopt archgate~~ (consume `.archgate/` as runtime dep) | Zero invention; production-grade | Adds external runtime prereq; couples contest-refactor to archgate evolution | **DROPPED** per user directive 2026-05-25 (keep prereqs minimal) |
| **C.2: TOML-declarative rules in `.contest-refactor.toml`** | Stays in-skill; no external dep; declarative-only = no arbitrary code execution; pairs with contest-refactor's existing `[[accepted_residuals]]` discipline | Limited expressiveness (regex/glob only; no AST queries beyond Gap D import graph) | **DEFAULT** |
| C.3: Hybrid — opportunistically ingest archgate output if `.archgate/` directory detected AND user opts in via flag | Zero-cost interop for archgate-using projects; no runtime dep added unless project already has archgate | Two parallel schemas; doc burden; subprocess invocation surface | Opt-in only (`--ingest-archgate` flag, default off) |

**Recommended**: **C.2** (TOML-only). Step 0 sub-step 7e loads TOML `[[boundary_rules]]` if declared into `governance_context.boundary_rules[]`. Finding `boundary_rule_id` field uses `toml:rule-id-slug` source prefix. archgate stays in this doc strictly as **prior-art reference + honest-comparison comparator**, NOT as recommended dependency.

C.3 stays documented as opt-in for users whose project already runs archgate independently of contest-refactor. Implementation: `--ingest-archgate` flag triggers `archgate check --json` subprocess when `.archgate/` is detected, parses output into `governance_context.archgate_violations[]`. Default off; no runtime dep introduced for the default code path.

**TOML-declarative rules** (C.2 fallback for archgate-less projects):

```toml
[[boundary_rules]]
id = "domain-no-ui"
from_pattern = "src/Domain/**"
imports_forbidden = ["src/UI/**", "src/Networking/**"]
reason = "Domain layer is pure"
adr_ref = "docs/adr/0003-pure-domain.md"

[[boundary_rules]]
id = "ui-no-direct-network"
from_pattern = "src/UI/**"
imports_forbidden = ["src/Networking/Transport/**"]
imports_via = ["src/UI/ViewModels/**"]   # must route through this layer
reason = "Views read from ViewModels only"
adr_ref = "docs/adr/0007-mvvm-boundary.md"
```

Step 0 loads `boundary_rules[]` into `governance_context.boundary_rules[]`. Method step 3 ("Review architecture") includes boundary-violation check. Violations emit a finding with `adr_conflicts: ["ADR-0003"]` auto-populated from the rule's `adr_ref`, and the `boundary_rule_id: "toml:domain-no-ui"` field links the finding back to the rule.

**contest-refactor still owns these layers archgate doesn't**:

1. **Reopen justification** — archgate violations cite `adrId` but have no `adr_reopen_justification` requirement when re-raising a previously-decided issue. contest-refactor's Critic Phase enforces this.
2. **Accepted-residual with mandatory expiry** — archgate has no `expires` semantics on suppressions; contest-refactor's `[[accepted_residuals]]` + HALT_SUCCESS validator gate is unique.
3. **Cross-loop fingerprint identity** — archgate runs check-per-invocation, no `findings_registry.json` equivalent; contest-refactor tracks finding stable IDs across loops.

These layers stay in contest-refactor regardless of C.1/C.2/C.3 choice.

Big lift — for C.2/C.3, requires a lightweight import-extractor per lens (regex is acceptable; AST is gold-plating per Gap D). For C.1/C.3, requires `archgate check` subprocess detection + JSON output parser.

**Cost:** New canon file `canon/boundary-rule-shape.toml` (covers both `toml:` and `archgate:` source prefixes). New `governance_context.boundary_rules[]` + `governance_context.archgate_violations[]` ingestion (C.3 only). New finding field `boundary_rule_id`. If a new hard gate is added, keep it **structural**: "Finding with `boundary_rule_id` populated MUST have `adr_conflicts[]` non-empty AND consistent with the rule's `adr_ref`." Do not ask `validate-artifact.py` to infer boundary semantics from prose.

### Gap D (P1, PROMOTED from defer): Import graph for executable boundary verification

**Promoted from defer per Gemini Pro peer review (round 1, B2):** for an architecture-first refactoring loop targeting enterprise codebases (≥500 files), the Critic cannot reliably detect deep circular dependencies, layer-crossing violations, or fan-out hotspots through grep + context-window memory alone. Deferring the only deterministic mechanism for whole-repo structural truth contradicts contest-refactor's positioning.

architecture-review-mcp builds NetworkX-backed dep + class graphs from AST. Brooks-lint does grep-based shallow version (first 200 imports/lang). Tree-sitter via aider's repo-map provides language-coverage breadth.

**Adopt** as Step 0 sub-step 7c (renumbered per Gemini Pro peer review round 2, B2: original "5c after lens detection (sub-step 6)" violated sequential ordering). Sub-step 7 in contest-refactor SKILL.md today is "Record commands, source roots, ADRs, domain terms, selected lens at top of `CURRENT_REVIEW.md`"; new 7a/7b/7c/7d/7e/7f/7g sub-steps follow as post-lens-detection activities:

```
7c. Build import graph (mandatory when boundary_rules[] non-empty OR codebase >100 files).
    - Tool dispatch per lens:
      - lens-apple: tree-sitter-swift via grep-ast OR swift package show; fallback to `swift build --print-modules`
      - lens-generic: per-language AST parser registry (Python ast, JS/TS tree-sitter, Go go/ast, etc.)
    - Output: NetworkX DiGraph serialized to `.contest-refactor/import-graph.json` (single mutable file, not SHA-suffixed — see Cache below)
    - Compute: strongly_connected_components (cycles), fan_out_per_node, fan_in_per_node
    - Cache (per Codex round 1 B2 — contest-refactor commits every loop per G22, so HEAD_SHA-only cache invalidates every loop, defeats the cache):
      - Cache key = sha256(concatenated content hashes of all source files matching source_roots + sha256(governance config sections boundary_rules/ignore/scope))
      - INCREMENTAL recompute: when `loop_result.changed_paths[]` from prior loop intersects source_roots AND `--no-graph-cache` flag not set, recompute graph for affected subgraph only (paths in changed_paths[] + their direct neighbors); merge into cached graph. Full rebuild only on `--rebuild-graph` flag OR when no prior graph exists OR when governance config sections change.
      - Stale-on-commit problem solved: HEAD_SHA changes don't invalidate; content of source roots changes selectively, so most loops do <5% recompute work.
    - Failure mode: when no AST parser available for detected stack, fall back to grep-based shallow graph with `graph_fidelity: "shallow"` flag in discovery. Don't block the loop.
```

**Schema additions** (additive, `schema_version: 4`):

```jsonc
{
  "governance_context": {
    "import_graph": {
      "head_sha": "abc1234",                  // SHA at graph-compute time (audit only, NOT cache key — see cache_key)
      "cache_key": "src_a8f3...+cfg_f9e3d2",  // INCREMENTAL composite hash per Codex round 1 B2: sha256(concatenated content of source-root files) + sha256(.contest-refactor.toml boundary_rules/ignore/scope). Recompute incremental on changed_paths[] intersect source_roots; full rebuild only on --rebuild-graph OR governance config change. Decouples cache from HEAD_SHA so commit-per-loop doesn't thrash the cache.
      "last_incremental_recompute_paths": ["src/Auth/TokenStore.swift"],  // audit field: paths that triggered the last partial recompute
      "graph_fidelity": "ast",                // enum: ast | shallow | unavailable
      "path": ".contest-refactor/import-graph-abc1234.json",
      "stats": {
        "nodes": 247,
        "edges": 1430,
        "strongly_connected_components": [
          ["src/Domain/Order.swift", "src/UI/OrderViewModel.swift"]
        ],
        "high_fanout_nodes": [
          {"path": "src/Coordinator.swift", "fan_out": 23}
        ]
      },
      "computed_at": "2026-05-25T13:00:00Z"
    }
  }
}
```

**Method step 5b extension** (boundary-rule enforcement gains graph teeth): when `governance_context.boundary_rules[]` non-empty AND `governance_context.import_graph` available, Critic verifies each boundary rule against the graph BEFORE emitting findings. Graph-confirmed violations get `confidence: high` automatically (per SCHEMA-GAP Gap 1). Graph-disagreement-with-boundary-rule = open-question to user (cannot silently override the graph).

**New validation gate G44**: When `governance_context.boundary_rules[]` non-empty AND `governance_context.import_graph.graph_fidelity == "ast"`, every emitted boundary-violation finding MUST cite the graph edge (source path → target path) in `evidence[]`. Graph-unable-to-verify boundary findings = downgrade to `confidence: medium` + explicit prose in `severity_rationale`.

**Honest caveats preserved**: graphs miss dynamic dispatch, reflection, lazy import, factory registry, runtime metaprogramming. The graph is **necessary not sufficient** evidence. Gate G44 only escalates `confidence` when the graph CONFIRMS; it doesn't override Critic judgment on cases the graph misses.

**Cost**: per-language AST parser dependency. Defer pluggable parser-registry to v5 of `provider-adapters.md`. Initial scope: lens-apple uses tree-sitter-swift (already standard); lens-generic ships Python + JS/TS + Go parsers; other languages fall back to shallow grep.

### Gap E: Trend dashboard (defer)

brooks-lint's `.brooks-lint-history.json` is optimized for time-keyed cross-month rendering. Contest-refactor's `REVIEW_HISTORY.json` is loop-keyed.

**Recommendation:** defer. REVIEW_HISTORY satisfies the autonomous loop's own delta logic. Cross-month human-facing dashboard is reporting, not loop input — out of scope.

## What NOT to import

| Tempting | Why skip |
|---|---|
| brooks-lint's book-only citation model | "Fowler — Shotgun Surgery" without local-rule citation is exactly what the doc warns against ("literature citations as decoration"). Contest-refactor's `test_failed` enum + `boundary_rule_id` (Gap C) is the correct direction. |
| architecture-review-mcp's "circular = always bad" hard-coding | Some circular deps are intentional (mutual recursion across types). Boundary-rule config (Gap C) lets the project declare which cycles are tolerated. |
| Grep-based shallow import graph (brooks-lint) | Mixes false positives (string mentions) with real imports. AST-based is the right move if a graph is ever needed (Gap D). |
| MCP-server architecture (architecture-review-mcp) | External MCP server adds deployment surface contest-refactor doesn't need. In-skill Python script or Critic-LLM reasoning is sufficient. |
| Full class-graph + data-flow diagrams | Out of scope for refactor-loop findings; useful for human onboarding only. |
| GitHub-Actions-only CI parsing | When adopting Gap B, support GH Actions + GitLab CI + Azure Pipelines minimally. Skip provider-specific exotic syntax. |

## Where contest-refactor is already strong (do not regress)

1. **ADR-aware findings with reopen justification** — `adr_conflicts[]` + `adr_reopen_justification` has no equivalent in brooks-lint, architecture-review-mcp, OR archgate-cli (archgate cites `adrId` per violation but has no reopen-justification requirement when re-raising a previously-decided issue)
2. **Accepted-residual MANDATORY expiry date** — validator-enforced; brooks-lint's `expires` is per-finding suppression, archgate has no `expires` semantics at all; contest-refactor's `[[accepted_residuals]]` + HALT_SUCCESS validator gate is structurally unique
3. **CONTEXT.md domain vocabulary enforcement** — findings must use project terms, not generic class names
4. **Validator catches expired residuals at HALT_SUCCESS** — concrete enforcement, not advisory
5. **Lens system** (apple / generic) — stack-aware analysis without per-language re-tooling
6. **Cross-loop fingerprint identity** — `findings_registry.json` with stable IDs across loops; archgate runs check-per-invocation with no cross-run identity layer

## Adoption order

1. **Prerequisite: add a durable `governance_context` container** — otherwise A/B/C collide with the first-loop-only `discovery` lifecycle.
2. **Gap C — DECIDE strategy first (C.1 adopt archgate / C.2 TOML-only / C.3 hybrid)** before scoping the work. C.3 hybrid is recommended: ingest `archgate check --json` output when `.archgate/` present + ship TOML `[[boundary_rules]]` fallback for archgate-less projects. The original "flagship P0 invention" framing is retired per archgate prior art; the contribution is now reopen-justification + accepted-residual + cross-loop identity layered over whichever enforcement source.
3. **Gap A (lint config ingestion)** — useful, but not a "quick win" once lifecycle and per-finding rule linkage are accounted for.
4. **Gap B (CI workflow ingestion)** — useful severity context after the durable container exists.
5. **Gap D (import graph)** — P1, PROMOTED from defer per Gemini Pro peer review. Ships after Gap C lands; if C.1 or C.3 chosen, archgate's `ctx.grep`/`ctx.glob` rules can compute much of this graph too, but a contest-refactor-internal graph still pays off for non-archgate users. Pairs with TRACEABILITY-GAP Gap E (shared AST infrastructure). Add G44 gate.
6. **Gap E (trend dashboard)** — defer indefinitely; out of scope.

## Minimal Step 0 diff for Gap A (the immediate win)

Today SKILL.md Step 0 sub-step 5 reads CONTEXT.md and docs/adr/; sub-step 6 detects lens; sub-step 7 records discovery. Add post-lens sub-step 7a (per Gemini round 2 B2 paradox fix — post-lens activities must follow sub-step 6 numerically):

> 7a. **Read local lint/format overrides** per active lens. Sub-step 6 detects the lens; 7 records discovery; this sub-step 7a runs after both, so the active lens is known.
>
> - **Apple lens:** `.swiftlint.yml`, `.swiftformat` (if present at repo root)
> - **Generic lens:** `.eslintrc.*` / `eslint.config.*`, `biome.json`, `ruff.toml`, `pyproject.toml` `[tool.ruff]` section, `.rubocop.yml`, `.golangci.yml`, `clippy.toml` — read only those matching the detected language
>
> Extract the disabled-rule list (`disabled_rules:`, `"rule": "off"`, `disable = [...]`) and record in `CURRENT_REVIEW.json.governance_context.local_lint_overrides: {<config-path>: [<rule-id>, ...]}`. The Critic should treat this as context: findings whose only basis is a locally-disabled rule need explicit structural justification, but that judgment belongs to Critic / validator reasoning, not deterministic artifact validation.

Do **not** add a hard Python gate yet. First decide whether findings need an explicit `lint_rule_id` / `governance_rule_ref` field so the linkage is machine-checkable.

Schema additions (additive, `schema_version: 4`):

```jsonc
{
  "governance_context": {
    "local_lint_overrides": {
      ".swiftlint.yml": ["trailing_whitespace", "line_length"],
      ".swiftformat": ["wrapMultilineStatementBraces"]
    },
    "ci_binding_rules": [],         // populated by Gap B
    "boundary_rules": []            // populated by Gap C
  }
}
```
