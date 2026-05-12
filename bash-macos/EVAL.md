# bash-macos Evaluation

**Date:** 2026-05-12
**Evaluator:** Claude Opus 4.7 (skill-evaluator-1.0.0)
**Skill version:** 6523d76
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
| 1.1 | Completeness | 3/4 | Strong Bash 3.2 + BSD/GNU + naming + 3-mode output coverage. Gaps: `zsh` vs `bash` differences on macOS 10.15+, `trap ... ERR` quirks in Bash 3.2, `ulimit`/`set -E` portability. |
| 1.2 | Correctness | 4/4 | Verified portable patterns. Self-contradictions resolved in 6523d76 (printf vs echo -e, python3 dep removed). |
| 1.3 | Appropriateness | 4/4 | Zero deps, pure-bash fallbacks, conforms to Anthropic skill spec. |
| 2.1 | Fault Tolerance | 3/4 | `set -euo pipefail`, `FAILED` + `\|\| true` carrier pattern, `have()` existence check. No retry guidance. |
| 2.2 | Error Reporting | 3/4 | `die`, color helpers (`info`/`warn`/`fail`), stderr usage. No structured/JSON error mode (not applicable for guidance skill). |
| 2.3 | Recoverability | 3/4 | `TMP_DIR` + `trap cleanup EXIT INT TERM`, sed-via-tmp-mv. No checkpoint/resume pattern. |
| 3.1 | Token Cost | 2/4 | SKILL.md is 332 lines — within the 250–400 band. References split helped (was 487), but body still verbose; Minimal Script Template + full Forbidden Features table are candidates to relegate. |
| 3.2 | Execution Efficiency | 3/4 | `capture_run`, log tail, ANSI strip. References show paginated head/grep fallbacks. |
| 4.1 | Learnability | 4/4 | WRONG/CORRECT pairings, verification + naming checklists, code snippets self-contained. |
| 4.2 | Consistency | 4/4 | Uniform pattern: rule → rationale → code → table. Same shape across all sections. |
| 4.3 | Feedback Quality | 3/4 | Color helpers + 3-mode output (compact/verbose/raw). No agent-facing JSON (not applicable). |
| 4.4 | Error Prevention | 4/4 | `BASH_VERSINFO` guard, quoting rules, naming checklist, `bash -n` / shellcheck guidance, array-in-conditional gotcha called out. |
| 5.1 | Discoverability | 4/4 | Forbidden-features table, BSD/GNU table, verb table, two checklists, references linked from body. |
| 5.2 | Forgiveness | 3/4 | sed-via-tmp+mv is safer default; `trap cleanup`. No `--dry-run` advisory section. |
| 6.1 | Credential Handling | 4/4 | N/A — no secrets in skill content. |
| 6.2 | Input Validation | 3/4 | Always-quote rule, `${var:-}` defaults, array `${#arr[@]:-0}` gotcha. No section on argument validation patterns. |
| 6.3 | Data Safety | 3/4 | sed-via-tmp safer than `-i`; `trap cleanup` on EXIT/INT/TERM. No dry-run pattern. |
| 7.1 | Modularity | 4/4 | Two references, clean section boundaries, table-driven catalogs. |
| 7.2 | Modifiability | 4/4 | Adding a new BSD/GNU row or verb is a table edit. New reference fits the pattern. |
| 7.3 | Testability | 3/4 | Recommends `bash -n` + `shellcheck`. No automated test suite for the skill's example snippets. |
| 8.1 | Trigger Precision | 4/4 | "Use when..." with file extensions (`.sh`), tool names (sed/readlink/mapfile), error symptoms ("command not found", "invalid option"). |
| 8.2 | Progressive Disclosure | 4/4 | Three levels: description → SKILL.md → 2 references. Body links to refs with one-line summaries. |
| 8.3 | Composability | 3/4 | Output-modes reference is a portable building block; naming reference cross-cuts with any project. No explicit skill-to-skill hooks. |
| 8.4 | Idempotency | 3/4 | Encourages idempotent patterns (mv over in-place, trap cleanup). No explicit "design for re-run" section. |
| 8.5 | Escape Hatches | 4/4 | Three-mode output (`--verbose`, `--raw`), env hooks (`TMPDIR`, `ROOT_DIR`, `OUTPUT_MODE`). |
| | **TOTAL** | **86/100** | Good — publishable, note known issues. |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. **Trim SKILL.md to <250 lines** (3.1). Candidates to move into references:
   - "Forbidden Features" full table + workarounds → `references/forbidden-features.md`
   - "Minimal Script Template" → `references/template.sh` (or inline in `references/output-modes.md`)
   Keep top-of-skill: a short forbidden-feature *summary list* and a pointer.
2. **Add zsh/sh distinctions** (1.1). macOS default shell since Catalina is zsh; clarify that this skill targets `/bin/bash` (3.2) explicitly and note `/bin/sh` is a different binary that does not honor `[[`.
3. **Add `trap ... ERR` / `set -E` note** (2.1). Bash 3.2's `ERR` trap does not propagate into functions/subshells without `set -E`; worth a one-liner in the Error Handling section.
4. **Add dry-run pattern** (5.2, 6.3). One snippet showing `DRY_RUN=${DRY_RUN:-0}` + guard.
5. **Add argument-validation snippet** (6.2). A short pattern for `[[ -z "${VAR:-}" ]] && die "VAR required"`.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 | 86/100 | Baseline after references split (d106b8f) + content fixes (6523d76) |
| 2026-05-12 | 90/100 | Phase A: split forbidden-features.md + template.md, trimmed SKILL.md 332→244 lines (+1 token cost, +1 completeness w/ zsh+ERR+dry-run+validation, +1 forgiveness, +1 data safety). Description tightened with exact error strings ("mapfile: command not found", etc.). 17/17 with-skill assertions pass in iteration-1 benchmark vs 16/17 baseline. |
