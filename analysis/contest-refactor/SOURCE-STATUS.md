# Source Status Matrix — contest-refactor competitive analysis

> **CURRENT-STATE (2026-06-28):** the gap corpus was re-audited against current skill source — each `*-GAP.md` now carries a verdict header, and four stale spots were corrected (SARIF + AST import-graph/cycle detection already SHIPPED; phantom gates G33+ flagged as unbuilt; `schema_version: 4` already taken by the HALT-challenge schema). See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md).

**Purpose**: per-candidate tracking matrix to prevent "research swamp" regrowth. Validates ChatGPT 2026-05-25 proposal. Updated whenever a new candidate is surfaced or an existing candidate's status changes.

**Last full refresh**: 2026-05-25 p.m.

## Status legend

| Status | Meaning |
|---|---|
| **CLONED+INSPECTED** | depth-1 clone in `refs/competitors/`; deep-inspection report exists in gap doc OR transcript |
| **CLONED+README** | depth-1 clone in `refs/competitors/`; README inspected but no deep inspection (e.g., T2/T3 per user directive) |
| **CLONED-PENDING** | depth-1 clone exists; inspection not yet done |
| **NOT FOUND** | `gh api repos/<owner>/<repo>` returned 404 — fabrication; do not clone |
| **HALLUCINATED-DESC** | repo exists but external-research-claimed description doesn't match actual repo |
| **STAR-ANOMALY** | repo exists with implausible star count; skip pending forensic |
| **NON-CLONEABLE** | blog / vendor docs / commercial source; track via `ADOPTION-SIGNAL-TRACKING-GAP.md` vendor-self-published flagging |
| **CLOSED-SOURCE** | source not publicly available (Jules cloud-VM etc.); track via inference only |

## Column legend

| Column | Meaning |
|---|---|
| Candidate | `owner/repo` format |
| Cloned? | Y/N + local dir name |
| README inspected? | Y/N (date) |
| Claims extracted? | Y/N + which gap docs cite |
| Gap docs referencing | Comma-separated list |
| Adoption verified? | stars + last-push date as of refresh |
| License verified? | SPDX ID from `gh api` or LICENSE file |
| Status | Per legend above |

## Skill-format competitors (have SKILL.md)

| Candidate | Cloned? | README inspected? | Claims extracted? | Gap docs referencing | Adoption verified? | License verified? | Status |
|---|---|---|---|---|---|---|---|
| `alirezarezvani/claude-skills` | Y `alirezarezvani-claude-skills/` | Y 2026-05-25 p.m. | Y deep-inspected | PHASE-CONTEXT-ISOLATION-GAP, ROUTING-DISCIPLINE-GAP, MULTI-HARNESS-ADAPTER-GAP, CLAIM-DELTA-pt2 | 16,146★, pushed 2026-05-25 | MIT | CLONED+INSPECTED |
| `parcadei/Continuous-Claude-v3` | Y `continuous-claude-v3/` | Y 2026-05-25 a.m. | Y (HALT-STATE Gap F, CRITIC-INDEPENDENCE cross-link) | HALT-STATE-GAP Gap F, CRITIC-INDEPENDENCE-GAP (6 critic-class agents), CLAIM-DELTA, CLAIM-DELTA-pt2 | 3,785★, pushed 2026-01-26 | MIT | CLONED+INSPECTED |
| `wshobson/agents` | Y `wshobson-agents/` | Y 2026-05-25 p.m. | Y deep-inspected | MULTI-HARNESS-ADAPTER-GAP, CONTINUOUS-SCORING-AUGMENTATION-GAP, PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP (file-ownership), CLAIM-DELTA-pt2 | 35,918★, pushed 2026-05-25 | MIT | CLONED+INSPECTED |
| `levnikolaevich/claude-code-skills` | Y `levnik-skills/` | Y | Y | LEVNIK-AUDIT-SUITE-GAP, SCHEMA-GAP | 137 SKILLs (per find) | TBD | CLONED+INSPECTED |
| `trailofbits/skills` | Y `trailofbits-skills/` | Y | Y | GATES-GAP, SCHEMA-GAP, SPECIALTY-LENS-DISPATCH-GAP | TBD | TBD | CLONED+INSPECTED |
| `garrytan/gstack` | Y `gstack/` | Y | Y | RESEARCH-DELTA | TBD | TBD | CLONED+INSPECTED |
| `spencermarx/open-code-review` | Y `open-code-review/` | Y | Y | CRITIC-INDEPENDENCE-GAP | TBD | TBD | CLONED+INSPECTED |
| `mattpocock/skills` | Y `mattpocock-skills/` | Y | Y | ARXIV-AGENTIC-REFACTORING-GAP | TBD | TBD | CLONED+INSPECTED |
| `shadowX4fox/solutions-architect-skills` | Y `shadowX4fox-solutions-architect-skills/` | N | N | (none yet) | 7★, pushed 2026-05-21 | MIT | CLONED-PENDING (T2 — deferred per user directive) |
| `obra/superpowers` | Y `superpowers/` | Y | Y | SKILL-TDD-FIXTURES-GAP, HALT-STATE-GAP worktree, CLEAN-ENVIRONMENT-VALIDATION-GAP | TBD | TBD | CLONED+INSPECTED |
| `avelikiy/great_cto` | Y `great_cto/` | Y | partial | (cited briefly) | TBD | TBD | CLONED+README |
| `AlabamaMike/forensic-skills` | Y `forensic-skills/` | Y | Y | ROI-PRIORITIZATION-GAP | TBD | TBD | CLONED+INSPECTED |
| `rknall/claude-skills` | Y `rknall-claude-skills/` | N | N | (none yet) | 49★, pushed 2025-10-20 | none | CLONED-PENDING (T3 — deferred per user directive) |
| `anthropics/claude-code` | Y `anthropic-claude-code/` (sparse-checkout plugins/ only) | Y | Y | CRITIC-INDEPENDENCE-GAP, SCHEMA-GAP, TRACEABILITY-GAP | TBD | TBD | CLONED+INSPECTED |
| `khendzel/skills-janitor` | Y `skills-janitor/` | Y | partial | (cited briefly) | TBD | TBD | CLONED+README |
| `xiaolai/grill-for-claude` | Y `grill-for-claude/` | Y | Y | SCHEMA-GAP Gap 7, GOVERNANCE-GAP | TBD | TBD | CLONED+INSPECTED |
| `hyhmrright/brooks-lint` | Y `brooks-lint/` | Y | Y | GOVERNANCE-GAP | TBD | TBD | CLONED+INSPECTED |
| `hyhmrright/logic-lens` | Y `logic-lens/` | Y | partial | (cited briefly) | TBD | TBD | CLONED+README |
| `piomin/claude-ai-spring-boot` | Y `piomin-claude-ai-spring-boot/` | N | N | (none yet) | 1,175★, pushed 2026-04-29 | Apache-2.0 | CLONED-PENDING (T3 — deferred per user directive) |
| `jakeefr/prism` | Y `prism/` | Y | Y | HALT-STATE-GAP session-event taxonomy | TBD | TBD | CLONED+INSPECTED |
| `coderabbitai/skills` | Y `coderabbit-skills/` | Y | Y | SCHEMA-GAP | TBD | TBD | CLONED+INSPECTED |
| `buildingopen/bouncer` | Y `buildingopen-bouncer/` | Y 2026-05-25 a.m. | Y | CROSS-MODEL-CRITIC-GAP Gap E (Category 2 SDK scoring), CLAIM-DELTA | 4★, pushed 2026-04-09 | MIT | CLONED+INSPECTED |
| `pauhu/claude-codex-review` | Y `pauhu-claude-codex-review/` | Y 2026-05-25 p.m. | Y | CROSS-MODEL-CRITIC-GAP (graceful-degradation pattern), CLAIM-DELTA-pt2 | 0★, pushed 2026-02-09 | MIT | CLONED+INSPECTED |
| `TimmyZinin/codex-review` | Y `TimmyZinin-codex-review/` | Y 2026-05-25 p.m. | Y | CROSS-MODEL-CRITIC-GAP (stdin invocation + git-status verification confirmation), CLAIM-DELTA-pt2 | 0★, pushed 2026-03-31 | MIT | CLONED+INSPECTED |
| `fastruby/tech-debt-skill` | Y `fastruby-tech-debt-skill/` | Y 2026-05-25 p.m. | Y | ROI-PRIORITIZATION-GAP (validates forensic-skills as stronger), CLAIM-DELTA-pt2 | 5★, pushed 2026-01-28 | MIT | CLONED+INSPECTED |
| `dstiliadis/security-review-skill` | Y `dstiliadis-security-review-skill/` | N | N | (none yet) | 8★, pushed 2026-02-02 | MIT | CLONED-PENDING (T2 — deferred per user directive) |
| `Dilaz/security-review-skill` | Y `Dilaz-security-review-skill/` | N | N | (none yet) | 6★, pushed 2026-02-03 | MIT | CLONED-PENDING (T2 — deferred per user directive) |
| `MaTriXy/github-review-skill` | Y `MaTriXy-github-review-skill/` | N | N | (none yet) | 3★, pushed 2025-12-15 | none | CLONED-PENDING (T2 — deferred per user directive) |
| `elvismdev/claude-wordpress-skills` | Y `elvismdev-claude-wordpress-skills/` | N | N | (none yet) | 191★, pushed 2025-11-29 | MIT | CLONED-PENDING (T3 — deferred per user directive) |
| `Th0rgal/open-ralph-wiggum` | Y `ralph-wiggum/` | Y | Y | HALT-STATE-GAP, GATES-GAP | TBD | TBD | CLONED+INSPECTED |
| `awesome-skills/code-review-skill` | Y `awesome-code-review/` | Y | Y | (progressive-disclosure example) | 666★, pushed 2026-05-09 | MIT | CLONED+INSPECTED |
| `patchorbit/domscribe` | Y `domscribe/` | Y | partial | (DOM/runtime axis; tangential) | TBD | TBD | CLONED+README |
| `Cygnusfear/claude-stuff` | Y `cygnusfear-stuff/` | Y | Y | RESEARCH-DELTA | TBD | TBD | CLONED+INSPECTED |
| `rohitg00/awesome-claude-code-toolkit` | Y `rohitg00-toolkit/` | Y | Y | TRACEABILITY-GAP Gap A.1 | TBD | TBD | CLONED+INSPECTED |

## CLI / tool competitors (no SKILL.md — read source/README)

| Candidate | Cloned? | README inspected? | Claims extracted? | Gap docs referencing | Adoption verified? | License verified? | Status |
|---|---|---|---|---|---|---|---|
| `Aider-AI/aider` | Y `aider/` | Y | Y | TRACEABILITY-GAP Gap E | TBD | TBD | CLONED+INSPECTED |
| `plandex-ai/plandex` | Y `plandex/` | Y | Y | HALT-STATE-GAP | TBD | TBD | CLONED+INSPECTED |
| `block/goose` | Y `goose/` (656 MB — consider deletion) | Y | Y | CLEAN-ENVIRONMENT-VALIDATION-GAP (claim refuted) | TBD | TBD | CLONED+INSPECTED |
| `qodo-ai/pr-agent` | Y `pr-agent/` | Y | Y | TRACEABILITY-GAP | TBD | TBD | CLONED+INSPECTED |
| `sweepai/sweep` | Y `sweep/` | Y | partial (stub — insufficient material) | RESEARCH-DELTA brief mention | TBD | TBD | CLONED+README (stub) |
| `0xmariowu/AgentLint` | Y `agentlint/` | Y | Y | GATES-GAP STOP_HOOK_ACTIVE pattern | TBD | TBD | CLONED+INSPECTED |
| `JustHereToHelp/claude-bouncer` | Y `claude-bouncer/` | Y | Y | GATES-GAP, SPECIALTY-LENS-DISPATCH-GAP | TBD | TBD | CLONED+INSPECTED |
| `vinit-devops/repo-architecture-mcp` | Y `architecture-review-mcp/` | Y | Y | GOVERNANCE-GAP Gap D | TBD | TBD | CLONED+INSPECTED |
| `hamelsmu/claude-review-loop` | Y `claude-review-loop/` | Y | Y | GATES-GAP Gap A, CROSS-MODEL-CRITIC-GAP | 619★ approx | none (no LICENSE) | CLONED+INSPECTED |
| `archgate/cli` | Y `archgate-cli/` | Y 2026-05-25 a.m. | Y deep-inspected | GOVERNANCE-GAP Gap C (prior-art reframe per user directive), CLAIM-DELTA | 38★, pushed 2026-05-25 | Apache-2.0 | CLONED+INSPECTED |
| `gemini-cli-extensions/jules` | Y `jules-cli-ext/` | Y 2026-05-25 a.m. | Y (verified tangential) | CLEAN-ENVIRONMENT-VALIDATION-GAP (verified-but-tangential), CLAIM-DELTA | 392★, pushed 2026-05-23 | TBD | CLONED+INSPECTED |
| `VoltAgent/awesome-claude-code-subagents` | Y `VoltAgent-awesome-claude-code-subagents/` | Y 2026-05-25 p.m. | Y deep-inspected (mostly anti-pattern) | CRITIC-INDEPENDENCE-GAP (validates structured discipline), ROI-PRIORITIZATION-GAP (codebase-orchestrator weighted-priority pattern), CLAIM-DELTA-pt2 | 20,508★, pushed 2026-05-25 | MIT | CLONED+INSPECTED |
| `anthropics/claude-code-security-review` | Y `anthropic-security-review/` (alias) | Y | Y | SCHEMA-GAP, GOVERNANCE-GAP | 4,809★, pushed 2026-02-11 | MIT | CLONED+INSPECTED |

## Fabrications + hallucinations + anomalies (do NOT clone)

| Candidate | Source of claim | Reason for exclusion | Status |
|---|---|---|---|
| `emaarco/agento-patronum` | external research | 404 NOT FOUND — confirmed via `gh search repos` | NOT FOUND |
| `KevinPoorDeveloper/agent-skills` | ChatGPT 2026-05-25 | 404 NOT FOUND — confirmed via `gh api` | NOT FOUND |
| Edison | external research (vendor name only; no owner/repo coords ever supplied) | `gh search repos "Edison" --owner=*` returns no claude-skills / claude-code-extension match; vendor never published owner/repo path; NOT-FOUND status NOT reproducible without coords — row retained for audit-trail; if external research re-surfaces the same name, demand owner/repo before re-checking | NOT-FOUND-UNREPRODUCIBLE |
| bug-detective | external research (vendor name only; no owner/repo coords ever supplied) | `gh search repos "bug-detective"` returns multiple unrelated repos in other ecosystems (not claude-skills); no specific owner/repo was given; NOT-FOUND status NOT reproducible without coords — row retained for audit-trail | NOT-FOUND-UNREPRODUCIBLE |
| Agento-Patronum (distinct from `emaarco/agento-patronum` row above) | external research mentioned the name without prefix/owner | Could not distinguish from the `emaarco/agento-patronum` candidate which IS confirmed 404 via `gh api repos/emaarco/agento-patronum`. Most likely a duplicate reference to the same fabrication; row retained because the original research log mentioned it as a separate candidate | NOT-FOUND-LIKELY-DUPLICATE |
| `hardwood-hq/hardwood` | ChatGPT 2026-05-25 | repo exists (282★, Apache-2.0) but actual content is "fast minimal dependency Apache Parquet" (Java parquet library), NOT "Code Review Pyramid" tool as ChatGPT claimed | HALLUCINATED-DESC |
| `affaan-m/everything-claude-code` → `affaan-m/ECC` | ChatGPT 2026-05-25 | live count `gh api repos/affaan-m/ECC --jq '.stargazers_count'` returned **192,046** at re-verification 2026-05-25 (prior reading was 191,901; count continues to climb at unrealistic velocity — implausibly high vs Linux kernel ~165k for reference). Almost certainly star manipulation or fork-inflation artifact. Anomaly categorization stands regardless of exact count. | STAR-ANOMALY |
| Jules (parcadei/Jules? google.dev/jules?) | research | Closed-source; cloud-VM mechanism inferred only via `jules-cli-ext` clone | CLOSED-SOURCE |

## Non-cloneable sources (track via vendor-self-published flagging)

These appear in external research / ChatGPT recommendations but are blogs / vendor docs / commercial sources. Per `ADOPTION-SIGNAL-TRACKING-GAP.md` discipline: tag with `[VENDOR-SELF-PUBLISHED]` when cited; never rely on as primary evidence.

| Source | Type | Why cited | Flag |
|---|---|---|---|
| HAMY 9-parallel reviewers blog | Personal blog post | Parallel critic pattern reference | [VENDOR-SELF-PUBLISHED: no] but personal anecdote — tag `[PERSONAL-BLOG]` |
| Cursor BugBot Autofix blog | Vendor blog | Commercial actor-critic precedent + autofix benchmark | `[VENDOR-SELF-PUBLISHED]` |
| Greptile benchmark page | Vendor docs | PR review benchmark (vendor-published) | `[VENDOR-SELF-PUBLISHED]` |
| DeepSource CVE benchmark page | Vendor docs | Security/autofix benchmark (vendor-published) | `[VENDOR-SELF-PUBLISHED]` |
| Google Jules / critic-augmented generation blog | Vendor blog | "Critic-augmented generation is mainstream" framing | `[VENDOR-SELF-PUBLISHED]` |
| arXiv:2511.04824 Agentic Refactoring paper | Academic paper | Empirical falsifier: agents do 30.7% rename/retype refactorings | Authoritative; cite in ARXIV-AGENTIC-REFACTORING-GAP |
| agentskills.io spec docs | Spec/standard | Packaging conventions (frontmatter, progressive-disclosure, etc.) | Authoritative; cross-link without duplicating |
| Claude plugin directory / Claude Code official docs | Vendor docs (Anthropic) | Plugin claims | Use anthropic-claude-code repo as primary source |
| MCP Market listings (provisional) | Aggregator | Per-listing provisional status | Snapshot if material; otherwise note + skip |

## Refresh cadence

Per `ADOPTION-SIGNAL-TRACKING-GAP.md` § quarterly refresh:

```bash
# Per-clone refresh
cd refs/competitors/<clone>
git pull --depth 1

# Per-repo metadata refresh
gh api "repos/<owner>/<repo>" --jq '{stars: .stargazers_count, pushed: .pushed_at, license: (.license.spdx_id // "none")}'

# Update this SOURCE-STATUS.md when:
# - stars drift > 5% from last refresh
# - last-push date older than 6 months → flag as "STALE" candidate
# - new repo surfaces from external research → add row + validate
# - deep inspection completes for a CLONED-PENDING row → upgrade to CLONED+INSPECTED
```

`scripts/competitor-refresh.sh` proposed but not yet implemented (P2 per ADOPTION-SIGNAL-TRACKING-GAP).

## Inversion log

Per `ADOPTION-SIGNAL-TRACKING-GAP.md` § notable inversions: cases where adoption signal contradicts quality signal OR vice versa.

| Inversion type | Instance | Date | Notes |
|---|---|---|---|
| Missed-from-clone-set high-adoption | `parcadei/Continuous-Claude-v3` (3.7k★) | 2026-05-25 a.m. | Surfaced by user; not in any prior research pass |
| Missed-from-clone-set high-adoption | `wshobson/agents` (35.9k★) | 2026-05-25 p.m. | Surfaced by user via ChatGPT validation; largest by stars in entire clone set |
| Missed-from-clone-set high-adoption | `alirezarezvani/claude-skills` (16.1k★, 728 SKILLs) | 2026-05-25 p.m. | Surfaced by user via ChatGPT validation; new largest by SKILL count |
| Missed-from-clone-set high-adoption | `VoltAgent/awesome-claude-code-subagents` (20.5k★) | 2026-05-25 p.m. | Surfaced by user via ChatGPT validation; mostly anti-pattern but adoption signal real |
| Star anomaly | `affaan-m/ECC` (191,901★) | 2026-05-25 p.m. | Surfaced + skipped per implausibility check |
| External-research fabrication | `KevinPoorDeveloper/agent-skills` | 2026-05-25 p.m. | ChatGPT-claimed; 404 confirmed |
| External-research description hallucination | `hardwood-hq/hardwood` | 2026-05-25 p.m. | ChatGPT-claimed "Code Review Pyramid"; actual is Apache Parquet lib |
| External-research fabrication | `emaarco/agento-patronum` | 2026-05-25 a.m. | External research-claimed; 404 confirmed |

These instances reinforce `ADOPTION-SIGNAL-TRACKING-GAP` discipline.
