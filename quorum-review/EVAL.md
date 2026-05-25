# quorum-review — Evaluation

Tracked via `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py quorum-review`.

## Score history

| Date | Score | Change |
|---|---|---|
| 2026-05-24 (pre-refactor baseline) | **77 %** (10 / 13) | Initial measurement at the start of the v3 → v3.1 refactor |
| 2026-05-24 (after v3.1 refactor) | **85 %** (11 / 13) | +8 pp |

## Improvements (v3 → v3.1)

| Check | Pre-refactor | Post-refactor | Resolved by |
|---|---|---|---|
| References are linked from SKILL.md | ⚠️ five unlinked (codex, gemini, claude, copilot, protocol) | ✅ all linked | Phase E — `## Bundled resources` index |
| Environment variables documented | ⚠️ `CODEX_HOME`, `GEMINI_CONFIG_DIR` undocumented | ✅ documented | Phase E — new `references/env.md` |

## Remaining warnings (intentional)

| Warning | Disposition |
|---|---|
| `CHANGELOG.md` flagged as "skills shouldn't include these" | **Keep.** A CHANGELOG is industry-standard for a versioned skill; the evaluator's check is overly restrictive. Documented in the refactor plan as expected. |
| `_common.*` imports flagged as "Possible external deps" | **False positive.** `_common/` is the vendored copy of `/common/common/` (kept byte-identical via `sync_common.py --check` in pre-commit + CI). Imports resolve from a sibling directory, not from a third-party package. |

## Refactor non-regression target (per plan)

> Score must equal or exceed the Pre-flight step-1 baseline.

✅ 85 % ≥ 77 %, +8 pp.

## Manual rubric

Manual rubric scoring (`references/rubric.md` in the skill-evaluator package) is a separate maintainer task — out of scope for the refactor's automated gate.
