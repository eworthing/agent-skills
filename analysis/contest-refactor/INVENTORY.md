# Competitor Inventory — contest-refactor comparison

**Location**: this inventory + all gap-analysis docs live under `analysis/contest-refactor/` (tracked by git). Competitor source clones live under `refs/competitors/` (gitignored, depth-1 git clones for source inspection). The two locations are paired but distinct: `analysis/` holds our derivative analysis; `refs/` holds upstream source.

**47 repos** cloned `depth=1` into `refs/competitors/` (gitignored) as of 2026-05-25 (22 initial-landscape + 8 added during RESEARCH-DELTA round [claude-review-loop, ralph-wiggum, awesome-code-review, cygnusfear-stuff, grill-for-claude, rohitg00-toolkit, forensic-skills, anthropic-security-review] + 4 added morning 2026-05-25 [archgate-cli, continuous-claude-v3, buildingopen-bouncer, jules-cli-ext] + 13 added afternoon 2026-05-25 per T1+T2+T3 expansion after user-supplied ChatGPT validation [alirezarezvani-claude-skills, wshobson-agents, VoltAgent-awesome-claude-code-subagents, shadowX4fox-solutions-architect-skills, rknall-claude-skills, piomin-claude-ai-spring-boot, pauhu-claude-codex-review, TimmyZinin-codex-review, fastruby-tech-debt-skill, dstiliadis-security-review-skill, Dilaz-security-review-skill, MaTriXy-github-review-skill, elvismdev-claude-wordpress-skills]). PRIOR INACCURACY: this preamble previously said "39 repos" which double-counted the original 22 with the morning-batch attribution; RESEARCH-DELTA-round additions (8 clones) were missed. Corrected 2026-05-25 via filesystem audit (`ls -d refs/competitors/*/ | wc -l = 47`). NOTFOUND/fabrications: Edison, bug-detective, Agento-Patronum, emaarco/agento-patronum, KevinPoorDeveloper/agent-skills. Hallucinated descriptions: hardwood-hq/hardwood (Java Parquet lib, not code-review tool), affaan-m/ECC (191k star anomaly). Closed-source NOTFOUND: Jules (jules-cli-ext is CLI extension orchestrator only). See `CLAIM-DELTA-2026-05-25.md` for first-batch impact + `CLAIM-DELTA-2026-05-25-pt2.md` (pending) for second-batch novel-method findings.

## Skill-format competitors (have SKILL.md)

Sorted by SKILL.md count descending. Original-batch + 4-added-morning + 13-added-afternoon-T1/T2/T3.

| Repo | SKILLs | Plugin | Doc grade | Why relevant |
|------|-------:|:------:|:---------:|--------------|
| `alirezarezvani-claude-skills` | **728** | yes | TBD | **NEW LARGEST**. 16.1k★, MIT. 14 domains. Cross-harness via stdlib-Python sync scripts. **Novel methods**: `context: fork` inter-skill contract, signal+forcing-question router, industry-profile-tuned references. Added 2026-05-25 p.m. (T1). |
| `continuous-claude-v3` | 160 | yes | TBD | 3.7k★, MIT. Session-spanning ledgers + handoffs (`thoughts/`). Postgres+pgvector archival memory. `.claude/agents/` ships 5 critic-class `.md` files: critic.md / judge.md / **validate-agent.md** (NOT `validator.md` — earlier draft had wrong filename) / arbiter.md / atlas.md, plus `warden.json` config only (no `warden.md`). **Affects HALT-STATE-GAP + CRITIC-INDEPENDENCE-GAP**. Added 2026-05-25 a.m. |
| `wshobson-agents` | 155 | yes | A | **35.9k★, MIT** (LARGEST by stars). 83 plugins + 191 agents across 5 harnesses. **Novel methods**: adapter-driven multi-harness gen, 3-layer evaluation (static+judge+Monte-Carlo), file-ownership-boundary, `make garden` drift. Added 2026-05-25 p.m. (T1). |
| `levnik-skills` | 137 | yes | B/C | Hash-verified editing, multi-model review, review schema with explicit file/line ranges |
| `trailofbits-skills` | 74 | yes | B | Security lens registry: `fp-check`, `differential-review`, `variant-analysis`, SARIF/static-analysis |
| `gstack` | 57 | no | B/C | Stage-gate workflow, QA/docs commands |
| `open-code-review` | 32 | yes | B | Multi-agent critic-independence with 28 reviewer personas |
| `mattpocock-skills` | 28 | yes | B/C | TDD, diagnose, to-issues, to-prd — vocabulary extraction |
| `shadowX4fox-solutions-architect-skills` | 17 | yes | TBD | 7★, MIT. Architecture doc workflow + 19 agents. NOT yet deep-inspected. Added 2026-05-25 p.m. (T2). |
| `superpowers` | 14 | yes | B/C | Red-Green-Refactor enforcement, worktree isolation |
| `great_cto` | 13 | yes | B/C | 8-specialist SDLC, 13 compliance frameworks |
| `forensic-skills` | 11 | yes | B/C | hotspot×complexity ROI formulas (source for ROI-PRIORITIZATION-GAP) |
| `rknall-claude-skills` | 10 | yes | TBD | 49★, no LICENSE. Python architecture-review. NOT deep-inspected. Added 2026-05-25 p.m. (T3). |
| `anthropic-claude-code` | 10 | n/a | A/B | Official `code-review` plugin: parallel agents, confidence scoring (`plugins/code-review/`) |
| `skills-janitor` | 9 | yes | B/C | Jaccard overlap audit for skill packs |
| `grill-for-claude` | 9 | yes | B | `[GOOD]` positive-finding enum, untrusted-content posture |
| `brooks-lint` | 6 | yes | B/C | Symptom→Source→Consequence→Remedy, 12-book grounding |
| `logic-lens` | 6 | yes | B/C | Premises→Trace→Divergence→Remedy execution traces |
| `piomin-claude-ai-spring-boot` | 5 | yes | TBD | 1.2k★, Apache-2.0. Spring Boot template. NOT deep-inspected. Added 2026-05-25 p.m. (T3). |
| `prism` | 3 | yes | B/C | Session intelligence: token cost + CLAUDE.md adherence |
| `coderabbit-skills` | 2 | yes | B | Severity-grouped findings, fix + re-review loop |
| `buildingopen-bouncer` | 1 | yes | TBD | 4★, MIT. Gemini-SDK post-output scoring (no argv leak). **Affects CROSS-MODEL-CRITIC-GAP**. Added 2026-05-25 a.m. |
| `pauhu-claude-codex-review` | 1 | yes | TBD | 0★, MIT. Argv-based optional Codex critic + npx fallback. **CROSS-MODEL-CRITIC comparator**. Added 2026-05-25 p.m. (T1). |
| `TimmyZinin-codex-review` | 1 | yes | TBD | 0★, MIT. **Stdin-based** Codex critic (confirms our recommendation as industry pattern). Pre/post git-status verification. **CROSS-MODEL-CRITIC comparator**. Added 2026-05-25 p.m. (T1). |
| `fastruby-tech-debt-skill` | 1 | yes | TBD | 5★, MIT. bundler-audit + brakeman + rubycritic + skunk orchestration. **Comparator for ROI-PRIORITIZATION-GAP**: confirms forensic-skills hotspot×complexity stronger than skunk's qualitative tiers. Added 2026-05-25 p.m. (T1). |
| `dstiliadis-security-review-skill` | 1 | yes | TBD | 8★, MIT. Security review. NOT deep-inspected. Added 2026-05-25 p.m. (T2). |
| `Dilaz-security-review-skill` | 1 | yes | TBD | 6★, MIT. Exploit-driven security. NOT deep-inspected. Added 2026-05-25 p.m. (T2). |
| `MaTriXy-github-review-skill` | 1 | yes | TBD | 3★, no LICENSE. GH security alerts → remediation. NOT deep-inspected. Added 2026-05-25 p.m. (T2). |
| `elvismdev-claude-wordpress-skills` | 1 | yes | TBD | 191★, MIT. WordPress engineering skills. NOT deep-inspected. Added 2026-05-25 p.m. (T3). |
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
| `claude-review-loop` | B | Stop-hook gated Actor-Critic loop with argv-leaky Codex multi-agent critic. **CROSS-MODEL-CRITIC source** |
| `archgate-cli` | B | 38★, Apache-2.0. ADRs-as-executable-rules: `.archgate/adrs/*.md` + `.rules.ts` companions. **Prior-art for GOVERNANCE-GAP Gap C** (NOT adopted per user prereq directive). Added 2026-05-25 a.m. |
| `jules-cli-ext` | C | 392★. Official Google Gemini-CLI extension for Jules orchestration. Does NOT expose Jules cloud-VM source. Added 2026-05-25 a.m. |
| `VoltAgent-awesome-claude-code-subagents` | C/D | 20.5k★, MIT. 154 agents under `categories/{NN-name}/*.md`. Mostly anti-pattern reference (context-manager magical-state + "senior X" generic prompts). One positive: `codebase-orchestrator` weighted-priority + diff-preview pattern. Added 2026-05-25 p.m. (T1). |

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

- [`RESEARCH-DELTA.md`](RESEARCH-DELTA.md) — Per-doc deltas after inspecting 8 missed competitors (claude-review-loop, ralph-wiggum, awesome-code-review, cygnusfear-stuff, grill-for-claude, rohitg00-toolkit, forensic-skills, anthropic-security-review) + finally opening `mattpocock-skills/skills/engineering/improve-codebase-architecture`
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

### From 2026-05-25 p.m. T1+T2+T3 expansion (per CLAIM-DELTA-pt2)

| File | Topic | Priority | Source competitor(s) |
|---|---|---|---|
| [`MULTI-HARNESS-ADAPTER-GAP.md`](MULTI-HARNESS-ADAPTER-GAP.md) | Cross-harness distribution: symlink (default) vs adapter framework (when forced) vs sync scripts | P2 (defer adapter framework until forced) | wshobson/agents (adapter), alirezarezvani/claude-skills (sync scripts) |
| [`PHASE-CONTEXT-ISOLATION-GAP.md`](PHASE-CONTEXT-ISOLATION-GAP.md) | Per-phase context isolation via `context: fork`; deep-dive of HALT-STATE Gap G | P2 (Validator phase only) | alirezarezvani/claude-skills |
| [`ROUTING-DISCIPLINE-GAP.md`](ROUTING-DISCIPLINE-GAP.md) | Signal-canon for Critic lens dispatch + forcing-question protocol + routing_rationale digest | P2 | alirezarezvani/claude-skills (Matt-Pocock-forcing-question pattern) |
| [`CONTINUOUS-SCORING-AUGMENTATION-GAP.md`](CONTINUOUS-SCORING-AUGMENTATION-GAP.md) | 3-layer eval framework (Static + LLM-judge + Monte Carlo) as ADDITIVE observability layer; never replaces binary G1-G48 gates | P2 (Gap A useful immediately) | wshobson/agents `plugin-eval` |

### Coverage map: landscape mechanism → gap doc

| Mechanism (per landscape doc) | Gap doc(s) |
|---|---|
| Evidence-linked finding schema | SCHEMA-GAP (incl. Gap 7 positive-finding from grill) |
| Critic independence gate | CRITIC-INDEPENDENCE + CROSS-MODEL-CRITIC + PARALLEL-CRITIC-ARTIFACT-CONTRACT + PHASE-CONTEXT-ISOLATION (Validator-fork) |
| Executable governance ingestion | GOVERNANCE (archgate prior art acknowledged 2026-05-25; C.2 TOML-default per user prereq directive) |
| Changed-line traceability | TRACEABILITY |
| Halt taxonomy / checkpoint state | HALT-STATE (loop-spanning gold) + HALT-STATE Gap F session-spanning handoff per continuous-claude-v3 |
| Forced-completion gates | GATES + TWO-LAYER-DETECTION |
| Risk-triggered external lenses (P1) | SPECIALTY-LENS-DISPATCH + ROUTING-DISCIPLINE (signal-canon + forcing-question per alirezarezvani) |
| Clean-environment validation (P2) | CLEAN-ENVIRONMENT-VALIDATION |
| Adoption-signal tracking (P2) | ADOPTION-SIGNAL-TRACKING (CLAIM-DELTA-pt2 reinforces: missed-from-clone-set + star-anomaly + fabrication + hallucinated-description as 4 inversion types) |
| Context ledger (P1) | covered in HALT-STATE-GAP (LOOP_STATE + checkpoint mechanics) + HALT-STATE Gap F (session-spanning) |
| ROI / backlog prioritization | ROI-PRIORITIZATION (fastruby comparator confirms forensic-skills hotspot×complexity stronger) |
| Skill-TDD with fixtures (research's "major moat") | SKILL-TDD-FIXTURES |
| Empirical falsifier (arXiv:2511.04824) | ARXIV-AGENTIC-REFACTORING |
| Specialty audit-suite architecture (levnik) | LEVNIK-AUDIT-SUITE |
| Cross-harness skill distribution | MULTI-HARNESS-ADAPTER (per wshobson + alirezarezvani; recommendation: symlink-only until forced) |
| Per-phase context isolation | PHASE-CONTEXT-ISOLATION (per alirezarezvani `context: fork`; recommendation: Validator phase only) |
| Routing decision discipline | ROUTING-DISCIPLINE (per alirezarezvani signal-based router + Matt-Pocock-forcing-question) |
| Continuous quality scoring | CONTINUOUS-SCORING-AUGMENTATION (per wshobson 3-layer eval; recommendation: additive only, never replaces binary G1-G48 gates) |
| Cross-model post-output scoring (Category 2) | CROSS-MODEL-CRITIC Gap E (per Bouncer Gemini-SDK pattern; 8/10 default vs Bouncer's 10/10 hardcoded) |

All mechanisms from the landscape research + 2026-05-25 p.m. T1+T2+T3 expansion now have dedicated gap docs. Multi-domain scanning is documented as deferred (stub doc).

## What NOT to import (doc § 7)

50-agent org chart, parallel editors, always-on deep security review, universal "no-delete-without-failing-test" rule, cloud-VM-mandatory validation, markdown-only findings, parent-repo-stars-as-skill-stars conflation, literature decoration, generic senior-engineer prompts.
