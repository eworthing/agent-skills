# Site pass — a per-file correctness pass for the Critic (plan, 2026-09-03, rev 1)

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

**Ledger shape** (`site_pass`, required non-null on scoped runs from the `site_pass` epoch;
`null` allowed on unscoped runs at v1):

```
"site_pass": [
  {"path": "BenchHypeKit/Sources/BenchHypeSettingsFeature/BackupSettingsView.swift",
   "findings": ["F3"],                       // finding ids this file's pass produced
   "clean": ["Q1","Q2","Q4","Q5","Q6","Q7","Q8"],
   "not_applicable": ["Q3"],                 // with reason in Builder Notes
   "reads": "full" | "partial:<line-ranges>"}
]
```

Each question id appears in exactly one of `findings`-backed / `clean` / `not_applicable`; a
question whose finding ids are empty may not be listed under `findings`. Gate **G52** (pre-emit,
epoch `site_pass`): on a scoped run, the `path` set equals the enumerated first-party source files
under `discovery.source_roots` (same filter as `coverage_ledger.py`); every entry has all eight
question ids partitioned; every finding id referenced exists in `findings`. Markdown mirror:
`## Site pass` table, one row per file.

**Question set** (`references/site-pass.md`, Critic-only in the load matrix; each question names
its corpus provenance so a later reviewer can retire it on evidence):

| Q | Ask, per file | Corpus provenance (validated-real) |
| --- | --- | --- |
| Q1 State rendered | Every enum case / phase this file's producer constructs is matched by its consumer; a case or payload constructed and never matched is a finding | small4 50, 51, 52, 45, 47 |
| Q2 Failure reaches someone | Every `.failure` arm, `catch`, `try?`, and error-carrying case reaches the user, a log with rationale, or a compensating return the caller acts on | 42, 45, 79, 90, 95 |
| Q3 Gate parity | A control's enabled/disabled predicate equals the predicate the receiving reducer or service uses to accept the intent | 39/44, 6/12, 22 |
| Q4 One authority per read | Within one view, reads of the same concern use one source; draft-precedent beside canonical is a finding | 71, 72, 16, 32 |
| Q5 Sibling parity | When sibling sites share a shape and one differs (missing modifier, index-keyed beside ID-keyed, `.combine` beside `.contain`), name the odd one and the sibling that is right | 23/26, 61, 67, 34, 17/18, 2/9 |
| Q6 Copy tells the truth | User-facing copy, help entries and doc comments name symbols, shortcuts, gestures and navigation paths that exist in the command/gesture layer | 54–58, 60, 21, 43; domain doc rows |
| Q7 Construction invariants | Value inits and `validate*`/`make*` bound every numeric and collection field on both sides, NaN/inf included; every `Codable` path goes through the throwing init | domain class V (202, 204, 224, 262, 266); small4 0, 85, 87 |
| Q8 Runtime, not test-only | An invariant the docs call enforced is enforced on a production path, not only in a test target; `audit_dead_surface.py` `test_only` rows are leads | 80, 81, 83–86 |

**Do-not-flag**, co-located in the same file (the DD-13 form, ten signatures from the 30
rejections): hardening for infrastructure the repo does not have (localization, plist shapes);
stale index unreachable because the lookup is recomputed per render; wrapper or narrow-surface
refactors with no demonstrated defect; speculative future SDK cases; deliberate finish-before-cache
where the cache self-heals from the ledger; a remedy that contradicts the repo's own documented
invariant; a mechanism you cannot grep (name it or drop it); unmeasured performance; races no human
can produce; a state the system already republishes.

**Where it runs.** `method.md` Step 1 gains sub-step 6b **Site pass (mandatory on scoped runs;
on unscoped runs, every file the Critic cites or triages)**, after the simplification audit and
before the leaf-module sweep, so its findings feed the same Evidence Chain and severity anchors.
Helper-friendly: one read-only helper per file cluster, handed the eight questions verbatim plus the
do-not-flag block; the Critic owns the ledger and the adopt-or-falsify of helper output.

## Waves

**W0 — Ground truth and grader (no LLM).**
- `evals/ocr-corpus/benchhype-settings-2026-09.json`: the 29 real sites and the 30 rejected sites
  from `scan-small4-validated.json`, path + line range + one-line claim + question id, at
  `909164fb`. Domain: extend the existing manifest with the 157 real / 126 rejected sites at
  `2b5247e9` as a `sites` array (detector targets unchanged).
- `scripts/grade_site_pass.py <CURRENT_REVIEW.json> <manifest> [--json]`: a real site is **hit**
  when any finding's `evidence` cites its path with a line inside the range ± 5, or the file's
  `site_pass` entry lists a finding whose `primary_file` is the path and whose evidence overlaps;
  **restraint failure** when a rejected site is hit. Prints hit/miss per site with the finding id.
  Selftest with a hand-built artifact. Exit 0 always; numbers are the output.
- Grade the archived flash dry-run (`run-2026-09-03-b05b…` in `REVIEW_HISTORY.json`): expected
  0/29, 0/30 — the mechanical baseline.
- Done when: both manifests validate, selftest green, baseline graded and recorded.

**W1 — Site pass (prose + schema + gate).**
- `references/site-pass.md` (new, Critic-only). `method.md` sub-step 6b. `output-format-json.md`
  `site_pass` shape; `output-format-markdown.md` `## Site pass` section; `output-format-migrations.md`
  "adding a required field" row.
- `canon/validation-gates.toml` G52; `_artifact_site_pass.py` + `_artifact_site_pass_selftest.py`;
  `_ruleset_epoch.py` `SITE_PASS` epoch bound to the landing rev, prose-then-gate; G52 report-only
  until the epoch rev is known, promoted in the same commit that records it.
- `token-budget.py`: raise the apple and generic per-loop ceilings by the measured delta of the
  new file plus sub-step, in the same commit, citing this plan.
- Fixtures: one `evals/fixtures/` artifact with a valid `site_pass`, one with a missing scoped file
  (G52 Issue), one unscoped with `site_pass: null` (allowed).
- Done when: validate-repo, validate-fixtures, all `_*_selftest.py`, ruff, budget guard green;
  writing-for-agents pass on the new prose (context pointer in the load matrix, no-op hunt,
  co-location of do-not-flag with the questions).

**W2 — Measure (opencode flash, ~$3).**
- Treat: 3 scoped dry-runs on `/Users/Shared/git/BenchHype-blind` (`blind-judge` @ `909164fb`),
  bookkeeping reset between reps (`git checkout -- . && git clean -fd` on the six files). Control:
  the archived flash run plus 2 reps at the pre-W1 skill rev (agent-skills worktree at `7efa0ab`,
  symlink swap for the rep).
- **Ship bar:** treat hits ≥ 10/29 on at least 2 of 3 reps; rejected-site hits = 0 on every rep;
  the four rubric findings F-025…F-028 still emitted (or same-site equivalents) on ≥ 2 reps — the
  pass adds, it must not displace the rubric.
- Generalization (report, not gate): 1 scoped dry-run on `BenchHypeKit/Sources/BenchHypeDomain/Values`
  at `2b5247e9` (blind worktree), graded against the Domain sites.
- Done when: the bar table is in the run-log with per-site hit/miss for every rep.

**W3 — Records.**
- Run-log section; detection-domains **DD-18 Site pass** row with the bar table and the DD-01
  reopen rationale; `startup.md` `--reset` description gains "keeps the registry and history —
  a fresh judge needs a first-install tree (worktree or `--purge`)"; memory.
- Plan outcome block here.

## Decision points (owner)

1. **Unscoped runs at v1:** `site_pass` optional (`null`) or required for every cited/triaged
   file? Recommendation: optional at v1, required from the first whole-repo run that ships the
   coverage floor (separate plan).
2. **Helper fan-out:** one helper per file cluster costs roughly a Critic's worth of tokens per
   cluster; owner has lifted the ceiling, so recommendation is helper-per-cluster on scoped runs
   only, measured in W2 as its own arm if the single-Critic arm misses the bar.
3. **Bar level:** 10/29 is a floor chosen so a real lift is unmistakable against 0/29; the
   ceiling OCR reached with a validation pass was 29/29 by construction. Raise the bar after the
   first pass ships, not before.

## Peer-review questions

1. Is a completeness gate on the ledger gameable into checkbox theater ("clean" on every row)?
   The grader measures recall independently of the ledger, so theater fails W2, not G52 — is that
   separation enough, or should G52 also require a citation per `clean` entry?
2. Q5 (sibling parity) is the least crisp question and the largest cluster. Is "name the sibling
   that is right" a sufficient precision anchor?
3. Should the pass run before dimension scoring so its findings can move scores, or after so it
   cannot inflate the rubric's severity calibration?
4. Is line ± 5 the right hit tolerance for the grader, given OCR's ranges are 1–10 lines?
5. Does anything here duplicate `lens-apple.md` § Failure modes (Q2) or § Hidden State Machines
   (Q1) enough to demand consolidation rather than a new file?
