# Gap Audit + Improvement Plan — contest-refactor (2026-06-28)

> **Rev 2 — revised after dual peer review (2026-06-28).** Reviewed by codex `gpt-5.4` (high
> effort, cross-family/independent) and copilot `claude-sonnet-4.6`; both returned **REVISE** and
> **converged** on the same substantive findings. Every load-bearing finding was source-verified
> before acceptance. Net effect of the revision: the audit's *classification method* and *core
> thesis stand* (no valuable gap was skipped by oversight; one harness is worth building; doc
> reconciliation is valuable), but four "already-covered" verdicts were **overstated** and are
> downgraded here, W2 had concrete technical errors (now corrected), and two W3 "DECLINE"s rested
> on doctrine that does not actually forbid the field (now reframed as honest DEFER). Change log at
> the end.
>
> **RE-VERIFIED 2026-06-30:** since this 2026-06-28 audit, gates **G33–G36 have SHIPPED** — canon `validation-gates.toml` now tops out at **G36** (G37+ remain unbuilt proposals). SARIF (`export_sarif.py`) and AST import-graph/cycle detection (`audit_boundaries.py`) re-confirmed SHIPPED; the `schema_version: 4`→v5 guidance is unchanged. Each gap doc's top-of-file ceiling header was updated to match. Scattered in-body counts (e.g. “G1–G31 / 31 hard gates”) are historical 2026-06-28 snapshots — the authoritative current ceiling is each doc's updated header, not the in-body prose.

**Question asked:** Did we ignore or skip the competitive gaps in `analysis/contest-refactor/*-GAP.md`
for a *good* reason (equivalent already exists / feature is bad / deliberately deferred), or did real
value slip through by oversight?

**Method:** four skeptical verifiers, one per gap-cluster, each re-checked every claimed gap against
**current** skill source (the docs predate `schema_version` 4, gates G27–G32, the `reviewer-cases`
harness, `audit_cochange.py`, `export_sarif.py`, and the depth-ceiling falsification). Load-bearing
claims were then spot-checked directly (grep/ls), and the plan itself was dual-peer-reviewed.

**Headline:** **No valuable gap was skipped by oversight** — but "no oversight" is *not* the same as
"already covered." Several items the first pass called "covered" are more honestly **genuinely open
but deliberately deferred** (the equivalent mechanism is a *complement*, not a *substitute*). The net
actionable list is still short — one eval harness worth building (W2), a batch of doc reconciliation
(W1), and a set of additive fields to defer with honest rationale (W3).

---

## Part 1 — Audit verdicts

### 1a. STALE DOCS — skill already surpassed the gap (verified directly)

| Gap doc | What the doc says is missing | Reality (verified) |
|---|---|---|
| SCHEMA Gap 6 — SARIF interop | "defer until a CI consumer exists" | **Shipped.** `scripts/export_sarif.py` (SARIF 2.1.0) + `_export_sarif_selftest.py`, wired in `references/output-format.md`. |
| GOVERNANCE C/D — import-graph / cycle detection | "—" (absent) | **Shipped.** `scripts/audit_boundaries.py` parses the real `ast` import graph + detects cycles (advisory candidate-evidence in method.md Step 3). |
| Multiple docs — gates G34/G37/G41/G42/G43 | proposed/assumed to exist or be added | **Phantom.** `canon/validation-gates.toml` tops out at **G32**. None of G34/G37/G41/G42/G43 exist. Any "add G4x" proposal is net-new, not an extension. |
| SCHEMA-GAP § Schema delta — "ship `confidence`/`severity_rationale` as `schema_version: 4`" (line ~130) | version arithmetic | **Stale in one specific spot (not blanket).** `schema_version: 4` **already shipped** — it is the HALT-challenge schema (12 v4 fixtures in `evals/`; G32 fires only at `schema_version >= 4`, `validation.md:152`). So new finding fields would be **v5**, not v4. The doc has *partially self-corrected* — its "§ Schema-version sequencing (v4→v5)" already routes some fields to v5. Fix is **scoped**: correct the "ship as v4" lines; leave the v4→v5 section. *(Reviewer-corrected: the earlier blanket "v4 arithmetic wrong" was too broad.)* |
| SKILL-TDD Gap A | "skill jumped to validate-the-validator without observing a baseline" | **Stale premise.** Layer-2 refactoring-judgment runs a 3-arm **no-skill baseline** and `principal_baseline.json` records `expected_baseline` (RED) vs `baseline_observed` + CP95 — that *is* baseline-observation discipline, at judgment grain. (The end-to-end *loop-replay* fixture is still genuinely absent — see W2.) |

→ **Action:** these docs actively mislead a future audit. Reconcile them (Part 2, W1).

### 1b. PARTIALLY COVERED — an equivalent helps, but is a complement, not a substitute

> Peer review correctly flagged that the Rev-1 "ALREADY / PARTIALLY COVERED" bucket conflated two very
> different things. The rows below are the ones where the existing mechanism is a genuine *complement*
> but leaves a real residual. The truly-equivalent cases (where the mechanism fully substitutes) are
> only GATES A/B and the dedup/provenance rows; the rest are downgraded.

| Gap | Claimed missing | What exists (complement) | Residual still open |
|---|---|---|---|
| TWO-LAYER-DETECTION A (P0) | a *named, mandatory* Layer-1→Layer-2 procedure + proof Layer-2 happened | Evidence Chain **encourages** grep→verify in prose (`method.md:18-30,36,71`); G3 checks finding *fields are populated*. | **No process-gate proves Layer-2 verification occurred** — a Critic can populate the fields without having read context. Net-new: the mandatory procedure + a verify-happened gate + optional excluded-candidate audit trail. *(Rev-1 "behavior enforced" was too strong.)* |
| SCHEMA 7 — `audited_areas[]` positive findings | "checked-and-clean vs silent" for **all** ≥9 dims | G24 (`test_strategy≥9`) + G25 (`concurrency≥9`) harden **2 of ~9** dims; G4 per-dim `proof` at >7; `strengths[]`. | **~7 dimensions have no "explicitly checked & clean" trail** — G4/G5/strengths answer "why this score," not "was this area audited or merely left silent." Partial, not covered. |
| SCHEMA 2 — `severity_rationale` | a "why this severity" field | function overlaps `test_failed` + `why_weakens_submission` + `canon/severity-anchors.toml`. | Marginal residual (the explicit one-liner). Low value. |
| SCHEMA 5 — per-finding validator subagent | semantic reject authority | `implementation_review` reviewer (reject authority, G15) + G32 HALT challenge (v4+). | Only *at-emit per-finding* downgrade is open (doc marks it "optional, harder"). |

### 1b′. ALREADY COVERED — truly equivalent

| Gap | Why fully covered |
|---|---|
| GATES A/B (P0) — Stop / SubagentStop hooks | **G20** ("do not yield turn; re-enter Step 1", `validation.md:86`) + **G15** enforce these at artifact level. Plugin Stop hooks are **Claude-Code-only** — a cross-provider skill (Claude/Codex/opencode/Gemini) can't portably own them; the gate is the portable equivalent. |
| SCHEMA 4 — cross-**loop** dedup | registry `fingerprint` (claim/consequence + evidence-path hashes) + fuzzy-match M1/M2 + G31. (The *parallel-critic* dedup triple is a different, deferred thing — see 1c.) |

### 1c. MEASURED & DELIBERATELY DEFERRED — parked on purpose, not ignored

| Gap | Status |
|---|---|
| CROSS-MODEL-CRITIC (P1) — Codex/Gemini cross-family critic | **Measured 2026-06-27.** Same-family Sonnet/Opus agree 9/10 (correlated blind spots); cross-family is "the one genuinely open lever… untested, structural… a documented future direction, not a shipped default" (`reviewer-model-experiment.md`). Note: the HALT challenger's independent post-output gate is **v4-only** (G32 fires at `schema_version >= 4`); it is not blanket coverage, and the *cross-family model* is absent regardless. |
| SCHEMA 3 — `critic_source` / parallel-critic dedup triple | Contingent on a parallel-critic mode that doesn't exist. Stamping provenance today = forward-compat bloat. |
| PARALLEL-CRITIC-ARTIFACT-CONTRACT | Self-gated: "no consumers until CRITIC-INDEPENDENCE Gap B ships." |
| HALT-STATE A — worktree isolation | "commits land on the active branch" **by design** (`trust-model.md:52`); the watch-it-work UX is intentional. Opt-in only. |
| HALT-STATE F — session-spanning halt-handoff | Absent in source (no `session_spanning`/`SessionStart`); the doc frames it as optional future "Gap F." Low value (Claude-Code-only SessionStart hook; cross-provider concern). |
| HALT-STATE G, all P2s (SPECIALTY-LENS, DOMAIN-AWARE, CONTINUOUS-SCORING, ROUTING-DISCIPLINE, PHASE-CONTEXT-ISOLATION, MULTI-HARNESS) | Each verified absent; each a deliberate simplicity choice. Correctly deferred. |

### 1d. CORRECTLY REJECTED — not a skill feature

- **ADOPTION-SIGNAL-TRACKING** — meta-discipline (quality-vs-adoption rank), not a loop feature.
- **ARXIV-AGENTIC-REFACTORING** — the 30.7%-rename finding is *context*, no proposed mechanism.

### 1e. GENUINELY OPEN — absent in source, after discounting the above

| Gap | Value | Note |
|---|---|---|
| **CRITIC-INDEPENDENCE Gap A (P0) — within-loop Critic↔Actor split** | **OPEN — owner's deferred "Execution-unfuse"** | *(Reviewer-corrected from Rev-1's "covered.")* The cold Step-3 reviewer (`implementation-reviewer.md:28`) and the HALT challenger (`halt-verifier.md`) give *cross-loop / post-execution* independence — **complements, not substitutes** for the gap, which is the **within-loop fusion**: current source still runs "Step 1 + Step 2 + Step 3 as one unit" in one subagent (`trust-model.md:52-54`). This is the owner's own gated *Execution-unfuse* item → routed to **W4** as a conscious defer (needs an execution-grain safety test first). |
| **SKILL-TDD Gap A — bad-*codebase* loop-replay harness** | **MOD (the one worth building)** | Layer-2 covers *judgment* baseline; what's missing is end-to-end **loop replay against a codebase**. Real regression value on schema/behavior bumps. See W2 (rewritten). |
| GOVERNANCE C (remaining half) — declarative `[[boundary_rules]]` config | MED for layered repos | Executable cycle-detection already ships; only the *declarative* forbidden-import TOML is open. Python-only today. |
| GOVERNANCE B — CI-workflow ingestion | LOW | Severity-escalation is Critic judgment; `validate-artifact.py` can't enforce it. |
| CLEAN-ENV A — fresh-checkout validation before HALT_SUCCESS | LOW-MED, **OPEN** | *(Reviewer-corrected from Rev-1's "covered.")* G21 full-suite reverify + dirty-tree abort are **same-worktree, version-independent** safeguards — **not** a fresh-checkout/worktree oracle; G32's independent challenge is **v4-only**. The fresh-checkout oracle (catches untracked/gitignored drift) is genuinely absent → **W4**, opt-in, honest cost/benefit. |
| CRITIC-INDEPENDENCE Gap B — parallel-critic mode | LOW-now | Large structural lift (Loop Isolation + single-writer lease); **no shipped consumers**. → W4. |
| confidence enum / ROI tiers / per-hunk `changed_hunks[]` / refactoring-patterns vocab | LOW | See W3 — defer with honest rationale (the doctrine does **not** forbid them; the case against is cost/consumer, not principle). |

---

## Part 2 — Improvement plan

Prioritized by the owner's bar: **biggest-gains / smallest-change / least-regression; judge by practical
loop output, not field coverage.** Methodology gate (writing-skills + skill-creator + skill-evaluator):
**every change is RED-first**, baseline observed before building, `eval-skill.py contest-refactor` stays
≥90, all `_*_selftest.py` exit 0.

### W1 — Reconcile the `analysis/` gap corpus with source *(cheap, high-leverage, zero skill-behavior risk)*

The audit proved the docs misdirect: SARIF marked "defer" but shipped; cycle/import-graph rows blank but
shipped; phantom gates G34–G43 cited though canon stops at G32; the "ship-fields-as-v4" lines stale
(v4 already taken by the HALT-challenge schema); SKILL-TDD "never observed baseline" premise stale.
Left as-is, the next audit re-chases closed gaps.

- Add a `CURRENT-STATE (2026-06-28)` header to each `*-GAP.md`: one of `SHIPPED / COVERED / PARTIALLY-COVERED
  / DEFERRED / REJECTED / OPEN`, with the source citation from Part 1.
- Correct the four factual stale spots (SARIF, audit_boundaries, gate ceiling, the specific "ship-as-v4" lines).
- Refresh `INVENTORY.md` / `SOURCE-STATUS.md` pointers.
- **Validation (reviewer-corrected):** `validate-repo.py` does **not** cover `analysis/` — it only checks the
  `contest-refactor` skill tree. W1 is validated by **source-citation review** (every CURRENT-STATE header
  cites a verified file:line) plus an optional lightweight doc-internal-consistency check (no dangling refs to
  phantom gates). Do **not** claim `validate-repo.py` green as W1's gate.

### W2 — Bad-codebase loop-replay regression harness *(the one genuinely-open feature worth building)*

Closes the real half of SKILL-TDD Gap A. **Reviewer-corrected scope** — Rev-1 wrongly claimed the runner
"already exists"; it does not. `scripts/dry-run.sh` is a **Step-0 preflight** (read-only, no loop, no commit);
the A1a/A1b verification proved the *method* by spawning a full loop via the `trust-model.md` loop **template**
inside an agent — that was a one-off, **not a committed runner**, and its `OrderCalculator` target lived in
scratchpad. So W2 must **build a new committed materializer/orchestrator** (or productionize the
`evals/reviewer-cases/` materialization pattern). Built RED-first per the Iron Law:

1. **RED** — add ONE fixture (`evals/loop-fixtures/<id>/`: a seeded bad codebase + `expected.toml`) and
   `scripts/_loop_replay_selftest.py` asserting the fixture is registered/well-formed → fails (no fixture/runner
   yet). Demonstrate the gap: nothing today replays a full loop end-to-end against a codebase.
2. **GREEN** — minimal committed orchestrator: materialize fixture (copy → `git init/add/commit`) → run one loop
   (host-dispatched, via the verbatim `trust-model.md` template) → assert **both** structural **and** semantic
   invariants:
   - *Structural:* artifact passes `validate-artifact.py --mode strict`; `loop_result.targeted_finding_status`
     present and valid; routing `priority_1_finding_id` set; G18/G19/G22 green; commit-subject format.
     *(Reviewer-corrected: drop `targeted_finding_id` — that field lives in reviewer-case TOML, not the emitted
     `CURRENT_REVIEW.json`.)*
   - *Semantic (the part that makes it not eval-theater):* at least one finding-content check from `expected.toml`
     — the emitted finding's **category/severity/primary_file** matches the planted debt, and the targeted
     dimension moves in the expected direction. **Name the exact observable** (reviewer-flagged, else the harness
     is flaky): the targeted dimension's entry in the emitted scorecard **`dimension_scores[<dim>]`** rises versus
     the fixture's recorded pre-loop score, **and/or** `loop_result.targeted_finding_status == "resolved"` for the
     planted finding. Without this, a syntactically-valid artifact that **missed or mis-targeted the debt** passes
     every structural gate. Still **not** full golden-diff matching (brittle).
3. **Scope guard** — one fixture, the common Critic→Architect→Execution path; framed as a **first smoke harness**
   with one semantic assertion (not HALT/retirement tails). Measurement is host-dispatched (repo is stdlib-only),
   mirroring the existing Layer-2/3 posture; document that it runs **on demand at schema/behavior bumps**, not
   automatically per commit.
4. **Gate** — `eval-skill.py contest-refactor` ≥90; full `_*_selftest.py` sweep exit 0; W2's own
   `scripts/_loop_replay_selftest.py` (RED→GREEN). *(Reviewer-corrected: W2's gate is its own selftest, not W1's
   source-citation check — those are separate deliverable gates; see Part 3 for the W1→W2 prerequisite ordering.)*

Value: catches schema↔behavior drift the artifact-fixtures (static) and judgment-scenarios (no real loop) can't.
Cost: **honest — a new committed orchestrator is required**; the A1a/A1b run proved feasibility, not a reusable asset.

### W3 — Additive fields: DEFER with honest rationale *(reviewer-corrected — not "decline on doctrine")*

Peer review correctly flagged that two Rev-1 "DECLINE on doctrine" calls were **rationalization-as-doctrine**:
the cited doctrines do **not** forbid the fields. Reframed as honest DEFER (the case against is cost/consumer,
not principle), so the decision is defensible and doesn't resurface mislabeled:

| Field | Verdict | Honest rationale (doctrine does NOT forbid it) |
|---|---|---|
| `confidence` enum | DEFER | The proposal is `high\|medium` only (Layer-1-only candidates dropped, not emitted) — that is **compatible** with "no low-confidence padding" (`validation.md:181`), even *enforces* it. Real reason to wait: adds ceremony with **no current consumer** and no measured practical-output gain. Not a doctrine conflict. |
| ROI tiers / effort estimates | DEFER | `priority` stays ground-truth; ROI would be an **optional ordering signal**, which the `audit_cochange.py` doctrine permits (it forbids co-change becoming a **score/gate**, not an ordering hint). Real reason to wait: "annual-savings-hours" inputs are **speculative**, plus maintenance cost and no consumer. The doctrine-consistent shape, if ever built, is another `audit_cochange.py`-style candidate-evidence tool (`promotion_allowed:false`). |
| per-hunk `changed_hunks[]` + `tie_kind` | DEFER | Refinement on working file-level `targeted_finding_status` tie-back; adds a v5 bump + a hunk-counter the doc admits LLMs do unreliably. Revisit only if a consumer needs hunk granularity. |
| `refactoring-patterns.toml` + `[Pattern]` commit prefix | SKIP | Pure vocabulary coverage; no practical-output gain (uncontested by reviewers). |

### W4 — Deferred / owner-decision (do not start without explicit request)

- **CRITIC-INDEPENDENCE Gap A — Execution-unfuse** *(moved here from the Rev-1 "covered" bucket).* The owner's
  own gated item: split the within-loop Critic↔Actor boundary. Needs an **execution-grain safety test** first
  (does a lower-tier/separate executor correctly apply a plan + narrow-revert + handle Meta-Rule-4 risk
  boundaries). Structural (touches Loop Isolation / single-writer lease / LOOP_STATE). Conscious defer.
- **CLEAN-ENV A — fresh-checkout/worktree validation before HALT_SUCCESS** *(moved here from "covered").*
  Opt-in `--worktree`-style fresh oracle; minutes/loop cost; catches untracked/gitignored drift G21 can't.
- **Declarative boundary-rule config** (GOVERNANCE C remaining half) — `[[boundary_rules]]` in
  `project-config.md` consumed by `audit_boundaries.py` as candidate-evidence. Build only against a real layered target.
- **Cross-family challenger** (CROSS-MODEL) — measured & parked; ship only if the owner accepts a cross-*provider*
  runtime dependency. Re-confirm value via the disagreement-probe recipe in `reviewer-model-experiment.md`.
- **Parallel-critic mode** (CRITIC-INDEPENDENCE B) — large; defer until there's a consumer.

---

## Part 3 — Recommended sequence & open decisions

**Recommended order:** W1 (now — cheap, unblocks honest future audits) → **W3 decisions recorded** (so the W2
fixture's `expected.toml` assertion surface is bounded by settled schema decisions — *reviewer-flagged
dependency*) → W2 (the one real feature, RED-first, with the new committed orchestrator) → W4 only on explicit
request. **W1 is a prerequisite for W2, not merely an owner-scope choice** (*reviewer-flagged*): the W2 fixtures
and their `CURRENT-STATE` references depend on the reconciled docs, so W1 must land before W2 even though it is
docs-only. (Decision 1 below still asks whether you want W1 *at all*; if yes, it precedes W2.)

**Decisions for the owner:**
1. **W1 in scope?** The `analysis/` corpus is contest-refactor's own (git-tracked) workspace — reconciling it fits
   "contest-refactor only," but it's docs, not skill code. Proceed?
2. **W2 — build the loop-replay harness?** Now honestly scoped: a **new committed orchestrator** + one fixture +
   structural **and** semantic assertions. This is the single net-new feature the audit endorses.
3. **W3 — confirm DEFER** on confidence / ROI / per-hunk (honest rationale, not doctrine), SKIP pattern-vocab?
4. **W4** — leave parked unless you name one (CRITIC-INDEPENDENCE A / CLEAN-ENV A / boundary-rules / cross-family / parallel-critic).

Plan was dual-peer-reviewed (codex `gpt-5.4` + copilot `claude-sonnet-4.6`, both REVISE round 1, convergent, all
findings source-verified). **Round-2 confirmation (codex `gpt-5.4`, high effort) → `VERDICT: APPROVED`** — all 5
blocking + 4 non-blocking round-1 findings confirmed RESOLVED, no new blocking defects; two new non-blocking
clarity nits (W2-gate decoupling from W1; name the `dimension_scores` observable) folded into Rev 2.

---

## Change log — Rev 1 → Rev 2 (peer-review adjudication)

All findings below were **source-verified** before acceptance (not taken on the reviewer's word).

| Finding (reviewer) | Disposition | Source check |
|---|---|---|
| CRITIC-INDEPENDENCE A falsely "covered" (codex B1 / copilot B1, both HIGH) | **ACCEPTED** — reclassified GENUINELY-OPEN, routed to W4 | `trust-model.md:52-54` still fuses Step 1+2+3; cold reviewer/challenger are post-hoc complements |
| W2 asserts non-existent `targeted_finding_id` (codex B2) | **ACCEPTED** — swapped to `loop_result.targeted_finding_status` + `priority_1_finding_id` | `targeted_finding_id` only in `evals/reviewer-cases/*/case.toml`; real fields at `output-format-json.md:265`, `trust-model.md:81` |
| W2 structural-only = eval theater (codex B2 / copilot B3) | **ACCEPTED** — added a semantic finding-content invariant | — |
| W2 "runner already exists" overstated (codex B3 / copilot B3) | **ACCEPTED** — W2 now builds a new committed orchestrator | `dry-run.sh:2-4` is a Step-0 preflight, not a loop runner |
| CLEAN-ENV A overstated as "covered" (codex B4 / copilot B2) | **ACCEPTED** — reclassified OPEN → W4 | G21/dirty-tree are same-worktree; G32 fires only `schema_version >= 4` (`validation.md:152`) |
| W3 confidence/ROI declines = doctrine-as-rationalization (codex B5 / copilot N2) | **ACCEPTED** — reframed DECLINE → DEFER on honest grounds | `validation.md:181` bars emitting low-confidence findings, not a label field; co-change doctrine bars score/gate, not ordering |
| TWO-LAYER "behavior enforced" too strong (codex N1 / copilot N4) | **ACCEPTED** — downgraded to PARTIAL with named residual | G3 checks field-population, not that Layer-2 verification occurred |
| SCHEMA 7 audited_areas overstated (codex N2 / copilot N1) | **ACCEPTED** — downgraded to PARTIAL (2 of ~9 dims) | G24/G25 cover `test_strategy`/`concurrency` only |
| W1 validation cites `validate-repo.py` which doesn't cover `analysis/` (codex N3) | **ACCEPTED** — W1 now validated by source-citation review | `validate-repo.py` has no `analysis/` reference |
| Stale-doc schema-arithmetic claim too broad (codex N4 / copilot N3) | **ACCEPTED (scoped)** — narrowed to the specific "ship-as-v4" lines; noted the doc's v4→v5 self-correction | v4 already shipped (12 fixtures); doc already has a v4→v5 section |
| W3 should precede W2 fixture design (copilot N5) | **ACCEPTED** — Part 3 sequence now W1 → W3 → W2 | — |
