# musickit-diagnostics Evaluation

**Date:** 2026-08-22 (manual rubric last scored 2026-07-14; baseline 2026-05-19)
**Evaluator:** agent (Claude Sonnet 5)
**Skill version:** iOS 27 accuracy + registration pass — see Revision History (2026-07-14, 98/100)
**Automated score:** 100% (15/15 structural checks pass)

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

- `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py musickit-diagnostics` → 100% (15/15 checks passed; grew from 13→15 since 2026-07-14 as the checker gained a body-token-count check and a literal-secret-prefix check — both pass, this is tooling growth, not a regression)
- SKILL.md body length: 351 lines (body = 373 total − 22 frontmatter lines through the closing `---`; within 10–500 band, under the 500-line warn threshold)
- references/ total: 728 lines across 5 files
- All 5 references files linked from SKILL.md (eval-skill.py "References are linked" check passes)
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
| 1.1 | Completeness | 4/4 | All ten failure modes from `LEARNINGS_MUSICKIT.md` mapped: diagnostic snippet, -8200, -8102/-7007, -7010, -7013, MPMusicPlayerControllerErrorDomain 1, "unknown error" fallback, library playlist empty-identifier-set, CreateRecordingTap crash, applicationQueuePlayer timeout, bundle ID registration, developer-token anti-pattern, auth-gate anti-pattern, auto-scroll anti-pattern. |
| 1.2 | Correctness | 4/4 | API signatures match iOS 16+ MusicKit (`MusicLibrary.shared.createPlaylist(name:description:authorDisplayName:)`, `MusicLibrary.shared.add(_:to:)`, `MusicAuthorization.request()`, `MusicCatalogSearchRequest(term:types:)`). Error codes verified against learnings doc which sourced them from real device logs. |
| 1.3 | Appropriateness | 4/4 | Uses only public Apple APIs and documented entitlements. No third-party deps. Anti-patterns are framed as such, not endorsed. |
| 2.1 | Fault Tolerance | 4/4 | The whole skill is fault-tolerance-oriented: diagnostic-first protocol, fallback messaging, graceful degradation pattern for post-save playback hiccup, single-flow rule for audio session. |
| 2.2 | Error Reporting | 4/4 | Diagnostic snippet captures domain/code/description/underlying. Fallback messaging gives users an actionable hint instead of "unknown error". |
| 2.3 | Recoverability | 4/4 | Verification checklist enables an agent to walk through six checks end-to-end. Each failure mode has both a fix and a verification step. |
| 3.1 | Token Cost | 4/4 | SKILL.md body 351 lines (within target band). Progressive disclosure pushes per-code deep dives into references/, only loaded when needed. Total skill 1101 lines split across 6 files (SKILL.md + 5 references). |
| 3.2 | Execution Efficiency | 4/4 | No scripts; pure documentation skill with no runtime cost. |
| 4.1 | Learnability | 4/4 | Routing map at top lets an agent jump straight to the relevant section without reading the whole skill. Diagnostic-first protocol teaches the meta-pattern ("get the real error before guessing") before any per-code rules. |
| 4.2 | Consistency | 4/4 | Section ordering, WRONG/CORRECT code pair pattern, and frontmatter shape mirror `apple-multiplatform` and `swiftui-file-export`. |
| 4.3 | Feedback Quality | 4/4 | Each anti-pattern has WRONG and CORRECT examples. Error-code table maps each code to a one-line fix and a longer-form reference. |
| 4.4 | Error Prevention | 4/4 | iOS anti-patterns frame the five most common wrong paths *before* the user writes them. "Skip this skill when" prevents misfire against general `musickit`. |
| 5.1 | Discoverability | 4/4 | Description leads with capability + 9 named failure modes / strings / codes. "Use when…" enumerates 8 trigger contexts. |
| 5.2 | Forgiveness | 4/4 | Skill teaches diagnostic-first workflow rather than memorization; even if an agent misreads a code, the diagnostic protocol re-anchors them. |
| 6.1 | Credential Handling | 4/4 | No credentials. Skill explicitly forbids the "developer token" anti-pattern that would hand-roll auth on iOS. |
| 6.2 | Input Validation | 3/4 | Speech-coexistence pattern enforces single-flow rule. Library-playlists pattern enforces the catalog-identifier rule (Song or Track must be catalog-sourced; the bare Album container isn't addable directly). Could add a section on validating `term` length / Unicode for `MusicCatalogSearchRequest`. |
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

## writing-for-agents Audit (2026-08-22)

Applied the context-pointer / information-hierarchy / co-location lens for the
first time (distinct from the ISO/Shneiderman rubric above, which had never
been checked against this framework before):

- **Anti-pattern co-location — verified pass.** All 6 WRONG/CORRECT pairs
  (SKILL.md ~lines 128–289) stay inline with their explanations rather than
  being split out to references/. No change needed.
- **"Remove the diagnostic before merging" appears twice** (SKILL.md ~102–104
  in the diagnostic-first protocol, and ~321–323 in the pre-merge verification
  checklist). Reviewed and kept as deliberate reinforcement at two distinct
  points an agent actually passes through, not duplication to trim.
- **Description length (942 chars)** exceeds this repo's established 400–800
  target band (under the 1024 hard cap). Reviewed and left as-is: the
  9-named-error-code breadth is what earned 8.1 Trigger Precision 4/4 below,
  and trimming risks that strength for a sizing-convention gain. User-confirmed
  2026-08-22.
- **GitHub-anchor links functionally inert for agent consumption.** SKILL.md's
  routing table links to `#icerrordomain--8200-...`-style anchors that only
  resolve in GitHub's web renderer — an agent reading via `Read` gets the
  whole file and never resolves markdown fragments (harmless in practice,
  since the agent still gets the full target file either way — this is a
  cosmetic/GitHub-only gap, not a functional break). Not unique to this
  skill: a repo-wide grep (`grep -rlE ']\(#[a-z0-9-]+\)'`) confirmed the same
  pattern in at least 8 other skills (apple-multiplatform, apple-tvos,
  contest-refactor, peer-plan-review, quorum-review, swiftui-design-tokens,
  swiftui-file-export) plus README.md and docs/. **Flagged as a repo-wide
  convention question for a separate follow-up** (per user decision
  2026-08-22), not fixed here in isolation.
- iOS 27 beta/GA staleness in `references/ios27-additions.md` (also present
  in 2–3 sibling skills) was raised and explicitly punted per user decision
  2026-08-22 — out of scope for this pass.

None of the above changed the manual rubric score — findings were confirmatory
(verified-pass or reviewed-and-kept) or explicitly deferred, not corrective.

## Behavioral Test — Iteration 1 (2026-08-22)

First-ever behavioral test for this skill (previously had no `evals/`
directory). 3 scenarios via `evals/evals.json`, each run with-skill and
baseline (no skill) in `musickit-diagnostics-workspace/iteration-1/`, graded
against per-scenario assertions, aggregated with skill-creator's
`aggregate_benchmark.py`, and reviewed via a static `generate_review.py`
HTML report.

**Result: with-skill 91.7% (11/12 assertions) vs. baseline 91.7% (11/12) —
tied, after correcting a two-sided grading error described below.** Original
grading read with-skill 100% vs. baseline 83.3%; both numbers were wrong in
the same direction, for the same reason.

| Scenario | With-skill | Baseline | Notes |
|---|---|---|---|
| Library-add Album silent failure | 3/4 (corrected from 4/4) | 4/4 (corrected from 3/4) | The skill's SKILL.md/library-playlists.md wording at test time claimed only `Song` (not `Track`) reliably carries a populated identifier set. A Context7 + web-search check against Apple's own `MusicPlaylistAddable` conformance docs found `Track` is a first-class, directly-addable conformer — the claim was a skill overclaim, not fact. The **with-skill run faithfully reproduced that overclaim as a stated fact** ("the item that reaches add must be a Song, not an Album") — that's the skill actively misleading its own consumer, not a harmless extra step, so it now fails that assertion. The **baseline run**, working from general knowledge alone, passed raw `Track` values without ever claiming Song was required — it was right and the skill was wrong. Skill wording corrected in both files (renamed "Song-only rule" → "the catalog-identifier rule"; Track-from-`album.tracks` added as an equally valid path); the WRONG-Album-example's claimed mechanism was also softened from an invented explanation to observed-not-documented, since Apple's own conformance list includes `Album` and nothing publicly documents why passing it directly no-ops. |
| Speech + MusicKit tap crash | 4/4 | 4/4 | Smallest gap of the three. `AVAudioEngine`'s single-tap-per-bus constraint is a well-known iOS gotcha independent of MusicKit, so general model knowledge already covers it well. Both fixes are independently correct, though the with-skill answer additionally ties in the sibling `applicationQueuePlayer` timeout as sharing the same root cause. |
| Generic ICError triage | 4/4 | 3/4 | Baseline correctly leads with diagnostic-first instrumentation (this is standard `NSError`-handling practice, not skill-unique), but recommends **keeping** structured domain/code capture permanently in production crash reporting — the opposite of the skill's explicit "remove before merging" instruction. This is a genuine product-judgment divergence surfaced by testing, not a knowledge gap, and is worth the skill's owner re-examining on its own merits rather than treating as a simple baseline miss. |

Full transcripts, grading evidence, and the benchmark summary are in
`musickit-diagnostics-workspace/iteration-1/` (`review.html`, `benchmark.md`,
per-scenario `grading.json`). This did not change the manual rubric score,
but it is worth being direct about what the tied 91.7%/91.7% result means:
on the one scenario where this skill's guidance was factually wrong, the
with-skill agent did *worse* than a baseline agent reasoning from general
knowledge alone, because it faithfully repeated the skill's own incorrect
claim. That is exactly the failure mode a documentation-correctness pass
exists to catch, and it is now fixed at the source (SKILL.md +
library-playlists.md). The ICError scenario's baseline miss remains a
genuine product-judgment divergence for the skill owner to weigh, not a
documentation defect.

Note: `benchmark.md`'s time/token columns read 0 — this dispatch environment's
task-completion notifications didn't surface `total_tokens`/`duration_ms` to
the coordinator, so those fields were left at their true default rather than
fabricated. Pass-rate and grading data are unaffected.

## Priority Fixes

### P0 — Fix Before Publishing
None. Skill passes structural checks (15/15) and exceeds the ≥90 manual threshold.

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
| 2026-08-22 | 98/100  | Combined audit (superpowers:writing-skills + skill-creator + writing-for-agents) + first-ever behavioral test. **Structural:** eval-skill.py grew 13→15 checks since last run, all pass, no regression. **writing-for-agents pass (new):** anti-pattern co-location verified, "remove the diagnostic" duplication reviewed-and-kept (two distinct decision points), description length (942 chars, over the 400-800 band) reviewed-and-kept per user decision, GitHub-anchor links in the routing table found functionally inert for agent (`Read`-tool) consumption — flagged as a repo-wide convention question for a separate follow-up rather than a one-file fix. iOS 27 beta/GA staleness raised and punted per user decision. **Behavioral test (new):** first `evals/evals.json` (3 scenarios) + `musickit-diagnostics-workspace/iteration-1/` — final result with-skill 91.7% (11/12) tied with baseline 91.7% (11/12); see Correction below for why. Baseline's one remaining miss on the ICError scenario is a genuine policy divergence (recommends keeping vs. removing the domain/code diagnostic) worth the skill owner's own review. **Correction (same day, user-requested):** the library-add scenario was initially graded with-skill 4/4 / baseline 3/4, on the theory that baseline's fix (passing raw `Track` instead of `Song`) wouldn't work. Re-investigated via Context7 + web search against Apple's actual `MusicPlaylistAddable` conformance docs: `Track` conforms directly, carries its own populated identifier set when catalog-sourced, and needs no conversion to `Song`. The skill's own "Song-only rule" wording was the overclaim — and the **with-skill run had faithfully restated that overclaim as fact** ("the item that reaches add must be a Song, not an Album"), which is the skill actively misleading its own consumer, not a harmless extra step. Re-graded to with-skill 3/4 / baseline 4/4 (net: tied 11/12 each). Fixed at the source: renamed the section to "the catalog-identifier rule" in `references/library-playlists.md` and SKILL.md anti-pattern §4, added a Track-from-`album.with(.tracks)` code path as equally correct (using the same `guard let` pattern already used elsewhere in the file, not an unverified `?? []`), corrected the pre-call-checklist item that implied only Song was acceptable, and softened the WRONG-Album-example's claimed mechanism from an invented "it's a single item not a collection" explanation to "observed, not documented" — Apple's own conformance list includes `Album`, so the real reason passing it directly no-ops isn't publicly known. Re-graded `grading.json` for both runs and re-ran `aggregate_benchmark.py`. No manual-rubric criterion changed net of the correction — findings were confirmatory/deferred (writing-for-agents pass) or a real documentation-correctness fix caught by testing (behavioral pass), not a new defect. Score held at 98/100. |
| 2026-05-19 | 97/100  | Baseline — extracted from `LEARNINGS_MUSICKIT.md` field notes; complements user's general `musickit` skill. |
| 2026-07-14 | 98/100  | iOS 27 accuracy + registration pass (peer-reviewed by codex gpt-5.6-sol @ high, 4 rounds to APPROVED). **Correctness:** fixed a false platform-availability claim in `references/ios27-additions.md` — Music Picker was documented as "iOS / iPadOS / **Mac Catalyst** 27.0+ (visionOS — metadata only)"; canonical DocC gives **iOS / iPadOS / visionOS 27.0, Beta, no Mac Catalyst** for both `musicPicker(...)` and `PickableMusicItem`. The omission is real, not a docs gap — `findEquivalents` *does* list Catalyst, so DocC surfaces it when supported. Removed the "Mac reaches the picker via Catalyst" guidance (it does not exist there) and stopped dismissing visionOS as metadata-only. **Coverage:** new Music Picker failure mode #4 — the `selection` binding persists/accumulates across presentations (derived from Apple's own `.onChange` count-diff sample, flagged as observed-not-documented); noted Pickable ≠ Addable (`Album` conforms to `MusicPlaylistAddable` but not `PickableMusicItem`). **Surface audit:** re-verified WWDC26 s254 + the framework availability index — `PickableMusicItem` is the only Beta symbol in MusicKit and `findEquivalents` (26.4) the only other 2026-cycle addition, so the two covered items are the *complete* new surface; the session's subscription-offer material (`MusicSubscriptionOffer.Options`, `messageIdentifier`) is iOS 15+ and correctly already marked pre-existing. **Registration:** added to the README Apple-platform catalog and the `SKILLS=()` install array (was absent from both). **Bookkeeping:** corrected stale counts (body 280→351, refs "607/4 files"→728/5, total "907/5"→1101/6). 13/13 structural retained. |
| 2026-07-04 | 98/100  | Verify-facts pass (two apple-docs research rounds + iOS 27 SDK-header probe), peer-reviewed by codex gpt-5.4-mini (2 approval cycles). **Correctness:** removed the wrong "`Album` does not conform to `MusicPlaylistAddable`" claim — SDK confirms Album/Song/Track/MusicVideo/Playlist all conform; reframed §4 + library-playlists.md on the true *runtime* empty-identifier-set cause. Added undocumented-`ICErrorDomain`-codes honesty note steering to `MusicAuthorization.Status` / `canPlayCatalogContent` / `MusicDataRequest.Error`. **Coverage:** new anti-pattern §6 (subscription / Voice Plan gotcha); new `references/ios27-additions.md` (Music Picker `@MainActor` + empty-on-cancel + Song/Track/MusicVideo-only conformance; `findEquivalents` silent partial results). **Pruning:** deduped fallback snippet to a single source (SKILL.md §3). Term-validation P2 dropped as no-op. 13/13 structural retained; body 351 lines. |
