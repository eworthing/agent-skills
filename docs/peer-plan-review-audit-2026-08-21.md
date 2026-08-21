# peer-plan-review — three-skill audit (2026-08-21)

Auditor: opencode (GLM-5.3) applying three loaded skills — `skill-writer` (router / reference / eval contracts), `writing-for-agents` (pointer wording, information hierarchy, pruning), `skill-creator` (eval scaffolding, trigger optimization).

Target: `peer-plan-review/` @ commit `5be2de1` (2026-08-21 13:43). **The skill was modified mid-audit** — that commit landed hours before this pass; every check below was re-run against it.

> Charter note: `docs/README.md` scopes this directory to cross-skill work. This audit is single-skill, filed here on explicit user instruction. Residual items should eventually fold into a cross-skill register.

## Summary

The transport layer and `SKILL.md` router remain in excellent shape — all validation gates verified live and green. Every real finding concentrates in the **eval scaffolding added by `5be2de1`**: one workflow eval asserts the opposite of the skill's output-format contract, the "standardized skill-creator evals" do not match the schema skill-creator's tooling actually consumes, an EVAL.md provenance claim has no artifact behind it, and the router-table rewrite dropped the branch condition from the provider-reference pointers. Nothing here challenges the skill's 98/100 standing or blocks use.

## Changes Made

Audit-only; no skill files were touched.

- This document.
- One index row in `docs/README.md`.

## Validation Results (live, 2026-08-21)

| Gate | Result |
|---|---|
| `eval-skill.py peer-plan-review` | 100% (15/15 checks) — matches EVAL.md |
| `pytest scripts/tests/` | 160 passed — matches EVAL.md |
| `common/scripts/sync_common.py --check` | clean (2 consumers byte-identical) |
| `ruff check` (scripts + evals) | clean |
| `run_review.py --self-check` | 6/6 providers found and healthy |
| skill-writer `quick_validate.py` | valid, 0 warnings |
| `git status peer-plan-review/` | clean tree |

## Findings

Severity: **P1** fix before treating the 08-21 eval work as done · **P2** should fix · **P3** nice to have.
IDs: `W` skill-writer lens · `A` writing-for-agents lens · `C` skill-creator lens.

### P1

**W1 — eval 0 asserts the wrong output contract.**
`evals/evals.json` eval 0 (`standard-plan-review`) asserts `structured-output-enforced`: "Prompt includes Pass A / Pass B structure". Per `references/output-format.md` (two-pass variant, lines 55–61) and SKILL.md (§Domain context, §Round 1 items 3–4), Pass A/Pass B replaces `### Reasoning` **only when a domain-context block is present**. Eval 0 is a standard review with no domain context, so a correctly executed run fails the assertion — and grading pressure pushes the agent toward always-two-pass, the exact over-triggering the Default-OFF predicate exists to prevent. Eval 2 (`domain-context-two-pass-review`) carries the two-pass assertion correctly.
Fix: assert the single-`### Reasoning` template on eval 0; leave two-pass on eval 2.

### P2

**W2 — EVAL.md provenance claim with no artifact.**
EVAL.md revision row 2026-08-21: "Analyzed 194 production tool invocations across `agent-skills` and `BenchHype` confirming 5-round multi-agent convergence and session degradation resilience." No `BenchHype` string, no 194-invocation dataset, script, or result file exists anywhere in the repo (searched). `SOURCES.md` — the skill's own provenance register, whose doc-honesty section set the "asserted-not-proven" bar for exactly this class of claim — has no entry for the 08-21 changes at all. Every other claim in that row (15/15, 160 tests, sync clean) verified true.
Fix: commit the analysis artifact + add a SOURCES.md row, or drop the sentence.

**W3 — workflow evals reference fixtures that don't exist.**
`evals/evals.json` `files` arrays point at `docs/plans/migration-plan.md`, `docs/plans/payments-redesign.md`, `docs/plans/ingestion-pipeline.md` — none exist relative to the skill root, so all four workflow evals are unfalsifiable as written. The real fixtures (`evals/fixtures/digest-plan.md`) belong to the efficacy harness, not to these.
Fix: add minimal plan fixtures under `evals/fixtures/` and point `files` at them (skill-evals rule: long source material lives in fixtures, not in the prompt).

**C1 — "standardized skill-creator evals" don't match skill-creator's tooling schema.**
Two mismatches:
(a) findings use `assertions: [{id, description, type}]` — skill-creator's grading pipeline consumes `expectations` (string list; `grading.json` carries `text/passed/evidence`), and skill-creator's own SKILL.md and `schemas.md` disagree with each other about the field name, so nothing tool-side reads `assertions`. The richer local schema is defensible — but then say so in `evals/README.md` instead of claiming standardization.
(b) the trigger set is embedded as `trigger_evaluation: {should_trigger: [...], should_not_trigger: [...]}` — skill-creator's `scripts/run_loop.py --eval-set` consumes a **flat array** of `{query, should_trigger}` objects (`run_loop.py:28–30`), so the set cannot feed the description-optimization loop without hand transformation.
Fix: split the trigger queries into the flat format `run_loop.py` consumes; rename `assertions` → `expectations` or document the intentional divergence.

### P3

**A1 — router table lost the provider-reference branch condition.**
The pre-`5be2de1` bullet said "Provider references — **read exactly one after reviewer chosen**". The new table's provider rows say "configure or troubleshoot the X CLI reviewer" — a weaker, troubleshoot-only cue. Preflight step 2 (SKILL.md:86) still carries the real instruction, so nothing is lost, but the pointer wording no longer encodes the branch: a host consulting only the table could skip the provider read on a clean run. Writing-for-agents: a must-reach target behind a weakly worded pointer is a variance bug.
Fix: restore the branch to the rows, e.g. "open your chosen reviewer's row right after parsing arguments, or when configuring/troubleshooting it".

**C2 — eval 0 overstates the verification contract; eval 1 bakes in a nonexistent flag.**
Eval 0's `adjudication-before-edit` assertion and expected_output make repo-verification of reviewer claims universal; SKILL.md Rules (line 265) mandates it **only for Gemini blocking findings**. Eval 1's prompt includes the literal `--stance adversarial` token, which is not in the skill's argument grammar (stance comes from natural language). Harmless as user speech, but assertions shouldn't encode either as the contract.
Fix: scope the verification assertion to Gemini blockers; drop the flag-shaped token.

**A2 — manual `## Contents` TOC is a cache of the environment.**
SKILL.md lines 25–39 restate the document's own headings — ~15 lines of always-loaded context. Renderers generate TOCs. Prune candidate.

**A3 — `--timeout` rationale duplicated.**
"reasoning depth, not plan size" appears in SKILL.md §Round 1 and again in `adapter-cli.md` `--timeout` — one meaning, two sites, drift risk. Keep the rationale in `adapter-cli.md`; one word in SKILL.md.

**W4 — `opencode.md` crosses the 100-line Contents rule by one line.**
101 lines; design-principles: references over 100 lines get `## Contents`. Trim a line or add the TOC — trivial either way.

**C3 — trigger queries are concrete but thin.**
skill-creator's description-optimization guidance asks for substantive queries with backstory, paths, typos, casual speech; most of the 20 are one-liners. A few are exactly right ("peer-plan-review codex gpt-5.6-sol high on @plan.md"; "Refactor this legacy module using contest-refactor" as a near-miss negative). The negative set's genuine near-misses (diff review, PR review) are good. Not yet run — see Open Gaps.

## What the audit did not find (positive verification)

- **Router rule satisfied.** All 10 references flat under `references/`, all 10 in the router table — the `5be2de1` restore of `domain-context.md` closed the last routing gap. Filenames predict contents; no catch-all files.
- **Eval routing stays out of runtime.** SPEC.md invariant 7 (evals) is maintenance-contract placement; `evals/` is absent from SKILL.md routing — matches skill-evals' placement rule.
- **Description discipline holds.** Capability first, one branch per trigger, provider names as leading words. Trigger precision intentionally unchanged since SOURCES.md's explicit decision.
- **Progressive disclosure and completion criteria are exemplary and survived the rewrite**: Default-OFF domain-context predicate, the single-recipe launcher, the exit-code-gated read ("never parse a verdict from absent files"), and the Finalize STOP with rationale.
- **agy exception single-sourced** to Rules + `antigravity.md` with pointer-style mentions elsewhere — no regression from the 2026-06-29 dedup.
- **Bash portability correct** in `ppr_launch.sh`: bash-3.2 array-guard expansion, no `readlink -f`, PIPESTATUS preserved through `tee`, gated `ppr_paths` eval.

## Open Gaps

1. **194-invocation / BenchHype analysis** (W2) — unverifiable until an artifact lands or the claim is dropped.
2. **Trigger optimization loop never run** — the 20 queries exist on paper only; `run_loop.py` has not executed them against the description.
3. **Workflow evals never executed** — no baseline/with-skill runs, no `evals/results/` entry; the efficacy harness has dated results (2026-06-29) but `evals.json` does not.
4. **AXIS vs custom harness** — skill-writer's current eval doctrine prescribes AXIS scenarios for repeatable agent evals; this repo standardized earlier on EVAL.md + custom harness. Reconciling the conventions is a cross-skill decision (belongs with the contest-refactor/quorum registers), not a peer-plan-review defect.

## Work order

1. **W1** — eval 0 two-pass assertion (correctness of the new eval set).
2. **W2 + C1** — provenance row + eval schema conformance (natural to combine with W1).
3. **W3** — fixtures for falsifiability.
4. **A1** — router-table branch wording (one-line edit).
5. **C2, A2, A3, W4, C3** — opportunistic.
