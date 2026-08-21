# peer-plan-review — validated multi-skill audit (2026-08-21)

Original audit: opencode (GLM-5.3) applying `skill-writer`, `writing-for-agents`, and the community `skill-creator`.

Validation pass: Codex applying both `skill-creator` variants (Codex system and community), `skill-writer`, and `writing-for-agents`, with graph-first source/caller discovery and direct checks of non-code artifacts.

Target: `peer-plan-review/` @ commit `5be2de1` (2026-08-21 13:43). Revalidated at repository HEAD `15ed263`; both `git diff 5be2de1..HEAD -- peer-plan-review/` and graph change detection found no later target changes.

> Charter note: `docs/README.md` scopes this directory to cross-skill work. This audit is single-skill, filed here on explicit user instruction. Residual items should eventually fold into a cross-skill register.

## Summary

The re-review confirms **seven actionable findings**: 1 P1, 3 P2, and 3 P3. It rejects three original P3 items that were style heuristics without demonstrated behavior impact. The transport layer and runtime workflow remain healthy; the actionable findings still concentrate in the eval scaffolding added by `5be2de1` plus one weakened router pointer.

The root eval issue is simpler than the original audit stated: `evals/evals.json` is not consumed by the existing `run_reviews.py` / `score.py` efficacy harness, its four input paths are missing, and “standardized skill-creator evals” has no single schema across the two loaded `skill-creator` variants. The shortest supported fix is to delete the unused 08-21 scaffold and its claims. If it is meant to stay, first choose a runner and document its schema; then make the cases executable.

Nothing here challenges the skill's 98/100 manual score or blocks normal use.

## Changes Made

Audit-only; no skill files were touched.

- Revalidated and refined every original finding.
- Added evidence status, corrected severities/recommendations, and retained rejected items with rationale.
- Updated this document and its `docs/README.md` index row.
- Post-validation correction (opencode): restored the skill-writer `quick_validate.py` gate row removed on a false premise, and extended the `argument-hint` validator gap to the community `skill-creator` variant (live-verified).

## Validation Results (live recheck, 2026-08-21)

| Gate | Result |
|---|---|
| `eval-skill.py peer-plan-review` | 100% (15/15 checks) |
| `pytest scripts/tests/` | 160 passed |
| `common/scripts/sync_common.py --check` | clean (2 consumers byte-identical) |
| `ruff check` + `ruff format --check` (scripts + evals) | clean; 36 files already formatted |
| `run_review.py --self-check` | 6/6 provider CLIs found and healthy |
| `evals/evals.json` JSON parse | valid |
| Workflow-eval input check | all 4 referenced inputs missing |
| Graph usage search | no code consumer of `evals.json` or `trigger_evaluation` in `peer-plan-review/` |
| `skill-creator` `quick_validate.py` (Codex system and community variants) | both reject repo-accepted `argument-hint` — community variant re-verified live ("Unexpected key(s) in SKILL.md frontmatter: argument-hint"); cross-validator schema mismatch, not a runtime failure |
| skill-writer `quick_validate.py` (repo-local copy; gitignored tree) | valid, 0 warnings |
| Target drift check | no `peer-plan-review/` changes after `5be2de1` |

Correction to the Codex pass: it removed the skill-writer `quick_validate.py` row on the rationale that "the loaded repo-local `skill-writer` does not bundle that script." That premise is false — the script exists at `.agents/skills/skill-writer/scripts/quick_validate.py` and was re-run during this validation (`valid`, 0 warnings); it is a different script from `skill-creator`'s validator of the same name, which is what actually rejects `argument-hint`. The defensible residue of the removal: the `.agents/skills/skill-writer/` tree is gitignored, so the gate is machine-local and not reproducible from a fresh clone. The row is restored above with that caveat.

## Actionable Findings

Severity: **P1** fix before treating the 08-21 eval work as done · **P2** should fix · **P3** low-risk quality issue.

IDs: `W` skill-writer lens · `A` writing-for-agents lens · `C` skill-creator lens.

### P1

**W1 — confirmed: eval 0 asserts the wrong output contract.**

`evals/evals.json` eval 0 (`standard-plan-review`) requires Pass A / Pass B. `references/output-format.md` permits that variant only when a Domain context block is present; otherwise the contract is one `### Reasoning` section. Eval 0 has no domain context, while eval 2 correctly tests the two-pass branch. A correct standard run therefore fails eval 0.

Fix if the file stays: require the single-`### Reasoning` template in eval 0 and keep Pass A / Pass B only in eval 2.

### P2

**W2 — confirmed, wording narrowed: EVAL.md makes a repository-unverifiable provenance claim.**

The 2026-08-21 revision row says 194 production tool invocations across `agent-skills` and `BenchHype` confirmed convergence and session-degradation resilience. The exact 194-invocation phrase appears only in EVAL.md and this audit; within `peer-plan-review/`, `BenchHype` appears only in that EVAL.md row. `SOURCES.md` has no 08-21 source record. This does not prove the analysis never occurred; it proves the repository does not preserve enough evidence to verify it.

Fix: add a durable source record and artifact, or drop the sentence. Do not label the claim false without evidence.

**W3 — confirmed: all workflow evals reference missing inputs.**

The four `files` entries resolve to three absent paths: `docs/plans/migration-plan.md`, `docs/plans/payments-redesign.md`, and `docs/plans/ingestion-pipeline.md`. The existing `evals/fixtures/digest-plan.md` belongs to the separate efficacy harness and does not satisfy these cases.

Fix if the file stays: add the minimum fixtures under `evals/fixtures/` and use skill-root-relative paths. Otherwise delete the unused cases.

**C1 — confirmed, root cause revised: the “standardized” eval file has no declared consumer or stable schema.**

- The local efficacy harness uses generated prompts, fixed matrices, and `runs/`; graph search found no code consumer of `evals.json` or `trigger_evaluation`, so the assertion objects have no local harness owner.
- The community `skill-creator` is internally inconsistent: its main instructions use object-valued `assertions`, `references/schemas.md` specifies string `expectations`, and its description-optimization input is a flat array of `{query, should_trigger}` objects.
- The Codex system `skill-creator` does not prescribe this `evals.json` schema and prioritizes observable behavior over wording/heading checks.

The original audit overreached by prescribing `assertions` → `expectations` as though one authoritative tool schema existed. Fix: delete the orphan scaffold, or name one runner as owner, document the intentional schema, and add a deterministic adapter/validator for it. If the community description optimizer is the owner, store its trigger set in the flat format it accepts.

### P3

**A1 — confirmed: provider-reference pointers lost their actual branch condition.**

Before `5be2de1`, the router said to read exactly one provider reference after choosing the reviewer. The new rows say only “configure or troubleshoot,” while Preflight still requires reading the selected provider reference on every run. The executable step prevents a contract loss, but the router pointer now understates when the target is required.

Fix: make each row say it is opened after that provider is selected; keep troubleshooting as a secondary cue.

**C2 — confirmed, wording corrected: two workflow cases overstate or misrepresent the argument contract.**

Eval 0 makes repository verification universal, but SKILL.md requires it only before adopting Gemini blocking findings. Eval 1 includes `--stance adversarial`, although stance is selected from natural-language intent and is not a supported runner or positional skill argument. The original audit incorrectly said the eval 1 assertions encoded the flag; only its prompt does.

Fix if the cases stay: scope verification to Gemini blockers and replace the flag-shaped token with “in adversarial mode.”

**C3 — confirmed but downstream of C1: trigger queries are thin and unexecuted.**

The set has useful near-miss negatives and a few realistic positives, but most entries are short, context-free one-liners. That falls below the community `skill-creator` guidance for realistic paths, backstory, casual phrasing, typos, and difficult boundaries. No result artifact shows that either trigger set has run.

Fix only after choosing a consumer: expand the difficult cases, run them, and preserve results. If the scaffold is deleted, delete this unused set too.

## Rejected Original Findings

**A2 — rejected: the SKILL.md Contents section is not a demonstrated defect.**

It duplicates headings, but the 274-line workflow benefits from direct anchors and neither `skill-creator` variant requires pruning it at this size. Remove it only if a behavioral comparison shows better navigation or execution without it.

**A3 — rejected: the short timeout cue is useful co-location, not harmful duplication.**

SKILL.md tells the host when to change the launcher argument; `adapter-cli.md` explains the flag and failure mechanics. Keeping “reasoning depth, not plan size” beside both decisions prevents a real timeout mistake, and the two copies have not drifted.

**W4 — rejected as a work item: 101 lines is a rubric threshold, not a user-visible failure.**

`opencode.md` exceeds skill-writer's 100-line Contents heuristic by one line, but it is already divided into seven descriptive headings. The two `skill-creator` variants use situational or much higher thresholds. Trimming a line solely to pass the number would be scoreboard work; add a TOC only if retrieval becomes difficult.

## Positive Verification

- All 10 runtime references are flat under `references/` and directly linked from the router table.
- `evals/` remains outside runtime SKILL.md routing, so maintenance artifacts do not add runtime context.
- The Default-OFF domain-context predicate, two-pass branch, background launcher, exit-code-gated read, and Finalize STOP remain explicit and internally consistent.
- The existing efficacy harness is still separate from the new workflow cases and retains its dated 2026-06-29 result artifact.

## Open Gaps

1. The 194-invocation analysis remains unverifiable from repository artifacts (W2).
2. The four workflow evals have no baseline/with-skill runs or result artifact (W3/C1).
3. Harness ownership is unresolved: skill-writer prefers AXIS, the community skill-creator uses its own workspace/viewer, the Codex system skill-creator is format-agnostic, and this repo already has a custom efficacy harness. This is a cross-skill policy choice, not automatically a peer-plan-review defect.
4. The Codex system validator rejects `argument-hint`, while the repo evaluator accepts it and `peer-plan-review`, `quorum-review`, and `contest-refactor` all use it. Resolve at the repository/tooling boundary; do not strip a multi-agent compatibility field from one skill in isolation.

## Work Order

1. **C1:** decide whether `evals/evals.json` needs to exist. Default to deleting the unused scaffold and its README/EVAL claims; keep it only with a named consumer.
2. **W1 + W3 + C2:** if kept, make the cases contract-correct and executable.
3. **W2:** preserve the 194-invocation evidence or remove the claim.
4. **A1:** restore the provider-selection branch wording.
5. **C3:** improve and run trigger cases only after a harness owns them.
