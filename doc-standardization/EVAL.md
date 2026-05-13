# doc-standardization Evaluation

**Date:** 2026-05-12 (Phase 1 MOVE-AS-IS from Tiercade)
**Evaluator:** Claude Opus 4.7
**Skill version:** Imported from `Tiercade/skills/doc-standardization`, de-projectized
**Automated score:** 100% (13/13)

---

## Automated Checks

```
📋 Skill Evaluation: doc-standardization
==================================================
  [STRUCTURE]
    ✅ SKILL.md / frontmatter / name match / no extras / resource dirs non-empty
  [TRIGGER]
    ✅ Description length adequate
    ✅ Description includes trigger contexts (Use when…)
  [DOCUMENTATION]
    ✅ SKILL.md body length
    ✅ References linked from SKILL.md
  [SCRIPTS]
    ✅ No scripts/ — n/a
  [SECURITY]
    ✅ No hardcoded credentials or emails

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Import Summary

Imported as-is from `Tiercade/skills/doc-standardization/SKILL.md` (252 lines)
with Phase 1 de-projectize sweep applied. No reference files; single SKILL.md.

**Frontmatter changes:**
- Dropped `metadata` block (`version`, `author: "Tiercade"`, `category`, `tags`,
  `discovered_from`, `evidence_commits`)
- Dropped `applyTo: "docs/**/*.md"` (project-glob, not portable)
- Added `author: eworthing` per repo convention
- Description rewritten: leads with capability summary, expanded from 40 → 79
  words, added explicit "Use when…" phrase + 7 trigger contexts, removed
  embedded trigger-quote list (rolled into prose)

**Body changes:**
- Dropped `Evidence commits:` block (4 commit hashes) from Purpose section
- Dropped commit hash from References section
- Step 7 "Run Naming Consistency Validation" rewritten: project-specific
  `run_local_gate.sh` reference removed; replaced with generic guidance on
  wiring a project's own validator into pre-commit/CI
- Code-Documentation Alignment table: replaced `ScreenID.headToHead` and
  `VisualAuditScenario.mainGridDefault` with generic `ScreenIdentifier.searchScreen`
  and `SnapshotScenario.homeScreenDefault` examples
- Validation paragraph: replaced specific paths (`docs/testing/testability-contract.md`,
  `scripts/visual_audit/run_visual_audit.sh`, `ScreenID`) with generic
  identifier-class descriptions
- References section: dropped `docs/specs/naming-standardization-spec-implemented.md`,
  `docs/specs/README.md`, specific `scripts/validate_naming_consistency.sh` path,
  and commit hash; kept generic `AGENTS.md`/`CLAUDE.md` + generic script-name reference

**Verification:**
- Forbidden grep (`tiercade`, `tierlogic`, `tiercadecore`, `appstate`, `screenid.`,
  `palette.`, `tvmetrics`, `tiermetrics`, `evidence_commits`, `run_local_gate`,
  `build_install_launch`, etc.): **0 hits**
- Allow-list body grep (`focusToken`, `UITestAXMarker`, `Liquid Glass`): **0 hits**
  (none introduced)

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Covers full lifecycle: naming convention, audit, rename, cross-ref fix, index update, validation, project-specific naming consistency. Status suffix reference table + directory structure reference + code-doc alignment guidance. |
| 1.2 | Correctness | 4/4 | `git mv` workflow is current; markdownlint-cli2 invocation is the current package; broken-link grep is standard. No deprecated tooling. |
| 1.3 | Appropriateness | 4/4 | Markdown reference, no scripts, no deps. |
| 2.1 | Fault Tolerance | 3/4 | Common Mistakes section enumerates 5 historical failure modes; broken-link validation loop in Step 6 catches mid-rename. Could add a "what if rename collides" recovery recipe. |
| 2.2 | Error Reporting | 3/4 | `BROKEN: $link` output pattern shown; markdownlint surfaces violations. No structured error taxonomy. |
| 2.3 | Recoverability | 4/4 | All operations use `git mv` — fully reversible via git. Index updates are plain Markdown edits. |
| 3.1 | Token Cost | 3/4 | 240 lines single file; no progressive-disclosure references. Appropriate for the surface area, but a future split (e.g. `references/regex-recipes.md`) would help if the script set grows. |
| 3.2 | Execution Efficiency | 4/4 | No scripts; bash one-liners are linear in doc count. |
| 4.1 | Learnability | 4/4 | Two complete worked examples (renaming a spec, organizing research). Naming convention table reads at a glance. |
| 4.2 | Consistency | 4/4 | Numbered Steps 1–7, consistent code-fence usage, tables follow same format. |
| 4.3 | Feedback Quality | 3/4 | Validation step shows expected output shape; "BROKEN: …" is specific. Could add expected-success indicators. |
| 4.4 | Error Prevention | 4/4 | Explicit "search before rename", "update H1", "update index", "no spaces" rules. Common Mistakes lists the 5 known fail modes. |
| 5.1 | Discoverability | 4/4 | "Use when…" phrase present; 7 trigger contexts in description; explicit "Do NOT use when" list inside SKILL.md. |
| 5.2 | Forgiveness | 4/4 | `git mv` based — every step reversible. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No untrusted input surface. |
| 6.3 | Data Safety | 4/4 | Read + git-based rename only; no destructive shell operations. |
| 7.1 | Modularity | 3/4 | Single-file skill. Reasonable for size but no `references/`. |
| 7.2 | Modifiability | 4/4 | Add new status suffix → one table row. Add new domain prefix → one row. Add new validator command → Step 7 paragraph. |
| 7.3 | Testability | 2/4 | No mechanism to detect drift against the conventions described (e.g. a verifier that scans a docs/ tree and reports violations against this skill's rules). No upstream-source citations (CommonMark, GitHub Flavored Markdown spec). |
| 8.1 | Trigger Precision | 4/4 | Description names specific operations: renames, link fixes, index updates, doc-tree audits. "Do NOT use when" carves out single-file edits and non-doc files. |
| 8.2 | Progressive Disclosure | 3/4 | Body is the only layer; no references/. SKILL.md is short enough that this is acceptable, but a `references/regex-recipes.md` for the bash one-liners would let the agent skim Steps 1–5 first and only load grep details when needed. |
| 8.3 | Composability | 3/4 | Cross-links generic `AGENTS.md` / `CLAUDE.md`. No explicit cross-link to sibling skills (e.g. `bash-macos` for portable grep/sed, `swift-file-splitting` for the maximum-lines convention). |
| 8.4 | Idempotency | 4/4 | Re-running grep/find/markdownlint produces same result; `git mv` is naturally idempotent (target stays renamed). |
| 8.5 | Escape Hatches | 3/4 | Project-specific Step 7 marked Optional; "Do NOT use when" list provides clear opt-out paths. No explicit "when to break the naming rule" guidance. |
| | **TOTAL** | **91/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. Add `references/regex-recipes.md` so the grep/find/markdownlint one-liners
   live separately from the workflow body. Improves 8.2 (Progressive Disclosure)
   and 3.1 (Token Cost) to 4/4.
2. Cross-link to sibling skills: `bash-macos` (portable grep/sed for the audit
   commands), `swift-file-splitting` (analogous "file size limit" pattern).
   Improves 8.3 (Composability) to 4/4.
3. Add upstream citations: CommonMark spec, GitHub Flavored Markdown spec,
   Apple "code-doc alignment" patterns. Improves 7.3 (Testability) and 1.2
   (Correctness) anchoring.
4. Add a "when to break the naming convention" subsection (e.g. legacy specs
   intentionally preserved, vendor-supplied docs). Improves 8.5 (Escape Hatches).
5. Add expected-output indicators alongside the validation commands so the
   agent knows what "passing" looks like. Improves 4.3 (Feedback Quality).
6. Add a structured error taxonomy table (broken link / orphan file / index
   drift / case violation) with diagnostic recipes. Improves 2.2 (Error Reporting).

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (import) | 100% structural / 91 manual | Phase 1 MOVE-AS-IS from Tiercade. Dropped frontmatter metadata + applyTo + evidence_commits. Genericized Code-Doc Alignment table (ScreenID → ScreenIdentifier, VisualAuditScenario → SnapshotScenario). Stripped Tiercade-specific script paths from Step 7 + References. Description rewritten to "Use when…" with 7 trigger contexts. |
