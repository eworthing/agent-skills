# Item 28 — Remediation Contract + Repair-Revalidation Record: Inventory + Design Note (2026-08-18)

## Verdict: small, real delta

Two of five candidate fields from Gap 26 are already covered (owning dimension, remediation
strategy — the second only partially, scoped too narrowly). One is genuinely absent and
cheap to add by copying a shape the skill already ships (`repair_revalidation`, modeled on
`risk_boundary_evidence`). One is genuinely absent and structurally new (`effort`). One
(chosen disposition) is absent and needs a new 3-value enum, but only for one finding family.
The essentiality ladder and disposition arrows are correctly identified by the source gap as
non-universal — this note's discriminated schema (§3) keeps them family-scoped and adds two
general fields. Section 4's collision check concludes `repair_revalidation` is a **fourth,
separate axis** from items 6/26/27's finding-assurance mechanisms, not a duplicate — different
subject (fix durability, not finding truth) and different pipeline stage (post-repair, not
pre-admission). Section 5 concludes center-audit's refactor-promotion test does not apply
as a gate, but the sharper finding is that **only one of its five conditions actually
inverts** — the other four are mandate-independent discipline this skill already satisfies in
substance. It also names one narrow, cheap, optional sibling check worth carrying forward.

**Revision note (same day, by the orchestrating session):** the first draft recorded
center-audit as unavailable and marked its enum semantics and promotion test "uncertain,
inferred." Both are vendored at `refs/competitors/contest-refactor/center-audit` (`b154fb0`);
sections 4 and 5 are now read from the source. This changed two substantive conclusions rather
than merely adding citations — the draft had `INVARIANT_DRIFTED`/`INVARIANT_REPLACED` as degrees
of *failure* when the source defines both as **successful** repairs whose invariant moved, and
it treated the promotion test as uniformly inapplicable. Two further source-backed items landed:
`drift_notes` must be conditionally required from the start, and a fifth `AUDIT_MOOT` outcome is
a known upstream gap this skill will hit routinely.

## Scope note

This is the design note only. No canon, schema, gate, or fixture changes ship in this pass —
per the item-28 backlog row's own framing ("begins with an inventory... adds only the missing
fields," `docs/review-skill-deep-dive-2026-08-17.md:1156`) and the assignment's scope
discipline. Every claim below about current skill behavior carries a `file:line` citation;
where I could not verify a claim against this repo or an available source, it is marked
**uncertain**, not asserted.

---

## 1. Inventory — what already exists

### G15 — Implementation review present

`references/validation.md:65`: when `loop_result` is present, `implementation_review` must
also be present with `verdict ∈ {approved, rejected}` (`conditional` is a mid-loop transient
that must resolve before commit). Run at Step 3 sub-step 8, after the Implementation Review
Pass writes the field (`SKILL.md:218`), before commit.

**Not mechanically enforced.** `scripts/validate-artifact.py` imports 20 check functions from
the `_artifact_*` modules (`scripts/validate-artifact.py:37-79`); none is named
`check_g15_*` or anything G15-shaped, and a repo-wide grep for `def check_g15` and `def
check_g17` returns nothing. G15 remains a manual checklist item the loop subagent runs at
Step 3 sub-step 8, same as most of G16 (see next).

### G16 — Registry consistency

`references/validation.md:66`: every emitted finding carries both `loop_local_id` and
`stable_id`; registry entries must agree with `findings[]`; every `entries[].stable_id` must
be unique.

**Partially mechanical.** Only the uniqueness sub-check is enforced in code:
`check_g16_registry_uniqueness` (`scripts/_artifact_core.py:369-392`) walks
`registry["entries"]` and flags a duplicate `stable_id`. It is imported and dispatched at
`scripts/validate-artifact.py:41,138`, and per the gate's own text, "the rest of G16 remains a
manual checklist" (`references/validation.md:66`). Run at Step 1 emit, Step 3 sub-step 8
(in-memory registry), and Step 3 sub-step 10 (on-disk registry) — `SKILL.md:218,229`.

### G17 — Indirect coverage citation

`references/validation.md:67`: when `loop_result.what_changed` contains a Deepening Keyword
(`collapsed | consolidated | merged | deepened | inlined | extracted | flattened`,
`references/output-format-json.md:441-446`) and the diff has no test-file changes,
`loop_result.interface_test_coverage_path` is required, with each entry non-empty on
`target_symbol`, `target_symbol_kind ∈ {new, existing_deepened}` (or a documented
`existing_<role>_interface` extension), and `distinguishes_no_op == true`
(`references/output-format-json.md:403-409`). The gate text is explicit about the division of
labor: "Reviewer's Check 2 verifies citation validity (cited assertion exists and exercises the
new code path); G17 verifies citation presence and structural shape at the artifact level"
(`references/validation.md:67`).

**Not mechanically enforced** — same grep result as G15; no `check_g17_*` function exists.
Manual checklist, run at Step 3 sub-step 8.

### Step 1 build verification — establishes a baseline, not a repair record

`SKILL.md:120`: "Run primary test/build command," first action of the Critic Phase, before any
structural finding is written. This is a **whole-repo, pre-refactor** ground-truth check, not
invariant-specific: on failure it re-runs once for a flake guard (`SKILL.md:121-127`), and on a
confirmed double-fail it writes a schema-valid minimal review — `Implementation credibility`
scored `1`, the other 8 dimensions carried forward flagged
`unverifiable_due_to_build_failure: true`, one Priority-1 backlog item "fix build"
(`SKILL.md:128-133`). It answers "does the codebase build before this loop touches it," which
is a precondition for the whole loop, not a per-finding pre-edit confirmation.

### Step 3 sub-step 3 — the actual post-edit re-verification

`SKILL.md:203`: "Re-run test/build. On failure, before reverting, branch on **what** failed" —
distinguishes a stale golden-fixture mismatch (regenerate, don't revert) from a real
regression (revert). This is the whole test/build suite, not the specific architectural test
the targeted finding cited, and its outcome is recorded only as free prose in
`loop_result.evidence_change_is_honest` (example: `"swift test 1439 passed; lint clean"`,
`references/output-format-json.md:397`) — no typed field, no enum.

### Step-3 implementation reviewer — the closest existing analog to a repair-revalidation check

`references/implementation-reviewer.md` runs post-diff, pre-commit, as an independent
fresh-eyes subagent (`references/implementation-reviewer.md:20-25`). Three checks, in order,
stop-at-first-failure:

- **Check 1 (Reality)** re-derives whether "current source actually no longer exhibits the
  targeted finding's pattern," by re-running the same architectural test the finding cited
  (deletion / two-adapter / shallow module / interface-as-test-surface / replace-don't-layer)
  and, if the finding cited `file:line` evidence, reading those exact lines post-diff
  (`references/implementation-reviewer.md:65-76`). This **is** an invariant-specific, post-fix
  confirmation — the closest thing this skill has to center-audit's post-edit invariant result.
- **Check 2 (Honesty)** re-applies the Simplify Pressure Test to the diff (deletion test,
  Unified Seam Policy, tests-at-new-interface, costume-layer scan, fake-clean-reward scan,
  suppression-as-fix scan) — `references/implementation-reviewer.md:79-119`.
- **Check 3 (Regression)** scans for a new finding at the same-or-higher severity, plus an
  **invariant-preservation** cue list for risk-bearing diffs (changed isolation, removed
  `final`/`Sendable`, narrowed `#if os()`/`canImport`, moved file dropping
  `private`/`fileprivate`, removed guard/lock) — `references/implementation-reviewer.md:143-159`.

**What it writes.** `implementation_review` object
(`references/output-format-json.md:414-432`): `verdict ∈ {approved, rejected, conditional}`
(`canon/verdicts.toml`, final committed value never `conditional` — G15), `reason`,
`checks.{reality,honesty,regression} ∈ {passed, failed, skipped}`, `regressions[]`,
`conditions[]`, `rounds`, and the v3+ retry envelope (`retry_count`, `retry_cause`,
`retry_attempts[]`).

**Pre-edit confirmation is not independently recorded, but a version of it exists implicitly.**
The finding's own Evidence Chain (`title` + `why_it_matters` + `what_is_wrong` as Claim,
`evidence[]` as Source — `references/output-format-json.md:281-297`) is written at Step 1,
*before* Step 3 edits anything. For carried-forward findings (loop ≥ 2), method.md Step 1.7
requires a fresh re-derivation, not a lift from history: "confirm its Claim was re-derived by
your Step 3-8 walk this loop, not lifted from `REVIEW_HISTORY.json`... Re-walk the file from
source roots; confirm independently" (`references/method.md:77`). This functions as a pre-edit
invariant check, but it is not a separately typed field distinct from the general Evidence
Chain — it's implicit in the finding's `evidence[]` plus the anchor-check discipline.

### The nearest existing *shape* for a typed, invariant-specific, independently recorded record

`loop_result.risk_boundary_evidence` (`references/output-format-json.md:398`) is
`{boundary_kind, verification, detail, mechanically_testable}`: `boundary_kind ∈
canon/risk-boundary-kinds.toml` (`isolation | sendable | conditional_compilation |
cross_file_visibility | lock_ordering`), `verification ∈ canon/risk-evidence-verifications.toml`
(`compile_matrix | focused_test | thread_sanitizer | sendable_conformance | reasoning_only |
carried_forward` — deliberately no single-config-compile value), `detail` non-empty string,
`mechanically_testable` bool. Gated at shape level by **G33**
(`references/validation.md:142`, "Shape-gates the Meta-Rule-4 preservation-evidence record...
G33 checks SHAPE only; the git-grounded safety check... is the Layer-5 grader's job"), and the
Layer-5 grader (`exec_replay_grade.py`, per G33's own text) fails a *committed* boundary diff
whose verification isn't real. This is exactly the pattern Gap 26 wants generalized — it's just
scoped to Meta-Rule-4 risk boundaries only, not to every finding's repair.

### The finding schema, as it stands

Per-finding fields (`references/output-format-json.md:284-306`): `loop_local_id`, `stable_id`
(v2+, format `F-NNN`), `id` (legacy alias), `title`, `why_it_matters`, `what_is_wrong`,
`evidence[]` (≥1), `test_failed` (inline enum: `Deletion test | Two-adapter rule | Shallow
module | Interface-as-test-surface | Replace-don't-layer | n/a` — **not** promoted to a
`canon/*.toml` file, confirmed by grep; every other closed enum below is), `dependency_category`
(`canon/dependency-categories.toml`: `in-process | local-substitutable | remote-owned |
true-external`), `leverage_impact`, `locality_impact` (one-sentence Depth-payoff fields, defined
in `references/architecture-rubric.md:25-26` as "what callers get" / "what maintainers get" —
**not** an effort/cost measure), `metric_signal`, `why_weakens_submission`, `severity`
(`canon/severity-anchors.toml`: `Cosmetic for contest | Noticeable weakness | Serious deduction
| Likely disqualifier`), `adr_conflicts[]`, `adr_reopen_justification`,
`minimal_correction_path` (free-prose remedy), `blast_radius: {change[], avoid[]}`.

Closed enums confirmed present in `canon/*.toml` (verified by reading each file):
`fix-kinds.toml` (`extract | inline | delete | merge | move | gate` — scoped to
`convergence_pass[].proposed_fix` only, see below), `finding-statuses.toml` (`open | resolved |
fixed_by_user | rejected_attempt | unresolvable`, used for registry `occurrences[].status`;
the JSON schema doc additionally documents a `withdrawn` value at
`references/output-format-state-schemas.md:190` not present in the current
`finding-statuses.toml` file — **uncertain**: whether this is a doc/canon drift or `withdrawn`
lives in a different canon file; out of scope to resolve here, flagged for whoever next touches
that enum), `severity-anchors.toml`, `residual-blocker-kinds.toml` (`structural_anchor_unmet |
ceremony | framework_constrained | cosmetic | adr_carved_out` — governs why a *scorecard
dimension* stays below 9.5, not why a *finding's fix* took a given shape), `scorecard-
dimensions.toml` (9 dimension ids), `dependency-categories.toml`, `retirement-reasons.toml`
(`unresolvable | user_decision | outside_scope | unverifiable | superseded` — governs why a
*finding* is retired from tracking, not how it was fixed), `risk-boundary-kinds.toml`,
`risk-evidence-verifications.toml`, `verdicts.toml` (`approved | rejected | conditional` — for
`implementation_review.verdict` only, i.e. "should this diff be committed," not "is the
invariant fixed").

**`fix_kinds` is real but narrowly scoped.** Its own header states why it's an enum: G43 judges
whether a repeated "clean" verdict on the Stalled-Dimension Sweep / Adversarial Pass proposed
something *new*, via the structured triple `(fix_kind, target_path, target_symbol)` inside
`convergence_pass[].proposed_fix` (`references/output-format-json.md:369-374`,
`canon/fix-kinds.toml:1-12`). It is **not** currently a field on `findings[]` or `backlog[]`
items — those carry only free-prose `minimal_correction_path` / `why_it_matters`.

### `loop_result` and `implementation_review` fields relevant to revalidation

`what_changed`, `evidence_change_is_honest` (free prose), `risk_boundary_evidence` (above),
`targeted_finding_status ∈ {resolved, carried_forward}` — a **binary, author-set** claim (the
loop subagent that wrote the diff sets this, not an independent checker) —
`unintended_regression`, `changed_paths[]` (v3+, from `git diff --name-only HEAD`),
`interface_test_coverage_path[]` (G17's payload). `implementation_review` is the independently
set counterpart, but its `verdict` answers "commit or revert," and `checks.reality` collapses
every failure mode (pattern persists / pattern replaced by something equally bad / pattern
genuinely gone but for reasons unrelated to this diff) into one `failed` value.

### The backlog item schema

`references/output-format-json.md:326-334`: `priority` (int), `stable_id` (v4+, required,
format `^F-\d{3,}$`, checked by `check_g42_backlog_stable_id`,
`scripts/_artifact_core.py:587`), `title`, `kind` (inline enum: `structural | simplification |
polish` — not promoted to canon), `rank` (inline enum: `needed for winning | helpful | minor` —
not promoted to canon), `why_it_matters`, `score_impact` (required string, format
`<canon_dim_id> <signed delta>`, `;`-joined for multi-dimension items, checked by
`check_g39_backlog_score_impact`, `scripts/_artifact_core.py:418`).

**G39** (`references/validation.md:175`): every dimension named in `score_impact` must be a
`canon/scorecard-dimensions.toml` id **and** present in this loop's `scorecard`. Explicitly
shape-only: "G39 never judges whether the projected move is *right*"
(`references/validation.md:179`).

**G42** (`references/validation.md:195`): every `backlog[]` item carries `stable_id` matching
`^F-\d{3,}$`, and when `findings[]` is non-empty this loop, the id must be one of them. Its own
rationale text: "after G39 an item says what it **moves**... `priority`/`rank` say where it
**ranks** — but nothing said *which finding it is*" (`references/validation.md:197`).

**No effort or cost field exists anywhere in the backlog or finding schema** — confirmed by
grep for `effort` across `references/*.md`, `canon/*.toml`, `SKILL.md`; the only hits are
unrelated ("best-effort" reverse-parse in resume-detection prose). The Backlog Prioritization
Pass explicitly ranks by "expected marginal contest gain, **not** confidence of completion,"
and states the two "invert routinely" (`references/method-critic.md:9-11`) — so `priority`
today is deliberately *not* an effort-weighted ranking. Adding an `effort` field is additive,
not a duplicate of `priority`/`rank`, but it should not silently change what `priority` means.

### Summary table

| Claimed-missing capability (Gap 26) | Status | Cite |
|---|---|---|
| Pre-edit invariant confirmation | **Partially covered** | Finding's Evidence Chain at Step 1 (`references/output-format-json.md:281-297`) + Step 1.7 anchor-check re-derivation for loop ≥ 2 (`references/method.md:77`) — implicit in the general Evidence Chain, not an independently typed field |
| Post-fix invariant result | **Mostly covered** | Reviewer Check 1 Reality (`references/implementation-reviewer.md:65-76`), recorded as `checks.reality ∈ {passed,failed,skipped}` (`references/output-format-json.md:419`) — binary, not 4-way |
| Lifecycle verdict (typed) | **Partially covered, by two different fields, neither matching** | `implementation_review.verdict` (commit-or-revert axis, `canon/verdicts.toml`) and registry `occurrences[].status` (audit-trail axis, `canon/finding-statuses.toml`) — see §4 |
| Remediation strategy (typed) | **Partially covered** | `canon/fix-kinds.toml` exists but is scoped to `convergence_pass[].proposed_fix` only (`references/output-format-json.md:369-374`), absent from `findings[]`/`backlog[]` |
| Owning dimension | **Mostly covered** | G39 requires `backlog[].score_impact` to name a `canon/scorecard-dimensions.toml` id (`references/validation.md:175`) — different mechanism than tech-audit's re-routing, same functional role in a single-critic model |
| Chosen disposition (guard/document/encode-in-type) | **Absent** | `residual-blocker-kinds.toml` and `retirement-reasons.toml` are adjacent enums answering different questions (why a score stays low; why a finding is retired) — no match |
| Effort | **Absent** | No field anywhere; `priority`/`rank` are explicitly gain-ranked, not effort-ranked (`references/method-critic.md:9-11`) |
| Leverage sort (severity × effort) | **Absent as a computed value** | `priority` (int) + `severity` (enum) exist as inputs; no stored or derived severity×effort key |
| `repair_revalidation` (4-value, center-audit) | **Absent, but a shape precedent exists** | `loop_result.risk_boundary_evidence` (`references/output-format-json.md:398`, gated by G33) is the closest existing typed/invariant-specific/per-diff record — scoped to Meta-Rule-4 boundaries only |

---

## 2. The delta — what is genuinely missing

Per candidate field, smallest closure:

1. **Remediation strategy** — partially covered. Extend `fix_kinds`' *scope*, not its values:
   allow `fix_kind` on `findings[]`/`backlog[]` items directly (currently `convergence_pass`-
   only). For the four non-simplification families the gap text names (dependency upgrade,
   data migration, configuration change, algorithm fix, test addition), `fix_kinds`' six values
   don't fit — see §3's discriminant. Cheapest closure: add `finding_family` (new small enum)
   as the general discriminant, and let `fix_kind` stay simplification-family-scoped exactly as
   it is today, just readable from `findings[]` too.

2. **Owning dimension** — already covered by G39's `score_impact` dimension attribution.
   Nothing to add. Recording this as a finding is more valuable than a field: tech-audit's
   re-routing rule is a correctness/security/a11y-vs-simplification boundary between
   *different owning agents*; this skill has one Critic and nine scorecard dimensions, and
   `score_impact` already says which dimension a fix credits. No new field.

3. **Chosen disposition** — absent, and genuinely needed only for one family
   (latent-premise findings — the family tech-audit/skillet's disposition arrows actually type).
   Smallest closure: a 3-value enum `guard | document | encode_in_type`, required only when
   `finding_family == latent_premise`. Do not make it a general field — it has no meaning for a
   dependency upgrade or an algorithm fix.

4. **Effort** — absent, structurally new, no existing field to extend. Smallest closure: a
   small closed ordinal (`trivial | small | moderate | large`, matching the cardinality
   `severity_anchors` already uses) — general field, cheap.

5. **Revalidation outcome** — absent as a typed value; `checks.reality` is the closest existing
   signal but collapses 3+ real outcomes into `passed`/`failed`. Smallest closure: adopt
   center-audit's 4-value `repair_revalidation` (`INVARIANT_HOLDS | INVARIANT_DRIFTED | INVARIANT_REPLACED |
   CONTRACT_REJECTED`) verbatim as the label set — it's already more granular than anything
   here, no reason to invent new labels — modeled structurally on `risk_boundary_evidence`'s
   shape (§1): pair it with an evidence sub-object rather than a bare enum, so the same
   `mechanically_testable`/`detail` discipline that already keeps `risk_boundary_evidence`
   honest applies here too.

6. **`repair_revalidation`, center-audit's 4-value field** — this *is* item 4/5 combined above;
   restating separately would double-count it in the delta.

**Preference order applied**: extend an enum (`fix_kind`'s scope) over adding a field
(`effort`, `repair_revalidation`) over adding an object — and even the "object" additions here
(`revalidation_evidence`) are one flat struct copied from an existing shipped shape, not a new
kind of nesting.

**Net new schema surface**: two general fields (`finding_family`, `effort`) + one general object
(`repair_revalidation` + its evidence sub-object) + one family-conditional field (`disposition`,
latent-premise only) + one scope extension (`fix_kind` readable from `findings[]`/`backlog[]`,
simplification family only). Nothing else from Gap 26's candidate list survives as a new
field — the rest is already covered.

---

## 3. Discriminated schema

### General fields (every finding, once it reaches Step 3 sub-step 4/6 — i.e. once a fix has
actually been attempted; absent on findings still in the backlog, unattempted)

- `finding_family`: enum — `simplification | latent_premise | dependency_upgrade |
  data_migration | configuration_change | algorithm_fix | test_addition | security_fix |
  concurrency_fix`. Discriminant for the conditional fields below.
- `effort`: enum — `trivial | small | moderate | large`.
- `repair_revalidation`: object — `{ outcome: "INVARIANT_HOLDS" | "INVARIANT_DRIFTED" | "INVARIANT_REPLACED" |
  "CONTRACT_REJECTED", detail: <non-empty string, what was actually re-checked>,
  mechanically_testable: bool }`. Directly mirrors `risk_boundary_evidence`'s
  `{detail, mechanically_testable}` discipline (`references/output-format-json.md:398`):
  `reasoning_only`-style prose is legal only when `mechanically_testable: false`.

### Family-conditional fields

- `finding_family == simplification` → `fix_kind` required, reusing `canon/fix-kinds.toml`
  verbatim (`extract | inline | delete | merge | move | gate`) — no new enum, just a new place
  to read it from.
- `finding_family == latent_premise` → `disposition` required, new enum `guard | document |
  encode_in_type`.
- `finding_family == security_fix` or `concurrency_fix` and the diff crosses a Meta-Rule-4
  boundary → `risk_boundary_evidence` is *already* required by existing G33; no new field, just
  a cross-reference (a security/concurrency `repair_revalidation` record with no
  `risk_boundary_evidence` alongside it, on a diff that G33 would recognize as boundary-
  crossing, is itself a coherence check worth a gate later — noted, not built here).
- `dependency_upgrade | data_migration | configuration_change | algorithm_fix | test_addition`
  → no additional typed field. `minimal_correction_path` (already required prose) plus the two
  general fields above are sufficient; these families don't have an upstream taxonomy claiming
  a typed sub-field, and inventing one un-asked-for repeats exactly the mistake Gap 26 warns
  against (forcing every repair through a lens built for a different kind of repair).

### Expressibility check

| Family | `finding_family` | `fix_kind` | `disposition` | `repair_revalidation.outcome` example | Notes |
|---|---|---|---|---|---|
| Dependency upgrade | `dependency_upgrade` | — | — | `INVARIANT_HOLDS` once build+tests green post-bump | If the bump crosses a `Sendable`/isolation boundary, `risk_boundary_evidence` also fires (existing G33) |
| Data migration | `data_migration` | — | — | `INVARIANT_HOLDS` via a focused round-trip test | No migration-specific sub-schema — accepted limitation, see below |
| Configuration change | `configuration_change` | (optional `gate` if it's literally a guard at an existing seam) | — | `INVARIANT_HOLDS` | Expressible with general fields alone |
| Algorithm fix | `algorithm_fix` | — | — | Reviewer re-runs the cited test; `INVARIANT_HOLDS`/`CONTRACT_REJECTED` | Same shape as reviewer Check 1 already produces, just typed |
| Test addition | `test_addition` | — | — | `INVARIANT_HOLDS` iff the new assertion exists **and** `distinguishes_no_op == true` per G17's own shape | Reuses G17's existing no-op discipline rather than inventing a second one |
| Simplification | `simplification` | required, existing enum | — | Reviewer Check 1 outcome mapped onto the 4 values (§4) | Best-fit family — `fix_kinds` was built for exactly this |
| Latent premise | `latent_premise` | — | required, new enum | e.g. `encode_in_type` → outcome checked via compile evidence, reusing `risk_evidence_verifications`' vocabulary as the "how" | New field genuinely earns its place here |
| Security fix | `security_fix` | — | — | `INVARIANT_HOLDS` (general fields) or paired with `risk_boundary_evidence` if boundary-crossing | Both paths expressible |
| Concurrency fix | `concurrency_fix` | — | — | Almost always paired with `risk_boundary_evidence` (already G33-required when committed) | Strongest existing precedent — concurrency fixes already get a typed, invariant-specific, independently recorded record; this proposal just names the pattern |

**Accepted limitation**: data migrations get no forward/backward-specific sub-field. The general
`repair_revalidation` axis is coarse enough not to need one for this skill's purpose (grading a
codebase against an architecture rubric, not running a migration-testing framework). If
migrations become a recurring finding family with real incidents, that's a future, separately
scoped item — not a defect in this proposal.

All nine families are expressible. No family required a proposal change to fit.

---

## 4. Collision check against items 26 and 27

The deep-dive's finding-assurance section names three overlapping mechanisms: item 6's
*confidence*, item 26's *evidence strength* (per link, A–D), item 27's *disproof* (a lifecycle
verdict) (`docs/review-skill-deep-dive-2026-08-17.md:1092`). `repair_revalidation` is a fourth
lifecycle-shaped value. Verdict: **it is a separate axis, not a duplicate of item 27's
verdict**, on two grounds:

- **Different subject.** Item 27's `VERIFIED / CORRECTED: [field] / REJECTED` verdict answers
  "is this *finding* real" — applied by an independent disprover with, per the gap text, "no
  trigger, no bug" discipline, *before* any repair is attempted, as part of finding admission.
  `repair_revalidation` answers "did the *fix* actually hold" — applied *after* a repair diff
  already exists, by the Step-3 reviewer (or its typed extension).
- **Different pipeline stage.** Item 27 gates whether a finding enters the loop's committed
  record at all (pre-admission). `repair_revalidation` gates what gets recorded once a fix has
  already been attempted against an admitted finding (post-repair). These are sequential, not
  overlapping: a finding must survive item 27's disproof pipeline (once built) before Step 3
  ever attempts a fix on it, and `repair_revalidation` only exists downstream of that.

**Existing near-collision, worth flagging precisely**: this skill already has two lifecycle-
shaped fields adjacent to `repair_revalidation` — `implementation_review.verdict` (`approved |
rejected | conditional`, `canon/verdicts.toml`) and registry `occurrences[].status` (`open |
resolved | fixed_by_user | rejected_attempt | unresolvable`, `canon/finding-statuses.toml`).
Neither is the same axis: `implementation_review.verdict` mixes all three reviewer checks
(reality + honesty + regression) into one commit-or-revert decision; `occurrences[].status` is
an audit-trail state across loops, set partly by the routing logic, not an independent
invariant re-check. `repair_revalidation` is deliberately *narrower* than both — it isolates
just the Check-1-Reality sub-question into its own typed, 4-way value. A rough mapping for the
schema pass to validate against real diffs later:

**Source-verified definitions.** center-audit *is* vendored, at
`refs/competitors/contest-refactor/center-audit` (`git rev-parse --short HEAD` = `b154fb0`,
matching the pin in the deep-dive's source table). The first draft of this note recorded the
enum semantics as "uncertain, inferred from the gap text"; they are now read from the source.
Note the real label names carry the `INVARIANT_` prefix on three of four — the deep-dive quotes
them in shorthand (`INVARIANT_HOLDS / DRIFTED / REPLACED / CONTRACT_REJECTED`), and adopting the
shorthand verbatim would ship names that do not match the source we cite.

Verbatim, from `center-audit/README.md:65-68`:

- `INVARIANT_HOLDS` — "required_invariant still reproduces. Proceed with the contract."
- `INVARIANT_DRIFTED` — "anchor or contract drifted; repair proceeded with adjustments in `drift_notes`."
- `INVARIANT_REPLACED` — "original invariant was wrong; repair replaced it."
- `CONTRACT_REJECTED` — "re-validation failed; repair halted; audit reopens."

`center-audit/CHANGELOG.md:29` narrows two of them further: `DRIFTED` is "reserved for cases
where the contract edge itself shifted (**not** for mechanical adjustments)"; `REPLACED` is "for
the audit having been wrong"; `REJECTED` is "for a failed handoff."

**This corrects the first draft's mapping, which had the axis wrong.** The draft read `DRIFTED`
as a *degree of failure* ("pattern partially persists") and `REPLACED` as "the finding went
moot." Against the source, `DRIFTED` and `REPLACED` are both **successful** repairs — the fix
landed, and the label records that the *invariant* moved underneath it — while every genuine
re-validation failure is `CONTRACT_REJECTED`. Corrected:

| `implementation_review.checks.reality` | `repair_revalidation.outcome` |
|---|---|
| `passed`, and the invariant reproduced as the finding stated it | `INVARIANT_HOLDS` |
| `passed`, but the contract edge itself had shifted since the finding was written; fix landed with adjustments | `INVARIANT_DRIFTED` (requires non-empty `drift_notes`) |
| `passed`, and re-checking showed the finding's stated invariant was wrong; the repair replaced it | `INVARIANT_REPLACED` — nearest existing precedent is registry status `withdrawn` (`references/output-format-state-schemas.md:190`, "re-verification shows the prior finding was a false positive") |
| `failed` — pattern persists, wholly or partially | `CONTRACT_REJECTED` (the loop's existing response is revert-and-reopen, which is exactly this label's semantics) |

Two further details worth carrying into the schema pass, both now source-backed:

1. **`drift_notes` is conditionally required.** `center-audit/CHANGELOG.md:13` records that
   v2.5.0 *described* `drift_notes` as required on a non-HOLDS result but did not enforce it;
   v2.5.1 uses JSON-Schema `allOf`/`if`/`then` so an empty `drift_notes` on `INVARIANT_DRIFTED`,
   `INVARIANT_REPLACED`, or `CONTRACT_REJECTED` is a schema violation. That is the same
   described-but-unenforced failure this skill's own gates exist to prevent — the schema pass
   should gate it mechanically from the start rather than repeating the v2.5.0 mistake.
2. **A fifth value is a known gap upstream.** `center-audit/ROADMAP.md:15` proposes `AUDIT_MOOT`
   (or `SCOPE_INVALID`) for "the code under audit was deleted, the feature was deprecated, or the
   scope no longer applies," noting `REJECTED` is the wrong fit because "there is no contradiction
   to resolve." This skill hits that case routinely — a later loop deletes the file an earlier
   finding targeted — and the first draft of this note tried to force exactly that case into
   `REPLACED`. Decide the fifth value **at design time**, not after the enum ships.

If item 6's experiment lands on finding-level confidence anchors, and if evidence-strength
grading (item 26) is ever extended to grade the *strength of revalidation evidence itself* (was
the post-fix re-check a `focused_test` or bare `reasoning_only`?), that would be a genuine
future link between this field and the finding-assurance model — but it is an enhancement, not
a blocking dependency. Item 28 does not need to wait on items 6, 26, or 27.

---

## 5. The refactor-promotion test

center-audit's promotion test gates *escalating a local fix into a structural refactor*,
framed by the deep-dive as "the inverse of our mandate." The first draft of this section
reasoned from the paraphrase alone, believing the source unavailable. It is available, so here
are the five conditions verbatim (`center-audit/SKILL.md:392-404`, under "No refactor during
CENTER"):

> Recommend structural redesign only when all are true:
> 1. the defect is confirmed
> 2. the trajectory proves the structure causes recurrence
> 3. a local patch would mask rather than remove the root cause
> 4. the recommendation names the minimum contract that must change
> 5. verification and rollback boundaries are explicit
>
> Otherwise, repair the defect. Do not redecorate the cathedral.

**Verdict, revised now that the conditions are readable: the *gate* does not apply, but it is
not five inapplicable conditions — it is one.** Reading them individually rather than as a
block:

| # | Mandate-dependent? | Standing here |
|---|---|---|
| 1 defect confirmed | No | Already required — a finding reaches Step 2 only through the Step-1 critic and the Evidence Chain. |
| 2 trajectory proves the structure causes recurrence | **Yes — this is the inverted one** | center-audit demands proof of *recurrence* before permitting structure work. This skill promotes structural work on a *Deepening Opportunity Test*, no recurrence required. Importing this condition would forbid the skill's core move. |
| 3 local patch would mask the root cause | No | Directionally already present — the Simplify Pressure Test and the reviewer's fake-clean-reward scan (`references/implementation-reviewer.md:115-117`) both reject masking. |
| 4 names the minimum contract that must change | No | Generic discipline. Partially covered by `blast_radius.change[]`, which names the surface but not the *contract*. |
| 5 verification and rollback boundaries explicit | No | Substantially covered — G33's `risk_boundary_evidence`, `changed_paths[]`, and `LOOP_STATE.pre_step3_blob_shas` (the narrow-revert classifier) are exactly verification and rollback boundaries. |

So the honest statement is narrower and more useful than "inverted, discard": **only condition 2
inverts.** The other four are mandate-independent discipline this skill already satisfies in
substance, which is a stronger corroboration of the existing design than a blanket rejection
would have been — and it means the "inverse of our mandate" framing in the deep-dive, while
true of the gate as a whole, should not be read as invalidating its parts.

This skill's mandate is to find and execute the deepest legitimate structural win each loop —
`references/method.md`'s Deepening Opportunity Test and the JSON schema's
`deepening_candidates[]` exist specifically to *promote* toward structural change. Adopting the
test as a gate would fight that. Adopting condition 4 as a *field* (name the minimum contract
that must change) is the one piece with any residual pull, and it is not proposed here: it
overlaps `blast_radius` enough that it should be argued on its own merits later, not smuggled in
as part of item 28.

But the *purpose* the promotion test serves — stopping unjustified scope creep — already has a
functional equivalent here, just aimed at justification rather than prevention:

- **G12 Seam policy + friction proof** (`references/validation.md`, referenced at
  `references/method.md:95` "Friction Proof Before Seam Recommendation") requires any new/
  restructured Seam to cite source-backed friction, conjunctive with Unified Seam Policy
  compliance.
- The reviewer's **Costume-layer scan**
  (`references/implementation-reviewer.md:110-113`): "did the diff add a folder, protocol, or
  naming scheme that 'looks architectural' but does not control writes, dependencies, or
  runtime authority? ... reject."
- The reviewer's **fake-clean-reward scan** (`references/implementation-reviewer.md:115-117`).

These already reject an escalation that doesn't earn its complexity — they just do it by
requiring the escalation to justify itself via friction proof, not by capping it against a
fixed condition list.

**One narrow, genuinely applicable sibling worth carrying forward, not as center-audit's test
itself**: within `repair_revalidation`, whether a committed diff's `changed_paths[]`
(`references/output-format-json.md:401`, already collected v3+) stayed inside the finding's
declared `blast_radius.change[]` (`references/output-format-json.md:302-305`, already
required). That's a cheap comparison of two path lists this skill already writes — a real,
narrow check that a *repair* didn't silently balloon past what Step 2 planned, without
importing a gate built for a mandate this skill doesn't have. Optional for the eventual schema
pass, not required — flagging it here so it isn't lost.

---

## 6. Sequencing and cost

**Nothing blocks this from landing next**, per §4: no dependency on items 6, 26, or 27's
finding-assurance decision. Two backlog items already shipped are worth confirming as
non-dependencies rather than assuming: item 12's declarative transition table
(`canon/states.toml`, commit `47f3f77` per this session's git log) governs top-level
`state ∈ {CONTINUE, HALT_*}` transitions — `repair_revalidation` is a finding/`loop_result`-
level field, a different namespace, so no interaction. Item 16's mechanized structural grading
(commit `58cbbfe`) is about Layer-5 execution-grain grading of already-shipped fields, not a
blocker for adding new ones.

**What the schema pass should build, in order:**

1. `canon/finding-families.toml` (9 values) and `canon/repair-dispositions.toml` (3 values,
   `guard | document | encode_in_type`) — new canon files, following the existing header
   convention (purpose comment + cross-references, per every file read in §1).
2. Extend `check_schema_enums` (`scripts/_artifact_core.py:246`) to validate `finding_family`,
   `effort`, `repair_revalidation.outcome`, and the family-conditional `disposition`/`fix_kind`
   presence rule — same pattern G39/G42 already use for backlog-item shape checks.
3. A new mechanical gate (next available G-number) for the conditional-presence rule
   (`disposition` required iff `finding_family == latent_premise`; `fix_kind` required iff
   `finding_family == simplification`) — modeled directly on G33's "shape gate, not truth gate"
   scoping (`references/validation.md:142`).
4. Expressibility fixtures — one fixture per family in the table in §3, each a valid
   `CURRENT_REVIEW.json` finding + `loop_result` exercising the new fields, validated by the
   new gate. This is what "expressibility fixtures proving every major finding family has a
   valid representation" (Gap 26,
   `docs/review-skill-deep-dive-2026-08-17.md:1078-1080`) concretely means for this skill.

**Acceptance test**: all 9 expressibility fixtures pass the new gate; the 9 finding families in
§3's table each produce a schema-valid artifact; no regression in the existing G16/G39/G42
selftests (`scripts/_g39_selftest.py`, `scripts/_g42_selftest.py`,
`scripts/_g16_uniqueness_selftest.py`) — this is entirely **deterministic** validation, same
class as G33's shape check.

**Cost**: Low-Moderate for the schema/shape pass, consistent with the backlog row's own
Moderate estimate (`docs/review-skill-deep-dive-2026-08-17.md:1156`) — it's additive fields
plus two small canon files plus one gate, closely mirroring the `risk_boundary_evidence`/G33
precedent this note found in §1, which is a small, self-contained diff.

**What is expensive and belongs in a separately batched behavioral sweep, not this pass**:
whether an executor/reviewer, in practice, *selects* the right `finding_family` and
`disposition`/`fix_kind` on real diffs, and whether the `repair_revalidation.outcome` it emits
correlates with ground truth — i.e., can a model reliably tell `INVARIANT_HOLDS` from `INVARIANT_DRIFTED`
on a diff that looks clean but isn't. That needs the same RED-first micro-test discipline this
project already uses for prose/schema changes (5+ reps, no-guidance control, read matches
before shipping) and should batch with other pending behavioral sweeps rather than run
standalone, per this project's own batching convention for LLM-judged validation.
