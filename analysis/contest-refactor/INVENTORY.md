# Competitor Inventory — contest-refactor comparison

**Location**: this inventory + all gap-analysis docs live under `analysis/contest-refactor/` (tracked by git). Competitor source clones live under `refs/competitors/` (gitignored, depth-1 git clones for source inspection). The two locations are paired but distinct: `analysis/` holds our derivative analysis; `refs/` holds upstream source.

**26 repos** cloned `depth=1` into `refs/competitors/` (gitignored) as of 2026-05-25 (22 original + 4 added 2026-05-25 after user surfaced missing-from-prior-research: archgate-cli, continuous-claude-v3, buildingopen-bouncer, jules-cli-ext). NOTFOUND: Edison, bug-detective, Agento-Patronum, emaarco/agento-patronum (separate fabrication, 2026-05-25), Jules (closed-source; jules-cli-ext is the CLI extension orchestrator only). See `CLAIM-DELTA-2026-05-25.md` for which gap docs are affected by the new clones.

## Skill-format competitors (have SKILL.md)

| Repo | SKILLs | Plugin | Doc grade | Why relevant |
|------|-------:|:------:|:---------:|--------------|
| `levnik-skills` | 137 | yes | B/C | Hash-verified editing, multi-model review, review schema with explicit file/line ranges |
| `trailofbits-skills` | 74 | yes | B | Security lens registry: `fp-check`, `differential-review`, `variant-analysis`, SARIF/static-analysis |
| `gstack` | 57 | no | B/C | Stage-gate workflow, QA/docs commands |
| `open-code-review` | 32 | yes | B | Multi-agent critic-independence with 28 reviewer personas |
| `mattpocock-skills` | 28 | yes | B/C | TDD, diagnose, to-issues, to-prd — vocabulary extraction |
| `superpowers` | 14 | yes | B/C | Red-Green-Refactor enforcement, worktree isolation |
| `great_cto` | 13 | yes | B/C | 8-specialist SDLC, 13 compliance frameworks |
| `anthropic-claude-code` | 10 | n/a | A/B | Official `code-review` plugin: parallel agents, confidence scoring (`plugins/code-review/`) |
| `skills-janitor` | 9 | yes | B/C | Jaccard overlap audit for skill packs |
| `brooks-lint` | 6 | yes | B/C | Symptom→Source→Consequence→Remedy, 12-book grounding |
| `logic-lens` | 6 | yes | B/C | Premises→Trace→Divergence→Remedy execution traces |
| `prism` | 3 | yes | B/C | Session intelligence: token cost + CLAUDE.md adherence |
| `coderabbit-skills` | 2 | yes | B | Severity-grouped findings, fix + re-review loop |
| `domscribe` | 1 | yes | C/B | MCP runtime DOM/props/state via React fiber / Vue VNode |

## CLI / tool competitors (no SKILL.md — read source/README)

| Repo | Doc grade | Why relevant |
|------|:---------:|--------------|
| `aider` | B | Repo map, auto-commit, lint/test loop, fix linter+test failures |
| `plandex` | B | Plan branching, diff sandbox, command-debug, 2M context, tree-sitter maps |
| `goose` | B | Agent framework, autonomous execution/edit/tool modes |
| `pr-agent` | B | `/review` `/improve`, PR compression, dynamic context, self-reflection, multi-provider |
| `sweep` | C | Issue→PR automation (tapered activity) |
| `agentlint` | B | Linter for CLAUDE.md / AGENTS.md / hooks; Stop-hook circuit-breaker checks |
| `claude-bouncer` | B | Pattern-level PreToolUse enforcement via executable hooks |
| `architecture-review-mcp` | C | MCP: class/service/data-flow diagrams, dep analysis |

## Strategic anchors (from doc § 1, § 6)

`contest-refactor` should import — every import maps to a competitor to inspect:

| Priority | Mechanism | Inspect first |
|----------|-----------|---------------|
| P0 | Evidence-linked finding schema | `coderabbit-skills`, `anthropic-claude-code/plugins/code-review`, `trailofbits-skills`, `levnik-skills` |
| P0 | Critic independence gate | `open-code-review`, `anthropic-claude-code/plugins/code-review`, `levnik-skills` |
| P0 | Executable governance ingestion | `brooks-lint`, `architecture-review-mcp` |
| P0 | Changed-line traceability | `pr-agent`, `aider`, `anthropic-claude-code/plugins/pr-review-toolkit`, `levnik-skills` |
| P1 | Forced-completion gates | `trailofbits-skills/plugins/fp-check`, `claude-bouncer`, `agentlint` |
| P1 | Context ledger | `prism`, `plandex` (plan state) |
| P1 | Risk-triggered external lenses | `trailofbits-skills`, `agentlint`, `claude-bouncer` |
| P2 | Clean-environment validation | `goose`, `sweep` |
| P2 | Adoption-signal tracking | marketplace/install metadata consumers (not yet analyzed in the six gap docs) |

## Gap-analysis docs in this folder

### Original six (first pass)

1. [`SCHEMA-GAP-CONTEST-REFACTOR.md`](SCHEMA-GAP-CONTEST-REFACTOR.md) — Evidence-linked finding schema
2. [`CRITIC-INDEPENDENCE-GAP.md`](CRITIC-INDEPENDENCE-GAP.md) — Critic independence gate
3. [`GOVERNANCE-GAP.md`](GOVERNANCE-GAP.md) — Executable governance ingestion
4. [`TRACEABILITY-GAP.md`](TRACEABILITY-GAP.md) — Changed-line traceability
5. [`HALT-STATE-GAP.md`](HALT-STATE-GAP.md) — Halt taxonomy / checkpoint state
6. [`GATES-GAP.md`](GATES-GAP.md) — Forced-completion gates

### Synthesis + delta passes

- [`RESEARCH-DELTA.md`](RESEARCH-DELTA.md) — Per-doc deltas after inspecting 8 missed competitors (claude-review-loop, ralph-wiggum, awesome-code-review, cygnusfear-stuff, grill-for-claude, rohitg00-toolkit, forensic-skills, anthropic-security-review) + finally opening mattpocock-skills/improve-codebase-architecture
- [`LEVNIK-AUDIT-SUITE-GAP.md`](LEVNIK-AUDIT-SUITE-GAP.md) — Deep probe of levnik's 35+ specialty worker audit-suite (orchestrator-worker-coordinator pattern)
- [`STATE-MACHINE-COMPOSITION-APPENDIX.md`](STATE-MACHINE-COMPOSITION-APPENDIX.md) — Unified end-to-end state machine sequencing 4 new intercept points (Parallel Critics + Synthesis, Validator Subagent, Cross-Model Critic, Clean-Env Revalidation) per Gemini Pro peer review round 1 (B1). Resolves race conditions + token-budget concerns; adds G45+G46+G47 + `canon/loop-phases.toml`.
- [`REVIEW-PROMPT.md`](REVIEW-PROMPT.md) — Copy-paste prompt for cross-LLM peer review of all gap docs

### New gap docs from this pass

| File | Topic | Priority |
|---|---|---|
| [`CROSS-MODEL-CRITIC-GAP.md`](CROSS-MODEL-CRITIC-GAP.md) | Cross-model adversarial critic (Claude actor + Codex critic) via Stop-hook architecture | P1 |
| [`SPECIALTY-LENS-DISPATCH-GAP.md`](SPECIALTY-LENS-DISPATCH-GAP.md) | Risk-triggered specialty lens dispatch (merges Risk-Triggered-Lenses + Specialty-Lens-Dispatch) | P0 |
| [`TWO-LAYER-DETECTION-GAP.md`](TWO-LAYER-DETECTION-GAP.md) | Formalize Layer 1 grep + Layer 2 context verify as Method rule | P0 |
| [`ARXIV-AGENTIC-REFACTORING-GAP.md`](ARXIV-AGENTIC-REFACTORING-GAP.md) | Empirical falsifier — Horikawa et al. 2025 finding agents do mostly low-level refactors; positioning response | P0 |
| [`SKILL-TDD-FIXTURES-GAP.md`](SKILL-TDD-FIXTURES-GAP.md) | Bad-codebase + expected-refactor fixtures as skill evals; closes the "major moat" gap | P0 |
| [`ROI-PRIORITIZATION-GAP.md`](ROI-PRIORITIZATION-GAP.md) | Forensic-skills' hotspot × complexity formulas for backlog ordering | P1 |
| [`CLEAN-ENVIRONMENT-VALIDATION-GAP.md`](CLEAN-ENVIRONMENT-VALIDATION-GAP.md) | `--clean-validate-before-halt` opt-in worktree validation before HALT_SUCCESS | P1 |
| [`PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP.md`](PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP.md) | Per-critic JSON+MD split artifact contract (gated on CRITIC-INDEPENDENCE Gap B parallel critic mode) | P1 |
| [`ADOPTION-SIGNAL-TRACKING-GAP.md`](ADOPTION-SIGNAL-TRACKING-GAP.md) | Meta-discipline: separating quality rank from adoption rank; vendor-self-published flagging | P2 |
| [`DOMAIN-AWARE-SCANNING-GAP.md`](DOMAIN-AWARE-SCANNING-GAP.md) | Multi-domain monorepo scanning (STUB — defer indefinitely; `--scope` workaround sufficient) | P2 |

### Coverage map: landscape mechanism → gap doc

| Mechanism (per landscape doc) | Gap doc(s) |
|---|---|
| Evidence-linked finding schema | SCHEMA-GAP (incl. Gap 7 positive-finding from grill) |
| Critic independence gate | CRITIC-INDEPENDENCE + CROSS-MODEL-CRITIC + PARALLEL-CRITIC-ARTIFACT-CONTRACT |
| Executable governance ingestion | GOVERNANCE |
| Changed-line traceability | TRACEABILITY |
| Halt taxonomy / checkpoint state | HALT-STATE |
| Forced-completion gates | GATES + TWO-LAYER-DETECTION |
| Risk-triggered external lenses (P1) | SPECIALTY-LENS-DISPATCH |
| Clean-environment validation (P2) | CLEAN-ENVIRONMENT-VALIDATION |
| Adoption-signal tracking (P2) | ADOPTION-SIGNAL-TRACKING |
| Context ledger (P1) | covered in HALT-STATE-GAP (LOOP_STATE + checkpoint mechanics) |
| ROI / backlog prioritization | ROI-PRIORITIZATION |
| Skill-TDD with fixtures (research's "major moat") | SKILL-TDD-FIXTURES |
| Empirical falsifier (arXiv:2511.04824) | ARXIV-AGENTIC-REFACTORING |
| Specialty audit-suite architecture (levnik) | LEVNIK-AUDIT-SUITE |

All mechanisms from the landscape research now have dedicated gap docs. Multi-domain scanning is documented as deferred (stub doc).

## What NOT to import (doc § 7)

50-agent org chart, parallel editors, always-on deep security review, universal "no-delete-without-failing-test" rule, cloud-VM-mandatory validation, markdown-only findings, parent-repo-stars-as-skill-stars conflation, literature decoration, generic senior-engineer prompts.
