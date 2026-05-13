# swiftui-file-export Evaluation

**Date:** 2026-05-12
**Evaluator:** agent (Claude Opus 4.7)
**Skill version:** initial (extracted from Tiercade `file-export` skill)
**Automated score:** 100% (13/13 structural checks pass)

---

## Merge Summary

This skill is a portable extraction of the Tiercade-internal `file-export`
skill. The following were generalized or removed:

- `TierListExportItem` → generic `DocumentExportItem`
- `app.overlays.pendingExportItem` / `app.overlays.showFileExporter` →
  generic `exportCoordinator.pendingExportItem` / `showFileExporter` on an
  `@Observable` (or `ObservableObject`) instance injected at the Scene level
- All Tiercade file paths (`MainAppView+Modals.swift`, `TiercadeCommands.swift`,
  `OverlaysState.swift`, `ToolbarExportFormatSheetView.swift`,
  `Export/TierListExportItem.swift`, `docs/specs/...`,
  `docs/research/...`) removed
- `.tierproj` content type and `Logger.export` Tiercade-specific subsystem
  replaced with generic `Logger` references
- `metadata:` block, `evidence_commits`, `applyTo` glob, and
  `author: "Tiercade Team"` removed from frontmatter
- Added explicit "Do NOT Use For" section and a debugging table with new
  symptoms (wrong file extension, missing `DataRepresentation` for a
  format, "Operation not permitted")
- Expanded the menu-bar Commands rule with full `@Observable`/Scene
  injection guidance
- Retained the WWDC22 "Meet Transferable" reference as a legitimate
  Apple source

## Verification

- `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py
  swiftui-file-export` → 100% (13/13 checks passed)
- `grep -irE
  "(tiercade|tierlogic|tiercadecore|appstate|screenid|palette\.[a-z]|tvmetrics|tiermetrics|modelresolver|projectvalidation|stagingstate|finalize[Cc]hange|build_install_launch|run_local_gate|run_ui_tests|sync_skills|init_skill|tiercade-schema|evidence_commits|launchtiercade|com\.tiercade|\.tierproj)"
  swiftui-file-export/SKILL.md` → no matches
- `grep -E "(focusToken|UITestAXMarker|Liquid Glass)"
  swiftui-file-export/SKILL.md` → no matches
- SKILL.md body length: 318 lines (within target band)

---

## Automated Checks

```
📋 Skill Evaluation: swiftui-file-export
==================================================
Path: /Users/Shared/git/agent-skills/swiftui-file-export

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
| 1.1 | Completeness | 4/4 | Covers single + multi-format Transferable, ShareLink vs. fileExporter, all three platforms, sandbox, entitlements, menu-bar Commands, debugging table. |
| 1.2 | Correctness | 4/4 | API signatures match iOS 16+/macOS 13+ SDK; root-placement rule and entitlement match documented Apple behavior. |
| 1.3 | Appropriateness | 4/4 | Modern Transferable API is the recommended Apple-sanctioned approach; no third-party deps. |
| 2.1 | Fault Tolerance | 3/4 | Skill is documentation; doesn't run code. Guidance covers `Result<URL, Error>` failure path and surface-error logging. |
| 2.2 | Error Reporting | 3/4 | Debugging table maps symptoms → fixes. Could add example logging output. |
| 2.3 | Recoverability | 3/4 | N/A for documentation skill; user-driven save panels are inherently re-runnable. |
| 3.1 | Token Cost | 3/4 | 318 lines, slightly above the 250-line ideal but within target band for a feature skill with code samples + tables. No reference files needed yet. |
| 3.2 | Execution Efficiency | 4/4 | No scripts; no execution overhead. |
| 4.1 | Learnability | 4/4 | Critical Rules section leads with the macOS placement gotcha; WRONG/CORRECT pairs throughout. |
| 4.2 | Consistency | 4/4 | Tables, WRONG/CORRECT pairs, and section ordering match peer SwiftUI skills in this repo. |
| 4.3 | Feedback Quality | 4/4 | Symptom-to-check debugging table is the highest-value section for diagnostic flows. |
| 4.4 | Error Prevention | 4/4 | All three "Critical Rules" are framed as anti-patterns first; entitlement section explicitly lists what NOT to add. |
| 5.1 | Discoverability | 4/4 | Description leads with capability summary + concrete "Use when…" triggers covering 12 distinct phrases. |
| 5.2 | Forgiveness | 3/4 | Guidance steers toward user-driven save panels (inherently forgiving — user picks location). |
| 6.1 | Credential Handling | 4/4 | No credentials; skill is style/pattern guidance. |
| 6.2 | Input Validation | 3/4 | Reminds reader to verify `item` non-nil and content-type matching; could expand on bad-data scenarios. |
| 6.3 | Data Safety | 4/4 | Hard rule against direct-write to user directories; sandbox-first approach. |
| 7.1 | Modularity | 4/4 | Sections are self-contained — Critical Rules, Implementation, Decision table, Platform table, Debugging — each independently consumable. |
| 7.2 | Modifiability | 4/4 | Easy to add new formats (chain another `DataRepresentation`), new symptoms (append to debugging table), or new platforms. |
| 7.3 | Testability | 3/4 | Patterns are testable in host app via UI tests; skill itself has no code to test. |
| 8.1 | Trigger Precision | 4/4 | Description includes 12+ specific triggers (fileExporter, Transferable, ShareLink, NSSavePanel, CSV/JSON, menu bar, sandbox, silent failure). |
| 8.2 | Progressive Disclosure | 3/4 | Two-level (frontmatter description → SKILL.md). No references/ yet because the body is still compact enough; could split debugging into references if it grows. |
| 8.3 | Composability | 3/4 | Composes naturally with swiftui-design-tokens, xctest-ui-testing (identifier conventions + AccessibilityMarkerView for fileExporter sheet markers), and ios-security-hardening. No machine-readable output (n/a for guidance skill). |
| 8.4 | Idempotency | 4/4 | Documentation skill; re-reading is always safe. |
| 8.5 | Escape Hatches | 4/4 | "Do NOT Use For" section explicitly lists out-of-scope cases (file import, tvOS-only, server writes). |
| | **TOTAL** | **92/100** | Solid, publishable. |

## Priority Fixes

### P0 — Fix Before Publishing
1. None — skill passes structural checks and meets the ≥90 manual threshold.

### P1 — Should Fix
1. If the body grows beyond ~400 lines as formats are added, split the
   debugging table and the multi-format examples into `references/*.md`.

### P2 — Nice to Have
1. Add a short `references/cross-platform-examples.md` with full working
   App + Scene + Commands sample once a real downstream consumer needs it.
2. Add explicit guidance on `FileDocument` vs. ad-hoc `Transferable` for
   document-based apps.

## Revision History
| Date       | Score   | Notes |
|------------|---------|-------|
| 2026-05-12 | 92/100  | Baseline — initial extraction from Tiercade `file-export` skill. |
