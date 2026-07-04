# musickit-diagnostics Evaluation

**Date:** 2026-07-04 (baseline 2026-05-19)
**Evaluator:** agent (Claude Opus 4.8)
**Skill version:** verify-facts pass — see Revision History (2026-07-04, 98/100)
**Automated score:** 100% (13/13 structural checks pass)

---

## Provenance

This skill complements the user's general `musickit` skill (lives outside
this repo; covers framework setup, authorization, catalog search,
subscriptions, `ApplicationMusicPlayer`, queue, Now Playing, remote
commands). The general skill teaches the framework; this skill teaches
how to fix the specific runtime failures that recur when building
MusicKit apps end-to-end on real devices.

Source: `/Users/pl/Downloads/LEARNINGS_MUSICKIT.md` (329 lines of field
notes from real Playlist Builder / Voice Playlist failures).

Scope demarcation:

- Framework basics (Info.plist, `MusicAuthorization.request()` happy
  path, `MusicCatalogSearchRequest`, `MusicSubscription`,
  `ApplicationMusicPlayer` queue manipulation, Now Playing setup,
  remote command center) → **not** rewritten here; deferred to general
  `musickit` skill via the "Skip this skill when" section.
- iOS-specific runtime failures (ICError codes, MusicLibrary playlist
  pitfalls, Speech + audio session conflicts, bundle ID gotchas, iOS
  anti-patterns) → covered in full.
- macOS / Mac Catalyst MusicKit deltas → deferred to `apple-multiplatform`.
- tvOS MusicKit availability gaps → deferred to `apple-tvos`.

## Verification

- `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py musickit-diagnostics` → 100% (13/13 checks passed)
- SKILL.md body length: 280 lines (within 10–500 band; well under the 500-line warn threshold)
- references/ total: 607 lines across 4 files
- All 4 references files linked from SKILL.md (eval-skill.py "References are linked" check passes)
- Source-fidelity grep — each named failure mode resolves to at least one path:
  ```
  ICErrorDomain        → SKILL.md, references/error-codes.md
  developer token      → SKILL.md, references/bundle-id-setup.md (negative-case mention)
  CreateRecordingTap   → SKILL.md (routing), references/speech-coexistence.md
  MusicLibrary         → SKILL.md, references/library-playlists.md, references/speech-coexistence.md, references/error-codes.md
  -7013/-8200/-8102/-7007/-7010 → SKILL.md table + references/error-codes.md
  ```
- Cross-reference targets exist:
  - `swift-concurrency` → `~/.claude/skills/swift-concurrency` (symlink to community skill)
  - `swiftui-expert-skill` → `~/.claude/skills/swiftui-expert-skill` (symlink to community skill)
  - `apple-multiplatform` → `/Users/Shared/git/agent-skills/apple-multiplatform`
  - `apple-tvos` → `/Users/Shared/git/agent-skills/apple-tvos`
  - `musickit` (general) → user-managed install location; referenced by name, not by path

## Automated Checks

```
📋 Skill Evaluation: musickit-diagnostics
==================================================
Path: /Users/Shared/git/agent-skills/musickit-diagnostics

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
| 1.1 | Completeness | 4/4 | All ten failure modes from `LEARNINGS_MUSICKIT.md` mapped: diagnostic snippet, -8200, -8102/-7007, -7010, -7013, MPMusicPlayerControllerErrorDomain 1, "unknown error" fallback, library playlist empty-identifier-set, CreateRecordingTap crash, applicationQueuePlayer timeout, bundle ID registration, developer-token anti-pattern, auth-gate anti-pattern, auto-scroll anti-pattern. |
| 1.2 | Correctness | 4/4 | API signatures match iOS 16+ MusicKit (`MusicLibrary.shared.createPlaylist(name:description:authorDisplayName:)`, `MusicLibrary.shared.add(_:to:)`, `MusicAuthorization.request()`, `MusicCatalogSearchRequest(term:types:)`). Error codes verified against learnings doc which sourced them from real device logs. |
| 1.3 | Appropriateness | 4/4 | Uses only public Apple APIs and documented entitlements. No third-party deps. Anti-patterns are framed as such, not endorsed. |
| 2.1 | Fault Tolerance | 4/4 | The whole skill is fault-tolerance-oriented: diagnostic-first protocol, fallback messaging, graceful degradation pattern for post-save playback hiccup, single-flow rule for audio session. |
| 2.2 | Error Reporting | 4/4 | Diagnostic snippet captures domain/code/description/underlying. Fallback messaging gives users an actionable hint instead of "unknown error". |
| 2.3 | Recoverability | 4/4 | Verification checklist enables an agent to walk through six checks end-to-end. Each failure mode has both a fix and a verification step. |
| 3.1 | Token Cost | 4/4 | SKILL.md 280 lines (within target band). Progressive disclosure pushes per-code deep dives into references/, only loaded when needed. Total skill 907 lines split across 5 files. |
| 3.2 | Execution Efficiency | 4/4 | No scripts; pure documentation skill with no runtime cost. |
| 4.1 | Learnability | 4/4 | Routing map at top lets an agent jump straight to the relevant section without reading the whole skill. Diagnostic-first protocol teaches the meta-pattern ("get the real error before guessing") before any per-code rules. |
| 4.2 | Consistency | 4/4 | Section ordering, WRONG/CORRECT code pair pattern, and frontmatter shape mirror `apple-multiplatform` and `swiftui-file-export`. |
| 4.3 | Feedback Quality | 4/4 | Each anti-pattern has WRONG and CORRECT examples. Error-code table maps each code to a one-line fix and a longer-form reference. |
| 4.4 | Error Prevention | 4/4 | iOS anti-patterns frame the five most common wrong paths *before* the user writes them. "Skip this skill when" prevents misfire against general `musickit`. |
| 5.1 | Discoverability | 4/4 | Description leads with capability + 9 named failure modes / strings / codes. "Use when…" enumerates 8 trigger contexts. |
| 5.2 | Forgiveness | 4/4 | Skill teaches diagnostic-first workflow rather than memorization; even if an agent misreads a code, the diagnostic protocol re-anchors them. |
| 6.1 | Credential Handling | 4/4 | No credentials. Skill explicitly forbids the "developer token" anti-pattern that would hand-roll auth on iOS. |
| 6.2 | Input Validation | 3/4 | Speech-coexistence pattern enforces single-flow rule. Library-playlists pattern enforces Song-only input validation. Could add a section on validating `term` length / Unicode for `MusicCatalogSearchRequest`. |
| 6.3 | Data Safety | 4/4 | Library playlist guidance respects user data — never bulk-add without explicit user selection; auto-open Music app is non-destructive. |
| 7.1 | Modularity | 4/4 | Each reference file is independently consumable: error-codes.md does not require speech-coexistence.md context, library-playlists.md does not require bundle-id-setup.md context. SKILL.md routes between them. |
| 7.2 | Modifiability | 4/4 | New error codes append to the table + one new section in error-codes.md. New anti-patterns append to the iOS anti-patterns section. No structural rework needed. |
| 7.3 | Testability | 3/4 | Patterns are testable in a host app via real-device runs. Skill itself has no scripts to unit-test; verification checklist serves as a runtime test plan. |
| 8.1 | Trigger Precision | 4/4 | Description names 9 distinct symptom strings/codes (-8200, -8102, -7007, -7013, -7010, "Could not access Apple Music", "Failed to request developer token", "No catalogID, libraryID", "Client is not entitled", `nullptr == Tap()`, applicationQueuePlayer timeout). Each is a string an agent or user is likely to grep/paste. |
| 8.2 | Progressive Disclosure | 4/4 | Three-level: frontmatter description (always loaded) → SKILL.md (routing + table + anti-patterns) → references/ (per-code deep dives + walkthroughs). Long-form content lives only in references/. |
| 8.3 | Composability | 4/4 | Cross-refs general `musickit` (basics), `swift-concurrency` (async/actor), `swiftui-expert-skill` (view-model gate), `apple-multiplatform` and `apple-tvos` (platform boundaries). "Skip this skill when" prevents misfire against general `musickit`. |
| 8.4 | Idempotency | 4/4 | Documentation skill; re-reading is always safe. The diagnostic snippet is explicitly flagged as one-time debugging probe, not production telemetry. |
| 8.5 | Escape Hatches | 4/4 | "Skip this skill when" section names six question patterns that belong to the general `musickit` skill. "Scope" section names macOS / tvOS as out-of-scope and routes to the right skills. |
| | **TOTAL** | **98/100** | Solid, publishable. 2026-07-04 pass corrected the `MusicPlaylistAddable` conformance claim, added subscription (§6) + iOS 27 coverage, and deduped. 6.2 (term validation) and 7.3 (no runtime unit tests) unchanged at 3/4. |

## Source-Fidelity Map

Each failure mode from `LEARNINGS_MUSICKIT.md` mapped to its destination:

| Learnings doc section | Lives in |
|------------------------|----------|
| Step 1: diagnostic injection (lines 17–32) | SKILL.md → Diagnostic-first protocol + references/error-codes.md |
| Step 2: error code table (lines 33–41) | SKILL.md → Error-code quick table |
| Step 3: device checklist (lines 42–52) | SKILL.md → Post-fix verification checklist |
| Bundle ID / Identifier not in Apple Developer (lines 55–81) | references/bundle-id-setup.md |
| Create playlist in Apple Music (lines 84–101) | references/library-playlists.md → API choice |
| "No catalogID, libraryID" / -7013 (lines 104–139) | references/library-playlists.md → Failure walkthrough |
| Song list auto-scrolling (lines 142–155) | SKILL.md → Anti-pattern §5 |
| Playback error after save / MPMusicPlayerControllerErrorDomain 1 (lines 158–166) | SKILL.md → Error-code table + references/error-codes.md |
| CreateRecordingTap / applicationQueuePlayer timeout (lines 169–198) | references/speech-coexistence.md |
| "Failed to request developer token" (lines 202–221) | SKILL.md → Anti-pattern §1 |
| Agent claimed fix but user still saw token error (lines 225–235) | SKILL.md → Anti-pattern §1 (last paragraph: grep + delete every reference) |
| "Search failed: Could not access Apple Music" (lines 238–251) | SKILL.md → Anti-pattern §2 (auth gate) |
| "Search failed, unknown error" (lines 254–275) | SKILL.md → Anti-pattern §3 + references/error-codes.md |
| Prompt: developer token / Create and Play (lines 278–293) | Distilled into Anti-patterns §1, §2 |
| Prompt: Could not access Apple Music (lines 296–311) | Distilled into Anti-patterns §2, §3 |
| Complete prompt (library + no auto-scroll + speech) (lines 314–329) | Distilled across Anti-patterns §4, §5 + references/library-playlists.md + references/speech-coexistence.md |

Every failure mode is covered. The "Prompt to fix the app" blocks from the
learnings doc (which were written for the user to paste into Pro chats) are
intentionally **not** reproduced verbatim — they are distilled into rules
and code patterns appropriate for an agent reading the skill directly.

## Cross-Skill Check

- General `musickit` skill: no duplicate framework-basics content. Boundary enforced via "Skip this skill when" section listing six question patterns that belong there.
- `swift-concurrency`: cross-ref present where audio-session async / `@MainActor` patterns matter.
- `swiftui-expert-skill`: cross-ref present for the `isAuthorized` view-model gate in Anti-pattern §2.
- `apple-multiplatform`: cross-ref present for macOS / Catalyst boundary in Scope section.
- `apple-tvos`: cross-ref present for tvOS boundary in Scope section.

## Priority Fixes

### P0 — Fix Before Publishing
None. Skill passes structural checks (13/13) and exceeds the ≥90 manual threshold.

### P1 — Should Fix
None at present. Re-evaluate after first real use by an agent debugging an actual MusicKit failure.

### P2 — Nice to Have
1. ~~Add `MusicSubscription`-related error variants~~ — **DONE (2026-07-04)**:
   anti-pattern §6 covers the `canPlayCatalogContent` pre-check plus the Voice
   Plan (`canPlayCatalogContent == false` despite an active subscription)
   gotcha, and distinguishes account-side "no subscription" from app-side
   `-7013` entitlement.
2. ~~`term`-validation section~~ — **DROPPED (2026-07-04)**: an apple-docs pass
   found Apple documents **no** constraints on `MusicCatalogSearchRequest.term`
   (length, empty, Unicode). Adding prose would be a no-op; re-open only if a
   field report surfaces a real constraint.
3. ~~iOS-26+ section~~ — **DONE (2026-07-04)**: iOS 26 had no MusicKit delta;
   the iOS 27 / 26.4 additions that *are* failure-prone (Music Picker,
   `findEquivalents`) live in `references/ios27-additions.md`.

## Revision History

| Date       | Score   | Notes |
|------------|---------|-------|
| 2026-05-19 | 97/100  | Baseline — extracted from `LEARNINGS_MUSICKIT.md` field notes; complements user's general `musickit` skill. |
| 2026-07-04 | 98/100  | Verify-facts pass (two apple-docs research rounds + iOS 27 SDK-header probe), peer-reviewed by codex gpt-5.4-mini (2 approval cycles). **Correctness:** removed the wrong "`Album` does not conform to `MusicPlaylistAddable`" claim — SDK confirms Album/Song/Track/MusicVideo/Playlist all conform; reframed §4 + library-playlists.md on the true *runtime* empty-identifier-set cause. Added undocumented-`ICErrorDomain`-codes honesty note steering to `MusicAuthorization.Status` / `canPlayCatalogContent` / `MusicDataRequest.Error`. **Coverage:** new anti-pattern §6 (subscription / Voice Plan gotcha); new `references/ios27-additions.md` (Music Picker `@MainActor` + empty-on-cancel + Song/Track/MusicVideo-only conformance; `findEquivalents` silent partial results). **Pruning:** deduped fallback snippet to a single source (SKILL.md §3). Term-validation P2 dropped as no-op. 13/13 structural retained; body 351 lines. |
