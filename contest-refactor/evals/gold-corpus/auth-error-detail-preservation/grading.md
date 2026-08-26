# Grading — auth-error-detail-preservation

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## One contract

All four pieces of an error -- a human-readable reason, a challenge, a
stable machine identifier, and the source location where it was raised --
must survive a middleware that catches and rethrows.

## What full credit looks like, per variant

**generic-error-on-catch (RED). Flag it, unconditionally.**
`withErrorMiddleware` catches whatever the guarded operation raises and
rethrows a fresh, generic error in its place. All four fields are lost,
every time, regardless of what failed. Its own bundled suite documents
this: the failure path never sees anything conforming to `RethrownDetail`.

**middleware-forwards-original-failure (GREEN). Accept it outright.** It
rethrows the exact same failure value it caught. All four fields survive
unchanged; every oracle in this pack holds for it.

**near-miss-reason-and-challenge-only (NEAR_MISS). Refuse it, and refuse
it for the specific reason.** The required reasoning: the reason and the
challenge -- the two pieces a human reads directly in an error message --
survive intact. The identifier and the source location do not; they are
silently dropped. `identifier_is_present` and `source_location_matches_original`
both fail against exactly this variant. **The trap is real**: this
variant's own bundled suite never asserts anything about the identifier
or the source location, so a reviewer who runs the suite and reads the
error message sees nothing wrong. Full credit requires naming that the
two dropped fields are specifically the ones a downstream handler or a
log aggregator would key on, not just "some fields are missing."

**mutant-identifier-from-wrapper (MUTANT).** A hard, unmissable Layer-5
case: all four fields are present and non-empty, and reason, challenge,
and source location all correctly match the original. Only the identifier
is wrong -- populated from the middleware's own wrapper label
("middleware.auth-failure-caught") instead of the original failure's
identifier. `identifier_matches_original` fails against it while
`identifier_is_present` still holds, which is exactly the signature of
"present but wrong" rather than "missing." A reviewer who checks only
that an identifier exists, without checking it traces back to the
original failure, will accept this variant by mistake.

## Why one oracle never fails, and what the others isolate

- **`operation_succeeds_without_raising` is a control.** None of this
  pack's four variants touches the non-failing path -- a successful
  operation's result passes through identically everywhere. It would only
  fail if the fixture itself were broken in a way that made the other
  checks' results meaningless.
- **`reason_and_challenge_survive`** isolates RED alone: it is the only
  variant that loses the two fields a human-readable error message is
  built from.
- **`identifier_matches_original`** fails for RED, the near-miss, and the
  mutant, for three different reasons -- missing entirely (RED and the
  near-miss) or present but wrong (the mutant). It is a strict check, not
  a discriminator on its own.
- **`identifier_is_present`** is THE NEAR-MISS-VS-MUTANT DISCRIMINATOR.
  Combined with `identifier_matches_original`: RED and the near-miss fail
  both (the identifier is simply absent); the mutant fails only the
  strict match (an identifier is there, it is just the wrong one). A
  reviewer's writeup should make exactly this distinction, not treat
  "identifier wrong" as one undifferentiated failure class.
- **`source_location_matches_original`** isolates the near-miss (and
  RED) from the mutant: the mutant's only corruption is the identifier,
  so its source location is correct and this check holds for it, same as
  GREEN.

## Scoring guidance

- **Full credit** needs: RED flagged unconditionally; GREEN accepted
  outright; the near-miss refused with both dropped fields (identifier
  AND source location) named specifically, not just "the message looks
  fine but something's missing"; the mutant's identifier named as
  present-but-wrong, distinguished explicitly from the near-miss's
  present-but-absent.
- **Partial credit:** the near-miss refused on a correct instinct
  ("more than the message matters here") without naming both dropped
  fields; the mutant flagged for "the identifier looks off" without
  identifying that the mechanism is wrapper-substitution, or without
  distinguishing it from the near-miss's outright omission.
- **No credit / active miss:** the near-miss accepted because its error
  message reads correctly; the mutant accepted because all four fields
  are structurally present; the near-miss and the mutant treated as the
  same failure ("identifier's wrong in both"); this pack's central
  judgment treated as settled by the parked-domain status noted in
  `provenance.json` -- the park is about how a bare-rubric miss here
  should be handled operationally, not a license to skip grading the
  pack's own contract.
