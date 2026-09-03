# OCR small-4 corpus vs contest-refactor run #9 — scope audit (2026-09-03)

**Question (owner):** are contest-refactor's misses against the two validated OCR corpora caused by
scoping, i.e. files the loop never opened, rather than by judgment?

**Answer:** yes, almost entirely. Run #9 explicitly read 66 of 580 source files (11%). Of the 224
validated-real OCR findings across both corpora, 14 (6%) sit in files the run read; 210 sit in files
it never opened. Nothing was *excluded*: all 104 finding files are inside the loop's enumerated
universe and none is dropped by `_fs_filters`. The gap is **selection** (churn ranking plus six
hotspot candidates), which is the loop's design as a sampling reviewer, not an accident.

## Method

- Run #9 sessions (`ses_f9d01c015ffe…` orchestrator, `ses_f9cfae6d8ffe…` loop, `ses_f9ccaa445ffe…`
  reviewer, `ses_f9ca8a35affe…` loop-2 challenger, `ses_f9d881499ffe…` setup) read from opencode's
  sqlite `part` table (`~/.local/share/opencode/opencode.db`).
- **Read** = a `read` tool call's `filePath`, or a bash `cat|sed|head|tail|awk|nl` naming the path.
  **Seen** = the path appears anywhere in a tool input or output (a grep hit counts). Read is the
  honest figure; seen is a ceiling.
- The observe plugin (`~/.config/opencode/plugins/observe-tools.ts`) records `argKeys` only for
  `read`, so paths are recoverable from sqlite alone. One-line fix candidate: log `filePath` for
  `read`/`glob`/`grep`.
- Corpora: `scan-domain-validated.json` (283 findings, 157 CONFIRMED/ESCALATE) at `2b5247e9`;
  `scan-small4-validated.json` (97 findings, 67 CONFIRMED/ESCALATE) at `909164fb`, scope
  StoreKit + StarterSounds + BoardsFeature + SettingsFeature, 27 files reviewed, 9.75M tokens on
  `qwen3.8-flash`, 40m46s.

## Coverage by module

| Module | Files | Read by run #9 | OCR real findings | In read files |
| --- | --- | --- | --- | --- |
| BenchHypeApplication | 184 | 19 | 0 | 0 |
| BenchHypeDomain | 90 | 8 | 157 | 8 |
| BenchHypePersistence | 69 | 2 | 0 | 0 |
| BenchHypeSharedUI | 54 | 6 | 0 | 0 |
| BenchHypeLibraryFeature | 54 | 10 | 0 | 0 |
| BenchHypeLiveFeature | 34 | 6 | 0 | 0 |
| BenchHypeAudio | 18 | 6 | 0 | 0 |
| BenchHypeAppleMusic | 11 | 6 | 0 | 0 |
| BenchHypeSettingsFeature | 10 | 2 | 29 | 6 |
| BenchHypeBoardsFeature | 10 | 0 | 25 | 0 |
| BenchHypeStarterSounds | 3 | 0 | 9 | 0 |
| BenchHypeStoreKit | 3 | 0 | 4 | 0 |
| **Total** | **580** | **66** | **224** | **14** |

Seen-anywhere ceiling: 219 files (38%); citation ledger after the run-9 fix: 29/607 (4.8%).
Zero-finding modules are zero because OCR has not scanned them yet, not because they are clean.

In-read misses: small4 46, 47, 48 (PaywallView, which loop 1 *edited* for the `public`
narrowing), 71, 72, 73 (SettingsScreenContent); domain 1, 31, 33, 34, 211, 212, 275, 277.
Every run-9 role ran on `qwen3.8-flash`, so these 14 are flash judgment misses and say nothing
about the Claude Critic.

Selection follows churn: commits touching each module in the last 400 — Application 285,
Domain 152, Persistence 118, LibraryFeature 91, LiveFeature 75, SharedUI 62, SettingsFeature 29,
BoardsFeature 16, StarterSounds 5, StoreKit 3. The six hotspot candidates were all in
Application/Audio/Persistence/Domain/scripts.

## Correction to the 2026-09-02 analysis

`OCR-VS-CONTEST-REFACTOR-BENCHHYPE-2026-09-02.md` reasoned about *why the Critic missed* the
Values-invariant findings as if it had read those files. 149 of the 157 real Domain findings were
in files the run never opened. The invariant detector (DD-15) keeps its justification, but as a
**selection** aid: it points Step 0 at Values files the churn walk skips. That is how it was wired
at 6c.

## Shipped aids against the small-4 modules (at `909164fb`)

- `audit_dead_surface.py`: `StarterSoundGate.violations` → `test_only` (0 prod / 35 test refs),
  which heads the fail-open cluster 80, 81, 83–87 (the gate runs only under `swift test`). Also
  19 `enum_case` rows in `Codable` enums decoded from the manifest — a false-positive shape
  (on Tiercade only 3 of 45 dead enum-case rows sit in Codable enums, so the fix is small).
  Missed 15/31 (`audioFileMetadata`, write-only stored property), 77 (`attributionRequired`),
  83 (`licenseReviewStatus`): stored properties are not a walked declaration kind.
- Invariant queue: `invariant: 0` in all four modules. Correct silence — this corpus is not
  Values-class — and the DD-15 re-entry criterion (a second corpus lifting recall to 7/10) is
  **not** met by it.
- Lexically visible and not yet a rule: enum cases constructed in a reducer and never matched in
  a view (50, 51, 52) — `.failed(` 23 constructions vs 1 pattern match in production for the
  Diagnostics/Backup phases.

## Restraint signatures in the 30 rejections

localization for infrastructure that does not exist (1, 11, 70, 74); stale index unreachable
because the lookup is recomputed every render (3, 4, 5, 13); wrapper/narrow-surface refactor with
no defect (7, 14, 24, 30, 65); speculative state or future SDK case (36, 38, 41, 78, 88, 89);
finish-before-cache is deliberate and the cache self-heals (91, 92, 94); contradicts the repo's own
documented invariant (37); confabulated mechanism, `usesRegularInterface` does not exist (59);
unmeasured perf (82); race no human can produce (66); auto-republish already covers it (49).

## What to do next, ranked

1. **Module-level coverage roll-up in the HALT handoff** (`coverage_ledger.py`, zero loop-path
   tokens): the disclosure should read "BoardsFeature 0/10 read" so a 9.5 certification is
   legible as "9.5 on 11% of files".
2. **Scoped flash run on `BenchHypeSettingsFeature` at `909164fb`** (`--scope`, 10 files,
   29 real findings, 6 already in read files): ~$1 on opencode, answers recall-given-files for the
   same model. Then a Step-1-only Claude replay for the model confound once the Sonnet spend limit
   resets. This replaces the deferred W4 with a measurement that has a denominator.
3. **Dead-surface increments**, measured on Tiercade before wiring: Codable-enum cases disclosed
   not flagged; stored-property write-only rule (targets 15/31, 77, 83); enum-case
   constructed-never-matched prototype (50, 51, 52).
4. **Reviewer-cases** from the ten restraint signatures above (needs LLM baselines; blocked on the
   spend limit this month).

Not recommended: new lens prose (the docket's zero-lift record stands) or the canonical v3 bump
(unchanged from the 2026-09-03 decision).

## Scoped dry-run result — 2026-09-03, same day

`/contest-refactor --reset --dry-run --scope BenchHypeKit/Sources/BenchHypeSettingsFeature` from
opencode at `909164fb`, loop model `opencode-go/qwen3.8-flash`. Sessions `ses_f9798b911ffe…`
(main) and `ses_f97946651ffe…` (loop). Wall 861s, 3396 tests green, cost $0.34 (11.6M cache-read,
84k output). HALT_DRY_RUN after Step 2; bookkeeping files left modified, no source change.

**Coverage: 10/10 Settings files explicitly read** (read tool or cat/sed), plus 12 out-of-scope
files. Selection is no longer the explanation for anything below.

**Recall against the 29 validated-real OCR sites in the module: 0/29.** Four findings emitted
(F-025 display mapping in views, F-026 permissive defaults in SettingsScreenContext, F-027
DiagnosticsView `public`, F-028 no render test for the control-to-intent mapping); scoped
scorecard average 9.33, concurrency 10, test_strategy 8.5. Site overlaps, all with a different
defect named:

| OCR site | OCR defect | What the Critic wrote at the same site |
| --- | --- | --- |
| 45 `statusMessage` | `.restoredAwaitingReload` arm drops the carried `error`, reads as success | hotspot `confirm` → F-025: the label mapping belongs on the owner type |
| 63, 64/73 `applySettingsChange` / `settingBinding` | stale-snapshot read-modify-write (ESCALATE); update + save dispatched on every slider tick | Authority Map verdict "Single and clear"; hotspot `confirm` → F-028: no test |
| 40, 42 `fileImporter` / `fileMover` | restore with no confirmation; `.failure` arm silently dropped | framework_idioms 9.5 proof cites them as native idioms |
| 68 refresh button | no in-flight / failure surface (ESCALATE) | concurrency 10 proof: "`.task` refreshes are view-lifecycle-scoped and reducer-guarded" |
| 65 (OCR **rejected**: defaults not reachable today) | — | F-026, the Critic's second finding |

Not touched at all: 39/44 (view gate ≠ reducer gate), 50/51/52 (`.failed` phases never
rendered), 46/47 (paywall price nil / pending swallowed), 71/72 (canonical vs draft reads),
the seven help-copy drifts (54–58, 60), the four accessibility findings (48, 61, 62, 67), 69, 53.

**Reading.** With every file read, a flash Critic asked the rubric's questions — ownership,
layering, idioms, test presence — and answered them plausibly, then certified 9.5 on dimensions
whose proof text names the exact sites where OCR's confirmed bugs live. The rubric can express
most of these (hidden state machines, silent failure, draft-vs-canonical authority); the Critic
did not apply it that way. What OCR found and this run cannot: bugs. What this run found and OCR
cannot: the missing render test (F-028), which is a real gap.

**Open confound: the model.** The docket's "legible 5/5" results were measured with a Claude
Critic on planted fixtures. This is the first real-corpus recall figure and it is on flash. Next:
the identical command from Codex, same cost class, same day if possible. If Codex also lands near
0/29, the gap is the method's question set, not the judge, and a per-file bug pass (OCR's shape)
becomes a candidate Step-0 aid rather than a lens.
