## Phase 2 — Verify (1-vote, recall-biased)

Dedup near-duplicates (same defect, same location, same reason → keep one). For
each remaining candidate, run **one verifier** via the {{AGENT_TOOL}} tool:
give it the diff, the relevant file(s), and the candidate; it returns exactly
one of **CONFIRMED / PLAUSIBLE / REFUTED**.

{{RECALL_BIASED_RUBRIC}}

Keep **CONFIRMED and PLAUSIBLE**. Drop REFUTED.
