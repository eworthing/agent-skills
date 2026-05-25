# Peer-Review Prompt — contest-refactor competitive gap analysis

Copy everything below the `---BEGIN PROMPT---` line and paste into another LLM (Codex CLI, Gemini CLI, GPT-5, opencode, etc.). The reviewing LLM should have read access to the `/Users/Shared/git/agent-skills/` repo and its `refs/competitors/` clones.

---BEGIN PROMPT---

You are reviewing a competitive gap analysis I produced for `contest-refactor`, an autonomous Actor-Critic refactoring loop skill. The analysis compares contest-refactor's existing mechanisms against ~22 cloned competitor repos (PR review tools, agent skills, MCP servers, RGR frameworks). Six gap-analysis markdown files were written, each covering one mechanism the source competitive-landscape doc flagged as P0/P1.

I want a HARD review. Not validation. I want you to find:

1. Claims I overstated or that the source code doesn't actually support
2. Gaps I missed entirely (mechanisms competitors have that I didn't surface)
3. Adoption recommendations that don't compose with each other or with contest-refactor's existing design
4. Schema additions that would break existing invariants
5. Order-of-adoption mistakes (something I labeled "quick win" that's actually high-risk)
6. Competitors I should have inspected but didn't (the analysis covers 22 clones; the source doc named more)
7. Places where my "contest-refactor already wins" claims rest on contest-refactor docs without checking the competitor source carefully enough

Default skeptical. Quote file paths and line numbers for every criticism. If a claim seems plausible but unverified, mark it `UNVERIFIED:` and say what evidence would confirm or refute. Do not be polite. Brief praise only where I avoided a mistake an average reviewer would make.

## Files to review

All paths under `/Users/Shared/git/agent-skills/refs/competitors/`:

| File | Subject | Headline claim |
|---|---|---|
| `INVENTORY.md` | 22-repo inventory + skill counts | maps doc P0/P1 mechanisms to competitors to inspect first |
| `SCHEMA-GAP-CONTEST-REFACTOR.md` | Finding schema | Add `confidence`, `severity_rationale`; reserve `critic_source` + dedup fields |
| `CRITIC-INDEPENDENCE-GAP.md` | Critic independence | Split Critic+Actor into 2 subagent dispatches per loop |
| `HALT-STATE-GAP.md` | Halt taxonomy + checkpoint state | contest-refactor "gold standard" on checkpoint mechanics; add `--worktree` opt-in + `critic_unfounded` subtype |
| `GOVERNANCE-GAP.md` | Executable governance ingestion | Add lint-config ingestion, CI workflow parsing, `[[boundary_rules]]` config |
| `TRACEABILITY-GAP.md` | Changed-line traceability | Add `changed_hunks[]` + `tie_kind` enum + new gate G34 |
| `GATES-GAP.md` | Forced-completion gates | Add `hooks/hooks.json` for Stop + SubagentStop |

Source competitive-landscape doc (the analysis is anchored to its P0/P1 priorities) was at `/Users/pl/Downloads/contest_refactor_competitive_landscape_consolidated.md` — may no longer exist; key claims about it are quoted inside the gap files.

## contest-refactor baseline you must spot-check

Before believing my "contest-refactor already has X" claims, verify against the actual skill source at `/Users/Shared/git/agent-skills/contest-refactor/`:

- `SKILL.md` (state machine: Step -1 / Step 0 / Step 1 Critic / Step 2 Architect / Step 3 Execution)
- `canon/*.toml` (9 canonical enum/taxonomy files — states, halt-subtypes, finding-statuses, retirement-reasons, severity-anchors, scorecard-dimensions, dependency-categories, fixture-rule-kinds, validation-gates, verdicts)
- `references/method.md` (10-step Critic method, Evidence Chain, Simplify Pressure Test)
- `references/validation.md` (31 hard gates G1-G31 + 8 quality passes Q1-Q8)
- `references/output-format-json.md` (CURRENT_REVIEW.json schema)
- `references/output-format-state-schemas.md` (LOOP_STATE.json, findings_registry.json, REVIEW_HISTORY.json)
- `references/halt-handoff.md` (structured halt_handoff object, expected_actions[])
- `references/resume-detection.md` (Resume Precedence Matrix, Cases A-E)
- `references/trust-model.md` (instruction vs evidence precedence, Loop Isolation, payload-as-evidence-only rule)
- `references/implementation-reviewer.md` (Reviewer subagent prompt + verdict schema)
- `references/provider-adapters.md` (Claude Code / Codex / opencode / unknown provider matrix)
- `references/architecture-rubric.md` (Score Anchors, Severity Anchors, Unified Seam Policy, 9.5+ threshold)
- `references/lens-apple.md` + `references/lens-generic.md`
- `references/project-config.md` + `.contest-refactor.example.toml`
- `scripts/validate-artifact.py` + `scripts/validate-repo.py` + `scripts/validate-fixtures.py` + `scripts/_canon.py` + `scripts/_fingerprint.py`

If any of my "already has" claims doesn't match the source, flag it.

## Competitor sources you must spot-check

For each gap file, sample at least one competitor's source code (not just the gap doc's summary) to confirm my characterization. Repos are at `/Users/Shared/git/agent-skills/refs/competitors/<name>/`:

- **Schema finding:** `coderabbit-skills/`, `anthropic-claude-code/plugins/code-review/`, `trailofbits-skills/plugins/{fp-check,c-review,static-analysis}/`
- **Critic independence:** `open-code-review/`, `anthropic-claude-code/plugins/code-review/`
- **Halt + state:** `plandex/app/`, `prism/prism/`, `superpowers/skills/`
- **Governance:** `brooks-lint/skills/`, `architecture-review-mcp/src/`
- **Traceability:** `pr-agent/pr_agent/{algo,tools,settings}/`, `aider/aider/`, `anthropic-claude-code/plugins/pr-review-toolkit/`
- **Gates:** `trailofbits-skills/plugins/fp-check/hooks/hooks.json` (paste-checked verbatim in the doc; confirm the paste is faithful)

## Specific failure modes to hunt for

For each gap file, look for these classes of error:

### Misread of competitor source
- Did I claim competitor X has feature Y, when in fact Y is in their marketing/README only and the source disagrees?
- Did I conflate "the doc said" with "the source confirms"? Several gap docs quote the source competitive-landscape doc as if it were primary; cross-check competitor source.
- Did I cite a file path that doesn't exist or quote text I didn't actually read?

### Misread of contest-refactor source
- Does contest-refactor actually have feature X that I claimed it lacks? (Easier to overlook in a 35K SKILL.md.)
- Did I cite a gate (G1-G31) by number against a behavior the gate doesn't actually enforce?
- Did I propose a "new" field that's already present (possibly under a different name)?

### Schema composability errors
- The six gap docs all propose additions to `CURRENT_REVIEW.json` for `schema_version: 4`. Do they collide? Do `changed_hunks[]` + `critic_source` + `confidence` + `severity_rationale` + `local_lint_overrides` + `boundary_rules` all compose cleanly with existing fields and existing validation gates G1-G31?
- Does any new field break a "skip-when-X" rule? (G4/G8 suspended for `unverifiable_due_to_build_failure: true` — would `changed_hunks[]` apply on that path?)
- Do new canon files (`canon/confidence-levels.toml`, `canon/tie-kinds.toml`) collide with existing ones?

### Adoption-order pathologies
- I claim several "biggest win, adopt first" items. Are any of them blocked by another gap's adoption?
- Schema Gap recommends a validator subagent (Gap C). Critic Independence Gap recommends splitting Critic+Actor (Gap A). Halt State Gap recommends `critic_unfounded` subtype. Gates Gap recommends hook for Reviewer completeness. Are these correctly sequenced, or is there an ordering trap?
- Traceability Gap A (changed_hunks) shares hunk-parsing layer with HALT-STATE-GAP Gap C (per-hunk partial-accept). Do I describe the shared layer consistently across the two docs?

### "Contest-refactor wins" overclaim
- Each gap doc ends with a "contest-refactor already wins on X" section. For each item: is the claim actually unique to contest-refactor, or do other competitors I didn't inspect closely have it too?
- For each claim, can you point to the competitor source that's missing the feature (proving the win) vs the competitor source where it exists (refuting the claim)?

### Missed competitors
The source doc named these I cloned but inspected lightly or not at all per gap:
- `levnik-skills` (137 SKILLs!) — never inspected per-gap; likely has finding schema + multi-LLM review patterns relevant to SCHEMA-GAP and CRITIC-INDEPENDENCE-GAP
- `mattpocock-skills` (28 SKILLs) — never inspected
- `gstack` (57 SKILLs) — only mentioned in INVENTORY
- `agentlint` — only mentioned for "linter for agent harness"; might have relevant gate mechanics
- `skills-janitor` — Jaccard overlap audit; relevant to SCHEMA-GAP dedup?
- `claude-bouncer` — pattern-level PreToolUse gate — relevant to GATES-GAP, never inspected
- `goose` — block/goose general agent framework — relevant to any of: halt-state, traceability, gates
- `sweep` — issue-to-PR automation — relevant to TRACEABILITY-GAP

Sample 2-3 of these. Did I miss material mechanisms?

### Missed mechanisms from the source doc
The source competitive-landscape doc named several P0/P1 mechanisms I may have under-treated:

- "Risk-triggered external lenses" (P1) — security/test/context/instruction-audit/second-opinion lenses with trigger conditions. Did any gap doc address this?
- "Clean-environment validation" (P2 — Jules / Goose / Sweep) — final validation from fresh checkout. Did HALT-STATE-GAP address this?
- "Adoption signal tracking" (P2) — separating stars/freshness/installs from quality. Marketplace versus skill stars conflation. Did anything address this?

If any of these is uncovered, flag as missing-gap-doc.

## Output format

Structure your review as:

```
# Gap Analysis Peer Review

## Verdict
One paragraph. Did the gap analysis hold up? What's the single biggest concern?

## File-by-file

### INVENTORY.md
- [issue]: [evidence — file:line]
- [issue]: [evidence]

### SCHEMA-GAP-CONTEST-REFACTOR.md
(same format)

[... one section per file ...]

## Cross-cutting issues

### Schema composability
[findings]

### Adoption-order pathologies
[findings]

### Over-claimed wins
[findings]

### Missed competitors
[findings — name competitor, name mechanism missed]

### Missed mechanisms from source doc
[findings]

## Things I'd change before merging this analysis

1. [concrete change with rationale]
2. [...]
```

Hard cap: 2500 words. Cite file paths + line numbers. Do not summarize what each gap doc says — I wrote them; I know. Tell me what's wrong.

If after spot-checking you find the analysis is largely sound, say so plainly — but spend most of your output on the residual weaknesses, not validation. The point of this review is to surface what I missed.

---END PROMPT---

## Notes for the user passing this prompt

- Paste everything between the BEGIN/END PROMPT markers.
- Pair it with whichever LLM you trust most for code review (GPT-5, Gemini Pro, Claude Opus from another session, opencode, Codex CLI). Cross-model is the point — the gap docs were written by Claude Opus; have something other than Claude review them.
- If the reviewing LLM has no filesystem access, give it the gap docs verbatim plus the baseline contest-refactor files; it will be partly blind to competitor source. Mark its output as "context-limited" if so.
- If you have `peer-plan-review` skill installed, you can dispatch this prompt via `/peer-plan-review` to multiple LLMs in parallel and merge their reviews.
