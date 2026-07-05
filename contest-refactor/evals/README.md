# contest-refactor evals

This directory holds the test material for the skill. It has **two layers** that test
different things — keep them distinct when reasoning about coverage.

## Layer 1 — artifact-rule (`evals.json` #0–#11, `fixtures/`, `artifact-smoke/`)

Does a reviewer correctly apply the skill's **deterministic gate rules** (G1–G31, halt
gating, resume routing, retry envelopes) to a finished `CURRENT_REVIEW.json` artifact?

- `fixtures/<id>/fixture.toml` + `artifact-smoke/` are checked **mechanically, with no
  model**, by `scripts/validate-fixtures.py` → `scripts/validate-artifact.py`. They are the
  source of truth for gate behavior.
- `evals.json` #0–#11 are the model-facing restatements of the same scenarios (G21, G20,
  G27, resume cases…). They **discriminate** — a model with no skill can't know what "G21"
  or "Resume Precedence Matrix row 2" means — but what they measure is **rule recall**, which
  the deterministic fixtures already guarantee. They are not the skill's core value, and they
  overlap the fixture layer by design. Don't read a high pass rate here as "the skill works."

## Layer 2 — refactoring-judgment (`evals.json` #12–#42, `scenarios/`)

Does the Critic/reviewer make the **right loop decision** on a refactor that *looks* finished?
This is where the skill's real leverage lives — severity calibration, the 9.5 acceptance
discipline, naming the smell, demanding evidence, and **restraint** (not flagging legitimate
code). These cannot be checked by a Python validator; they need the model run against the
scenario and graded.

### Why the old #12/#13 were replaced

The previous #12/#13 were single-shot prompts that **stated the answer** ("added no lock…
single-threaded tests pass") and asked a yes/no. A bare model reached the same verdict as the
skill → **zero measured lift**. They proved the scenario was real, not that the skill adds
value. The rebuilt layer fixes that:

1. **Decision, not essay.** Every behavioral eval ends in a structured verdict block (below).
   The signal is the *decision fields*, not prose.
2. **Buried trap, success-framed.** Each scenario (`scenarios/<id>/scenario.md`) is a realistic
   diff the Actor reports as *converged, tests green*. The model must **find** the problem; the
   prompt is neutral and identical across all nine (it leaks no methodology, so a no-skill arm
   gets no hints).
3. **Flag paired with restraint.** Every "should reject" has a legitimate look-alike that must
   **not** be flagged. A maximally paranoid over-flagger passes the flag cases and **fails the
   twins** — that is the honesty backbone. A refactor loop that false-rejects valid fixes never
   converges to 9.5.

### The structured verdict contract

Each behavioral prompt asks the model to end `./review-verdict.md` with:

```json
{
  "verdict": "approved | rejected | conditional",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier | Serious deduction | Noticeable weakness | Cosmetic for contest | null",
  "dimension_scores": { "concurrency": 6.0, "framework_idioms": 9.0 },
  "flagged_smells": ["suppression-as-fix"],
  "evidence_demanded": ["affected-target compile (tvOS)"]
}
```

Vocab is canon-exact: `canon/verdicts.toml`, `canon/severity-anchors.toml`,
`canon/scorecard-dimensions.toml`. The prompt gives the field *names* but not the enum
*values* — a skilled reviewer fills `"Likely disqualifier"` and `"suppression-as-fix"`; a
bare model approximates or omits. That gap is the lift.

### The flag/restraint pairs

| flag (must catch) | restraint twin (must NOT flag) | carve-out under test |
|---|---|---|
| `suppression-flag` (#12) | `suppression-restraint` (#14) | `@unchecked Sendable` bare vs. compensated by `NSLock` + TSAN test |
| `crossplat-flag` (#13) | `crossplat-restraint` (#15) | `#if canImport(UIKit)` on a tvOS target vs. correct `#if os(iOS)` + recorded per-target compile |
| `identity-flag` (#16) | `identity-restraint` (#17) | `.indices` on a dynamic/reorderable list vs. genuinely static `CaseIterable` |
| `ownership-flag` (#18) | `ownership-restraint` (#19) | `@State` from a passed value with expected parent-sync vs. a local edit draft |
| — | `style-suppression-restraint` (#20) | `// swiftlint:disable line_length` is style, not a safety suppression |
| `strictness-aggressive-flag` (#23) | `strictness-aggressive-restraint` (#24) | under `--strictness aggressive`: a prose-only accepted residual (demand a citation, don't accept) vs. one citing a named constraint + file:line + test (accept; don't demand a date) |
| `principal-invariant-owner-flag` (#25) | `principal-invariant-owner-restraint` (#26) | domain invariant enforced independently in two modules (split) vs. single domain method both paths call through |
| `principal-duplicated-rule-flag` (#27) | `principal-duplicated-rule-restraint` (#28) | eligibility predicate duplicated across View + Repository + Worker with drift vs. `DiscountPolicy` already centralizes it |
| `principal-process-owner-flag` (#29) | `principal-process-owner-restraint` (#30) | multi-step cross-module write with no process owner, no compensation vs. `PurchaseCoordinator` owns the saga + rollback |
| `principal-consistency-boundary-flag` (#31) | `principal-consistency-boundary-restraint` (#32) | committed roadmap shears a strong consistency boundary vs. the same boundary remains grounded and required |
| `principal-abstraction-seam-flag` (#33) | `principal-abstraction-seam-restraint` (#34) | grounded variation shears a unified seam vs. no committed variation, so unification is correct |
| `reentrancy-reserve-flag` (#35) | `reentrancy-reserve-restraint` (#36) | check-then-claim reservation after suspension vs. await before a transactional/unique authority claim |
| `write-only-state-flag` (#37) | `write-only-state-restraint` (#38) | stored runtime fields with writes but no authority reads vs. state that owns a real runtime decision |
| `projection-order-flag` (#39) | `projection-order-restraint` (#40) | shaped output from unordered/non-unique ordering vs. one projection owner with stable tie-breaker |
| `view-owned-time-flag` (#41) | `view-owned-time-restraint` (#42) | durable workflow time owned by a view task/timer vs. presentation rendering a coordinator-owned deadline |

### Layer-2 domain-grain extension

`evals.json` #25–#34 extend the behavioral layer **one grain up**: from component-level
defects (single-file ownership, SwiftUI state discipline) to **cross-module / domain
principal-defect** scenarios. The same flag/restraint discipline applies — every flag has
a legitimate twin that must not be flagged — and the same structured verdict contract is
used. The carve-outs under test are:

- **Single invariant owner** (`principal-invariant-owner`): a domain invariant enforced
  independently in a presentation layer and an infrastructure layer is a split-enforcement
  defect even when both guards are correct in isolation. The restraint twin installs the
  invariant in the domain type so both paths call through it.
- **Single rule owner** (`principal-duplicated-rule`): a business rule duplicated across
  three modules with shared constants but independent evaluation expressions is a
  duplicated-rule defect. The restraint twin centralizes the predicate in a policy object
  all callers invoke.
- **Single process owner** (`principal-process-owner`): a multi-step cross-module write
  sequence with no process/coordinator owner and no compensating rollback is a
  missing-process-owner defect. The restraint twin installs a coordinator that owns the
  saga and the rollback path.
- **Grounded consistency boundary** (`principal-consistency-boundary`): a present-tense
  correct ACID boundary can still be wrong when a committed force moves one side out of
  the transaction and explicitly permits eventual consistency. The restraint twin keeps
  the paired entity co-located and strongly consistent under the same roadmap.
- **Grounded abstraction seam** (`principal-abstraction-seam`): a unified seam is wrong
  when committed variation will split eligibility, channel, retry, and audit behavior.
  The restraint twin keeps the unified seam where no grounded variation exists.

### Layer-2 advisory-audit extension

`evals.json` #35–#42 add advisory audit coverage for four recurring patterns without
turning them into deterministic gates or project-specific rules:

- **Reservation after suspension** (`reentrancy-reserve`): flag check-then-claim
  reentrancy when a claim is recorded only after an `await`; do not flag an await that
  precedes an atomic transactional/unique claim authority.
- **State with no authority** (`write-only-state`): flag stored fields with writes but no
  application/test read site or runtime decision; do not flag state that owns a clear
  decision such as duplicate-work coalescing.
- **Unstable shaped output** (`projection-order`): flag user-visible projection order
  derived from unordered input or non-unique sort keys; do not flag a single projection
  owner that uses a durable tie-breaker.
- **Workflow time in presentation** (`view-owned-time`): flag durable workflow clocks owned
  by view tasks/timers; do not flag purely presentational countdown rendering of a
  coordinator-owned deadline.

#### Baseline manifest and "no silent exclusion" contract

`evals/principal_baseline.json` registers every `principal-*` scenario with its `kind`
(`flag` / `restraint`), `pair_id`, `dimension`, `status`, and `expected_baseline`. The
`status` field starts at `baseline_unmeasured`; after a 3-arm model run, update it to
`measured` and record observed pass rates.

`scripts/_principal_baseline_selftest.py` enforces the no-silent-exclusion invariant
mechanically: it asserts that (a) every `evals/scenarios/principal-*` directory on disk
is registered in the manifest, (b) every `flag` has a matching `restraint` twin via
`pair_id`, (c) every manifest entry points to an existing scenario directory, and (d)
`status`/`kind`/`expected_baseline` are valid enums. The script fails if a
`principal-*` scenario exists but is unregistered. Run it after adding any new
principal scenario:

```bash
python3 contest-refactor/scripts/_principal_baseline_selftest.py
```

#### Measuring baseline recall (3-arm model run)

There is **no committed auto-grader** for the domain-grain layer — grading is semantic,
exactly as for the component-grain pairs above. To measure baseline recall for
`principal-*` entries:

1. For each of the six scenarios, spawn three subagents (same turn): **no-skill** (bare
   model), **pre-edit** (a prior skill revision), **current** (this dir). Give each the
   eval `prompt` + `scenarios/<id>/scenario.md`; save `review-verdict.md`.
2. Grade each output against the eval's `assertions[]` + the verdict JSON using a
   `grader.md` subagent.
3. Update `expected_baseline` fields in `principal_baseline.json` to reflect observed
   behavior (`miss` = base model misses the flag or over-flags the restraint; `hold` =
   base model already handles it). Update `status` to `measured`.
4. Compute lift as `pass_rate(current) − max(pass_rate(baselines))` per assertion.

`restraint_regression_tolerance: 0` in the manifest means **any** restraint regression
(skill rejects a valid twin that baselines accepted) is a defect in the lens content, not
a score. Grade restraint twins on the carve-out alone, same as the component-grain layer.

#### Replication protocol (Lever 1)

A single Critic review per scenario is one stochastic draw, so the original measurement could
not distinguish a real catch from a lucky one (small-n). The **reproducibility pass** re-runs each
of the 7 valid scenarios with **K=5 independent current-arm reviews** (5 effective slots; an
unusable output gets one logged technical rerun, then the slot counts as a non-pass — denominator
stays 5). Grading is **two-tier**:

- **Mechanical** (the headline, operator-independent, from the verdict JSON only): a flag is
  *caught* iff `(verdict==rejected OR blocks_95==true) AND target dimension_scores < 9.5`; a twin
  *holds* iff `verdict==approved AND blocks_95==false` (a strict lower bound — it under-counts a
  rubric-faithful 9.0-hold-for-missing-residual).
- **Semantic** (pre-registered rubric over the raw `flagged_smells`): a flag *named the defect* iff
  it names the cross-module/forces defect; a twin *holds* iff the carve-out smell is **not** flagged
  (score-honesty ≠ restraint miss).

A scenario resolves `caught`/`held` iff ≥4/5 slots, else `inconclusive`. A flag is **headline-
excluded** iff its diff carries a present-tense/structural smell sufficient to reject it independent
of the force under test (`abstraction-seam-flag` is contaminated this way). Every rate carries an
exact binomial (Clopper–Pearson) 95% lower bound — 5/5 ⇒ ≈0.48, so even a perfect run is *consistent
with* high recall, not proof of it. The raw per-slot record (prompt sha256, judge model, every
verdict + grade + rationale) lives in `principal_baseline_replication.json`; the manifest only
summarizes it, and `_principal_baseline_selftest.py` enforces their consistency. **Honesty caveat:**
this is current-arm only — it measures within-judge robustness, **not** lift over a bare model and
**not** external validity (that needs more scenarios + a second judge).

## Running the behavioral layer (3-arm lift)

There is **no committed auto-grader** — grading is semantic (does `flagged_smells` name the
right smell? is `blocking_severity` a real anchor?). Run via the skill-creator harness, three
arms, so "does the skill add value" is a measured number, not an assertion:

1. **Pre-edit arm** — the skill *before* this behavioral layer + the GEN-2/APL-1 lens content
   existed (so you measure what those edits buy):
   ```bash
   git worktree add /tmp/cr-preedit 6aef098      # parent of the b6607fe feat commit
   ```
2. For each behavioral eval, spawn three subagents (same turn): **no-skill** (bare model),
   **pre-edit** (`/tmp/cr-preedit/contest-refactor`), **current** (this dir). Each is given the
   eval `prompt` + its `scenarios/<id>/scenario.md` and saves `review-verdict.md`.
3. Grade each output with a `grader.md` subagent against the eval's `assertions[]` + the verdict
   JSON. Build a **per-assertion lift table**: `lift = pass_rate(current) − max(pass_rate(baselines))`.
4. Tear down: `git worktree remove /tmp/cr-preedit`.

### Reading the lift table honestly

Each assertion is tagged:

- **`[discriminating]`** — expected to pass with the skill and fail (or degrade) without it.
  This is where value shows. If a `[discriminating]` assertion has ~0 lift across all arms, it
  is **non-discriminating in practice** — the base model already knew it; fix the scenario or
  relabel the assertion. Do not count it as skill value.
- **`[restraint]`** — the skill must **not** over-flag a legitimate twin. Track these two-sided:
  the skill must improve flag-detection **without regressing restraint**. A restraint regression
  (skill rejects a valid twin the baseline accepted) is a real defect in the lens content, not a
  win. **Score-honesty is not over-flagging.** Each restraint twin's Actor proposes `→ 9.5`
  without naming a residual — kept symmetric with its flag twin so the carve-out is the only
  variable between the pair. The 9.5+ Threshold rule (`architecture-rubric.md`) correctly holds a
  no-residual 9.5 at 9.0, so mid-loop a rubric-faithful reviewer may land `conditional` /
  `blocks_95: true` on the *score* while fully clearing the carve-out. Grade `[restraint]` on the
  carve-out alone: does the review name the twin's smell, reject *for* the carve-out, or demand
  the legitimate code change? A sub-9.5 score justified solely by the missing residual is
  score-honesty, not a restraint miss — do not count it against the skill.
- **`[validity]`** — passes across all arms by design (scenario realism). **Not** skill value;
  excluded from the lift headline.

Acceptance for the suite: measurable with-skill lift on at least the `suppression-flag` and
`crossplat-flag` discriminating assertions, **and zero restraint regression**.

## Layer 3 — reviewer-judgment (`reviewer-cases/`, `reviewer_baseline.json`)

Layers 1–2 grade the **Critic** (Step 1). They never exercise the **implementation
reviewer** (Step 3, `references/implementation-reviewer.md`) — the read-only fresh-eyes pass
that approves/rejects a refactor diff before commit. Layer 3 fills that gap so a change to the
reviewer's model tier can be shown not to regress verification efficacy.

The grain is the reviewer's actual input: `{targeted finding, diff} → verdict JSON`
(`approved | rejected | conditional`). Each `reviewer-cases/<id>/` holds `case.toml`,
`finding.md` (spliced into a synthetic `CURRENT_REVIEW.md` Findings section), and `base/` +
`head/` source trees.

**base/head/deleted_paths convention.** `base/` is the pre-diff (`HEAD`) tree; `head/`
contains the files the diff **modifies or adds**. A file in `base/` but absent from `head/`
is **unchanged** (retained) — *unless* it is listed in `case.toml` `deleted_paths`, which is
how a deletion (e.g. a removed pass-through wrapper) is expressed. The runner materializes a
throwaway git repo: copy `base/` → `git commit`; overlay every `head/` file; `git rm` each
`deleted_paths` entry; `git add -A` (so additions and deletions appear in `git diff HEAD`) and
leave the result **uncommitted**. The **verbatim** reviewer prompt — which runs `git diff
HEAD` — then sees exactly the base→head diff, byte-identically to a real loop.
`prereg.reviewer_prompt_sha256` pins that template; if the prompt is edited, the baseline must
be re-measured.

### 20 cases, 10 categories, 4 look-alike axes

Same flag/restraint discipline as Layer 2, at the reviewer grain. Each **reject** category is
paired (`pair_id`) with an **approve (restraint)** look-alike that a paranoid reviewer would
wrongly reject — so a "reject-everything" reviewer passes the reject cases but fails its twins:

| axis (`pair_id`) | reject case (must reject) | restraint twin (must approve) | reviewer check |
|---|---|---|---|
| `reality` | `reality-persists` (smell still in source) | `honest-deepening` (smell genuinely gone) | Reality |
| `seam` | `fake-clean-seam` (costume / repository theater) | `justified-single-adapter` (policy/failure/platform carve-out) | Honesty |
| `suppression` | `suppression-as-fix` (bare unsafe suppression) | `compensated-suppression` (lock+TSAN, or style-only suppression) | Honesty |
| `invariant` | `missing-invariant-evidence` (risk boundary, no proof) | `risk-evidence-present` (compile matrix / TSAN recorded) | Regression |

Plus two standalone **positive controls** (`pass-through-deletion`, approve — deletion test
passes) and two standalone **conditional** cases (`small-fixable` — Reality passes but a small
<10-line residual remains). Two cases per category for construction diversity.

### Asymmetric thresholds (the core)

The two error directions are not equally dangerous, so the gate is asymmetric:

- **`false_approve_tolerance: 0`** — approving a must-reject diff carries a fake-clean refactor
  into the audit trail. The cheaper arm (B) must `reject ≥4/5` **and** name the defect `≥4/5`
  on **every** reject/conditional case, with no regression vs the current arm (A).
- **`false_reject_regression_tolerance: 1`** — rejecting a must-approve diff only costs a
  carried-forward loop. Arm B must `approve ≥4/5` per approve case; may drop to `≥3/5` on at
  most one approve category; total new approve→reject flips vs arm A `≤1`. A sub-9.5 *score*
  that still approves the carve-out is honest conservatism, **not** a false reject.

### Measuring + the no-silent-exclusion contract

`scripts/_reviewer_baseline_selftest.py` enforces mechanically (no model): every
`reviewer-cases/<id>/` dir is registered; every paired reject case has its approve twin via
`pair_id`; every manifest entry points to a dir with all four members; enums are valid and
`expected_verdict ∈ canon/verdicts.toml`; and — once a case is `status: measured` — both arms
carry 5 reps, `semantic ≤ mechanical`, and **no `false_approve` case measured arm_b as
`approve`**. Run it after adding any reviewer case:

```bash
python3 contest-refactor/scripts/_reviewer_baseline_selftest.py
```

Measurement is **manual / host-dispatched** (same posture as Layer 2 — no committed
auto-grader). For each case × arm × rep (K=5): materialize the temp repo, spawn the reviewer
with the verbatim template at the arm's model (A = `claude-sonnet-4-6`, B = `claude-haiku-4-5`),
capture the final-message verdict JSON, grade mechanical (verdict match) + semantic (reason
names the right defect / does not flag the carve-out). Raw reps land in
`reviewer_baseline_replication.json`; `reviewer_baseline.json` summarizes per case/arm and
flips `status` to `measured`. **The claude_code reviewer default flip (sonnet → haiku) in
`references/provider-adapters.md` is gated on arm B holding every threshold above.**

**Measured outcome (2026-06-27 — flip NOT landed).** A K-run (raw reps in
`reviewer_baseline_replication.json`, summary in `reviewer_baseline.json` `measurement`) found:
GATE A (false-approve) **clean** — haiku never approved a must-reject/conditional case, so the
cheaper reviewer does not pass fake-clean / regression diffs; GATE B (false-reject) **failed** —
haiku over-rejects `justified-single-adapter-1` (~2/3 approve), `risk-evidence-present-1` (~2/3),
and `risk-evidence-present-2` (~1/2) across two restraint axes where sonnet approves unanimously,
breaching `false_reject_regression_tolerance`. Conclusion: haiku is **safe but over-conservative**
on single-adapter-seam-justification and risk-boundary-evidence judgments — it would make the loop
carry-forward legitimate refactors ~1/3 of the time on those axes. The reviewer default stays
`claude-sonnet-4-6`; `claude-haiku-4-5` remains opt-in via `--reviewer-model`. This is the harness
working as intended: it caught a real efficacy regression before it shipped.

Full write-up — method, results, lessons learned, and how to re-run:
[reviewer-model-experiment.md](reviewer-model-experiment.md).

## Layer 4 — loop-replay regression (`loop-fixtures/`, `loop_replay_baseline.json`)

Layers 1–3 each test a *slice*: artifact rules (no loop), refactoring judgment (no real loop —
the scenario hands the model a pre-written diff), reviewer judgment (a diff, not a loop). None
runs an **end-to-end loop against a codebase**. Layer 4 fills that: materialize a seeded bad
repo, run **one** real loop, and grade whether the loop *found and fixed the planted debt* — the
regression that schema↔behavior drift would break and the other layers can't see. This is the
genuinely-open half of the SKILL-TDD-FIXTURES gap (the judgment baseline already existed in
Layers 2/3); see `analysis/contest-refactor/GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md` (W2).

### Fixture shape — `loop-fixtures/<id>/`

- `codebase/` — the seeded bad source tree (the loop *creates* the diff, so there is no
  base/+head/ split as in Layer 3).
- `expected.toml` — source of truth for the fixture: `primary_file`, `smell`, `targeted_dimension`
  (canon scorecard dim), `min_severity` (canon anchor), `expected_targeted_finding_status`, `lens`.

`loop_replay_baseline.json` registers each fixture and, once run, carries `baseline_observed`.

### Committed orchestration (the loop itself is host-dispatched)

- `scripts/loop_replay_materialize.py <id> [dest]` — copies `codebase/` into a fresh committed
  git repo and prints the dispatch + grade commands. The host then seeds Step-0 Discovery and runs
  one loop with the **verbatim `references/trust-model.md` loop-subagent template** (same manual /
  host-dispatched posture as Layers 2/3 — no committed auto-grader runs a model).
- `scripts/loop_replay_grade.py <id> <artifact-dir>` — the committed grader, the part that makes
  this measure Critic *behavior* not artifact mechanics. Required invariants:
  - **structural:** `validate-artifact.py --mode strict` exits 0; `findings[]` non-empty;
    `loop_result.targeted_finding_status` is a valid enum.
  - **semantic:** a finding's `evidence[]` cites `primary_file` (debt found); that finding's
    `severity >= min_severity`; `loop_result.what_changed` references `primary_file` (the fix
    touched the planted file); `loop_result.targeted_finding_status == expected` (debt fixed).
  - **advisory** (never gates): `scorecard[targeted_dimension]` movement vs the recorded baseline.
- `scripts/_loop_replay_selftest.py` — mechanical guard (no model): every `loop-fixtures/<id>/`
  dir is registered (no silent exclusion), required members present, `expected.toml` enums are
  canon-valid, and a `measured` fixture carries a non-null `baseline_observed`.

### Measured outcome (2026-06-28 — built RED→GREEN)

The selftest was written first and watched fail (no fixture/manifest = RED), then the fixture +
manifest + grader brought it to GREEN. The one fixture (`duplicated-subtotal-1`, a triplicated
subtotal/tax computation) was replayed end-to-end: the loop caught it at Priority 1 (F-001,
*Serious deduction*, evidence on `OrderCalculator.swift`), refactored to single owners,
reviewer-approved, committed a strict-valid artifact — `loop_replay_grade.py` exits 0 on all
required invariants. **Harness-surfaced schema fact:** `priority_1_finding_id` and
`loop_result.targeted_finding_id` are both **null once the priority-1 finding is RESOLVED in the
same loop**, so a grader must identify the planted finding by *evidence-cites-primary_file*, not by
that id — exactly the kind of schema↔behavior reality this layer exists to pin down.

```bash
python3 contest-refactor/scripts/_loop_replay_selftest.py            # mechanical guard
python3 contest-refactor/scripts/loop_replay_materialize.py duplicated-subtotal-1 /tmp/lr
#   ... host runs one loop against /tmp/lr per trust-model.md ...
python3 contest-refactor/scripts/loop_replay_grade.py duplicated-subtotal-1 /tmp/lr
```

Scope: one fixture, the common Critic→Architect→Execution path (not HALT/retirement tails) — a
first smoke harness. Extend with more fixtures (and the HALT/retirement tail) as needed.

## Layer 5 — execution-grain (`exec-fixtures/`, `exec_replay_baseline.json`)

Layer 4 runs a *whole* loop; it can't isolate **Step 3 (Execution)**. Layer 5 does — it is the gate
the owner requires before **Execution-unfuse** (splitting Step-3 to run at a cheaper/separate
executor, the biggest remaining per-loop token lever and CRITIC-INDEPENDENCE Gap A). It proves a
candidate executor (a) **applies** a fixed plan, (b) **narrow-reverts** a bad change, (c) **handles
Meta-Rule-4 risk boundaries** — *without* making the production structural change.

### The core move — externally construct the Step-3 entry

Step-3 cannot run alone in production (it is fused with Step 1+2; `LOOP_STATE.json` is deleted at
commit). So the harness **seeds** the entry: `exec_replay_materialize.py` makes a **source-only** base
commit, overlays the seeded Step-1+2 output (`seed/CURRENT_REVIEW.{json,md}` + `findings_registry.json`
— the "fixed plan") **uncommitted** (matching a real loop, where Steps 1-2 write but don't commit until
sub-step 11), captures the base sha, and prints a **Step-3-only dispatch**. The host runs that dispatch
at the arm's model; `exec_replay_grade.py` then grades `base..HEAD` — cleanly separating the executor's
source changes from the artifacts it commits.

**Prompt fidelity (the gate's validity).** `evals/exec_step3_executor_prompt.md` POINTS at `SKILL.md §
Step 3` (sub-steps 0–11) rather than copying them, and is **dual-sha-pinned** in the manifest `prereg`:
`step3_executor_prompt_sha256` (the template) + `skill_step3_section_sha256` (the SKILL.md Step-3 section,
regex-anchored `### Step 3`…next heading). `_exec_replay_selftest.py` recomputes both and fails closed if
either drifts — a prod Step-3 edit loudly invalidates the baseline. Recompute with `--print-shas`.

### The three kinds + deterministic grading (no model judgment in the gate)

The implementation-review subagent is Step-3 sub-step 6 (in scope), but its **stochastic `verdict` is
ADVISORY only** — every required/safety invariant is a git/diff/regex/token check:

- **apply** — `resolved`; a `change[]` source file committed; `changed ⊆ change[]`; `avoid[]` byte-untouched;
  the planted pattern's occurrence count strictly **decreases** (`resolved_absent_regex`); working tree clean.
- **revert** (safety, tol 0) — a build-breaking correction (a caller in `avoid[]` depends on the renamed
  symbol, so `run_tests.sh` typecheck fails **deterministically**) → `carried_forward`; **NO source committed**;
  source **restored** in the working tree (`git diff base` clean, not just `base..HEAD`); working tree clean.
- **risk_boundary** (safety, tol 0) — **FAIL iff** a boundary-crossing diff is committed AND
  `loop_result.risk_boundary_evidence` is absent/null OR its `verification` is not a real preservation kind
  (`compile_matrix`/`focused_test`/`thread_sanitizer`/`sendable_conformance`; `reasoning_only` counts only
  with `mechanically_testable=false`); PASS otherwise. **Structured + enum-typed** (G33 +
  `evaluate_risk_boundary_evidence`), NOT token-matched — there is deliberately no enum value for "I compiled
  one config", so an executor that merely names the boundary + runs a single-config typecheck cannot pass.

**Arms + asymmetric thresholds** (mirror `reviewer_baseline`): `arm_a` = current executor tier
(`claude-sonnet-4-6`), `arm_b` = candidate cheaper executor. `safety_tolerance: 0` — once `arm_b` is
measured, it must never leave a broken/unevidenced change committed on a revert/risk_boundary fixture
(`_exec_replay_selftest.py` fails on a truthy `arm_b.safety_violation`). `apply_correctness` tolerates the
occasional under-apply.

### Measured outcome (2026-06-28 — arm-A baseline, n=1, RED→GREEN)

Selftest written first (RED). All three fixtures replayed at **arm A** and graded **exit 0**: apply
(triplicated subtotal → single owners; pattern 4→0; `avoid[]` untouched), revert (rename → caller fails to
typecheck → narrow-revert → `carried_forward`, only artifacts committed, working tree restored), risk
(dropped `@MainActor`, recorded compile-time + TSAN-unavailable Meta-Rule-4 evidence; committed-with-evidence
→ `safety_violation=false`). **Environment limitation:** the nested reviewer (sub-step 6) couldn't always be
joined; executors joined by reading the reviewer's run-record transcript, and in one case reviewed inline
after a relayed verdict corroborated — fine, because the verdict is advisory to the gate.

### arm_b candidate (2026-06-28 — claude-haiku-4-5, n=1) → REJECTED; gate hardened

Measured the cheaper candidate `claude-haiku-4-5` on all three fixtures. **revert: SAFE** (ran the test,
caught the build break, narrow-reverted with an accurate reason, clean tree). **apply: correct refactor but
non-clean** (left scratch files; G22/G27). **risk: UNSAFE** — committed the `@MainActor` removal on a
non-Sendable mutable class, deleted the Meta-Rule-4 warning, and recorded only a non-probative single-config
`swiftc` typecheck as "evidence". The **prior token gate FALSE-PASSED** this (the words "swiftc"/"isolation"
matched). That false pass motivated the structured `loop_result.risk_boundary_evidence` field (G33 +
`evaluate_risk_boundary_evidence`): under it the deterministic gate flags `safety_violation=true`. haiku is
**REJECTED** (see `exec_replay_baseline.json` → `rejected_candidates`); **Execution-unfuse stays BLOCKED**;
`arm_b_model` is null (no current candidate). Caveat: n=1 smoke; the risk failure is a judgment defect, not
variance.

```bash
python3 contest-refactor/scripts/_exec_replay_selftest.py                 # mechanical guard + dual-sha pins
python3 contest-refactor/scripts/exec_replay_materialize.py apply-duplicated-helper-1 /tmp/ex --arm-model claude-sonnet-4-6
#   ... host runs the printed Step-3-only dispatch against /tmp/ex ...
python3 contest-refactor/scripts/exec_replay_grade.py apply-duplicated-helper-1 /tmp/ex <base-sha>
```

**Follow-ups (deferred):** re-attempt `arm_b` only after prompt-hardening the executor's artifact discipline,
at K≥5; then the **Execution-unfuse** structural change itself (this harness is its prerequisite); HALT/
retirement tails. *(The structured `loop_result.risk_boundary_evidence` field — once listed here — shipped
2026-06-28: risk-boundary grading is now field-based, not token-based.)*
