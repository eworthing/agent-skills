## Phase 2 — Verify (1-vote, 3-state)

Dedup candidates that point at the same line/mechanism, keeping the one with
the most concrete failure scenario. For each remaining candidate, run **one
verifier** via the {{AGENT_TOOL}} tool: give it the diff, the relevant
file(s), and the candidate, and have it return exactly one of:

{{VERDICT_LADDER}}

Keep candidates where the vote is CONFIRMED or PLAUSIBLE.
