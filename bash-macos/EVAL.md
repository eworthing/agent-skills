# bash-macos Evaluation

**Date:** 2026-08-21
**Evaluator:** Antigravity CLI (skill-evaluator-1.0.0, writing-for-agents, skill-writer)
**Skill version:** Modernized (SPEC + validate_portability.py + lean router)
**Automated score:** 100% (15/15 checks passed)

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

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Strong Bash 3.2 + BSD/GNU + naming + 3-mode output coverage. zsh distinction, `set -E` / ERR-trap propagation, dry-run pattern, argument validation, base64 wrapping, find flag order, and negative line counts covered. |
| 1.2 | Correctness | 4/4 | Verified portable patterns. Pure-bash fallbacks, array unbound expansion guards (`${arr[@]+"${arr[@]}"}`), and sed-via-tmp-mv atomic updates. |
| 1.3 | Appropriateness | 4/4 | Zero external dependencies; stdlib-only validation tooling. |
| 2.1 | Fault Tolerance | 4/4 | Strict mode (`set -euo pipefail`), subshell trap propagation (`set -E`), intentional non-zero handling (`grep \|\| true`), and SIGPIPE pipefail mitigations. |
| 2.2 | Error Reporting | 3/4 | `die`, color helpers (`info`/`warn`/`fail`), stderr usage. No structured/JSON error mode (not applicable for guidance skill). |
| 2.3 | Recoverability | 4/4 | `TMP_DIR` + `trap cleanup EXIT INT TERM`, atomic sed-via-tmp-mv, and dry-run execution gates. |
| 3.1 | Token Cost | 4/4 | `SKILL.md` trimmed from 378 lines to 194 lines. Zero duplication with references; all references flat under `references/` with explicit "Open when..." routing triggers. |
| 3.2 | Execution Efficiency | 4/4 | `capture_run`, log tail, ANSI strip, and zero-subprocess pure-bash fallbacks where possible. |
| 4.1 | Learnability | 4/4 | WRONG/CORRECT pairings, verification + naming checklists, code snippets self-contained. |
| 4.2 | Consistency | 4/4 | Uniform pattern: rule → rationale → code → table. Same shape across all sections. |
| 4.3 | Feedback Quality | 3/4 | Color helpers + 3-mode output (compact/verbose/raw). |
| 4.4 | Error Prevention | 4/4 | `BASH_VERSINFO` guard, quoting rules, naming checklist, `bash -n` / shellcheck guidance, local variable assignment separation, and array-in-conditional gotchas called out. |
| 5.1 | Discoverability | 4/4 | Clear reference table with "Open when..." branch conditions, BSD vs GNU lookup table, and deterministic verification checklist. |
| 5.2 | Forgiveness | 4/4 | sed-via-tmp+mv safer default; `trap cleanup`; dry-run pattern with `run_cmd` helper documented in template + SKILL.md. |
| 6.1 | Credential Handling | 4/4 | N/A — no secrets in skill content. |
| 6.2 | Input Validation | 4/4 | Always-quote rule, `${var:-}` defaults, array `${arr[@]+"${arr[@]}"}` guard, and missing argument validation. |
| 6.3 | Data Safety | 4/4 | sed-via-tmp safer than `-i`; `trap cleanup` on EXIT/INT/TERM; dry-run gating documented for destructive operations. |
| 7.1 | Modularity | 4/4 | Clean progressive disclosure: lean router (`SKILL.md`) + 4 focused references + standalone validator script (`scripts/validate_portability.py`). |
| 7.2 | Modifiability | 4/4 | Adding a new BSD/GNU row or verb is a table edit. New reference fits the pattern. |
| 7.3 | Testability | 4/4 | Standalone `scripts/validate_portability.py` provides deterministic static analysis. Expanded `evals/evals.json` to 7 high-coverage scenarios. |
| 8.1 | Trigger Precision | 4/4 | "Use when..." with file extensions (`.sh`), tool names (sed/grep/date/stat/readlink/base64), exact error symptoms ("mapfile: command not found", "declare: -A: invalid option"). |
| 8.2 | Progressive Disclosure | 4/4 | Three levels: description → SKILL.md router → 4 specialized references + SPEC.md contract. |
| 8.3 | Composability | 3/4 | Output-modes reference is a portable building block; naming reference cross-cuts with any project. |
| 8.4 | Idempotency | 4/4 | Encourages idempotent patterns (mv over in-place, trap cleanup, centralized dry-run wrapper). |
| 8.5 | Escape Hatches | 4/4 | Three-mode output (`--verbose`, `--raw`), env hooks (`TMPDIR`, `ROOT_DIR`, `OUTPUT_MODE`). |
| | **TOTAL** | **96/100** | Exceptional — robust & publishable. |

---

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 | 86/100 | Baseline after references split (d106b8f) + content fixes (6523d76) |
| 2026-05-12 | 90/100 | Phase A: split forbidden-features.md + template.md, trimmed SKILL.md 332→244 lines. |
| 2026-05-13 | 90/100 | Audit pass: propagated Phase A cell updates; fixed `${#arr[@]:-0}` non-fix; added `${arr[@]+"${arr[@]}"}` idiom. |
| 2026-05-23 | 98/100 anthropic-grade | Orthogonal audit via `anthropic-grade-optimizer`. Baseline 87 → 98. |
| 2026-07-04 | 90/100 | macOS 27 Golden Gate currency pass. Darwin 27 verification notes. |
| 2026-08-21 | 96/100 | **Modernization Pass (`writing-for-agents` + `skill-writer` + `skill-creator`)**: Pruned `SKILL.md` from 378 lines to 194 lines (removed manual TOC, duplicate naming tables, historical sediment); added `SPEC.md` maintenance contract; added `scripts/validate_portability.py` zero-dependency static analyzer; expanded BSD/GNU coverage (`base64`, `find` ordering, `head -n -N`, `|&`); expanded `evals/evals.json` from 3 to 7 high-signal scenarios; 15/15 automated structural checks passed. |
