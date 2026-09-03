# Plan: close the contest-refactor gaps the validated OCR corpus exposed

Date: 2026-09-03. Revision 5, **APPROVED** by peer review round 5 (codex gpt-5.6-sol, effort high;
rounds 1–4 REVISE, 22 blocking findings resolved). Three non-blocking clarifications from round 5
folded in below. Status: awaiting owner go, nothing built.
Inputs: `analysis/contest-refactor/OCR-VS-CONTEST-REFACTOR-BENCHHYPE-2026-09-02.md` (rev 2),
`BenchHype/.artifacts/ocr/scan-domain-validated.json`, BenchHype fix commits `5ef7a09c` … `80499e9c`.

## Goal

Make contest-refactor reach the finding classes the validated corpus proved real and in-scope,
without adding judgment prose (2026-08-26 stop decision) and without turning the loop into a
per-file scanner (24.1M tokens for 89 files is OCR's shape, not the loop's).

## Ground truth

The pre-fix BenchHype revision is `2b5247e9`, which is contest-refactor run #9's own loop-2
HALT_SUCCESS commit. Every fix below was applied on top of the tree the loop certified at 9.5 on
all eight dimensions. A detector run at `2b5247e9` must surface the fixed sites; run at
`80499e9c` it must go quiet on them.

## In scope: three gap classes, all validated

| Class | Validated evidence | Why it belongs to the loop | Mechanism |
| --- | --- | --- | --- |
| **V — value-type invariant gaps** | 12 applied fixes with a mechanical shape. **Ten float-or-type targets**: one-sided guards on `Double`/`TimeInterval` (202, 226, 267), NaN through `min`/`max` (204), wall-clock delta with no floor (189), non-finite via `Codable` bypassing a throwing init (205, 266), duplicate IDs stored in aggregates (224, 227), unbounded `Int(Double)` (262). **Two `Int` targets** excluded by decision 2: one-sided `orderIndex` guards on `Int` (138, 242) | `domain_modeling` is a scored dimension; run #9 gave it 9.5 with one residual. Leaf value inits are low-churn and low cognitive density, so churn top-3 and the hotspot scanner never rank them | Fourth hotspot queue, `invariant`, as Step-0 candidate evidence |
| **Z — zero-reference surface** | 17 deletions applied; 10 are mechanically findable: never-constructed enum cases (15, 195, 221, 234), unused protocol requirements (82, 97), unread accessors and config (166, 251, 272, 282) | `simplicity` is scored; the loop already does this sweep by hand (F-024) but only for `public` decls with zero cross-module callers | New dead-surface aid covering cases, requirements and intra-module decls |
| **W — dual writer across files** | One applied fix (128): a reducer arm and a settings draft both write `duckFallbackRoutes`; both writers sit in a churn-top-20 file the loop read | Step 2 Authority Map is state-slice grained; a field-level second writer inside one slice is invisible | Parked as DD-17, one data point, no build |

Dropping the two `Int` targets is a deliberate recall trade: the `Int` one-sided guard is the
noisiest rule, and the validated scope keeps them on record for a later `Int` variant with its own
precision corpus.

Out of scope, on the validation's own evidence: single-consumer `AsyncStream` complaints and
`Sendable`-is-not-serialization complaints (named false-positive signatures), "contract lives in
prose" (56 declined as a class under Rule 10), speculative future-conformer arguments, and the 25
owner-gated Rule 3/4 remodels (owner decisions, not detection gaps; `audit-enum-interpretation.sh`
already exists). Also out of scope: any new scoring or judgment sentence in the Critic prose.

## Constraints carried from the repo

- Detectors emit **candidate evidence only** (`promotion_allowed: false`); Method re-derives.
  Same precedent as DD-06/DD-07 and the hotspot scanner.
- **RED first.** Every detector rule gets a failing fixture before code. Selection floors are
  tuned on the corpus, then frozen.
- **The owner sets value thresholds** before any live measurement run (stop decision). The
  thresholds below are proposals adopted from review rounds 1–2.
- Every wave sweeps **all** `scripts/_*_selftest.py` (plain `python3`, no `timeout` on macOS),
  plus `validate-repo.py`, `validate-fixtures.py contest-refactor/evals/fixtures`,
  `ruff==0.15.6`, token budget, and `eval-skill.py`. Prose edits get the writing-for-agents pass.
- Commit straight to `main`, **serially**: one wave lands before the next starts. Investigation
  may overlap; commits do not.
- Corpus evals depend on other repos. They are **run-gated** on `BENCHHYPE_ROOT` and
  `TIERCADE_ROOT`: a missing root is a typed skip, never a pass, never a failure of the suite.

## Commit sequence (one owner, one order)

1. **W0** — manifests, runner, clean Swift corpus, selftest. No detector exists yet.
2. **W1a** — ast-grep helper extraction, RED fixtures, `_invariant_signals.py`, experimental
   non-persisted scanner output. Corpus and restraint measurement.
3. **W2** — dead-surface aid, selftest, corpus and restraint measurement.
4. **Go decision** on W1a and W2 numbers, including the independent-repo restraint numbers
   (owner).
5. **W3 prose commit** — v3 schema documented, Step 6 routing sentence, startup 6c aid list,
   validation.md G49/G50 entries, output-format-json.md discovery block. Epoch boundary is this
   commit's SHA.
6. **W3 gate commit** — canonical v3 emission on by default, version-aware validators, G50 v3
   state scope, epoch, canon golden, selftests.
7. **W4** live run, **W5** records.

A no-go at step 4 leaves the experimental flag in place and the canonical document unchanged.
Nothing to roll back. The independent-repo restraint measurement is part of the go decision, not
a post-ship follow-up.

## Waves

### W0 — Freeze the corpora (small)

**Manifest** `contest-refactor/evals/ocr-corpus/benchhype-domain-2026-09.json`, checked in and
**immutable after W0**:

```json
{
  "repo_env": "BENCHHYPE_ROOT",
  "pre_fix_rev": "2b5247e9", "post_fix_rev": "80499e9c",
  "scope": "BenchHypeKit/Sources/BenchHypeDomain",
  "targets": [
    {"fid": 202, "class": "V", "detector": "invariant", "signal": "one_sided_guard",
     "path": "BenchHypeKit/Sources/BenchHypeDomain/Values/PlaybackSpec.swift",
     "symbol": "PlaybackSpec.init", "line_start": 0, "line_end": 0}
  ],
  "excluded_targets": [{"fid": 138, "reason": "Int one-sided guard, decision 2"}],
  "must_stay_silent": [{"fid": 155, "detector": "invariant", "path": "...", "symbol": "..."}]
}
```

Ten V targets, ten Z targets, two excluded `Int` targets kept on record, four must-stay-silent
rows (155, 131, 249 parallel-fields that are not impossible states; 141 sort-stability).
`symbol` follows the scanner's `Type.member` form for `invariant` rows. `dead_surface` targets
carry explicit `kind`, `type_name` and `name` fields instead of a composite symbol, matching the
row schema one-to-one. W0 fills `line_start`/`line_end` and the exact
symbols by reading the files at `pre_fix_rev`. Nothing writes to this file after W0.

**Restraint manifest** `contest-refactor/evals/ocr-corpus/tiercade-restraint.json`:
`{"repo_env": "TIERCADE_ROOT", "rev": "<HEAD sha pinned in W0>", "scope": "."}`. Tiercade is an
independent Swift repository on the owner's machine that neither OCR nor contest-refactor has
scanned; it is the out-of-sample restraint corpus.

**Clean Swift corpus** `contest-refactor/evals/ocr-corpus/clean-swift/`: ten hand-written value
types with correct two-sided and finite guards, uniqueness checks, custom `init(from:)`, and
every declared case, requirement and property referenced. Shared by W1a and W2, so it lands here.

**Runner** `contest-refactor/evals/ocr-corpus/run_corpus.py`:

- `--detector {invariant,dead_surface}` `--manifest PATH` `--rev {pre,post,pinned}` `[--assert]`
  `[--json PATH]`.
- Creates the worktree under `tempfile.mkdtemp()` outside both repos, `git -C $ROOT worktree
  add --detach <tmp> <rev>`, removes it through one idempotent `cleanup()` called from
  `finally`: `git worktree remove --force <tmp>` when the directory exists, then `git worktree
  prune` unconditionally so metadata never outlives a vanished directory; the `atexit`
  registration is removed after a successful `finally` cleanup.
- Adapters: `invariant` runs `scripts/audit_hotspots.py <tmp> --json --scope <scope>
  --experimental-invariant-queue --invariant-json <out>` (W1a) or reads the canonical v3 document
  (after W3). `dead_surface` runs `scripts/audit_dead_surface.py <tmp> --json --scope <scope>`.
- **Target matching** (`invariant`): `path` must equal and the normalized `symbol` must equal
  (strip generic clauses and parameter labels; POSIX path). When the target carries a non-zero
  `line_start`/`line_end`, the candidate's `line_range` must also overlap it, even when it is the
  only candidate with that symbol, so a different initializer of the same type can never satisfy
  the target. Overlap is never a substitute for the symbol match. `dead_surface` matches on
  `(kind, path, type_name, name)`.
- **Coverage validity comes first.** A run is `invalid_coverage` when the scanner `status` is
  anything other than `ok`, the command exits non-zero, the output is not decodable, or the
  detector flag is unknown or the detector script is missing. Partial scans are invalid here
  even when the target file was scanned; the corpus is small enough to demand `ok`.
- Result JSON: `{status: passed|failed|skipped_missing_root|skipped_missing_revision|
  invalid_coverage, detector, detector_version, command, rev, hits: [fid], misses: [fid],
  flagged_silent: [fid], candidate_total, files_scanned, target_candidate_ids: {fid: id}}`.
  `target_candidate_ids` is a generated output, not a manifest write.
- `--assert` exits **1 on `failed` and on `invalid_coverage`**, 0 on `passed` and on either
  skip. A skip prints its reason on stderr.

**Selftest** `scripts/_ocr_corpus_selftest.py`: manifest schema and `fid` uniqueness; every
target path exists at `pre_fix_rev` when the repo is reachable; `skipped_missing_root` with the
env unset; `skipped_missing_revision` on a bogus rev; a stubbed adapter returning `partial`
maps to `invalid_coverage`; `--assert` exit codes for all five states; the clean corpus parses.

Completion criterion: with no detector built, the runner reports `invalid_coverage` (unknown
flag / missing script) for both detectors at both revisions, and `--assert` exits 1. That is the
RED baseline.

### W1a — Queue D `invariant`, experimental (medium)

**Helper extraction first**: move `_ast_grep_matches` and its failure list from
`audit_hotspots.py` into `scripts/_ast_grep.py` (about 50 lines); `audit_hotspots.py` imports it.
`audit_boundaries.py` and `repo_map.py` keep their own copies untouched; no behavior change,
selftests unchanged. This removes the import cycle and makes the reuse claim true.

**Module contract** `scripts/_invariant_signals.py` (stdlib only, no imports from the scanner
family). It is a pure analyzer: `audit_hotspots.py` owns ast-grep and `_fs_filters`, obtains the
matches, and passes spans and contexts in.

```python
@dataclass
class InvariantSignals:
    one_sided_guard: int = 0
    clamp_unchecked: int = 0
    id_collection_no_uniqueness: int = 0
    codable_bypasses_throwing_init: int = 0
    int_conversion_unbounded: int = 0

@dataclass
class InvariantCandidate:
    path: str; symbol: str; start_line: int; end_line: int
    signals: InvariantSignals

@dataclass
class TypeContext:
    type_name: str
    stored_floating_properties: set[str]   # `var|let name: Double|Float|TimeInterval|CGFloat` lines in the type body
    conformances: set[str]
    has_init_from: bool
    has_throwing_init: bool                # any `init(...) throws` in the type body

def analyze_type(path: str, type_span: str, type_lines: tuple[int, int]) -> TypeContext
def analyze_member(path: str, ctx: TypeContext, member_kind: str, member_span: str,
                   member_lines: tuple[int, int]) -> InvariantCandidate | None
def analyze_type_level(path: str, ctx: TypeContext, type_lines: tuple[int, int]) -> InvariantCandidate | None
```

`audit_hotspots.py` calls `_ast_grep` for `class_declaration` (tree-sitter-swift uses it for
struct, class, enum and actor) and, inside each, `init_declaration` and `function_declaration`;
it builds `TypeContext` once per type and calls `analyze_member` per member and
`analyze_type_level` once. It also walks **top-level** `function_declaration` nodes that sit
outside any type (W0 found target 262, `formatTimeMMSS`, is a free function) and passes an
empty `TypeContext` for them.

W0 also established that target 205 (`Dropout`) has no throwing or guarded init at
`2b5247e9`, so the type-level rule as written cannot fire on it. It stays in the manifest as an
`expected_miss` row rather than being widened into a rule that would flag every Codable DTO with
a `Double`; the 7-of-10 bar counts it as a miss. A file whose ast-grep run fails contributes nothing and the failure
feeds the existing `partial` coverage path. Swift only in this wave; other languages produce no
invariant candidates.

**Predicates are name-local.** The name set for a member is the union of its floating
parameters `p` (declared type in `Double`/`Float`/`TimeInterval`/`CGFloat`, lexical from the
parameter list) and `ctx.stored_floating_properties`. `one_sided_guard`, `id_collection_no_uniqueness`
and `int_conversion_unbounded` evaluate over parameters only; `clamp_unchecked` evaluates over
the whole union, so a member with no floating parameter can still fire on a stored property.
The type-level rule reads `ctx` alone:

| Signal | Fires when | Targets | Silent fixture |
| --- | --- | --- | --- |
| `one_sided_guard` | comparisons naming `p` exist in exactly one direction after operand normalization (`0 < p` reads as `p > 0`), and neither `p.isFinite`, `p.isNaN`, nor an `allSatisfy` over a collection containing `p` appears in the member span | 202, 226, 267 | both directions, or `p.isFinite` |
| `clamp_unchecked` | `min(`/`max(` whose argument list names `p` or a name in `ctx.stored_floating_properties`, and no `isFinite` check for that same name in the member span | 204, 189 | `x.isFinite ? max(0, min(2, x)) : 0` |
| `id_collection_no_uniqueness` | a parameter typed `[<Name>ID]` or `[UUID]` is assigned to `self.` and the member span contains none of `Set(`, `Dictionary(grouping`, `allSatisfy`, `unique` | 224, 227 | `guard Set(ids).count == ids.count` |
| `codable_bypasses_throwing_init` (type-level) | `ctx.conformances` contains `Codable` or `Decodable`, `ctx.has_throwing_init` is true, and `ctx.has_init_from` is false | 205, 266 | custom `init(from:)` present |
| `int_conversion_unbounded` | `Int(<name>)` where `<name>` is `p` or a local assigned from `p`, the span contains `isFinite` for that name, and no `min(`/`max(` wraps that name | 262 | `Int(min(max(x, 0), 1e15))` |

Candidate identity: `(path, symbol, start_line, end_line)`; `symbol` is `Type.init` /
`Type.name` / `Type` (type-level). One candidate per member; signal counts are per parameter
hit.

Merge with A/B/C: equal identity unions `candidate_queues` and keeps the existing
`primary_queue`; otherwise a new entry with `primary_queue: "invariant"`. Roster cap
`--invariant-top-k` default 12; order by signal total desc, `path` asc, `start_line` asc.

Experimental output: `--experimental-invariant-queue` requires `--invariant-json PATH`; the
canonical stdout document stays v2. The side file uses the v3 shape defined in W3 so W0's adapter
and the W3 validator read one shape.

**RED fixtures**: one Swift file per signal and one silent file per signal under
`evals/hotspot-fixtures/invariant/`, exercised by a new Queue D section in
`_audit_hotspots_selftest.py`, one signal at a time.

**Measurement** (corpus runner, per signal kind and in total):
- Recall at `2b5247e9`: **≥ 7 of 10** V targets in the invariant roster.
- Silence at `80499e9c`: **0 of 10** still flagged; **0** of `must_stay_silent`.
- Budget: **≤ 20** invariant candidates on `BenchHypeDomain` at `80499e9c`.
- Restraint: clean Swift corpus **0** candidates; existing scanner fixtures silent; Tiercade at
  the pinned rev **≤ 0.25 candidates per Swift file**, with a ten-row spot check recorded
  (plausible / implausible, by a Sonnet-tier agent) for the owner to read.

### W2 — Dead-surface aid (medium)

`scripts/audit_dead_surface.py [<repo-root>] [--scope DIR] [--access public|internal|all]
[--json]` (stdlib). Defaults: repo root `.`, `--access all`, markdown table on stdout. Source
roots come from the `coverage_ledger.py --list-source-roots` enumerator (`_fs_filters`). Test
files use the same `_fs_filters` predicate and are scanned **separately**.

**Envelope** (`--json`): `{schema_version: 1, status: ok|partial|absent, promotion_allowed:
false, coverage: {files_scanned, files_failed, test_files_scanned}, rows: [...]}`. Exit 0 for
`ok`/`partial`/`absent`, 2 for usage errors. `absent` when no Swift source is found.

**Row**: `{kind: enum_case|protocol_requirement|declaration, path, line, type_name, name, access,
references_production, references_in_tests, references_in_previews, status:
dead|test_only|preview_only}`. The markdown table mirrors the fields. Status precedence when
production references are 0: `test_only` if `references_in_tests > 0`, else `preview_only` if
`references_in_previews > 0`, else `dead`.

**Declaration candidate set** (what enters the scan):
- `enum_case`: every `case` in an `enum` body, including associated-value cases. Access is
  inherited from the containing enum.
- `protocol_requirement`: named `func` and `var` requirements inside a `protocol` body only.
  `subscript` and `init` requirements are excluded in v1: their uses (`value[i]`,
  `Concrete(...)`, `.init(...)`) carry no member name the lexical rule can count, neither
  validated target needs them, and adding them requires a type-aware reference algorithm with
  its own corpus. Access is inherited from the containing protocol.
- `declaration`: type-member `var`, `let`, `func`, `static var/let/func`, and computed
  properties, declared directly in a type body or a type extension. Excluded: local declarations
  inside function bodies, closure parameters, `init` declarations (covered by callers of the
  type), declarations nested inside a `#Preview` block or a `PreviewProvider` type, and
  `@objc`/`@IBAction`/`@IBOutlet`/`@main`-attributed members (reflection or framework dispatch).
- `--access` filter: `public` = `public` and `open`; `internal` = `public`, `open`, and
  implicit or explicit `internal`; `all` = everything including `private` and `fileprivate`
  (whose references are counted within their declaring file only, since that is their scope).
  Each form and each access mode is pinned by a fixture in the selftest.

Reference counting, lexical and conservative:
- Production references are counted across **all** production files including the declaring
  file, excluding only declaration occurrences and pattern positions.
- Declaration occurrences: the declaring line of the symbol, and for protocol requirements every
  `func name(` / `var name` line inside a type that declares `: <ProtocolName>` (the
  implementations). Calls inside conformance files **do** count.
- Pattern positions for enum cases: `case .name`, `case let .name`, `case .name(`, `if case
  .name`, and `.name:` at the start of a switch arm. Everything else that reads `.name` or
  `.name(` counts as a construction or read.
- Dispatch through `any P` / `some P` counts as a reference like any other call.
- Shadowed or overloaded names: any occurrence of the bare name counts, so a shadowed name is
  never flagged. False negatives are accepted; false positives are the enemy.
- `#Preview { … }` blocks and `PreviewProvider` types are **counted separately** as
  `references_in_previews`. A symbol with production count 0 and preview count > 0 reports
  `preview_only`, never `dead`.

Pointer from `audit-public-surface.sh` lives in its `--help` text and stderr, never stdout.

Selftest `_audit_dead_surface_selftest.py`: one dead fixture per row kind; one silent fixture
per kind (case constructed in another file; requirement called from inside a conformance file;
declaration read in its own file); one `test_only`; one `preview_only`; envelope and exit-code
contract; `absent` on an empty root.

Measurement: **≥ 8 of 10** Z targets listed at `2b5247e9`; **0 of 10** at `80499e9c`; total
`dead` rows on `BenchHypeDomain` at `80499e9c` **≤ 30**; clean corpus 0; Tiercade **≤ 0.3 dead
rows per Swift file** with a ten-row spot check recorded.

Wiring: optional aid listed in startup.md 6c beside the existing three (decision 4). Inside the
W4 protocol, Step 0 runs `scripts/audit_dead_surface.py . --json` and the main agent includes
the `rows` array in the loop-1 dispatch payload as candidate evidence, exactly as the other
"Other candidate aids" reach the Critic; the W4 result records whether any row was cited in a
finding or in Builder Notes.

### W3 — v3 schema, prose then gate (small)

**v3 `hotspot_scan` schema**, exact deltas from v2:
- `schema_version: 3`.
- `queue_counts` has exactly `control`, `mutation`, `navigation`, `invariant`.
- Every candidate carries `candidate_id` and `invariant_signals` with exactly the five keys
  above (zeros for A/B/C-only candidates). `signals` keeps its exact v2 key set.
  `candidate_queues` may contain `"invariant"`.
- `candidate_id` = first 12 lowercase hex of SHA-1 over the UTF-8 string
  `f"{posix_path}|{symbol}|{start_line}|{end_line}"`. The validator recomputes it from those four
  fields and rejects a mismatch or a duplicate.
- Coverage object unchanged.

**Prose commit** (epoch boundary = its SHA); writing-for-agents pass on all four files:
- `startup.md` 6c: canonical schema statement names v3; dead-surface aid joins "Other candidate
  aids".
- `method.md` Step 6 hotspot handoff: one sentence routing `invariant` rows to Step 7 terms
  ("is the impossible state reachable through a public init or a decode path?"). Disposition
  vocabulary unchanged. v3 triage rows carry `candidate_id` beside `path`/`symbol`.
- `validation.md` G49 and G50 entries.
- `output-format-json.md` discovery block.

**Gate commit**:
- `_ruleset_epoch.py`: `HOTSPOT_V3` epoch at the prose SHA; `REQUIREMENT_EPOCHS["G49_HOTSPOT_V3"]`
  and `["G50_V3"]`.
- `_artifact_discovery.validate_hotspot_scan(scan, *, version)`; `check_g49_hotspot_scan`
  derives the version from the epoch (v2 before, v3 at or after). Per-version `_QUEUES`,
  `_CANDIDATE_KEYS`, and the `candidate_id` recomputation.
- `preflight.py` reads `skill_rev` from `--current-review` to pick the version.
- **G50 v3 state scope**: rows keyed by `candidate_id`; required when the scan is v3, candidates
  are non-empty, and either `state ∈ {HALT_SUCCESS_candidate, HALT_SUCCESS}` (unchanged) or
  `state == HALT_LOOP_CAP` with `loop == loop_cap` (the ordinary completed-cap path, which only
  exists after Step 6 ran). `HALT_EXHAUSTION` and `HALT_STAGNATION` can be emitted before Step 6
  (an emergency halt, or a `user_decision` at Method Step 1.5) and stay prose-governed, as do
  `CONTINUE` and `HALT_DRY_RUN`. v2 scope is unchanged before the epoch.
- Scanner emits v3 by default; `--experimental-invariant-queue` becomes a no-op alias, removed
  in W5.
- Canon: `validation-gates.toml` G49/G50 titles; `_canon_selftest.py` golden regenerated.
- Selftests touched: `_g49_selftest.py`, `_g50_selftest.py`, `_preflight_selftest.py`,
  `_audit_hotspots_selftest.py`, `_ruleset_epoch_selftest.py`, `_canon_selftest.py`. No fixture
  under `evals/fixtures` carries a `hotspot_scan`, so none change. `_g50_selftest.py` pins three
  cap-boundary cases for v3 scans: `HALT_LOOP_CAP` with `loop == loop_cap` requires triage;
  `HALT_LOOP_CAP` with `loop > loop_cap` is exempt; `HALT_EXHAUSTION` is exempt.

### W4 — Live recall run (owner-gated, one loop)

Setup: BenchHype worktree at `2b5247e9`; `/contest-refactor --cap 1` with opencode
`qwen3.8-flash`, the run-#9 configuration. Expected terminal state `HALT_LOOP_CAP` with
`loop == loop_cap == 1`, which G50 v3 now covers.

Observability, all named:
- **Roster and triage**: `discovery.hotspot_scan` (Step 0) and
  `discovery_consumption.hotspot_triage` (Step 6, gated at `HALT_LOOP_CAP` after W3) in
  `CURRENT_REVIEW.json`. Rows present with `dismiss` is a judgment result; rows absent with
  candidates present fails G50 and makes the run **invalid**.
- **Target attribution**: the W0 runner's `target_candidate_ids` output at `2b5247e9` gives each
  V target its `candidate_id`. Triage rows join on that id. Findings join through
  `findings[].evidence[]` entries whose path equals the target path and whose line falls inside
  the target's `line_start`–`line_end`. Accepted spellings for this measurement: `path:line` and
  `path:start-end` (the range must overlap), with or without surrounding backticks; anything else
  does not join and is listed under `unparsed_evidence` in the result. The finding schema is not
  changed.
- **Session capture**: the W4 protocol records `run_started_at` before launch and
  `run_ended_at` after the terminal state is written. The worktree directory is unique to W4, so
  the session set is **every** row `SELECT id, parent_id FROM session WHERE directory = ? AND
  time_created BETWEEN ? AND ?` for that directory and window; this includes the orchestrator,
  its `parent_id` descendants, and the independent reviewer session in one query. Assumption,
  stated: W4 launches a fresh root opencode session after `run_started_at`, so the selected set
  must contain **exactly one** row with `parent_id IS NULL`; zero or more than one sets
  `invalid_reason`. The observe plugin's `sessionID` values
  (`~/.contest-refactor/observe/tool-events.jsonl`, same directory and window) are a
  cross-check: every observed id must be a member of the selected set, else `invalid_reason`.
  The final set is written to the result file.
- **Token telemetry**: opencode's store `~/.local/share/opencode/opencode.db`, table `session`,
  columns `tokens_input`, `tokens_output`, `tokens_cache_read`, `tokens_cache_write`, `cost`,
  summed over the captured session ids. A missing table or column, or an unmatched captured id,
  sets `invalid_reason`.
- **Baseline, run #9 loop 1** (same store, 2026-09-02): loop subagent
  `ses_f9cfae6d8ffe…` 27.04M tokens (744 in, 95,947 out, 25.39M cache read, 1.55M cache write,
  $0.761); orchestrator `ses_f9d01c015ffe…` 5.75M ($0.255); reviewer `ses_f9ccaa445ffe…` 0.72M
  ($0.030). Total **33.5M tokens, $1.05**.
- **Result artifact**: `evals/ocr-corpus/w4-result.json` `{valid, invalid_reason, terminal_state,
  run_started_at, run_ended_at, queue_counts, triage_rows_present, sessions: [id],
  observed_session_ids: [id], target_candidate_ids: {fid: id}, v_targets_confirmed: [fid],
  z_targets_surfaced: [{fid, source: finding|builder_notes}], unparsed_evidence: [str],
  tokens_total, cost_usd}` plus a run-log entry.

Threshold (decision 3): **valid run** and **≥ 3 distinct V targets across ≥ 2 signal kinds** reach
`confirm` triage or a finding, with **tokens ≤ 41.9M** (1.25× baseline). Infrastructure or
telemetry failure is an invalid run, not a failed value. Z consumption is recorded, not
thresholded.

### W5 — Records (small)

- `docs/contest-refactor-run-log.md`: corpus and restraint results per detector with `status`,
  `detector_version`, and `command`; W4 result.
- `docs/contest-refactor-detection-domains.md`: DD-15 invariant queue, DD-16 dead-surface aid,
  each through the promotion bar with the measurements; DD-17 parked (W).
- Remove the experimental alias; memory update.

## Second pass: what could be wrong

- **Over-fit to one module of one repo.** Mitigations now in the go decision: clean corpus,
  existing restraint fixtures, and the Tiercade out-of-sample density bars with recorded spot
  checks.
- **Lexical type detection misses aliased types.** `TimeInterval` is covered; a project alias
  such as `typealias Seconds = Double` is not. Documented limit; the Critic re-derives.
- **W4 measures one loop with a flash model.** Triage rows separate judgment zeros from plumbing
  zeros; a plumbing zero now fails G50 and invalidates the run.
- **Dead-surface lexical rules under-count references in string-keyed or reflective code.** The
  conservative "any bare-name occurrence counts" rule makes that a false negative.
- **Schema bump blast radius.** Validator, preflight, canon golden, six selftests, G50 scope.
  No fixture carries a `hotspot_scan` today.
- **Tiercade density bars are guesses.** 0.25 and 0.3 per file are starting points; the owner
  reads the spot checks, and the bars are recorded with the result so a later corpus can
  recalibrate them.

## Owner decisions

Adopted from review rounds 1–2; the owner may override any of them:

1. **v3 bump behind an epoch**, with the `candidate_id` triage key and G50 v3 covering the two
   success states plus the completed-cap `HALT_LOOP_CAP` (`loop == loop_cap`).
2. **Float-only `one_sided_guard`**; 138 and 242 are `Int` targets, excluded and kept on record.
   Recall bar 7 of 10.
3. **Keep W4** with the predeclared threshold, captured session ids, and the named telemetry
   query.
4. **W2 stays optional** in production; run inside the W4 protocol.

## Parked

- W (field-level dual writer) as DD-17.
- An `Int` one-sided-guard variant, pending its own precision corpus.
- Reopening the 2026-08-26 stop decision for a presence-count scoring guardrail.

## Estimated size

Six waves, landed serially. W0 ~300 LoC plus the clean corpus. W1a ~550 LoC (helper extraction,
signals, fixtures). W2 ~450 LoC. W3 ~300 LoC across validator, preflight, epoch, canon, selftests,
plus four prose edits. W4 one loop, budget 41.9M tokens. W5 docs.
