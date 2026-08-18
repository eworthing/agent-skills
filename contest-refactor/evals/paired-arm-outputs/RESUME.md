# Paired-arm run — handoff note

**This note is a convenience. The commits are the authority.** A resuming session reads
this, then verifies it against `git log`. Uncommitted work does not exist.

## pilot

- pairs complete: **0 / 2**
- next in frozen order: **pilot-001 (principal-duplicated-rule-restraint rep 1, attempt 2)**
- interrupted (started, no terminal record — attempt index spent): ['pilot-001']
- exhausted (2 attempts spent, unresolved): none

## study

- pairs complete: **0 / 55**
- next in frozen order: **pair-001 (crossplat-flag rep 5, attempt 1)**
- interrupted (started, no terminal record — attempt index spent): none
- exhausted (2 attempts spent, unresolved): none

## Operational

- measured host concurrency: None
- pairs-per-session cap: not yet derived
- measured spend to date: not yet recorded

## Next action

```bash
cd contest-refactor
python3 scripts/paired_arm_run.py next --mode pilot
```
