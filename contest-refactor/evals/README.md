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

## Layer 2 — refactoring-judgment (`evals.json` #12–#24, `scenarios/`)

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

### Layer-2 domain-grain extension

`evals.json` #25–#30 extend the behavioral layer **one grain up**: from component-level
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
