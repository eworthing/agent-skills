# Source-Verification Prompt — fresh LLM conversation

Copy everything below the `---BEGIN PROMPT---` line and paste into a fresh LLM conversation. Reviewer should have **filesystem read access** to the agent-skills repo at `/Users/Shared/git/agent-skills/` (or equivalent path).

Different from `REVIEW-PROMPT.md` (which is for the `peer-plan-review` skill harness — internal consistency check). This prompt asks for **source-vs-claim verification**: do the gap docs' claims survive inspection of the actual contest-refactor skill source AND the competitor clones?

---BEGIN PROMPT---

You are evaluating a 21-doc competitive gap analysis for `contest-refactor`, an autonomous Actor-Critic refactoring loop skill. The gap docs claim to compare contest-refactor against ~30 inspected competitor skills/tools, plus respond to arXiv:2511.04824's empirical findings on agentic refactoring.

**Your job: hunt for inaccuracies by cross-checking gap-doc claims against actual source code.**

The analysis has already survived 7 rounds of cross-LLM adversarial review (3 Gemini Pro + 4 Codex GPT-5.4 xhigh, both APPROVED). Those rounds focused on internal consistency, schema composability, cross-doc references, and operational/security concerns. **You are checking a different axis: do the source claims hold?**

## What to read

### Gap analysis docs (the artifacts under review)

`/Users/Shared/git/agent-skills/analysis/contest-refactor/` — 21 markdown files. Start with:

- `INVENTORY.md` — coverage map: which mechanism is covered by which gap doc + which competitor sources it
- `STATE-MACHINE-COMPOSITION-APPENDIX.md` — single source of truth for the proposed end-to-end loop pipeline
- `RESEARCH-DELTA.md` — synthesis pass that absorbed 8 missed competitors + arXiv paper
- `LEVNIK-AUDIT-SUITE-GAP.md` — deepest single-competitor analysis (levnik 35+ workers)

Then 17 more `*-GAP.md` files covering specific mechanisms.

### contest-refactor skill source (truth set for "contest-refactor already has X" claims)

`/Users/Shared/git/agent-skills/contest-refactor/` — the skill being analyzed. Authoritative paths:

- `SKILL.md` — state machine (Step -1 / Step 0 / Step 1 Critic / Step 2 Architect / Step 3 Execution + Halting Conditions + Continuation Discipline)
- `canon/*.toml` — 9 canonical enum files: `states`, `halt-subtypes`, `finding-statuses`, `retirement-reasons`, `severity-anchors`, `scorecard-dimensions`, `dependency-categories`, `fixture-rule-kinds`, `validation-gates`, `verdicts`
- `references/method.md` — 10-step Critic Method + Evidence Chain + Simplify Pressure Test
- `references/validation.md` — 31 hard gates G1-G31 + 8 quality passes Q1-Q8
- `references/output-format-json.md` — `CURRENT_REVIEW.json` schema (the gap docs propose `schema_version: 4` additions; verify the v3 baseline)
- `references/output-format-state-schemas.md` — `LOOP_STATE.json`, `findings_registry.json`, `REVIEW_HISTORY.json` schemas
- `references/halt-handoff.md` — structured `halt_handoff{text, expected_actions[]}` object + drift-matcher
- `references/resume-detection.md` — Resume Precedence Matrix (Cases A-E)
- `references/trust-model.md` — instruction-vs-evidence precedence + Loop Isolation + payload-as-evidence-only rule
- `references/implementation-reviewer.md` — Reviewer subagent prompt + verdict schema
- `references/provider-adapters.md` — Claude Code / Codex / opencode / unknown provider matrix
- `references/architecture-rubric.md` — Score Anchors, Severity Anchors, Unified Seam Policy
- `references/lens-apple.md` + `references/lens-generic.md`
- `references/project-config.md` + `.contest-refactor.example.toml`
- `scripts/*.py` — `validate-artifact.py`, `validate-repo.py`, `validate-fixtures.py`, `_canon.py`, `_fingerprint.py`
- `evals/` — existing artifact-smoke fixtures (12 fixtures per a gap-doc claim — verify the count)

### Competitor source clones (truth set for "competitor X has feature Y" claims)

`/Users/Shared/git/agent-skills/refs/competitors/` — 30 depth-1 git clones. See the `README.md` in that dir for the per-clone catalog with size + SKILL count + relevance. Key clones the gap docs cite heavily:

- `claude-review-loop/` — Stop-hook + Codex multi-agent critic (closest live competitor; ~619★ per gap docs)
- `levnik-skills/plugins/codebase-audit-suite/` — 35+ specialty audit workers + shared contract files in `shared/references/`
- `trailofbits-skills/plugins/fp-check/` — Stop+SubagentStop hook prompts in `hooks/hooks.json`
- `anthropic-claude-code/plugins/{code-review,pr-review-toolkit}/` — official Anthropic plugins (sparse-checkout: `plugins/` only)
- `mattpocock-skills/skills/improve-codebase-architecture/` — deletion test prose
- `superpowers/skills/` — RGR doctrine, worktree isolation, skill-TDD (no fixtures)
- `forensic-skills/.claude/skills/forensic-hotspot-finder/` + `forensic-refactoring-roi/` — ROI formulas
- `grill-for-claude/codex/skills/grill-core/` — `[GOOD]` enum + untrusted-content posture
- `rohitg00-toolkit/agents/developer-experience/refactoring-specialist.md` — atomic-step + per-pattern-commit prose
- `anthropic-security-review/.claude/commands/security-review.md` — 12-item hard exclusion list + HIGH-confidence-only filter
- `pr-agent/pr_agent/{algo,tools,settings}/` — hunk parsing + dynamic-context + self-reflection
- `aider/aider/` — repo-map + edit-format coders
- `cygnusfear-stuff/agents/code-reviewer.md` — 6-pass protocol
- `ralph-wiggum/` — `<promise>COMPLETE</promise>` sentinel + `.ralph/` state dir
- `awesome-code-review/SKILL.md` — 5-phase progressive-disclosure design
- `agentlint/src/scanner.sh` + `standards/evidence.json` — 51 deterministic checks + circuit-breaker H3
- `claude-bouncer/hooks/` — PreToolUse pattern matchers
- `prism/prism/` — Python observability tool (NOT runtime intervention; verify gap-doc framing)
- `plandex/app/` — Go agent server (plan state, branching)
- `goose/` — block/goose agent framework
- `architecture-review-mcp/src/repo_architecture_mcp/` — NetworkX AST graphs
- `brooks-lint/` + `logic-lens/` + `skills-janitor/` + `gstack/` + others — sampled less deeply

## Failure modes to hunt

### Class 1: Source mismatch (HIGHEST priority)

For each "competitor X has feature Y" or "contest-refactor already has Z" claim:

1. Open the cited source file
2. Verify the claim matches what's actually there
3. If summarized rather than quoted: re-read the summary against source, flag paraphrasing drift
4. Flag any cited URL, file path, line number that doesn't resolve

Specific high-value spot-checks:

- **claude-review-loop**: verify `hooks/stop-hook.sh` actually has the claimed retry cap of 2, fail-open ERR trap, and `--dangerously-bypass-approvals-and-sandbox` default (RESEARCH-DELTA + GATES-GAP + CROSS-MODEL-CRITIC-GAP all cite this).
- **trailofbits fp-check `hooks/hooks.json`**: GATES-GAP pastes claimed-verbatim hooks.json. Diff against the actual file.
- **anthropic code-review plugin**: CRITIC-INDEPENDENCE-GAP claims "4 parallel agents (2 Sonnet CLAUDE.md auditors + 1 Opus bug + 1 Opus logic/security)". Verify against `plugins/code-review/commands/code-review.md`.
- **levnik audit_summary_contract.md**: LEVNIK-AUDIT-SUITE-GAP claims `"status": "completed"` is valid, `"complete"` invalid (strict enum). Verify in source.
- **levnik audit_scoring.md**: same doc claims formula `penalty = critical*2.0 + high*1.0 + medium*0.5 + low*0.2`. Verify.
- **mattpocock deletion-test**: ARXIV-AGENTIC-REFACTORING-GAP and others quote the deletion test verbatim from `mattpocock-skills/skills/improve-codebase-architecture/SKILL.md`. Verify lines + phrasing.
- **forensic-skills formulas**: ROI-PRIORITIZATION-GAP quotes `Risk Score = Normalized Change Frequency × Normalized Complexity Factor` and the 4-tier ROI bands. Verify against `forensic-hotspot-finder/SKILL.md` + `forensic-refactoring-roi/SKILL.md`.
- **rohitg00 refactoring-specialist**: TRACEABILITY-GAP quotes atomic-step + characterization-test + per-pattern-commit prose. Verify line numbers + exact phrasing in `agents/developer-experience/refactoring-specialist.md`.
- **grill-for-claude `[GOOD]` enum**: SCHEMA-GAP Gap 7 + GOVERNANCE-GAP cite specific lines + verbatim untrusted-content rule. Verify in `codex/skills/grill-core/SKILL.md`.
- **anthropic-security-review** 12 hard exclusions: verify count + content against `.claude/commands/security-review.md`.
- **opencode `--prompt-file` flag**: CROSS-MODEL-CRITIC-GAP now marks NOT VERIFIED after Codex caught it (claimed flag doesn't exist in opencode docs). Re-verify in `refs/competitors/` if a clone exists, or note that opencode is not cloned.
- **pr-agent hunk regex**: TRACEABILITY-GAP cites `@@ -start,size +start,size @@` parser at specific files. Verify.
- **prism**: gap docs frame it as post-mortem analyzer. Verify it's actually read-only Python and not runtime hook.
- **contest-refactor counts**: gap docs claim "31 hard gates G1-G31", "8 quality passes Q1-Q8", "5 halt states + 4 subtypes", "5 retirement reasons", "9 scorecard dimensions", "12 evals fixtures". Spot-check by reading `references/validation.md`, `canon/*.toml`, `evals/`.

### Class 2: Missing competitors / under-inspected sources

The gap docs cite ~30 competitors. The source landscape research originally named more. Some clones are present but never inspected per-doc:

- `gstack/` (57 SKILL.md files; only mentioned in INVENTORY)
- `brooks-lint/` (6 SKILL.md; cited in GOVERNANCE-GAP only)
- `logic-lens/` (6 SKILL.md; barely cited)
- `domscribe/` (1 SKILL.md, 47MB; mentioned in INVENTORY only)
- `plandex/` (60MB Go server; cited mostly in HALT-STATE-GAP)
- `architecture-review-mcp/` (1MB; cited in GOVERNANCE-GAP only)
- `claude-bouncer/` (252KB; cited in GATES-GAP + SPECIALTY-LENS-DISPATCH-GAP only)
- `agentlint/` (11MB; cited mainly for circuit-breaker H3)

Sample 2-3 of these. Do they have mechanisms the gap docs missed entirely? Flag substantive omissions, not just "this exists too."

### Class 3: Logical issues

- Cross-doc contradictions: one doc says X, another says ¬X
- Adoption-order chains: doc A's Phase N depends on doc B's Phase M, but B's Phase M depends on A's Phase N (cycle)
- Schema additions that collide at the JSON top-level (`schema_version: 4` is supposed to be additive across all docs — verify field-name + nesting doesn't collide)
- Gate-number reservations: G34, G34.1 (renamed G43), G35-G47 across multiple docs. Any unintended overlap?
- New canon files proposed: `canon/loop-phases.toml`, `canon/refactoring-patterns.toml`, `canon/tie-kinds.toml`, `canon/confidence-levels.toml`, `canon/area-verdicts.toml`, `canon/boundary-rule-shape.toml`, `canon/critic-status.toml`. Any naming collisions with existing canon files?

### Class 4: Misframed prior reviews

The gap docs cite Gemini Pro + Codex GPT-5.4 review history. Both APPROVED. Verify the docs' summary of those reviews matches the actual review trail — look for inflation ("survived 7 rounds" — that's true; "no remaining issues" — verify the polish-N1/N2 from Gemini round 3 actually applied to the docs; "Codex GPT-5.4 round 4 APPROVED with 0 findings" — true).

### Class 5: arXiv response defensibility

`ARXIV-AGENTIC-REFACTORING-GAP.md` accepts the empirical finding that AI agents do 30.7% rename/retype refactorings. The response: add `refactoring_types[]` audit field, document the bias, propose new 10th scorecard dimension `code_hygiene` for low-level edits.

Is the response defensible, OR does it leave contest-refactor's core "9.5+ architecture-first" pitch implicitly contradicted by other docs that haven't been updated to match? Check whether other docs (e.g., LEVNIK-AUDIT-SUITE-GAP's metric-worship deferral) still implicitly assume contest-refactor produces structural findings as dominant mode.

## Output format

```
# Source-Verification Review

## Verdict
One paragraph. How does the bundle hold up against actual source? Was the prior 7-round adversarial review thorough enough OR did it miss source-mismatch issues only filesystem inspection can catch?

## Class 1: Source mismatches found
- [SM1] (HIGH|MEDIUM|LOW) Gap doc claim:
  Cited as: `<doc-name>:<line>` saying "<quote>"
  Source says: `<source-file>:<line>` actually says "<quote>"
  Severity: paraphrase drift / wrong line number / fabricated detail / etc.

[... one entry per finding ...]

## Class 2: Missed competitors / under-inspected sources
- [MC1] `<clone-dir>/<file>` has mechanism X that gap doc Y should cover but doesn't
  Suggested adoption: add to <doc-name> as <Gap-letter> OR new gap doc <name>

## Class 3: Logical issues
- [LI1] Cross-doc contradiction / cycle / collision
  Evidence: `<doc-A>:<line>` vs `<doc-B>:<line>`
  Recommendation: ...

## Class 4: Misframed prior reviews
- [PR1] Claim about Gemini/Codex history that doesn't match actual review trail

## Class 5: arXiv response defensibility
[your assessment]

## Things the bundle got right
[1-2 sentences max — counterpoint to the criticism above, only the most defensible wins]

## Suggested round
If Class 1 findings are severe (multiple source fabrications), recommend FRESH round-1 with a different reviewer model. If only minor paraphrase drift + a few Class 2 misses, recommend targeted patches. If sound, say so.
```

Hard cap: 2500 words. Cite source file:line for every claim. Prefer **quoting** to summarizing. If a claim is plausibly right but you can't verify without more reading, mark `UNVERIFIED:` and state what you'd need to check.

## Don't

- Don't re-do Gemini's or Codex's prior internal-consistency review. Their findings are already merged.
- Don't fix the docs yourself. Reviewer-only.
- Don't summarize what each gap doc says (the author wrote them).
- Don't speculate about source you didn't read. Better to say "didn't check X" than to invent.
- Don't grade on "would I have written it this way." Grade on "does the source support the claim."

## Why this prompt exists

The 7 prior adversarial review rounds verified the bundle is **internally consistent**. None of them ran a filesystem cross-check at scale. This is the dimension still under-tested. Likely findings: paraphrase drift, line-number drift, occasional fabricated details that survived because reviewers trusted the prose.

If you find none, that's a strong signal the bundle is publication-ready. If you find many, that's the next class of issues to remediate before treating the bundle as authoritative.

---END PROMPT---

## Notes for the person passing this prompt

- Paste everything between BEGIN/END markers into a fresh LLM conversation (Claude Sonnet 4.6 / Opus 4.7 from a fresh session, or GPT-5.5, or a different Gemini model)
- Reviewer needs **filesystem read access** to `/Users/Shared/git/agent-skills/`. Without it, they can only review the gap doc text (defeats the purpose).
- Best paired with a model that has aggressive Read/Grep tool budget — this is a scan-heavy task, not a reasoning-heavy task.
- If using `peer-plan-review` harness: this prompt overlaps but isn't identical to the `REVIEW-PROMPT.md` already in this dir. That one tests internal consistency; this one tests source veracity. Both valuable; run separately.
- Cross-model: if Claude Opus authored the bundle, pair this prompt with a non-Claude reviewer (Gemini, GPT, Llama). Same-model blindspots persist for source-paraphrase drift just like they do for reasoning errors.
