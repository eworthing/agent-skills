# Grading — auth-concurrent-login-storage

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## Why this is a scripted interleaving, not real concurrency

The real test this pack is drawn from runs 1000 iterations of genuinely
concurrent tasks, each logging in one type against a shared cache, because
the real race is narrow -- its own comment records losing roughly one pair
in ten against a previous storage design. That loss rate is exactly why
the real suite needs a stress loop: any single run might not reproduce it.
A graded fixture cannot depend on a race window reproducing at some
undetermined iteration on arbitrary grading hardware, so this pack models
the same lost-update mechanism as a deterministic, scripted interleaving
instead. Storing a login is decomposed into two explicit steps --
`beginStore`, which captures whatever a caller needs before conceptually
yielding control, and `commitStore`, which performs the actual write once
resumed -- and `oracles.py` drives a fixed, named order of those steps for
two callers. There is no task, no timer, no iteration count anywhere in
this pack; the lost update either happens on this exact script or it
doesn't, every time.

## What full credit looks like, per variant

**unsynchronized-shared-map (RED). Flag it, and flag it precisely.**
`commitStore` computes its write from a snapshot of storage taken back
when `beginStore` ran. If a second caller's own `beginStore` /
`commitStore` pair completes entirely in between, the first caller's
eventual commit overwrites storage using data that no longer reflects the
second caller's write -- not merged with it, gone. The precise scope: this
requires the two callers' *steps* to interleave. Either caller acting
alone, or one fully finishing (both its own begin and commit) before the
other starts, is completely correct in this same variant --
`both_kinds_retrievable_without_interleaving` confirms it directly.

**atomic-commit-per-login (GREEN). Accept it outright.** Its `commitStore`
captures nothing at `beginStore` time and performs the entire
read-modify-write in one non-decomposed call. Because nothing else can run
"in between" a single Swift function call in this synchronous model, no
interleaving of two callers' steps has anywhere to land. This is
demonstrated, not asserted: `both_kinds_retrievable_under_scripted_
interleaving` runs the exact script that breaks RED and the near-miss
against this variant and it holds.

**per-kind-lock-shared-map-race (NEAR_MISS). Refuse it, and refuse it for
the specific granularity mismatch, not a generic "needs more locking"
complaint.** This is the pack's centerpiece. Its lock is not theater: `Lock`
genuinely traps if reacquired while held, and it genuinely prevents the
same login kind from being stored twice concurrently. The defect is what
it does *not* protect: two different login kinds acquire two different
lock objects, and the race this pack is built around is a cross-kind
race -- caller A stores `.primary`, caller B stores `.secondary`, and they
were never going to contend on the same lock in the first place. The
underlying shared map is exactly as unprotected against that specific
interleaving as it is in RED, and the observed result is identical:
`both_kinds_retrievable_under_scripted_interleaving` fails against this
variant exactly as it fails against RED, for the same read-modify-write
reason, dressed in real synchronization code that never engages the actual
race. A reviewer who checks "is there a lock" and stops has verified
something true and irrelevant.

**mutant-misrouted-storage-key (MUTANT).** This one is a hard, unmissable
Layer-5 case, not a reviewer-judgment one: its write is exactly as
indivisible as GREEN's -- no interleaving-dependent bug exists here at
all -- but `storageKey(for:)` silently maps `.secondary` to `.primary`'s
own slot. `both_kinds_retrievable_without_interleaving` fails against it
even with no interleaving whatsoever, which is what marks this as a
different class of bug than the near-miss's: the near-miss passes that
same check cleanly (its defect needs the interleaved script to show up at
all), while the mutant fails the boring, sequential version too.

## Oracle taxonomy

- **`ordinary_login_round_trips` is a control.** A single caller, one
  kind, no interleaving. Holds in every variant, deliberately -- none of
  this pack's three defects touch an uninterrupted single store.
- **`both_kinds_retrievable_without_interleaving` is a discriminator aimed
  at the mutant.** RED and the near-miss both pass it cleanly, honestly --
  their defects are genuinely interleaving-dependent, and a purely
  sequential two-kind store never gives either variant's stale-snapshot
  logic anything stale to read. Only the mutant's unconditional wrong-key
  routing fails it.
- **`both_kinds_retrievable_under_scripted_interleaving` is a
  discriminator aimed at RED and the near-miss, and it also (honestly, not
  by design) catches the mutant.** The mutant's failure here has nothing
  to do with interleaving -- it fails this script for the same unconditional
  reason it fails the non-interleaved one. Its presence in this oracle's
  failing set is not evidence of a race in the mutant; it is evidence that
  wrong-key routing fails everything, interleaved or not.

## Scoring guidance

- **Full credit** needs: RED's bypass scoped to the specific interleaving
  (not "every store loses data"); the near-miss refused specifically for
  locking the wrong thing (not "needs more synchronization" or "the lock
  looks fine to me"); GREEN accepted outright.
- **Partial credit:** the near-miss refused only on a vague "concurrency is
  hard, I don't trust this" basis, without naming that its lock is scoped
  per kind while the race is cross-kind; or RED's bug over-generalized to
  every store rather than scoped to the interleaved case.
- **No credit / active miss:** the near-miss accepted because it visibly
  acquires and releases locks; RED's or the near-miss's defect conflated
  with the mutant's (they are a race and a deterministic bug,
  respectively, and require different fixes).
- mutant-misrouted-storage-key is graded by the hidden oracle
  (`both_kinds_retrievable_without_interleaving`), not by reviewer
  narrative; do not penalize a candidate for missing it in a static read
  unless they also assert with confidence that both kinds route to their
  own storage correctly.
