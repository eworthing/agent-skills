# Repo-map recall/restraint measurement — 2026-06-30

**Method.** Model: `claude-sonnet-4-6` (the contest-refactor default `loop_model`). K=5 per cell,
**between-subjects** (no-map agents never saw the map, so no contamination). Both fixtures presented
fully inline; each Critic asked the single narrow question "is there an import cycle between
top-level packages?" **Blind**: fixtures labelled A / B with no hint which contained a cycle.

## Results

| arm | cell | catch / flag rate |
|---|---|---|
| **Recall** (fixture A — genuine `billing`↔`reporting` cycle) | no-map | **5/5** caught (billing,reporting) |
| | with-map | **5/5** caught |
| | **differential** | **0** → ship-gate (with-map ≥3/5 **and** > no-map) **NOT met** |
| **Restraint** (fixture B — clean `api`→`domain`→`infrastructure` DAG) | no-map | **1/5** false flag (one run hallucinated a dep-direction violation) |
| | with-map | **0/5** false flags |
| | **result** | with-map ≤ no-map → ship-gate **MET** |

## Conclusion

- **RESTRAINT: PASS.** The map introduced **zero** new false positives; it was in fact *cleaner*
  than the no-map control (which produced one hallucinated violation). Consistent with the
  deterministic gate-isolation selftest (`_repo_map_selftest.py`).
- **RECALL: INCONCLUSIVE (ceiling artifact).** The 8-file fixture fits fully in context, so the
  no-map Critic already catches the cycle 5/5 — there is no recall gap for the map to close at
  this scale. The map's value proposition (surfacing coupling the Critic **misses at scale**, in a
  >300-file repo it cannot hold in one context window) is **not testable on a toy fixture**.

## Implication

Auto-engage-by-default is **not yet justified by a measured recall lift**. The map is **safe**
(restraint-validated here + isolation-proven) and is shipped as an **available manual/opt-in Step-0
helper**. A genuine recall measurement needs a realistically large fixture (or a context-windowed
no-map condition) where the no-map Critic provably **misses** the buried cycle. Until then,
`method.md` presents the map as available, not auto-proven.

_Raw verdicts (10 runs): no-map A 5/5 cycle, B 4/5 clean + 1 false violation; with-map A 5/5 cycle,
B 5/5 clean._
