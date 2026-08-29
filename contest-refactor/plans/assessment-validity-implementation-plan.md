# Contest-Refactor Assessment Validity — Implementation Plan

**Status:** Final. Two peer-review passes, both applied in full. The plan itself
went five rounds with codex/gpt-5.6-sol (blocking 10 → 8 → 6 → 4 → 3); the ten
decisions in §1 then went four rounds with opencode/glm-5.3 (D1–D9 accepted and
stable across three consecutive rounds; D10 revised each round). A fifth decision
round timed out twice with no output and was abandoned, so D10's final state is
reviewed through round 4 and confirmed by nothing later. Not started;
implementation is gated on Wave 0's approval step.

**Spec:** [`assessment-validity-improvement-spec.md`](assessment-validity-improvement-spec.md)
(1,636 lines; opencode/glm-5.3 APPROVED R3, codex/gpt-5.6-sol APPROVED R10)

**Research basis:**
[`docs/contest-refactor-assessment-validity-research-2026-08-28.md`](../../docs/contest-refactor-assessment-validity-research-2026-08-28.md)

**Revision baselines.** `b2af9a6` is the **pre-Wave-0 baseline** that W0-T1
verifies. The **implementation base** is `HEAD` immediately after the approved
Wave-0 commit; because a commit cannot contain its own SHA, it is recorded
outside that commit by tagging it `assessment-v6-base`. Every later wave asserts
its parent against the previous wave's commit. Only unexpected divergence forces
re-review; the plan's own authorized commits do not.

## Scope

Schema version 6 `assessment` envelope, gates G51/G52, one canon file, one
validator subsystem, nine fixture pairs, one self-test, and the reference edits
the spec's change map names.

**Beyond the spec's change map** — each forced by a verified defect, each written
into the spec by Wave 0 before any code lands:

| Addition | Why it is unavoidable |
| --- | --- |
| G29 schema-version admission (`_artifact_review_contract.py`, `_panel_capability.py`, `canon/panel-certification.toml`) | Without it, no v6 artifact passes validation at all — D5 |
| Sub-rule diagnostic pinning (`fixture.toml`, `validate-fixtures.py`) | Existing attribution is gate-grain; G51 alone carries ~15 sub-rules — D7 |
| `scripts/_assessment_render.py` | G52 demands exact string equality with rendered output; two implementations would drift — D2 |
| Bound-read v6 capability lookup (`_panel_capability.py`) | Verified: the lookup reads the LIVE manifest, so identical `skill_rev`s can be validated under different admission regimes — D10 |

---

## How to read this

Every task carries: **ID**, **size** (S ≈ under an hour, M ≈ half a day,
L ≈ a day or more), **Files** (exact paths, or `none`), **Steps**, **Done-when**
(a check runnable at that task's completion, naming a checked-in case — never a
scratch script, never an artifact a later task produces), and **Depends on**
(task IDs only).

**Waves execute strictly in order and commit atomically.** Parallelism exists
only *within* a wave. Every wave's commit changes at least one file.

---

## 0. Standing rules

1. **Work on `main`.** No branches (repo convention, reaffirmed 2026-06-30).
2. **One commit per wave**, Conventional Commits, `feat(contest-refactor):` with
   the EVAL delta when a score shifts. Rollback granularity is the wave.
3. **Each wave starts by asserting its parent** is the previous wave's commit
   (the first asserts the `assessment-v6-base` tag) and that the worktree is
   clean. A mismatch stops the plan for re-review.
4. **An artifact's `skill_rev` must name a COMMITTED revision that already
   contains everything the artifact depends on.** This is why capability and
   emission behavior commit in a wave before the run that exercises them, and
   why fixture artifacts bind the Wave-A commit (see R1-T12).
5. **Verification cadence:** focused checks during a wave; **§7's full battery
   before every wave commit**, never a subset. The battery's *scope* is
   non-negotiable — every self-test, not the ones a change appears to touch.
6. **Ruff pinned at `0.15.6`.** `ruff check --fix .` then `ruff format .` before
   every commit. Never hand-edit a vendored `_common/` mirror.
7. **Module size:** the validator subsystem targets under the 600-line soft
   warning per file and splits along cohesive seams before the 800-line hard
   cap. No waiver; no module names pre-committed.
8. **Prose edits run the writing-for-agents checks** (context pointers,
   co-location, no-op detection) in addition to `eval-skill.py`.
9. **Token-budget ceilings** are paid in the same commit as the prose that
   spends them, dated and sized against the new measured actual.
10. **No live-path claims.** G51/G52 close their gaps at the validator level.
    Production-loop invocation is the register's open Tier-3 decision, out of
    scope.
11. **Trust ceiling stated, not implied.** Every task touching the attested
    wrapper states, in code comment and prose, that it gives host-local
    consistency evidence against a forgetting or mis-reporting loop — never
    tamper resistance against a same-privilege forger (G47's Tier-1 model).
12. **The 2026-08-26 stop decision binds.** No new pack harvesting, no
    prose-clause measurement.

---

## 1. Decision record

Ten normative outcomes awaiting user sign-off — **not implementation latitude**.
Wave 0 writes the approved set into the spec's change map and acceptance
criteria before Wave A starts.

| ID | Question | Decision | Blocks |
| --- | --- | --- | --- |
| D1 | Where the `validation` execution-evidence entry lives | At v6, `loop_result.execution_evidence` becomes a keyed map `{"build": entry\|null, "validation": entry\|null}`; G47 reads flat for v≤5, keyed for v6 | R1-T5, R1-T10 |
| D2 | Who owns scope-line rendering | `scripts/_assessment_render.py`, a pure derivation module importing neither the validator nor the renderer; both import it | R1-T8, R2-T2 |
| D3 | v1 measurement registry | Exactly `score_mean_abs_gap` (points, 0–10) and `weighted_kappa` (coefficient, −1–1), both threshold-free | R1-T1 |
| D4 | How `_canon.py` exposes the new file | `canon.extra["assessment_model"]` behind a typed accessor, fail-closed at load | R1-T1 |
| D5 | G29 admission for v6 | R1-T2 ships the mechanism (a `v6` capability outcome, G29 mapping `{v4:4, v5:5, v6:6}`) **and records the one manifest entry** for the reserved fixture pair (D9). The corpus lands later and binds the Wave-A commit. Production pairs derive v4 until R2-T1 | R1-T2, R1-T12 |
| D6 | Wrapper `--input`/child-operand binding | The child command carries exactly one literal `{input}` token, which the wrapper substitutes; zero or two occurrences is a pre-spawn usage error | R1-T10 |
| D7 | Fixture diagnostic attribution | `expected_diagnostic` in `fixture.toml`, **mandatory** — gate-keyed for any fixture citing G51/G52 whenever authored, plus a cohort rule covering every fixture this change adds whatever it cites. Corpus-level accounting covers every rule this change adds or modifies | R1-T12 |
| D8 | Unverifiable source references | Verification failure **and** verification unavailability both prevent `valid`. BLIND is a diagnostic annotation naming the environmental cause, never a pass | R1-T6 |
| D9 | The reserved fixture identity | Provider `opencode` with both `*_model_source: "user_flag"` and a reserved model literal — legal under G19 (a known provider; `user_flag` lifts the default-equality constraint) and unused by the corpus | R1-T12 |
| D10 | How admission state binds to an artifact | **Excluded** from `rule_set_sha256` (the manifest records environment capability, not assessment policy — including it would let a routine admission edit perturb every earlier fixture's digest), **and** the v6 capability lookup becomes a **bound read at the artifact's `skill_rev`**, live read retained for v≤5. No new provenance field; admission becomes reproducible from the artifact's own bindings | R1-T1, R1-T2, R1-T11, R1-T12, R2-T1 |

**D1, verified:** the spec's digest recipe nulls `execution_evidence.validation`,
but `execution_evidence` is today a single flat object at
`loop_result.execution_evidence` (`references/output-format-json.md:447`), so
that path names nothing yet; only two fixtures hold a non-null value, both v4.

**D5, verified:** `check_g29_schema_version` requires `schema_version` to EQUAL a
capability-derived version; `_panel_capability.emit_check` returns only `v4` or
`v5`; the manifest ships zero entries, so every profile derives `4`. Existing v5
fixtures escape only because they carry no `skill_rev` and classify `LEGACY`; a
v6 artifact cannot, since the spec requires a well-formed `skill_rev`. **The spec
needs a correction:** its Release-1 acceptance says v5 emission is the default,
but the capability-derived default is v4 and v5 is unreachable without an entry
that does not exist.

**D8:** the **gate** may report BLIND to tell an operator why verification could
not run; the **artifact** can never derive `valid` when a required reference went
unverified, for any reason. Fixtures avoid the situation by using `skill_source:`
and artifact-local references, as the spec directs.

**D9, verified — and the guard is admission scope, not the label.** The corpus
holds 102 fixture directories and 101 artifacts (`bootstrap-repo` has no
`CURRENT_REVIEW.json`), and every one of those 101 uses provider `claude_code`,
so the reserved pair collides with nothing. An earlier draft claimed G47 linkage
was the guard; that is wrong, because most fixtures carry null execution evidence
and linkage checks nothing there. **The actual guard is that the reserved
identity is admitted to nothing of production value**, plus the in-band
`evidence` pointer on its manifest entry and a model literal that is
unmistakably non-production. A test-time manifest overlay was considered and
rejected: it exercises a path production never uses and leaves admission
unauditable from the repository alone.

**D10, two verified facts that redrew the question.** (1) `skill_rev` DOES cover
the manifest — it is a git SHA resolved in the skill's own repository, which
contains `canon/panel-certification.toml`. (2) **But validation never reads the
bound copy:** `_panel_capability.load_manifest` reads
`(root or _DEFAULT_ROOT) / "canon" / "panel-certification.toml"` from the live
working tree. So the manifest is bound and the check ignores the binding — two
artifacts with identical `skill_rev` can be validated under different admission
regimes, and post-rollback replay cannot distinguish "was admitted then" from
"never admitted". A separate `capability_manifest_sha256` field was considered
and rejected: computed live it reintroduces the digest instability that ruled out
bundling the manifest, and computed at `skill_rev` it merely restates a binding
that already exists. The bound read closes it with no new field.

**Two residuals, recorded rather than left implicit.** (i) Under D10 the v≤5
admission path intentionally still tracks the live manifest; this is recorded in
canon beside the exclusion rationale so a future v7 does not inherit the live
read by silence. (ii) The **emitter** must read live — the revision it will bind
does not exist yet at emission — while validators bound-read. A manifest change
inside the emission-to-commit window that *alters this pair's derivation*
surfaces as a G29 mismatch; one that does not is irrelevant to this artifact.
(Universal detection is NOT claimed.)

**D10 ordering — entry first, and this reverses an earlier reviewer.** The
manifest entry lands **with the canon file in Wave A**; the corpus lands in
Wave D and binds the Wave-A commit. This rests on `skill_rev` binding the
*ruleset*, not the test data, so the bound commit need not contain the corpus.
The alternative — entry and corpus together, with a follow-up commit rewriting
the fixtures' `skill_rev` — requires a transiently non-validating commit, which
collides with standing rule 5. **A codex round-3 finding had moved the entry into
the corpus task** so that no entry could cite a missing corpus; under the bound
read that placement makes admission structurally impossible, so the ordering is
decided here on merit and the audit invariant is rescoped rather than abandoned:
**"no manifest entry cites a corpus that does not exist" is enforced at release
tags and `HEAD` by the release acceptance battery resolving every entry's
`evidence` pointer, and intermediate wave commits are declared explicitly
non-replayable for that one check.**

---

## 2. Wave 0 — preflight and approval

**W0-T1 — Baseline preflight** · S
Files: none.
Steps: confirm `git rev-parse HEAD` = `b2af9a6`; branch `main`; worktree clean or
every deviation understood; `ruff --version` = 0.15.6; §7's battery exits 0 at
baseline expectations (80 self-tests, 102 fixtures, 26 gold-corpus packs,
`validate-repo` emitting only its OK line, `eval-skill` at `Warn: 3 / Fail: 0`);
confirm D9's reserved pair passes G19; confirm the tag `assessment-v6-base` is
absent, or already points at the intended commit — **never force-move it**.
Done-when: every assertion holds and the battery exits 0. Any mismatch stops the
plan for re-review.
Depends on: —

**W0-T2 — Decision record into the spec** · S
Files: `contest-refactor/plans/assessment-validity-improvement-spec.md`.
Steps: write the approved D1–D10 outcomes into the spec — change map (now four
beyond-map items), Pre-handoff section (D1 shape and its single serialization
owner, D6 token mechanics), Assessment records section (D8 semantics),
provenance section (D10's bundle exclusion, the bound read, and both recorded
residuals), Fixtures section (D7's mandatory pin, D9 identity and its
admission-scope guard). **Amend the false acceptance text**: the spec says
"version 5 emission remains the observable default", which is untrue against a
zero-entry manifest — replace it with the real invariant, *production pairs
derive v4, the reserved fixture pair derives v6, no pair derives v5* — and record
the doubly-dormant v5 capability branch as acknowledged pre-existing debt, not
extended by this work. Leaving the text would push a later acceptance run toward
adding a v5 entry to make it true, contradicting D5. Reconcile every acceptance
criterion the delta touches.
Done-when: the spec contains no statement contradicted by D1–D10;
`validate-repo` green; **the user has approved the delta**; the commit is tagged
`assessment-v6-base`. Implementation does not begin before that approval.
Depends on: W0-T1

---

## 3. Release 1 — semantics, validator, fixtures

Production emission stays at the capability-derived v4 throughout.

### Wave A — Canon, loader, gates, fingerprint

**R1-T1 — `canon/assessment-model.toml` and its loader** · L
Files: `contest-refactor/canon/assessment-model.toml` (new), `scripts/_canon.py`,
`scripts/_canon_selftest.py`.
Steps: write the 24 closed vocabularies; the per-object FIELD TABLE for every
shape the spec enumerates, with the per-validity-variant requiredness column; the
profile declaration (nine construct decisions, six `(construct, dimension)`
coverage keys with criticality, required logical reports, report→claim mapping,
declared-fixed constructs, mechanism table, completion label and scope-line
template); the four claim templates and required excluded-claim identifiers; the
namespace resolution table; the measurement registry (D3); the
scorecard↔residual mapping; the `hotspot_scan.status` mapping; and the
`rule_set_sha256` bundle membership list, which per D10 **excludes
`panel-certification.toml` with its rationale stated in the file, beside a note
that v≤5 admission intentionally still tracks the live manifest** so a future v7
does not inherit the live read by silence. Then load it per D4 with fail-closed
shape validation (missing table, unknown vocabulary reference, malformed field
entry → exit 2). The measurement registry ships D3's two threshold-free
measures; because that leaves the **threshold mechanism** unexercised, a
self-test proves the threshold path against a **synthetic, non-canon
registration** — the mechanism is proven without shipping a dormant canon
value.
Done-when: `python3 -B scripts/_canon_selftest.py` exits 0 and asserts every
spec-named vocabulary is present exactly once, every namespace has a resolution
row, every mechanism carries all five attributes, and the bundle list excludes
`panel-certification.toml`; each of three corruption cases exits 2 with its own
named error.
Depends on: W0-T2

**R1-T2 — Gate registration and the G29 v6 mechanism** · M
Files: `canon/validation-gates.toml`, `scripts/_validate_gates_selftest.py`,
`scripts/_panel_capability.py`, `scripts/_artifact_review_contract.py`,
`scripts/_schema_compat_selftest.py`, `canon/panel-certification.toml`.
Steps: register G51 and G52 with `schema_version >= 6` scope. Add the `v6`
outcome to `emit_check` under the existing default-deny manifest shape and map
G29's required version `{v4:4, v5:5, v6:6}`. Make the v6 capability lookup a
**bound read at the artifact's `skill_rev`** (git-object read, the same model
R1-T6's resolvers use), keeping the live read for v≤5 — dispatch is keyed on
declared version and is **pair-agnostic**. An unresolvable `skill_rev` or a
non-git environment is **fail-closed deny with an operator signal
distinguishable from a plain derivation mismatch**, never a silent fall back to
the live read. **Record the one manifest entry** for D9's reserved pair here,
per D10's entry-first ordering; its `evidence` pointer names the corpus R1-T12
will add, and dangles until then by design.
Done-when: `validate-repo.py` OK (its `check_gate_range_freshness` stays green);
`--gates G51,G52` accepted by `_resolve_gates`; checked-in cases prove the
reserved pair derives v6 while every unlisted pair derives v4, and that removing
the single entry restores v4 everywhere; all 102 existing fixtures produce
byte-identical results.
Depends on: R1-T1

**R1-T3 — Fingerprint v6 payload** · S
Files: `scripts/candidate_fingerprint.py`.
Steps: version-gate `_architecture_payload` so v≤5 stays byte-identical and v6
adds profile id+version, stable candidate SCOPE only (canon coverage keys and
deliberate exclusions with bases), construct projections, and canonical
residuals. Run-result statuses, failure references, claim ceiling, and validity
stay out.
Done-when: the existing v5 assertions pass untouched; a new v6 case changes the
fingerprint for each enumerated payload field and leaves it unchanged across a
transient pre-applicability failure.
Depends on: R1-T1

**R1-T4 — Repo validator** · S
Files: `scripts/validate-repo.py`.
Steps: canon/reference consistency for the new canon file; reject unauthorized
certificate/aggregate vocabulary; check the mechanism table's role, typed cost
ceiling, enforcement, effort, and burden entries.
Done-when: `validate-repo.py` OK; a checked-in case proves a canon edit dropping
a mechanism's cost ceiling fails with a named error.
Depends on: R1-T1

### Wave B — Validator (strictly serial: one shared subsystem)

Every focused check in Waves B and C runs **gate-scoped** (`--gates G51,G52`):
no v6 manifest entry exists until R1-T12, so an unscoped strict run would fail on
`G29-version-equality` before reaching the gate under test. Full-strict,
G29-inclusive verification happens in R1-T12.

**R1-T5 — G51 core: shape, default-deny, derived validity** · L
Files: `scripts/_artifact_assessment.py` (new),
`scripts/_assessment_model_selftest.py` (new — the self-test count becomes 81
here).
Steps: field-table-driven shape checks with default-deny on unknown keys; the
no-copy rule (envelope re-declaring `source_rev`, `candidate_fingerprint`,
`skill_rev`, `provider`, or `model` → reject; absent or malformed enclosing
binding → `invalid`); provenance digest binding with `fields`-matched structured
limitations; bundle-manifest digest recomputation (NFC UTF-8 path, tab, 64-hex,
`\n`, bytewise-sorted) over D10's membership list; derived-validity recomputation
rejecting emitter disagreement; per-validity-variant requiredness; D1's keyed
`execution_evidence` shape at v6. The "null `execution_evidence.validation`,
canonicalize, hash" operation gets **one shared implementation** used by both the
validator and R1-T10's wrapper — two implementations that null or canonicalize
differently would compare incomparable bytes. Migration parity is asserted, not
assumed: the keyed `build` entry is policed by exactly the rules the flat v≤5
object carried, and a v6 artifact presenting the flat shape fails shape
validation; both get flag fixtures in R1-T12, because a shape migration is where
a new version silently escapes a rule the old one enforced.
Done-when: a checked-in valid envelope passes gate-scoped; each of the eight
`invalid` triggers in the spec's rule 2 fires its own `G51-<subrule>` diagnostic
(`_gate_satisfies` already treats sub-rule ids as satisfying their gate).
Depends on: R1-T1

**R1-T6 — G51 references and resolvers** · M
Files: `scripts/_artifact_assessment.py`, `scripts/_assessment_model_selftest.py`.
Steps: reference grammar `<namespace>:<id>`; artifact-local resolution per the
canon table; `finding:<stable_id>` against top-level `findings[]`; split
resolvers with a fully defined execution model:

- **Roots.** `target_source:` resolves in the repository under validation — the
  git toplevel of `artifact_dir`, obtained as `_artifact_attestation._toplevel`
  obtains it, which means **the artifact directory must lie inside the target
  worktree** (R2-T3 guarantees this for the real run). `skill_source:` resolves
  in the skill's own repository, the toplevel of `SKILL_ROOT`. Computed
  independently, never substituted.
- **Read model.** Git-object reads at the bound revision
  (`git cat-file -p <rev>:<path>`), never the working tree — the tree may have
  moved since the artifact was written.
- **Paths.** Repo-relative, forward slashes, NFC-normalized UTF-8; a leading
  `/`, a drive letter, or any surviving `..` is a grammar failure. A path whose
  git object mode is a symlink (120000) is rejected: evidence names a real file.
- **Lines.** 1-based inclusive; split on `\n`; a final line without a trailing
  newline counts. Requires `1 <= start <= end <= line_count`.
- **Failure and unavailability.** Per D8 — both prevent `valid`; BLIND annotates
  the environmental cause (git missing, not a work tree) without ever passing.
- **Exemption.** A `closed_for_audit` residual is exempt, covering its `source`
  and retired `scorecard:` references.

Done-when: each namespace has a passing and a failing checked-in case with
distinct diagnostics; a `target_source:` path present in the skill repository but
absent from the target repository fails, proving the roots are not shared; a
symlink path, an out-of-range span, and a `..` path each fail on their own
diagnostic; and a self-test forcing a git-unavailable environment on an artifact
carrying a required reference asserts **both outcomes together** — BLIND at the
gate, `invalid` for the artifact — since that combination is the whole point of
D8 and is otherwise unproven.
Depends on: R1-T5

**R1-T7 — G51 records** · L
Files: `scripts/_artifact_assessment.py`, `scripts/_assessment_model_selftest.py`.
Steps: coverage partition integrity over recorded ledger sets, declared key set,
missing-cause references, the applicability↔coverage iff invariant; measurement
registry equality, invalidate-don't-clamp, `attempted >= sample_size` and
`attempted - sample_size ==` linked-failure count; claim-ceiling shape on
load-bearing records; confidence/uncertainty shape and separation; unique IDs;
residual derived `disposition`/`lifecycle` recomputation and open-residual
scorecard equality; projection presence, tuple uniqueness, no-restated-severity,
role subset, `defer` → `residual_ref`; pipeline-failure shape with stage-scoped
cause membership and invalidation consistency; cost shape with per-quantity
`sources` and null-with-limitation; the validity↔G43 no-counter-advance
cross-check; v6 fingerprint recomputation against R1-T3's payload.
Done-when: every bullet in the spec's G51 list has a firing checked-in case with
its own diagnostic ID.
Depends on: R1-T6, R1-T3

**R1-T8 — G52 eligibility** · M
Files: `scripts/_artifact_assessment.py`, `scripts/_assessment_render.py` (new),
`scripts/_assessment_model_selftest.py`.
Steps: one applicability decision per profile construct on an assessment that
ran; declared-fixed constructs match canon; required coverage dimensions and
criticality; invalidity on unknown applicability or missing critical coverage;
limited-coverage claim narrowing; envelope claim-template conformance with strict
precedence and the required excluded set; assurance delegation boundaries
(`satisfied` unreachable in v6); residual staleness; handoff coupling via exact
recomputed scope-line equality using `_assessment_render.py`; the
prohibited-claim scan with the disclaimer exemption; the pre-handoff
validation-entry rule. Add the **pre-applicability interaction case** here — a
failure before applicability leaves fixed constructs at their canon decisions,
undecided constructs `unknown`, and remaining coverage `missing` with failure
refs, deriving `invalid` while every G52 invariant holds simultaneously. The
spec's self-test list places this in the self-test rather than the fixture
corpus, which is why the corpus grows by 18 and not 19.
Done-when: each bullet fires its own diagnostic; the limited-coverage case stays
`valid` while the unqualified profile-satisfied sentence is rejected; the
interaction case derives `invalid` with full G52 green; a checked-in import check
asserts `_assessment_render.py` imports neither the validator nor
`render_report.py`, and that those two never import each other (both importing
the render module is the intended shape).
Depends on: R1-T7

### Wave C — Integration surfaces (serial)

**R1-T9 — Dispatcher and `--pre-linkage`** · S
Files: `scripts/validate-artifact.py`.
Steps: wire the two gate entry points into `run_checks`; add `--pre-linkage`,
skipping **exactly** the linkage-presence check; ordinary strict mode always
rejects a null validation entry on a completion handoff.
Done-when: gate-scoped, `--pre-linkage --gates G51,G52` on a null-entry artifact
exits 0 while `--gates G51,G52` alone exits 1 naming G52; a before/after run over
the whole fixture corpus shows `--pre-linkage` changes no other diagnostic.
Depends on: R1-T8

**R1-T10 — Attested wrapper input digest** · M
Files: `scripts/attested_run.py`, `scripts/_artifact_attestation.py`,
`scripts/_attested_run_selftest.py`, `scripts/_g47_selftest.py`.
Steps: add `--input <path>`; require the child command to carry exactly one
literal `{input}` token, which the wrapper substitutes with the resolved path
(D6) — zero or two occurrences is a usage error **before spawn** (exit 2, nothing
recorded), since the run has not happened and there is nothing to degrade.
Substitution is **argv-token-level, never string interpolation into a shell
command** (a spaced path split by a shell is exactly the attest-A-validate-B
failure); the path is canonical and absolute **before both** hashing and
substitution; and the ledger stores the **substituted** command, not the
template, so the record itself proves which path the child received. Parse
the artifact, null `execution_evidence.validation` (D1), serialize with
`candidate_fingerprint.py`'s canonical encoder, hash before spawn and after exit,
treating a mismatch as degraded under the existing mid-run-edit rule; add
`input_sha256` (`sha256:<64 hex>`) to the ledger record, **required only for v6
keyed validation evidence**; extend G47's linkage validation accordingly; state
the Tier-1 trust ceiling in the module docstring per §0.11.
Done-when: checked-in cases prove matching, mismatched, and null-entry inputs; a
mid-run artifact edit degrades; zero-token and two-token child commands exit 2
with nothing appended to the ledger; a v≤5 ledger record lacking `input_sha256`
still validates.
Depends on: R1-T9

### Wave D — Proof

**R1-T11 — Structural guarantees** · M
Files: `scripts/_assessment_model_selftest.py`.
Per-rule cases ship with the rules that introduce them (Wave B). This task adds
the three guarantees that make those cases trustworthy:

| # | Guarantee | Check |
| --- | --- | --- |
| 1 | Handler-kind coverage | Every rule KIND in canon has a handler; every registered handler is reachable from canon. A generic interpreter has no second value list to compare against, so coverage is asserted over kinds, not values |
| 2 | Vocabulary and kind mutation | Per vocabulary: one accepted member, one rejected unknown. Per rule KIND: one mutation (drop a required field, widen a scale, remove a member) that must flip a checked-in case from pass to fail |
| 3 | Rule-to-diagnostic matrix | **Every rule this change adds or modifies** — G51/G52 checklist items, G29's v6 mapping, the bound read's dispatch and fail-closed behavior, D1's shape rules — maps to a checked-in case AND the diagnostic ID it must produce, or is listed as an explicit coverage residual; an unaccounted rule fails |
| 4 | Bound-read dispatch is pair-agnostic | A **synthetic non-canon manifest** carrying a **non-reserved** pair whose entry exists at a bound revision but not in the live tree; the bound derivation must apply to it. Drives the real lookup function directly (so a path-keyed variant is caught) and exercises two divergent revisions **within one process** (so a cached manifest is caught) |

Guarantee 4 exists because no fixture can catch a dispatch cheat. The manifest's
only v6 entry is the reserved pair's, so the corpus's entire bound-versus-live
divergence space is that one pair — a lookup keyed on pair identity rather than
declared version behaves honestly on every corpus artifact while handing
production live-read admission the moment R2-T1 lands. Behavioral coverage is
bounded by the divergence space, and this one is degenerate by design, so the
proof is a synthetic-input self-test (the D3 pattern generalized).

Done-when: `python3 -B scripts/_assessment_model_selftest.py` exits 0 and prints
its assertion count; removing a handler fails guarantee 1; each per-kind mutation
fails guarantee 2; an unaccounted rule fails guarantee 3; a pair-keyed or
path-keyed dispatch fails guarantee 4. One case the accounting must show is
present rather than residual: **a declared-v6 artifact with a non-reserved pair
binding the entry commit derives v4 and is denied** — admission is required, not
merely declared.
Depends on: R1-T8, R1-T4, R1-T10

**R1-T12 — Fixture pairs, diagnostic pinning, capability entry** · L
Files: the 18 directories below under `contest-refactor/evals/fixtures/` (each:
`CURRENT_REVIEW.json`, `CURRENT_REVIEW.md`, `findings_registry.json`,
`REVIEW_HISTORY.json`, `REVIEW_HISTORY.md`, `fixture.toml`);
`scripts/validate-fixtures.py`; `scripts/_fixture_pairing_selftest.py`;
`scripts/_assessment_model_selftest.py`.

| Pair | Flag directory | Restraint directory |
| --- | --- | --- |
| envelope | `assessment-envelope-no-claim-ceiling` | `assessment-envelope-complete` |
| projection | `assessment-projection-duplicate-tuple` | `assessment-projection-two-distinct` |
| eligibility | `assessment-eligibility-missing-critical-coverage` | `assessment-eligibility-limited-narrowed` |
| completion language | `assessment-completion-certified-wording` | `assessment-completion-label-valid` |
| handoff coupling | `assessment-handoff-overclaims-coverage` | `assessment-handoff-scope-line-matches` |
| judgment invalidation | `assessment-measure-offscale-clamped` | `assessment-measure-offscale-invalid` |
| evidence reference | `assessment-evidence-ref-unresolvable` | `assessment-evidence-ref-resolving` |
| stale residual | `assessment-residual-open-dangling-source` | `assessment-residual-closed-for-audit` |
| pre-handoff evidence | `assessment-prehandoff-null-entry` | `assessment-prehandoff-linked-attested` |

Steps: implement D7 — `fixture.toml` gains an `expected_diagnostic` string and
`validate-fixtures.py` asserts a failing fixture's issues include that exact rule
id. It is **mandatory, two ways**: gate-keyed as the standing rule (any fixture
citing G51 or G52, whenever authored, is rejected without it) plus a cohort rule
covering **every fixture this change adds, whatever it cites** — which is what
catches the G29-citing denial fixtures below. Optionality was rejected: it
reproduces, opt-in, the silent under-attribution the field exists to prevent.
Existing gate-grain attribution (`_cross_check_expected_result` already requires
a negative fixture to fail for its cited gate) stays the floor, unchanged for the
102 existing fixtures, which cite neither new gate.

Build the nine pairs, each carrying D9's reserved identity and, per §0.4, a
`skill_rev` naming **the Wave-A commit** — the first committed revision
containing both `canon/assessment-model.toml` and the manifest entry that admits
them (D10 entry-first ordering). Because `panel-certification.toml` sits outside
the ruleset bundle, neither this wave nor R2-T1 perturbs the `rule_set_sha256`
these fixtures record. Add the end-to-end wrapper case, now able to end in an
ordinary full-strict G29-inclusive run.

**Two denial fixtures prove the read is actually bound**, covering the
degradation axis (guarantee 4 covers the dispatch axis):

- **Pre-entry revision denied** — a v6 artifact binding a revision earlier than
  the entry. Catches an always-live lookup and a fallback-when-nothing-found.
- **Unresolvable revision denied** — a v6 artifact carrying the reserved pair and
  a **fabricated, well-formed 40-hex `skill_rev` that resolves nowhere in any
  clone**, denied with the operator signal. This is the only case that catches
  fallback-on-error, because there the live read finds the entry and passes. A
  shallow-boundary SHA was rejected (it resolves in a full clone, so the denial
  arrives as a plain mismatch and the fixture fails its own signal assertion for
  the wrong reason); a malformed value was rejected (format validation rejects it
  before the lookup runs); a non-git *environment* is not expressible as a
  fixture and lives in R1-T11's environment-forcing self-test.
Done-when: `validate-fixtures.py` passes all 120 under the unmodified full
battery; every new flag fixture pins and fails on **its** diagnostic; changing
one pin makes that fixture fail; `_fixture_pairing_selftest.py` passes with no
new `pair_exception`; the 102 existing fixtures produce byte-identical results;
the end-to-end wrapper case passes full-strict; both denial fixtures fail on
their pinned diagnostic. **Manifest rollback check** (the entry lives in R1-T2,
so this is run by reverting that one line): removing it gives all 18 new
fixtures a `G29-version-equality` diagnostic
— the nine restraint fixtures flip pass→fail, the nine flag fixtures keep their
pinned G51/G52 diagnostic *and* gain G29 — with no other fixture's diagnostic set
changing, and no `rule_set_sha256` mismatch anywhere (the D10 proof).
Depends on: R1-T2, R1-T11

### Wave E — Prose and Release-1 acceptance

**R1-T13 — Reference and doc edits** · L
Files: `SKILL.md`; `references/output-format-json.md`,
`output-format-migrations.md`, `output-format-markdown.md`,
`output-format-state-schemas.md`, `method.md`, `method-critic.md`,
`architecture-rubric-scoring.md`, `validation.md`, `validation-sources.md`,
`halt-handoff.md`; `evals/README.md`; `docs/README.md`.
Steps: define v6 and the v5→v6 default-deny migration, with a version-by-version
compatibility statement — v3, v4, v5 read under their own declared version; the
D1 flat→keyed transition and the `input_sha256` requirement are v6-only and do
not reinterpret an older artifact; a lower declared version is never an escape
from a rule that version already carried, and this promise does not forbid a
deliberate, documented security correction to an older version's validation.
Document the four logical projections, the completion label, and the derived
scope line; distinguish internal `HALT_SUCCESS` from user-facing completion; mark
the scorecard advisory; document G51/G52 and their authorities; correct
`evals/README.md`'s gold-corpus count from the stale prose figure 25 to the
validator-observed 26 (the doc is stale, not the corpus); index the research
report.
Done-when: `eval-skill.py contest-refactor` reports `Fail: 0` and `Warn: 3` —
**unchanged from the measured baseline**, whose three warnings (SKILL.md token
count, the `tiktoken` import in `token-budget.py`, undocumented
`CONTEST_REFACTOR_HOME`) are pre-existing and out of scope; a fourth is a
regression. `token-budget.py --check` green with any ceiling bump dated and sized
in this commit; writing-for-agents checks clean on every touched file;
`check_reference_links_resolve` passes.
Depends on: R1-T12

**R1-T14 — Release-1 acceptance** · S
Files: `docs/contest-refactor-review-register.md` (records this work as
register-owned and its acceptance result — so the wave's commit is never empty).
Steps: run §7's battery at Release-1 expectations; confirm every new flag fixture
fails and every restraint fixture passes on its pinned diagnostic; confirm v5
fingerprint stability; confirm production pairs still derive v4.
Done-when: every Release-1-scoped spec acceptance criterion holds; battery exits
0; the register entry is written; Wave E commits.
Depends on: R1-T13

---

## 4. Release 2 — v6 emission

**Gate: Release-1 acceptance green.** There is no emitter program — the artifact
is written by the agent following `output-format-json.md` — so enabling v6
emission is a prose change plus one real run. The two waves exist because §0.4
requires the run to bind a committed revision that already contains the
capability entry and emission prose.

### Wave F — Capability and emission (commits before any run)

**R2-T1 — Production capability evidence and entry** · M
Files: `contest-refactor/evals/assessment-v6-preadmission/` (new: the
pre-admission artifact and its validation output);
`canon/panel-certification.toml`; `scripts/_schema_compat_selftest.py`;
`docs/contest-refactor-run-log.md`.
Steps: **record the chosen production (provider, model) pair in the run log
first.** Fixture-pair evidence proves the *mechanism*, not a production model's
capability, so produce provider-specific evidence: have the chosen pair emit a v6
artifact and validate it with `--gates G51,G52`, which exercises the envelope
while G29 still derives v4. This is not circular — the pre-admission check
deliberately excludes the one gate the entry unlocks. Only then record the
manifest entry naming that pair, with this evidence path and the recorded date.
If pre-admission fails, **retain the attempted artifact, its validation output,
and the chosen pair in the run log, then stop the release** — do not try
alternatives silently.
Done-when: the pre-admission artifact passes `--gates G51,G52` **before** the
entry exists; after the entry, a checked-in case proves the chosen pair derives
v6 while every unlisted pair derives v4; all 120 fixtures unchanged, with no
`rule_set_sha256` mismatch (D10); reverting the single entry restores v4.
Depends on: R1-T14

**R2-T2 — Emission and rendering prose** · M
Files: `references/method.md`, `references/output-format-json.md`,
`references/output-format-markdown.md`, `scripts/render_report.py`.
Steps: canonical-records-first construction order — build the assessment records,
then derive the scorecard projection and the residual docket from them, never the
reverse; the residual work docket
(`docs/audits/contest-refactor-residuals-<run_id>.md`) derives its rows from
canonical records with `lifecycle: "open"` and `disposition: "accepted"`;
`render_report.py` imports `_assessment_render.py` so the label and scope line it
writes into `halt_handoff` are the string G52 recomputes.
Done-when: a checked-in case asserts the rendered scope line and G52's
recomputation are byte-equal on the restraint fixture; eval-skill, token-budget,
and writing-for-agents green; battery exits 0; Wave F commits. (The docket is
agent-produced prose with no generator, so its row check belongs to R2-T3,
against a real docket.)
Depends on: R2-T1

### Wave G — The real run

**R2-T3 — One real v6 run** · L
Files: a run-log entry in `docs/contest-refactor-run-log.md`; artifacts under a
directory **inside the frozen target worktree** — R1-T6's `target_source:`
resolver derives its root from `artifact_dir`, so an artifact outside that
worktree resolves against the wrong repository; the run's residual docket.
Steps: freeze target repository and revision, provider and model (R2-T1's pair),
and environment before dispatch. The loop runs against **Wave F's commit**, which
is the `skill_rev` the emitted artifact binds (§0.4) — this is why capability and
emission committed first. Emit the v6 artifact; run pre-linkage validation
through `attested_run.py --input`; link the entry; run ordinary strict
validation.
Done-when: the artifact passes `--mode strict` end to end including handoff
coupling; its `skill_rev` equals Wave F's commit; the run's docket matches its
canonical open-accepted records row for row; all v3–v5 fixtures pass unchanged;
the v5 fingerprint fixture proves byte-stability; the linked run's `input_sha256`
equals the recomputed self-excluding digest; the run log records target,
revision, **the resolved target root**, provider, model, artifact paths, and
exact commands.
Depends on: R2-T2

**R2-T4 — Release-2 acceptance** · S
Files: `docs/contest-refactor-review-register.md`.
Steps: battery at Release-2 expectations; register and run-log updated.
Done-when: battery exits 0; Wave G commits.
Depends on: R2-T3

---

## 5. Release 3 — measurement only

**Gate: Release-2 acceptance green. Inside the 2026-08-26 stop decision.** Two
waves, because preregistration must be committed before any dispatch.

### Wave H — Preregistration (commits alone)

**R3-T1 — Preregistration** · M
Files: `docs/contest-refactor-assessment-measurement-prereg-<date>.md` (new),
referenced from `docs/contest-refactor-review-register.md`.
Steps: freeze before any dispatch — the harness
(`contest-refactor/evals/reviewer-cases/`, guarded by
`scripts/_reviewer_baseline_selftest.py`) and its exact invocation contract; the
case list and its source; repetitions per case; and the schedule: **a randomized
schedule requires a recorded seed; a deterministic counterbalanced schedule
requires the complete frozen order instead** — fixed arbitrary order records a
temporal confound rather than controlling it, and one-case-per-fresh-context
removes batch composition effects but not drift across a long run. Also freeze
exclusion rules; treatment of a missing or errored run (counted in `attempted`,
never silently dropped); per-run environment and model capture; the analysis
model; the decision rule; the stopping rule.
Done-when: the document is committed with its seed or frozen order recorded and
contains no field left to post-hoc judgment. Dispatch before this commit
invalidates the measurement.
Depends on: R2-T4

### Wave I — Results

**R3-T2 — Run** · L
Files: raw outputs at the exact path the prereg names.
Steps: execute the preregistered schedule, **one case per fresh context** — the
2026-08-26 harness measurement swung a control 5/5 → 2/5 on identical inputs from
batch composition and order alone.
Done-when: every prereg case has a recorded outcome or a recorded exclusion citing
a prereg rule; no case ran outside a fresh context; the executed order matches the
preregistered schedule.
Depends on: R3-T1

**R3-T3 — Record** · S
Files: measurement records at the prereg-named path;
`docs/contest-refactor-run-log.md`; `docs/contest-refactor-review-register.md`.
Steps: results as measurement records carrying `attempted` accounting, bound to
the prereg document.
Done-when: `attempted - sample_size` equals the count of recorded exclusions;
battery exits 0; Wave I commits. **No certification or aggregation is enabled by
this release.**
Depends on: R3-T2

---

## 6. Dependency DAG

Waves run in order and commit atomically; arrows show task order within that
constraint.

```text
W0-T1 → W0-T2 (USER APPROVAL, tagged assessment-v6-base)
Wave A ──→ R1-T1 ─┬→ R1-T2
                  ├→ R1-T3
                  └→ R1-T4
Wave B ──→ R1-T5 → R1-T6 → R1-T7 → R1-T8          (strictly serial)
Wave C ──→ R1-T9 → R1-T10                          (strictly serial)
Wave D ──→ R1-T11 → R1-T12
Wave E ──→ R1-T13 → R1-T14                         (prose + acceptance)
Wave F ──→ R2-T1 → R2-T2                           (capability + emission)
Wave G ──→ R2-T3 → R2-T4                           (real run + acceptance)
Wave H ──→ R3-T1                                   (commits alone)
Wave I ──→ R3-T2 → R3-T3
```

Cross-wave dependencies carried by wave order: `R1-T7` needs `R1-T3` (Wave A);
`R1-T11` needs `R1-T4` (Wave A) and `R1-T10` (Wave C); `R1-T12` needs `R1-T2`
(Wave A) and binds Wave A's commit; `R2-T3` binds Wave F's commit.

**Genuinely parallel:** `R1-T2`, `R1-T3`, and `R1-T4` after `R1-T1`, inside
Wave A. Nothing else.

---

## 7. The verification battery

Run before **every wave commit**, in full. Failures propagate — this block exits
nonzero if anything fails, and asserts counts rather than trusting a green log.

```bash
#!/usr/bin/env bash
# Standing verification battery. Exits 0 only if every check passed.
set -uo pipefail
cd /Users/Shared/git/agent-skills || exit 2
fail=0

n=0
for f in contest-refactor/scripts/_*_selftest.py; do
  n=$((n + 1))
  python3 -B "$f" >/dev/null 2>&1 || { echo "SELFTEST FAIL: $f"; fail=1; }
done
[ "$n" -eq "${EXPECT_SELFTESTS:-80}" ] || {
  echo "selftest count $n != ${EXPECT_SELFTESTS:-80}"; fail=1; }

run() { echo "--- $*"; "$@" || { echo "FAIL: $*"; fail=1; }; }
run python3 -B contest-refactor/scripts/validate-fixtures.py contest-refactor/evals/fixtures
run python3 -B contest-refactor/scripts/validate-gold-corpus.py contest-refactor/evals/gold-corpus
run python3 contest-refactor/scripts/token-budget.py --check
run ruff check contest-refactor/scripts
run ruff format --check contest-refactor/scripts
run git diff --check

# Direct validate-artifact.py CLI checks, gate-scoped. NOTE: no fixture passes an
# UNSCOPED strict run — mid-loop artifacts structurally fail gates like G18 by
# design, which is why --gates exists. Verified at b2af9a6: these two exit 0.
run python3 -B contest-refactor/scripts/validate-artifact.py \
  contest-refactor/evals/fixtures/g39-score-impact-valid --mode strict --gates G39 --quiet
run python3 -B contest-refactor/scripts/validate-artifact.py \
  contest-refactor/evals/fixtures/g43-clean-streak-fresh-target --mode strict --gates G43 --quiet
# From Wave D on (EXPECT_FIXTURES=120), the normative v6 restraint fixture too.
if [ "${EXPECT_FIXTURES:-102}" -eq 120 ]; then
  run python3 -B contest-refactor/scripts/validate-artifact.py \
    contest-refactor/evals/fixtures/assessment-envelope-complete \
    --mode strict --gates G51,G52 --quiet
fi

# validate-repo emits exactly one OK line at baseline; any other line is a new
# diagnostic, not noise.
repo_out=$(python3 -B contest-refactor/scripts/validate-repo.py 2>&1) || {
  echo "FAIL: validate-repo"; fail=1; }
echo "$repo_out"
[ "$repo_out" = "validate-repo: OK (all checks passed)" ] || {
  echo "validate-repo emitted unexpected output"; fail=1; }

# eval-skill: pin the warning COUNT. All three are pre-existing and unrelated to
# this work (SKILL.md token count, tiktoken import, CONTEST_REFACTOR_HOME).
eval_out=$(python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py contest-refactor 2>&1) || {
  echo "FAIL: eval-skill"; fail=1; }
printf '%s\n' "$eval_out" | tail -5
printf '%s\n' "$eval_out" | grep -q "Warn: ${EXPECT_EVAL_WARNINGS:-3}" || {
  echo "eval-skill warning count != ${EXPECT_EVAL_WARNINGS:-3}"; fail=1; }
printf '%s\n' "$eval_out" | grep -q "Fail: 0" || { echo "eval-skill has failures"; fail=1; }

fixtures=$(ls -1 contest-refactor/evals/fixtures | wc -l | tr -d ' ')
[ "$fixtures" -eq "${EXPECT_FIXTURES:-102}" ] || {
  echo "fixture count $fixtures != ${EXPECT_FIXTURES:-102}"; fail=1; }
packs=$(ls -1 contest-refactor/evals/gold-corpus | wc -l | tr -d ' ')
[ "$packs" -eq "${EXPECT_PACKS:-26}" ] || {
  echo "gold-corpus pack count $packs != ${EXPECT_PACKS:-26}"; fail=1; }

exit "$fail"
```

| Boundary | `EXPECT_SELFTESTS` | `EXPECT_FIXTURES` |
| --- | --- | --- |
| Baseline, Wave A commit | 80 | 102 |
| Wave B commit onward (`_assessment_model_selftest.py` lands in R1-T5) | 81 | 102 |
| Wave D commit onward | 81 | 120 |

`EXPECT_PACKS` stays 26 throughout. **Verified 2026-08-28 at `b2af9a6`:**
extracted verbatim from this document and executed — exit 0 on the clean tree,
with failure propagation separately proven (a failing command and a count
mismatch each force exit 1). Runtime ~3–5 minutes; run it past a 2-minute shell
ceiling.

---

## 8. Out of scope

Every deferral in the spec's Explicit deferrals section — certificate issuance, a
headline aggregate, `samples` calibration machinery, semantic
finding-deduplication, a new report renderer, additional analyzers, a separate
evidence store — plus any Tier-3 host hook or live-path enforcement claim. Adding
one requires a measured failure of this smaller design first.
