# Continuous Scoring Augmentation Gap — contest-refactor binary-gate vs continuous-score evaluation

Source: `refs/competitors/wshobson-agents/` (35.9k★, MIT, added 2026-05-25 p.m.) — 3-layer evaluation framework with continuous scoring + confidence intervals. Used in `plugin-eval` plugin to assess skill quality.

## Baseline: contest-refactor today

Contest-refactor uses **binary gates** for quality enforcement:

| Gate range | Mechanism | Outcome |
|---|---|---|
| G1-G15 | Schema validation in `validate-artifact.py` | pass/fail |
| G16-G19 | Loop-state invariants | pass/fail |
| G20-G25 | Stop-hook + reviewer envelope discipline | pass/fail |
| G26-G31 | Halt-handoff structural correctness | pass/fail |
| G42 (per TWO-LAYER-DETECTION-GAP) | Two-layer grep+context detection | per-finding pass/fail |
| G43-G44 (per GOVERNANCE-GAP Gap D) | Boundary-rule + graph-confirmed-violation | per-finding pass/fail |
| G45-G47 (per STATE-MACHINE-COMPOSITION-APPENDIX) | Phase-lifecycle ownership invariants | pass/fail |
| G48 (per CROSS-MODEL-CRITIC-GAP Gap E) | Cross-model scoring threshold | pass/fail (above/below threshold) |

Binary gates have advantages: deterministic, fast, no LLM-judgment required, machine-checkable.

Binary gates have disadvantages: no confidence interval, no continuous quality signal, no gradation between "barely passes" and "comfortably passes."

## wshobson's mechanism

Three-layer evaluation framework, blended continuous scoring. Used in `plugin-eval/agents/eval-orchestrator.md` + per `docs/plugin-eval.md`:

### Layer 1: Static analysis (< 2s, free, deterministic)

7 weighted sub-checks against the skill being evaluated:
- `frontmatter_quality` (32%) — YAML completeness, trigger phrase presence, model declaration
- `orchestration_wiring` (23%) — worker-vs-orchestrator pattern adherence
- `progressive_disclosure` (14%) — references/ subdir usage, body size discipline
- `structural_completeness` (10%) — required sections present
- `token_efficiency` (9%) — words-per-instruction ratio
- `ecosystem_coherence` (6%) — naming conventions, cross-references
- `harness_portability` (6%) — passes per-harness validation

Plus multiplicative anti-pattern penalty (orchestrator-masquerading-as-worker, generic-scope, missing-examples, weak-trigger, tool-allowlist-overkill, circular-refs).

Output: 0-100 score + penalty multiplier.

### Layer 2: LLM judge (~30s, 4 calls, semantic)

4 dimensions assessed by LLM judge against the skill:
- `triggering_accuracy` (F1 score on 10 synthetic prompts)
- `orchestration_fitness` (5-point anchored rubric: worker vs orchestrator role match)
- `output_quality` (3 simulated tasks evaluated for output usefulness)
- `scope_calibration` (5-point anchored rubric: scope matches stated trigger)

Output: 0-100 score per dimension.

### Layer 3: Monte Carlo (~2min, 50-100 runs, statistical)

Statistical validation via repeated trials:
- `activation_rate` (Wilson confidence interval)
- `output_consistency` (Bootstrap CI)
- `failure_rate` (Clopper-Pearson CI)
- `token_efficiency` (mean ± stddev)

Output: 0-100 score per dimension + confidence intervals.

### Composite score

```
composite = Σ(dimension_weight × blended_score) × 100 × anti_pattern_penalty
```

10 dimensions weighted: `triggering_accuracy` (25%), `orchestration_fitness` (20%), `output_quality` (15%), `scope_calibration` (12%), `progressive_disclosure` (10%), `token_efficiency` (6%), `robustness` (5%), `structural_completeness` (3%), `code_template_quality` (2%), `ecosystem_coherence` (2%).

Each dimension gets per-layer blend weights (e.g., `triggering_accuracy`: Static 0.15, Judge 0.25, Monte Carlo 0.60).

### Badges & letter grades

- Platinum ≥ 90 (A+ ≥ 97)
- Gold ≥ 80 (B- ≥ 80)
- Silver ≥ 70 (C+ ≥ 77)
- Bronze ≥ 60 (D+ ≥ 67)

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent.

| Mechanism | contest-refactor | wshobson plugin-eval |
|---|:--:|:--:|
| Binary pass/fail gates | ✓ G1-G48 | ✓ (Layer 1 anti-pattern penalty) |
| Continuous static scoring | — | ✓ Layer 1 (7 sub-checks weighted) |
| LLM-judge semantic scoring | partial (Critic emits findings; not quantitative score) | ✓ Layer 2 (4 dimensions × 5-point rubric) |
| Monte Carlo statistical validation | — | ✓ Layer 3 (50-100 runs + Wilson/Bootstrap/Clopper-Pearson CIs) |
| Confidence intervals on score | — | ✓ Layer 3 |
| Composite weighted score | partial (Critic findings have severity; not aggregated into single score) | ✓ Σ(dim_weight × blended_score) |
| Anti-pattern multiplicative penalty | — | ✓ |
| Letter-grade / badge output | — | ✓ Platinum / Gold / Silver / Bronze |
| Per-dimension layer-blend weights | n/a | ✓ |

## Strategic insight

Binary gates are RIGHT for contest-refactor's autonomous-loop discipline (deterministic, machine-checkable, no LLM-judgment latency per gate). Wholesale replacement with continuous scoring would BREAK the loop's determinism guarantees.

But continuous scoring AS A COMPLEMENT addresses a gap: today contest-refactor can say "Critic emitted 12 findings, 3 disqualifiers; HALT_STAGNATION at loop 8 due to oscillation." It CAN'T say "loop quality score: 73/100 (Silver), confidence interval [68, 78], improving trend +5 per loop." That observability is missing.

Use cases for continuous score:

1. **Cross-loop quality trajectory** — track loop_score_trend over the autonomous loop's lifecycle. Useful for "is this loop converging or thrashing?"
2. **Cross-skill quality benchmarking** — compare contest-refactor against other refactor skills using same evaluation framework
3. **HALT_SUCCESS threshold quantification** — instead of "Critic emits no disqualifiers," use "loop score ≥ threshold (default 90)"
4. **User-facing score communication** — "your refactor pass scored 87/100 (Gold)" is more useful than "12 findings retired"

## P2 GAPS — what to potentially adopt (additive only, NEVER replace binary gates)

### Gap A: Layer 1 static-scoring layer (per-loop quality score)

**Adopt** new optional artifact `LOOP_QUALITY_SCORE.json` emitted per loop:

```jsonc
{
  "layer_1_static": {
    "score": 78,
    "breakdown": {
      "finding_dedup_rate": 0.92,        // 0-1, higher = less duplicate findings
      "evidence_density": 0.85,          // findings with file:line evidence / total findings
      "scope_coherence": 0.71,           // findings within source_roots / total findings
      "schema_compliance": 1.0,          // G1-G15 pass rate
      "gate_robustness": 0.94            // G16-G48 pass rate
    },
    "anti_pattern_penalty_multiplier": 0.97,  // 1.0 = no penalty; lower = more penalties
    "anti_patterns_detected": [
      "single_finding_dominates_loop"
    ]
  }
}
```

**Cost**: Python script computes from CURRENT_REVIEW.json + LOOP_STATE.json + REVIEW_HISTORY.json. Deterministic, < 1s per loop.

### Gap B: Layer 2 LLM-judge dimension (HALT_SUCCESS gate complement)

**Adopt** opt-in via `--llm-judge-halt-success` flag. When candidate HALT_SUCCESS state reached:

1. Dispatch LLM-judge subagent with: final CURRENT_REVIEW.json + commit message + diff summary
2. Judge evaluates 4 dimensions vs anchored rubric:
   - Finding quality (1-5: are findings well-founded? evidence-backed?)
   - Resolution thoroughness (1-5: do retirements actually address the issue?)
   - Scope adherence (1-5: did loop stay within Architect's plan?)
   - Test integrity (1-5: do tests verify the refactor's correctness?)
3. Composite judge score = mean of 4 dimensions × 20 = 0-100 scale
4. Gate G49 (NEW): if `--llm-judge-halt-success` enabled AND judge_score < threshold (default 70 = "C+"), state → HALT_STAGNATION/llm_judge_below_threshold (NEW subtype)

**Differs from CROSS-MODEL-CRITIC Gap E (Category 2 SDK scoring)**: this is SAME-model LLM-judge (subagent dispatch); Gap E is CROSS-model SDK scoring (Gemini Flash). Both can ship; Gap B is cheaper (no external provider).

### Gap C: Layer 3 Monte Carlo trajectory analysis (defer)

50-100 runs per loop is impractical for autonomous-loop latency. Defer indefinitely unless contest-refactor adopts plan-branching (HALT-STATE-GAP Gap E), in which case Monte Carlo over branches becomes feasible.

### Gap D: Composite score + badge in HALT_SUCCESS handoff

When Gap A + Gap B both ship, optionally compute composite:

```
composite = 0.6 * layer_1_static.score + 0.4 * layer_2_judge.score
badge = "Platinum" if composite >= 90 else "Gold" if composite >= 80 else "Silver" if composite >= 70 else "Bronze"
```

Surface in halt_handoff:

```
HALT_SUCCESS at loop 8.
Loop quality score: 87/100 (Gold)
- Static score: 78/100
- LLM judge: 92/100 (composite reflects judge weight)

Improvements from baseline:
- finding_dedup_rate: 0.82 → 0.92
- evidence_density: 0.71 → 0.85

Open backlog: 0 priority-1; 2 priority-3 (deferred per Architect plan)
```

User-facing communication win. No behavioral change beyond reporting.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Wholesale replacement of binary gates with continuous score | Breaks determinism. Binary gates are RIGHT for machine-checkable enforcement. Continuous score is ADDITIVE for observability. |
| Layer 3 Monte Carlo per loop | Latency-prohibitive for autonomous loop (50-100 runs × per-loop latency). Defer indefinitely. |
| Anti-pattern penalty as multiplicative on overall score | Multiplicative penalty composes badly with sparse binary signal. Use binary gate (G1-G48 fail = halt loop) instead; reserve multiplicative for Layer 1 sub-checks within the static score. |
| Platinum/Gold/Silver/Bronze gamification surfaced as user goal | User goal is "refactor that improves the codebase," not "earn Platinum." Surface composite score as informational; don't gamify. |
| Cross-loop trajectory chart auto-rendered as Markdown | Out of scope for contest-refactor's text-mode output. If a user wants visualization, they can post-process REVIEW_HISTORY.json. |
| LLM-judge replacing Critic | Critic IS the LLM-judge for findings; this gap proposes a DIFFERENT layer (loop-wide quality assessment, not per-finding). Don't conflate. |

## Adoption order

1. **Gap A (Layer 1 static scoring)** — additive Python script; emit `LOOP_QUALITY_SCORE.json` per loop. Zero behavior change. Useful for observability immediately.
2. **Gap D (composite + badge in HALT_SUCCESS handoff)** — depends on Gap A + Gap B. Surfaces score in user-facing handoff. No gate change.
3. **Gap B (Layer 2 LLM-judge + G49 gate)** — opt-in via `--llm-judge-halt-success`. Adds LLM-judge dispatch latency at HALT_SUCCESS candidate moment. Validate threshold on real loops before defaulting.
4. **Gap C (Layer 3 Monte Carlo)** — defer indefinitely.

## Pairing with other gap docs

- **SCHEMA-GAP**: confidence levels per finding (high|medium) are PER-FINDING; this doc's continuous score is PER-LOOP. Different scale, complementary.
- **CROSS-MODEL-CRITIC-GAP Gap E**: Category-2 cross-model scoring is CROSS-MODEL Gemini-SDK score; Gap B in this doc is SAME-MODEL LLM-judge dispatch. Cross-references — orchestrator may run both at HALT_SUCCESS for layered verification (Gap B same-model + Gap E cross-model).
- **GATES-GAP**: Gap A's `LOOP_QUALITY_SCORE.json` is observational; doesn't add new GATES. Gap B's G49 IS a new gate (LLM-judge threshold).
- **HALT-STATE-GAP**: `LOOP_QUALITY_SCORE.json` complements `LOOP_STATE.json`. Different focus (quality vs progress).
- **STATE-MACHINE-COMPOSITION-APPENDIX**: Gap B (LLM-judge at HALT_SUCCESS) is a NEW Phase 1.6 — runs AFTER Phase 1.5 Cross-Model Scoring (CROSS-MODEL-CRITIC Gap E) when both enabled.

## Cost summary

| Gap | Latency cost | Implementation lift | Determinism impact |
|---|---|---|---|
| Gap A | < 1s per loop (deterministic) | Small (~100 LoC Python) | None |
| Gap B | +5-15s per HALT_SUCCESS candidate | Medium (LLM-judge prompt + subagent dispatch) | Adds non-determinism IF threshold matters; mitigate by recording judge_seed |
| Gap C | +5-15min per loop (50-100 LLM runs) | Large | Heavy non-determinism |
| Gap D | +0s (cosmetic) | Trivial | None |
