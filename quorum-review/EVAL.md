# quorum-review — Evaluation

Tracked via `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py quorum-review`.

## Score history

| Date | Score | Change |
|---|---|---|
| 2026-05-24 (pre-refactor baseline) | **77 %** (10 / 13) | Initial measurement at the start of the v3 → v3.1 refactor |
| 2026-05-24 (after v3.1 refactor) | **85 %** (11 / 13) | +8 pp |
| 2026-06-03 (anthropic-grade polish) | **85 %** (11 / 13) | No change — doc/comment-only polish (AR-CC-S21/S22/S18); the 2 remaining warnings are intentional (below) |
| 2026-06-14 (Antigravity `agy` added) | **92 %** (12 / 13) | +7 pp vs 85 % — the structural gain is the evaluator's `_common/` sibling-import fix, **not** agy. agy = 6th accepted reviewer (panel + auto-verifier candidate), successor to the EOL-2026-06-18 Gemini CLI (Gemini retained for enterprise). ⚠️ agy is **not read-only** (auto-approves tools) — shipped experimental with `--sandbox` + a read-only prompt preamble + docs warnings; the other reviewers stay sandboxed read-only. Tests: **156** (run_quorum) incl. a parallel-safe agy id-capture test. |
| 2026-06-14 (CHANGELOG removed) | **100 %** (13 / 13) | +8 pp vs 92 % — removed the root `CHANGELOG.md`. A changelog is needless weight in an agent-facing skill dir; the full v3.1 refactor narrative is retained in git history and the version progression is summarized in this very table. Resolves the last structural warn → **0 warnings**. (The earlier `_common.*` "external deps" warning already stopped firing after the evaluator's vendored-sibling-import fix.) |

> **Score column = repo `eval-skill.py` structural rubric.** For the separate
> Anthropic-grade doctrine audit, see the next section — different rubric, do not
> conflate the two numbers.

## Anthropic-grade audit (separate rubric)

Tracked via the `anthropic-grade-optimizer` skill
(`run.py SKILL.md --target opus-4-7 --mode audit`), scored against 189 cited
Anthropic rules across 11 dimensions. **This is a distinct scoring system from
the `eval-skill.py` percentage above.**

| Date | Score | Notes |
|---|---|---|
| 2026-06-03 (pre-polish) | **95 / 100** (grade A) | Ship-it; only D-CC below 100 (75), from 2 soft 🟢 findings |
| 2026-06-03 (post-polish) | **100 / 100** | D-CC 75 → 100 after AR-CC-S22 exec-intent framing, AR-CC-S21 TOCs (`references/protocol.md` + body), AR-CC-S18 merge-threshold comments. 0 critical, voice fully preserved |

## Improvements (v3 → v3.1)

| Check | Pre-refactor | Post-refactor | Resolved by |
|---|---|---|---|
| References are linked from SKILL.md | ⚠️ five unlinked (codex, gemini, claude, copilot, protocol) | ✅ all linked | Phase E — `## Bundled resources` index |
| Environment variables documented | ⚠️ `CODEX_HOME`, `GEMINI_CONFIG_DIR` undocumented | ✅ documented | Phase E — new `references/env.md` |

## Warnings — all resolved

As of 2026-06-14 the structural rubric reports **13 / 13, 0 warnings**.

| Former warning | Disposition |
|---|---|
| `CHANGELOG.md` flagged as "skills shouldn't include these" | **Removed** 2026-06-14. Previously kept (the check is opinionated about versioned skills), but a root changelog is needless weight in an agent-facing dir; the history lives in git and the score-history table above. |
| `_common.*` imports flagged as "Possible external deps" | **No longer fires.** The evaluator's sibling-import detection now recognizes the vendored `_common/` tree (byte-identical to `/common/common/`, enforced by `sync_common.py --check` in pre-commit + CI). |

## Refactor non-regression target (per plan)

> Score must equal or exceed the Pre-flight step-1 baseline.

✅ 85 % ≥ 77 %, +8 pp.

## Manual rubric

Manual rubric scoring (`references/rubric.md` in the skill-evaluator package) is a separate maintainer task — out of scope for the refactor's automated gate.
