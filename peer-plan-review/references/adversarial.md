# Adversarial Review Stance

A single-round, deliberately skeptical review. The reviewer tries to find
reasons the plan should NOT proceed. No revision loop — present findings and
let the user triage.

Use this stance when the user asks to *pressure-test*, *break the plan*,
*adversarial review*, or *find holes in* a plan.

## Prompt additions

Append these instructions to the normal prompt:

- Default to skepticism — assume the plan can fail in subtle, high-cost,
  or user-visible ways until evidence says otherwise.
- Do not give credit for good intent, partial fixes, or likely follow-up work.
- Focus on expensive, dangerous, or hard-to-detect failures:
  - Auth, permissions, trust boundaries
  - Data loss, corruption, irreversible state changes
  - Rollback safety, idempotency gaps
  - Race conditions, ordering assumptions, stale state
  - Missing error handling for degraded dependencies
  - Schema/version compatibility risks
  - Observability gaps that would hide failure
- Prefer one strong, well-evidenced finding over multiple weak ones.
- Use the structured output format from `references/output-format.md`.
- End with `VERDICT: APPROVED` or `VERDICT: REVISE`.

## Flow

1. Write the adversarial prompt including the additions above.
2. Run the adapter once (no `--resume`).
3. Present findings with the standard review header.
4. Stop. Do not enter the revision loop. Do not auto-apply fixes.
