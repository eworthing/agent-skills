# Instrumented-run predeclaration — next contest-refactor run on BenchHype

Written 2026-08-21, BEFORE the run (register rule D4: preregistration beats
post-hoc interpretation). Everything below is declared now; anything measured
after the run that is not declared here is an anecdote, labeled as such.

The run's primary purpose is unchanged: certify the shipped tranche (items
G33–G47, item 14 wrapper, epoch scoping). Nothing in this kit touches the loop
path — every tool here is operator-side, post-hoc, or observe-only.

## Launch checklist (operator, in order)

1. **Pin the test command** (human act — that is the point):
   `python3 /Users/Shared/git/agent-skills/contest-refactor/scripts/attested_run.py --trust -- <real test command>`
   run from the BenchHype repo root. Wrong-directory pins are refused (exit 2).
2. **Verify `.gitignore` covers build/test byproducts.** Untracked byproducts
   change the source fingerprint mid-run and degrade wrapper records to
   `unavailable` (uncitable) — check before, not after.
3. **Install the observer** (exactly ONE directory, remove after the run):
   `cp analysis/contest-refactor/run-kit/observe-tools.ts ~/.config/opencode/plugins/`
   Scratch-tested 2026-08-21: logs only, never blocks; both `plugin/` and
   `plugins/` load, so never install in both (double records).
4. **Launch with `--scope`** (the run-gated probe): scope to `BenchHypeKit` (or
   the operator's chosen subtree) and record the exact flag used.
5. After terminal state: run the post-run protocol below, then remove the
   observer plugin.

## Predeclared measurements

### M1 — G17 promotion datapoints
- **Applicable loop**: `what_changed` matches a canonical Deepening Keyword
  (case-insensitive substring; canonical block in `output-format-json.md`).
- **Violation**: applicable ∧ no test path in `changed_paths` ∧
  `interface_test_coverage_path` null/empty → `[G17]` line.
- **Restraint**: applicable ∧ a `changed_paths` entry classifies as a test path
  ∧ G17 silent.
- **Blind**: any `[g17-check-blind]` line — each one adjudicated by a human.
- Banked from the historical sweep (all Swift, adjudication pending): 3
  applicable loop-events, 3 violations, 0 restraint, 1 blind (v2-era
  `changed_paths` absent — expected-blind). The ≥2-languages bar CANNOT be met
  by this run (Swift again); promotion stays open regardless of outcome.

### M2 — run_id stability (new, from the historical sweep)
The Aug-19 run minted `run_id` per loop (`loop-2-302837137`; loop 1 null) —
wrong format, wrong lifecycle — which is what made the transition check go
blind (`hint=run_id must be stable across the loops of one run`). The current
SKILL.md rev instructs minting `run-<UTC date>-<hex>` at sub-step 3 and
carrying it unchanged. **PASS**: every loop artifact of the new run carries one
identical `run-…` id and `[transition-check-blind]` does not fire for run_id
instability. **FAIL**: either condition broken.

### M3 — wrapper adoption (observation, 1 datapoint of the queued probe)
Per loop: did Step-3 invoke `attested_run.py` and emit
`loop_result.execution_evidence`? Record adopted / not-adopted / adopted-but-
uncitable per loop, from the artifact + `~/.contest-refactor/attestation-ledger.jsonl`.
If any loop cites evidence: run `validate-artifact.py` with the three
attestation flags — G47's first live checks. No adoption-rate claim from n=1.

### M4 — `findings_carried_from_prior_loops` first live emission
BenchHype has prior terminal runs, so the observed-only spec
(`output-format-json.md`) gets its first live instance. **PASS**: emitted value
matches the spec's shape and provenance rules. Record content either way.

### M5 — reviewer input surface (staleness trigger b)
From the reviewer subagent's transcript (opencode db, child session): did the
reviewer read any untracked/new files? Feeds the reviewer-baseline staleness
log; no re-measure is triggered from prose impressions, only from this record.

### M6 — cost accounting
`cost_accounting.py --dir-like BenchHype --since <launch date>`, immediately
after terminal state. Baseline banked from the Aug-19 run: **$9.30, 500
assistant messages, 92.6M resident tokens** (parent + 2 loop executors + 2
challengers, `opencode-go/minimax-m3`). Tracked series only — the codebase and
skill both changed, so no per-feature cost attribution is claimed.

### M7 — post-hoc gate sweep (phase-to-gate matrix)
`posthoc_gate_sweep.py` re-run after the run; new rows diffed against
`reports/benchhype-posthoc-sweep-2026-08-21.*`. Strict failures on pre-epoch
artifacts are epoch observations, not violations. The new run's own loops are
the first rows where the current gate set is contemporaneous — those rows ARE
violations if they fail.

### M8 — observer telemetry (Tier-3 design data)
From `~/.contest-refactor/observe/tool-events.jsonl` (via CONTEST_REFACTOR_HOME
default): tool-call counts, bash commands at commit boundaries, after-hook
payload shape. Already resolved in the scratch test and to be confirmed at run
scale: opencode's `tool.execute.after` metadata is `{output, exit, truncated}`
— a raw exit code IS present (the Item-14 uncertain cell, now observed).

### Conditional (recorded only if reached)
- **G43 live behavior**: requires loop ≥ 4 with clean dimensions.
- **G17 restraint case**: requires an applicable loop that changed a test file.

## Post-run protocol (in order)
1. `cost_accounting.py` (M6) — first, before any other session activity muddies
   the window.
2. `posthoc_gate_sweep.py` (M7, M1, M2) and `coverage_citations.py` (item-24
   delta vs the 2026-08-21 baseline: 302/1313 files, BenchHypeKit 24%).
3. M3/M4 from the terminal artifact + ledger; M5 from the reviewer transcript.
4. Human adjudication of every G17 line and blind line; ledger entries in
   `docs/behavioral-validation-ledger.md`.
5. Remove the observer plugin; record removal.

## Non-claims
- No before/after cost attribution to any single feature (M6 note).
- No G17 promotion this run (single language).
- No adoption-rate claim from M3's n=1.
- Sweep percentages are unique-load proxies where they touch token counts —
  no billed-savings bound in either direction (register, audit round 4).
