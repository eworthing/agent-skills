# Token-Usage Audit — contest-refactor per-loop + per-run cost model

**Date**: 2026-06-26
**Author**: Claude (Opus 4.8) — in-session analysis
**Snapshot**: repo HEAD `0d4e8e3`
**Measurement basis**: file word counts (`wc -w`); token heuristic **tok ≈ words × 1.33**; real artifact sizes from `evals/fixtures/bootstrap-repo/REVIEW_HISTORY.md`; loading model read from `SKILL.md` §Reference Load Matrix + `references/trust-model.md` subagent template.
**Status**: estimate-grade — source-walk and thinking are the widest bands (see [Methodology & caveats](#methodology--caveats)).

---

## Summary

contest-refactor's revisions were never measured for token cost. This audit supplies a baseline.

A skill's token cost is not its repo size — it is **what enters an agent context, times how often**. Three tiers:

1. **Trigger-load** — `SKILL.md`, read once when the skill fires.
2. **Per-loop reload** — a subset of `references/*.md`, **re-read by every fresh loop subagent** (state flows via files, so each loop is a clean context that reloads from disk).
3. **Out-of-context** — `scripts/`, `evals/`, `canon/`, `fixtures/`, `assets/` — execute or sit on disk but never enter reasoning context.

Headline numbers (Loop-Isolation mode, Apple stack):

- Per-loop fixed protocol+reference reload ≈ **~43.7k tok** — the dominant fixed cost.
- **`SKILL.md` is re-read every loop** (not just at trigger) — `references/trust-model.md:62` tells each loop subagent "Read first: `SKILL.md`".
- Typical per-loop total ≈ **130–140k tok**; a typical 8-loop 9.5-convergence run ≈ **~1.14M tok**.
- The recent T1/T2/A1/B1 feature wave added ~56k tok of *disk* weight but **~0 run tokens** — it all landed in tier 3.

## The 3-tier cost model

| Tier | Files | Loads | Run-cost driver |
|------|-------|-------|-----------------|
| **Trigger-load** | `SKILL.md` (5,527 w) | once per invocation | ~7.4k tok — but also re-read per loop (see tier 2) |
| **Per-loop reload** | `references/*.md` subset | **every loop, fresh subagent** | dominant — ~43.7k tok/loop (table below) |
| **Out-of-context** | `scripts/` (27.8k w), `evals/` (14.1k w), `canon/` (918 w), `fixtures/`, `assets/` (1.1k w) | never enter reasoning context (scripts exec → ~300-tok JSON back) | **~0** (≈58k tok of disk weight) |

Roughly half the repo's text (`scripts/` + `evals/` + `canon/` + `assets/`) is out-of-context. Growth there is free at runtime.

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
| `provider-adapters.md` | 1,792 | 2.4k |
| `output-format-markdown.md` | 1,377 | 1.8k |
| `lens-security.md` | 1,001 | 1.3k |
| `output-format.md` | 329 | 0.4k |
| **Σ fixed protocol / loop** | **32,844** | **~43.7k** |

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

### Sidecar — implementation-reviewer subagent (1× per loop)

Own context: `implementation-reviewer.md` (~3k) + diff + changed files (~5–15k) ≈ **~10k in / 0.5k out**.

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
small repo / low gen:   ~44k + 19k + 15k + 10k  in  + 26k out  ≈ 113k tok
large repo / high gen:  ~44k + 19k + 60k + 12k  in  + 46k out  ≈ 181k tok
typical:                                                        ≈ 130–140k tok/loop
```

## Run totals

One-time costs outside the loop: **start** (`SKILL.md` + `resume-detection.md` + `halt-handoff.md` + `trust-model.md` read in main) ≈ **~20k**; **G32 challenger** at end (`halt-verifier.md` + re-derive scorecard from source) ≈ **~30–40k**.

| Loops | Typical (~135k/loop) | + one-time | **Run total** |
|------:|---------------------:|-----------:|--------------:|
| 3 (quick) | 405k | +20k | **~425k tok** |
| 8 (typical 9.5 convergence) | 1.08M | +60k | **~1.14M tok** |
| 15 (hard repo) | 2.03M | +60k | **~2.1M tok** |

Input : output ≈ **3.5 : 1**. Output bills at ~4–5× the input rate, so the ~30k output/loop is a larger cost slice than its token count implies.

## Why the reload isn't waste

The per-loop reload is **load-bearing, not redundant**. The design wants each Critic *blind*: write an independent per-dimension scorecard from current source before reading any prior verdict (`method.md:48` Anchor-to-source; `trust-model.md:64` blind-critic ordering). Caching the prior loop's context cross-loop would defeat the anti-anchoring property the whole skill rests on.

So the lever is to shrink **what** reloads (trim fat reference files), **not** to kill the reload.

Tradeoff worth noting: **inline mode** (same agent runs consecutive loops — the documented *failure* path for an `unknown` provider or spawn-blocked host, per `SKILL.md` §Loop Isolation) keeps references in one context, so loop N+1 hits the prompt cache and re-pays little input. Loop-Isolation re-pays each loop's reads in full. Inline is cheaper on input tokens but is chosen against for independence + context-hygiene reasons, not cost.

## No quadratic blowup

`REVIEW_HISTORY.md` grows monotonically on disk (~3.7–5k words appended per loop; the real `bootstrap-repo` archive is 36k words across ~10 loop blocks). But it is **not** re-read whole each loop. Delta basis is the compact `findings_registry.json` (8–140 words in real fixtures) + the prior loop's scorecard + the **tail-2** loops only (`trust-model.md:64`). Per-loop read cost is therefore O(1) in loop count, not O(N). Confirmed — no accumulating history-read tax.

## Marginal cost of a change (per +1k words, at 8 loops)

| Edit target | tok/run added per +1k words |
|-------------|----------------------------:|
| per-loop ref (`method`/`validation`/`architecture-rubric`/`output-format-json`/`lens-*`/`implementation-reviewer`/`provider-adapters`/`output-format-markdown`) | **+10.6k** (×8 loops) |
| `SKILL.md` | **~+12k** (×9 — trigger + every loop) |
| start-only ref (`resume-detection`/`halt-handoff`/`trust-model`) | +1.3k (×1) |
| `halt-verifier.md` | +1.3k (only if `HALT_SUCCESS` reached) |
| **`scripts/` / `evals/` / `canon/` / `fixtures/`** | **+0** (out of context) |

**Conclusion:** the recent T1/T2/A1/B1 wave (SARIF export, scorecard/trend report, change-coupling audit, module-boundary audit, principal-defect benchmark, strictness presets) landed almost entirely in tier 3 — scripts + evals + fixtures. It added ~56k tok of disk weight for **≈0 run tokens**. Whether by design or instinct, the heavy machinery went where it costs nothing per run.

## Ranked reduction targets

By tok/run saved per 1k words cut (×9 for `SKILL.md`, ×8 for other per-loop refs):

1. **`SKILL.md`** — ~66k/run per 1k words. Re-read every loop *and* at trigger → the highest-leverage file. The flag-parsing mega-paragraph at `SKILL.md:117` (every flag — `--strictness`, `--purge`, `--incidents`, …— described inline) is prime to move behind a reference loaded only when a flag is actually present.
2. **`output-format-json.md`** (5,349 w) — ~57k/run. Fattest single per-loop reference (the JSON schema, needed every emit).
3. **`validation.md`** (4,825 w) — ~51k/run.
4. **`method.md`** (3,695 w) / **`architecture-rubric.md`** (3,592 w) — ~39k/run each.

Trimming any of these pays back × loop count. Trimming a script pays back nothing (and that's fine — leave scripts alone).

## Recommended follow-up — `scripts/token-budget.py`

Not built here; proposed so this audit becomes a living number instead of a one-time snapshot. Sketch:

- **Tokenizer-based** per-file counts (replace the word×1.33 heuristic with a real tokenizer).
- Compute the per-loop fixed-input sum (the tier-2 reload set) and the trigger-load total.
- `--loops N` → project a full-run budget (low/typical/high bands).
- `--diff <ref>` → classify a change's tok/run delta by tier (per-loop ref vs start-only vs out-of-context), so a PR that fattens `validation.md` shows its true `×loops` cost.
- CI-checkable: fail or warn when the tier-1/2 footprint grows past a threshold, making reference creep visible at review time.

## Methodology & caveats

- **Heuristic, not a tokenizer.** `tok ≈ words × 1.33`. JSON is denser per token than prose, so JSON-schema/instance figures are approximate. A real tokenizer (the `token-budget.py` follow-up) would tighten these.
- **Widest bands are repo-driven.** The target-source walk (15–60k/loop) and thinking tokens (8–20k/loop) dominate variance and scale with the size of the repo being refactored — not with anything in this skill. On a large target, references are a minority of the run; on a small target they dominate.
- **Mode + stack assumptions.** Numbers assume Loop-Isolation (subagent) mode on the Apple stack. Generic stack is ~2.3k words lighter per loop (`lens-generic.md` 821 w vs `lens-apple.md` 3,129 w). Inline mode is cheaper on input (cache hits) but is the failure path.
- **Snapshot.** All figures are measured at HEAD `0d4e8e3` and drift as references grow. Re-run the measurement commands (see the audit's companion verification) to refresh.
