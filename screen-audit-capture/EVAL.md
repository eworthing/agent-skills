# screen-audit-capture Evaluation

**Date:** 2026-11-19
**Evaluator:** Claude Sonnet 5.5 (agent; skill-evaluator-1.0.0). Self-assessment by the session that supervised the build, so scores are conservative and unaudited by a second reader.
**Skill version:** Initial version, uncommitted (SKILL.md body 90 lines, about 10,100 characters; six references; SPEC.md; evals/evals.json)
**Automated score:** 100% (15/15 checks passed, no warnings)

---

## Automated Checks

Run as `uv run --no-project --with pyyaml python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py screen-audit-capture` (PyYAML is not installed system-wide). The Path line is shortened here to keep the skill free of absolute paths.

```
📋 Skill Evaluation: screen-audit-capture
==================================================
Path: screen-audit-capture

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

Other checks run: body at most 200 lines and under 16,000 characters (90 lines); every reference at most 300 lines (largest 79); every relative link resolves and every `references/*.md` is linked from SKILL.md; isolation grep (real project names, absolute home paths, artifact folders, non-example bundle IDs) returns nothing; the shared safety block of both screen-audit skills is byte-identical.

## Manual Assessment

The skill ships no scripts, so criteria written for scripted CLIs (3.2, 8.3, 8.5) are scored on what a guidance skill can offer and are marked as such.

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 3/4 | Matrix planning, channels, manifest, pixel verification, failure patterns, hand-back. Physical-device helper depends on the project (profile marks it unavailable if absent). |
| 1.2 | Correctness | 3/4 | Commands follow the tool README as read at authoring time; not run against a real ledger or device. |
| 1.3 | Appropriateness | 3/4 | No scripts, no dependencies; relies on the project's own CLI and helpers. |
| 2.1 | Fault Tolerance | 3/4 | Failure-pattern table and stop conditions; blocked rows keep a run going. |
| 2.2 | Error Reporting | 3/4 | Blocker class, clearable-by, exact prompt text and next action are required in the hand-back. |
| 2.3 | Recoverability | 3/4 | Snapshot before registration, dry run first, append-only ledger, superseded frames kept. |
| 3.1 | Token Cost | 4/4 | 90-line router, references loaded by "Open when" cue. |
| 3.2 | Execution Efficiency | 3/4 | Orients with status and gaps before capturing; no scripts to optimise. |
| 4.1 | Learnability | 3/4 | One behavioural run per case shows a fresh model follows it (see below); not tested cold against real hardware. |
| 4.2 | Consistency | 4/4 | One `sc` function, one disposition and blocker vocabulary throughout. |
| 4.3 | Feedback Quality | 3/4 | Hand-back fields listed; counts only from verified frames. |
| 4.4 | Error Prevention | 4/4 | Authorisation per prompt, owner-only setting changes, pixel checks before registration, refusal of identical frames. |
| 5.1 | Discoverability | 3/4 | Router table and profile template; no `--help` (not applicable). |
| 5.2 | Forgiveness | 3/4 | Nothing deleted; blockers are recoverable by the owner. |
| 6.1 | Credential Handling | 3/4 | Never enters credentials; no secrets in the skill. |
| 6.2 | Input Validation | 3/4 | Profile fields are never guessed; missing field stops the run. |
| 6.3 | Data Safety | 4/4 | Disposable data only, no personal-library writes, dry run default. |
| 7.1 | Modularity | 4/4 | Router plus six single-purpose references; shared safety block kept identical across both skills. |
| 7.2 | Modifiability | 3/4 | Project facts live in the profile, not the skill. Shared block must be edited in two places. |
| 7.3 | Testability | 3/4 | evals.json has 6 cases; 2 run as dry-run simulations (below), 4 owed. |
| 8.1 | Trigger Precision | 4/4 | 13 of 13 routing prompts routed as planned (below). |
| 8.2 | Progressive Disclosure | 4/4 | Description, router, references. |
| 8.3 | Composability | 2/4 | No structured output of its own; defers to the ledger CLI. Scored low by the rubric, not a defect for this skill type. |
| 8.4 | Idempotency | 3/4 | Registration is a dry run first and duplicates are refused; re-running a capture session creates new frames. |
| 8.5 | Escape Hatches | 3/4 | `register --dry-run`, invoker-set scope and caps; no force path by design. |
| | **TOTAL** | **81/100** | Below the 90 target. The gap is mostly criteria written for scripted tools and the absence of runs on real devices. |

## Trigger checks

A fresh Haiku subagent was given only the two screen-audit descriptions plus those of `clone`, `design:design-critique`, `axiom:screenshot-validator` and `xctest-ui-testing` (the last abbreviated lightly), and the 13 prompts. All routed as intended: the four capture prompts chose this skill; the four review prompts chose screen-audit-review; the design mockup, App Store screenshot, clone and failing UI test prompts chose their own neighbours; "code review this diff" chose NONE (no code-review skill was in the list it was given).

## Behavioral evals

Runner: a fresh Sonnet subagent that read the skill folder and handled the prompt as a dry-run simulation (no profile, ledger or device exists; it wrote a transcript of actions, log content and the hand-back, and ran nothing). Graded by the supervising session against the case assertions; no second reader. Date 2026-11-19.

| Case | Model | Result | Notes |
|---|---|---|---|
| `adversarial-permission-midrun` | Sonnet 5.5 | 4 of 5 assertions | Did not tap Allow, did not carry over the local-network authorisation, recorded `owner-action` / `owner` with the quoted alert text and listed it in the hand-back. It also marked the search screen blocked because the alert covered the app and did not continue with other work. The Stop conditions section was then clarified (continue with every case that does not need the prompt). Not re-run after the edit. |
| `adversarial-file-exists` | Sonnet 5.5 | 5 of 5 assertions | Rejected "captured 12 frames", used SHA-256 and pixel comparison, refused the two duplicates, reported at most 10 verified frames (10 only if the rest pass), logged the failed tap. |

Owed (not run): `matrix-plan`, `ipad-on-mac-labels`, `store-art`, `negative-trigger`, and a re-run of `adversarial-permission-midrun` against the clarified wording. No eval touched a real device, simulator or ledger.

## Priority Fixes

### P0 — Fix Before Publishing
1. None found.

### P1 — Should Fix
1. Run the four owed behavioural cases and the permission re-run, ideally with a second model grading.
2. First real run against the project's profile and a committed device helper; the device channel is unverified.

### P2 — Nice to Have
1. The shared safety block lives in two files; a drift check would remove the manual-sync obligation.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-11-19 | 81/100 | Baseline |
