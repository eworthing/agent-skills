# OCR Domain scan vs. contest-refactor run #9 — what each should have found

Date: 2026-09-02. Inputs: opencodereview (`ocr scan --path BenchHypeKit/Sources/BenchHypeDomain`,
qwen3.8-flash, session `383f579d`, 142 findings across 37 files at the time of this cut; scan still
running) versus contest-refactor run `run-2026-09-02-8747656f…` (opencode, qwen3.8-flash, `--reset`,
HALT_SUCCESS at loop 2, all eight dimensions 9.5).

Verification status at Revision 1: four OCR highs had their cited lines checked (#2, #53, #85,
#122); the other 138 were classified on the claim as written. Revision 2 below replaces that with
the validated outcomes for every row. Severity labels are OCR's.

## Revision 2 (2026-09-03) — validated outcomes supersede the claim-level read below

Source: `BenchHype/.artifacts/ocr/scan-domain-validated.json` — 283 findings after the retry scan
covered all 89 Domain files; Sonnet/Fable validation, failing-test-first remediation in eight
commits (`5ef7a09c` … `80499e9c`); a Codex second pass agreed 281/283 with templated notes and was
judged near-zero information.

**Whole scan:** 73 applied (48 fixes, 17 deletions, 8 doc corrections), 125 rejected (44%),
56 declined as a class ("contract lives in prose", Rule 10), 25 owner-gated Rule 3/4 remodels,
4 escalated. 43 claims were put behind a failing test: 36 real, 7 disproved.

**My 142 (the Ports-heavy first batch):** 18 applied, 74 rejected, 38 declined, 7 owner-gated,
1 owner. **Of my 95 "should find": 9 applied, 52 rejected, 22 declined, 7 owner-gated.** The
premise of Revision 1 was wrong in the direction that matters: contest-refactor's silence on
`Ports/` was mostly correct restraint, not a coverage failure.

- Class **B** (single-consumer `AsyncStream`) and class **C** (`Sendable` without serialization)
  are named false-positive signatures in the validation: the streams go through
  `StateBroadcaster` by design, and every conformer is an actor or `@MainActor`. Class **A**
  (return-type collapse): 0 applied.
- My four "verified" highs: **#2 applied**; **#53 rejected** (`AVAudioRecorder.stop()` closes the
  file synchronously; my check confirmed the cited lines existed, not the conclusion);
  **#85 rejected**; **#122 rejected** (SwiftUI keeps the first `@State` value for the scene's
  lifetime, so the throwaway relays are never iterated). Of the six "judgment misses", only
  **#133** (duckFallbackRoutes dual writer) held. #2 held but was a local decode bug, not a
  lens item.
- **Retracted:** Revision-1 recommendation 1 (port-contract detector) would have fed the Critic
  mostly rejected or declined items. Recommendation 2 (AsyncStream lens line) would have encoded a
  false-positive signature. Recommendation 4's presence-count guardrail stands as a proof-quality
  point, but the count was not hiding real bugs in `Ports/`.

**Where the real bugs were:** the `Values/` batch my table never covered. The 48 fixes cluster in
value-type invariants: one-sided numeric guards on `Double` (7), NaN through `min`/`max`,
non-finite inputs, synthesized `Codable` bypassing a throwing init (2), positional sentinels that
shift on edit (3), duplicate IDs stored in aggregates (Setlist, Script, Roster), playback elapsed
on `.ending`/`.errored`, error-mapping order (2), plus 13 dead symbols found by grep and the one
dual writer.

**Contest-refactor reach on those:** still zero, and for a structural reason beyond coverage.
Leaf value types with ten-line inits are low-churn and low cognitive density, so neither the churn
top-3 nor the hotspot scanner ever ranks them; the Authority Map is state-slice grained. The
domain-integrity lens that targets exactly this class was parked in June on "recall lift 0,
defects too legible", measured on fixtures. This corpus is the input that measurement lacked: 36
test-confirmed bugs the loop never had a path to.

**Revised proposal, mechanical first, no new prose levers:**

1. **Step-0 value-invariant detector** (candidate evidence, `promotion_allowed: false`, ast-grep
   on Swift, same precedent as DD-06/DD-07): Domain value inits or validators with a one-sided
   numeric guard on `Double` (no lower bound or no `isFinite`), `min`/`max` on an unguarded
   `Double`, an array-of-ID field stored without a uniqueness check, `Codable` synthesized on a
   type whose designated init throws. Would have put at least 12 of the 48 fixes in front of the
   Critic.
2. **Step-0 zero-reference detector**: public declarations, enum cases and protocol requirements
   with no non-test reference. 13 applied deletions here, and it generalizes the F-024 sweep the
   loop already does by hand (`audit-public-surface.sh` covers removed/changed since a rev; this is
   the zero-caller variant).
3. **Keep the prior-audit intake.** 19 rejections were "already declined in `docs/audits/README.md`".
   Verify run #9's Step 0 actually recorded `prior_audit_docs`; the adopt-or-falsify step is the
   skill's cheapest false-positive filter.
4. **Coverage stays report-only.** OCR spent 24.1M tokens on 89 files; whole-file dwell over 607 is
   not the loop's shape. The two detectors are how leaf value types become visible without being
   read.
5. **Precision lessons corroborate the existing design**, nothing to change: "CONFIRMED is a
   claim, not a bug" is the Critic's crux-and-reproducer rule; "reviewer agreement is near-zero
   information" is the cross-provider memory; test-first remediation is Rule 11.

The classes table and appendix below keep the Revision-1 verdicts; the appendix gains a
**Validated outcome** column so the two can be compared row by row.

## Bottom line (Revision 1, 2026-09-02 — superseded above)

- **95 of 142 (67%) are inside contest-refactor's declared lens** and it found none of them.
  Cause is coverage, not the lens: across all 19 history loops the skill cited **three** files
  under `BenchHypeDomain/` and **zero** under `BenchHypeDomain/Ports/`. Run #9's ledger figure is
  29/607 files cited (4.8%).
- **Six of those 95 were in files the run did inspect** and still missed (judgment, not coverage):
  the TransportEventRelay single-consumer bus (#122/#123), the DomainInvariantError decode
  fallback cited as *proof* of domain_modeling 9.5 (#2), StateBroadcaster (#141/#142), and the
  AppSettings dual-writer inside a churn-top-20 file it read for dispatch shape (#133).
- **11 are partly in scope** (documented invariant vs. conformer drift). The mandatory doc-vs-code
  grep only fires on marker tokens (`LEGACY|TEMPORARY|DEPRECATED|…`), so ordinary contract comments
  are never checked against conformers.
- **36 are correctly out of contest-refactor's remit**: 22 prose-only or speculative
  ("a future conformer could…") that the rubric's `Ignore:` line excludes, and 14 real but local
  bugs that a repo-scope leverage loop finds only opportunistically. That is what a per-file
  scanner is for.
- The architecture_quality 9.5 proof "26/26 BenchHypeDomain/Ports protocols have production
  conformer + test fake" is a presence count standing in for contract quality. The rubric names
  that pattern: fake-clean reward.

## Classes

| Code | Class | Count | Should CR find? | Where the lens already says so | Why run #9 missed it |
| --- | --- | --- | --- | --- | --- |
| A | Port return type collapses distinct outcomes (bare snapshot / `Bool` / `Optional` / `nil`-and-throws) | 14 | **Yes** | Method Step 3 canon smell *adapter output contract incompleteness* | COV — no Ports file read |
| B | Single-consumer `AsyncStream` exposed as broadcast, stream lifetime / replay unspecified | 9 | **Yes** | Step 5 concurrency (task lifetime, reentrancy) | COV, plus **JUDG** on #122/#123: the adversarial pass asked whether an injectable seam had leverage (SPT Q5), not whether one stream can serve two iterators |
| C | `Sendable` asserted without serialization / isolation, reentrancy and cancellation contract absent | 11 | **Yes** | lens-apple "Sendable and cross-actor usage"; Step 5 | COV; #141 JUDG (StateBroadcaster named as a fix target in loop 1) |
| D | Parallel fields admit impossible states; documentation-only invariants on public inits | 16 | **Yes** | Step 7 hidden state machines; BenchHype Hard Rule 3 which the Critic reads | COV — Domain value types never read |
| E | Ownership: dual writers, ambient identity minting, untargeted singleton | 6 | **Yes** | Step 2 Authority Map, canon *stable workflow identity* | COV; #133 **JUDG** (both writers in AppReducer+Workflow.swift, a file the run read to count dispatch arms) |
| F | Silent swallow / no failure path (`try?`, `continue`-as-success, discarded yield result) | 10 | **Yes** | Failure modes & observability silent-swallow audit | COV — the audit's grep targets were run over roots the Critic then did not follow into Ports conformers |
| G | Security / privacy: framework text and paths into user copy, raw filenames to unlink, unvalidated URLs, mic keeps recording after dismiss | 5 | **Yes** | lens-security (always-included); #54 is also canon *reservation after suspension* | COV |
| H | Resource retention / structural waste (whole-track PCM decode for artwork, unbounded buffers, temp files never removed) | 6 | **Yes** | lens-efficiency D1–D4 | COV |
| J | Duplicate mapping sites, dead protocol requirements, misplaced layer | 18 | **Yes** | Step 6 simplification; the registry already holds this genre (F-024, "PlaybackOrigin coding duplicated") | COV — the 26/26 port sweep checked conformer presence and stopped one grep short of per-requirement production callers |
| I | Documented invariant no conformer enforces, or conformers disagree | 11 | **Partly** | HR-12 (BenchHype rule the Critic applies); Step 6 doc-vs-code grep | Design gap: the grep keys on marker tokens only, never on contract comments |
| K | Prose-only, under-specified doc, style, speculative future conformer | 22 | **No** | rubric `Ignore:` (stylistic, speculation) | — |
| L | Real but local bugs (decode round-trip, error-mapping order, default disagreement) | 14 | **Not by design** | Findable when the file is read for another reason | The mechanism is repo-scope leverage, not a per-file sweep |

Why-missed codes: **COV** file never cited in any loop; **JUDG** file or type inspected in run #9
and the defect not seen; **OOS** excluded by rubric; **OPP** opportunistic only.

## Should contest-refactor change?

Recommendation is one detector and one lens line. Not a per-file sweep, and not more
judgment prose (the 2026-08-26 stop decision on prose-clause levers stands).

1. **Build: port-contract candidate detector at Step 0** (same shape as DD-06/DD-07: candidate
   evidence, `promotion_allowed: false`, zero loop-path tokens). For every `protocol` under a
   ports-like directory, emit per requirement: return type in {`AsyncStream`, `Bool`, `Optional`,
   bare struct} on a `throws` or `async` member, doc-comment invariant words ("never", "exactly
   once", "must", "guaranteed"), conformer count, and production call-site count. That mechanizes
   classes A, B, J-dead-surface and hands I to the Critic as leads. It would have put 41 of the 95
   in front of the Critic in run #9. Cost: one script plus a selftest, no prose growth.
2. **Add one line to lens-apple concurrency**: an `AsyncStream` reached through a protocol
   requirement, a computed accessor, or a shared property is single-consumer; verify exactly one
   iterator exists and name it. Class B is nine findings and one shipped bug the codebase itself
   documents; the run reasoned about the relay's *shape* and never its semantics.
3. **Do not**: add a Sendable-audit sweep (C), a parallel-fields sweep (D), or a doc-comment
   verifier (I) as loop-path steps. Each is real but each is a per-file pass; that is OCR's job,
   and the two tools are complementary at exactly this seam.
4. **Watch, do not gate**: the coverage ledger already reported 4.8%. The run reached HALT_SUCCESS
   with an entire module uncited. Whether a per-root zero-citation figure should block promotion
   is an owner decision with a value threshold, per the stop decision. Before that, one cheap
   fix: the architecture_quality proof line may not cite a presence count as evidence of contract
   quality. That is a scoring guardrail in method-critic.md, one sentence.

## Per-finding classification

Legend: Sev = OCR severity. Verdict: **Y** should find, **P** partly, **N** out of scope,
**O** opportunistic only.

| # | File | Sev | Class | Verdict | Why missed | Validated outcome |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | IDs/BoardID | med | E | Y | COV | Rejected |
| 2 | DomainInvariantError | high | L | O | **JUDG** — decode arms 283-291 cited as domain_modeling proof | Applied |
| 3 | DomainInvariantError | med | L | O | JUDG (same file) | Applied |
| 4 | DomainInvariantError | med | J | Y | JUDG (hotspot triage looked at `make` only) | Rejected |
| 5 | DomainInvariantError | med | L | O | JUDG | Rejected |
| 6 | DomainInvariantError | low | L | O | JUDG | Rejected |
| 7 | IDs/PreflightCheckID | med | K | N | OOS (modelling taste) | Declined (class) |
| 8 | IDs/PreflightCheckID | low | J | Y | COV | Rejected |
| 9 | IDs/RosterID | med | E | Y | COV | Declined (class) |
| 10 | Ports/AppSettingsStore | med | A | Y | COV | Rejected |
| 11 | Ports/AppSettingsStore | med | E | Y | COV | Rejected |
| 12 | Ports/AppleMusicCatalogPort | med | L | O | OPP | Applied |
| 13 | Ports/AppleMusicCatalogPort | med | L | O | OPP | Applied |
| 14 | Ports/AppleMusicCatalogPort | med | J | Y | COV | Applied |
| 15 | Ports/AppleMusicCatalogPort | low | I | P | grep keys on markers only | Declined (class) |
| 16 | Ports/AppleMusicCatalogPort | med | L | O | OPP | Applied |
| 17 | Ports/AppleMusicCatalogPort | low | J | Y | COV | Applied |
| 18 | Ports/AppleMusicCatalogPort | low | K | N | OOS | Rejected |
| 19 | Ports/AppleMusicEntitlementPort | med | C | Y | COV | Rejected |
| 20 | Ports/AppleMusicEntitlementPort | med | A | Y | COV | Rejected |
| 21 | Ports/AppleMusicEntitlementPort | med | J | Y | COV | Applied |
| 22 | Ports/AppleMusicEntitlementPort | med | J | Y | COV | Rejected |
| 23 | Ports/AppleMusicEntitlementPort | med | A | Y | COV | Rejected |
| 24 | Ports/AppleMusicTransport | high | K | N | OOS — argument rests on a hypothetical future conformer | Rejected |
| 25 | Ports/AppleMusicTransport | med | D | Y | COV | Rejected |
| 26 | Ports/AppleMusicTransport | med | I | P | marker grep | Rejected |
| 27 | Ports/AppleMusicTransport | low | K | N | OOS | Declined (class) |
| 28 | Ports/AppleMusicTransport | med | C | Y | COV | Declined (class) |
| 29 | Ports/AppleMusicDuckVeiling | med | C | Y | COV | Rejected |
| 30 | Ports/AppleMusicDuckVeiling | med | F | Y | COV | Declined (class) |
| 31 | Ports/AppleMusicDuckVeiling | med | K | N | OOS | Rejected |
| 32 | Ports/AppleMusicDuckVeiling | low | K | N | OOS | Declined (class) |
| 33 | Ports/AudioFileImportPort | med | G | Y | COV | Declined (class) |
| 34 | Ports/AudioFileImportPort | med | F | Y | COV | Rejected |
| 35 | Ports/AudioFileImportPort | low | I | P | marker grep | Applied |
| 36 | Ports/AudioFileImportPort | med | A | Y | COV | Declined (class) |
| 37 | Ports/AudioFileMetadataPort | med | D | Y | COV | Owner-gated |
| 38 | Ports/AudioFileMetadataPort | low | H | Y | COV | Applied |
| 39 | Ports/AudioFileMetadataPort | med | A | Y | COV | Declined (class) |
| 40 | Ports/AudioFileMetadataPort | med | C | Y | COV | Declined (class) |
| 41 | Ports/AudioFileMetadataPort | med | H | Y | COV | Rejected |
| 42 | Ports/AudioPreviewPort | med | I | P | marker grep | Declined (class) |
| 43 | Ports/AudioPreviewPort | med | A | Y | COV | Rejected |
| 44 | Ports/AudioPreviewPort | high | B | Y | COV | Rejected |
| 45 | Ports/AudioPreviewPort | med | I | P | conformers disagree; no cross-conformer step | Declined (class) |
| 46 | Ports/AudioPreviewPort | med | I | P | marker grep | Declined (class) |
| 47 | Ports/AudioPreviewPort | med | D | Y | COV | Rejected |
| 48 | Ports/AudioPreviewPort | low | K | N | OOS | Declined (class) |
| 49 | Ports/AudioRecordingPort | med | G | Y | COV | Rejected |
| 50 | Ports/AudioRecordingPort | med | D | Y | COV | Owner-gated |
| 51 | Ports/AudioRecordingPort | med | B | Y | COV | Rejected |
| 52 | Ports/AudioRecordingPort | med | C | Y | COV | Declined (class) |
| 53 | Ports/AudioRecordingPort | high | A | Y | COV (verified) | Rejected |
| 54 | Ports/AudioRecordingPort | high | G | Y | COV — also canon *reservation after suspension* | Rejected |
| 55 | Ports/AudioSessionConfiguring | med | C | Y | COV | Rejected |
| 56 | Ports/AudioSessionConfiguring | med | F | Y | COV | Declined (class) |
| 57 | Ports/AudioSessionConfiguring | med | I | P | marker grep | Declined (class) |
| 58 | Ports/AudioSessionConfiguring | high | F | Y | COV | Rejected |
| 59 | Ports/BatterCursorRepository | low | K | N | OOS | Applied |
| 60 | Ports/BackupPort | med | D | Y | COV | Rejected |
| 61 | Ports/BackupPort | med | J | Y | COV | Rejected |
| 62 | Ports/BackupPort | low | K | N | OOS | Rejected |
| 63 | Ports/BackupPort | low | J | Y | COV | Rejected |
| 64 | Ports/BackupPort | low | K | N | OOS | Declined (class) |
| 65 | Ports/BatterCursorWriter | med | I | P | docs/qa not in grep roots | Owner |
| 66 | Ports/BatterCursorWriter | low | K | N | OOS | Rejected |
| 67 | Ports/AudioTransport | high | B | Y | COV | Rejected |
| 68 | Ports/AudioTransport | med | A | Y | COV | Rejected |
| 69 | Ports/AudioTransport | med | D | Y | COV | Rejected |
| 70 | Ports/AudioTransport | med | J | Y | COV | Owner-gated |
| 71 | Ports/AudioTransport | med | J | Y | COV (layering) | Rejected |
| 72 | Ports/AudioTransport | low | J | Y | COV | Declined (class) |
| 73 | Ports/DiagnosticsPort | med | G | Y | COV | Declined (class) |
| 74 | Ports/DiagnosticsPort | high | F | Y | COV | Rejected |
| 75 | Ports/DiagnosticsPort | med | D | Y | COV | Rejected |
| 76 | Ports/DiagnosticsPort | med | D | Y | COV | Owner-gated |
| 77 | Ports/DeviceVolumeRamping | med | D | Y | COV | Rejected |
| 78 | Ports/DeviceVolumeRamping | med | D | Y | COV | Declined (class) |
| 79 | Ports/DeviceVolumeRamping | high | A | Y | COV | Rejected |
| 80 | Ports/DeviceVolumeRamping | med | D | Y | COV | Declined (class) |
| 81 | Ports/DeviceVolumeRamping | low | L | O | OPP | Declined (class) |
| 82 | Ports/DeviceVolumeRamping | low | K | N | OOS | Rejected |
| 83 | Ports/EntitlementService | med | B | Y | COV | Rejected |
| 84 | Ports/EntitlementService | med | J | Y | COV | Applied |
| 85 | Ports/EntitlementService | high | A | Y | COV (verified) | Rejected |
| 86 | Ports/EntitlementService | high | A | Y | COV | Rejected |
| 87 | Ports/EntitlementService | low | K | N | OOS | Declined (class) |
| 88 | Ports/InterruptionObserver | high | D | Y | COV | Applied |
| 89 | Ports/InterruptionObserver | med | B | Y | COV | Declined (class) |
| 90 | Ports/InterruptionObserver | med | C | Y | COV | Rejected |
| 91 | Ports/GamePackageResults | med | E | Y | COV | Rejected |
| 92 | Ports/GamePackageResults | med | A | Y | COV | Declined (class) |
| 93 | Ports/GamePackageResults | med | A | Y | COV | Declined (class) |
| 94 | Ports/GamePackageResults | low | D | Y | COV | Owner-gated |
| 95 | Ports/GamePackageResults | low | D | Y | COV | Declined (class) |
| 96 | Ports/GamePackageResults | low | H | Y | COV | Declined (class) |
| 97 | Ports/GamePackageResults | low | K | N | OOS | Applied |
| 98 | Ports/LibrarySnapshotPort | high | A | Y | COV | Rejected |
| 99 | Ports/LibrarySnapshotPort | med | L | O | OPP | Rejected |
| 100 | Ports/LibrarySnapshotPort | med | J | Y | COV | Applied |
| 101 | Ports/LibrarySnapshotPort | med | I | P | marker grep | Applied |
| 102 | Ports/LibrarySnapshotPort | low | K | N | OOS | Rejected |
| 103 | Ports/LibrarySnapshotPort | low | K | N | OOS | Rejected |
| 104 | Ports/NetworkReachabilityProviding | med | B | Y | COV | Rejected |
| 105 | Ports/NetworkReachabilityProviding | low | I | P | marker grep | Rejected |
| 106 | Ports/LibraryPersistenceWriter | med | F | Y | COV | Declined (class) |
| 107 | Ports/LibraryPersistenceWriter | med | F | Y | COV | Applied |
| 108 | Ports/LibraryPersistenceWriter | low | K | N | OOS | Declined (class) |
| 109 | Ports/SessionLogWriter | low | C | Y | COV | Declined (class) |
| 110 | Ports/SessionLogWriter | low | K | N | OOS | Declined (class) |
| 111 | Ports/NowPlayingDisplaying | med | E | Y | COV | Rejected |
| 112 | Ports/NowPlayingDisplaying | med | J | Y | COV | Owner-gated |
| 113 | Ports/NowPlayingDisplaying | med | L | O | OPP | Rejected |
| 114 | Ports/NowPlayingDisplaying | med | D | Y | COV | Rejected |
| 115 | Ports/RouteObservationController | med | B | Y | COV | Declined (class) |
| 116 | Ports/RouteObservationController | med | C | Y | COV | Owner-gated |
| 117 | Ports/RouteObservationController | low | J | Y | COV | Rejected |
| 118 | Ports/PlayHistoryWriter | med | C | Y | COV | Rejected |
| 119 | Ports/PlayHistoryWriter | med | I | P | conformers disagree | Rejected |
| 120 | Ports/PlayHistoryWriter | med | F | Y | COV | Rejected |
| 121 | Ports/PlayHistoryWriter | med | F | Y | COV | Rejected |
| 122 | TransportEventRelay | high | B | Y | **JUDG** — accepted as data_flow residual "bus shape" (verified) | Rejected |
| 123 | TransportEventRelay | high | B | Y | **JUDG** (same pass) | Rejected |
| 124 | TransportEventRelay | med | F | Y | JUDG | Rejected |
| 125 | TransportEventRelay | med | H | Y | JUDG | Rejected |
| 126 | Values/AlbumArtVisibility | med | J | Y | COV | Rejected |
| 127 | Values/AlbumArtVisibility | low | J | Y | COV | Rejected |
| 128 | Values/AppleMusicCatalogResult | med | G | Y | COV | Declined (class) |
| 129 | Values/AppleMusicCatalogResult | med | L | O | OPP | Applied |
| 130 | Values/AppleMusicCatalogResult | med | D | Y | COV | Rejected |
| 131 | Values/AppleMusicCatalogResult | low | K | N | OOS | Rejected |
| 132 | Values/AppleMusicCatalogResult | low | K | N | OOS | Rejected |
| 133 | Values/AppSettings | med | E | Y | **JUDG** — both writers in AppReducer+Workflow.swift, read for dispatch count | Applied |
| 134 | Values/AppSettings | low | L | O | OPP | Declined (class) |
| 135 | Values/AppSettings | low | H | Y | COV | Rejected |
| 136 | Values/AppSettings | low | L | O | OPP | Rejected |
| 137 | Values/AppleMusicDuplicateDecision | med | J | Y | COV | Rejected |
| 138 | Values/AppleMusicDuplicateDecision | med | K | N | OOS | Declined (class) |
| 139 | Values/AppleMusicCueRef | low | K | N | OOS | Rejected |
| 140 | Values/AppleMusicCueRef | low | L | O | OPP | Rejected |
| 141 | Support/StateBroadcaster | med | C | Y | **JUDG** — named as loop-1 fix target | Rejected |
| 142 | Support/StateBroadcaster | med | H | Y | JUDG | Rejected |
## Caveats

- Classification is on OCR's claim text. A flash-model claim that a conformer "disagrees" may not
  survive a read; the four checked highs did.
- "Should find" means inside the declared lens, not that a single loop is expected to surface it.
  The loop emits one backlog item per loop by design. The gap that matters is that the run
  declared 9.5 on every dimension while the module carrying these was uncited.
- The OCR scan is still running; the second batch (Values/, Support/) will add rows. Two files
  were dropped by OCR's context-compression ceiling (InstanceID.swift, StringProtocol+TrimmedOrNil.swift).
