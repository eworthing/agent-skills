# Peer-Review Prompt — contest-refactor competitive gap analysis (merged 2026-05-25)

Copy everything below the `---BEGIN PROMPT---` line and paste into another LLM (Codex CLI, Gemini CLI, GPT-5, opencode, Claude Opus from a fresh session, etc.). The reviewing LLM should have **filesystem read access** to the `/Users/Shared/git/agent-skills/` repo and its `refs/competitors/` clones.

Replaces the prior `SOURCE-VERIFICATION-PROMPT.md` (merged in 2026-05-25). Covers BOTH review axes in one prompt:

1. **Internal consistency** — claim-overstating, schema composability, adoption-order, "contest-refactor wins" overclaim, missed competitors, missed mechanisms.
2. **Source veracity** — do gap-doc claims about competitor source AND about contest-refactor's own source survive filesystem inspection? (paraphrase drift, fabricated details, wrong line numbers.)

---BEGIN PROMPT---

You are reviewing a competitive gap analysis I produced for `contest-refactor`, an autonomous Actor-Critic refactoring loop skill. The analysis compares contest-refactor's existing mechanisms against 47 cloned competitor repos (PR review tools, agent skills, MCP servers, RGR frameworks, plugin marketplaces, cross-model critic patterns, post-output scoring SDKs). 29 markdown files (21 mechanism `*-GAP.md` + 3 meta + 2 CLAIM-DELTAs + SOURCE-STATUS + REVIEW-PROMPT + SOURCE-VERIFICATION-PROMPT stub) live under `analysis/contest-refactor/`.

I want a HARD review. Not validation. Default skeptical. Quote file paths and line numbers for every criticism. If a claim seems plausible but unverified, mark it `UNVERIFIED:` and say what evidence would confirm or refute. Do not be polite. Brief praise only where I avoided a mistake an average reviewer would make.

The analysis has been described in commit messages as having survived 7 rounds of cross-LLM adversarial review (3 Gemini Pro + 4 Codex GPT-5.4 xhigh, both APPROVED) on internal-consistency dimensions. **Caveat for the present review** (per Codex Class 7 PR1): the primary review transcripts for those 7 rounds were not committed to this repo — only the resulting revisions and commit messages persist as evidence. If you want to audit the prior-round verdicts directly, you would need access to the original session transcripts in `~/.claude/projects/-Users-Shared-git-agent-skills/*.jsonl`; from `analysis/contest-refactor/` alone, the trail is summarized-only. It has also survived two 2026-05-25 expansion rounds documented in `CLAIM-DELTA-2026-05-25.md` (morning: 4 missed competitors added) and `CLAIM-DELTA-2026-05-25-pt2.md` (afternoon: 13 T1+T2+T3 clones + 4 new gap docs + 3 revised docs). **Your job is to find what the prior rounds missed**, particularly anything requiring filesystem cross-check (paraphrase drift, line-number drift, fabricated details, missed mechanisms in newly-added clones).

## What to read

### Gap analysis docs (the artifacts under review)

`/Users/Shared/git/agent-skills/analysis/contest-refactor/` — **29 markdown files** (21 `*-GAP.md` mechanism-by-mechanism docs + 3 meta docs `INVENTORY.md`/`RESEARCH-DELTA.md`/`STATE-MACHINE-COMPOSITION-APPENDIX.md` + 2 CLAIM-DELTAs + `SOURCE-STATUS.md` + `REVIEW-PROMPT.md` (this file) + `SOURCE-VERIFICATION-PROMPT.md` (stub pointer to this file)). Start with:

- `INVENTORY.md` — coverage map: mechanism → gap doc → competitor source; full clone catalog
- `SOURCE-STATUS.md` — per-candidate matrix (cloned / README-inspected / claims-extracted / gap-docs-referencing / adoption-verified / license / status) + fabrication+hallucination+anomaly log + inversion log
- `STATE-MACHINE-COMPOSITION-APPENDIX.md` — single source of truth for the proposed end-to-end loop pipeline
- `RESEARCH-DELTA.md` — synthesis pass that absorbed 8 missed competitors + arXiv paper
- `CLAIM-DELTA-2026-05-25.md` — morning expansion (4 new clones + impact analysis on existing docs)
- `CLAIM-DELTA-2026-05-25-pt2.md` — afternoon expansion (24 ChatGPT-claimed candidates validated: 17 verified + 5 false-positive-already-cloned + 1 fabrication + 1 hallucinated-desc + 1 star-anomaly); 13 T1+T2+T3 clones + novel-method extraction; 4 new gap docs authored
- `LEVNIK-AUDIT-SUITE-GAP.md` — deepest single-competitor analysis (levnik 35+ workers)

**Original 21 gap docs** (mechanism-by-mechanism):

`SCHEMA-GAP-CONTEST-REFACTOR.md`, `CRITIC-INDEPENDENCE-GAP.md`, `GOVERNANCE-GAP.md`, `TRACEABILITY-GAP.md`, `HALT-STATE-GAP.md`, `GATES-GAP.md`, `CROSS-MODEL-CRITIC-GAP.md`, `SPECIALTY-LENS-DISPATCH-GAP.md`, `TWO-LAYER-DETECTION-GAP.md`, `ARXIV-AGENTIC-REFACTORING-GAP.md`, `SKILL-TDD-FIXTURES-GAP.md`, `ROI-PRIORITIZATION-GAP.md`, `CLEAN-ENVIRONMENT-VALIDATION-GAP.md`, `PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP.md`, `ADOPTION-SIGNAL-TRACKING-GAP.md`, `DOMAIN-AWARE-SCANNING-GAP.md`, `LEVNIK-AUDIT-SUITE-GAP.md` (deep-dive), `STATE-MACHINE-COMPOSITION-APPENDIX.md`, `RESEARCH-DELTA.md`, `INVENTORY.md`, `REVIEW-PROMPT.md` (this file).

**Revised 2026-05-25 p.m.** (verify the revisions are coherent and don't contradict unrevised sections):

- `GOVERNANCE-GAP.md` — Gap C reframed per archgate prior art; decision-fork C.1/C.2/C.3 with C.2 (TOML-only) as default per user prereq directive (don't adopt archgate runtime dep). Verify the doc CLEARLY drops C.1 and demotes C.3 to opt-in; flag ambiguous "we could go either way" framing.
- `CROSS-MODEL-CRITIC-GAP.md` — two-tier categorization (Cat 1 pre-output via stdin / Cat 2 post-output via SDK); added Bouncer + pauhu + TimmyZinin comparators; Gap E (G48 Category-2 HALT_SUCCESS gate via Gemini Flash SDK); schema_version 4→5. Verify provider/pattern assignment to category is unambiguous + G48 gate definition is clear.
- `HALT-STATE-GAP.md` — added continuous-claude-v3 comparator + temporal-scope framing (loop-spanning vs session-spanning vs permanent); added Gap F (session-spanning halt-handoff) + Gap G (context: fork Phase 1.1 Validator); cross-link to CRITIC-INDEPENDENCE-GAP. Verify "no competitor matches checkpoint mechanics" is consistently narrowed to LOOP-spanning scope (no remaining unscoped "gold standard" claims).
- `INVENTORY.md` — count 26→39; skill-format table reordered (alirezarezvani 728 SKILLs = new largest); coverage map updated for new docs.

**Newly authored 2026-05-25 p.m.** (verify methods extracted from sources actually exist):

- `MULTI-HARNESS-ADAPTER-GAP.md` — sourced from wshobson-agents adapter framework + alirezarezvani-claude-skills sync scripts. Recommendation: symlink-only until forced.
- `PHASE-CONTEXT-ISOLATION-GAP.md` — sourced from alirezarezvani-claude-skills `context: fork` pattern. Deep-dive of HALT-STATE Gap G; recommendation Validator phase only.
- `ROUTING-DISCIPLINE-GAP.md` — sourced from alirezarezvani-claude-skills signal-based router + Matt-Pocock-forcing-question pattern. Three gaps: signal canon, forcing-question protocol, routing_rationale digest.
- `CONTINUOUS-SCORING-AUGMENTATION-GAP.md` — sourced from wshobson-agents `plugin-eval` 3-layer evaluation framework. Recommendation: ADDITIVE observability layer only; never replaces binary G1-G48 gates.

### contest-refactor skill source (truth set for "contest-refactor already has X" claims)

`/Users/Shared/git/agent-skills/contest-refactor/` — the skill being analyzed. Authoritative paths:

- `SKILL.md` — state machine (Step -1 / Step 0 / Step 1 Critic / Step 2 Architect / Step 3 Execution + Halting Conditions + Continuation Discipline)
- `canon/*.toml` — 9+ canonical enum files: `states`, `halt-subtypes`, `finding-statuses`, `retirement-reasons`, `severity-anchors`, `scorecard-dimensions`, `dependency-categories`, `fixture-rule-kinds`, `validation-gates`, `verdicts`. Gap docs propose additional canon files: `loop-phases`, `refactoring-patterns`, `tie-kinds`, `confidence-levels`, `area-verdicts`, `boundary-rule-shape`, `critic-status`, `critic-lens-signals`. Verify naming/scope collisions.
- `references/method.md` — 10-step Critic Method + Evidence Chain + Simplify Pressure Test
- `references/validation.md` — 31 hard gates G1-G31 + 8 quality passes Q1-Q8 (gap docs reserve G42, G43, G44, G45, G46, G47, G48, G49 — verify no unintended overlap)
- `references/output-format-json.md` — `CURRENT_REVIEW.json` schema (the gap docs propose `schema_version: 4` and `schema_version: 5` additions; verify the v3 baseline + that v4 and v5 fields don't collide at top-level)
- `references/output-format-state-schemas.md` — `LOOP_STATE.json`, `findings_registry.json`, `REVIEW_HISTORY.json` schemas
- `references/halt-handoff.md` — structured `halt_handoff{text, expected_actions[]}` object + drift-matcher
- `references/resume-detection.md` — Resume Precedence Matrix (Cases A-E)
- `references/trust-model.md` — instruction-vs-evidence precedence + Loop Isolation + payload-as-evidence-only rule
- `references/implementation-reviewer.md` — Reviewer subagent prompt + verdict schema
- `references/provider-adapters.md` — Claude Code / Codex / opencode / unknown provider matrix
- `references/architecture-rubric.md` — Score Anchors, Severity Anchors, Unified Seam Policy, 9.5+ threshold
- `references/lens-apple.md` + `references/lens-generic.md`
- `references/project-config.md` + `.contest-refactor.example.toml`
- `scripts/*.py` — `validate-artifact.py`, `validate-repo.py`, `validate-fixtures.py`, `_canon.py`, `_fingerprint.py`
- `evals/` — existing artifact-smoke fixtures (verify the exact count claimed in gap docs)

### Competitor source clones (truth set for "competitor X has feature Y" claims)

`/Users/Shared/git/agent-skills/refs/competitors/` — **47 depth-1 git clones** (verified 2026-05-25 via `ls -d refs/competitors/*/ | wc -l`). Breakdown: 30 originals (22 from initial landscape inspection + 8 added in RESEARCH-DELTA round: `claude-review-loop`, `ralph-wiggum`, `awesome-code-review`, `cygnusfear-stuff`, `grill-for-claude`, `rohitg00-toolkit`, `forensic-skills`, `anthropic-security-review`) + 4 added 2026-05-25 a.m. (`archgate-cli`, `continuous-claude-v3`, `buildingopen-bouncer`, `jules-cli-ext`) + 13 added 2026-05-25 p.m. (T1+T2+T3). See `refs/competitors/README.md` for the per-clone catalog with size + SKILL count + relevance, AND `analysis/contest-refactor/SOURCE-STATUS.md` for per-candidate inspection status.

**Note** (historical, kept for audit-trail of an earlier accuracy fix; do NOT re-flag — see Codex Class 1 SM8): Pre-2026-05-25 drafts of `INVENTORY.md` preamble and CLAIM-DELTA-pt2 stated count "39", missing 8 RESEARCH-DELTA-round clones. As of 2026-05-25 both files were corrected to 47 (filesystem audit: `ls -d refs/competitors/*/ | wc -l = 47`). If you still encounter a "39" claim anywhere in the bundle today, **that** is a fresh Class 1 source mismatch worth flagging — but `INVENTORY.md:5` and `CLAIM-DELTA-2026-05-25-pt2.md` already read 47 as of the last accuracy pass.

**Originals (cited heavily in pre-2026-05-25 docs)**:

- `claude-review-loop/` — Stop-hook + Codex multi-agent critic (closest live competitor; ~619★ per gap docs)
- `levnik-skills/plugins/codebase-audit-suite/` — 35+ specialty audit workers + shared contract files in `shared/references/`
- `trailofbits-skills/plugins/fp-check/` — Stop+SubagentStop hook prompts in `hooks/hooks.json`
- `anthropic-claude-code/plugins/{code-review,pr-review-toolkit}/` — official Anthropic plugins (sparse-checkout: `plugins/` only)
- `mattpocock-skills/skills/engineering/improve-codebase-architecture/` — deletion test prose
- `superpowers/skills/` — RGR doctrine, worktree isolation, skill-TDD (no fixtures)
- `forensic-skills/.claude/skills/forensic-hotspot-finder/` + `forensic-refactoring-roi/` — ROI formulas
- `grill-for-claude/codex/skills/grill-core/` — `[GOOD]` enum + untrusted-content posture
- `rohitg00-toolkit/agents/developer-experience/refactoring-specialist.md` — atomic-step + per-pattern-commit prose
- `anthropic-security-review/.claude/commands/security-review.md` — 12-item hard exclusion list + HIGH-confidence-only filter (NOTE: actual git origin is `anthropics/claude-code-security-review.git` — alias confirmed 2026-05-25)
- `pr-agent/pr_agent/{algo,tools,settings}/` — hunk parsing + dynamic-context + self-reflection
- `aider/aider/` — repo-map + edit-format coders
- `cygnusfear-stuff/agents/code-reviewer.md` — 6-pass protocol
- `ralph-wiggum/` — `<promise>COMPLETE</promise>` sentinel + `.ralph/` state dir
- `awesome-code-review/SKILL.md` — 5-phase progressive-disclosure design (NOTE: actual git origin is `awesome-skills/code-review-skill.git` — alias confirmed 2026-05-25)
- `agentlint/src/scanner.sh` + `standards/evidence.json` — 51 deterministic checks + circuit-breaker H3
- `claude-bouncer/hooks/` — PreToolUse pattern matchers
- `prism/prism/` — Python observability tool (NOT runtime intervention; verify gap-doc framing)
- `plandex/app/` — Go agent server (plan state, branching)
- `goose/` — block/goose agent framework
- `architecture-review-mcp/src/repo_architecture_mcp/` — NetworkX AST graphs
- `brooks-lint/` + `logic-lens/` + `skills-janitor/` + `gstack/` + others — sampled less deeply

**Added 2026-05-25 a.m. — 4 new clones (per CLAIM-DELTA + revised docs)**:

- `archgate-cli/` (38★, Apache-2.0) — `.archgate/adrs/DOMAIN-NNN-title.md` + paired `.rules.ts` companion. Key files: `src/formats/adr.ts:31-45` (YAML frontmatter schema), `src/formats/rules.ts:67-90` (RuleContext APIs), `src/commands/check.ts:22-157` (exit codes + output formats), `package.json:41` (CI scripts)
- `continuous-claude-v3/` (3.7k★, MIT) — session-spanning ledgers + handoffs + 30 hooks + 6 critic-class agents + PostgreSQL+pgvector `archival_memory`. Key paths: `thoughts/ledgers/`, `thoughts/shared/handoffs/`, `.claude/hooks/`, `.claude/agents/{critic,judge,warden,validator,arbiter,atlas}.md`
- `buildingopen-bouncer/` (4★, MIT) — Stop hook + `/bouncer` skill; post-output scoring via `google.genai.Client()` SDK. Key files: `gemini-audit.sh` (wrapper), `gemini-audit.py:25-313` (Python SDK invocation + scoring prompt + threshold), `skill/scripts/bouncer-deep.py:175-295` (deep mode with tool access)
- `jules-cli-ext/` (392★) — Gemini-CLI extension; does NOT expose Jules cloud-VM internals

**Added 2026-05-25 p.m. — 13 T1+T2+T3 clones**:

- `alirezarezvani-claude-skills/` (16.1k★, MIT) — **NEW LARGEST**: 728 SKILL.md across 14 domains + 171 agents + 11 real hooks. Example file with extracted patterns: `business-operations/skills/business-operations-skills/SKILL.md`. Sync scripts: `scripts/sync-{codex,gemini,hermes,vibe}-skills.py`
- `wshobson-agents/` (35.9k★, MIT) — **LARGEST by stars**: 83 plugins + 155 SKILLs + 191 agents + 102 commands across 5 harnesses. Adapter framework: `tools/adapters/{base,codex,cursor,opencode,gemini}.py`. 3-layer eval: `plugins/plugin-eval/agents/eval-orchestrator.md` + `docs/plugin-eval.md`. File-ownership: `plugins/agent-teams/agents/team-lead.md:1-93`. Drift detection: `Makefile` + `tools/` scripts
- `VoltAgent-awesome-claude-code-subagents/` (20.5k★, MIT) — 154 agents under `categories/{NN-name}/*.md`. Key positive: `categories/09-meta-orchestration/codebase-orchestrator.md:1-80`. Mostly anti-pattern reference per CLAIM-DELTA-pt2
- `pauhu-claude-codex-review/` (0★, MIT) — 1 SKILL.md. Codex invocation at SKILL.md:48 (argv-based, optional); npx fallback at SKILL.md:46-51
- `TimmyZinin-codex-review/` (0★, MIT) — 1 SKILL.md. **Stdin-based Codex invocation** at SKILL.md:138 (`codex exec ${CODEX_FLAGS} - < /tmp/codex-review-prompt-${TIMESTAMP}.md`). Pre/post git-status verification at SKILL.md:49-151. Hard prompt constraints at SKILL.md:62-69. 600s timeout at SKILL.md:134. **Critical claim**: confirms contest-refactor stdin recommendation is industry pattern. Verify literal line.
- `fastruby-tech-debt-skill/` (5★, MIT) — 1 SKILL.md. Skunk formula at SKILL.md:255-258. Coverage prerequisite at SKILL.md:157,244. Health Score 5-bucket scheme at SKILL.md:399-434. Pre-audit tool detection at SKILL.md:41-43
- `shadowX4fox-solutions-architect-skills/` (7★, MIT, 17 SKILLs, 19 agents) — CLONED-PENDING, NOT deep-inspected per user T2 directive
- `dstiliadis-security-review-skill/`, `Dilaz-security-review-skill/`, `MaTriXy-github-review-skill/` — all CLONED-PENDING per user T2 directive
- `piomin-claude-ai-spring-boot/`, `elvismdev-claude-wordpress-skills/`, `rknall-claude-skills/` — all CLONED-PENDING per user T3 directive

## Failure modes to hunt

### Class 1: Source mismatch (HIGHEST priority — filesystem-cross-check axis)

For each "competitor X has feature Y" or "contest-refactor already has Z" claim:

1. Open the cited source file
2. Verify the claim matches what's actually there
3. If summarized rather than quoted: re-read the summary against source, flag paraphrasing drift
4. Flag any cited URL, file path, line number that doesn't resolve

**High-value spot-checks (originals)**:

- **claude-review-loop**: verify `hooks/stop-hook.sh` actually has the claimed retry cap of 2, fail-open ERR trap, and `--dangerously-bypass-approvals-and-sandbox` default (RESEARCH-DELTA + GATES-GAP + CROSS-MODEL-CRITIC-GAP all cite this).
- **trailofbits fp-check `hooks/hooks.json`**: GATES-GAP pastes claimed-verbatim hooks.json. Diff against the actual file.
- **anthropic code-review plugin**: CRITIC-INDEPENDENCE-GAP claims "4 parallel agents (2 Sonnet CLAUDE.md auditors + 1 Opus bug + 1 Opus logic/security)". Verify against `plugins/code-review/commands/code-review.md`.
- **levnik audit_summary_contract.md**: LEVNIK-AUDIT-SUITE-GAP claims `"status": "completed"` is valid, `"complete"` invalid (strict enum). Verify in source.
- **levnik audit_scoring.md**: same doc claims formula `penalty = critical*2.0 + high*1.0 + medium*0.5 + low*0.2`. Verify.
- **mattpocock deletion-test**: ARXIV-AGENTIC-REFACTORING-GAP quotes the deletion test verbatim from `mattpocock-skills/skills/engineering/improve-codebase-architecture/SKILL.md`. Verify lines + phrasing.
- **forensic-skills formulas**: ROI-PRIORITIZATION-GAP quotes `Risk Score = Normalized Change Frequency × Normalized Complexity Factor` and 4-tier ROI bands. Verify against `forensic-hotspot-finder/SKILL.md` + `forensic-refactoring-roi/SKILL.md`.
- **rohitg00 refactoring-specialist**: TRACEABILITY-GAP quotes atomic-step + characterization-test + per-pattern-commit prose. Verify in `agents/developer-experience/refactoring-specialist.md`.
- **grill-for-claude `[GOOD]` enum**: SCHEMA-GAP Gap 7 + GOVERNANCE-GAP cite specific lines + verbatim untrusted-content rule. Verify in `codex/skills/grill-core/SKILL.md`.
- **anthropic-security-review** 12 hard exclusions: verify count + content against `.claude/commands/security-review.md`.
- **opencode `--prompt-file` flag**: CROSS-MODEL-CRITIC-GAP marks NOT VERIFIED. Re-verify if a clone exists.
- **pr-agent hunk regex**: TRACEABILITY-GAP cites `@@ -start,size +start,size @@` parser. Verify.
- **prism**: gap docs frame it as post-mortem analyzer (read-only Python). Verify NOT runtime hook.
- **contest-refactor counts**: gap docs claim "31 hard gates G1-G31", "8 quality passes Q1-Q8", "5 halt states + 4 subtypes", "5 retirement reasons", "9 scorecard dimensions", "12 evals fixtures". Spot-check.

**High-value spot-checks (added 2026-05-25)**:

- **archgate-cli ADR schema**: GOVERNANCE-GAP cites YAML frontmatter required fields (`id, title, domain, rules:bool, files[]?, respectGitignore?`) at `src/formats/adr.ts:31-45`. Verify.
- **archgate-cli `.rules.ts` API**: GOVERNANCE-GAP cites `RuleSet` type + `check: (ctx: RuleContext) => Promise<void>` + `ctx.report.violation({...})` + sandboxed APIs (`ctx.glob/grep/readFile/readJSON/scopedFiles/changedFiles`) — NO exec/spawn. Verify in `src/formats/rules.ts:67-90`.
- **archgate-cli CI integration**: GOVERNANCE-GAP cites exit codes 0/1/2/130, `--json/--ci` output formats, `archgate check` (CI) + `archgate check --staged` (pre-commit). Verify in `src/commands/check.ts:22-157` + `package.json:41`.
- **continuous-claude-v3 ledger format**: HALT-STATE-GAP cites `thoughts/ledgers/CONTINUITY_CLAUDE-<session>.md` (markdown with frontmatter, session-spanning, git-tracked). Verify.
- **continuous-claude-v3 handoff schema** (corrected per Codex Class 1 SM4): actual handoff YAML at `thoughts/shared/handoffs/<workflow>/<timestamp>_<desc>.yaml` carries `session`, `goal`, `now` per `docs/MULTI-SESSION-ARCHITECTURE.md:89-94`; extractor `.claude/hooks/src/session-start-continuity.ts:118-126` reads only `goal` + `now`. Prose at `:44-47` lists `done_this_session` / `blockers` / `next steps` as intended *contents of* `now` but they are NOT structured payload fields. Verify HALT-STATE-GAP no longer claims the prior fabricated section names (Task Summary / What Worked / What Failed / Key Decisions / State to Restore).
- **continuous-claude-v3 30 hooks across 7 events** (corrected per Codex Class 1 SM5): the source at `README.md:670-680` and `.claude/hooks/README.md:29-35` enumerates 7 events — PreToolUse / PostToolUse / SessionStart / PreCompact / UserPromptSubmit / **SubagentStop** (not `Stop`) / SessionEnd. Per-event count breakdown was never enumerated in the source; prior draft invented numbers (PreToolUse 9, PostToolUse 7+, etc.) — those should be removed wherever cited. Run `find .claude/hooks -name '*.ts' -o -name '*.py' -o -name '*.sh' | wc -l` to verify ~30 total; per-event counts require enumerating each hook's registered event from its source.
- **continuous-claude-v3 critic-class agent files** (corrected per Codex Class 1 SM6): `ls .claude/agents/*.md` returns 5 critic-class files — `critic.md` (review), `judge.md` (refactor), `validate-agent.md` (plan; NOT `validator.md`), `arbiter.md` (testing), `atlas.md` (E2E). `warden.md` does NOT exist — only `warden.json` (445 B config) is present, so the security role is config-only in this repo. Verify HALT-STATE-GAP:8,63,216 + CRITIC-INDEPENDENCE-GAP cross-link no longer claim "6 dedicated agents" with `validator.md`+`warden.md`.
- **buildingopen-bouncer Python SDK invocation**: CROSS-MODEL-CRITIC-GAP Gap E cites `google.genai.Client().models.generate_content(...)` at `gemini-audit.py:306-313` (HTTP POST, NOT CLI). Verify NO argv-passed source. Verify diff text IS in POST body (cloud-API exposure remains; only argv-leak eliminated).
- **buildingopen-bouncer threshold**: CROSS-MODEL-CRITIC-GAP Gap E warns Bouncer default threshold hardcoded 10/10. Verify at `gemini-audit.py:25` (`THRESHOLD = 10`) + `gemini-audit.py:419-427` (block behavior).
- **buildingopen-bouncer deep mode**: CROSS-MODEL-CRITIC-GAP Gap E cites `/bouncer deep` gives Gemini tool access (read_file, run_command, search_code, list_files, git_log, git_diff). Verify at `skill/scripts/bouncer-deep.py:175-295`.
- **pauhu Codex invocation**: revised CROSS-MODEL-CRITIC-GAP cites argv-based `codex exec -s read-only "..."` at SKILL.md:48 + optional fallback to npx tsc/eslint at SKILL.md:46-51. Verify.
- **TimmyZinin Codex stdin invocation** (CRITICAL): revised CROSS-MODEL-CRITIC-GAP cites `codex exec ${CODEX_FLAGS} - < /tmp/codex-review-prompt-${TIMESTAMP}.md` at SKILL.md:138. This is the central claim that stdin transport is industry pattern (not contest-refactor invention). VERIFY the literal `- <` redirect is present at the cited line.
- **TimmyZinin git-status verification**: cited at SKILL.md:49-151 with file-mutation warning. Verify.
- **TimmyZinin hard prompt constraints**: cited at SKILL.md:62-69. Verify.
- **TimmyZinin 600s timeout**: cited at SKILL.md:134. Verify (literal Russian text on line 134 says "Запуск Bash tool с **timeout 600000**" i.e. 600000ms = 600s). NOTE: TimmyZinin SKILL.md is partially bilingual (English + Russian); don't flag Russian sections as fabrication.
- **fastruby skunk formula**: cited at `fastruby-tech-debt-skill/.claude/skills/tech-debt-audit/SKILL.md:255-258` (NOT `fastruby-tech-debt-skill/SKILL.md` — the SKILL.md lives in `.claude/skills/tech-debt-audit/`). Verify literal `SkunkScore = (Code Smells + Complexity) * Coverage Penalty`.
- **fastruby coverage prerequisite**: cited at `.claude/skills/tech-debt-audit/SKILL.md:157, 244`. Verify.
- **fastruby 5-category Health Score**: cited at `.claude/skills/tech-debt-audit/SKILL.md:399-434`. Verify the 5 buckets.
- **fastruby SKILL.md path correction**: CLAIM-DELTA-pt2 + ROI-PRIORITIZATION-GAP cite simply `SKILL.md:NNN` — the actual location is one level deeper: `.claude/skills/tech-debt-audit/SKILL.md`. If any doc cites the root-level `SKILL.md` path, flag as Class 1 source mismatch.
- **alirezarezvani `context: fork`** (CRITICAL): PHASE-CONTEXT-ISOLATION-GAP + ROUTING-DISCIPLINE-GAP cite YAML frontmatter `context: fork` pattern at `business-operations/skills/business-operations-skills/SKILL.md`. Verify the literal `context: fork` declaration exists.
- **alirezarezvani signal-based router + Matt-Pocock-forcing-question**: ROUTING-DISCIPLINE-GAP cites 2-signal-confident + 1-signal-forcing-question pattern. Verify.
- **alirezarezvani 4 sync scripts**: MULTI-HARNESS-ADAPTER-GAP cites `scripts/sync-{codex,gemini,hermes,vibe}-skills.py`. Verify all 4 exist and are stdlib-Python only.
- **alirezarezvani 728 SKILL.md actual count**: README badge claims 329; INVENTORY says actual 728. Run `find /Users/Shared/git/agent-skills/refs/competitors/alirezarezvani-claude-skills -name SKILL.md | wc -l` to verify 728.
- **wshobson adapter framework**: MULTI-HARNESS-ADAPTER-GAP cites `tools/adapters/{base,codex,cursor,opencode,gemini}.py` with HarnessAdapter ABC + per-harness subclasses. Verify all 5 files exist.
- **wshobson plugin-eval 3 layers**: CONTINUOUS-SCORING-AUGMENTATION-GAP cites Layer 1 (7 weighted sub-checks with stated weights), Layer 2 (4 dimensions), Layer 3 (Wilson CI + Bootstrap CI + Clopper-Pearson CI). Verify in `docs/plugin-eval.md`.
- **wshobson agent-teams file-ownership**: CLAIM-DELTA-pt2 + PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP cite file-ownership boundary model from `plugins/agent-teams/agents/team-lead.md:1-93`. Actual file is 92 lines; cited range `:1-93` should be `:1-92` (off by one). Minor.
- **VoltAgent codebase-orchestrator**: CLAIM-DELTA-pt2 + ROI-PRIORITIZATION-GAP cite `categories/09-meta-orchestration/codebase-orchestrator.md:1-80` for weighted-priority axis (security→bugs→arch→perf→style) + approval gates + diff previews + structured JSON. Verify.
- **VoltAgent 154 agents under categories/{NN}/**: CLAIM-DELTA-pt2 cites 10 category dirs. Verify via `find categories -name '*.md' -not -name README.md | wc -l` (returns 154 actual agents). NOTE: unfiltered `find categories -name '*.md'` returns 164 due to per-category README.md files; the 154 claim is correct when READMEs are excluded.

### Class 2: Missing competitors / under-inspected sources

The gap docs cite 47 competitors (per filesystem count; INVENTORY may understate as 39). Some clones are present but never inspected per-doc:

**Pre-2026-05-25 light-inspection list** (sample 2-3):
- `gstack/` (57 SKILL.md files; only mentioned in INVENTORY)
- `brooks-lint/` (6 SKILL.md; cited in GOVERNANCE-GAP only)
- `logic-lens/` (6 SKILL.md; barely cited)
- `domscribe/` (1 SKILL.md, 47MB; mentioned in INVENTORY only)
- `plandex/` (60MB Go server; cited mostly in HALT-STATE-GAP)
- `architecture-review-mcp/` (1MB; cited in GOVERNANCE-GAP only)
- `claude-bouncer/` (252KB; cited in GATES-GAP + SPECIALTY-LENS-DISPATCH-GAP only)
- `agentlint/` (11MB; cited mainly for circuit-breaker H3)

**2026-05-25 T2/T3 CLONED-PENDING list** (deferred per user directive; verify whether anything novel was missed):
- `shadowX4fox-solutions-architect-skills/` (T2, 17 SKILLs, 19 agents) — architecture peer-review patterns
- `dstiliadis-security-review-skill/`, `Dilaz-security-review-skill/`, `MaTriXy-github-review-skill/` (T2) — security review patterns
- `piomin-claude-ai-spring-boot/`, `elvismdev-claude-wordpress-skills/`, `rknall-claude-skills/` (T3) — language-domain patterns

If you find a method-process pattern in any T2/T3 clone that affects existing gap docs, flag — user's "no language/security coverage expansion" directive doesn't preclude method-pattern discovery.

Sample 2-3 across both lists. Do they have mechanisms the gap docs missed entirely? Flag substantive omissions, not just "this exists too."

### Class 3: Schema composability errors

The gap docs propose additions to `CURRENT_REVIEW.json` for `schema_version: 4` AND `schema_version: 5` (the latter introduced 2026-05-25 by CROSS-MODEL-CRITIC Gap E + HALT-STATE Gap F).

- Do additive fields collide at top-level?
- `changed_hunks[]` + `critic_source` + `confidence` + `severity_rationale` + `local_lint_overrides` + `boundary_rules` + `cross_model_critic{}` + `cross_model_scoring{}` + `session_spanning_handoff{}` + `routing_rationale` + per-finding `boundary_rule_id` — all compose cleanly?
- Does any new field break a "skip-when-X" rule? (G4/G8 suspended for `unverifiable_due_to_build_failure: true` — would new fields apply on that path?)
- Do new canon files (`canon/confidence-levels.toml`, `canon/tie-kinds.toml`, `canon/loop-phases.toml`, `canon/refactoring-patterns.toml`, `canon/area-verdicts.toml`, `canon/boundary-rule-shape.toml`, `canon/critic-status.toml`, `canon/critic-lens-signals.toml`) collide with existing ones?
- Gate-number reservations: G42 (TWO-LAYER-DETECTION), G43 (renamed from G34.1), G44 (GOVERNANCE-GAP Gap D), G45+G46+G47 (STATE-MACHINE-COMPOSITION-APPENDIX), G48 (CROSS-MODEL-CRITIC Gap E), G49 (CONTINUOUS-SCORING-AUGMENTATION Gap B). Any unintended overlap with existing G1-G31?
- Schema_version 4 vs 5: is there a defined migration / default-fill table for v4-to-v5? Or are they parallel-applied (some fields v4, some v5)?

### Class 4: Adoption-order pathologies

- "Quick win" items: actually low-risk and self-contained, or blocked by other gaps?
- Schema Gap C (validator subagent) + Critic Independence Gap A (Critic+Actor subagent split) + Halt State Gap B (`critic_unfounded` subtype) + Halt State Gap F (session-spanning handoff) + Halt State Gap G (Phase 1.1 context-fork) + Gates Gap (Reviewer completeness hook) + CROSS-MODEL-CRITIC Gap A (Cat 1) + CROSS-MODEL-CRITIC Gap E (Cat 2) + CONTINUOUS-SCORING Gap A/B — sequenced correctly, or ordering trap?
- Traceability Gap A (changed_hunks) shares hunk-parsing layer with HALT-STATE-GAP Gap C (per-hunk partial-accept). Consistent across docs?
- MULTI-HARNESS-ADAPTER recommendation defers adapter framework "until forced" — does any other gap doc require the adapter? (e.g., if CONTINUOUS-SCORING ships per-harness, would that force adapter?)
- ROUTING-DISCIPLINE Gap A (signal-canon) depends on SPECIALTY-LENS-DISPATCH-GAP being settled. Settled?

### Class 5: "Contest-refactor wins" overclaim

Each gap doc ends with a "contest-refactor already wins on X" section. For each item: is the claim actually unique to contest-refactor, or do other competitors I didn't inspect closely have it too?

For each claim, can you point to the competitor source that's missing the feature (proving the win) vs the competitor source where it exists (refuting the claim)?

Particular high-risk areas after 2026-05-25 expansion:
- HALT-STATE-GAP "gold standard at LOOP-spanning" — verify continuous-claude-v3 doesn't have loop-spanning mechanism too (only session-spanning)
- GOVERNANCE-GAP "contest-refactor wins" items (reopen-justification, accepted-residual expiry, cross-loop identity) — verify archgate genuinely lacks these (not just that they're not in README)
- CROSS-MODEL-CRITIC "contest-refactor schema discipline wins" — verify TimmyZinin / pauhu / Bouncer don't have equivalent structured output

### Class 6: External-research-claim verification (added 2026-05-25)

`SOURCE-STATUS.md` + `CLAIM-DELTA-2026-05-25-pt2.md` log validations of external research claims (initially from ChatGPT). Verify:

- **`KevinPoorDeveloper/agent-skills` fabrication**: SOURCE-STATUS.md + CLAIM-DELTA-pt2 claim 404. Verify via `gh api repos/KevinPoorDeveloper/agent-skills`.
- **`hardwood-hq/hardwood` hallucinated description**: SOURCE-STATUS.md claims actual content is Java Apache Parquet implementation, NOT "Code Review Pyramid." Verify via `gh api repos/hardwood-hq/hardwood --jq '.description, .language'`.
- **`affaan-m/ECC` star anomaly**: SOURCE-STATUS.md claims 191,901 stars (implausible). Verify via `gh api repos/affaan-m/ECC --jq '.stargazers_count'`.
- **5 already-cloned alias-mismatches**: SOURCE-STATUS.md claims `anthropics/claude-code-security-review` → `anthropic-security-review/` and `awesome-skills/code-review-skill` → `awesome-code-review/` are alias-confirmed. Verify via `cd refs/competitors/<dir> && git remote get-url origin`.
- **`emaarco/agento-patronum` fabrication**: claimed 404. Verify.

If any of these "fabrication" / "hallucinated" / "anomaly" claims is itself wrong (e.g., repo actually exists; description IS what we said it isn't; star count is genuinely 191k due to platform anomaly), flag — overclaim of "fabrication" is itself a form of paraphrase drift.

### Class 7: Misframed prior reviews

The gap docs cite Gemini Pro + Codex GPT-5.4 review history (7 rounds) + two CLAIM-DELTA expansion rounds (2026-05-25 a.m. + p.m.). Verify the docs' summary matches actual review trail — look for inflation ("survived 9 rounds" — that's true if you count both CLAIM-DELTAs; "no remaining issues" — verify polish from each round actually applied; etc.).

### Class 8: arXiv response defensibility

`ARXIV-AGENTIC-REFACTORING-GAP.md` accepts the empirical finding that AI agents do 30.7% rename/retype refactorings. The response: add `refactoring_types[]` audit field, document the bias, propose new 10th scorecard dimension `code_hygiene` for low-level edits.

Is the response defensible, OR does it leave contest-refactor's core "9.5+ architecture-first" pitch implicitly contradicted by other docs (e.g., LEVNIK-AUDIT-SUITE-GAP's metric-worship deferral)?

### Class 9: User-directive consistency (added 2026-05-25)

Two user directives from 2026-05-25 should be reflected consistently in revised + new docs:

1. **Archgate prereq directive**: don't adopt archgate as runtime dependency to keep prereqs minimal. Verify:
   - GOVERNANCE-GAP Gap C decision-fork clearly drops C.1 + demotes C.3 to opt-in
   - No other gap doc proposes archgate runtime adoption
   - INVENTORY coverage map reflects this

2. **Method/process focus directive** (NOT lens/language/security expansion): T2 + T3 deep-inspections deferred. Verify:
   - SOURCE-STATUS.md flags T2/T3 entries as CLONED-PENDING per this directive
   - No gap doc cites T2/T3 source as if deep-inspected
   - CLAIM-DELTA-pt2 articulates the directive clearly

If either directive is partially-applied (e.g., a gap doc still recommends archgate adoption; or a doc cites a T2 security skill as if inspected), flag.

## Output format

```
# Gap Analysis Peer Review (merged internal-consistency + source-veracity)

## Verdict
One paragraph. Did the gap analysis hold up across BOTH internal-consistency AND source-veracity axes? What's the single biggest concern?

## Class 1: Source mismatches found
- [SM1] (HIGH|MEDIUM|LOW) Gap doc claim:
  Cited as: `<doc-name>:<line>` saying "<quote>"
  Source says: `<source-file>:<line>` actually says "<quote>"
  Severity: paraphrase drift / wrong line number / fabricated detail / etc.

[... one entry per finding ...]

## Class 2: Missed competitors / under-inspected sources
- [MC1] `<clone-dir>/<file>` has mechanism X that gap doc Y should cover but doesn't
  Suggested adoption: add to <doc-name> as <Gap-letter> OR new gap doc <name>

## Class 3: Schema composability issues
- [SC1] Cross-doc collision / cycle / break-of-invariant
  Evidence: `<doc-A>:<line>` vs `<doc-B>:<line>`
  Recommendation: ...

## Class 4: Adoption-order pathologies
- [AO1] Gap A blocks Gap B but B is sequenced first
  Evidence: ...
  Fix: ...

## Class 5: Over-claimed wins
- [OW1] Doc claims X is unique to contest-refactor but `<competitor>/<file>` has equivalent
  Evidence: ...

## Class 6: External-research-claim mis-categorizations
- [ER1] SOURCE-STATUS.md flags X as fabrication/hallucinated/anomaly, but actually...
  Evidence: ...

## Class 7: Misframed prior reviews
- [PR1] Claim about Gemini/Codex/CLAIM-DELTA history that doesn't match actual trail

## Class 8: arXiv response defensibility
[your assessment]

## Class 9: User-directive consistency
- [UD1] Directive X partially-applied: doc Y still says ...
  Evidence: ...

## Things the bundle got right
[1-2 sentences max — only the most defensible wins]

## Suggested next round
If multiple HIGH Class-1 findings (source fabrications): recommend fresh adversarial round with different reviewer model.
If only minor paraphrase drift + a few Class-2 misses: targeted patches.
If Class 9 surface user-directive drift: flag specific docs needing alignment pass.
If sound across all 9 classes: say so plainly.
```

Hard cap: **3500 words** (longer than legacy 2500-word cap due to merged scope). Cite source file:line for every claim. Prefer **quoting** to summarizing. If a claim is plausibly right but you can't verify without more reading, mark `UNVERIFIED:` and state what you'd need to check.

## Don't

- Don't re-do Gemini's or Codex's prior internal-consistency review (3 + 4 rounds). Their findings are already merged.
- Don't fix the docs yourself. Reviewer-only.
- Don't summarize what each gap doc says (the author wrote them).
- Don't speculate about source you didn't read. Better to say "didn't check X" than to invent.
- Don't grade on "would I have written it this way." Grade on "does the source support the claim AND is the bundle internally coherent."
- Don't ignore Class 6 (external-research-claim verification). The CLAIM-DELTA-pt2 inversion log is a recent addition; mis-categorizations there are higher-risk than older claims that have been through multiple review rounds.

## Why this prompt exists

The 7 prior adversarial review rounds verified the bundle is **internally consistent**. The 2 CLAIM-DELTA expansion rounds (2026-05-25 a.m. + p.m.) covered **coverage gaps** (missed competitors + ChatGPT-claim validation). What's still under-tested:

1. **Filesystem cross-check at scale** for the 2026-05-25 newly-added claims (archgate / continuous-claude-v3 / Bouncer / pauhu / TimmyZinin / fastruby / alirezarezvani / wshobson / VoltAgent)
2. **Schema_version 5 composability** — Gap E (CROSS-MODEL-CRITIC) + Gap F (HALT-STATE) both bump 4→5; no prior review validated their composability
3. **User-directive consistency** — archgate-prereq + methods-focus directives are new and may not yet propagate consistently
4. **External-research-claim verification** (Class 6) — inversion log claims (fabrication / hallucination / anomaly) need filesystem confirmation themselves

If you find none of these, that's a strong signal the bundle is publication-ready. If you find many, that's the next class of issues to remediate before treating the bundle as authoritative.

---END PROMPT---

## Notes for the person passing this prompt

- Paste everything between BEGIN/END markers into a fresh LLM conversation (Claude Sonnet 4.6 / Opus 4.7 from a fresh session, GPT-5+, or a different Gemini model)
- Reviewer needs **filesystem read access** to `/Users/Shared/git/agent-skills/`. Without it, they can only review the gap doc text (defeats the source-veracity axis).
- Best paired with a model that has aggressive Read/Grep tool budget — this is a scan-heavy task, not a reasoning-heavy task.
- Cross-model: if Claude Opus authored the bundle, pair this prompt with a non-Claude reviewer (Gemini Pro, GPT-5+, Llama). Same-model blindspots persist for source-paraphrase drift just like for reasoning errors.
- If using `peer-plan-review` skill harness: this prompt fits the harness as a single review payload (verdict contract + structured findings template).
- Replaces the prior `SOURCE-VERIFICATION-PROMPT.md` (merged in 2026-05-25). If you find the legacy file in the repo, it should be a pointer to this file.
