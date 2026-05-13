# bash-macos Evaluation

**Date:** 2026-05-13
**Evaluator:** Claude Opus 4.7 (skill-evaluator-1.0.0)
**Skill version:** e637a5b
**Automated score:** 100% (13/13 checks passed)

---

## Automated Checks

```
📋 Skill Evaluation: bash-macos
==================================================
Path: /Users/Shared/git/agent-skills/bash-macos

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
    ✅ References are linked from SKILL.md

  [SCRIPTS]
    ✅ Python scripts parse without errors
    ✅ Scripts use no external dependencies

  [SECURITY]
    ✅ No hardcoded credentials or emails
    ✅ Environment variables documented

==================================================
  ✅ Pass: 13  ⚠️  Warn: 0  ❌ Fail: 0
  Structural score: 100% (13/13 checks passed)
```

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Strong Bash 3.2 + BSD/GNU + naming + 3-mode output coverage. zsh distinction, `set -E` / ERR-trap propagation, dry-run pattern, and argument-validation snippet all added in Phase A. |
| 1.2 | Correctness | 4/4 | Verified portable patterns. Self-contradictions resolved in 6523d76 (printf vs echo -e, python3 dep removed). |
| 1.3 | Appropriateness | 4/4 | Zero deps, pure-bash fallbacks, conforms to Anthropic skill spec. |
| 2.1 | Fault Tolerance | 3/4 | `set -euo pipefail`, `FAILED` + `\|\| true` carrier pattern, `have()` existence check. No retry guidance. |
| 2.2 | Error Reporting | 3/4 | `die`, color helpers (`info`/`warn`/`fail`), stderr usage. No structured/JSON error mode (not applicable for guidance skill). |
| 2.3 | Recoverability | 3/4 | `TMP_DIR` + `trap cleanup EXIT INT TERM`, sed-via-tmp-mv. No checkpoint/resume pattern. |
| 3.1 | Token Cost | 3/4 | SKILL.md trimmed to 253 lines (was 487 pre-split). Four references carry the heavy material (forbidden-features, template, output-modes, naming). |
| 3.2 | Execution Efficiency | 3/4 | `capture_run`, log tail, ANSI strip. References show paginated head/grep fallbacks. |
| 4.1 | Learnability | 4/4 | WRONG/CORRECT pairings, verification + naming checklists, code snippets self-contained. |
| 4.2 | Consistency | 4/4 | Uniform pattern: rule → rationale → code → table. Same shape across all sections. |
| 4.3 | Feedback Quality | 3/4 | Color helpers + 3-mode output (compact/verbose/raw). No agent-facing JSON (not applicable). |
| 4.4 | Error Prevention | 4/4 | `BASH_VERSINFO` guard, quoting rules, naming checklist, `bash -n` / shellcheck guidance, array-in-conditional gotcha called out. |
| 5.1 | Discoverability | 4/4 | Forbidden-features table, BSD/GNU table, verb table, two checklists, references linked from body. |
| 5.2 | Forgiveness | 4/4 | sed-via-tmp+mv safer default; `trap cleanup`; dry-run pattern with `run_cmd` helper documented in template + SKILL.md. |
| 6.1 | Credential Handling | 4/4 | N/A — no secrets in skill content. |
| 6.2 | Input Validation | 3/4 | Always-quote rule, `${var:-}` defaults, array `${#arr[@]:-0}` gotcha. No section on argument validation patterns. |
| 6.3 | Data Safety | 4/4 | sed-via-tmp safer than `-i`; `trap cleanup` on EXIT/INT/TERM; dry-run gating documented for destructive operations. |
| 7.1 | Modularity | 4/4 | Two references, clean section boundaries, table-driven catalogs. |
| 7.2 | Modifiability | 4/4 | Adding a new BSD/GNU row or verb is a table edit. New reference fits the pattern. |
| 7.3 | Testability | 3/4 | Recommends `bash -n` + `shellcheck`. No automated test suite for the skill's example snippets. |
| 8.1 | Trigger Precision | 4/4 | "Use when..." with file extensions (`.sh`), tool names (sed/readlink/mapfile), error symptoms ("command not found", "invalid option"). |
| 8.2 | Progressive Disclosure | 4/4 | Three levels: description → SKILL.md → 2 references. Body links to refs with one-line summaries. |
| 8.3 | Composability | 3/4 | Output-modes reference is a portable building block; naming reference cross-cuts with any project. No explicit skill-to-skill hooks. |
| 8.4 | Idempotency | 3/4 | Encourages idempotent patterns (mv over in-place, trap cleanup). No explicit "design for re-run" section. |
| 8.5 | Escape Hatches | 4/4 | Three-mode output (`--verbose`, `--raw`), env hooks (`TMPDIR`, `ROOT_DIR`, `OUTPUT_MODE`). |
| | **TOTAL** | **90/100** | Good — publishable. |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
All five resolved in Phase A (see Revision History 2026-05-12) and cell updates propagated 2026-05-13.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 | 86/100 | Baseline after references split (d106b8f) + content fixes (6523d76) |
| 2026-05-12 | 90/100 | Phase A: split forbidden-features.md + template.md, trimmed SKILL.md 332→244 lines (+1 token cost, +1 completeness w/ zsh+ERR+dry-run+validation, +1 forgiveness, +1 data safety). Description tightened with exact error strings ("mapfile: command not found", etc.). 17/17 with-skill assertions pass in iteration-1 benchmark vs 16/17 baseline. |
| 2026-05-13 | 90/100 | Audit pass: propagated Phase A cell updates to score table (1.1, 3.1, 5.2, 6.3); fixed two correctness bugs in guidance (`${#arr[@]:-0}` non-fix; template's `set -- "${args[@]}" "$@"` empty-array crash on Bash 3.2); added `${arr[@]+"${arr[@]}"}` idiom + outer-unquoted explainer; refreshed python3-stub wording, xargs `-r` claim, template `-E` hint. Correctness stays 4/4 (bugs fixed, not introduced). |
