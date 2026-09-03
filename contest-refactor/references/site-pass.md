# Site pass — per-file correctness questions (Step 6.5, Critic only)

Eight questions asked of **every file in scope**, answered per file in `site_pass` (schema in
[output-format-json.md](output-format-json.md)). Provenance: the 2026-09 OCR corpora
(`evals/ocr-corpus/`), where two full-read judges answered the rubric's questions and named 0 of 29
validated bugs. Each question names its corpus sites so a later measurement can retire it.

## Procedure

1. Roster = `discovery.site_pass_roster.paths` (script-emitted at Step 0; never re-enumerate).
2. For each path, read the file — `reads: "full"`, or `"partial:<ranges>"` with the ranges named —
   and answer Q1–Q8. Every answer is one of `clean`, `finding` (with the finding ids this file's
   answer produced), or `not_applicable` (with a one-clause reason: the shape does not occur in
   this file). A finding still goes through the Evidence Chain and Severity Anchors like any other;
   the ledger records it, it does not create it.
3. Helper-friendly: one read-only helper per file cluster, handed this file verbatim; the Critic
   owns the ledger and adopts or falsifies every helper row.

## Questions

| Q | Ask, per file | Telltale | Corpus sites |
| --- | --- | --- | --- |
| **Q1 State rendered** | Every enum case or phase a producer in this file constructs — or a consumer here receives — is matched somewhere by its consumer, payload included. | `= .failed(` in a reducer, no `case .failed` in any view; a `nil` that disables a control with no text saying why | small4 50, 51, 52, 45, 46, 47, 68 |
| **Q2 Failure reaches someone** | Every `.failure` arm, `catch`, `try?`, and error-carrying case reaches the user, a log with rationale, or a compensating return the caller acts on (the [lens-apple.md § Failure modes](lens-apple.md#failure-modes--observability-apple-flavored) silent-swallow rule, applied per site). | `if case .success = result` with no `.failure`; an error field never read | small4 42, 45, 47, 79, 90, 95 |
| **Q3 Gate parity** | A control's enabled/disabled predicate equals the predicate the receiving reducer or service uses to accept the intent. | `.disabled(x.isRunning)` where the reducer checks `acceptsPhaseChange`; one surface of several missing the guard | small4 39, 44, 6, 12, 22 |
| **Q4 One authority per read** | Within one view, reads of the same concern use one source; a draft-precedent binding beside a canonical read, or a read-modify-write on a render-time snapshot, is a finding. | `state.appSettings.x` next to `settingBinding(\.x)`; `var draft = state.draft; draft.y = …; dispatch(draft)` | small4 71, 72, 63, 16, 32 |
| **Q5 Sibling parity** | When sibling sites share a shape and one differs — a missing modifier, index-keyed beside ID-keyed, `.combine` beside `.contain`, a fallback the sibling branch has — name the odd one **and the sibling that is right**. | grep the modifier or helper across the siblings; one hit fewer than siblings | small4 23, 26, 61, 67, 34, 17, 18, 2, 9, 48, 69 |
| **Q6 Copy tells the truth** | User-facing copy, help entries, labels and doc comments name symbols, shortcuts, gestures and navigation paths that exist in the command/gesture layer; an ellipsis promises a dialog that opens. | grep the named shortcut, gesture or feature; zero hits outside the copy | small4 54–58, 60, 21, 43, 53; domain tier-3 doc rows (BenchHype `d0a3d1ed`) |
| **Q7 Construction invariants** | Value inits and `validate*`/`make*` bound every numeric and collection field on both sides, NaN/inf included; every `Codable` path goes through the throwing init; an `Int(x)` has a ceiling. | `guard x >= 0` with no upper bound; `if x < 0 { throw }` (admits NaN); `init(from:)` bypassing the validating init | domain 202, 204, 224, 262, 266; small4 0, 85, 87 |
| **Q8 Runtime, not test-only** | An invariant the docs call enforced is enforced on a production path, not only under the test target. | a gate type with zero production callers (`audit_dead_surface.py` `test_only` rows are leads); a filter keyed on one field while the doc names two | small4 80, 81, 83–86 |

Q1 overlaps [lens-apple.md § Hidden State Machines](lens-apple.md#hidden-state-machines-apple-flavored)
and Q2 its Failure-modes audit: emit a site once, under the question that names the defect; the lens
sections keep their dimension-level scope.

## Do not flag (measured signatures from the same corpora's 30 rejections)

hardening for infrastructure the repo does not have (localization catalogs, plist shapes the
build never emits) · a stale index that cannot be stale because the lookup is recomputed every
render · a wrapper or narrower interface with no demonstrated defect · a future SDK case or state
no current caller can produce · finish-before-cache where the cache self-heals from the ledger ·
a remedy that contradicts the repo's own documented invariant (raise the doc conflict instead) ·
a mechanism you cannot grep — name the symbol or drop the claim · unmeasured performance ·
a race no human can produce in the UI · a state the system already republishes on its own.
