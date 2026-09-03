# Site pass — a per-file correctness pass for the Critic (plan, 2026-09-03, rev 2 — after peer round 1, opencode qwen3.8-flash)

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
"site_pass": {
  "roster": {"paths": ["…/AppBuildInfo.swift", "…/BackupSettingsView.swift", …],
             "digest": "<sha256 of the sorted path list>"},     // pinned at Step-1 emit
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

The roster is the Critic's own enumeration of first-party source files under
`discovery.source_roots` with `coverage_ledger.py`'s filter, **pinned into the artifact** the way the
coverage ledger pins its denominator, so the gate never depends on the live tree at a later phase
(the Tier-3 hook runs the full battery at `postchallenge-precommit`, after Step 3 may have added or
renamed in-scope files).

Gate **G52** (pre-emit, epoch `site_pass`, **report-only until W2 passes**): artifact-internal
only — `files[].path` set equals `roster.paths` exactly (no missing, extra, or duplicate); every
entry's `questions` key set equals {Q1…Q8}; `finding_ids` non-empty iff `status == "finding"`,
every id present in `findings`; `reason` non-empty iff `not_applicable`; `roster.digest` matches
its list. Whether the pinned roster matches the live enumeration is a Step-1 procedure obligation
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
- Grade the archived flash dry-run (`run-2026-09-03-b05b…` in `REVIEW_HISTORY.json`): expected
  0/29 real; the rejected-site hits it produces **are** the exclusion set, pre-registered here
  before any treat rep runs.
- `_ocr_corpus_selftest.py` extended to pin the site-manifest schema: `sites[]` with `fid`,
  `verdict` ∈ {real, rejected}, `path`, `line_start ≤ line_end`, `claim`, `question` ∈ {Q1…Q8,
  null}; `fid` unique per manifest.
- Done when: both manifests pass the selftest, grader selftest green, baseline graded with its
  exclusion set recorded in this plan.

**W1 — Site pass (prose + schema + gate).**
- `references/site-pass.md` (new, Critic-only). `method.md` sub-step 6b. `output-format-json.md`
  `site_pass` shape; `output-format-markdown.md` `## Site pass` section; `output-format-migrations.md`
  "adding a required field" row.
- `startup.md` sub-step 2 records `discovery.scope`; `output-format-json.md` documents it;
  `_artifact_discovery.py` accepts it (string | null) from the epoch.
- `canon/validation-gates.toml` G52; `references/validation.md` checklist entry and
  `validation-sources.md` provenance line (validate-repo.py requires every canon gate to be
  referenced); `_artifact_site_pass.py` + `_artifact_site_pass_selftest.py`; `_ruleset_epoch.py`
  `SITE_PASS` epoch bound to the landing rev, prose-then-gate. **G52 stays report-only through
  W2** and is promoted to Issue only in W3 on a passed bar.
- `_token_budget_selftest.py` golden load-set gains `site-pass.md` on the Critic path. The per-loop
  ceilings are **not** raised in W1: the new file may exceed them, and `token-budget.py --check`
  will fail; W1's done-when tolerates exactly that one failure, annotated. The raise lands in W3
  with the measured lift beside it (owner constraint, line 16).
- Fixtures: one `evals/fixtures/` artifact with a valid `site_pass`, one with a missing scoped file
  (G52 Issue), one unscoped with `site_pass: null` (allowed).
- Done when: validate-repo, validate-fixtures, all `_*_selftest.py`, ruff, budget guard green;
  writing-for-agents pass on the new prose (context pointer in the load matrix, no-op hunt,
  co-location of do-not-flag with the questions).

**W2 — Measure (opencode flash, ~$3).**
- Both arms run on the same target tree, `/Users/Shared/git/BenchHype-blind` (`blind-judge` @
  `909164fb`), with the same reset between reps (`git checkout -- . && git clean -fd` restricted
  to the six bookkeeping files) — never the main checkout, whose registry would contaminate the
  judge (`--reset` does not blind). **3 treat reps, 3 control reps.** Control skill rev = the last
  `main` commit before W1's first prose commit, checked out in an agent-skills worktree with the
  `~/.config/opencode/skills/contest-refactor` symlink swapped for the rep and restored after.
- Trial validity per `canon/trial-validity.toml`, pre-registered: a rep is invalid on
  `rate_limited`, `auth_failure`, `infra_timeout`, or `artifact_lost`; invalid reps are re-run;
  the run is void if either arm exceeds `max_invalid_rate_per_arm` (0.20) or the arms differ by
  more than `max_between_arm_asymmetry` (0.10). Classification recorded per rep.
- **Ship bar:** treat real-site hits ≥ 10/29 on at least 2 of 3 reps; rejected-site hits outside
  the W0 exclusion set = 0 on every treat rep; the four rubric findings F-025…F-028 (or same-site
  equivalents) present on ≥ 2 treat reps — the pass adds, it must not displace the rubric.
- **Negative disposition, decided now:** if the bar is missed, Step 6.5 is demoted to an
  advisory sentence pointing at `site-pass.md` (no ledger, no gate), G52 and the `site_pass`
  epoch are removed before promotion, ceilings stay where they are, and the DD-18 row records the
  per-rep numbers as the result. Nothing from W1 ships as required on a missed bar.
- Generalization (report, not gate): 1 scoped dry-run on `BenchHypeKit/Sources/BenchHypeDomain/Values`
  at `2b5247e9` (blind worktree), graded against the Domain sites.
- Done when: the bar table is in the run-log with per-site hit/miss for every rep.

**W3 — Promotion and records (only on a passed bar; otherwise the negative disposition above).**
- Promote G52 from report-only to Issue at the recorded epoch rev; raise the apple and generic
  ceilings in `token-budget.py` by the measured delta, citing the W2 table in the commit.
- Run-log section; detection-domains **DD-18 Site pass** row with the bar table and the DD-01
  reopen rationale; `startup.md` `--reset` description gains "keeps the registry and history —
  a fresh judge needs a first-install tree (worktree or `--purge`)"; memory.
- Plan outcome block here.

## Decision points (owner)

1. **Unscoped runs at v1:** resolved in the design as `null` + prose-only obligation, gated by
   `discovery.scope`; required from the first whole-repo run that ships the coverage floor
   (separate plan). Confirm or override.
2. **Helper fan-out:** one helper per file cluster costs roughly a Critic's worth of tokens per
   cluster; owner has lifted the ceiling, so recommendation is helper-per-cluster on scoped runs
   only, measured in W2 as its own arm if the single-Critic arm misses the bar.
3. **Bar level:** 10/29 is a floor chosen so a real lift is unmistakable against 0/29; the
   ceiling OCR reached with a validation pass was 29/29 by construction. Raise the bar after the
   first pass ships, not before.

## Peer-review questions (round 2)

1. Q5 (sibling parity) is the least crisp question and the largest cluster. Is "name the sibling
   that is right" a sufficient precision anchor, or should Q5 be split by shape (modifier parity,
   index-vs-ID, accessibility container)?
2. Is pinning the roster into the artifact (B4 fix) enough, or does a Step-1 report-only check
   comparing the pinned roster to the live enumeration also need a home so a Critic that under-
   enumerates is visible before W2?
3. With G52 report-only through W2, is there any path by which W1's prose alone changes loop
   behaviour on a production run before the bar is met? If so, should W1 land behind a flag?
