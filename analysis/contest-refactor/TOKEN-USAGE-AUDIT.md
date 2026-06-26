# Token-Usage Audit — contest-refactor per-loop + per-run cost model

**Date**: 2026-06-26
**Author**: Claude (Opus 4.8) — in-session analysis
**Snapshot**: repo HEAD `537fd95`
**Measurement basis**: file word counts (`wc -w`, excluding ignored local cache files such as `.DS_Store` and `__pycache__/`); token heuristic **tok ≈ words × 1.33**; real artifact sizes from `evals/fixtures/bootstrap-repo/REVIEW_HISTORY.md`; loading model read from `SKILL.md` §Reference Load Matrix + `references/trust-model.md` subagent template + `references/implementation-reviewer.md` subagent template.
**Status**: estimate-grade — source-walk and thinking are the widest bands (see [Methodology & caveats](#methodology--caveats)).

---

## Summary

contest-refactor's revisions were never measured for token cost. This audit supplies a baseline.

A skill's token cost is not its repo size — it is **what enters an agent context, times how often**. Three tiers:

1. **Trigger-load** — `SKILL.md`, read once when the skill fires.
2. **Per-loop reload** — a subset of `references/*.md`, **re-read by every fresh loop subagent** (state flows via files, so each loop is a clean context that reloads from disk).
3. **Out-of-context** — `scripts/`, `evals/`, `canon/`, `fixtures/`, `assets/` — execute or sit on disk but never enter reasoning context.

Headline numbers (Loop-Isolation mode, Apple stack):

- Per-loop fixed protocol+reference reload ≈ **~46.4k tok** before target-source reads and reviewer sidecar.
- **`SKILL.md` is re-read every loop** (not just at trigger) — `references/trust-model.md:62` tells each loop subagent "Read first: `SKILL.md`".
- The implementation-reviewer sidecar is not a 10k-token add-on; its own template reloads rubric/method/provider/lens context, so it is closer to **~32–42k input tokens** on the Apple stack.
- Typical per-loop total ≈ **160–175k tok**; a typical 8-loop 9.5-convergence run ≈ **~1.4M tok**.
- The recent T1/T2/A1/B1 feature wave added substantial *disk* weight but **~0 run tokens** — it landed in tier 3.

## The 3-tier cost model

| Tier | Files | Loads | Run-cost driver |
|------|-------|-------|-----------------|
| **Trigger-load** | `SKILL.md` (5,527 w) | once per invocation | ~7.4k tok — but also re-read per loop (see tier 2) |
| **Per-loop reload** | `references/*.md` subset | **every loop, fresh subagent** | dominant fixed loop cost — ~46.4k tok/loop before sidecars (table below) |
| **Out-of-context** | `scripts/` (27.8k w), `evals/` top-level (14.1k w), `evals/fixtures/` (60.8k w), `canon/` (918 w), `assets/` (1.1k w) | never enter reasoning context during normal skill execution (scripts exec → compact stdout/JSON back) | **~0 run tokens** (≈104.7k words / ≈139k tok of disk weight) |

About two-thirds of the repo's measured text (`scripts/` + `evals/` + `canon/` + `assets/`) is out-of-context. Growth there is free at runtime unless the skill or an eval explicitly opens those files.

## Per-loop token budget

Loop-Isolation mode (the default — each loop a fresh `Agent` subagent), Apple stack. `tok ≈ words × 1.33`.

### INPUT — protocol + references (re-paid every loop)

| File | words | tok |
|------|------:|----:|
| `SKILL.md` ⚠️ re-read/loop | 5,527 | 7.4k |
| `output-format-json.md` | 5,349 | 7.1k |
| `validation.md` | 4,825 | 6.4k |
| `method.md` | 3,695 | 4.9k |
| `architecture-rubric.md` | 3,592 | 4.8k |
| `lens-apple.md` | 3,129 | 4.2k |
| `implementation-reviewer.md` | 2,228 | 3.0k |
| `output-format-state-schemas.md` | 2,016 | 2.7k |
| `provider-adapters.md` | 1,792 | 2.4k |
| `output-format-markdown.md` | 1,377 | 1.8k |
| `lens-security.md` | 1,001 | 1.3k |
| `output-format.md` | 329 | 0.4k |
| **Σ fixed protocol / loop** | **34,860** | **~46.4k** |

### INPUT — delta basis (every CONTINUE loop)

Bounded — **not** the full archive (`references/trust-model.md:64`: read `REVIEW_HISTORY.md` tail, last 2 loops).

| Source | tok |
|--------|----:|
| prior `CURRENT_REVIEW.md` | ~7.7k |
| `REVIEW_HISTORY.md` tail-2 loops | ~10.6k |
| `findings_registry.json` | ~0.5k |
| **Σ delta basis** | **~18.8k** |

### INPUT — variable (target repo)

Critic Step 3–8 source walk + Actor edits + gate stdout = **15k–60k tok**, repo-size dependent. On a large target this is the elephant and dwarfs references; on a small repo references dominate.

### Sidecar — implementation-reviewer subagent (1× per non-HALT Step 3 loop)

Own context comes from the reviewer template in `implementation-reviewer.md`, not just from the reviewer file itself.

| Source | tok |
|--------|----:|
| reviewer fixed refs (`implementation-reviewer.md`, `architecture-rubric.md`, `method.md`, `provider-adapters.md`, selected Apple lens) | ~19.2k |
| `CURRENT_REVIEW.md` finding context | ~7.7k |
| diff + changed hunks | ~5–15k |
| **Σ sidecar input** | **~32–42k in / 0.5k out** |

Generic-stack reviewer sidecars are ~3.1k tok lighter when the selected lens is `lens-generic.md` instead of `lens-apple.md`.

### OUTPUT — generation (~4–5× input $ rate)

| Artifact | tok |
|----------|----:|
| `CURRENT_REVIEW.md` | 7.7k |
| `CURRENT_REVIEW.json` | 3.3k |
| `REVIEW_HISTORY.md` archive append | 4.9k |
| code edits | 2–10k |
| reasoning / thinking | 8–20k |
| **Σ output / loop** | **~26k–46k** |

### Per-loop total

```
small repo / low gen:   ~46k + 19k + 15k + 32k  in  + 26k out  ≈ 138k tok
large repo / high gen:  ~46k + 19k + 60k + 42k  in  + 46k out  ≈ 213k tok
typical:                                                        ≈ 160–175k tok/loop
```

## Run totals

One-time costs outside the loop: **start** (`resume-detection.md`, `halt-handoff.md`, `provider-adapters.md`, `SKILL.md`, `trust-model.md`, `architecture-rubric.md`, `method.md`, `lenses.md`, selected Apple lens, `lens-security.md` read in main) ≈ **~35k** before repo `CONTEXT.md`/ADR/config reads; **G32 challenger** at end (`halt-verifier.md` + reviewer spawn profile + re-derived scorecard from source) ≈ **~30–40k** and fires only when `HALT_SUCCESS_candidate` is reached.

| Loops | Typical (~165k/loop) | + start | + challenger if HALT_SUCCESS | **Run total** |
|------:|---------------------:|--------:|-----------------------------:|--------------:|
| 3 (quick) | 495k | +35k | +0–40k | **~530–570k tok** |
| 8 (typical 9.5 convergence) | 1.32M | +35k | +30–40k | **~1.39M tok** |
| 15 (hard repo) | 2.48M | +35k | +30–40k | **~2.55M tok** |

Input : output ≈ **4 : 1**. Output bills at ~4–5× the input rate, so the ~30–40k output/loop is a larger cost slice than its token count implies.

## Why the reload isn't waste

The per-loop reload is **load-bearing, not redundant**. The design wants each Critic *blind*: write an independent per-dimension scorecard from current source before reading any prior verdict (`method.md:48` Anchor-to-source; `trust-model.md:64` blind-critic ordering). Caching the prior loop's context cross-loop would defeat the anti-anchoring property the whole skill rests on.

So the lever is to shrink **what** reloads (trim fat reference files), **not** to kill the reload.

Tradeoff worth noting: **inline mode** (same agent runs consecutive loops — the documented *failure* path for an `unknown` provider or spawn-blocked host, per `SKILL.md` §Loop Isolation) keeps references in one context, so loop N+1 hits the prompt cache and re-pays little input. Loop-Isolation re-pays each loop's reads in full. Inline is cheaper on input tokens but is chosen against for independence + context-hygiene reasons, not cost.

## No quadratic blowup

`REVIEW_HISTORY.md` grows monotonically on disk (~3.7–5k words appended per loop; the real `bootstrap-repo` archive is 36k words across ~10 loop blocks). But it is **not** re-read whole each loop. Delta basis is the compact `findings_registry.json` (8–140 words in real fixtures) + the prior loop's scorecard + the **tail-2** loops only (`trust-model.md:64`). Per-loop read cost is therefore O(1) in loop count, not O(N). Confirmed — no accumulating history-read tax.

## Marginal cost of a change (per +1k words, at 8 loops)

| Edit target | tok/run added per +1k words |
|-------------|----------------------------:|
| ref loaded in main start + loop + reviewer (`method.md`, `architecture-rubric.md`, selected stack lens, `provider-adapters.md`) | **+22.6k** (×17 reads: start + 8 loops + 8 reviewer sidecars) |
| `implementation-reviewer.md` | **+21.3k** (×16 reads: loop + reviewer sidecar) |
| ordinary per-loop ref (`validation.md`, `output-format*.md`, `lens-security.md`) | **+10.6k** (×8 loops; add +1.3k if also loaded at start) |
| `SKILL.md` | **~+12.0k** (×9 — trigger + every loop) |
| start-only ref (`resume-detection`/`halt-handoff`/`trust-model`) | +1.3k (×1) |
| `halt-verifier.md` | +1.3k (only if `HALT_SUCCESS` reached) |
| **`scripts/` / `evals/` / `canon/` / `fixtures/`** | **+0** (out of context) |

**Conclusion:** the recent T1/T2/A1/B1 wave (SARIF export, scorecard/trend report, change-coupling audit, module-boundary audit, principal-defect benchmark, strictness presets) landed almost entirely in tier 3 — scripts + evals + fixtures. It adds disk weight for **≈0 normal-run tokens**. Whether by design or instinct, the heavy machinery went where it costs nothing per run.

## Ranked reduction targets

By current whole-file footprint in an 8-loop Apple-stack run (not per-1k-word savings):

1. **`method.md`** (3,695 w) / **`architecture-rubric.md`** (3,592 w) — ~83k / ~81k per run because each is read at start, by every loop, and by every reviewer sidecar.
2. **`lens-apple.md`** (3,129 w) — ~71k per run for the same start + loop + reviewer reason. Generic-stack runs are much lighter here.
3. **`SKILL.md`** (5,527 w) — ~66k per run. Re-read every loop *and* at trigger. The flag-parsing mega-paragraph at `SKILL.md:117` (every flag — `--strictness`, `--purge`, `--incidents`, …— described inline) is prime to move behind a reference loaded only when a flag is actually present.
4. **`output-format-json.md`** (5,349 w) — ~57k per run. Fattest ordinary per-loop-only reference.
5. **`validation.md`** (4,825 w) — ~51k per run.
6. **`implementation-reviewer.md`** (2,228 w) — ~47k per run because the loop and reviewer sidecar both read it.

Trimming any of these pays back × loop count. Trimming a script pays back nothing (and that's fine — leave scripts alone).

## Recommended follow-up — `scripts/token-budget.py`

Not built here; proposed so this audit becomes a living number instead of a one-time snapshot. Sketch:

- **Tokenizer-based** per-file counts (replace the word×1.33 heuristic with a real tokenizer).
- Compute the per-loop fixed-input sum (the tier-2 reload set) and the trigger-load total.
- `--loops N` → project a full-run budget (low/typical/high bands).
- `--diff <ref>` → classify a change's tok/run delta by tier (start + loop + reviewer, loop-only, start-only, halt-only, out-of-context), so a PR that fattens `method.md` shows the true `×17` cost in an 8-loop Apple-stack run.
- CI-checkable: fail or warn when the tier-1/2 footprint grows past a threshold, making reference creep visible at review time.

## Reduction applied (tokenizer-measured)

`scripts/token-budget.py` (the follow-up above) is now built — tiktoken/cl100k_base when importable, deterministic fallback otherwise; `--loaded-set <step>` prints the exact per-step reload set, guarded by `_token_budget_selftest.py` against the Reference Load Matrix. All figures below are **real tiktoken counts**, not the word×1.33 estimate used elsewhere in this audit (tiktoken runs higher: the per-loop fixed reload is ~61.1k tok, not the ~43.7k estimate).

Reductions land on `docs/contest-refactor-token-audit`, one commit per lever, gated by the verification harness in `/Users/pl/.claude/plans/tender-mixing-avalanche.md`. Each row is paired with its commit so reverting a lever reverts its row.

| Lever | Change | Net tok/run (8-loop Apple) | Verification |
|-------|--------|---------------------------:|--------------|
| Baseline | — | 499,486 | all gates green at HEAD `22055c7` |
| **Lever 1** | Extract main-only Step −1/Step 0 → `references/startup.md`; per-loop `SKILL.md` read drops 10,718→8,903 tok | **−14,068 (−2.82%)** | B1 load-path proof (startup.md absent from loop set; referenced only by SKILL.md); validate-repo OK; 18 fixtures; eval-skill 92% unchanged; behavioral-by-construction (no loop-rule text changed) |

Run projection after Lever 1: per-loop fixed reload 59,281 + `SKILL.md` trigger 8,903 + `startup.md` once 2,267 = **485,418 tok/run**.

**Levers 2–3 evaluated and declined** (decision 2026-06-26). Lever 1 captured the bulk of the safe win the audit predicted (~1.5–3% ceiling) from one structural move. Lever 2 (cross-file dedupe) netted only ~0.1–0.3% once schema self-containment (`output-format-json.md` enum values) and teaching examples (`method.md` fake-clean cases) were excluded as unsafe to strip. Lever 3 (concision via anthropic-grade-optimizer) offered ~1% but edits loop-rule prose, requiring a ~90–126-run powered behavioral sweep to prove no efficacy loss — diminishing returns past the structural win. Caveman remains rejected throughout (degrades hot-path instruction files). Peer-reviewed (Codex gpt-5.5 high: REVISE→APPROVED).

## Methodology & caveats

- **Heuristic, not a tokenizer.** `tok ≈ words × 1.33`. JSON is denser per token than prose, so JSON-schema/instance figures are approximate. A real tokenizer (the `token-budget.py` follow-up) would tighten these.
- **Widest bands are repo-driven.** The target-source walk (15–60k/loop) and thinking tokens (8–20k/loop) dominate variance and scale with the size of the repo being refactored — not with anything in this skill. On a large target, references are a minority of the run; on a small target they dominate.
- **Mode + stack assumptions.** Numbers assume Loop-Isolation (subagent) mode on the Apple stack. Generic stack is ~2.3k words lighter per loop and ~2.3k words lighter per reviewer sidecar (`lens-generic.md` 821 w vs `lens-apple.md` 3,129 w). Inline mode is cheaper on input (cache hits) but is the failure path.
- **Snapshot.** All figures are measured at HEAD `537fd95` and drift as references grow. Re-run the measurement commands (see the audit's companion verification) to refresh.
