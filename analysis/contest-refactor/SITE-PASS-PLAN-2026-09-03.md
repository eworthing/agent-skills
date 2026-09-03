# Site pass — a per-file correctness pass for the Critic (plan, 2026-09-03, rev 5 — APPROVED at peer round 5, opencode qwen3.8-flash, review 3f920a3a8c7b)

**Goal.** contest-refactor finds, on its own, the class of real defects OCR finds, in files the
Critic already reads. OCR stays the benchmark, never a component.

**Evidence that opens this.** Two judges (`qwen3.8-flash`, `gpt-5.6-luna` — the second
contaminated by registry carry-over, assumed similar by owner decision) read all 10 files of
`BenchHypeSettingsFeature` and named **0 of 29** validated-real OCR sites, while their proof text
praised the exact sites (Authority Map "Single and clear" at the stale read-modify-write;
framework idioms 9.5 citing the `fileMover` whose failure arm is dropped; concurrency 10 citing the
refresh with no failure surface). The docket's earlier "legible 5/5" results were a Claude Critic on
planted fixtures; DD-01's adjudication asked for exactly this kind of real-corpus, at-rate evidence
before an obligation-gap change could reopen — and named the missing piece as a **quantifier**, not
a capability. Record: `OCR-SMALL4-SCOPE-AUDIT-2026-09-03.md`.

**Owner constraints (2026-09-03).** Loop-path token ceiling may rise when value is measured
(`feedback_token_headroom`). Sonnet/Codex budgets are exhausted this month; opencode flash is
available (~$0.34 per scoped dry-run). Commit to `main`; subagents never commit.

## Design

**Not a lens.** A lens is a smell list the Critic may or may not consult. This is a **step with a
ledger**: for every file in scope the Critic answers a fixed question set and records the answer
per file in `CURRENT_REVIEW.json.site_pass`, and a gate fails the emit when a scoped file has no
entry. Prose alone measured zero lift on a Claude Critic; a per-path artifact the validator checks
is the form the hotspot triage (G50) and coverage ledger already use, and the only form a flash
judge reliably follows.

**Scope marker (new, Step 0).** `discovery.scope`: the `--scope` directory as given, or `null`.
Recorded by `startup.md` sub-step 2 beside the filtered roots, carried forward verbatim by rule
#32 like the rest of `discovery`. Nothing in the artifact says "scoped" today; G40 deliberately
never re-compares roots to the repo, so a checker cannot infer it. G52 fires iff
`discovery.scope != null`. Unscoped runs: `site_pass` is `null` and the pass is a **prose-only**
obligation at v1 (every file the Critic cites or triages); the checker is written against the
scoped rule only.

**Ledger shape** (`site_pass`, required non-null when `discovery.scope` is non-null, from the
`site_pass` epoch):

```
"discovery": {
  …,
  "scope": "BenchHypeKit/Sources/BenchHypeSettingsFeature",        // string | null
  "site_pass_roster": {"paths": ["…/AppBuildInfo.swift", …],       // object | null (null iff scope null)
                       "digest": "<sha256 hex>"}
},
"site_pass": {                                   // sibling of discovery; per loop, never carried forward
  "files": [
    {"path": "BenchHypeKit/Sources/BenchHypeSettingsFeature/BackupSettingsView.swift",
     "reads": "full" | "partial:<line-ranges>",
     "questions": {
       "Q1": {"status": "clean"},
       "Q2": {"status": "finding", "finding_ids": ["F3"]},
       "Q3": {"status": "not_applicable", "reason": "no intent-dispatching control in file"},
       … "Q8": {…}                                              // all eight keys required
     }}
  ]
}
```

The roster is **script-emitted, never hand-built**: new `scripts/site_pass_roster.py . --scope
<dir> --json` reuses `coverage_ledger.py`'s enumerator and `_fs_filters` and prints
`{"paths": [...], "digest": "..."}` — repo-relative POSIX paths, sorted by byte order,
`\n`-joined, UTF-8, sha256 hex. Step 0 (main agent) runs it beside the hotspot scan and assigns the
decoded object unchanged to `discovery.site_pass_roster` (startup sub-step 7 doctrine: never
reconstruct field-by-field); preflight checks the persisted object equals a fresh emission, the
same way it checks the hotspot object. The roster is pinned in `discovery`, so G52 never depends
on the live tree at a later phase (the Tier-3 hook runs the full battery at
`postchallenge-precommit`, after Step 3 may have added or renamed in-scope files). On unscoped runs
`discovery.site_pass_roster` is `null` and the script exits non-zero without `--scope` (no no-scope
mode). Because rule #32 carries `discovery` forward on faithfulness alone and preflight runs only at
Step 0, the roster digest is also **bound into the candidate fingerprint** beside `source_roots`
(`candidate_fingerprint.py`), so a roster narrowed at loop 2+ can never ride a HALT_SUCCESS
candidate. The ledger itself is **per loop**: Step 6.5 runs every loop and `site_pass` is
re-emitted, not copied forward like `discovery`.

Gate **G52** (pre-emit, epoch `site_pass`, **report-only until W2 passes** — diagnostics, never an
Issue, with the promotion bar written in `_artifact_site_pass.py` per the G48 precedent):
artifact-internal only — `site_pass.files[].path` set equals `discovery.site_pass_roster.paths`
exactly (no missing, extra, or duplicate); every entry's `questions` key set equals {Q1…Q8};
`finding_ids` non-empty iff `status == "finding"`, every id present in `findings`; `reason`
non-empty iff `not_applicable`; `roster.digest` re-derives from `paths` with the encoding above.
 Whether the pinned roster matches the live enumeration is a Step-1 procedure obligation
measured by W2's grader, not a gate. Markdown mirror: `## Site pass` table, one row per file.
No citation is required on a `clean` row: theater is measured by the grader's recall, not by the
gate (peer-round-1 N6).

**Question set** (`references/site-pass.md`, Critic-only in the load matrix; each question names
its corpus provenance so a later reviewer can retire it on evidence):

| Q | Ask, per file | Corpus provenance (validated-real) |
| --- | --- | --- |
| Q1 State rendered | Every enum case / phase this file's producer constructs is matched by its consumer; a case or payload constructed and never matched is a finding | small4 50, 51, 52, 45, 47 |
| Q2 Failure reaches someone | Every `.failure` arm, `catch`, `try?`, and error-carrying case reaches the user, a log with rationale, or a compensating return the caller acts on | 42, 45, 79, 90, 95 |
| Q3 Gate parity | A control's enabled/disabled predicate equals the predicate the receiving reducer or service uses to accept the intent | 39/44, 6/12, 22 |
| Q4 One authority per read | Within one view, reads of the same concern use one source; draft-precedent beside canonical is a finding | 71, 72, 16, 32 |
| Q5 Sibling parity | When sibling sites share a shape and one differs (missing modifier, index-keyed beside ID-keyed, `.combine` beside `.contain`), name the odd one and the sibling that is right | 23/26, 61, 67, 34, 17/18, 2/9 |
| Q6 Copy tells the truth | User-facing copy, help entries and doc comments name symbols, shortcuts, gestures and navigation paths that exist in the command/gesture layer | 54–58, 60, 21, 43; domain tier-3 doc rows fixed in BenchHype `d0a3d1ed` (eight doc comments) |
| Q7 Construction invariants | Value inits and `validate*`/`make*` bound every numeric and collection field on both sides, NaN/inf included; every `Codable` path goes through the throwing init | domain class V (202, 204, 224, 262, 266); small4 0, 85, 87 |
| Q8 Runtime, not test-only | An invariant the docs call enforced is enforced on a production path, not only in a test target; `audit_dead_surface.py` `test_only` rows are leads | 80, 81, 83–86 |

A site may inform more than one question (45 appears under Q1 and Q2); the manifest's
`question` field is the primary attribution and uniqueness is on `fid` only.

**Do-not-flag**, co-located in the same file (the DD-13 form, ten signatures from the 30
rejections): hardening for infrastructure the repo does not have (localization, plist shapes);
stale index unreachable because the lookup is recomputed per render; wrapper or narrow-surface
refactors with no demonstrated defect; speculative future SDK cases; deliberate finish-before-cache
where the cache self-heals from the ledger; a remedy that contradicts the repo's own documented
invariant; a mechanism you cannot grep (name it or drop it); unmeasured performance; races no human
can produce; a state the system already republishes.

**Where it runs.** `method.md` gains **Step 6.5 — Site pass** between Step 6 (simplification,
which contains the leaf-module sweep) and Step 7 (hidden state machines), in the existing decimal
style of 1.5/1.6/1.7; the label "6b" is avoided because startup.md uses 6c and the resume matrix
uses row 6b. It runs before dimension scoring so its findings feed the Evidence Chain and severity
anchors like any other; G26 anchor-to-source and the "adds, must not displace" bar in W2 bound
inflation (peer-round-1 q3). `site-pass.md` cites `lens-apple.md` § Failure modes for Q2 and
§ Hidden State Machines for Q1 so a site is never emitted twice under two rules (q5).
Helper-friendly: one read-only helper per file cluster, handed the eight questions verbatim plus the
do-not-flag block; the Critic owns the ledger and the adopt-or-falsify of helper output.

## Waves

**W0 — Ground truth and grader (no LLM).**
- `evals/ocr-corpus/benchhype-settings-2026-09.json`: the 29 real sites and the 30 rejected sites
  from `scan-small4-validated.json`, path + line range + one-line claim + question id, at
  `909164fb`. Domain: extend the existing manifest with the 157 real / 126 rejected sites at
  `2b5247e9` as a `sites` array (detector targets unchanged).
- `scripts/grade_site_pass.py <CURRENT_REVIEW.json> <manifest> [--baseline <artifact>] [--json]`:
  a site is **hit** when any finding's `evidence` cites its path with a cited **range that
  intersects** the site's range; a single-line cite gets ± 5. Real-site hits are recall;
  rejected-site hits are restraint failures **except** those in the baseline exclusion set:
  `--baseline` grades the pre-change artifact and records which rejected sites its rubric findings
  already touch (known today: F-026's evidence `SettingsScreenContext.swift:10-26` intersects
  rejected site 65 at :14-15). Prints hit/miss per site with the finding id. Selftest with a
  hand-built artifact covering intersect, single-line ± 5, and the exclusion set. Exit 0 always.
  `--json` carries, per artifact: hits/misses with finding ids, the arm/rep label passed via
  `--label`, and `roster_gap` = manifest site paths ∉ `discovery.site_pass_roster.paths` (emitted as
  `null` when the artifact has no roster, i.e. every control-arm artifact), which is how a Critic
  that under-enumerates becomes visible before W3 at zero loop cost.
- Copy the baseline artifact (the archived flash loop from BenchHype's `REVIEW_HISTORY.json`) into
  `evals/ocr-corpus/baselines/benchhype-settings-flash-2026-09-03.json` so the exclusion set is
  reproducible from this repo alone.
- Grade the archived flash dry-run (`run-2026-09-03-b05b…` in `REVIEW_HISTORY.json`): expected
  0/29 real; the rejected-site hits it produces **are** the exclusion set, pre-registered here
  before any treat rep runs.
- `_ocr_corpus_selftest.py` extended to pin the site-manifest schema: `sites[]` with `fid`,
  `verdict` ∈ {real, rejected}, `path`, `line_start ≤ line_end`, `claim`, `question` ∈ {Q1…Q8,
  null}; `fid` unique per manifest.
- Done when: both manifests pass the selftest, grader selftest green, baseline graded with its
  exclusion set recorded in this plan.
- **W0 result (2026-09-03):** manifests landed (settings 29 real / 10 rejected; domain 157 / 126);
  `grade_site_pass.py` + selftest green; `_ocr_corpus_selftest.py` pins both `sites[]` shapes.
  Baseline (archived flash dry-run) grades **real 1/29 mechanical, rejected 1/10**: the one real
  hit is fid 45 (`BackupSettingsView.swift:122-123`) intersected by F-025's `statusMessage` range
  112-125 — same site, different defect, so the instrument counts it; by reading it is 0/29. The
  **exclusion set is [65]** (F-026 ↔ rejected site 65). The W2 bar (≥ 10/29) is measured with the
  same instrument, so the mechanical 1 is inside it, not subtracted.

**W1 — Site pass (prose + schema + gate).**
- `references/site-pass.md` (new, Critic-only). `method.md` Step 6.5. `scripts/site_pass_roster.py`
  + selftest; `startup.md` Step 0 runs it and preflight checks persisted-equals-fresh (`_preflight_selftest.py`
  case: a hand-edited roster fails the gate). `output-format-json.md`
  `site_pass` shape; `output-format-markdown.md` `## Site pass` section; `output-format-migrations.md`
  "adding a required field" row.
- `startup.md` sub-step 2 records `discovery.scope`; `output-format-json.md` documents it and
  `site_pass_roster` (object | null, null iff scope null); `_artifact_discovery.py` accepts both
  from the epoch; `candidate_fingerprint.py` binds `site_pass_roster.digest` beside `source_roots`
  (selftest case: a narrowed roster changes the fingerprint).
- `canon/validation-gates.toml` G52; `references/validation.md` checklist entry and
  `validation-sources.md` provenance line (validate-repo.py requires every canon gate to be
  referenced); `_artifact_site_pass.py` + `_artifact_site_pass_selftest.py`; `_ruleset_epoch.py`
  `SITE_PASS` epoch bound to the landing rev, prose-then-gate. **G52 stays report-only through
  W2** and is promoted to Issue only in W3 on a passed bar.
- `_token_budget_selftest.py` golden load-set gains `site-pass.md` on the Critic path. **Ceiling
  rule, one and consistent:** `token-budget.py --check` has no ceiling waiver, so W1 raises the
  apple and generic per-loop ceilings by the measured delta of `site-pass.md` plus Step 6.5, in
  the W1 commit, annotated `provisional — keyed to W2 disposition (SITE-PASS plan)`. The loop-path
  cost is real from W1 even before the lift is. The failed-bar revert commit (spec in W2's
  negative disposition, the single authority) lowers them to their pre-W1 values; W3's promotion
  re-annotates them with the measured lift. Budget guard is green at every commit.
- Fixtures (G48 pattern): one `evals/fixtures/` artifact with a valid `site_pass` (no diagnostic),
  one with a missing scoped file that asserts the **report-only diagnostic prints and no Issue**,
  one unscoped with `site_pass: null` (allowed), each registered in `_smoke_check.py`'s EXPECTED
  map and the fixtures README. W3's promotion commit flips the second fixture's expectation to a
  real G52 Issue.
- Done when: validate-repo, validate-fixtures, all `_*_selftest.py`, ruff, budget guard green;
  writing-for-agents pass on the new prose (context pointer in the load matrix, no-op hunt,
  co-location of do-not-flag with the questions).

**W1 result (2026-09-03):** landed as two commits, prose-then-gate. **W1a `1b4ddd5`:**
`references/site-pass.md`, `method.md` Step 6.5, `startup.md` (`discovery.scope`, roster emission
at 6c, seed list, preflight flags), `scripts/site_pass_roster.py` + selftest, `preflight.py`
`--roster-json` + `_roster_failures` (fresh-emission equality; null required when unscoped) with
six new selftest cases, `candidate_fingerprint.py` binds `site_pass_roster.digest` only when
present (historical fingerprints unchanged; new `_candidate_fingerprint_selftest.py`), schema rows
in `output-format-json.md` / `-markdown.md` / `-migrations.md`, load matrix + `token-budget.py`
step-1 table + golden set. Measured delta **+1,978 tok** on both lens paths; ceilings raised
**provisionally** 87,800 → 88,700 (apple, now 88,348) and 83,700 → 84,600 (generic, now 84,518,
82 below — soft warning, not a failure), annotated in `CEILINGS` and keyed to the W2
disposition. **W1b `fccd950`:** `SITE_PASS` epoch bound to `1b4ddd5`, `_artifact_site_pass.py`
(report-only, promotion bar in the docstring) + `_g52_selftest.py` (13 diagnostics, never an
Issue, pre-epoch silent), wired in `validate-artifact.py`, canon G52 + `validation.md` +
`validation-sources.md`, canon golden regenerated. Fixtures live in `evals/fixtures/` (the
`fixture.toml` corpus that carries G39/G40/G41 fixtures), **not** `evals/artifact-smoke/` as the
peer review assumed — that corpus is the eleven-file minimal set with its own `_smoke_check`
map; recorded as a deviation. The three fixtures are built from the real flash dry-run artifact
because no committed fixture at a modern epoch passes strict once `skill_rev` is bumped
(hotspot_scan, run_id, System Flag and history all become owed). Verification: validate-repo,
105 fixtures, 90/90 selftests, ruff 0.15.6, budget guard OK.

**W2 — Measure (opencode flash; nominal 6 reps + 1 generalization ≈ $2.4, worst case with one full both-arm re-run ≈ $4.5).**
- Both arms run on the same target tree, `/Users/Shared/git/BenchHype-blind` (`blind-judge` @
  `909164fb`), with the same reset between reps (`git checkout -- . && git clean -fd` restricted
  to the six bookkeeping files) — never the main checkout, whose registry would contaminate the
  judge (`--reset` does not blind). **3 treat reps, 3 control reps.** Control skill rev = the last
  `main` commit before W1's first prose commit, checked out in an agent-skills worktree with the
  `~/.config/opencode/skills/contest-refactor` symlink swapped for the rep and restored after;
  no other opencode session may run during a control rep (the swap is global), recorded in the
  rep log.
- Trial validity per `canon/trial-validity.toml`, pre-registered with replacement semantics
  (at n=3 one unreplaced invalid rep is 0.33 > 0.20 and voids the arm by the strict-greater rule,
  so the semantics matter): the void caps (0.20 per arm, 0.10 between arms) are computed over
  **attempts**. At n=3 the honest consequence is: **any invalid attempt in either arm voids the
  run** — one invalid plus its replacement is 1/4 = 0.25 > 0.20 on that arm's own cap, so neither
  replacement nor symmetric failure rescues it. There is therefore no in-run replacement. Void
  disposition: one full re-run of **both** arms (keeps the arms symmetric and the pre-registration
  simple), classification recorded per attempt; if the re-run is void too, W2 is deferred, W1 stays
  report-only with its provisional ceilings dated, and the DD-18 row records "void, not measured".
  Canon is used unchanged; an owner may instead adjudicate n=5 per arm (survives one invalid per
  arm on the rate cap but not a one-sided one on the asymmetry cap) as a recorded divergence. Every classification is recorded per attempt.
- **Ship bar:** treat real-site hits ≥ 10/29 on at least 2 of 3 reps; rejected-site hits outside
  the W0 exclusion set = 0 on every treat rep; the four rubric findings F-025…F-028 (or same-site
  equivalents) present on ≥ 2 of 3 scored treat reps — the pass adds, it must not displace the rubric.
- **Negative disposition, decided now — the one authoritative spec of the revert commit.** If
  the bar is missed, one commit does all of the following: Step 6.5 in `method.md` is reduced to a
  single pointer sentence ("a per-file site pass is described in `references/site-pass.md`;
  measured 2026-09 below its bar, advisory only"); `site-pass.md` stays on disk but is **removed
  from the Critic's per-loop load matrix** and from the `_token_budget_selftest.py` golden set;
  the G52 canon entry, `_artifact_site_pass.py` and its selftest, the three fixtures (and their
  `_smoke_check.py` EXPECTED + README rows), the
  `site_pass` / `site_pass_roster` schema rows, `site_pass_roster.py`, the fingerprint binding,
  and the `SITE_PASS` epoch are removed; `discovery.scope` stays (it is useful on its own); the
  ceilings are lowered to their **pre-W1 values** (the pointer sentence's cost is inside the
  pre-W1 soft margin). Budget guard green in that commit. The DD-18 row records the per-rep
  numbers as the result, and the DD-01 row is reconfirmed parked with this measurement cited.
  Nothing from W1 ships as required on a missed bar.
- Generalization (report, not gate): 1 scoped dry-run on `BenchHypeKit/Sources/BenchHypeDomain/Values`
  at `2b5247e9` (blind worktree), graded against the Domain sites.
- Done when: the bar table is in the run-log with per-site hit/miss for every rep.

**W3 — Promotion and records (only on a passed bar; otherwise the negative disposition above).**
- Promote G52 from report-only to Issue at the recorded epoch rev (promotion bar in
  `_artifact_site_pass.py`), flip the diagnostic fixture to an Issue expectation, and re-annotate
  the ceilings from provisional to measured, citing the W2 table in the commit.
- Run-log section; detection-domains **DD-18 Site pass** row with the bar table, and one sentence
  on the DD-01 row: its reopen condition (quantifier, at-rate, real corpus) was met here and rides
  the promotion; `startup.md` `--reset` description gains "keeps the registry and history —
  a fresh judge needs a first-install tree (worktree or `--purge`)"; memory.
- Plan outcome block here.

## Decision points (owner)

1. **Unscoped runs at v1:** resolved in the design as `null` + prose-only obligation, gated by
   `discovery.scope`; required from the first whole-repo run that ships the coverage floor
   (separate plan). Confirm or override.
2. **Helper fan-out:** one helper per file cluster costs roughly a Critic's worth of tokens per
   cluster. Not part of W2. If the single-Critic arm misses the bar, the negative disposition
   executes in full; a helper-per-cluster variant would be a **new plan** with its own
   pre-registered bar, never a stay that keeps W1's provisional ceilings alive.
3. **Bar level:** 10/29 is a floor chosen so a real lift is unmistakable against 0/29; the
   ceiling OCR reached with a validation pass was 29/29 by construction. Raise the bar after the
   first pass ships, not before.

## Peer-review questions (round 5)

Round-4 B1 accepted as stated: under attempts-based caps at n=3 any invalid attempt voids the run;
the plan now says so and re-runs both arms. No open questions.

## Peer review record

Reviewer: opencode `opencode-go/qwen3.8-flash`, effort provider-default (medium), five rounds,
session-resumed each round. Round verdicts: REVISE (6 blocking), REVISE (5), REVISE (1),
REVISE (1), **APPROVED** (3 non-blocking, applied). Every blocking claim was verified against source
before revision; none was wrong. Notable: the reviewer caught the `--reset`-blindness premise,
the missing scope marker, the budget guard's lack of a ceiling waiver, and the void arithmetic at
n=3 under attempts-based caps.
