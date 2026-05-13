# doc-standardization Evaluation

**Date:** 2026-05-12 (post-P2-fix)
**Evaluator:** Claude Opus 4.7
**Skill version:** Post-P2 hardening — references/ split, scripts/ added, hardened validators, sibling cross-links, upstream citations, escape-hatch section
**Automated score:** 100% (13/13)
**Manual score:** **99/100** — Excellent

---

## Automated Checks

```
📋 Skill Evaluation: doc-standardization
==================================================
  [STRUCTURE]
    ✅ SKILL.md exists
    ✅ SKILL.md has valid frontmatter
    ✅ Skill name matches directory
    ✅ No extraneous files
    ✅ Resource directories are non-empty
  [TRIGGER]
    ✅ Description length adequate (55 words)
    ✅ Description includes trigger contexts ("use when")
  [DOCUMENTATION]
    ✅ SKILL.md body length (137 lines)
    ✅ References are linked from SKILL.md
  [SCRIPTS]
    ✅ Python scripts parse without errors (no Python)
    ✅ Scripts use no external dependencies
  [SECURITY]
    ✅ No hardcoded credentials or emails
    ✅ Environment variables documented (no env vars found)

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## File Layout

```
doc-standardization/
  SKILL.md                          156 lines (137 body)
  EVAL.md                           this file
  references/
    regex-recipes.md                213 lines — hardened bash recipes per error class
    error-taxonomy.md                25 lines — error class → detector → fix
    conventions.md                   99 lines — naming, status suffixes, tree, alignment, exceptions
  scripts/
    check-doc-naming.sh             190 lines, executable — one-shot drift verifier
```

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Full lifecycle (audit → rename → cross-ref → index → re-audit) + bundled script + per-class taxonomy + exceptions. |
| 1.2 | Correctness | 4/4 | Hardened link validator (skips `http(s)://`, `mailto:`, anchors-only; URL-decodes `%20`; resolves relative to source file's directory). Smoke-tested on a planted-fault fixture and a clean fixture — both behave correctly (exit 1 + per-class FAILs / exit 0 + CLEAN). |
| 1.3 | Appropriateness | 4/4 | Pure Markdown + portable Bash 3.2 / BSD-userland-safe. Zero external dependencies. |
| 2.1 | Fault Tolerance | 4/4 | Script exits 0/1/2 cleanly. Missing-directory path returns 2 with stderr message. Orphan-class is correctly separated as advisory (does not fail the run). |
| 2.2 | Error Reporting | 4/4 | Structured taxonomy (`references/error-taxonomy.md`) maps every output prefix (`BROKEN:` / `ORPHAN:` / `INDEX-DRIFT:` / `CASE:` / `NAMING:`) to a canonical fix. Per-class FAIL summary lines plus indented detail lines. |
| 2.3 | Recoverability | 4/4 | All ops `git mv`-based → fully reversible. Audit script is idempotent. |
| 3.1 | Token Cost | 4/4 | SKILL.md body 137 lines (<150 = top tier). Progressive disclosure via `references/` (3 files, scoped). Every section in SKILL.md is workflow-relevant. |
| 3.2 | Execution Efficiency | 4/4 | Single-pass `find` produces the file list once; each check reads from a temp file. Linear in doc count. |
| 4.1 | Learnability | 4/4 | Two end-to-end worked examples. Expected outputs shown for clean and failure cases. Run command is one line. |
| 4.2 | Consistency | 4/4 | Uniform numbered steps, code fence usage, `[OK]` / `[FAIL]` / `[WARN]` output prefixes, link style across SKILL.md and references. |
| 4.3 | Feedback Quality | 4/4 | `[OK] links: 0 broken (N checked)` for clean, `[FAIL] links: N broken (M checked)` plus indented `BROKEN: <src>:<line> -> <target>` lines for failures. Final summary line is parseable. |
| 4.4 | Error Prevention | 4/4 | "Common Mistakes" enumerates 5 historical failures; bundled script catches all of them automatically. |
| 5.1 | Discoverability | 4/4 | "Use when…" + 6 trigger contexts in description + explicit "Do NOT use when" list. Related Skills section cross-links siblings. |
| 5.2 | Forgiveness | 4/4 | `git mv` reversible. Audit script is read-only. |
| 6.1 | Credential Handling | 4/4 | No secrets surface. |
| 6.2 | Input Validation | 4/4 | Script validates directory exists, exits 2 with stderr otherwise. Allowlist for base names is explicit. |
| 6.3 | Data Safety | 4/4 | Read-only audit + `git mv` rename only. No destructive shell. |
| 7.1 | Modularity | 4/4 | Three clear layers: SKILL.md (workflow), `references/` (lookups + recipes + taxonomy), `scripts/` (one-shot runner). Adding a new error class = add recipe + table row + script section in one obvious place each. |
| 7.2 | Modifiability | 4/4 | New status suffix = one row in `conventions.md`. New error class = one recipe + one taxonomy row + one script block. Patterns are explicit. |
| 7.3 | Testability | **3/4** | Script ships with documented exit codes (0/1/2) and structured output making fixture-based testing trivial; smoke tests in this eval validate the happy and unhappy paths. No bundled automated test suite. |
| 8.1 | Trigger Precision | 4/4 | Description names specific operations: renames, link fixes, index updates, doc-tree audits. "Do NOT use when" carves out single-file edits + non-doc files. |
| 8.2 | Progressive Disclosure | 4/4 | 3 levels: description → SKILL.md (137 lines) → references/ (4 files) + scripts/. Agent loads only what it needs. |
| 8.3 | Composability | 4/4 | Script exits with conventional codes (0/1/2). Structured output prefixes (`[OK]` / `[FAIL]` / `BROKEN:` / etc.) are pipe-friendly. Sibling skills cross-linked: `bash-macos`, `swift-file-splitting`. CommonMark + GFM cited. |
| 8.4 | Idempotency | 4/4 | Audit re-runs produce identical output for identical state. `git mv` idempotent. |
| 8.5 | Escape Hatches | 4/4 | "When to break the convention" subsection covers vendor docs, legacy specs, top-level files. Allowlist hardcoded into the script + documented in `conventions.md`. |
| | **TOTAL** | **99/100** | **Excellent** — publish confidently. |

## Delta vs. Prior Evals

| Criterion | Import (2026-05-12) | Re-eval (2026-05-12) | Post-fix (2026-05-12) | Lift driver |
|---|---|---|---|---|
| 1.2 Correctness | 4 | 3 | **4** | Hardened link validator (http/mailto/anchor skip, URL-decode, source-dir resolution). Smoke-tested on faults + clean fixture. |
| 2.1 Fault Tolerance | 3 | 3 | **4** | Script exit codes 0/1/2 + advisory-vs-blocking class separation. |
| 2.2 Error Reporting | 3 | 3 | **4** | `references/error-taxonomy.md` table; structured `[OK]`/`[FAIL]`/`BROKEN:` prefixes. |
| 3.1 Token Cost | 3 | 3 | **4** | SKILL.md body 252 → 137 lines via references/ split. |
| 4.3 Feedback Quality | 3 | 3 | **4** | Explicit `OK: 0 broken links (N checked)` and per-class FAIL summaries. |
| 7.1 Modularity | 3 | 3 | **4** | SKILL/references/scripts three-layer split with one home per concern. |
| 7.3 Testability | 2 | 2 | **3** | Bundled drift verifier with documented exit codes + smoke-tested. CommonMark + GFM cited. (Would reach 4 with an automated test harness for the script.) |
| 8.2 Progressive Disclosure | 3 | 3 | **4** | 3-level disclosure now exists (description → SKILL → references/scripts). |
| 8.3 Composability | 3 | 3 | **4** | Sibling cross-links (`bash-macos`, `swift-file-splitting`) inline. Upstream citations (CommonMark, GFM). |
| 8.5 Escape Hatches | 3 | 3 | **4** | New "When to break the convention" section + allowlist documented + hardcoded in script. |
| **Total** | **91** | **89** | **99** | +10 vs. re-eval baseline (89 → 99); +8 vs. import (91 → 99). |

## Priority Fixes

### P0 — Blocks publishing
None.

### P1 — Should fix
None.

### P2 — Nice to have
1. **Automated test suite for `check-doc-naming.sh`** — A `tests/` directory with planted-fault fixtures (each class) and one clean fixture, plus a `run-tests.sh` that asserts exit codes and output substrings. Would lift 7.3 from 3 → 4 and unlock a perfect 100/100.

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (import) | 91 | Phase 1 MOVE-AS-IS from Tiercade. Dropped frontmatter metadata + `applyTo` + `evidence_commits`. Genericized Code-Doc Alignment table. Stripped Tiercade-specific paths. |
| 2026-05-12 (re-eval) | 89 | Independent fresh eval. Surfaced bash validator fragility (1.2 = 4 → 3): no `http(s)://` filter, no URL-decode, paths anchored to `docs/` root instead of source file dir. Same verdict bucket as import. |
| 2026-05-12 (post-fix) | **99** | Applied all 7 P2 fixes from the re-eval. New layout: `references/regex-recipes.md` + `references/error-taxonomy.md` + `references/conventions.md` + `scripts/check-doc-naming.sh`. SKILL.md slimmed 252 → 137 body lines. Hardened link validator (HTTP/mailto/anchor skip, URL-decode, source-dir resolution). Structured `[OK]`/`[FAIL]`/`BROKEN:` output with exit codes 0/1/2. Sibling cross-links to `bash-macos` + `swift-file-splitting`. CommonMark + GFM citations. "When to break the convention" section. Smoke-tested on clean and planted-fault fixtures — both pass. Only remaining gap: no bundled automated test harness (7.3 = 3/4). |
