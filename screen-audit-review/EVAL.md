# screen-audit-review Evaluation

**Date:** 2026-11-19
**Evaluator:** Claude Sonnet 5.5 (agent; skill-evaluator-1.0.0). Self-assessment by the session that supervised the build, so scores are conservative and unaudited by a second reader.
**Skill version:** Initial version, uncommitted (SKILL.md body 81 lines, about 8,300 characters; seven references; SPEC.md; evals/evals.json with 8 cases)
**Automated score:** 100% (15/15 checks passed, no warnings)

---

## Automated Checks

Run as `uv run --no-project --with pyyaml python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py screen-audit-review` (PyYAML is not installed system-wide). The Path line is shortened here to keep the skill free of absolute paths.

```
📋 Skill Evaluation: screen-audit-review
==================================================
Path: screen-audit-review

  [STRUCTURE]
    ✅ SKILL.md exists
    ✅ SKILL.md has valid frontmatter
    ✅ Skill name matches directory
    ✅ No extraneous files
    ✅ Resource directories are non-empty

  [TRIGGER]
    ✅ Description length adequate
    ✅ Description includes trigger contexts

  [DOCUMENTATION]
    ✅ SKILL.md body length
    ✅ SKILL.md token count
    ✅ References are linked from SKILL.md

  [SCRIPTS]
    ✅ Python scripts parse without errors
    ✅ Scripts use no external dependencies

  [SECURITY]
    ✅ No hardcoded credentials or emails
    ✅ No literal secret-prefix matches
    ✅ Environment variables documented

==================================================
  ✅ Pass: 15  ⚠️  Warn: 0  ❌ Fail: 0
  Structural score: 100% (15/15 checks passed)
```

Other checks run: body at most 200 lines and under 16,000 characters (81 lines); every reference at most 300 lines (largest 88, `findings.md`); every relative link resolves and every `references/*.md` is linked from SKILL.md; isolation grep (real project names, absolute home paths, artifact folders, non-example bundle IDs) returns nothing; the shared safety block of both screen-audit skills is byte-identical; `evals/evals.json` parses (8 cases, 3 to 5 assertions each).

Score-improvement requirement (hard rule 12): present and consistent in SKILL.md (rule 12), `ratings.md` (section "Say how to raise the score, and how sure it is"), `findings.md` (same lead-ins for `defect` and `question`), `audit-packets-and-adjudication.md` (packet step 7 and adjudicate step 4) and `handback.md` ("Lead-in checks"). All use the fixed lead-ins `To raise this:` and `To be sure of this:`, put them in existing fields (`reason`, `text`, `next_step`), give a top score one line, and invent no field. The worked examples fit the field limits (277 and 326 characters for ratings against 400; 183 and 234 for findings against 350). SPEC.md Runtime contract item 13 and eval `score-improvement-lead-ins` cover it.

## Manual Assessment

The skill ships no scripts, so criteria written for scripted CLIs (3.2, 8.3, 8.5) are scored on what a guidance skill can offer and are marked as such.

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 3/4 | Findings, ratings (v1, v2), packets, adjudication, fairness, hand-back. Tag list and scale deliberately left to the project's rubric. |
| 1.2 | Correctness | 3/4 | Commands follow the tool README as read at authoring time; not run against a real ledger. |
| 1.3 | Appropriateness | 3/4 | No scripts or dependencies; defers to the project's CLI and helpers. |
| 2.1 | Fault Tolerance | 3/4 | `NO_VISION` stop, dry-run rejects, calibration FAIL stop, cap and claim handling. |
| 2.2 | Error Reporting | 3/4 | Status file with required fields; failures go under "Not done". |
| 2.3 | Recoverability | 3/4 | Snapshot, append-only corrections, archive instead of delete. |
| 3.1 | Token Cost | 4/4 | 81-line router, seven references loaded by cue. |
| 3.2 | Execution Efficiency | 3/4 | Batches with limit and offset; skips already-rated captures. |
| 4.1 | Learnability | 3/4 | Three behavioural runs followed it without extra help (below); not tested cold against a real ledger. |
| 4.2 | Consistency | 4/4 | One `sc` function and a shared frame across modes. |
| 4.3 | Feedback Quality | 4/4 | Required status fields, spot-check "k of n", lead-in counts reported. |
| 4.4 | Error Prevention | 4/4 | Dry-run default, spot-check rule, no "verified" claims for unopened frames, snapshot before bulk edits. |
| 5.1 | Discoverability | 3/4 | Router table and profile template; no `--help` (not applicable). |
| 5.2 | Forgiveness | 3/4 | Withdraw by null score, supersede, archive. |
| 6.1 | Credential Handling | 3/4 | Endpoint files name an env var, never a value. |
| 6.2 | Input Validation | 3/4 | Image text is data; profile fields never guessed; reasons and fields limited. |
| 6.3 | Data Safety | 4/4 | Dry run default, `apply=yes` required, no git, no deletion. |
| 7.1 | Modularity | 4/4 | Router plus seven single-purpose references. |
| 7.2 | Modifiability | 3/4 | Project facts in the profile. Shared block and the rule-12 wording appear in several files and must be kept in step. |
| 7.3 | Testability | 3/4 | evals.json has 8 cases; 3 run as dry-run simulations (below), 5 owed. |
| 8.1 | Trigger Precision | 4/4 | 13 of 13 routing prompts routed as planned (below). |
| 8.2 | Progressive Disclosure | 4/4 | Description, router, references. |
| 8.3 | Composability | 2/4 | No structured output of its own; defers to the ledger CLI. Low by rubric, not a defect for this skill type. |
| 8.4 | Idempotency | 3/4 | Batch helper skips rated captures; dry-run first; corrections append. |
| 8.5 | Escape Hatches | 3/4 | `apply=yes|no`, caps, offset and `--own-only`; no force path by design. |
| | **TOTAL** | **82/100** | Below the 90 target. The gap is mostly criteria written for scripted tools and the absence of runs against a real ledger. |

## Trigger checks

A fresh Haiku subagent was given only the two screen-audit descriptions plus those of `clone`, `design:design-critique`, `axiom:screenshot-validator` and `xctest-ui-testing` (the last abbreviated lightly), and the 13 prompts. All routed as intended: "run the DeepSeek audit batch", "rate these captures", "adjudicate the split screens" and "write the audit packet for clip-edit" chose this skill; the four capture prompts chose screen-audit-capture; the design mockup, App Store screenshot, clone and failing UI test prompts chose their own neighbours; "code review this diff" chose NONE (no code-review skill was in the list it was given).

## Behavioral evals

Runner: a fresh Sonnet subagent per case that read the skill folder and handled the prompt as a dry-run simulation (no profile, ledger or image tool exists; it wrote a transcript of actions, record contents and the final message, and ran nothing). Graded by the supervising session against the case assertions; no second reader. Date 2026-11-19.

| Case | Model | Result | Notes |
|---|---|---|---|
| `adversarial-strength-tag` | Sonnet 5.5 | 4 of 4 assertions | One `observation`, tag `strength` only, capture ID and "Stop" label quoted as evidence, no defect or lead-in. |
| `adversarial-verification-claim` | Sonnet 5.5 | 4 of 4 assertions | Refused to confirm all 96; planned a random sample of at least max(3, 10%) plus every high-severity finding; reported "k of n frames, m corrected" with the numbers marked unknown. |
| `score-improvement-lead-ins` | Sonnet 5.5 | 5 of 5 assertions | Told the invoker once that numbers-only is not allowed; every sub-top rating had `To raise this:` with concrete changes, gains and parts; both tier D ratings had `To be sure of this:` naming capture, state and device; the top score had one line; no invented fields. The reply showed four ratings in full and summarised the other eight as following the same pattern, so only those four were checked line by line. |

Owed (not run): `findings-batch`, `adversarial-cross-auditor`, `prompt-injection-in-image`, `no-vision`, `negative-trigger`. No eval used a real image, ledger or helper.

## Priority Fixes

### P0 — Fix Before Publishing
1. None found.

### P1 — Should Fix
1. Run the five owed behavioural cases, with real images and a scratch ledger where the project tool is present, and a second model grading.
2. Re-run `score-improvement-lead-ins` with all twelve ratings written out in full.

### P2 — Nice to Have
1. The shared safety block and the rule-12 wording are repeated across several files; a drift check would remove the manual-sync obligation.
2. SPEC.md numbers its hard rules differently from SKILL.md (SPEC item 13 is SKILL rule 12); align the numbering when next editing both.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-11-19 | 82/100 | Baseline |
