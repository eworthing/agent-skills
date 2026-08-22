# Expected disposition — `compensating-return-restraint`

**Kind:** restraint. **Correct outcome: HOLD.** The `try?` here must NOT be raised as a
silent-swallow finding, at any severity.

## Why it holds

`lens-apple.md` § Failure modes, silent-swallow audit requires *"an inline rationale (comment,
log, or a compensating return the caller acts on)"*. All three are present, and the compensating
return is genuinely **consumed**: `LibraryViewModel.reclaimSpace()` branches on it and retries with
a tighter horizon. The rule's requirement is satisfied by its own text.

## The two over-flag routes this fixture pins

Measured 2026-08-22. The bare rubric raised this **5 of 5** before the clause shipped, and each
route has to stay closed:

1. **Rationale route** — reading `try?` as unrationalised. Closed by the canonical qualifier
   *"a compensating return the caller acts on"*, which `lens-generic.md:64` always had and
   `lens-apple.md`'s inlined copy had dropped.
2. **Telemetry route** — conceding the rationale is satisfied, then flagging anyway under the
   **adjacent** rule 4, *"Observability at adapter boundaries … Missing telemetry on user-visible
   paths is a `credibility` finding"*. Closed only by the clause's second sentence. **Restoring the
   qualifier alone left this at 5/5** — every rep pivoted to rule 4. This is why the clause is two
   sentences and not four words.

## What must still fire (the near-neighbour)

A `try?` whose compensating return **no caller consumes** is still a finding. The clause says
*"the caller branches on it"*; a `@discardableResult` return that is discarded does not qualify.
Measured 5/5 caught with the clause present, with reps excluding it using the clause's own wording.
If a future edit makes this fixture hold *and* the unconsumed case hold, the clause has become a
blind spot and must be reverted.
