# Implementation Plan: Weekly Email Digest

Goal: send each opted-in user a weekly email summarizing their account activity.
Stack: Python 3.11 service, Postgres, existing `mailer` module, existing Celery worker pool.

## Task 1 — Build the digest collector
Add `DigestService.collect_unsent(user)` in `services/digest.py`. It queries activity
since the user's `last_digest_sent_at` timestamp and returns a list of activity rows.
Reads `users.last_digest_sent_at` and filters `ActivityLog` to rows newer than it.

## Task 2 — Wire the scheduler, queue worker, template renderer, and admin dashboard
Implement the periodic scheduler that fans out one job per opted-in user, the Celery
worker that processes each job, the HTML/text template renderer, and an admin dashboard
page showing per-user digest status and a "resend" button. Ship all four together.

## Task 3 — Enqueue jobs from the scheduler
In the scheduler from Task 2, call `enqueue_digest_job(user_id)` for every user with
`digest_opt_in = true`. The job is picked up by a `DigestScheduler` instance in the
worker.

## Task 4 — Add digest columns
Add a migration creating `users.digest_opt_in boolean default false` and
`users.last_digest_sent_at timestamp null`. Derive each user's `digest_opt_in` from the
legacy `users.newsletter_flag` column, then drop `newsletter_flag` in the same migration.

## Task 5 — Send the digest
For each collected digest, render the template and send via `mailer.send()`. Record a
delivery row by calling `db.execute("INSERT INTO digest_deliveries (...) VALUES (...)")`
directly after each send. Add appropriate error handling and retries to the send step.

## Task 6 — Add the feature flag
Gate the whole feature behind a `WEEKLY_DIGEST_ENABLED` config flag, defaulting to false.
Read it once at scheduler startup; if false, the scheduler registers no periodic task.

## Task 7 — Tests
Add unit tests for `DigestService.collect_unsent` covering: a user with new activity, a
user with none, and a user whose `last_digest_sent_at` is null (treat as "all activity").
Mock `ActivityLog` and assert the returned row set.

## Task 8 — Update last_digest_sent_at
After a digest is successfully sent in Task 5, set `users.last_digest_sent_at = now()` for
that user so the next run does not re-send the same activity.
