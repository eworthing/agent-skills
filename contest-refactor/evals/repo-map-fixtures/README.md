# W2.1 repo-map eval fixtures

Two paired fixtures for the W2.1 repo-map / import-graph advisory candidate-evidence
(Method.md Step 0 / Step 3). They gate the **model-behavior track** of the W2.1 ship
criteria — separate from the script/isolation track covered by
`scripts/_repo_map_selftest.py`.

**Script/isolation track (necessary but not sufficient):** `_repo_map_selftest.py`
passes. **Model-behavior track (required to authorize auto-engage):** both arms below
show measured lift (recall) AND zero new false positives (restraint). The owner runs
these; no committed auto-grader.

## Arms

| arm | fixture | planted defect | expected outcome |
|---|---|---|---|
| recall | `recall-cross-module-coupling-1/` | billing ↔ reporting import cycle hidden across directory boundary | Critic with map flags the cycle; Critic without map may miss it |
| restraint | `restraint-clean-dag-1/` | none — clean api→domain→infrastructure DAG | Map introduces zero new flags vs no-map control |

## Measurement protocol

For each fixture:

1. **Generate map evidence:**
   ```bash
   python3 scripts/repo_map.py evals/repo-map-fixtures/<fixture>/codebase/ --format md
   ```

2. **Arm A (no-map control):** spawn Critic on `codebase/` with standard Step-0 discovery
   but WITHOUT the repo-map output.

3. **Arm B (with-map):** spawn Critic on the same `codebase/` with the `repo_map.py`
   markdown output prepended to Step-0 candidate evidence.

4. **Grade:**
   - **Recall arm:** Arm B must cite the `billing <-> reporting` cycle as a candidate
     coupling signal; Arm A should miss it. If Arm A also catches it (e.g. from a direct
     source read), the recall case is moot — that gap was already closed by existing audits.
   - **Restraint arm:** count new flags raised by Arm B but not by Arm A. Must be zero.
     The `domain -> infrastructure` edge is the intended dependency direction and must NOT
     be flagged.

5. **Repeat K≥5 times** per arm per fixture (same posture as `principal_baseline` replication
   in `evals/README.md`). Use zero/fixed temperature where the provider exposes it.

6. **Ship gate (auto-engage):**
   - Recall arm: Arm B shows a strict majority (≥3/5) catch rate on the billing↔reporting
     cycle AND Arm A does not (differential lift attributable to the map).
   - Restraint arm: zero new false flags across all K runs.
   - Both arms must pass before auto-engage (first_party_file_count > 300) ships.

## Doctrine

`promotion_allowed: false` — the repo-map is advisory evidence, not a verdict. Even
when the map surfaces a cycle, the Critic must re-derive the claim from source:
investigate whether the coupling is a necessary invariant or a leaky seam, cite
the exact import chain (file:line), and assess consequence before elevating to a
finding. The map never decides; it surfaces candidates.

See `scripts/repo_map.py` docstring and `references/method.md` Step 0 / Step 3 for
the full doctrine boundary.

## Measurement results

First run 2026-06-30 (sonnet, K=5): **restraint PASS** (0 added false positives), **recall inconclusive** — the 8-file fixture is fully visible to the no-map Critic (5/5 catch), so it cannot demonstrate the map's at-scale recall value. Auto-engage default-on stays gated on a realistic-scale recall fixture. See [`MEASUREMENT-2026-06-30.md`](MEASUREMENT-2026-06-30.md).

**Update (windowed recall):** `recall-windowed-large-1/` (20 pkgs / 40 files, buried cycle) measured recall under an at-scale window — no-map 0/5 vs with-map 5/5. Both recall and restraint now pass; auto-engage above >300 files is justified. See [`MEASUREMENT-2026-06-30.md`](MEASUREMENT-2026-06-30.md).
