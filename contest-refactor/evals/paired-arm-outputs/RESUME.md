# Paired-arm run — handoff note

**This note is a convenience. The commits are the authority.** A resuming session reads
this, then verifies it against `git log`. Uncommitted work does not exist.

## pilot

- pairs complete: **2 / 3**
- next in frozen order: **pilot-003 (principal-abstraction-seam-restraint rep 1, attempt 2)**
- interrupted (started, no terminal record — attempt index spent): ['pilot-003']
- exhausted (2 attempts spent, unresolved): none

## study

- pairs complete: **0 / 55**
- next in frozen order: **pair-001 (crossplat-flag rep 5, attempt 1)**
- interrupted (started, no terminal record — attempt index spent): none
- exhausted (2 attempts spent, unresolved): none

## Operational

- measured host concurrency: 4
- pairs-per-session cap: 8
- measured spend to date: not yet recorded

## Next action

```bash
cd contest-refactor
python3 scripts/paired_arm_run.py next --mode pilot
```
