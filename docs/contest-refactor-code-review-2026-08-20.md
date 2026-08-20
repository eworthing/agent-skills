# `contest-refactor` whole-skill code review

**Date:** 2026-08-20
**Scope:** `/Users/Shared/git/agent-skills/contest-refactor`
**Review passes:** 2 code-review passes + 1 ponytail whole-skill audit + 1 duplication/clarity pass + 1 full revalidation + 1 cross-doc merge (deep-dive backlog, behavioral ledger, June research doc)
**Revalidated:** 2026-08-20 against HEAD `cc3057b`. All five P1 and four P2 findings re-confirmed: every citation re-checked and all five reproductions re-run against the current tree (the two synthetic ones rebuilt from scratch). No finding overturned. Two findings' subject matter moved in the interim without resolving them — `a9ad8f3`/`e3f5aa8` added `challenger_isolation`/`reviewer_isolation` *recording* while the independence check stayed report-only, and `a9ad8f3` deleted the dead `validate-artifact.py` instruction the loop-path finding discusses. A dozen metrology corrections (counts and line spans) are folded in below; none changes a conclusion.
**Verdict:** **Request changes.** Five P1 execution/certification gaps and four P2 contract/test-oracle gaps remain. The second pass confirmed all six original findings, strengthened the dirty-tree finding, corrected two proposed remedies, and added two report-only hard-gate findings. The separate ponytail pass found two material simplification cuts and one exact dead-code cleanup. A third pass, run with the skill's own advisory audit tools pointed at the skill, added one P2 contract finding, four behaviour-preserving duplication cuts, and one test-coverage gap. A cross-doc merge validated the still-open findings from the deep-dive backlog, the behavioral ledger, and the June research doc, adding one P2-class compatibility defect ([I1], live on the repo's own artifact) and three smaller gaps ([I2]–[I4]).

## Coverage

The entire 1,348-file skill directory was in scope: `SKILL.md`, 26 reference documents, 111 top-level Python scripts, 6 top-level shell scripts, 21 canon TOMLs, 91 fixture directories, 20 reviewer cases, 37 scenarios, and the remaining plans, assets, eval outputs, and metadata. The review used the repository knowledge graph for structural discovery and call-path tracing, then inspected the relevant source and prose contracts directly. Corpus-sized fixture/output trees were validated mechanically; execution, rollback, terminal-validation, migration, and fixture-harness paths received manual source review.

### Validation run

| Check | Result |
|---|---|
| `python3 contest-refactor/scripts/validate-repo.py` | Pass |
| `python3 contest-refactor/scripts/validate-fixtures.py contest-refactor/evals/fixtures` | Pass: 91 fixtures |
| All `contest-refactor/scripts/_*selftest.py` files | Pass: 62/62 |
| `python3 contest-refactor/scripts/_smoke_check.py` | Pass: 11/11 |
| `python3 contest-refactor/scripts/token-budget.py --check` | Pass |
| `ruff check contest-refactor` | Pass |
| `ruff format --check contest-refactor` | Pass: 112 files already formatted |
| `bash -n contest-refactor/scripts/*.sh` | Pass |
| Skill evaluator | 12/15 automated checks (80%): warnings for `SKILL.md` size, optional `tiktoken`, and a credential-pattern heuristic in a self-test |
| `python3 contest-refactor/scripts/audit_boundaries.py .` | Pass: no first-party import cycles |
| `python3 contest-refactor/scripts/audit_clones.py .` | 34 clone-candidate pairs (16 in `scripts/`, 18 in fixture trees) |
| AST sweep: length + branch count per function | 807 functions (nested defs included); 49 over 80 lines; 28 over 120 |
| AST sweep: top-level defs referenced once and absent from prose | 3 candidates, all confirmed dead |

Passing these checks does not contradict the findings below: the gaps are either outside the current test oracle or explicitly configured as report-only.

### Second-pass challenge results

| Finding challenged | Result |
|---|---|
| Dirty-tree rollback | **Confirmed and strengthened.** Raw `git diff ... HEAD` includes unrelated tracked dirt that Step 0 explicitly allows, so the ownership bug applies beyond first-loop overlap. |
| Untracked-file review/rollback | **Confirmed.** The live untracked report appears in `git ls-files --others --exclude-standard` and is absent from `git diff --name-only HEAD`. |
| G5 9.5 residual | **Confirmed.** The v4 candidate reproduction still exits 0 in strict mode with a null residual and rationale. |
| G29 emission version | **Confirmed.** A complete v4 terminal fixture, relabelled as v3 in current + history, exits 0 and bypasses the v4 challenge floor. |
| Aspirational fixtures | **Confirmed; remedy revised.** Removing the exemption exposes wrong-gate failures, including canonical `G21` versus emitted `G21-scorecard`; two exemptions are already redundant. |
| Transition legality | **Confirmed.** `HALT_LOOP_CAP -> CONTINUE` prints a violation but exits 0 in strict mode. |
| Challenge/reviewer independence | **New P1.** A positive terminal fixture has no recorded challenge isolation, prints an unverified-independence warning, and exits 0. |
| G17 coverage citation | **New P1.** Two non-aspirational expected-pass fixtures print G17 violations and still exit 0. |

## Findings

### [P1] `changed_paths` conflates pre-existing dirt with loop-owned edits

**Source.** Step 0 explicitly permits non-overlapping dirt and promises those paths are excluded from narrow revert (`references/startup.md:31`). The desired overlap abort is also stated in the schema commentary (`references/output-format-json.md:223`), but the exact touch set is not selected until Step 2 (`SKILL.md:184-188`) and no operational recheck appears before Step 3 (`SKILL.md:191-197`). More importantly, Step 3 derives `loop_result.changed_paths[]` from the entire `git diff --name-only HEAD` (`SKILL.md:205`), which includes every pre-existing tracked difference, not only paths the loop touched. Rejection then restores every listed tracked path from `HEAD` (`SKILL.md:208`). The checkpoint's `pre_step3_blob_shas` also records committed blobs, not pre-existing working-tree bytes (`SKILL.md:197`).

**Consequence.** Any allowed pre-existing tracked edit appears in `changed_paths` even when it is outside the plan, but an unrelated path has no `pre_step3_blob_shas` entry and therefore no safe rejection branch. G28 can diagnose that mismatch only at Step 3 sub-step 8 (`SKILL.md:211`), after rejection already ran at sub-step 6. Separately, a first-loop plan can select a dirty path after the Step-0 check had no plan to compare; that planned path is snapshotted from `HEAD` and then restored to `HEAD` on rejection. The latter path directly erases user work.

**Smallest correction.** The safest minimal rule is to abort every mutating run when the tree is dirty. If non-overlapping dirt must remain supported, freeze its paths and bytes at Step 0, recheck the final Step-2 touch set before Step 3, and derive one loop-owned path set from changes relative to that baseline—not from the whole `HEAD` diff. Add replay cases for both an overlapping dirty file and an unrelated dirty file; rejection must preserve both original byte sequences.

### [P1] Untracked files are absent from the implementation review and rollback set

**Source.** Step 3 populates `loop_result.changed_paths[]` with `git diff --name-only HEAD` (`SKILL.md:205`), while the implementation reviewer is told to inspect `git diff HEAD` (`references/implementation-reviewer.md:49-56`). Neither command includes ordinary untracked files. Rejection iterates only `loop_result.changed_paths[]` (`SKILL.md:208`). G28 checks that each *listed* changed path has a pre-Step-3 snapshot, but never checks for changed/untracked paths omitted from that list (`scripts/_artifact_history.py:748-773`).

**Consequence.** A loop-created file can be committed after an approval even though the reviewer never saw it. On rejection, the same file is not deleted, so it contaminates the next loop and remains outside the claimed rollback boundary.

**Second-pass confirmation.** The repository's own Layer-3 materializer runs `git add -A` before `git diff HEAD`, specifically so additions appear (`evals/README.md:952-959`). Production Step 3 has no equivalent pre-review staging instruction, so the eval topology masks the production gap.

**Smallest correction.** Build one frozen **loop-owned** path set: planned tracked paths whose content changed from the Step-3 baseline plus planned untracked paths created after that baseline. Do not union all repository untracked paths; that would absorb pre-existing user files and repeat the first finding. Use the same set for reviewer input, `loop_result.changed_paths`, G28, staging, and rejection cleanup. Extend the reviewer-revert self-test with one loop-created untracked file and one pre-existing untracked restraint file.

### [P1] Strict validation accepts a 9.5 score with no residual evidence

**Source.** G2 and G5 require every score in `[9.5, 10)` to name its residual and rationale (`references/validation.md:35-42`). The implementation explicitly skips that range and says the forward half is deliberately unmechanized because an expected-pass fixture violates it (`scripts/_artifact_residual.py:69-91`). The G5 self-test locks this bypass in as a passing case (`scripts/_g5_selftest.py:96-102`).

**Reproduction.** Starting from the complete v4 `halt-candidate-no-challenge` fixture, setting one 9.5 dimension's `residual_blocking_10` and `residual_rationale_or_backlog_ref` to `null`, keeping `residual_disposition: "accepted"`, mirroring the change into history, and recomputing the candidate fingerprint produced:

```text
python3 contest-refactor/scripts/validate-artifact.py <repro> --mode strict --quiet
validator_exit=0
```

The only output was the unrelated report-only challenge-independence warning.

**Consequence.** A `HALT_SUCCESS_candidate` can clear strict validation while omitting the evidence that distinguishes an earned 9.5 from an inflated score. G21 checks the score and `accepted` disposition, so it does not close this hole.

**Smallest correction.** Enforce the existing forward-half rule for every `[9.5, 10)` dimension. Repair `halt-loop-cap-clean` rather than preserving its invalid shape as the reason not to enforce the rule, and turn the reproduction above into a negative v4 fixture.

### [P1] Terminal success does not require an independently run reviewer or challenger

**Source.** The v4 schema says `challenger_isolation` records how the challenge actually ran, that top-level loop isolation does not imply it, and that absence means unverified (`references/output-format-json.md:131-143`). The checker documents a live terminal self-vet, detects inline or missing isolation, but is deliberately `REPORT_ONLY` and returns no issue (`scripts/_artifact_independence.py:1-38,49-126`). It only prints when `implementation_review.reviewer_isolation == "inline"` and does not even construct a reviewer issue (`scripts/_artifact_independence.py:83-88`).

**Reproduction.** The non-aspirational, expected-pass `halt-terminal-held` fixture claims valid G32 terminal success (`evals/fixtures/halt-terminal-held/fixture.toml:1-9`) but records neither reviewer nor challenger isolation. Strict validation prints `challenge-independence-unverified` and exits 0.

**Consequence.** `HALT_SUCCESS` can assert that an independent challenge held even when the artifact proves only that a model string was recorded. An inline self-review or self-challenge shares the context and anchoring that these passes exist to remove, so the terminal certification is materially weaker than advertised.

**Smallest correction.** For artifacts emitted by the current skill, require `reviewer_isolation == "subagent"` on approved implementations and `challenger_isolation == "subagent"` before terminal promotion. Scope compatibility with a schema bump or `skill_rev`; do not retroactively reject older v4 artifacts. Providers that cannot perform the required spawn should follow the existing fail-closed `verification_blocked` route.

### [P1] G17 is called a hard gate but cannot block an untested deepening refactor

**Source.** Step 3 requires G17 before commit (`SKILL.md:211`), and the reviewer contract says a deepening refactor with neither new tests nor a valid indirect-coverage citation must be rejected (`references/implementation-reviewer.md:94-108`). The structural checker detects the missing citation but is deliberately `REPORT_ONLY`, prints each issue, and returns an empty list (`scripts/_artifact_coverage_citation.py:1-19,124-208`).

**Reproduction.** Both `g41-cap-loop-executed` and `reviewer-retry-then-success` are non-aspirational `expected_result = "pass"` fixtures (`evals/fixtures/g41-cap-loop-executed/fixture.toml:1-7`; `evals/fixtures/reviewer-retry-then-success/fixture.toml:1-6`). Each records an approved deepening change with only source paths and no `interface_test_coverage_path`. Running strict validation prints a G17 violation for each and exits 0.

**Consequence.** A model reviewer can approve a deepening refactor that has no test at the new interface, and the supposedly redundant hard gate still certifies the artifact. The fixture suite currently locks both violations in as valid successes.

**Smallest correction.** Enforce G17 for new current-schema emits, add valid citations or test paths to the two positive fixtures, and keep an isolated negative fixture proving the missing-citation case exits nonzero. Preserve old-artifact compatibility through the same version/`skill_rev` policy used for the independence fix. Since this was written, a promotion bar for flipping `REPORT_ONLY` was recorded in `docs/behavioral-validation-ledger.md` (≥5 applicable runs, ≥1 observed violation, ≥2 restraint cases, zero blind lines, human-adjudicated) — the flip condition now exists in writing; the gap stays open until a run history satisfies it.

### [P2] The current emission-version contract still tells agents to write schema v3

**Source.** The current format says capable profiles emit schema v5 and unentered profiles remain on v4 (`references/output-format-json.md:21-31`); the required-field example is v4 (`references/output-format-json.md:169-180`). G29 still says every artifact emitted by “this version of the skill” must use schema v3 and only describes v1-v3 mixed history (`references/validation.md:99-104`). Step 3 continues to require G29 before commit (`SKILL.md:211`). `validate-artifact.run_checks` has no G29/version-emission check at all (`scripts/validate-artifact.py:124-172`), and `check_schema_enums` does not validate `schema_version` (`scripts/_artifact_core.py:250-329`).

**Consequence.** The emit-time reference set contains mutually incompatible instructions. An agent that follows G29 can write v3 and thereby avoid all v4/v5-gated controls while strict validation still accepts the declared version.

**Second-pass reproduction.** Copying the complete expected-pass `halt-terminal-held` artifact, changing only current and latest-history `schema_version` from 4 to 3, and rerunning strict validation exits 0. The terminal challenge is no longer required because the artifact self-declared the stale version.

**Smallest correction.** Update G29 to the current v4/v5 capability rule and give emission one authoritative version decision. Either enforce that decision on new emits or stop describing G29 as a hard gate; retain per-entry compatibility only for reading genuine older history.

### [P2] Eight aspirational fixtures can pass for an unrelated failure

**Source.** `validate-fixtures.py` checks only exit status for `aspirational = true` failures and skips the assertion that a cited gate actually fired (`scripts/validate-fixtures.py:443-499`). Eight fixtures use the exemption: `bootstrap-repo`, `continuation-post-commit`, `dry-run-halt-after-step2`, `dry-run-rerun-no-reset`, `halt-success-bad`, `incremental-then-halt-success`, `loop-state-post-commit-pre-delete`, and `no-backlog-residual-accounting`. Seven notes explicitly say strict mode currently fails on missing unrelated artifacts or that the intended rule is not implemented; for example `continuation-post-commit/fixture.toml:1-10`, `incremental-then-halt-success/fixture.toml:1-10`, and `no-backlog-residual-accounting/fixture.toml:1-10`. `halt-success-bad` says it now fails for the canonical G21 reason but remains aspirational (`halt-success-bad/fixture.toml:1-10`).

**Consequence.** A regression in the named continuation, resume, dry-run, full-reverify, or residual-accounting behavior can leave `validate-fixtures: OK (91 fixtures passed)` unchanged. The suite verifies that *something* failed, not the behavior each fixture claims to protect.

**Second-pass correction.** Removing `aspirational` in memory shows that `halt-success-bad` fires `G21-scorecard`, while its canonical citation is `G21`, so the harness reports `wrong-gate-fired`; `G18` also fires. `loop-state-post-commit-pre-delete` already satisfies its cited-gate assertion without the exemption, while `bootstrap-repo` cites no gate and the flag has no effect.

**Smallest correction.** First normalize emitted sub-rule labels to canonical gate IDs (or declare an explicit sub-rule mapping). Make each remaining fixture complete enough to fail only for its intended behavior. Then remove the exemption from `halt-success-bad` and `loop-state-post-commit-pre-delete`; reclassify examples with no mechanized assertion rather than counting them as gate coverage.

### [P2] Illegal terminal-to-active transitions do not fail strict validation

**Source.** The transition validator prints violations but deliberately returns no issues while `REPORT_ONLY = True` (`scripts/_artifact_transitions.py:23-30,55` and `scripts/_artifact_transitions.py:117-136`). The dedicated `transition-illegal-post-cap-continue` fixture declares `expected_result = "pass"` even though it contains `HALT_LOOP_CAP -> CONTINUE` without a reset (`evals/fixtures/transition-illegal-post-cap-continue/fixture.toml:1-7`).

**Consequence.** `validate-artifact.py --mode strict` exits zero for history that continues past a terminal state. Automation can therefore accept a run whose state history contradicts the canonical transition table. This is not hypothetical: the repo's own dogfood artifact trips the same checker with `HALT_LOOP_CAP→CONTINUE` at loop 10→11 (see [I1]).

**Smallest correction.** Finish the existing shadow rollout: set `REPORT_ONLY = False`, change the illegal-transition fixture to an expected failure, and keep the existing transition-table self-test as the restraint check for legal histories.

### [P2] The loop is told to run hard gates but never told to run the gate implementation

**Source.** Step 3 sub-step 8 instructs the agent to "Run hard gates G15 + G16 + G17 + G19 + G22 ... + G38 before commit" (`SKILL.md:211`); sub-step 5 does the same for G1 + G2 (`SKILL.md:204`). Neither names a command. `canon/validation-gates.toml` registers 46 gates, and 27 of them have a deterministic implementation (`grep -rhoE 'def check_g[0-9]+' scripts/*.py | sort -u`; the digit is required — a `[0-9]*` variant also matches helper names like `check_gate_sequencing`). But `validate-artifact.py` appears only three times across the entire loop-path reference set, and none is an instruction: once in a script inventory (`SKILL.md:294`) and twice as descriptive asides naming which sub-check is mechanized (`references/validation.md:42,66`). Compare `repo_map.py` (`references/method.md:46,82`) and `audit_clones.py` (`references/method.md:85`), which *are* invoked as steps.

**Consequence.** "Run hard gates" resolves to hand-checking against `references/validation.md` — 14,547 tokens, **17.3 % of the 84,276-token per-loop reload** — while a deterministic implementation of 27 of those same gates sits unexecuted. This is the delivery mechanism behind the two report-only findings above: flipping `REPORT_ONLY = False` on G17 or on the transition validator changes nothing on the loop path, because nothing on that path runs the module the flag lives in. Enforcement work lands in a component the loop does not reach.

A second-order effect compounds it. Registering `G<n>` obliges a `validation.md` checklist bullet, and `validation.md` is on the per-loop reload path — so every gate that gets mechanized makes the Critic's per-loop reading **longer**, never shorter. Nothing in the file marks a gate as mechanized, so the prose grows monotonically with the mechanization that was supposed to relieve it.

**This is measured, not inferred.** `docs/behavioral-validation-ledger.md` sweep #4 recorded it directly: across ~6 Step-3 passes over two production runs, in both inline and subagent isolation, the loop never ran `validate-artifact.py` (P2, **0/2**), while output-shaping prose was followed (P3, **2/2**). Run by hand against the same artifact the validator reported 15 WARNs mid-run and a real G17 violation at terminal. Corroboration: asked for concerns about its own run, the loop's provider hand-audited the artifact and produced 12 findings, **5 of which are defects `validate-artifact.py` already implements**.

**Smallest correction.** Invoke the validator outside the model's discretion — a host hook or a wrapper around the commit step — not a prose instruction. Adding "run `validate-artifact.py`" to the checklist is the obvious fix and is **already measured dead**: that instruction shipped 2026-08-19 (`ee21bc8`, the "Mechanical sweep" bullet in `validation.md`), fired 0/6 across two production runs, and was deleted 2026-08-20 (`a9ad8f3`) at a measured 64 tokens per loop. The full prose-instruction lifecycle — added, measured never firing, withdrawn — ran to completion in under 40 hours, between this review's first pass and its revalidation; the host-hook route is now the only one not yet tried. The ledger's own conclusion stands: *enforcement cannot be reached through an instruction that never executes.* Only once invocation is guaranteed does compressing the bullets it subsumes become safe; until then `validation.md` must keep carrying all 46. One prerequisite before any hook ships: the retroactive-invalidation gap in [I1] — a hook that runs strict validation inherits the false failures on every pre-existing artifact.

## Ponytail over-engineering audit

**Boundary.** This pass covered only tracked material under `/Users/Shared/git/agent-skills/contest-refactor`. It excluded ignored/generated `.build`, `__pycache__`, and `.DS_Store` content from the line estimate. The P1/P2 findings above—including the three report-only validators—remain correctness work and are intentionally not recast as simplification opportunities.

1. `yagni:` `SKILL.md:140`, `canon/panel-certification.toml:5-39`, `plans/rec1-panel-certification.md:1-469`, panel scripts/evidence, and `evals/fixtures/panel-*` — remove the parked v5 panel stack from the shipped skill until a provider/model can actually satisfy its certification contract: the manifest has zero entries, the routing contract says no profile is v5-authorized, and the recorded owner decision parks the feature while v4 remains the live path everywhere. The 20 panel fixtures plus only the wholly attributable scripts, plan, canon, and recorded gate output total at least 14,666 tracked lines; mixed v4/v5 validator files and embedded prose are deliberately omitted from that estimate.
2. `shrink:` `evals/fixtures/*/{CURRENT_REVIEW.json,REVIEW_HISTORY.json}` and `scripts/validate-fixtures.py` — materialize the final history entry from `CURRENT_REVIEW.json` inside the fixture harness instead of storing it twice. G18 requires parsed equality, and 83 of 85 fixture histories repeat the current review as their last entry; after excluding the panel fixtures above, 63 histories still duplicate 9,485 lines. Keep explicit prefixes for multi-loop cases and explicit full histories for the two current nonmatches; this preserves the production artifact contract while removing roughly 9,400 net fixture lines.
3. `delete:` `scripts/audit_cochange.py:214-219` and `scripts/validate-repo.py:292-297` — remove `_has_python_sources`, `_has_swift_sources`, and `_enum_tokens_from_text`. The knowledge graph reports zero callers for the first two, and a repository-wide `git grep` across every tracked file returns only the three definitions themselves. The extension sets `_PYTHON_EXTS` / `_SWIFT_EXTS` remain live elsewhere (`audit_cochange.py:294,397,399`), so only the functions go. `_enum_tokens_from_text` was found by the third pass and is doubly removable: its entire body is `set(re.findall(...))`, so it is a redundant wrapper as well as an uncalled one. Fourteen dead lines total, no replacement needed.

`net: -24,000 lines, -0 deps possible`

## Duplication and clarity audit

**Boundary.** This pass ran the skill's own advisory audit tools *against the skill* — the same tools Method Step 3 points at a target repo. Dogfooding them is cheaper than hand-rolling duplication analysis and doubles as a live test of whether they work. `audit_clones.py` produced D1 through D4 directly; D5 and the D6 notes came from the AST sweeps and from building D1's proof. It also correctly flagged the fixture trees (which are *supposed* to contain duplicates) and printed its own `promotion_allowed: false` doctrine note. Scope is **behaviour-preserving** cuts only: nothing here changes what the skill decides, which is what separates this section from the P1/P2 findings above. It does not overlap the ponytail audit — that section deletes whole features, this one factors repetition inside code that stays.

The skill is in good shape by these measures: no import cycles, no lint debt, three dead functions in 31,851 lines, and selftests making up 45 % of the Python tree. Total mechanical saving below is ~260 lines — deliberately not a large number, because there is not a large one available. The value is in D1 (a live wrong-file-error hazard) and D4 (a divergence that has already happened), not the line count.

| # | Item | Saving | Risk |
|---|---|---|---|
| **D1** | `_canon.load_canon` writes one 4-line idiom 20× | **−91 lines**, proven equivalent | Very low |
| **D2** | `_load_validator` copy-pasted into 14 files | −85 lines | Very low |
| **D3** | Gate-selftest driver duplicated across G39–G42 | −87 lines | Low |
| **D4** | `_check_replication` duplicated **and already diverged** | 0 lines; correctness risk | Needs a decision |
| **D5** | `_canon.py`'s 16 error paths are exercised by nothing | +1 selftest | Independent of D1 |

### [D1] `_canon.load_canon` — one idiom, twenty times

`scripts/_canon.py:78-296`. 219 lines, branch count 25, in the module **30 other scripts import** — the highest-fan-in function in the skill and the most repetitive. Three shapes repeat: load-one-file-take-one-list (20 call sites), list-of-tables→id-keyed-map (twice: `scorecard-dimensions` 30 lines, `validation-gates` 28 lines, same algorithm, two key names apart), and optional-file-if-exists (three identical 4-line blocks).

The load-one-list idiom spells the filename **twice per call**:

```python
halt_subtypes = _require_list(
    _load_toml(canon_dir / "halt-subtypes.toml"),
    "halt_subtypes",
    canon_dir / "halt-subtypes.toml",     # <-- same literal, second time
)
```

**Ten canon files have their path literal written twice in the same call**, and nothing forces the two to agree. The second exists only so the error message names the right file, so the failure is silent and specific: edit one, miss the other, and a malformed `match-kinds.toml` reports itself as a problem in `verdicts.toml` — a wrong-file error message in the one component whose whole job is being the single source of truth for enums.

**Recommended shape.** Three helpers — `_fail(path, msg)`, `_list_from(canon_dir, filename, key)`, `_id_map(canon_dir, filename, list_key, value_key, noun)` — then the bulk of `load_canon` becomes a declarative `(filename, key)` table in which each filename appears **once**, so the hazard cannot be written. Files contributing several keys or scalars alongside lists (`states`, `exhaustion-kinds`, `remediation-fields`, `trial-validity`) stay explicit; they are genuinely different, and flattening them would be the over-simplification this pass exists to avoid.

**Proven, not estimated.** A working prototype was built and measured; it is **not** in the repository.

| Check | Result |
|---|---|
| `load_canon` | **219 → 99 lines** |
| Module, post `ruff format` | **338 → 247 lines** (−91) |
| `ruff check` / `ruff format --check` | Clean |
| Canon equivalence | **All 21 dataclass fields identical**, including `extra`'s 12 keys and the insertion order of both `MappingProxyType` maps |
| Mutation test | **11/11 killed identically** by old and new |

Mutations: missing top-level key, key-not-a-list, duplicate gate id, gate entry missing `title`, duplicate scorecard id, scorecard entry missing `display_label`, multi-list file broken, optional file broken, canon file missing, canon file empty, canon file malformed. All exit 2 under both versions.

The equivalence test is the deliverable, not the diff — with 30 importers, "the Canon object is unchanged" is the only assurance worth having. Ship it as `scripts/_canon_selftest.py` — see **D5**, which is the reason to write that file whether or not D1 ever ships.

> Two mutations initially read as MISMATCH and were not: `verdicts` first occurs inside a comment so the replace hit the comment, and the scorecard id is `architecture_quality`, not `architecture`. Both were failing to *land*; old and new agreed on every row throughout. Recorded because a mutation that does not mutate is the commonest way a mutation test lies, and it lies reassuringly.

### [D2] `_load_validator` is copy-pasted into 14 files

AST-normalized with string constants folded, **14 files carry one identical definition** — `_g5`, `_g16_uniqueness`, `_g19_skill_rev`, `_g22_status`, `_g32_panel_testkit`, `_g37`, `_g39`, `_g40`, `_g41`, `_g42`, `_g43`, `_metric_isolation`, `_ref_tree_lint`, `_strictness_isolation`:

```python
def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_g17", path)   # only the name differs
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

Two more files (`_project_config_selftest`, `_repo_map_selftest`) load a *different* module and are correctly excluded. The varying `"_va_g17"` string is cosmetic: `module_from_spec` never registers in `sys.modules`, so the name surfaces only in a traceback.

**The precedent already exists.** `scripts/_g32_panel_testkit.py` is a shared selftest helper imported by two G32 selftests, so the repository has already accepted a testkit module. Extend it or add `scripts/_selftest_lib.py` beside it: ~85 lines, and the importlib incantation stops being something 14 files can independently get wrong.

### [D3] The gate-selftest driver is duplicated across G39–G42, and its guards have already drifted

`_g39_selftest.py:158`, `_g40_selftest.py:174`, `_g41_selftest.py:162`, `_g42_selftest.py:157` run the same driver: iterate a case table, assert fire-vs-silence, assert every emitted `Issue.rule` is the expected gate, add `_isolation()`, then apply vacuity guards. `audit_clones.py` reports **similarity 1.00 over 37 lines** for each pair among G40/G41/G42; AST comparison shows `_g41` and `_g42` are structurally identical, with `_g39` (33 lines) and `_g40` (39 lines) differing only in whether `canon` is threaded through and whether `_cases()` is bound to a variable. 146 lines across four copies.

**The drift is not hypothetical — it is already present.** Three of the four carry both vacuity guards; `_g39_selftest.py` has only `triggers == 0` and no `REGRESSION_CASE` guard, and defines no regression case at all:

| file | `triggers == 0` guard | `REGRESSION_CASE` guard |
|---|---|---|
| `_g39_selftest.py` | ✅ | **❌** |
| `_g40_selftest.py` | ✅ | ✅ |
| `_g41_selftest.py` | ✅ | ✅ |
| `_g42_selftest.py` | ✅ | ✅ |

That is the argument for factoring, and it is not about the ~87 lines. The vacuity guards are the cleverest thing in these tests and the part a new gate is most likely to omit — a guard that lives in four copies is one that will exist in three of them. A shared `run_gate_cases(va, gate_fn, rule, cases, regression_case, isolation)` makes both guards the default rather than something each new selftest must remember to copy. Each file keeps its own `_cases()` and `_isolation()`; those are the actual test content.

Whether `_g39` *should* pin a regression case is a separate call — G39 may genuinely have no production shape worth pinning. The finding is that guard coverage is 3-of-4 and nothing enforces the fourth. Best done when the next gate is written, so the driver is designed against a real fifth caller rather than a guessed one.

### [D4] `_check_replication` is duplicated and has already diverged

`_advisory_baseline_selftest.py:98` (92 lines) and `_principal_baseline_selftest.py:52` (105 lines) — similarity 0.89, the largest pair in `scripts/`, **79 lines matching verbatim** (difflib matching blocks across the two bodies). This is the one item here with a correctness edge, because the two copies no longer agree on what they check:

| Check | advisory | principal |
|---|---|---|
| Block shape, `runs == 5`, decision enum, `m + inv > 5`, kind-specific floor ordering | ✅ | ✅ |
| Terminal-slot count / invalid-count reconciliation / valid-slot field presence | ✅ | ✅ |
| `arm` validated against `VALID_ARMS` | ✅ | ❌ |
| Terminal slot scoped to the `current` arm | ✅ | ❌ |
| `headline_excluded` ⇒ `contaminated` | ❌ | ✅ |
| No retry attempt after a valid attempt 1 | ❌ | ✅ |

Four checks exist in one copy and not the other. That is the expected end state of a 92-line copy-paste, and it has arrived. The open question is which asymmetries are deliberate — the two studies genuinely differ (multi-arm versus single-arm), so some are correct — and which are simply the edit that only landed once.

**Do not unify first.** `evals/advisory_baseline.json`, `evals/principal_baseline.json` and both `*_replication.json` files are frozen historical records that must stay byte-identical, so a merged checker that is *stricter* would fail a committed baseline and one that is *looser* would silently stop checking something. Sequence it: (1) add each missing check to the copy lacking it, one at a time, and observe which baselines still pass — a check that passes on both was an omission, one that fails was a real difference; (2) only then factor the common core, passing the genuinely per-study checks in. Step 1 is the valuable half and is worth doing even if step 2 never happens.

### [D5] `_canon.py`'s 16 error paths are exercised by nothing

Found while building D1's proof, and **independent of it** — this holds whether or not D1 is ever done.

`_canon.py` has no dedicated selftest, but that is the wrong way to state the gap: `load_canon` is among the most-exercised code in the skill. 27 files call it across 29 call sites (AST-counted call expressions; an earlier grep count of 31 included two docstring mentions), and every run of the 62-selftest suite goes through it. The happy path is covered many times over.

What is covered *only* by the happy path is the point. Every one of the 29 call sites passes the **real, shipped, valid canon**:

| Call shape | Sites |
|---|---|
| `load_canon(SKILL_ROOT)` | 22 |
| `load_canon(HERE.parent)` | 5 |
| `load_canon()` (defaults to the real root) | 1 |
| `load_canon(vf.SKILL_ROOT)` | 1 |

Not one passes a synthetic or malformed canon directory. `_canon.py` has **16 `sys.exit(2)` sites** — 3 in `_load_toml` (file missing / malformed TOML / empty), 2 in `_require_list` (key missing / key not a list), and 11 inline in `load_canon` (per-entry shape, duplicate ids, missing scalars); split re-verified at HEAD. **All 16 are unreachable from the current test suite**, because nothing ever hands the loader a bad canon.

**Consequence.** The module that every validator treats as the single source of truth for enums will exit 2 with a specific diagnostic on every malformed-canon shape it is written to reject, and no test has ever confirmed that any of them fires, or that it names the right file when it does. This is also what makes D1's double-spelled-path hazard invisible: the wrong-file error message it produces would surface only on a path nothing exercises.

**Correction.** `scripts/_canon_selftest.py`, feeding `load_canon` a `tempfile` copy of `canon/` with one file broken per case, asserting exit code 2. The 11 mutations from D1's proof are exactly this test and already cover every category: missing top-level key, key-not-a-list, duplicate gate id, gate entry missing `title`, duplicate scorecard id, scorecard entry missing `display_label`, multi-list file broken, optional file broken, canon file missing, canon file empty, canon file malformed.

**This is time-sensitive in a way the other items are not.** Those 11 mutations are the only thing that has ever executed those paths, they were written as throwaway session scratchpad scripts, and they are gone when the session ends. Every other item here can be re-derived from the repository at any time; this one has to be re-written from scratch once the harness is lost. It is roughly an hour's work either way — but an hour that has already been spent once.

### [D6] Consistency notes — no action proposed

- **Two selftest idioms.** 56 files accumulate `failures: list[str]` (47 of them share the epilogue byte-for-byte); `_panel_capability_selftest.py` and `_panel_gate_adapter_selftest.py` use a `[(label, test_fn)]` table with an `except AssertionError` driver (which `audit_clones` catches as a 51-line 0.94 pair). The assert style is better — per-case `ok:` output, failures name themselves. If a third file wants a driver, use that shape rather than adding a third.
- **Four spellings of one bootstrap.** 31 files put `scripts/` on `sys.path` as `HERE` (14), `SCRIPT_DIR` (10), `SKILL_ROOT / "scripts"` (6), and one inline `Path(__file__).resolve().parent`. Normalize opportunistically.
- **`_artifact_history.py` is at 799 lines against the 800-line hard cap** enforced by `common/scripts/check_module_size.py` via `.githooks/pre-commit`. Comments were already compressed to fit rather than take a `# WAIVER: module-size`. One line of headroom: splitting the G19/G28 checks into their own module is a prerequisite for further work there, not a nice-to-have.

### Checked and deliberately not flagged

Static analysis over-rates severity, so the calibration matters as much as the findings.

- **`_paired_arm_validate.validate_attempt`** — 127 lines, branch count **51**, the densest function in the skill. Not a finding. It is a flat schema validator: independent field checks appending to one `add` accumulator, with an early bail-out where branches genuinely cascade. Every branch *is* a rule; splitting it into five helpers would move the rules without reducing them and would hide the bail-out. Cyclomatic complexity measures the wrong thing on flat validators.
- **`_g32_panel_selftest._cases` (438 lines), `_g32_panel_coupling_selftest._cases` (282), `_g43_selftest._cases` (159)** — branch count **1**. Literal case tables: data, not logic. Long data is not complex data.
- **`audit_cochange.py:496` ↔ `repo_map.py:323`** (43 lines, 0.91) — argparse CLI boilerplate, at n=2. Below the rule of three; a shared CLI factory for two scripts with different flags costs more than it saves. Revisit if a third advisory tool grows an argparse block.
- **The `if failures: … return 1` epilogue — 47 byte-identical copies, 188 lines.** Deliberately **not** recommended for extraction despite being the largest raw duplication in the skill. Those four lines are not incantation; they *are* the contract `CLAUDE.md` states ("run each directly, exit 0 = pass"), visible where a reader needs them. Centralizing would make 47 standalone tests share a dependency whose breakage breaks all 47 at once, to save four lines each. The distinction against D2, and the whole judgment call in this section: **`_load_validator` is incantation — seven lines of importlib nobody reads and anybody could get wrong; the failure epilogue is contract — four lines everybody reads and nobody gets wrong. Factor incantation; leave contract at the call site.**
- **18 of the 34 clone rows** — all in `evals/reviewer-cases/`, `evals/loop-fixtures/`, `evals/exec-fixtures/`: near-duplicate Swift in base/head and paired fixtures. That duplication is the test material; several of those fixtures exist precisely to give a reviewer duplicated code to find. Removing it would delete the tests.

### Suggested sequence

Each step is independently shippable and revertable. 1) The dead-code deletion in ponytail item 3 above — minutes, zero risk. 2) **D1**, with `scripts/_canon_selftest.py` carrying the equivalence and mutation tests; highest value, and the proof already exists. 3) **D2**, extending the `_g32_panel_testkit.py` precedent. 4) **D3**, when the next gate is written. 5) **D4 step 1** only — cross-apply the four asymmetric checks and record which were omissions; do not unify yet. **D5 is not in this order**: it is independent of D1 and should be written while the mutation set that proves it still exists. Steps 1–3 are ~260 lines and behaviour-preserving; step 5 is the one that might find something real.


## Findings inherited from the deep-dive backlog, the behavioral ledger, and the June research doc

**Boundary.** A merge pass over `docs/review-skill-deep-dive-2026-08-17.md` (35-row backlog), `docs/behavioral-validation-ledger.md`, and `temp/contest-refactor_research.md` (2026-06-24), keeping only findings that are (a) defect-shaped, (b) still open at HEAD, and (c) not already covered above. Most of both documents dedups away: sweep #4's P2/P3 measurements are the evidence base of the loop-path P2 above; the G17 promotion bar is cross-referenced there; backlog item 12 became the transitions P2; rows 31/32 shipped the morning of this review (`a9ad8f3`/`e3f5aa8`); rows 1–4, 14, 16–22, 24–26, 29 are shipped, designed, measured-and-declined, or parked with recorded evidence.

### [I1] G43/G46 added required v4 fields with no version bump — the repo's own artifact now fails strict validation (backlog row 30)

**Re-validated at HEAD.** The repo's own dogfood artifact (`CURRENT_REVIEW.json`, loop 15, `HALT_LOOP_CAP`, committed 2026-08-05, `schema_version: 4`) fails `validate-artifact.py --mode strict` with **10 issues**: 3 × G46 (`finding_family`/`effort`/`repair_revalidation` required; gate landed 2026-08-18) and 7 × G43 (convergence-pass records owed; landed 2026-08-06). Both gates added required v4 fields without a bump or default-fill — the pattern `output-format-migrations.md` itself forbids by example (v2→v3 bumped *and* shipped a default-fill table). `skill_rev`, the field designed to scope rules to rulesets, is **null on this artifact**, so ruleset-scoping has no signal for existing history. The correct pattern ships one gate over: G19 is deliberately type-only, and this week's isolation fields used optional-with-shape-gating for exactly this reason.

**This blocks the loop-path P2's remedy.** `validate-artifact.py` cannot safely be wired into the loop or run over `REVIEW_HISTORY.json` until an old artifact can be judged by the rules in force when it was emitted — enforcement-by-hook inherits this problem on any repo with pre-existing artifacts.

**Corroboration found during this validation, free of charge:** the same artifact also trips the report-only transition checker — `[transition-violation HALT_LOOP_CAP→CONTINUE loop=10->11]` — so the illegal-transition P2 above now has a real-data instance in the repo's own history, not just a fixture.

### [I2] `implementation_review.rounds` is specified and never read (backlog row 33)

`output-format-json.md:440` specifies `rounds` as an int counting reviewer invocations; `grep '"rounds"' scripts/` returns zero, and both BenchHype production loops emitted `null` unchallenged. Blocked on a decision (any int? `{1,2}`? coupled to conditional re-spawn?), not on effort.

### [I3] `source_rev` is ambiguous mid-loop, and `findings_carried_from_prior_loops` is emitted but specified nowhere (backlog row 34)

Re-verified: `source_rev` is defined twice as "HEAD sha of the analyzed source tree at emit time" (`output-format-json.md:126,193`) — *analyzed source* and *at emit time* diverge when Step 3 commits mid-loop, and two consecutive production loops read it differently. `findings_carried_from_prior_loops[]` is emitted by real runs and appears in zero reference files.

### [I4] The paired-arm harness does not record grading spend, against the ledger's own rule

Sweep #3 recorded arm dispatch per pair (27.9M context tokens) but grading spend for rungs 2–4 was never committed per call, so the study's total is not reconstructible — with grading projected at ~57 % of cost, **the majority of the sweep's spend is unmeasured**. `paired_arm_record_grades.py` still records no usage at HEAD. Companion observations from the same closed run, recorded in the ledger and still open: four arithmetically impossible usage records (classified incomplete-usage, arm-balanced), grader agreement of 1/58 on assertions but 1/14 on tiers (the fragility is the tier roll-up rule), and 7+ graders independently inventing the same unschema'd `outside_spec` field (a spec gap deferred to the next preregistration by design).

### Adjudicated, recorded here so the disposition is findable

- **Row 35, `repair_revalidation` unknown keys** — accepted debt with a written reopening trigger (unknown keys shown to *mislead audit interpretation*); deliberately not re-flagged.
- **Row 3 residual** — both dispatch-boundary selftests *enumerate* their sites (4 G14, 3 redaction), so a fifth boundary would carry neither hard rule and fail no test. Recorded closure: a discovery tripwire on prompt-bearing files when the next boundary is added.
- **Ledger, phantom-signal generalization** — the bare-model-id class got its class guard (`b2b96ef`); the phantom-detection-signal class (`OPENCODE_SESSION`, an env var opencode never set, degrading silently into a gate-approved fallback) has no equivalent guard yet.
- **The June research doc's program is almost fully adjudicated by later work:** change-coupling shipped as candidate evidence (`audit_cochange.py`), the context-sufficiency cap shipped as prose (measured: over-claim 2/5 → 0/5), the domain-integrity lens was parked on a measured recall lift of 0 (bare rubric 6/6), expert panels shipped as the v5 certification stack and are parked (ponytail item 1 above), and benchmark-first became the principal corpus plus the paired-arm study (Decision 3: retargeting not licensed). Two requirements were **never built and never formally adjudicated**: the Serious+ grounded `change_scenario` requirement and the minimal `tradeoff_analysis` requirement — `git log -S` shows no commit ever introduced either field. Given the judgment-lever program's measured zero recall lift, non-adoption is evidence-consistent; it is recorded here so it reads as a decision rather than an omission.

## Priority summary

- **P1:** pre-existing dirty edits can be mistaken for loop-owned paths and overwritten on rejection.
- **P1:** untracked files can bypass both implementation review and rollback.
- **P1:** strict validation accepts unsupported 9.5 residual claims.
- **P1:** terminal success does not require independent reviewer/challenger execution.
- **P1:** report-only G17 permits approved deepening changes without interface-test evidence.
- **P2:** v3/v4/v5 emission instructions conflict and G29 is not implemented.
- **P2:** eight fixtures can pass for the wrong reason.
- **P2:** illegal terminal transitions are report-only.
- **P2:** the loop is instructed to run hard gates but never to run the module implementing 27 of them; measured 0/2 in production.
- **P2 (inherited, [I1]):** G43/G46 required fields with no version bump retroactively invalidate committed artifacts — the repo's own loop-15 artifact fails strict with 10 issues, and this blocks wiring the validator into the loop.
- **Inherited, smaller ([I2]–[I4]):** `rounds` specified but read by nothing; `source_rev` ambiguous mid-loop and `findings_carried_from_prior_loops` specified nowhere; paired-arm grading spend unrecorded (majority of sweep #3's cost unmeasured).
- **Test gap:** `_canon.py` is the enum single-source-of-truth for every validator; its 16 `sys.exit(2)` paths are unreachable from the 62-selftest suite because all 29 call sites pass the real canon.
- **Simplification (behaviour-preserving):** `load_canon` repeats one idiom 20× with ten double-spelled paths (−91 lines, proven equivalent); `_load_validator` is copy-pasted into 14 files; the G39–G42 selftest driver is duplicated and its vacuity guards are already 3-of-4; `_check_replication` is duplicated across two baseline selftests and has diverged by four checks.

No source changes were made as part of any of these passes; this document is the only repository change, now committed in its own docs commits so the revalidation lands as a reviewable diff. The D1 equivalence and mutation harnesses were session-scratchpad scripts and are **not committed**; they are lost when that session ends. They are the only code that has ever executed `_canon.py`'s 16 error paths. Re-creating them as `scripts/_canon_selftest.py` is **D5** — worth doing on its own merits even if D1 is declined, and cheapest to do before the harness is gone.
