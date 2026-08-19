# Paired-arm run — handoff note

**This note is a convenience. The commits are the authority.** A resuming session reads
this, then verifies it against `git log`. Uncommitted work does not exist.

## pilot

- pairs complete: **3 / 3**
- next in frozen order: **none — mode complete**
- interrupted (started, no terminal record — attempt index spent): none
- exhausted (2 attempts spent, unresolved): none

## study

- pairs complete: **26 / 55**
- next in frozen order: **pair-005 (principal-abstraction-seam-flag rep 5, attempt 1)**
- interrupted (started, no terminal record — attempt index spent): ['pair-009']
- exhausted (2 attempts spent, unresolved): none

## Operational

- measured host concurrency: 4
- pairs-per-session cap: 8
- measured spend to date: not yet recorded

## Next action

```bash
cd contest-refactor
python3 scripts/paired_arm_run.py next --mode study
```
