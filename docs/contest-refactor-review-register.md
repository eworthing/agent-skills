# `contest-refactor` review register

The consolidated living record for the skill: every still-open review finding, adjudicated
disposition, backlog row, and the cost-ranked work order. Started life as the 2026-08-20
whole-skill code review (`contest-refactor-code-review-2026-08-20.md`; renamed 2026-08-20) and
absorbed the retired deep-dive backlog, behavioral-validation ledger, June research doc, and
runtime-cost audit.

**Review date:** 2026-08-20
**Peer-reviewed:** codex `gpt-5.6-sol` (xhigh), 11 rounds, 2026-08-20 — rounds 1–10 returned REVISE with 60 findings total, every finding verified against the repo before adoption and all 60 adopted; round 11 **APPROVED** with zero findings. Revisions are commits `a88da54`…`c5debd4`.
**Scope:** `/Users/Shared/git/agent-skills/contest-refactor`
**Review passes:** 2 code-review passes + 1 ponytail whole-skill audit + 1 duplication/clarity pass + 1 full revalidation + 1 cross-doc merge (deep-dive backlog, behavioral ledger, June research doc)
**Revalidated:** 2026-08-20 against HEAD `cc3057b`. All five P1 and four P2 findings re-confirmed: every citation re-checked and all five reproductions re-run against the current tree (the two synthetic ones rebuilt from scratch). No finding overturned. Two findings' subject matter moved in the interim without resolving them — `a9ad8f3`/`e3f5aa8` added `challenger_isolation`/`reviewer_isolation` *recording* while the independence check stayed report-only, and `a9ad8f3` deleted the dead `validate-artifact.py` instruction the loop-path finding discusses. A dozen metrology corrections (counts and line spans) are folded in below; none changes a conclusion.
**Verdict:** **Request changes.** Five P1 execution/certification gaps and four P2 contract/test-oracle gaps remain, plus one inherited P2-class compatibility defect ([I1]). The second pass confirmed all six original findings, strengthened the dirty-tree finding, corrected two proposed remedies, and added two report-only hard-gate findings. The separate ponytail pass found two material simplification cuts and one exact dead-code cleanup. A third pass, run with the skill's own advisory audit tools pointed at the skill, added one P2 contract finding, four behaviour-preserving duplication cuts, and one test-coverage gap. A cross-doc merge validated the still-open findings from the deep-dive backlog, the behavioral ledger, and the June research doc, adding one P2-class compatibility defect ([I1], live on the repo's own artifact) and three smaller gaps ([I2]–[I4]).

**The chronological run log split out 2026-08-25.** Every dated production-run and
root-caused-incident section that used to open this document — the 2026-08-20 fleet run, the
2026-08-21 run kit and run_id/G17 packet, instrumented runs #5–#7, and live run #8 — now lives in
[`contest-refactor-run-log.md`](contest-refactor-run-log.md), so new run entries stop crowding out
this standing reference. This document keeps the skill's standing findings, coverage snapshot,
ponytail/duplication audits, and cost-ranked work order.

**A validated, unbuilt eval gold-corpus proposal** — real expert-reviewed Swift refactoring PRs,
RED/GREEN/NEAR-MISS/MUTANT derivation, executable hidden oracles — lives at
[`contest-refactor-gold-corpus-2026-08-25.md`](contest-refactor-gold-corpus-2026-08-25.md); it
proposes fixtures under `evals/gold-corpus/` (not yet built) and belongs to the eval architecture
this register owns.

## Pending owner decisions

Four items are blocked on an owner call rather than on work, scattered across four documents.
Collected here for a single read; each entry names its source rather than re-arguing it.

### 1. G17 D2 disposition — false positive or true-but-trivial?

**Source:** `analysis/contest-refactor/run-kit/G17-ADJUDICATION-2026-08-21.md`. Four historical
datapoints await adjudication and all four checkboxes are unchecked. D1 (expected-blind, loop
compliant), D3, and D4 (both proposed TRUE violations) carry no blocking consequence in the
packet; D2 is the load-bearing one.

**The question:** is D2 (`2caa30e4b` — a **target-repo** sha, in BenchHype, not resolvable in this
repository; a docs-only rewrite the trigger flagged as an untested deepening refactor) a
**FALSE POSITIVE** (the packet's proposal), or a true-but-trivial violation?

**What it unblocks:** the G17 promotion bar (report-only → live enforcement), which requires zero
false positives among adjudicated datapoints.

**Options and costs:**
- Adjudicate FALSE POSITIVE → refine the trigger: add one condition to
  `contest-refactor/scripts/_artifact_coverage_citation.py` requiring at least one `changed_paths`
  entry that classifies as source. Specify that as a **positive** extension set — reuse
  `coverage_ledger.SOURCE_EXTS` (`contest-refactor/scripts/coverage_ledger.py:64`), the closest
  thing to a shared classifier in the tree, and document its extension ceiling rather than treating
  it as exhaustive. Do **not** define it as "anything that is not markdown": a blacklist makes
  JSON, asset, and configuration rewrites the next false positives. Plus a RED/restraint fixture
  pair and selftest cases, including a mixed source+docs case and restraint cases for
  representative included and excluded file types. Validator-side only, zero loop-token cost.
  **Timing is separable from the disposition:** the adjudication can be recorded now and the
  trigger change deferred until the next G17 measurement run is actually scheduled, since nothing
  consumes the refined trigger until then.
- Adjudicate true-but-trivial → no code change; the trigger stays as-is, at the cost of counting a
  docs-only rewrite as a violation.

**Either way:** promotion cannot close this cycle, and the language gap is not the only reason.
The live tally in the source packet is **4/5 applicable runs, 0/2 restraint cases, 1 of 2 required
languages (all Swift), and all four dispositions still unchecked**. This decision clears the
false-positive blocker only; three other bar conditions remain open. Adjudicating D1, D3, and D4
in the same administrative pass costs nothing and closes the checkbox gap.

### 2. Tier-3 validator pricing — schedule the build?

**Source:** `analysis/contest-refactor/TIER3-FEASIBILITY-GATE-2026-08-20.md`.

**The question:** commission the five-phase validator plus host-hook build.

**What it unblocks:** the register's most consequential open finding — the loop is told to run the
hard gates but never told to run the module implementing them, measured 0/2 in production. The
prose-only fix was measured dead (0/6 fire rate) and reverted; automatic invocation at a host
boundary is the only remedy left untried. A second model-invoked wrapper is not a cheaper
substitute — the 0/6 result rejects that class of fix directly, and a sentinel that reports the
module's output as absent cannot enforce itself unless something invokes the sentinel.

**Status:** feasibility gate PASSED/GO 2026-08-20. Threat model fixed at automatic invocation, not
tamper resistance (no supported harness offers privilege separation today). One qualifying
interception point was demonstrated — claude_code `PreToolUse`, in an isolated scratch repo,
firing with zero model cooperation and blocking a commit fail-closed. Both stated prerequisites
have since shipped: the ruleset-epoch classifier (`60e1294`) and G29 version enforcement
(`d46360b`). Nothing upstream blocks starting.

**What it costs:** ~250–400k validator-side. The hook build itself is explicitly unpriced — "the
owner prices it."

**The scope estimate is stale — reprice before commissioning.** The ~250–400k figure is costed
against the 2026-08-20 design snapshot, and two things have moved since. The gate count in that
snapshot ("27 hard gates") no longer matches the tree: at HEAD there are **32** distinct
`check_g<n>` implementations across `contest-refactor/scripts/*.py`. And `5f74abc` shipped
`validate-artifact.py --gates`, a phase-targeted battery selector — part of what the five-phase
design was scoped to build now already exists. A refreshed phase-to-gate matrix against G1–G50 and
the existing `--gates`/G47 phase facilities is a prerequisite to any credible total price.

**Caveat:** only claude_code's interception point was demonstrated, and that demonstration was a
substring-matching stub. The other four harnesses are documented, not demonstrated. Opencode — the
runner on the two production runs behind the 0/2 measurement — is named to demonstrate first once
the build starts. (Opencode is not the runner on *every* instrumented run: the log has #5 opencode,
**#6 codex**, #7 opencode.) Whether that demonstration is a precondition to commissioning or the
first funded phase is itself part of this decision.

**A cheaper boundary exists and the feasibility gate never evaluated it: native Git hooks.** The
whole design assumes a *harness-specific* interception point, one integration per runner, none of
which is demonstrated except a claude_code stub. But `pre-commit` and `commit-msg` are runner-
agnostic, fire on the same boundary the design targets, and give exactly the two things it needs —
the staged tree and the drafted commit message. This is not speculative here: **this repository
already runs them** (`.githooks/pre-commit`, `.githooks/commit-msg`, `core.hooksPath=.githooks`),
enforcing vendor integrity (`sync_common`), module size, and ruff on every commit. The eval guard is
the instructive case rather than a fourth enforced check. It runs **report-only at `pre-commit`,
always exiting 0** — git has not obtained the commit message at that stage, so it structurally cannot
see a waiver trailer and must not block on its absence. The separate `commit-msg` hook is the correct
enforcement *stage* and CI the intended backstop, but **neither blocks today**: `REPORT_ONLY = True`
(`common/scripts/eval_guard.py:72`, checked at line 359) makes every stage advisory until it is
flipped (`common/README.md`). What the hooks actually enforce right now is vendor integrity, module
size, and ruff. The point for Tier-3 stands regardless, and is about mechanism rather than this
guard's current setting: the pre-commit/commit-msg split is precisely the
staged-tree-then-drafted-message boundary the design needs, already wired here.
One integration would cover all five harnesses instead of five separate ones. The accepted limitation
is `--no-verify`, which bypasses them — acceptable under the stated threat model (automatic
invocation, *not* tamper resistance) and no weaker than a harness hook the operator can disable.
This decision should not be settled before that comparison is on paper: coverage, installation into
a target repo the loop does not own, rollback, and the `--no-verify` gap, against the
harness-specific alternative.

**A bounded first phase exists as a third shape**, between "commission the full five-phase build"
and "defer": (1) **compare native Git hooks against harness-specific interception** and either
adopt them or rule them out with evidence; (2) refresh the phase-to-gate matrix against G1–G50 and
the existing `--gates`/G47 facilities; (3) price a pre-commit MVP that runs the final-artifact gate
subset automatically and accepts the G22 draft from the hook, with decision 3's early-commit
incident as a rejection case; (4) add earlier and post-commit phases only where the refreshed
matrix shows value unavailable at pre-commit. Only the demonstration for whichever boundary wins
step 1 needs building — if Git hooks carry it, the per-harness demonstrations may never be needed.

**What is actually fundable today, stated plainly.** Steps 1–2 above are *discovery*: they have no
token cap and no price, so they are a scoping proposal, not a line item an owner can approve as
written. Steps 3–4 are *build* and cannot be priced until steps 1–2 finish. So the live choice this
week is narrower than it looks:
- **Fund a capped discovery phase** — the Git-hook-vs-harness comparison plus the phase-to-gate
  refresh, under a token ceiling the owner sets now, delivering a priced MVP proposal as its output.
  This is the only option here that can be approved today.
- **Defer** — accept a continued enforcement gap, mitigated by pausing unattended production runs or
  having the operator invoke validation manually.
- **Commission the full build** — available, but priced against a snapshot the packet has already
  shown to be stale; approving it means accepting an unknown total.

### 3. Preflight auto-commit — what enforcement does an already-violated rule get?

**Source:** `docs/contest-refactor-run-log.md`, Instrumented run #5 (2026-08-23).

**What happened:** ~30 seconds into the run, inside Step 0, before any plan existed, the loop ran
`git add skills-lock.json && git commit` against the target repo (BenchHype, `5d85cc14` — a
target-repo sha, not resolvable in this repository) — it tidied a pre-existing dirty file on its
own initiative.

**This is not an open posture question.** The rule already existed and the run broke it. `3906fb2`
(2026-08-20, three days before the run) rewrote Step 0 sub-step 4b to require a clean
tracked-and-untracked tree outside the six bookkeeping paths and to **abort, "no exception"**, on
anything left after filtering. The prescribed behavior on a dirty `skills-lock.json` was the
"commit or stash, then re-invoke" handoff. The loop instead made the tree clean by committing. So
the record shows a measured violation of a live contract, not an absent policy — recorded at the
time as "worth an owner call, not yet adjudicated," which framed it as a gap rather than a breach.

**What is actually open:** whether prose alone is the enforcement. Adopting "in bounds" would
weaken a safety boundary that already exists, with no evidence offered for the weakening. The
live question is the remedy, and it is the same shape as decision 2's: a rule the loop is told to
follow and demonstrably did not.

**Options:**
- **Mechanical guard at the commit boundary** (the reviewed recommendation): reject a
  target-repository commit whose staged paths and G22 subject do not match an authorized loop
  phase, read from a durable, mechanically-bound commit-intent source **still to be selected** —
  see the unresolved block below. `LOOP_STATE.json` covers only the two transitions it is alive
  for (the Step-3 commit and out-of-plan cleanup) and cannot be the source for the rest.
  **The condition must be a phase-aware allowlist, not "a Step-2 plan exists and Step 3 is
  authorized."** That narrower rule was drafted first and it would break the loop: `SKILL.md`'s
  guardrail is **one commit per durable transition** (`SKILL.md:284`), and Step 1 Routing legitimately
  commits well outside Step 3 — the `HALT_SUCCESS_candidate` archive commit, the separate promotion
  commit after the challenge holds, the CONTINUE-transition commit when a challenger *breaks* a
  candidate, `HALT_STAGNATION` (including the `verification_blocked` fail-closed commit),
  `HALT_LOOP_CAP`, and the out-of-plan cleanup commit. The allowlist must enumerate every durable
  transition, carry a positive acceptance case for each, and carry the preflight auto-commit as its
  rejection case.
  **Unresolved, and it must be resolved before this option can be built: what the allowlist reads.**
  `LOOP_STATE.json` cannot be the authority for most of those transitions. It is defined as a
  *mid-Step-3* checkpoint — "created at Step 3 sub-step 0 … deleted at Step 3 sub-step 11.f after
  the loop's commit lands" (`references/output-format-state-schemas.md:16`). It therefore exists at
  the Step-3 commit and the out-of-plan cleanup commit, and **does not exist** at any Step-1 commit:
  candidate archive, promotion, challenger-broke CONTINUE, or terminal halt. The v5 panel checkpoint
  does not cover the gap either, since no profile is v5-authorized today. Each transition needs a
  durable, mechanically-bound commit-intent source. The obvious candidate is `CURRENT_REVIEW.json` —
  it carries `state`/`system_flag`, `run_id`, `source_rev`, `candidate_fingerprint`, and
  `halt_success_challenge`, and it is itself staged in exactly these commits, so a hook could read it
  from the staged tree — but that is a **hypothesis, not a verified design**: it has not been checked
  for staleness across a crash, for the CONTINUE-transition case, or for whether the staged copy is
  reliably the authoritative one. Scoping this is part of the work, not a precondition already met.
  Whatever source is chosen must be tested for absence, staleness, crash recovery, and every positive
  transition.
  This is the same host-boundary mechanism decision 2 would build, so it is best sequenced as an
  acceptance case of that MVP rather than funded separately. Cost accepted: legitimate housekeeping
  needs a separate operator action and a re-invoke.
- **Prose-only restatement** — cheapest, and the option the 0/6 measurement in decision 2 argues
  against for exactly this class of instruction.
- **Explicit scoped exception:** allow pre-mutation housekeeping only under an operator
  authorization that names the paths and is recorded separately from the refactor plan.

**What it unblocks:** nothing is gated on this decision. It is an enforcement-remedy call whose cost
of deciding is near zero and whose cost of not deciding is recurrence on every future run.

### 4. Gold-corpus spend — build the first three fixture packs?

**Source:** `docs/contest-refactor-gold-corpus-2026-08-25.md`, "Open owner decisions". Two of that
section's sub-decisions are already settled and are not reopened here: `provenance_labeled`
timing (hidden mode is the primary build and run mode; labeled runs once as a batch calibration
pass) and schema vocabulary (`must_find`/`must_not_find` canonical, first-round names rejected as
aliases).

**The question:** commission the first three real-PR fixture packs (Swift Collections #688, #298,
SwiftNIO #2486).

**What it unblocks:** eval-corpus material for restraint, calibration, and execution — the axes
the register's own measurement history says have actually paid, as opposed to recall (measured
zero lift, repeatedly).

**What it costs:** ~500k tokens per pack-order-of-magnitude; ~1.5M for the first three, the same
approval shape as a detection-programme measurement run. That figure conflates two budgets that
should be approved separately: **construction** of the fixture packs, and **dispatch** of the runs
that grade against them.

**A one-pack pilot is the most defensible shape** — but see the next paragraph: it is not fundable
today either. `#298` is the cheapest of the three because it reuses the existing `#13`/`#15`
synthetic pair — which also makes it the only *matched* experiment available: the real-world
minimized fixture against its synthetic twin, measuring whether real-world shape adds discrimination
rather than assuming it does. Order-of-magnitude: one pack, not three.

**Naming the pilot is not the same as bounding it — the following must be written down before it
is approvable**, and none of it exists today:
- **Construction priced apart from dispatch.** Building the `#298` pack and running the graded
  comparison are two budgets with two go/no-go points; a single blended figure hides which half
  overran.
- **The experiment, preregistered.** Arms (real `#298` vs its synthetic `#13`/`#15` twin), grading
  model, repetitions, a token ceiling, and how an invalid trial is handled. The source document
  mentions a five-repetition two-arm shape but the packet neither allocates its cost nor commits to
  it.
- **The metric and its threshold.** "Out-discriminates its twin" is not yet a number. What
  separation, on what measure, over how many repetitions, counts as a pass — decided *before* the
  run, not read off the result.
- **What earns `#688`, and what ends the programme.** A stop rule and an escalation rule. Zero
  incremental signal, detected leakage, or high grader variance should end it; nothing currently
  says so in terms anyone could apply.

**So "fund a smaller slice" is not on today's menu.** Until the four items above exist, the `#298`
pilot cannot be approved any more than the three-pack spend can — listing what is missing does not
supply it. The live choice is:
- **Fund a capped design-and-pricing phase** — produce the split budgets, the preregistration, the
  threshold, and the stop rules, under a ceiling the owner sets now, delivering a fundable pilot
  proposal as its output. This is the only option here that can be approved today.
- **Defer the corpus entirely.** It is independent of decisions 1–3 and blocks nothing; the
  measurement history that justifies it (restraint and calibration paid, recall did not) will keep
  just as well for a quarter.

Of the two sub-decisions below, only the GREEN scoring rule is settleable now at no cost.
Closure-hardening splits into a free policy decision and a later spend — see there.

**The manifest validator is not yet the assurance this decision can lean on.** As of `e357a80`
`contest-refactor/scripts/validate-gold-corpus.py` exists and covers negative-oracle presence,
role-tag completeness, and leak checks — but it is **standalone: nothing invokes it**, and
`validate-repo.py` does not call it. Its own module docstring also records that the mutant-oracle
check verifies a *declaration* only, not that an executable oracle actually fails the mutant.
Wiring it into an invoked repository gate and giving mutants executable oracles belong in the
pilot's acceptance criteria, not in the case for approving the spend.

**Two smaller open decisions worth settling in the same pass:**
- **Closure-hardening runs — two decisions, not one.** The **policy** half is free and settleable
  today: *if* the SwiftNIO #2486 or Vapor packs are ever built, the bare-rubric control must be
  preregistered, because it is the evidence capable of reopening the parked DD-01/DD-03/DD-05 rows
  and the parks are reversible by design. The **spend** half — actually dispatching those
  model-graded control runs — is a separate, later approval and is not on today's menu: neither pack
  exists, and both fall outside a one-pack `#298` slice by construction (SwiftNIO is pack 3, Vapor is
  pack 7). Settling the policy now costs nothing and prevents the control being skipped or
  retrofitted after the fact.
- **Where GREEN anchors score.** Write down the rule before grading starts, aligned to the existing
  G5/G6/G37 semantics rather than invented for the corpus: **9.5** when the 9-anchor is met and a
  documented accepted residual remains; **10** only when no behavior-preserving, source-backed
  improvement remains; **below 9.5** only when an anchor is unmet or an actionable structural
  blocker stands. Expert acceptance (TCA, SwiftNIO #2959) is provenance, not an automatic score.
  Left unwritten, graders will invent the rule per case.

## Coverage — 2026-08-20 snapshot

**Current, 2026-08-25 (`a6dc71d`):** 102 fixtures, 79/79 selftests passing — see the run log's
Live run #8 remediation outcomes for the sweep that reproduced these. The numbers below are the
frozen 2026-08-20 review snapshot; kept for the record, not live counts.

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

**Status: CLOSED at spec level 2026-08-20 (`3906fb2`)** via the preferred clean-tree branch below, implemented as approved. G28 validates the new `out_of_plan_cleanup` checkpoint (18-case selftest); the `out-of-plan-cleanup-mid-restore` fixture covers the `restoring` subphase — the `committing`-subphase resume path is G28-validated and specified in resume-detection row 6c but has no executable replay yet.

**Source.** Step 0 explicitly permits non-overlapping dirt and promises those paths are excluded from narrow revert (`references/startup.md:31`). The desired overlap abort is also stated in the schema commentary (`references/output-format-json.md:223`), but the exact touch set is not selected until Step 2 (`SKILL.md:184-188`) and no operational recheck appears before Step 3 (`SKILL.md:191-197`). More importantly, Step 3 derives `loop_result.changed_paths[]` from the entire `git diff --name-only HEAD` (`SKILL.md:205`), which includes every pre-existing tracked difference, not only paths the loop touched. Rejection then restores every listed tracked path from `HEAD` (`SKILL.md:208`). The checkpoint's `pre_step3_blob_shas` also records committed blobs, not pre-existing working-tree bytes (`SKILL.md:197`).

**Consequence.** Any allowed pre-existing tracked edit appears in `changed_paths` even when it is outside the plan, but an unrelated path has no `pre_step3_blob_shas` entry and therefore no safe rejection branch. G28 can diagnose that mismatch only at Step 3 sub-step 8 (`SKILL.md:211`), after rejection already ran at sub-step 6. Separately, a first-loop plan can select a dirty path after the Step-0 check had no plan to compare; that planned path is snapshotted from `HEAD` and then restored to `HEAD` on rejection. The latter path directly erases user work.

**Smallest correction — the preferred branch, which closes both this finding and the next.** Require a clean tracked-and-untracked tree as a Step-0 precondition and state exclusive writership as an *assumed precondition, not a detected property* — without a provenance primitive, a concurrent write is indistinguishable from a loop write, so the register promises no detection. From a clean baseline, every post-Step-3-baseline delta — tracked content change or untracked creation, mechanically enumerated — is loop-owned *by construction*. On the normal path — no out-of-plan delta — every planned delta goes through reviewer input, `changed_paths`, G28, staging, and rollback; any out-of-plan delta instead puts the run into a **persistent halt that reuses existing machinery rather than inventing any**: transition to `HALT_STAGNATION` with `halt_subtype: "user_decision"` and a `halt_handoff` whose text names the out-of-plan paths and whose `expected_actions` enumerate the permitted operator dispositions (adopt the file into the plan, delete it, or abort the run). The halt is a **complete cleanup transaction**, not just a flag, and it must be crash-safe — and the mechanism is not an invention, because the repo already ships the exact pattern: `LOOP_STATE.json.phase == "halt_success_panel"` is a phase-scoped checkpoint with its own resume-precedence row (6b) that intercepts *before* the generic step routing. `out_of_plan_cleanup` is defined the same way: a canonical `LOOP_STATE.json` phase value whose checkpoint records the planned and unexpected path sets, a cleanup subphase (`restoring | committing | done`), and the halt-commit draft — with the landed commit detected by subject/tree match, so a crash *after* the commit lands but *before* its SHA is recorded is distinguished from a pre-commit crash instead of double-committing. It gets its own resume-precedence row ahead of the generic Step-3 routing (Case D must never see this phase), schema/G28 treatment for the checkpoint fields, and a completion lifecycle that clears the phase only after restoration and the halt commit are both verified. An interruption mid-cleanup therefore resumes by **idempotently finishing restoration and the halt commit** — never by falling into the generic Step-3 sub-step replay this halt exists to forbid. Then, before the artifact-only commit, every *planned* delta is restored from `pre_step3_blob_shas` (the in-progress edit was never reviewed, and the interrupted sub-step is never resumed, so restoring it loses nothing a fresh Critic plan would keep) while only the *out-of-plan* paths are preserved for operator disposition — otherwise the interrupted planned edit stays dirty, blocking the clean preflight, or tempts the operator to commit an unreviewed edit during adoption. The halt leaves `LOOP_STATE.json` in place and touches none of the preserved out-of-plan files. Each disposition has an **executable resolution route on existing machinery** — mid-sub-step resume is deliberately not one of them, because the machinery cannot represent it (`expected_actions` matches post-halt commits, deleting an untracked file produces no commit to match, and holding an uncommitted file for adoption would fail the clean-tree precondition): *delete* means the operator removes or reverts the named paths and re-invokes with `--reset`; *adopt* means the operator deliberately commits the paths as the new baseline and re-invokes with `--reset`; *abort* leaves the terminal halt standing. Re-entry always starts from the clean-tree preflight and a fresh Critic plan — the interrupted Step-3 sub-step is never resumed. Two boundary rules keep this executable. First, **cleanliness and out-of-plan detection are defined over source paths only**: the skill's own bookkeeping (`CURRENT_REVIEW.md`/`.json`, `REVIEW_HISTORY.md`/`.json`, `findings_registry.json`, `LOOP_STATE.json`) is carved out as a mechanically known allowance — `--reset` rewrites those files before Step 0 and Step 3 rewrites them again, so a literal whole-tree clean check would halt on the very machinery this design uses; artifact changes must also never enter `loop_result.changed_paths`. Second, this halt's `halt_handoff.expected_actions` are **advisory**: `--reset` takes precedence before drift handling, so the delete/adopt dispositions never surface in `prior_handoff_actions_taken` — the chosen disposition is recorded in the reset confirmation, derived deterministically from pre-reset observation — `committed`, `removed_or_reverted`, or `unverified` from the commit and path state, never from operator self-report, since a bare `--reset` invocation carries no disposition value. Replay cases: a planned edit, an unplanned loop-side-effect file, a deletion, a symlink, and **end-to-end cases for all three dispositions in which a planned edit and an out-of-plan side effect coexist, asserted per disposition**: *delete* and *adopt* run `--reset`, record the observed resolution, and reach the fresh Critic with the planned edit restored from its snapshot and the unexpected path carrying its disposition; *abort* performs no reset, emits no reset confirmation, preserves the unexpected path, retains the terminal halt, and dispatches no Critic. All three assert no artifact path appears in `changed_paths`. Plus **failpoint cases** interrupting cleanup around the planned-path restoration and around the halt commit, each verifying resume completes the transaction idempotently — planned paths return to **exact baseline equality** (presence or absence, content, file type, and executable mode, explicitly including planned deletions and symlinks), unexpected paths stay byte- and type-identical — without entering generic Step-3 replay.

**The dirty-tree-support branch is deferred, and deliberately unpriced.** Supporting pre-existing dirt requires distinguishing loop writes from other writes on a tree where both exist — a real provenance primitive (there is none today) — plus a defined, persisted halt/resume state for the fail-closed path. Until the register can name both mechanisms, pricing this branch would be pricing an unknown; Step 0's current allowance for non-overlapping dirt should be withdrawn when the preferred branch ships.

### [P1] Untracked files are absent from the implementation review and rollback set

**Status: CLOSED at spec level 2026-08-20 (`3906fb2`)** — closed by the same clean-tree branch: `changed_paths` is now the tracked+untracked union computed before the reviewer spawns, and the reviewer prompt receives the list and reads untracked additions.

**Source.** Step 3 populates `loop_result.changed_paths[]` with `git diff --name-only HEAD` (`SKILL.md:205`), while the implementation reviewer is told to inspect `git diff HEAD` (`references/implementation-reviewer.md:49-56`). Neither command includes ordinary untracked files. Rejection iterates only `loop_result.changed_paths[]` (`SKILL.md:208`). G28 checks that each *listed* changed path has a pre-Step-3 snapshot, but never checks for changed/untracked paths omitted from that list (`scripts/_artifact_history.py:748-773`).

**Consequence.** A loop-created file can be committed after an approval even though the reviewer never saw it. On rejection, the same file is not deleted, so it contaminates the next loop and remains outside the claimed rollback boundary.

**Second-pass confirmation.** The repository's own Layer-3 materializer runs `git add -A` before `git diff HEAD`, specifically so additions appear (`evals/README.md:952-959`). Production Step 3 has no equivalent pre-review staging instruction, so the eval topology masks the production gap.

**Smallest correction.** Closed by the preferred branch above: from a clean-tree baseline, untracked creations are post-baseline deltas like any other, mechanically enumerated and loop-owned by construction — planned ones flow through reviewer input, `loop_result.changed_paths`, G28, staging, and rejection cleanup; unplanned ones (exactly the escape this finding documents) trigger the persistent halt, surfaced and preserved rather than silently committed or silently left behind. Extend the reviewer-revert self-test with one loop-created untracked file and one loop-created *unplanned* file.

### [P1] Strict validation accepts a 9.5 score with no residual evidence

**Status: CLOSED at validator+fixture level 2026-08-20 (`ab44c63`)** — `check_g5_forward_residual_fields` enforces the forward half in strict mode; all seven violating fixtures repaired (retain branch, history-mirrored); the reproduction below is now the committed negative fixture `g5-residual-95-null-evidence`. Live-path closure still requires a guaranteed commit boundary (Tier 3), per the loop-path finding.

**Source.** G2 and G5 require every score in `[9.5, 10)` to name its residual and rationale (`references/validation.md:35-42`). The implementation explicitly skips that range and says the forward half is deliberately unmechanized because an expected-pass fixture violates it (`scripts/_artifact_residual.py:69-91`). The G5 self-test locks this bypass in as a passing case (`scripts/_g5_selftest.py:96-102`).

**Reproduction.** Starting from the complete v4 `halt-candidate-no-challenge` fixture, setting one 9.5 dimension's `residual_blocking_10` and `residual_rationale_or_backlog_ref` to `null`, keeping `residual_disposition: "accepted"`, mirroring the change into history, and recomputing the candidate fingerprint produced:

```text
python3 contest-refactor/scripts/validate-artifact.py <repro> --mode strict --quiet
validator_exit=0
```

The only output was the unrelated report-only challenge-independence warning.

**Consequence.** A `HALT_SUCCESS_candidate` can clear strict validation while omitting the evidence that distinguishes an earned 9.5 from an inflated score. G21 checks the score and `accepted` disposition, so it does not close this hole.

**Smallest correction.** Enforce the existing forward-half rule for every `[9.5, 10)` dimension. The repair bill is larger than one fixture: **seven** non-aspirational expected-pass fixtures currently violate the forward rule (mechanically re-scanned 2026-08-20) — `halt-loop-cap-clean`, `g45-exhaustion-preventive-honest`, and five `panel-*` fixtures (`panel-pending-ambiguous-raw`, `panel-pending-deferred-sibling`, `panel-rule6-continue-two-findings`, `panel-rule6-dedup-one-finding`, `panel-rule6-user-decision-stage2`). Repair all seven rather than preserving their invalid shape as the reason not to enforce the rule, and turn the reproduction above into a negative v4 fixture. Five of the seven are panel fixtures, so the panel disposition (ponytail item 1) taken first shrinks the repair to two.

### [P1] Terminal success does not require an independently run reviewer or challenger

**Status: CLOSED at validator level 2026-08-20 (`d46360b`)** — for current-epoch artifacts, terminal promotion requires `challenger_isolation == "subagent"` and an approved implementation review requires `reviewer_isolation == "subagent"` (rule ids `challenge-independence` / `reviewer-independence`); legacy keeps the print-only warning. `halt-terminal-held` — this finding's repro, itself accidentally legacy-epoch — repaired into a compliant current-epoch control, with `independence-missing` as its negative twin. The live-promotion half (the loop refusing a violating terminal mid-run) remains open, Tier-3-gated.

**Source.** The v4 schema says `challenger_isolation` records how the challenge actually ran, that top-level loop isolation does not imply it, and that absence means unverified (`references/output-format-json.md:131-143`). The checker documents a live terminal self-vet, detects inline or missing isolation, but is deliberately `REPORT_ONLY` and returns no issue (`scripts/_artifact_independence.py:1-38,49-126`). It only prints when `implementation_review.reviewer_isolation == "inline"` and does not even construct a reviewer issue (`scripts/_artifact_independence.py:83-88`).

**Reproduction.** The non-aspirational, expected-pass `halt-terminal-held` fixture claims valid G32 terminal success (`evals/fixtures/halt-terminal-held/fixture.toml:1-9`) but records neither reviewer nor challenger isolation. Strict validation prints `challenge-independence-unverified` and exits 0.

**Consequence.** `HALT_SUCCESS` can assert that an independent challenge held even when the artifact proves only that a model string was recorded. An inline self-review or self-challenge shares the context and anchoring that these passes exist to remove, so the terminal certification is materially weaker than advertised.

**Smallest correction.** For artifacts emitted by the current skill, require `reviewer_isolation == "subagent"` on approved implementations and `challenger_isolation == "subagent"` before terminal promotion. Scope compatibility with a schema bump or `skill_rev`; do not retroactively reject older v4 artifacts. Providers that cannot perform the required spawn should follow the existing fail-closed `verification_blocked` route.

### [P1] G17 is called a hard gate but cannot block an untested deepening refactor

**Source.** Step 3 requires G17 before commit (`SKILL.md:211`), and the reviewer contract says a deepening refactor with neither new tests nor a valid indirect-coverage citation must be rejected (`references/implementation-reviewer.md:94-108`). The structural checker detects the missing citation but is deliberately `REPORT_ONLY`, prints each issue, and returns an empty list (`scripts/_artifact_coverage_citation.py:1-19,124-208`).

**Reproduction.** Both `g41-cap-loop-executed` and `reviewer-retry-then-success` are non-aspirational `expected_result = "pass"` fixtures (`evals/fixtures/g41-cap-loop-executed/fixture.toml:1-7`; `evals/fixtures/reviewer-retry-then-success/fixture.toml:1-6`). Each records an approved deepening change with only source paths and no `interface_test_coverage_path`. Running strict validation prints a G17 violation for each and exits 0.

**Consequence.** A model reviewer can approve a deepening refactor that has no test at the new interface, and the supposedly redundant hard gate still certifies the artifact. The fixture suite currently locks both violations in as valid successes.

**Smallest correction.** Enforce G17 for new current-schema emits, add valid citations or test paths to the two positive fixtures, and keep an isolated negative fixture proving the missing-citation case exits nonzero. Preserve old-artifact compatibility through the same version/`skill_rev` policy used for the independence fix. Since this was written, a promotion bar for flipping `REPORT_ONLY` was recorded in the behavioral-validation ledger (now merged here): **≥5 applicable runs, ≥1 observed true violation, ≥2 restraint cases, ≥2 languages** among the observed cases (the path classifier is the risky part and it is language-shaped), **zero unadjudicated blind lines, zero false positives, human-adjudicated** — the flip condition now exists in writing; the gap stays open until a run history satisfies it (live adjudication tally in *Carried from the ledger* below). And meeting that bar authorizes only the validator-side flip — this module is not on the production path (see the loop-path finding below), so the P1 closes only when a guaranteed commit boundary invokes the check.

### [P2] The current emission-version contract still tells agents to write schema v3

**Status: prose half CLOSED 2026-08-20 (`62d5a71`)** — G29's bullet now states the capability-derived version rule (v4 today; v5 only where panel_certification authorizes — none does) and defers to output-format-json.md as the authority; the canon-pinned gate title keeps its historical label (coordinated rename flagged). **Enforcement half CLOSED 2026-08-20 (`d46360b`)** — `check_g29_schema_version`: a current-epoch artifact's declared `schema_version` must equal the capability-derived version via the same `_panel_capability.emit_check` lookup the emitter uses (no hardcoded literal, no blocklist); with the manifest empty, every v5 declaration fails naming `no_entry`. `version-stale` pins the direction.

**Source.** The current format says capable profiles emit schema v5 and unentered profiles remain on v4 (`references/output-format-json.md:21-31`); the required-field example is v4 (`references/output-format-json.md:169-180`). G29 still says every artifact emitted by “this version of the skill” must use schema v3 and only describes v1-v3 mixed history (`references/validation.md:99-104`). Step 3 continues to require G29 before commit (`SKILL.md:211`). `validate-artifact.run_checks` has no G29/version-emission check at all (`scripts/validate-artifact.py:124-172`), and `check_schema_enums` does not validate `schema_version` (`scripts/_artifact_core.py:250-329`).

**Consequence.** The emit-time reference set contains mutually incompatible instructions. An agent that follows G29 can write v3 and thereby avoid all v4/v5-gated controls while strict validation still accepts the declared version.

**Second-pass reproduction.** Copying the complete expected-pass `halt-terminal-held` artifact, changing only current and latest-history `schema_version` from 4 to 3, and rerunning strict validation exits 0. The terminal challenge is no longer required because the artifact self-declared the stale version.

**Smallest correction.** Update G29 to the current v4/v5 capability rule and give emission one authoritative version decision. Either enforce that decision on new emits or stop describing G29 as a hard gate; retain per-entry compatibility only for reading genuine older history. Enforcement means **equality with the capability-derived current version** (v4, or v5 only where the routing contract authorizes it), not a blocklist of one stale value — relabelling to v1 or v2 bypasses a `!= 3` test exactly as v3 does, since no version check exists at all. Negative tests: every stale version, missing, null, and non-integer; positive tests: the allowed v4/v5 branches and genuine older history entries.

### [P2] Eight aspirational fixtures can pass for an unrelated failure

**Status: CLOSED 2026-08-20 (`13c947c`)** — validate-fixtures.py maps gate sub-rules onto canonical citations (`G<n>` ⇐ `G<n>-*`), the exemption self-corrects (`aspirational-gate-implemented` fires the moment a cited gate starts firing), two fixtures lost the exemption for real, bootstrap-repo reclassified `example = true`, and the four genuinely aspirational notes now cite a verified zero-emitting-code-paths scan. Follow-ups flagged: halt-success-bad's incidental G18/G5 noise; re-citing no-backlog-residual-accounting onto G37 (needs v4 upgrade).

**Source.** `validate-fixtures.py` checks only exit status for `aspirational = true` failures and skips the assertion that a cited gate actually fired (`scripts/validate-fixtures.py:443-499`). Eight fixtures use the exemption: `bootstrap-repo`, `continuation-post-commit`, `dry-run-halt-after-step2`, `dry-run-rerun-no-reset`, `halt-success-bad`, `incremental-then-halt-success`, `loop-state-post-commit-pre-delete`, and `no-backlog-residual-accounting`. Seven notes explicitly say strict mode currently fails on missing unrelated artifacts or that the intended rule is not implemented; for example `continuation-post-commit/fixture.toml:1-10`, `incremental-then-halt-success/fixture.toml:1-10`, and `no-backlog-residual-accounting/fixture.toml:1-10`. `halt-success-bad` says it now fails for the canonical G21 reason but remains aspirational (`halt-success-bad/fixture.toml:1-10`).

**Consequence.** A regression in the named continuation, resume, dry-run, full-reverify, or residual-accounting behavior can leave `validate-fixtures: OK (91 fixtures passed)` unchanged. The suite verifies that *something* failed, not the behavior each fixture claims to protect.

**Second-pass correction.** Removing `aspirational` in memory shows that `halt-success-bad` fires `G21-scorecard`, while its canonical citation is `G21`, so the harness reports `wrong-gate-fired`; `G18` also fires. `loop-state-post-commit-pre-delete` already satisfies its cited-gate assertion without the exemption, while `bootstrap-repo` cites no gate and the flag has no effect.

**Smallest correction.** First normalize emitted sub-rule labels to canonical gate IDs (or declare an explicit sub-rule mapping). Make each remaining fixture complete enough to fail only for its intended behavior. Then remove the exemption from `halt-success-bad` and `loop-state-post-commit-pre-delete`; reclassify examples with no mechanized assertion rather than counting them as gate coverage.

### [P2] Illegal terminal-to-active transitions do not fail strict validation

**Status: CLOSED at validator level 2026-08-20 (`d46360b`)** — the global `REPORT_ONLY` flag is gone; transition legality is enforced per-artifact for current-epoch histories. The dogfood artifact's real `HALT_LOOP_CAP→CONTINUE` at loop 10→11 is legacy-epoch and stays print-only — that is its recorded disposition. `transition-illegal-post-cap-continue` gained the epoch marker and flipped to expected-fail.

**Source.** The transition validator prints violations but deliberately returns no issues while `REPORT_ONLY = True` (`scripts/_artifact_transitions.py:23-30,55` and `scripts/_artifact_transitions.py:117-136`). The dedicated `transition-illegal-post-cap-continue` fixture declares `expected_result = "pass"` even though it contains `HALT_LOOP_CAP -> CONTINUE` without a reset (`evals/fixtures/transition-illegal-post-cap-continue/fixture.toml:1-7`).

**Consequence.** `validate-artifact.py --mode strict` exits zero for history that continues past a terminal state. Automation can therefore accept a run whose state history contradicts the canonical transition table. This is not hypothetical: the repo's own dogfood artifact trips the same checker with `HALT_LOOP_CAP→CONTINUE` at loop 10→11 (see [I1]).

**Smallest correction.** Finish the existing shadow rollout: set `REPORT_ONLY = False`, change the illegal-transition fixture to an expected failure, and keep the existing transition-table self-test as the restraint check for legal histories.

### [P2] The loop is told to run hard gates but never told to run the gate implementation

**Source.** Step 3 sub-step 8 instructs the agent to "Run hard gates G15 + G16 + G17 + G19 + G22 ... + G38 before commit" (`SKILL.md:211`); sub-step 5 does the same for G1 + G2 (`SKILL.md:204`). Neither names a command. `canon/validation-gates.toml` registers 46 gates, and 27 of them have a deterministic implementation (`grep -rhoE 'def check_g[0-9]+' scripts/*.py | sort -u`; the digit is required — a `[0-9]*` variant also matches helper names like `check_gate_sequencing`). But `validate-artifact.py` appears only three times across the entire loop-path reference set, and none is an instruction: once in a script inventory (`SKILL.md:294`) and twice as descriptive asides naming which sub-check is mechanized (`references/validation.md:42,66`). Compare `repo_map.py` (`references/method.md:46,82`) and `audit_clones.py` (`references/method.md:85`), which *are* invoked as steps.

**Consequence.** "Run hard gates" resolves to hand-checking against `references/validation.md` — 14,547 tokens, **17.3 % of the 84,276-token per-loop reload** — while a deterministic implementation of 27 of those same gates sits unexecuted. This is the delivery mechanism behind the two report-only findings above: flipping `REPORT_ONLY = False` on G17 or on the transition validator changes nothing on the loop path, because nothing on that path runs the module the flag lives in. Enforcement work lands in a component the loop does not reach.

A second-order effect compounds it. Registering `G<n>` obliges a `validation.md` checklist bullet, and `validation.md` is on the per-loop reload path — so every gate that gets mechanized makes the Critic's per-loop reading **longer**, never shorter. Nothing in the file marks a gate as mechanized, so the prose grows monotonically with the mechanization that was supposed to relieve it.

**This is measured, not inferred.** The behavioral-validation ledger's sweep #4 (merged into this document and deleted 2026-08-20; full text in git history) recorded it directly: across ~6 Step-3 passes over two production runs, in both inline and subagent isolation, the loop never ran `validate-artifact.py` (P2, **0/2**), while output-shaping prose was followed (P3, **2/2**). Run by hand against the same artifact the validator reported 15 WARNs mid-run and a real G17 violation at terminal. Corroboration: asked for concerns about its own run, the loop's provider hand-audited the artifact and produced 12 findings, **5 of which are defects `validate-artifact.py` already implements**.

**Smallest correction.** Invoke the validator outside the model's discretion — a host hook or a wrapper around the commit step — not a prose instruction. Adding "run `validate-artifact.py`" to the checklist is the obvious fix and is **already measured dead**: that instruction shipped 2026-08-19 (`ee21bc8`, the "Mechanical sweep" bullet in `validation.md`), fired 0/6 across two production runs, and was deleted 2026-08-20 (`a9ad8f3`) at a measured 64 tokens per loop. The full prose-instruction lifecycle — added, measured never firing, withdrawn — ran to completion in under 40 hours, between this review's first pass and its revalidation; the host-hook route is now the only one not yet tried. The ledger's own conclusion stands: *enforcement cannot be reached through an instruction that never executes.* Only once invocation is guaranteed does compressing the bullets it subsumes become safe; until then `validation.md` must keep carrying all 46. Two prerequisites before any hook ships. First, the retroactive-invalidation gap in [I1] — a hook that runs strict validation inherits the false failures on every pre-existing artifact. Second, from the runtime-cost audit (consolidated below): **a bare strict invocation is impossible at most loop phases.** G18 requires `len(loops) == current_review.loop`, which only holds after the Step-3 sub-step-9 append, so a Step-1 call fails on every normal pre-archive state; G22 reads existing git history and cannot see a pending commit subject; and the main-owned challenge transitions (held/broke/unavailable — where G32's 1,218 tokens of obligations live entirely) happen after the loop's last validation opportunity. The audit's stated prerequisite is a phase-aware validator with five declared phases (`step1-post-write | step3-prearchive | postarchive | postchallenge-precommit | postcommit`), per-phase gate sets, and commit-draft input.

## Ponytail over-engineering audit

**Boundary.** This pass covered only tracked material under `/Users/Shared/git/agent-skills/contest-refactor`. It excluded ignored/generated `.build`, `__pycache__`, and `.DS_Store` content from the line estimate. The P1/P2 findings above—including the three report-only validators—remain correctness work and are intentionally not recast as simplification opportunities.

1. `yagni:` `SKILL.md:140`, `canon/panel-certification.toml:5-39`, `plans/rec1-panel-certification.md:1-469`, panel scripts/evidence, and `evals/fixtures/panel-*` — remove the parked v5 panel stack from the shipped skill until a provider/model can actually satisfy its certification contract: the manifest has zero entries, the routing contract says no profile is v5-authorized, and the recorded owner decision parks the feature while v4 remains the live path everywhere. The 20 panel fixtures plus only the wholly attributable scripts, plan, canon, and recorded gate output total at least 14,666 tracked lines; mixed v4/v5 validator files and embedded prose are deliberately omitted from that estimate. **Owner decision 2026-08-20: RETAIN** — the parked stack stays; the seven residual-rule fixtures were repaired on the retain branch, and removal remains available later at the priced ~80k.
2. `shrink:` `evals/fixtures/*/{CURRENT_REVIEW.json,REVIEW_HISTORY.json}` and `scripts/validate-fixtures.py` — materialize the final history entry from `CURRENT_REVIEW.json` inside the fixture harness instead of storing it twice. G18 requires parsed equality, and 83 of 85 fixture histories repeat the current review as their last entry; after excluding the panel fixtures above, 63 histories still duplicate 9,485 lines. Keep explicit prefixes for multi-loop cases and explicit full histories for the two current nonmatches; this preserves the production artifact contract while removing roughly 9,400 net fixture lines. **Executed 2026-08-20 (`4d4f6ae`), retain branch:** 86 of 97 fixtures converted to `materialize_final_history: true` (net **−15,174 lines** — larger than the pre-fleet estimate because the corpus had grown), four kept explicit by design: the two mismatch-by-design fixtures, plus `transition-legal-multiloop`/`transition-illegal-post-cap-continue`, which `_transition_table_selftest.py` reads raw off disk and whose truncation would have dropped the exact transition under test — a consumer the original estimate did not know about.
3. `delete:` `scripts/audit_cochange.py:214-219` and `scripts/validate-repo.py:292-297` — remove `_has_python_sources`, `_has_swift_sources`, and `_enum_tokens_from_text`. The knowledge graph reports zero callers for the first two, and a repository-wide `git grep` across every tracked file returns only the three definitions themselves. The extension sets `_PYTHON_EXTS` / `_SWIFT_EXTS` remain live elsewhere (`audit_cochange.py:294,397,399`), so only the functions go. `_enum_tokens_from_text` was found by the third pass and is doubly removable: its entire body is `set(re.findall(...))`, so it is a redundant wrapper as well as an uncalled one. Fourteen dead lines total, no replacement needed. **Executed 2026-08-20 (`831f901`).**

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

**Status: SHIPPED 2026-08-20 (`4fee1c1`)** — ported behind a byte-identical old/new equivalence gate; the D5 golden and all 16 exit-site diagnostics unchanged; 338→247 lines.

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

The equivalence test is the deliverable, not the diff — with 30 importers, "the Canon object is unchanged" is the only assurance worth having. Two oracles, two lifetimes: the old-vs-new comparison is a **one-time port gate** that dies with the old implementation, so the lasting form in `scripts/_canon_selftest.py` asserts against a **committed golden snapshot** — all 21 Canon fields serialized (including `extra`'s keys and both map insertion orders) from the shipped canon *before* D1 lands. The golden also pins the canon *content*, so a legitimate canon edit updates the snapshot in the same commit — that is the point, not a nuisance. See **D5**, which is the reason to write that file whether or not D1 ever ships.

> Two mutations initially read as MISMATCH and were not: `verdicts` first occurs inside a comment so the replace hit the comment, and the scorecard id is `architecture_quality`, not `architecture`. Both were failing to *land*; old and new agreed on every row throughout. Recorded because a mutation that does not mutate is the commonest way a mutation test lies, and it lies reassuringly.

### [D2] `_load_validator` is copy-pasted into 14 files

**Status: SHIPPED 2026-08-20 (`ac839c5`)** — neutral `scripts/_selftest_lib.py` `load_validator(filename=...)`; aliased imports, zero call-site changes; `_ref_tree_lint` uses `filename=` for validate-repo.py; the two module-level-`VALIDATOR` selftests stay out by design.

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

**Do not unify first.** `evals/advisory_baseline.json`, `evals/principal_baseline.json` and both `*_replication.json` files are frozen historical records that must stay byte-identical, so a merged checker that is *stricter* would fail a committed baseline and one that is *looser* would silently stop checking something. Sequence it: (0) **adjudicate intent first, from the contracts, not from data** — and the contracts are distributed, not standalone documents: for each study, in precedence order when they disagree: the committed `prereg` block in its `*_replication.json` first; then schema/threshold rules that git history proves were frozen *before* dispatch; then the governing `evals/README.md` layer section. The baseline files' `measurement` blocks are post-run **evidence, not intent** — they never adjudicate what a check was *supposed* to be (selftest docstrings are commentary; a disagreement the order cannot settle goes to the owner). For each of the four asymmetries, record whether the check belongs to both contracts or is genuinely study-specific — historical baselines cannot answer this (a passing inapplicable check is not an omission, and a failing baseline may be exposing a real defect rather than a deliberate difference). (1) For each check adjudicated as shared, add it to the lacking copy with one synthetic positive and one synthetic negative case proving it executes — necessary because the sides are not symmetric: `advisory_baseline.json` contains **zero** `replication` blocks and both copies of `_check_replication` return immediately when no entry carries one, so a cross-applied check can pass vacuously there (the principal side, with 10 `replication` blocks and 35 recorded attempts, does exercise them). The frozen baselines then serve as regression evidence for the adjudicated contract, not as the intent oracle. (2) Only then factor the common core, passing the genuinely per-study checks in. Step 0–1 is the valuable half and is worth doing even if step 2 never happens.

**Adjudication record (step 0–1 executed 2026-08-20, `7d6f4b8`).** Intent oracle: prereg > git-provably-frozen rules > `evals/README.md`; measurement blocks are evidence, not intent. (1) `arm`/`VALID_ARMS` — **study-specific, advisory-only**: principal is prereg'd current-arm-only (`principal_baseline_replication.json` `confound_noted`; README "current-arm only"; its attempts carry no `arm` key; `967a845` predates and is independent of advisory's 3-arm `e6ec2de`). (2) Terminal slot scoped to `current` arm — **study-specific, advisory-only**, same citations; meaningless on a single-arm data model. (3) `headline_excluded` ⇒ `contaminated` — **study-specific, principal-only**: defined by principal's prereg `contamination_rule` and README's `abstraction-seam-flag` note; the concept appears nowhere in advisory's committed contract. (4) No retry attempt after a valid attempt 1 — **shared**: principal's prereg `invalid_output_rule` plus README's unqualified Lever-1 K=5-with-one-rerun protocol; advisory's own attempt schema carries the exact fields and its commit message declares it "mirrors principal selftest". Cross-applied to the advisory copy keyed by `(arm, slot_index)`, with an in-memory synthetic positive+negative pair driving the real `_check_replication` (necessary: advisory has zero replication blocks, so real data exercises nothing). No owner-decision items; step 2 (factoring) remains deliberately unstarted.

### [D5] `_canon.py`'s 16 error paths are exercised by nothing

**Status: SHIPPED 2026-08-20 (`acd0bfd`)** — `scripts/_canon_selftest.py`: one case per each of the 16 `sys.exit(2)` sites, each asserting the diagnostic names the broken file, mutations guarded against failing-to-land, plus the committed 21-field golden. The expiring scratchpad discount was captured before loss.

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

**Correction.** `scripts/_canon_selftest.py`, feeding `load_canon` a `tempfile` copy of `canon/` with one file broken per case, asserting exit code 2 **and that the diagnostic names the file that was broken** — the wrong-file hazard from D1 is invisible to an exit-code-only assertion. Keep the committed 21-field golden-snapshot oracle in the same file (old-vs-new equivalence is D1's one-time port gate, not a lasting test). The 11 mutations from D1's proof are the seed, and they cover every *category* — but 11 cases cannot reach all 16 *sites*: the bar is **one case per `sys.exit(2)` site**, so extend the seed with the uncovered ones (canon directory absent entirely — `_canon.py:87`, hit by none of the 11 — plus the remaining inline per-entry sites) until each of the 16 is individually exercised. Seed categories: missing top-level key, key-not-a-list, duplicate gate id, gate entry missing `title`, duplicate scorecard id, scorecard entry missing `display_label`, multi-list file broken, optional file broken, canon file missing, canon file empty, canon file malformed.

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

Superseded. This section originally carried its own ordering, which drifted from the canonical one (it put D1 before D5, always placed D2 in the panel-named testkit, and predated D4's contract-adjudication step). The single authoritative sequence for these items is *Token-cost estimates and work order* below; D3 remains deferred to the next gate by design.


## Findings inherited from the deep-dive backlog, the behavioral ledger, and the June research doc

**Boundary.** A merge pass over `docs/review-skill-deep-dive-2026-08-17.md` (35-row backlog), `docs/behavioral-validation-ledger.md`, and `temp/contest-refactor_research.md` (2026-06-24), keeping only findings that are (a) defect-shaped, (b) still open at HEAD, and (c) not already covered above. Most of both documents dedups away: sweep #4's P2/P3 measurements are the evidence base of the loop-path P2 above; the G17 promotion bar is cross-referenced there; backlog item 12 became the transitions P2; rows 31/32 shipped the morning of this review (`a9ad8f3`/`e3f5aa8`); rows 1–4, 14, 16–22, 24–26, 29 are shipped, designed, measured-and-declined, or parked with recorded evidence.

### [I1] G43/G46 added required v4 fields with no version bump — the repo's own artifact now fails strict validation (backlog row 30)

**Status: SHIPPED 2026-08-20 (`60e1294`)** — `scripts/_ruleset_epoch.py`: two-epoch classifier (`legacy`/`current`) keyed on `skill_rev` presence + short-SHA shape, `REQUIREMENT_EPOCHS` matrix as data (G43/G46 first clients; slots reserved for independence, transitions, rounds, G29, G17). Fail-closed toward legacy — retroactive rules never fail an unprovable artifact; the dogfood artifact drops 10→0 strict issues. Marker-less current emits go unchecked by scoped rules; the emitter obligation at output-format-json.md's `skill_rev` note records this. Both gate selftests and the 4 negative fixtures now carry markers; `g46-current-epoch-fields-missing` pins the current-epoch direction. Per-commit epoch ordering was rejected on evidence (bare short SHAs are unorderable without a live repo).

**Re-validated at HEAD.** The repo's own dogfood artifact (`CURRENT_REVIEW.json`, loop 15, `HALT_LOOP_CAP`, committed 2026-08-05, `schema_version: 4`) fails `validate-artifact.py --mode strict` with **10 issues**: 3 × G46 (`finding_family`/`effort`/`repair_revalidation` required; gate landed 2026-08-18) and 7 × G43 (convergence-pass records owed; landed 2026-08-06). Both gates added required v4 fields without a bump or default-fill — the pattern `output-format-migrations.md` itself forbids by example (v2→v3 bumped *and* shipped a default-fill table). `skill_rev`, the field designed to scope rules to rulesets, is **null on this artifact**, so ruleset-scoping has no signal for existing history. The correct pattern ships one gate over: G19 is deliberately type-only, and this week's isolation fields used optional-with-shape-gating for exactly this reason.

**This blocks the loop-path P2's remedy.** `validate-artifact.py` cannot safely be wired into the loop or run over `REVIEW_HISTORY.json` until an old artifact can be judged by the rules in force when it was emitted — enforcement-by-hook inherits this problem on any repo with pre-existing artifacts.

**Corroboration found during this validation, free of charge:** the same artifact also trips the report-only transition checker — `[transition-violation HALT_LOOP_CAP→CONTINUE loop=10->11]` — so the illegal-transition P2 above now has a real-data instance in the repo's own history, not just a fixture.

### [I2] `implementation_review.rounds` is specified and never read (backlog row 33)

**Status: CLOSED at validator level 2026-08-20 (`d46360b`)** — `_artifact_review_contract.check_rounds_membership`: current-epoch `rounds` must satisfy `type(rounds) is int and rounds in (1, 2)` (bool excluded); legacy null-emitting artifacts tolerated. The conditional-coupling clause stays an open residual as this register specified.

`output-format-json.md:440` specifies `rounds` as an int counting reviewer invocations, and its comment already fixes the value set — "1 normally; 2 when conditional → re-spawn" — so the value-set decision this register previously listed as open is in fact already made by the spec. **The check this register commits to is the membership check**: after [I1], `rounds` is *required* on current-ruleset emits and must be an exact integer in `{1, 2}` — exact meaning `type(rounds) is int`, since Python's `bool` is an `int` subclass and `True ∈ {1, 2}` — with null tolerated only on scoped older artifacts. Selftests: missing, null, boolean, out-of-range, and an old-artifact compatibility case. The contract's second clause — `2` is legal only after a conditional first pass — is *not* enforceable and **remains an open residual of this finding**: the artifact carries no durable first-pass verdict evidence to corroborate against, so enforcing it requires a schema addition first, unpriced until someone proposes one. `grep '"rounds"' scripts/` still returns zero, and both BenchHype production loops emitted `null` unchallenged — so any *required*-presence enforcement retroactively invalidates those artifacts, the same defect class as [I1]. The membership check is therefore sequenced after [I1]; it is trivial once scoping exists.

### [I3] `source_rev` is ambiguous mid-loop, and `findings_carried_from_prior_loops` is emitted but specified nowhere (backlog row 34)

**Status: CLOSED 2026-08-20 (`62d5a71`)** — `source_rev` = HEAD sha captured at Step 1, pinned across the loop's own Step 3 commit (adjudicated from halt-verifier.md's oscillation key: `source_rev` must stay stable across artifact-only recommits while `candidate_commit_sha` moves); both definition sites identical. `findings_carried_from_prior_loops` specified as observed-only and ungated (`{stable_id, status, current_status}`); the two checked producers disagree on whether to emit it at all, recorded rather than papered over.

Re-verified: `source_rev` is defined twice as "HEAD sha of the analyzed source tree at emit time" (`output-format-json.md:126,193`) — *analyzed source* and *at emit time* diverge when Step 3 commits mid-loop, and two consecutive production loops read it differently. `findings_carried_from_prior_loops[]` is emitted by real runs and appears in zero reference files.

### [I4] The paired-arm harness does not record grading spend, against the ledger's own rule

Sweep #3 recorded arm dispatch per pair (27.9M context tokens) but grading spend for rungs 2–4 was never committed per call, so the study's total is not reconstructible — with grading projected at ~57 % of cost, **the majority of the sweep's spend is unmeasured**. `paired_arm_record_grades.py` still records no usage at HEAD. Companion observations from the same closed run, recorded in the ledger and still open: four arithmetically impossible usage records (classified incomplete-usage, arm-balanced), grader agreement of 1/58 on assertions but 1/14 on tiers (the fragility is the tier roll-up rule), and 7+ graders independently inventing the same unschema'd `outside_spec` field (a spec gap deferred to the next preregistration by design).

### Adjudicated, recorded here so the disposition is findable

- **Row 35, `repair_revalidation` unknown keys** — accepted debt with a written reopening trigger (unknown keys shown to *mislead audit interpretation*); deliberately not re-flagged.
- **Row 3 residual** — both dispatch-boundary selftests *enumerate* their sites (4 G14, 3 redaction), so a fifth boundary would carry neither hard rule and fail no test. Recorded closure: a discovery tripwire on prompt-bearing files when the next boundary is added.
- **Ledger, phantom-signal generalization** — the bare-model-id class got its class guard (`b2b96ef`); the phantom-detection-signal class (`OPENCODE_SESSION`, an env var opencode never set, degrading silently into a gate-approved fallback) has no equivalent guard yet.
- **The June research doc's program is almost fully adjudicated by later work:** change-coupling shipped as candidate evidence (`audit_cochange.py`), the context-sufficiency cap shipped as prose (measured: over-claim 2/5 → 0/5), the domain-integrity lens was parked on a measured recall lift of 0 (bare rubric 6/6), expert panels shipped as the v5 certification stack and are parked (ponytail item 1 above), and benchmark-first became the principal corpus plus the paired-arm study (Decision 3: retargeting not licensed). Two requirements were **never built and never formally adjudicated**: the Serious+ grounded `change_scenario` requirement and the minimal `tradeoff_analysis` requirement — `git log -S` shows no commit ever introduced either field. Given the judgment-lever program's measured zero recall lift, non-adoption is evidence-consistent; it is recorded here so it reads as a decision rather than an omission. The doc's remaining two proposals — a refactor-value taxonomy and a tangled-refactor detector — were self-deferred (P2/conditional) by the doc itself and stay deferred.

### Carried from the ledger at its deletion (operational state, not findings)

The ledger's merged findings are above; these four things were *live state* with no other home:

- **Pending probe P1 (`--scope`)** — never tested: neither production run passed the flag. The instruction shipped at `ae272ec`; whether the loop narrows the scan and records `discovery.source_roots` is unmeasured.
- **Pending A/A noise-floor run (backlog item 20)** — `evals/noise_floor.json` ships deliberately empty and `evaluate_lift()` returns `unreportable` for any key with no floor, so **no Tranche 3 lift claim is reportable until this runs**. It also supplies item 19's development-set outcomes (the discriminating-power classifier ships unfitted and refuses to classify). `required_n_for_power(0.10, 0.05, 0.80) = 778` discordant pairs — at this corpus size most honest verdicts will be `inconclusive`, which is the expected result. This is instrumentation that is complete as code and inert as measurement, by design.
- **G17 promotion bar** — full criteria stated in the G17 finding above. Updated 2026-08-25: the `G17-ADJUDICATION-2026-08-21.md` packet now carries **four** datapoints with proposed dispositions (2 true violations, 1 expected-blind-compliant, 1 proposed false positive), all Swift-only. All four disposition checkboxes in the packet are still unchecked, so human adjudication remains genuinely pending — only the count moved, not the bar's status.
- **Keyed probe (G29 emission version, `62d5a71`) — PASS, sweep #5 (2026-08-20).** Tier-2 Step-1-only loop replay of `duplicated-subtotal-1` (stock materializer, verbatim trust-model.md loop template plus a stop-after-Critic-emit addendum), fresh claude-sonnet-5 emitter, provider claude_code (not v5-authorized — no profile is). Emitted `schema_version: 4` — not `3` (the old prose's literal instruction) and not `5` (unauthorized). Two free secondary reads, both good: `skill_rev` was captured (`9e4f26c`, per the emitter-obligation sentence added this fleet) and strict validate-artifact reported zero content failures (only the two REVIEW_HISTORY-missing lines, correct for a Step-1-only scope). Spend: 33 API messages, ~266k fresh input, ~70k output.
- **Keyed probe (loop-ownership P1 pair, `3906fb2`) — PASS, sweep #5 (2026-08-20).** Step-3-only exec replay (Layer-5 mechanics, probe-grade — fixture NOT added to the pinned manifest): `apply-duplicated-helper-1` cloned to scratch with one delta — a green `run_tests.sh` (swiftc typecheck + two API greps) that writes an untracked `test-output.log` on every run, so the mandated sub-step-3 test re-run legitimately produces an out-of-plan delta; seed `discovery.test_command` set to `bash run_tests.sh`. The claude-sonnet-5 executor applied the planned fix, ran tests, computed `unexpected = {test-output.log}` at sub-step 6, skipped the reviewer, and ran cleanup 6.a–6.e verbatim: checkpoint restoring→committing→done, planned edit restored to baseline, artifacts-only G22 halt commit, `HALT_STAGNATION`/`user_decision` with all three handoff actions (delete/adopt/abort, correct `match_kind`s), tree clean except the preserved untracked byproduct, `LOOP_STATE.json` rename-then-unlinked. 16/16 mechanical checks; G35 passed on the emitted handoff. Harness notes (fixture age, not loop behavior): the seed's `reviewer_model: claude-sonnet-4-6`/`default` now trips G19 (the provider default moved to sonnet-5) and the seed `CURRENT_REVIEW.md` lacks several G1 sections — **both repaired 2026-08-20** (seeds bumped to the current default; all G1 sections rendered from the seed JSONs; `_exec_replay_selftest.py` now runs G19 on every raw seed so the next default move fails at selftest time, not mid-measurement). Spend: 51 API messages, ~207k fresh input, ~62k output.
- **Pending probe (wrapper adoption, item 14)** — keyed probe for the next sweep: does a loop given the sub-step-3 wrapped-run instruction actually invoke `attested_run.py` and cite the event, vs a no-guidance control leaving `execution_evidence: null` out of inertia (or to dodge the stricter gate)? 5+ reps per arm when run (design §6's behavioral flag; the gate mechanically working when the wrapper IS invoked is already selftested — adoption is the open question).
- **Sweep protocol** — LLM behavioral probes are batched (~3–5 pending, disjoint failure signatures, one keyed probe per change, measured spend recorded per sweep). Sweeps #1, #2, #4, #5 and the paired-arm study (#3) are closed; their results are quoted where merged above. Sweep #5 ran at batch size 2 (below the ~3–5 convention) deliberately: the third pending probe (`--scope`) is production-run-gated, and the two executable probes were the fleet's highest-risk unvalidated prose changes — holding them for a bigger batch bought nothing.

### Open backlog carried from the deep-dive at its deletion

Rows 30/33–35 were merged as [I1]–[I3] and the row-35 adjudication above. Rows already shipped despite stale status columns: 1, 2, 4, 7, 9, 10, 17–22, 28, 31, 32. Still genuinely open:

**Rows 23, 24, 25 and 27 moved 2026-08-21** to [`contest-refactor-detection-domains.md`](contest-refactor-detection-domains.md) — they are detection-reach items (what the loop looks for in the target codebase), and that document now owns them alongside the competitor domain sweep. Row numbers are preserved there for citation continuity.

| Row | Item | State |
|---|---|---|
| 5 | arm_b 2×2 factorial ({weak, strong executor} × {backlog, self-contained}) | Experiment protocol first; the 1×1 arm_b was measured 2026-06-28 and rejected |
| 6 | Confidence two-stage experiment (does the Evidence Chain lose information) | Two-stage experiment, unrun |
| 8 | Strictness as deterministic post-filter with pinned per-preset counts | RFC only. **Re-verified 2026-08-20: NO-GO for implementation** — blocked on item 6 (confidence-axis experiment, unrun) per the RFC's own prerequisites, and the RFC's post-filter-over-a-superset model is incompatible with current `--strictness` semantics (evidence bar for residuals, selftested finding-invariant via `_strictness_isolation_selftest.py`); building it needs an explicit owner decision (second axis vs. redefinition) plus loop-prose changes, precision/restraint fixtures, and periodic model sampling — not a contained script |
| 11 | Axis-split graders, each declaring the axis it does not judge | Candidate in Tranche-3 comparison |
| 13 | Cost-proportional stage skipping (`skip_when` by size) | Was gated on the runtime-cost audit, now consolidated below; the audit's measured cost model puts structural trims on a modestly-weighted axis, so weigh this against the behavioral levers first |
| 14 | Host-attested execution-evidence ledger | **SHIPPED at Tier 1, 2026-08-21** — `attested_run.py` wrapper (true-child oracle, shlex-canonical command pin, per-stream digests, degrade-on-mid-run-edit) + `_wtree.py` source-scoped fingerprints + G47 linkage gate (opt-in via `loop_result.execution_evidence`, phase-aware freshness, fail-closed taxonomy) + canon `attestation-statuses` (`attested` withheld until a Tier-2 writer exists). Plan dual-peer-approved: codex gpt-5.6-sol xhigh (4 rounds) + claude (fresh seat after agy degraded), every load-bearing git-behavior claim verified in scratch repos before adoption. Tier-2 privilege separation stays open by design (design §5 rows 2/6) |
| 15 | DAG-shaped grading | Conditional on node-pilot |

### Carried from the runtime-cost audit at its consolidation (2026-08-14 rev 3, retired 2026-08-20)

The audit itself is closed work: three peer-review rounds plus the 2026-08-20 round-4 confirmation (REVISE — see its record below), every rev-2 figure independently reproduced by the reviewer. Its shipped levers were re-verified at HEAD today — the canon-derived gate range (`SKILL.md:133,237`) with its `check_gate_range_freshness` pin, the Lever-E provenance carve (`validation-sources.md`, −3,073 tok/loop), the Lever-D budget guard (`token-budget.py --check`, ceilings since deliberately bumped at `cc3057b`), and the Lever-F reading-discipline recipe (`method.md:48`). Adjudicated negatives, recorded so they are never re-litigated: Lever B reviewer trims (**measured <0.1 % of real cost — do not revisit**), Lever C cap-default (withdrawn; the flag exists), narrative-prose trimming, cross-file dedupe, concision sweeps, and `evals/` size — all measured non-causes. The measured cost model behind all of it: **cost ≈ per-message resident context × messages** (~241 messages/run, 93.9 % cache hit — caching is not the leak); loop subagents are 66.8 % of cost; the unexploited leverage is behavioral (fewer assistant messages, read→extract→drop), not structural.

Still open, carried here:

- **No end-to-end before/after on a real run** — everything shipped was measured in isolation. One instrumented `/contest-refactor` invocation supplies the *after* arm; the *before* arm must come from the audit's recorded pre-lever transcripts if one proves comparable (same target, same scope) — otherwise two matched runs are needed. The audit calls this the cheapest remaining source of certainty, and it would advance (not settle) the next two items. (The two BenchHype runs since were behavioral-probe observations, not before/after cost measurements.)
- **Lever F's cost claim is underpowered** — −20.2 % median but 16/25 pairwise at n=5/arm; the robust half is quality (+67 % verified citations). Five more reps per arm settle it.
- **G43 is fixed but not re-baselined** — inside the instructed range since the fix, but its trigger needs a dimension answering `clean` three loops running (loop 4+), and no run since has gone past loop 2. The largest gate's live behavior remains unobserved.
- **Lever A (carving the 11 audited-clean gates' prose) is default-no** — three review rounds shrank its value (10,475 → 6,249 tok) while growing its prerequisites (clause-level coverage matrix with negative fixtures, the five-phase validator above, a pre-registered behavioral experiment across ten loop shapes). Revisit only if the real-run measurement shows the shipped work fell short.
- **Loop-count distribution unmeasured** (10 is a cap, not a mean; 15-loop runs appear in gate rationales).
- **Round 4 (confirmation) ran 2026-08-20** — codex `gpt-5.6-sol` xhigh over the recovered rev-3 text; verdict **REVISE**, five findings, all five verified against the doc before adoption. The doc stays retired; these are the reading corrections its citations need, recorded here so the historical record is citable honestly:
  - **B1 (HIGH, confirmed)** — the ranked-levers intro restores the exact "lower bounds; billed value is larger" interpretation the doc's own accounting model explicitly retracts ("no upper- or lower-bound interpretation"), and labels Lever E's **net** 3.6% (−30,667, post pointer add-back) as "gross" (the gross is 3.7%/31,760). **Reading rule for every audit figure quoted anywhere in this register: 3.6/3.7/7.3/10.0% are unique-load proxies with no billed-savings bound in either direction; the accounting-model paragraph is the correct reading, the ranked-levers sentence is the defect.**
  - **B2 (MEDIUM, confirmed)** — provenance undercount: the metadata says "corrected after two peer-review rounds" while the body cites round-3 corrections ("round-3 N6"; Open Risk 7). Correct history: **three** REVISE rounds preceded, rev 3 kept its number through in-place round-3 adoption, and the 2026-08-20 confirmation is round 4.
  - **B3 (MEDIUM, confirmed — already corrected at consolidation)** — the doc's "one run would settle open risks 1–3 at once" overclaims (an underpowered variance claim and a loop-4-gated gate cannot be settled by one arbitrary run); this register's carried text already says "advance (not settle)". No further action.
  - **N1 (confirmed)** — the doc's final Shipped list omits Lever F, which its own status line ships; the correct list is G43 fix + E + D + F (as this register already records).
  - **N2 (confirmed)** — the doc's quoted reproducibility command omits the `--require-tiktoken` flag its own Method section declares a prerequisite; reproduce with the flag.

## Token-cost estimates and work order

**Board status, 2026-08-25: nothing agent-executable remains.** Tier 1 (10/10 rows) and Tier 2
(8/10 rows) below shipped in the 2026-08-20 fleet run; `docs/contest-refactor-run-log.md:32` says
so directly — *"Fleet complete. Everything agent-executable from the work order is landed or
dispositioned."* Rows are marked `SHIPPED`/`CLOSED`/decided in place rather than deleted, because
the cost estimates are the tables' remaining value as a record of what the work actually cost.
What's left is gated on an owner decision (Tier-3 validator pricing, the G17 D2 disposition,
Backlog 8's axis call), on a production run (the run-gated tier, the G17 promotion bar, the
`--scope` probe), or is `[D3]`, which is deliberately deferred until a fifth gate selftest exists
— do not pick it up thinking it's a cheap win.

**Added 2026-08-20 at the owner's request**, so the open items can be sequenced by cost against the
standing budget rule (significant improvements, or improvements that cost very little). **Method.**
"Session tokens" prices the full read–implement–validate–commit cycle, calibrated against observed
work in this repo: the D1 prototype plus its equivalence/mutation proof cost roughly 60k in-session;
a shipped gate with selftest and fixtures has historically run 100–200k; one codex peer-review round
is ~30k. Bands are honest to about ±2×. Items whose real price is **production runs** are priced in
runs, not session tokens: the runtime-cost audit's measured model puts one BenchHype-scale run at
~20M+ resident context tokens (~241 messages × ~84k per-loop reload, 93.9 % cached), and sweep #3's
arm dispatch alone was 27.9M. A run costs 50× the largest engineering estimate below and roughly
three orders of magnitude more than a Tier-1 item — which is why run-gated items sort last
regardless of their small session cost, and why the one run that feeds several measurements at once
is the only good buy in that tier.

### Decision gate — costs an owner call, not tokens

**Decided 2026-08-20: RETAIN** (owner call; recorded at the ponytail item). The retain-branch sequencing below was executed. Original text follows for the record. **The panel disposition (ponytail item 1) comes first.** It is a decision, not work, and four
priced items hinge on it: the residual-rule fixture repairs (five of seven are `panel-*`), D2's
shared-loader placement (extend the panel-named testkit versus a neutral `_selftest_lib.py`),
the G29 prose correction's v5 clause (the routing contract currently authorizes no v5 profile),
and ponytail 2's history materialization (63 versus 83 histories). The decision alone deletes
nothing — the cheaper prices below require the removal to have been **executed**, so the two
branches sequence differently:

- **Retain:** repair all seven residual fixtures, keep the v4/v5 G29 prose as drafted, materialize
  83 histories in ponytail 2. Tier-1 + prerequisites total: ~350k scratchpad-assisted / ~420k
  without (optional Tier-2 work such as ponytail 2's ~70k is extra on either branch).
- **Remove:** execute ponytail 1 (~80k, Tier 2) *before* the residual repair, the G29 prose edit,
  and ponytail 2 — then repair the surviving two fixtures and materialize 63 histories. The Tier-1
  numbers below are **subtotals**; Tier-1 + prerequisites on this branch is ~410k
  scratchpad-assisted / ~480k without, because the ~80k removal is a prerequisite, not an option
  (optional Tier-2 work such as ponytail 2's ~70k is extra on either branch).

[I1] needs the panel **decision** (it fixes the go-forward version topology, v4-only versus
v4/v5) but not the removal's execution; either branch may start [I1] as soon as the call is made.

### Tier 1 — cheap and real — SHIPPED 2026-08-20 (cost: ~330–350k with that session's scratchpad;
~400–420k without)

The table lists items in the order they shipped. Each was independently shippable and closed
something named in this review. Two prices differed for a reason: D5 and D1's lower price assumed
this session's scratchpad artifacts (the higher figure is what a fresh engineer would have paid
after they were gone), and the residual repair's lower price assumed the panel removal had been
executed first — the panel decision came down RETAIN (Decision gate above), so the realized cost
was the higher retain-branch figure, ~70k, not the remove-branch figure.

| # | Item | Est. | Why this price |
| --- | --- | --- | --- |
| 1 | **D5** — `scripts/_canon_selftest.py` | **~25k now, ~75k later** | `_canon_new.py` and the loader driver still exist in this session's scratchpad, and the 11 mutation cases are enumerated above; once the scratchpad is gone the harness is rebuilt from prose. The only item with an expiring discount. Acceptance: one case per each of the **16** `sys.exit(2)` sites (the 11 are the seed), each asserting the diagnostic *names the offending file* — not just exit code 2 — plus the committed 21-field golden snapshot. **Status: SHIPPED 2026-08-20 (`acd0bfd`).** |
| 2 | Ponytail 3 — dead-code deletion | ~5k | 14 lines; zero callers already proven twice. **Status: SHIPPED 2026-08-20 (`831f901`).** |
| 3 | **P1 ×2** — loop ownership, preferred clean-tree branch | ~60k | Moved up from Tier 2: first among the substantive fixes — only the expiring D5 discount and the ~5k dead-code triviality precede it — because nothing justifies deferring the two highest-severity findings (data loss). Covers the clean-tree precondition, by-construction ownership, the `HALT_STAGNATION`/`user_decision` persistent halt defined in the finding, and the replay matrix including halt-and-resume. Dirty-tree support stays deferred and unpriced. **Status: SHIPPED 2026-08-20 (`3906fb2`)** — the keyed probe it owed also ran and PASSED in sweep #5 (2026-08-20), see the keyed-probe log above. |
| 4 | **D1** — `load_canon` refactor | ~40k now, ~60k later | The rewritten module exists and already passed 21-field equivalence + 11/11 mutations; remaining work is port, re-prove, commit. Rebuilt from scratch it costs what it cost the first time (~60k). Acceptance: the one-time old/new comparison passes **and the committed golden snapshot is unchanged**. Do D5 first — its golden is D1's regression net. **Status: SHIPPED 2026-08-20 (`4fee1c1`).** |
| 5 | **P1** — 9.5-residual enforcement | ~70k retain-branch, ~50k after removal executes | Pure validator change + one negative fixture — but the repair bill is **seven** fixtures, not one (see the finding above); five are `panel-*` and are deleted only when ponytail 1 has actually run, not by the decision itself. Touches no loop-path prose, so no behavioral probe is owed. Still the cheapest P1 on the board. **Status: SHIPPED 2026-08-20 (`ab44c63`)** — realized at the retain-branch price (~70k); the removal-branch alternate never applied, since ponytail 1 was decided RETAIN. |
| 6 | G29 prose correction | ~15k | The cheap half of the emission-version P2: align G29's text to the v4/v5 rule. Write the v5 clause to match the panel decision. The enforcement half inherits [I1] and is priced in Tier 2. **Status: SHIPPED 2026-08-20 (`62d5a71`).** |
| 7 | **I3** — `source_rev` + `findings_carried_from_prior_loops` spec | ~20k | One definition decision plus two spec paragraphs. **Status: CLOSED 2026-08-20 (`62d5a71`)** — same commit as row 6. |
| 8 | Audit rev-3 re-review | ~30k | One codex round; closes the only unreviewed revision. Moved out of the run-gated tier — it has no production-run dependency. **Status: DONE 2026-08-20** (no sha — a review round, not a commit) — round-4 codex REVISE, five findings (B1–B3, N1–N2), all confirmed and recorded in "Carried from the runtime-cost audit" above. |
| 9 | **D2** — `_load_validator` testkit | ~35k | 14-file mechanical edit. If the panel decision leaves removal open, put the shared loader in a neutral `scripts/_selftest_lib.py` rather than extending the panel-named testkit. **Status: SHIPPED 2026-08-20 (`ac839c5`)** — landed as the neutral `_selftest_lib.py` loader. |
| 10 | **D4 step 0–1** — adjudicate the four asymmetric checks, then cross-apply | ~50k | Adjudicate each asymmetry against the two study contracts first (shared versus study-specific — baselines cannot answer intent), then add each *shared* check with one synthetic positive and one synthetic negative case, because the advisory side's `_check_replication` is dormant (zero replication blocks) and passes cross-applied checks vacuously. The adjudication record is the deliverable, no unification. **Status: SHIPPED 2026-08-20 (`7d6f4b8`)** — step 0–1 only; step 2 (factoring) remains deliberately unstarted, see the adjudication record above. |

[I2] left this tier: the spec already fixes the `rounds` value set, and required-value enforcement
retro-invalidates the null-emitting production artifacts — it is now priced after [I1] in Tier 2.

### Tier 2 — medium engineering — 8 of 10 rows SHIPPED 2026-08-20 (that work cost ~80k–300k);
Backlog 8 (NO-GO) and D3 (deferred by design) remain open

A caveat that applies to every validator flip below (independence, transitions, G29): each
enforces in `validate-artifact.py`, which this register measures the production loop **never
invokes** — so each flip closes its finding *at the validator only*. Live-path closure arrives
with Tier 3 (or another guaranteed host check), and no P1/P2 should be marked fully closed on a
validator flip alone.

| Item | Est. | Notes |
| --- | --- | --- |
| **[I1]** — version/ruleset scoping fix | **~120k** | The highest-leverage single item on the board: it unblocks the independence flip, the transitions flip, [I2], G29 enforcement, and is prerequisite #1 of the loop-path hook. Its named deliverable is **one authoritative ruleset-epoch classifier plus compatibility matrix** that all of those consume — G43/G46 scoping is the first client, not the product, and the G17 flip is a client too (its requirement must scope to current emits). The design pattern already exists in-repo (v2→v3 bumped *and* default-filled); the work is the decision, the migration table, and the classifier. **Status: SHIPPED 2026-08-20 (`60e1294`).** |
| P1 — independence enforcement (validator side) | ~50k after I1 | Small once scoping exists; blocked until then. The P1 itself closes only when the **live promotion route** refuses a terminal candidate with missing or inline reviewer/challenger isolation — that half is Tier-3-gated. **Status: CLOSED at validator level 2026-08-20 (`d46360b`)** — live-promotion half remains open, Tier-3-gated. |
| P2 — transitions `REPORT_ONLY` flip | ~20k after I1 | Plus one decision: the disposition of the dogfood artifact's real `HALT_LOOP_CAP→CONTINUE` at loop 10→11. **Status: CLOSED at validator level 2026-08-20 (`d46360b`)** — the dogfood artifact's transition is legacy-epoch and stays print-only by design; that is its recorded disposition. |
| [I2] — `rounds` membership check | ~15k after I1 | Required exact-int `{1, 2}` on current-ruleset emits (`bool` excluded), null only on scoped older artifacts; the conditional-coupling clause stays an open residual. Waits on scoping because both production artifacts emitted `null`. **Status: CLOSED at validator level 2026-08-20 (`d46360b`)** — the conditional-coupling clause stays an open residual as noted. |
| P2 — G29 emission-version enforcement | ~20k after I1 | The other half of the Tier-1 prose fix; without it the P2 stays half-closed. Acceptance: a new emit's declared version must **equal** the capability-derived current version — every stale version (v1/v2/v3), missing, and null all fail strict; scoped older history stays readable. The alternative closure — stop calling G29 a hard gate — is a decision, not code; pick one. **Status: CLOSED 2026-08-20 (`d46360b`)** — the keyed probe for this enforcement also ran and PASSED in sweep #5 (2026-08-20), see the keyed-probe log above. |
| P2 — aspirational-fixture repair | ~100k | Sub-rule label normalization first, then per-fixture completion; fiddly rather than hard. **Status: CLOSED 2026-08-20 (`13c947c`)** — see "[P2] Eight aspirational fixtures can pass for an unrelated failure" above for the full disposition and follow-ups flagged. |
| Ponytail 2 — fixture-history materialization | ~70k | Harness change is small; the rewrite is scriptable across 63 histories (remove branch) or 83 (retain branch — the −9,400-line figure is the remove branch's). Sequenced after the panel branch is executed. **Status: SHIPPED 2026-08-20 (`4d4f6ae`)** — materialized on the retain branch (83 histories). |
| Ponytail 1 — panel-stack removal | ~80k, **owner call first** | Executing the deletion is mechanical; the decision to reverse a shipped-then-parked feature is not a reviewer's to make. **Status: DECIDED RETAIN 2026-08-20** (owner call, recorded at the Decision gate above) — this is a decision against removal, not pending work; the ~80k removal cost was never spent. |
| Backlog 8 — strictness post-filter | ~80k | RFC exists; implementation unstarted. **Status: NO-GO 2026-08-20 (`bceff1b`)** — blocked on item 6 (the confidence-axis experiment, unrun) and on an incompatibility with current `--strictness` semantics; see the "Carried from the ledger" entry for item 8 above. Still open, but not a pickup: it needs the owner axis decision plus the unrun experiment first. |
| **D3** — gate-driver factoring | ~30k, deferred by design | Priced for when the next gate is written; doing it now designs against a guessed caller. **Still open — do not pick up as a quick win.** Deliberately deferred until a fifth gate selftest exists to design the driver against a real caller instead of a guessed one. |

### Tier 3 — the big build

**Feasibility gate: PASSED (GO), 2026-08-20** — threat model fixed at **automatic invocation**
(the measured failure is forgetting — 0/6 prose fire rate — and Item-14 verified tamper
resistance is not buildable today on any harness); one qualifying interception point
demonstrated on claude_code `PreToolUse` in an isolated scratch repo: automatic fire with zero
model cooperation, drafted commit subject captured pre-commit (the G22 input), fail-closed
block with the staged change intact, validator stderr round-tripped to the model. Both stated
prerequisites have since shipped ([I1] `60e1294`, G29 enforcement `d46360b`). Full record:
`analysis/contest-refactor/TIER3-FEASIBILITY-GATE-2026-08-20.md`. The build itself remains
unstarted — the owner prices it; opencode (the production runner) is first among providers to
demonstrate in the build phase.

**Five-phase validator + host hook** (the loop-path P2's only untried remedy): **~250–400k for the
validator side**, strictly after [I1], then **either** G29 enforcement **or** independently derived host-side
ruleset selection — without one of the two, a current artifact can self-declare v3 (or v1/v2) and
evade every version-scoped check the hook runs. The project **starts with a feasibility go/no-go**, not code, and
that gate reuses the Item-14 host analysis already in the repo, whose verdict is: *buildable today
as a same-privilege wrapper; not buildable today as strict* — every verified harness runs hooks as
the agent's own OS user from agent-writable config, and this repo currently has zero hook
configuration for any harness. So the design must first pick the threat model: **automatic
invocation** (a hook the model never has to remember — achievable, and sufficient against the
measured 0/6 forgetting failure) versus **tamper resistance** (not achievable today without
privilege separation). Then: the phase-to-gate matrix and expected artifact state per phase, the
commit-draft input, the named interception point per supported provider and the declared behavior
for `unknown` (which has none), an installation health check plus phase-level diagnostics so an
operator can tell validation failure from a missing or bypassed hook, fail-closed behavior,
installation and rollback, and end-to-end tests per phase. Hook implementation is **not priced
until one qualifying interception point is demonstrated**. The validator remains the expensive
half — and the piece that makes the 27 already-mechanized gates actually execute. Price it as a
deliberate project, not something to pick up alongside other work.

### Run-gated — priced in production runs, not session work

| Item | Price | Notes |
| --- | --- | --- |
| **Next production run, instrumented** | 1 run (~20M+ context) | The best buy in this tier: **two guaranteed advances and up to two conditional ones**. Guaranteed: the *after* arm of the audit's end-to-end cost measurement (the *before* arm must come from the audit's recorded pre-lever transcripts, whose comparability — same target, same scope — must be verified before any before/after claim; if none is comparable, this becomes the first of two matched runs), and the `--scope` probe (P1). Conditional: one G17 promotion datapoint only if the run contains an applicable deepening loop *and* it is human-adjudicated (predeclare language and applicability first), and G43's live behavior only if a dimension answers `clean` three loops running (loop 4+). The next natural use of the skill should be this measurement — a run bought for any one of these alone pays the same price for a fraction of the value. |
| G17 `REPORT_ONLY` flip (validator side) | ~30k session, gated on runs **and on [I1]** | The promotion bar (full criteria in the G17 finding above; live adjudication tally in *Carried from the ledger*) is not yet met. Meeting the bar authorizes `REPORT_ONLY = False` and nothing more, and even then the flip cannot ship before [I1]'s ruleset classifier scopes the requirement to current emits — otherwise it retroactively applies G17 to artifacts with no reliable ruleset epoch, the exact [I1] defect class. The P1 closes only when a guaranteed commit boundary (Tier 3) invokes the check. Live-path acceptance: an approved deepening change with neither test nor valid citation is stopped *before commit*; restraint case: a valid citation passes. Session cost is trivial; the data is the cost. |
| Lever F +5 reps/arm | moderate (order 1M context) | Settles the −20.2 % cost claim; the quality half needs no more data. |
| A/A noise-floor run | moderate, **low yield at current n** | Required before *any* Tranche-3 lift claim, but `required_n = 778` discordant pairs means the honest outcome now is `inconclusive`. Run it when a Tranche-3 claim actually matters, not before. |
| Backlog 5, 6, 11, 15, 23, 27 | multi-run or gated | Experiments (5 is ≥4 arms × reps at run scale) or blocked on decisions/pilots named in the backlog table. Parked. |

### Declined by default — recorded so the price stays visible

- **Lever A** (carving audited-clean gate prose): prerequisites (clause-level coverage matrix,
  the Tier-3 validator, a pre-registered ten-shape experiment) cost multiples of the 6,249 tok/loop
  payoff. Stays default-no unless the instrumented run shows the shipped levers fell short.
- **Backlog 13** (`skip_when` stage skipping): ~40k to build, but the audit's measured cost model
  puts structural trims on the weak axis; weigh against behavioral levers first.
- **[I4]** (grading-spend recording): ~20k, worth nothing until the next paired study exists — fold
  it into that study's preregistration rather than shipping it cold.
- **Builds 14 / 24 / 25** (host attestation, coverage manifest, tool substrate): ~150–400k each.
  Designs are done and kept; these are feature investments, not defect work, and should be chosen
  deliberately, not picked from this list by cost.

### Reading of the board

The panel decision cost nothing and re-sequenced four items; it came down RETAIN, executed
2026-08-20 (Decision gate above). Tier 1 shipped in full 2026-08-20 for ~330–350k
(scratchpad-assisted; ~400–420k without), closing **three P1s outright** — the two data-loss
ownership findings and the 9.5-residual hole — plus the canon test gap, the dead code, two spec
ambiguities, and the audit's last unreviewed revision, and banking the already-proven D1 — the
densest value on the list, led by the one item whose price would have tripled had the session
ended first. The single most leveraged spend after that, **[I1] at ~120k**, also shipped
(`60e1294`) the same day, and unblocked four items that landed alongside it in one commit
(`d46360b`) — the independence flip (~50k), the transitions flip (~20k), the [I2] membership check
(~15k), and G29 enforcement (~20k), ~105k of Tier-1-grade work — plus the G17 flip once its run bar
is met (still unmet). The loop-path P2 — this review's
most consequential finding — cannot be bought for less than the Tier-3 project, and no cheaper
route remains untried; its validator side is estimated at ~250–400k while **total closure cost
stays unknown until the hook go/no-go passes**. Treat it as its own funded effort, starting with
the feasibility gate. Spend nothing on the run-gated tier until the skill's next natural
production use, then instrument that run to collect its two guaranteed advances and up to two
conditional ones.


## Priority summary

Per-item token-cost estimates and the recommended sequence are in *Token-cost estimates and work order* above; this list is severity order, not work order.

- **P1 — CLOSED at spec level (`3906fb2`):** pre-existing dirty edits can be mistaken for loop-owned paths and overwritten on rejection.
- **P1 — CLOSED at spec level (`3906fb2`):** untracked files can bypass both implementation review and rollback.
- **P1 — CLOSED at validator+fixture level (`ab44c63`):** strict validation accepts unsupported 9.5 residual claims.
- **P1 — CLOSED at validator level (`d46360b`); live-promotion half still open, Tier-3-gated:**
  terminal success does not require independent reviewer/challenger execution.
- **P1 — OPEN** (run-gated; see the work order's Run-gated tier): report-only G17 permits approved
  deepening changes without interface-test evidence.
- **P2 — CLOSED (`62d5a71`/`d46360b`):** v3/v4/v5 emission instructions conflict and G29 is not implemented.
- **P2 — CLOSED (`13c947c`):** eight fixtures can pass for the wrong reason.
- **P2 — CLOSED at validator level (`d46360b`):** illegal terminal transitions are report-only.
- **P2 — OPEN:** the loop is instructed to run hard gates but never to run the module
  implementing 27 of them; measured 0/2 in production.
- **P2 (inherited, [I1]) — CLOSED (`60e1294`):** G43/G46 required fields with no version bump
  retroactively invalidated committed artifacts — the repo's own loop-15 artifact failed strict with
  10 issues, blocking the validator's wiring into the loop. The ruleset-epoch classifier shipped, so
  old artifacts are judged by their own rules.
- **Inherited, smaller ([I2]–[I4]):** `rounds` specified but read by nothing; `source_rev` ambiguous mid-loop and `findings_carried_from_prior_loops` specified nowhere; paired-arm grading spend unrecorded (majority of sweep #3's cost unmeasured).
- **Test gap — RESOLVED (`acd0bfd`):** `_canon.py` is the enum single-source-of-truth for every
  validator; its 16 `sys.exit(2)` paths were unreachable from the selftest suite (62 selftests at
  review time, now 79) because all 29 call sites pass the real canon. `_canon_selftest.py` now
  covers all 16 sites.
- **Simplification (behaviour-preserving) — half shipped:** `load_canon`'s twenty-times-repeated
  idiom with ten double-spelled paths is **CLOSED ([D1], `4fee1c1`, −91 lines, proven equivalent)**
  and `_load_validator`'s 14 copies are **CLOSED ([D2], `ac839c5`)**. Still **OPEN**: the G39–G42
  selftest driver is duplicated and its vacuity guards are already 3-of-4 ([D3]);
  `_check_replication` is duplicated across two baseline selftests and has diverged by four checks
  ([D4]).

No source changes were made as part of any of these passes. After the merges, both `docs/` source documents (the deep-dive and the ledger) and 40 of the 44 `analysis/contest-refactor/` files were **deleted at the owner's direction** — their still-open content lives in this document and in `analysis/contest-refactor/GAP-REGISTER.md`, and every retired file remains in git history. Citations to the retired paths from shipped scripts and prose are provenance pointers and resolve via `git show`. The D1 equivalence and mutation harnesses were session-scratchpad scripts and are **not committed**; they are lost when that session ends. Their 11 seed cases are the only code that has ever executed *any* of `_canon.py`'s 16 error paths — they cover the failure categories, while the five site-specific cases needed for full per-site coverage have never been written by anyone. Re-creating and completing them as `scripts/_canon_selftest.py` is **D5** — worth doing on its own merits even if D1 is declined, and cheapest to do before the harness is gone. **Resolved: D5 shipped 2026-08-20 (`acd0bfd`) while the scratchpad harness still existed; the per-site coverage now lives in the committed selftest and this paragraph is historical.**
