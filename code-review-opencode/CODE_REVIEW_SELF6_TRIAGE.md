# code-review-opencode — Self-review 6 — aborted run and provider-saturation fix

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-11.

Result: **aborted at ~22 minutes** — all 8 finders went silent together after
~20 minutes of work. The stall watchdog interrupted six of them; each retry
prompted the already-interrupted session and stalled for another full window.
No report artifact was written, so the run cannot be judged against the
stopping rule.

## Evidence

- All 8 finders were created within a few milliseconds of each other.
- `time.updated` for each child stopped changing at roughly the same wall-clock
  time, then the watchdog fired 180s later.
- The retries hit the same silence, so the cascade was watchdog → interrupt →
  retry same session → watchdog.
- A tiny max-effort probe after the abort returned in ~1.2s, so the provider
  itself was healthy; the failure was load/queueing, not an outage.
- Run 5 showed the same pattern at a smaller scale: two finders stalled, and
  three more ended with empty structured output.

## Root causes

1. **Eight concurrent max-effort children saturated the provider.** The engine
   launched every finder at once, and each finder carries the full diff
   (~250k input tokens in this repository). The children did not fail; they
   stopped receiving provider responses.
2. **`time.updated` is turn-level, not token-level.** A max-effort final answer
   can legitimately be silent for minutes, so 180s is too short for a healthy
   child.
3. **A watchdog interrupt was retried as if it were a schema failure.**
   Prompting an interrupted session again repeats the full stall window instead
   of recovering.
4. **The 30-step finder budget is too small for DeepSeek.** OpenCode injects
   `CRITICAL - MAXIMUM STEPS REACHED ... Respond with text only` on the final
   step. The finder then writes a prose summary, and the retry prompt is
   ignored because the CRITICAL message remains in the same session's context.
   This is the cause of the empty structured responses in runs 5–7, not just
   provider load.

## Fixes

- **Concurrency default 4** (`--concurrency 8` restores the reference fan-out;
  `CODE_REVIEW_CONCURRENCY` still overrides). The engine gate is shared by all
  roles, so this halves provider load in every phase.
- **Stall default 600s** (`CODE_REVIEW_STALL_MS`; `0` disables). Still a
  no-activity watchdog, not a wall-clock cap.
- **No retry after a stall.** `waitForChild` now returns `idle` / `stalled` /
  `gone`; a stalled child is recorded as a failed finder and the engine marks
  the run partial, rather than spending another 10 minutes on the same session.
- **Finder/sweep `steps` 30 → 60.** The verifier/synth budget stays 20. This is
  a documented DeepSeek adaptation; the reference `maxTurns` is 20.
- **Step-limit recovery.** A retry on a step-limited session is ignored because
  OpenCode keeps the `MAXIMUM STEPS REACHED` message in context. The runner now
  detects that message and creates a fresh formatter child that converts the
  previous summary into the schema, without re-reading the diff. The strict
  tool boundary is unchanged.
- **Regression tests:** the silent-child test now asserts one prompt only; the
  concurrency resolver tests cover the new default.

## Next run

Rerun `max --max-findings all --fix` with the new defaults. The stopping rule is
unchanged: complete run, fewer than 10 findings, no high/medium severity.
