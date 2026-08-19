# Paired-arm run — handoff note

**This note is a convenience. The commits are the authority.** A resuming session reads
this, then verifies it against `git log`. Uncommitted work does not exist.

## pilot

- pairs complete: **3 / 3**
- next in frozen order: **none — complete**
- interrupted (started, no terminal record — attempt index spent): none
- exhausted (2 attempts spent, unresolved): none

## study

- pairs complete: **36 / 55**
- next in frozen order: **pair-027 (principal-consistency-boundary-restraint rep 5, attempt 1)** _(within rung 3 only)_
- interrupted (started, no terminal record — attempt index spent): none
- exhausted (2 attempts spent, unresolved): none

## Operational

- measured host concurrency: 4
- pairs-per-session cap: 8
- measured spend to date: not yet recorded

## Next action

```bash
cd contest-refactor
python3 scripts/paired_arm_run.py next --mode study --rung 3
```

Rung 3 is the active rung. Do **not** drop `--rung 3` to reach the next pending pair: the unrestricted order runs through rungs that have not been authorised, and `prereg.execution_ladder.continuation_rule` requires explicit authorisation per rung — a rung is never auto-continued and never auto-stopped.

