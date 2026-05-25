# Claim Delta — 2026-05-25 (post-clone of 4 missed competitors)

After 21-doc bundle + 3 Gemini rounds + 4 Codex rounds + APPROVED status, user surfaced 5 competitor repos claimed missing from `refs/competitors/`. Verified via `gh api`:

| User claim | Verified? | Stars | Status |
|---|---|---|---|
| `archgate/cli` | ✅ EXISTS | 38 | Cloned 2026-05-25 |
| `parcadei/Continuous-Claude-v3` | ✅ EXISTS | **3785** | Cloned 2026-05-25 |
| `buildingopen/bouncer` | ✅ EXISTS | 4 | Cloned 2026-05-25 (distinct from `claude-bouncer` already cloned) |
| `gemini-cli-extensions/jules` | ✅ EXISTS | 392 | Cloned 2026-05-25 |
| `emaarco/agento-patronum` | ❌ NOT FOUND | — | Fabrication (matches prior `RESEARCH-DELTA.md` finding) |

4 genuine misses. Material impact on 3 existing gap docs + 1 minor impact.

## Affected docs (per-doc delta)

### 1. GOVERNANCE-GAP.md (Gap C boundary-rule config) — **MATERIAL CONTRADICTION**

**Current claim**: contest-refactor's `[[boundary_rules]]` config proposal "takes contest-refactor from ADR-aware citation to executable governance verbatim per doc § 1." Framed as P0 invention with no prior art.

**Reality** (per `refs/competitors/archgate-cli/README.md` + `cli.archgate.dev` docs):

> Archgate has two layers:
> 1. **ADRs as documents** — markdown files with YAML frontmatter stored in `.archgate/adrs/`. Each ADR records a decision: what was decided, why, and what to do and not do.
> 2. **ADRs as rules** — each ADR can have a companion `.rules.ts` file that exports automated checks. Archgate runs these checks against your codebase and reports violations.

archgate is **operational prior art** for "executable governance ingestion." Working CI + pre-commit + agent-feedback layer with 38★, Apache-2.0, OpenSSF Best Practices badge.

**Required revision to GOVERNANCE-GAP**:

- Add archgate-cli to comparator table at top of doc (was: brooks-lint + architecture-review-mcp; now: + archgate-cli)
- Reframe Gap C: NOT a P0 invention; ADOPTING archgate's pattern (ADR + companion executable file). Decide: pair existing `.contest-refactor.toml [[boundary_rules]]` block design with archgate's `.rules.ts` companion file pattern — OR redirect users to archgate as the canonical solution and have contest-refactor just CONSUME archgate output via `.archgate/` directory scan in Step 0 sub-step 7e.
- "contest-refactor leads on rule-of-record citation discipline" strategic insight survives — archgate provides enforcement layer, contest-refactor adds finding-level citation discipline. Both layers complementary.
- New comparator column: archgate stores rules in TS (compiled); contest-refactor's proposed TOML rules are declarative-only. Tradeoff documentation needed.

### 2. CROSS-MODEL-CRITIC-GAP.md — **NEW CATEGORY (Gemini-for-scoring vs Gemini-for-prompting)**

**Current claim**: Gemini DROPPED from supported `--cross-model-critic` providers because Gemini's `-p` requires argv-passed prompt (leaks source via process table). Codex sole verified provider.

**Reality** (per `refs/competitors/buildingopen-bouncer/README.md`):

> Claude cannot wave through unverified work. Another model checks the evidence.
> One install gives you both the automatic Stop hook and the on-demand `/bouncer` skill.
> ```
> User prompt → Claude Code → [Stop Hook] → Gemini 2.5 Flash → Score 1-10
> ```

Bouncer is a Gemini-based Stop hook that **scores Claude's output post-hoc**. Gemini reads files locally (no argv-prompt of source); scores 1-10; threshold-gated. Different mechanism from claude-review-loop's Codex-as-cross-model-Critic.

**Required revision to CROSS-MODEL-CRITIC-GAP**:

- Add Bouncer comparator. **NEW pattern category**: "post-output scoring" vs "pre-output adversarial critic." Bouncer is the first; claude-review-loop is the second.
- Re-evaluate Gemini-drop decision: applies to PROMPT TRANSPORT (argv leak when sending source TO Gemini). Doesn't apply to Bouncer's pattern (Gemini reads files locally, scores). Both Gemini modes are different attack surfaces.
- Two-tier provider support:
  - Pre-output adversarial critic (sends source to provider): Codex stdin verified-supported; Gemini/opencode blocked per earlier Codex round 2 + 3 review
  - Post-output scoring (provider reads files independently, no prompt-borne source): Gemini Flash supported via Bouncer pattern; potentially extend to Codex/opencode equivalents
- Add Bouncer's Stop-hook mechanism to provider-adapters table as a Phase 1.4-equivalent gate (post-routing scoring before final state lands)

### 3. HALT-STATE-GAP.md + STATE-MACHINE-COMPOSITION-APPENDIX.md — **MATERIAL OVERLAP**

**Current claim**: contest-refactor's `LOOP_STATE.json` + `findings_registry.json` + `REVIEW_HISTORY.json` checkpoint mechanics are "gold standard"; "no competitor matches contest-refactor checkpoint mechanics."

**Reality** (per `refs/competitors/continuous-claude-v3/README.md`):

> Continuous Claude transforms Claude Code into a continuously learning system that maintains context across sessions, orchestrates specialized agents, and eliminates wasting tokens through intelligent code analysis.
>
> - Skills: 109
> - Agents: 32
> - Hooks: 30
> - Memory System
> - YAML-based ledgers and handoffs (per Description)

3.7k★, MIT licensed, active. Larger skill ecosystem than levnik (137 SKILLs) or trailofbits (74). Has hooks layer (30) larger than most competitors. Explicit "ledgers and handoffs" mechanism for cross-session state.

**Required inspection**:

- Read `continuous-claude-v3/.claude/hooks/` (or equivalent) for actual ledger/handoff schema
- Compare to contest-refactor's `LOOP_STATE.json` + `LOOP_PHASE_STATE.json` (the latter proposed in STATE-MACHINE-COMPOSITION-APPENDIX)
- Likely finding: continuous-claude-v3's ledgers are session-spanning (Claude Code sessions); contest-refactor's are loop-spanning (within one invocation). Different temporal scope. Both legitimate; not direct competition.
- BUT contest-refactor's HALT-STATE-GAP § "What contest-refactor wins" claims need narrowing — continuous-claude-v3 may have YAML-handoff patterns that contest-refactor's structured-action `halt_handoff.expected_actions[]` should compare against, not dismiss.

**Required revision**:
- Add continuous-claude-v3 to HALT-STATE-GAP comparator table
- Add "session-spanning vs loop-spanning state" framing — both axes valid
- Re-check "no competitor matches contest-refactor checkpoint mechanics" claim against continuous-claude-v3's actual hook implementations
- Consider Phase 12 (Step 12 loop dispatch) handoff pattern: should it emit a YAML ledger entry that future Claude Code sessions can resume from? This is contest-refactor's main weak point per landscape research

### 4. SKILL-TDD-FIXTURES-GAP.md + LEVNIK-AUDIT-SUITE-GAP.md — **POTENTIAL ECOSYSTEM SIZE UPDATE**

**Current framing**: levnik (137 SKILLs) is the largest skill ecosystem in the bundle; orchestrator-worker pattern reference. trailofbits (74 SKILLs) is the second-largest.

**Reality**: continuous-claude-v3 has 160 SKILL.md files (vs claimed 109 in README badge — file count exceeds badge). Now THE largest skill ecosystem in the bundle.

**Required revision** (minor): update INVENTORY ordering. Update LEVNIK-AUDIT-SUITE-GAP's "largest competitor ecosystem" framing if used.

### 5. CLEAN-ENVIRONMENT-VALIDATION-GAP.md — **MINOR**

**jules-cli-ext** shows Gemini-CLI-as-Jules-orchestrator pattern. Doesn't expose Jules cloud-VM source. Adds nothing material to clean-env analysis; current gap doc's "Jules cloud-VM mechanism inferred only" framing is correct.

**Required revision**: add jules-cli-ext to "verified-but-tangential" notes; correct framing unchanged.

## Adoption-Signal Tracking Discipline (per ADOPTION-SIGNAL-TRACKING-GAP)

Verified per `gh api repos/<owner>/<repo>` 2026-05-25:

| Repo | Stars | Last commit | License | Source authority |
|---|---:|---|---|---|
| `archgate/cli` | 38 | 2026-05-25 (today, active) | Apache-2.0 | github-direct + cli.archgate.dev docs |
| `parcadei/Continuous-Claude-v3` | 3785 | 2026-01-26 (4 months stale; check active) | MIT (per badge) | github-direct |
| `buildingopen/bouncer` | 4 | 2026-04-09 (1 month) | per LICENSE file | github-direct |
| `gemini-cli-extensions/jules` | 392 | 2026-05-23 (active) | (official Google) | github-direct |
| `emaarco/agento-patronum` | n/a | n/a | n/a | **NOT FOUND** — fabrication |

continuous-claude-v3 stars (3.7k) inverts the prior "underrated quality vs adoption" framing — it's HIGH adoption + previously-missed in our research. This is the kind of finding ADOPTION-SIGNAL-TRACKING-GAP § "Notable inversions" should track.

## Recommended next steps

1. **Inspect 3 high-impact clones** (parallel agent dispatch):
   - `archgate-cli/`: extract `.rules.ts` schema, ADR markdown schema, CI/pre-commit hook integration
   - `continuous-claude-v3/`: extract hook layer (30 hooks), ledger format, handoff schema, agent registry (32 agents)
   - `buildingopen-bouncer/`: extract Stop-hook script, Gemini scoring prompt, threshold mechanism, on-demand /bouncer skill

2. **Revise affected gap docs**: GOVERNANCE-GAP (Gap C reframe), CROSS-MODEL-CRITIC-GAP (add post-output-scoring category + un-drop Gemini Flash for that mode only), HALT-STATE-GAP + STATE-MACHINE-COMPOSITION-APPENDIX (acknowledge continuous-claude-v3 ledger pattern), INVENTORY (skill counts + comparator tables)

3. **Run additional Codex/Gemini review round** focused on the 3 revised docs only (not full bundle re-review)

4. **Update INVENTORY.md** § "Coverage map" to reflect new comparators

## Verification trail

`gh api` queries run 2026-05-25:
```bash
for repo in archgate/cli parcadei/Continuous-Claude-v3 buildingopen/bouncer gemini-cli-extensions/jules emaarco/agento-patronum; do
  gh api "repos/$repo" --jq '{full: .full_name, stars: .stargazers_count, desc: .description, pushed: .pushed_at}'
done
```

First 4 returned valid JSON. Fifth returned 404. Cross-verified via `gh search repos "agento-patronum"` (no results) + `gh search repos "patronum claude"` (no results).

## Lessons for review discipline

The 7-round adversarial review (3 Gemini + 4 Codex) did NOT catch these 4 missing competitors because both reviewers worked from the bundle text + competitor clones IN refs/competitors/. They couldn't surface competitors that weren't in either location. `REVIEW-PROMPT.md` Class 2 ("Missed competitors") — merged from former SOURCE-VERIFICATION-PROMPT.md 2026-05-25 — explicitly hunts for this — but only within ALREADY-cloned repos.

To catch missed-from-clone-set competitors, a reviewer needs:
- Web search authority OR knowledge of additional competitors from training
- The user's external research pipeline (which surfaced these 4)

This is a structural limit of source-grounded review: can only verify what's in the source pool. Mitigation: add `ADOPTION-SIGNAL-TRACKING-GAP` quarterly competitor-refresh discipline (already documented).
