# Answer Key — Weekly Email Digest fixture (`digest-plan.md`)

Correct overall verdict: **REVISE** (6 blocking defects present).

## Seeded BLOCKING defects

| ID | Category | Where | Detection |
|----|----------|-------|-----------|
| B-SEQ | Sequencing / hidden dependency | Task 1 & Task 3 read `last_digest_sent_at` / `digest_opt_in`, but Task 4 (the migration that creates those columns) is sequenced AFTER them. | general |
| B-ROLLBACK | Data loss / irreversible migration | Task 4 drops `newsletter_flag` in the same migration after deriving from it — no backfill safety, no down-migration. | general |
| B-UNDEF | Undefined reference / name drift (executability) | Task 3 calls `enqueue_digest_job()` and uses a `DigestScheduler` type; Task 2 only says "implement the scheduler/worker" and never defines them — names drift. | general (executability) |
| B-UNDERSPEC | Under-specification (executability) | Task 5: "Add appropriate error handling and retries" — no count, no error classes, no backoff. | general (executability) |
| B-TOOLARGE | Task too large / coupled (executability) | Task 2 bundles scheduler + worker + renderer + admin dashboard, "Ship all four together". | general (executability) |
| B-DOMAIN | Bespoke domain-rule violation | Task 5 records deliveries via direct `db.execute("INSERT ...")` instead of the required AuditStore path. | **only with domain-context block** |

## Seeded NON-BLOCKING

| ID | Category | Where |
|----|----------|-------|
| N-OBS | Observability gap | No metrics/logging on digest job success/failure anywhere. |
| N-PERF | Minor perf | Task 5 sends one-by-one; could batch. (Low value — fine if missed.) |

## Precision probes (genuinely fine — flagging these BLOCKING = false positive)
- Task 6 (feature flag): clean.
- Task 7 (tests): reasonable coverage.

## Bonus (real but NOT seeded — neither credit nor penalty)
- Missing `digest_deliveries` table (Task 5 inserts into a table no migration creates).
- Task 8 stamping `last_digest_sent_at = now()` can drop activity between collect and send (lost-update window) / non-atomic with the send.

## Expected catch sets
- **Standard / adversarial, NO domain block:** 5 blocking expected {B-SEQ, B-ROLLBACK, B-UNDEF, B-UNDERSPEC, B-TOOLARGE}. B-DOMAIN not expected.
- **WITH domain-context block:** all 6 blocking expected (B-DOMAIN via Pass B).

## Domain-context block to use (criteria, abstract — per skill's authoring rule)
- Persistence: every database write (insert/update/delete) must go through the audit store; no direct SQL execution for writes.
- Migrations must be reversible: a destructive column drop requires a documented backfill and a down-migration.
- Every background job must emit a structured success/failure metric on completion.

## Reference baseline (2026-06-29, 5 runs: Haiku+Sonnet×3+Codex-mini)
Verdict 5/5 REVISE; B-SEQ/B-ROLLBACK/B-UNDEF/B-TOOLARGE caught as blocking in most runs;
B-UNDERSPEC often downgraded to non-blocking; **N-OBS missed by every non-domain run**;
B-DOMAIN caught only with the domain block (controlled std-vs-dom). See `../results/`.
