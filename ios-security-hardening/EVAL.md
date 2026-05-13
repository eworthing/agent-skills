# ios-security-hardening Evaluation

**Date:** 2026-05-12 (post-Phase-3 merge from Tiercade)
**Evaluator:** Claude Opus 4.7
**Skill version:** SKILL.md after URL Source Resolution merge
**Automated score:** 100% (13/13)

---

## Automated Checks

```
  [STRUCTURE]
    ✅ SKILL.md exists
    ✅ SKILL.md has valid frontmatter
    ✅ Skill name matches directory
    ✅ No extraneous files
    ✅ Resource directories are non-empty (no references/ — OK for single-file skill)
  [TRIGGER]
    ✅ Description length adequate (61 words)
    ✅ Description includes trigger contexts (Use when…)
  [DOCUMENTATION]
    ✅ SKILL.md body length (445 lines)
    ✅ References are linked from SKILL.md (no references/)
  [SCRIPTS]
    ✅ No scripts/
  [SECURITY]
    ✅ No hardcoded credentials or emails
    ✅ Environment variables documented (no scripts/)

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Merge Summary

Imported from `Tiercade/skills/security-hardening`:
- **URL Source Resolution pattern** (~75 lines) — generic `ImageSource` enum + `imageSource(from:allowedDomains:)` function that branches asset catalog / bundled asset / local file / remote URL references. De-projectized from Tiercade's `URLValidator.imageSource()` and `AssetImageProvider`.
- **HTTP-alongside-HTTPS rationale** for image CDN allowlist (image CDNs sometimes serve over HTTP; domain allowlist is the primary security boundary).
- **Three failure-mode notes** explaining what the branching prevents (silent failures from mismatched APIs, unvalidated `javascript:`/`data:` schemes).

Rejected (Tiercade-coupled):
- Frontmatter `evidence_commits` array (4 commit hashes)
- Body commit-hash citations
- `TiercadeCore`/`Tiercade` file paths
- Tiercade type names: `URLValidator.imageSource()`, `AssetImageProvider.image(named:)` — replaced with generic `imageSource(from:allowedDomains:)` and `loadAssetCatalogImage(named:)`.

Also fixed while editing:
- Description warnings (was 85% structural): "Relevant when…" → "Use when…", word count 26 → 61.

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Covers path traversal, URL validation, multi-source URL resolution (new), CSV/JSON sanitization, BOM stripping, AI prompt sanitization, size limits, secret handling, sandbox dirs, iOS data protection, entitlement scoping. Audit checklist + anti-patterns. |
| 1.2 | Correctness | 4/4 | URLComponents recommendation matches Apple guidance. iOS Data Protection levels accurate. HTTP-alongside-HTTPS rationale verified (CDN reality). |
| 1.3 | Appropriateness | 4/4 | Markdown reference, right tool. |
| 2.1 | Fault Tolerance | 3/4 | Anti-pattern + audit checklist sections preempt common failures. No retry semantics (N/A doc). |
| 2.2 | Error Reporting | 4/4 | New "three classes of mistake" callout explicitly enumerates silent-failure modes the branching prevents. |
| 2.3 | Recoverability | 4/4 | Read-only artifact. |
| 3.1 | Token Cost | 3/4 | 445 lines SKILL.md — over the 150-line target but no references/ split would help. Single-file skill is acceptable for security checklists (need to read end-to-end). |
| 3.2 | Execution Efficiency | 4/4 | No scripts. |
| 4.1 | Learnability | 4/4 | GOOD/BAD/WRONG/CORRECT pairs throughout; complete `ImageSource` enum example with caller branching. |
| 4.2 | Consistency | 4/4 | Uniform code-fence style, uniform anti-pattern callouts, audit checklist at end. |
| 4.3 | Feedback Quality | 4/4 | New section explicitly enumerates silent-failure cases. |
| 4.4 | Error Prevention | 4/4 | Strong: explicit `javascript:`/`data:` scheme call-out; domain allowlist as primary boundary stated. |
| 5.1 | Discoverability | 4/4 | "Use when…" phrase present; trigger contexts listed. |
| 5.2 | Forgiveness | 4/4 | Read-only. |
| 6.1 | Credential Handling | 4/4 | Secret/credential section explicit; recommends URLComponents over interpolation. |
| 6.2 | Input Validation | 4/4 | Whole skill is about input validation. |
| 6.3 | Data Safety | 4/4 | iOS Data Protection levels documented; entitlements scoping called out. |
| 7.1 | Modularity | 3/4 | Single SKILL.md; could split into refs (path-traversal, url-validation, csv-sanitization). Not blocking — security checklists benefit from linear read. |
| 7.2 | Modifiability | 3/4 | New attack pattern → append section. No need to edit existing content. |
| 7.3 | Testability | 2/4 | No mechanism to detect drift against OWASP guidance or platform API changes. No source-link citations. |
| 8.1 | Trigger Precision | 4/4 | Description expanded to enumerate specific contexts (CSV/JSON, image refs, restoration, etc.). |
| 8.2 | Progressive Disclosure | 3/4 | Linear single-file — fine for a security checklist; less elegant than reference-split skills. |
| 8.3 | Composability | 3/4 | Doc-only. Composes with `xctest-ui-testing` (test patterns include attack-input fuzzing) implicitly. No explicit cross-link. |
| 8.4 | Idempotency | 4/4 | Read-only. |
| 8.5 | Escape Hatches | 3/4 | Documents iOS data protection level trade-offs; HTTP-alongside-HTTPS rationale shows when to relax (with caveat). |
| | **TOTAL** | **92/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None. No blockers.

### P1 — Should Fix
None. Description + multi-source pattern landed.

### P2 — Nice to Have
1. Split into `references/path-traversal.md`, `references/url-validation.md`, `references/csv-sanitization.md` if file grows past 500 lines.
2. Add upstream citations to OWASP Mobile Security Testing Guide sections per pattern. Improves `7.3` testability.
3. Cross-link to `xctest-ui-testing` for security-test patterns (fuzz input, malformed CSV).

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 85% structural / ~86 manual | Pre-merge. 2 description warnings. |
| 2026-05-12 (post-merge) | 100% structural / 92 manual | URL Source Resolution pattern merged from Tiercade. Description warnings fixed. |
