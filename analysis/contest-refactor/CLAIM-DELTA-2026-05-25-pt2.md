# Claim Delta — 2026-05-25 part 2 (post-T1/T2/T3 expansion, method/process mining)

After morning's CLAIM-DELTA (4 verified clones + 1 fabrication), user surfaced a ChatGPT response listing 24 additional candidate repos. Per user directive: validate skeptically; expansion focus = method/process discovery, NOT lens/language/security coverage.

## ChatGPT-claim validation results

21 GitHub repos validated via `gh api`:

| Bucket | Count | Items |
|---|---:|---|
| ✅ Already in clone set under different alias | 5 | `mattpocock/skills`→mattpocock-skills, `xiaolai/grill-for-claude`→grill-for-claude, `AlabamaMike/forensic-skills`→forensic-skills, `anthropics/claude-code-security-review`→anthropic-security-review (git remote confirmed), `awesome-skills/code-review-skill`→awesome-code-review (git remote confirmed) |
| ✅ Verified + cloned (T1/T2/T3) | 13 | listed below |
| ❌ NOT FOUND (fabrication) | 1 | `KevinPoorDeveloper/agent-skills` (404) |
| ⚠️ Hallucinated description | 1 | `hardwood-hq/hardwood` — actual repo is Apache Parquet Java lib, not "Code Review Pyramid" tool. ChatGPT hallucinated. |
| ⚠️ Star anomaly (skip pending forensic) | 1 | `affaan-m/everything-claude-code` → redirects to `affaan-m/ECC`; reports **191,901 stars** (implausibly high — Linux kernel ~165k for reference). Almost certainly star manipulation. |

ChatGPT's 24-item "must-add" list contained 21% false positives (already-cloned with alias mismatch) + 4% fabrications + 4% hallucinated metadata. Net 17 genuine candidates → 13 cloned per user T1+T2+T3 directive.

## User directives applied (2026-05-25)

1. **Archgate prereq directive**: GOVERNANCE-GAP Gap C reframed; default = C.2 TOML-only (no runtime dep); C.3 hybrid demoted to opt-in `--ingest-archgate` flag; C.1 full-adopt dropped.
2. **Method/process focus**: T1 high-impact 6 clones deep-inspected for novel methods. T2 security-review (4 clones) + T3 language-domain (3 clones) NOT deep-inspected per user directive.

## 13 clones added

| Clone | Stars | License | Inspection depth | Status |
|---|---:|---|---|---|
| alirezarezvani-claude-skills | 16,146 | MIT | DEEP | Method-extracted (see below) |
| wshobson-agents | 35,918 | MIT | DEEP | Method-extracted |
| VoltAgent-awesome-claude-code-subagents | 20,508 | MIT | DEEP | Mostly anti-pattern + 1 positive |
| pauhu-claude-codex-review | 0 | MIT | DEEP | Cross-model critic comparator |
| TimmyZinin-codex-review | 0 | MIT | DEEP | Cross-model critic comparator |
| fastruby-tech-debt-skill | 5 | MIT | DEEP | Tech-debt ROI comparator |
| shadowX4fox-solutions-architect-skills | 7 | MIT | NOT inspected | T2 — defer |
| dstiliadis-security-review-skill | 8 | MIT | NOT inspected | T2 — user directive (no security expansion) |
| Dilaz-security-review-skill | 6 | MIT | NOT inspected | T2 — user directive |
| MaTriXy-github-review-skill | 3 | none | NOT inspected | T2 — user directive |
| piomin-claude-ai-spring-boot | 1,175 | Apache-2.0 | NOT inspected | T3 — user directive (no language expansion) |
| elvismdev-claude-wordpress-skills | 191 | MIT | NOT inspected | T3 — user directive |
| rknall-claude-skills | 49 | none | NOT inspected | T3 — user directive |

## Novel methods extracted (T1 deep inspections)

### From wshobson/agents (35.9k★) — STRONG

| # | Method | Description | Affects |
|---|---|---|---|
| W1 | **Adapter-driven multi-harness gen** | One markdown source → `tools/adapters/{base,codex,cursor,opencode,gemini}.py` transforms per harness. Outputs gitignored. Adapters handle YAML frontmatter, Codex 8KB body cap, OpenCode permission blocks, Gemini TOML, Cursor `.mdc`. Per-harness model alias mapping in `tools/adapters/capabilities.py`. | NEW POTENTIAL GAP DOC — `MULTI-HARNESS-ADAPTER-GAP.md`. contest-refactor today is bash-portable (single source for Claude Code) but no adapter pattern for cross-harness distribution. |
| W2 | **3-layer evaluation framework** | Layer 1 static (<2s, deterministic, 7 weighted sub-checks: frontmatter_quality 32% + orchestration_wiring 23% + progressive_disclosure 14% + structural_completeness 10% + token_efficiency 9% + ecosystem_coherence 6% + harness_portability 6%) + Layer 2 LLM judge (~30s, 4 calls semantic) + Layer 3 Monte Carlo (~2min, 50-100 runs with Wilson CI / Bootstrap CI / Clopper-Pearson CI). Composite × anti-pattern penalty. | SCHEMA-GAP (current binary G1-G31 gates). Could augment with continuous scoring layer + confidence intervals. NEW POTENTIAL section "Continuous Scoring Augmentation." |
| W3 | **File-ownership boundary model** | agent-teams plugin: per-agent exclusive file ownership prevents parallel merge conflicts. Interface contracts at boundaries. | PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP — could specify per-critic ownership of output files (avoid race on `critic-1-output.md` + `critic-2-output.md` writes). |
| W4 | **`make garden` drift detection** | CI-enforced detection of oversize skills, dead refs, orphaned plugins, marketplace orphans. Sorted by severity. | contest-refactor has G3 SKILL size gate per-skill but no bundle-wide drift detector. Low priority. |
| W5 | **Model-tier-as-routing-policy** | Tier 1 Opus (orchestrators, architecture, security, critical) / Tier 2 inherit (user choice) / Tier 3 Sonnet (workers: docs, testing, debugging) / Tier 4 Haiku (fast ops). | provider-adapters.md — currently `loop_model` + `reviewer_model` per loop; could add explicit tier mapping. |

### From alirezarezvani-claude-skills (16.1k★, 728 SKILLs — NEW LARGEST) — STRONG

| # | Method | Description | Affects |
|---|---|---|---|
| A1 | **`context: fork` inter-skill contract** | Parent skill invokes sub-skill with `context: fork` in YAML frontmatter → fresh forked context → returns ≤200-word digest → parent never sees child's ingestion artifacts. Eliminates context pollution. | STATE-MACHINE-COMPOSITION-APPENDIX phase boundaries (Critic 1.0 → Validator 1.1 → Cross-Model 1.2 → Routing 1.4) currently single-context; could use `context: fork` between phases. NEW POTENTIAL: per-phase context isolation. |
| A2 | **Signal-based router + Matt-Pocock-forcing-question** | Orchestrator detects keyword signal classes; 2 signals = confident route; 1 signal = single forcing question with recommended answer; never silent post-question. Routes return ≤200-word digest citing canon. | NEW POTENTIAL GAP DOC — routing discipline for contest-refactor's Critic Phase findings (which lens / which subagent). |
| A3 | **Industry-profile-tuned references** | Python tools expose `--profile {saas,fintech,healthcare,enterprise}` flag to re-weight scorecards. References are structured markdown with profile-specific weighted tables. | SPECIALTY-LENS-DISPATCH-GAP — current lens system (apple/generic) could extend to industry profiles. Out of scope per user directive. |
| A4 | **Sync-script-driven cross-harness** | Symlinks + index generation via stdlib Python scripts (sync-codex-skills.py, sync-gemini-skills.py, sync-hermes-skills.py, sync-vibe-skills.py). Single source-of-truth in domain folders. Simpler alternative to wshobson's adapter pattern. | Same as W1; alternative implementation. Less powerful (just symlinks vs transforms) but simpler. |

### From VoltAgent (20.5k★) — MOSTLY ANTI-PATTERN + 1 POSITIVE

| # | Method | Description | Affects |
|---|---|---|---|
| V1 | **codebase-orchestrator weighted-priority + diff-preview + approval-gate** | Weighted priority axis: security → bugs → arch → perf → style. Human-approval gates before execution. Diff previews. Deterministic fallback strategies (large file summarization, permission denial, context pruning). Structured JSON output. | NEW POTENTIAL — weighted priority axis is novel; contest-refactor uses Critic-assigned 1-3 without explicit weighting. ROI-PRIORITIZATION-GAP could absorb. |
| V2 | **agent-organizer + multi-agent-coordinator split** | Task decomposition + capability matching SEPARATE from execution governance (deadlock prevention, message routing, fault recovery). Prevents single mega-orchestrator from handling both planning + execution. | Out of scope for contest-refactor (single Critic-Actor split is sufficient). |
| V3 anti-pattern | **"context-manager" magical-shared-state** | 154 agents call "context manager" for state with no formal contract. Confirmed anti-pattern. | **VALIDATES contest-refactor's structured LOOP_STATE.json + findings_registry.json + CURRENT_REVIEW.json discipline as superior.** No revision needed; reinforces existing direction. |
| V4 anti-pattern | **"Senior X" generic prompts** | Generic role openings with checklists of outcome assertions (no concrete deliverable schemas). Confirmed anti-pattern. | VALIDATES contest-refactor's typed-schema discipline. |

### From pauhu + TimmyZinin (CROSS-MODEL-CRITIC comparators) — STRONG VALIDATION

| # | Method | Description | Affects |
|---|---|---|---|
| C1 | **TimmyZinin uses stdin already** | `codex exec ${CODEX_FLAGS} - < /tmp/codex-review-prompt-${TIMESTAMP}.md`. Confirms our CROSS-MODEL-CRITIC-GAP stdin recommendation is industry pattern, not invention. | CROSS-MODEL-CRITIC-GAP — add TimmyZinin as positive prior art for stdin invocation. |
| C2 | **TimmyZinin pre/post git-status verification** | Snapshots state before/after Codex run; warns user if files modified. Belt-and-suspenders for read-only enforcement. | CROSS-MODEL-CRITIC-GAP — add to Security & Trust section as recommended additional verification. |
| C3 | **TimmyZinin hard constraints in prompt** | Explicit prohibitions on file writes, git mutations, dependency installs IN THE PROMPT (not just sandbox). | CROSS-MODEL-CRITIC-GAP — already covered by our trust-model carry-forward, but reinforced. |
| C4 | **TimmyZinin 600s timeout** | Hard upper bound. | CROSS-MODEL-CRITIC-GAP — current proposal `timeout_seconds = 90`; TimmyZinin's 600 is much more generous. Discuss tradeoff. |
| C5 | **TimmyZinin output schema** | `VERDICT: APPROVED \| NEEDS_CHANGES` + severity-tagged findings + file:line refs. | CROSS-MODEL-CRITIC-GAP — aligns with our proposed schema; cross-reference. |
| C6 | **Pauhu graceful fallback** | If Codex unavailable, falls back to direct `npx tsc + eslint`. Different model from TimmyZinin's fail-hard. | CROSS-MODEL-CRITIC-GAP — `fail_open` discussion already covers; add Pauhu as fallback-to-local-tools precedent. |

### From fastruby (5★) — MEDIUM

| # | Method | Description | Affects |
|---|---|---|---|
| F1 | **Coverage prerequisite** | Forces `COVERAGE=true bundle exec rspec` before tech-debt analysis. Ensures data freshness. | contest-refactor Step 0 could validate test-coverage data exists before backlog ordering. Low priority. |
| F2 | **Pre-audit tool detection** | Checks for SonarQube / Code Climate before running duplicate analysis. | contest-refactor Step 0 could detect competing tools. Low priority. |
| F3 | **No formal ROI scoring** | 5-category Health Score (Security/Dependencies/Complexity/Coverage/Maintainability × 20pts each) + Skunk formula `(Code Smells + Complexity) × Coverage Penalty`. | **VALIDATES forensic-skills' hotspot×complexity as stronger ROI signal** than fastruby's qualitative tiers. ROI-PRIORITIZATION-GAP direction confirmed. |

## Methods that affect existing gap docs (cross-reference)

| Existing gap doc | New method(s) affecting | Recommendation |
|---|---|---|
| CROSS-MODEL-CRITIC-GAP | C1-C6 from pauhu+TimmyZinin + Bouncer (from a.m. CLAIM-DELTA) | Revise: add post-output scoring category + Bouncer + TimmyZinin/pauhu comparators + add C2 git-status verification recommendation |
| SCHEMA-GAP | W2 (3-layer evaluation) | OPTIONAL revision: continuous-scoring augmentation section |
| PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP | W3 (file-ownership) | Revise: per-critic file-ownership boundary mapping |
| ROI-PRIORITIZATION-GAP | V1 (weighted priority axis) + F3 (fastruby validation) | OPTIONAL revision: add weighted-priority-axis option (security→bugs→arch→perf→style) |
| HALT-STATE-GAP + STATE-MACHINE-COMPOSITION-APPENDIX | A1 (`context: fork`) + continuous-claude-v3 (a.m.) | Revise: temporal scope framing + phase-context-isolation option |
| GOVERNANCE-GAP | (archgate per a.m. CLAIM-DELTA) | DONE 2026-05-25: Gap C reframed C.1/C.2/C.3 → C.2 default per user directive |
| ADOPTION-SIGNAL-TRACKING-GAP | (validates discipline — alirezarezvani 16k★ was previously missed; affaan-m/ECC star anomaly = anti-signal) | OPTIONAL revision: add "star anomaly detection" sub-discipline + note this missed-then-found instance as Inversion #2 |

## Potential NEW gap docs (require user authorization)

| Proposed | Rationale | Priority |
|---|---|---|
| MULTI-HARNESS-ADAPTER-GAP | W1 + A4 — wshobson adapters + alirezarezvani sync-scripts both achieve cross-harness from single source. contest-refactor currently bash-portable (single source for Claude Code) without adapter discipline. Question: should contest-refactor target multi-harness distribution? | P2 (out of scope for autonomous-refactor-loop focus; defer unless user requests) |
| PHASE-CONTEXT-ISOLATION-GAP | A1 — `context: fork` between Critic 1.0 / Validator 1.1 / Cross-Model 1.2 / Routing 1.4 phases could eliminate cross-phase pollution. Currently single context across phases. | P1 (if isolation improves Critic-validator independence) |
| CONTINUOUS-SCORING-AUGMENTATION | W2 — Monte Carlo + LLM judge + static layers with confidence intervals; complements binary G1-G31 gates. | P2 (additive nice-to-have; gates work fine) |
| ROUTING-DISCIPLINE-GAP | A2 — signal-based router + forcing-question pattern for Critic's specialty-lens selection. | P2 (current contest-refactor lens detection is heuristic; could be more disciplined) |

None of these are urgent. All require user authorization before scoping.

## Updates to ADOPTION-SIGNAL-TRACKING

Per ADOPTION-SIGNAL-TRACKING-GAP discipline, document the validation findings:

| Inversion type | Instance | Action taken |
|---|---|---|
| Missed-from-clone-set high-adoption | alirezarezvani (16.1k★, 728 SKILLs) and wshobson (35.9k★, 191 agents) — neither in prior 22-clone set despite massive adoption | Added 2026-05-25 p.m. via T1 expansion |
| Star anomaly | `affaan-m/ECC` reports 191,901 stars (implausibly high) | Skipped pending forensic; documented in README "Hallucinated descriptions" section |
| External-research fabrication | `KevinPoorDeveloper/agent-skills` (404) | Documented in README "Fabrications" section + `analysis/contest-refactor/CLAIM-DELTA-2026-05-25-pt2.md` (this doc) |
| External-research description hallucination | `hardwood-hq/hardwood` (real repo, wrong description) | Documented in README "Hallucinated descriptions" section |

These instances reinforce ADOPTION-SIGNAL-TRACKING discipline: quarterly competitor refresh + adoption-vs-quality decoupling + star-anomaly detection.

## Verification trail

`gh api` queries run 2026-05-25 p.m.:

```bash
for repo in wshobson/agents VoltAgent/awesome-claude-code-subagents pauhu/claude-codex-review TimmyZinin/codex-review fastruby/tech-debt-skill dstiliadis/security-review-skill Dilaz/security-review-skill MaTriXy/github-review-skill Jeffallan/claude-skills alirezarezvani/claude-skills shadowX4fox/solutions-architect-skills rknall/claude-skills piomin/claude-ai-spring-boot elvismdev/claude-wordpress-skills citypaul/.dotfiles solatis/claude-config affaan-m/everything-claude-code KevinPoorDeveloper/agent-skills hardwood-hq/hardwood awesome-skills/code-review-skill anthropics/claude-code-security-review; do
  gh api "repos/$repo" --jq '{full, stars, pushed, lang, license, desc}'
done
```

Alias-confirmation queries:

```bash
cd refs/competitors/anthropic-security-review && git remote get-url origin
# → https://github.com/anthropics/claude-code-security-review.git
cd refs/competitors/awesome-code-review && git remote get-url origin
# → https://github.com/awesome-skills/code-review-skill.git
```

## Recommended next steps (pending user authorization per step)

1. **Revise CROSS-MODEL-CRITIC-GAP** to incorporate Bouncer (a.m.) + pauhu + TimmyZinin findings — pre/post-output category split + stdin-as-industry-pattern confirmation + git-status verification + fail_open variants. (Task #24)
2. **Revise HALT-STATE-GAP + STATE-MACHINE-COMPOSITION-APPENDIX** for continuous-claude-v3 (a.m.) + temporal scope framing + optional `context: fork` adoption. (Task #25)
3. **Decide on NEW gap docs**: MULTI-HARNESS-ADAPTER, PHASE-CONTEXT-ISOLATION, CONTINUOUS-SCORING-AUGMENTATION, ROUTING-DISCIPLINE.
4. **Optional**: deep-inspect T2 + T3 clones if user reverses no-language/no-security-expansion directive.
5. **Optional**: write SOURCE-STATUS.md scaffold (Task #30) for ongoing tracking matrix per ChatGPT proposal.
6. Commit all revisions.

## Skipped per user directive

- T2 security-review deep inspections (dstiliadis, Dilaz, MaTriXy) — no security coverage expansion.
- T3 language-domain deep inspections (piomin, elvismdev, rknall) — no language coverage expansion.
- shadowX4fox-solutions-architect-skills — deferred T2; could be inspected later if architecture-doc workflow methods needed.
- Adopting archgate-cli as runtime dep — per user prereq directive.
- Cloning suspicious / fabricated repos (KevinPoorDeveloper, hardwood-hq, affaan-m/ECC).
- Cloning vendor commercial sources (Cursor BugBot, Greptile, DeepSource, etc.) — already covered by ADOPTION-SIGNAL-TRACKING vendor-self-published flagging.
