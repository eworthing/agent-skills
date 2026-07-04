# swiftui-file-export Evaluation

**Date:** 2026-07-04
**Evaluator:** agent (Claude Opus 4.8)
**Skill version:** full-expansion pass (`references/` added: filedocument, dialog-configuration, cross-platform-example)
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
- `grep -irE "(tiercade|tierproj)" swiftui-file-export/SKILL.md
  swiftui-file-export/references/` → no matches (skill content clean; EVAL.md
  retains historical extraction provenance intentionally)
- Every `references/*.md` linked by name from SKILL.md (`check_references_linked`
  passes): filedocument.md, dialog-configuration.md, cross-platform-example.md
- SKILL.md length: 398 lines (under the 400-line target, well under the
  500-line evaluator warn); heavy material now lives in `references/`
- All new APIs verified against live `developer.apple.com` DocC before writing:
  `FileDocument` (iOS 14+, not deprecated), `ReferenceFileDocument` (deprecated
  in the iOS 27 SDK; successors `Document`/`ReadableDocument`/`WritableDocument`),
  `item:…onCompletion:onCancellation:` (iOS 17+/macOS 14+), the `fileDialog*`
  family + `fileExporterFilenameLabel` (iOS 17+/macOS 14+), `ShareLink`
  (visionOS 1+/watchOS 9+)

**Note on `[SCRIPTS]` automated checks:** this skill ships **no** scripts, so the
two `[SCRIPTS]` checks pass vacuously — they are **N/A**, not evidence of validated
executable code. The 13/13 reflects structure/trigger/docs/security, not scripts.

## Model Coverage

This skill is API-reference guidance — it ships no executable code, so "testing"
means verifying the description triggers and the patterns apply correctly per
model, not running scripts.

- **Authored / validated under:** Claude Opus 4.7 (see `Evaluator` above).
- **Target models:** Opus 4.x and Sonnet 4.x Claude Code sessions — the tiers
  that typically apply SwiftUI export patterns.
- **Haiku 4.5:** supported (triggers and patterns are model-agnostic) but not
  separately validated; spot-check before relying on it there.

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
| 2.2 | Error Reporting | 4/4 | Debugging table maps symptoms → fixes; now includes sample `Logger` console output for success/failure and a silent-cancel diagnostic row. |
| 2.3 | Recoverability | 3/4 | N/A for documentation skill; user-driven save panels are inherently re-runnable. |
| 3.1 | Token Cost | 4/4 | Body 398 lines (under the 400 target); heavy material (FileDocument, dialog config, full worked example) disclosed to `references/` and loaded only on demand. |
| 3.2 | Execution Efficiency | 4/4 | No scripts; no execution overhead. |
| 4.1 | Learnability | 4/4 | Critical Rules section leads with the macOS placement gotcha; WRONG/CORRECT pairs throughout. |
| 4.2 | Consistency | 4/4 | Tables, WRONG/CORRECT pairs, and section ordering match peer SwiftUI skills in this repo. |
| 4.3 | Feedback Quality | 4/4 | Symptom-to-check debugging table is the highest-value section for diagnostic flows. |
| 4.4 | Error Prevention | 4/4 | All three "Critical Rules" are framed as anti-patterns first; entitlement section explicitly lists what NOT to add. |
| 5.1 | Discoverability | 4/4 | Description leads with capability summary + concrete "Use when…" triggers covering 12 distinct phrases. |
| 5.2 | Forgiveness | 3/4 | Guidance steers toward user-driven save panels (inherently forgiving — user picks location). |
| 6.1 | Credential Handling | 4/4 | No credentials; skill is style/pattern guidance. |
| 6.2 | Input Validation | 4/4 | Verifies `item` non-nil; now also covers the `contentType` ∈ `writableContentTypes` rule (silent wrong-type fallback) and user-cancel handling via `onCancellation:`. |
| 6.3 | Data Safety | 4/4 | Hard rule against direct-write to user directories; sandbox-first approach. |
| 7.1 | Modularity | 4/4 | Sections are self-contained — Critical Rules, Implementation, Decision table, Platform table, Debugging — each independently consumable. |
| 7.2 | Modifiability | 4/4 | Easy to add new formats (chain another `DataRepresentation`), new symptoms (append to debugging table), or new platforms. |
| 7.3 | Testability | 3/4 | Patterns are testable in host app via UI tests; skill itself has no code to test. |
| 8.1 | Trigger Precision | 4/4 | Description includes 12+ specific triggers (fileExporter, Transferable, ShareLink, NSSavePanel, CSV/JSON, menu bar, sandbox, silent failure). |
| 8.2 | Progressive Disclosure | 4/4 | Three-level now: frontmatter → SKILL.md → three `references/*.md`, mapped by a "Load References As Needed" table. Heavy material loads only when the branch needs it. |
| 8.3 | Composability | 4/4 | Explicit "Sibling Skills — Defer When" section routes to `swiftui-drag-drop` (inbound), `swiftui-native-ux` (placement), `ios-security-hardening` (sandbox), `xctest-ui-testing` (markers). No machine-readable output (n/a for guidance skill). |
| 8.4 | Idempotency | 4/4 | Documentation skill; re-reading is always safe. |
| 8.5 | Escape Hatches | 4/4 | "Do NOT Use For" section explicitly lists out-of-scope cases (file import, tvOS-only, server writes). |
| | **TOTAL** | **97/100** | Full-expansion pass closed the FileDocument, dialog-config, worked-example, and composability gaps; remaining sub-4 rows (2.1/2.3 fault-tolerance, 5.2 forgiveness, 7.3 testability) are inherent to a run-nothing documentation skill. |

## Priority Fixes

### P0 — Fix Before Publishing
1. None.

### P1 — Should Fix
1. ✅ Done — `references/` split introduced (filedocument, dialog-configuration,
   cross-platform-example) with a "Load References As Needed" table; body held at
   398 lines.

### P2 — Nice to Have
1. ✅ Done — `references/cross-platform-example.md` ships a full App + Scene +
   coordinator + Commands + entitlements sample.
2. ✅ Done — `references/filedocument.md` covers `FileDocument` vs. ad-hoc
   `Transferable`, plus the iOS 27 reference-type deprecation.
3. Open — a `.fileImporter` companion skill remains a genuine future gap (out of
   scope here by design).

## Revision History
| Date       | Score   | Notes |
|------------|---------|-------|
| 2026-05-12 | 92/100  | Baseline — initial extraction from Tiercade `file-export` skill. |
| 2026-06-03 | 92/100  | Declared model coverage (closes AR-CC-S12); SKILL.md body unchanged. |
| 2026-07-04 | 97/100  | Full-expansion pass: FileDocument + dialog config + multi-doc + worked example split to `references/`; `onCancellation:`; visionOS row; sibling cross-refs; real reference URLs. |
