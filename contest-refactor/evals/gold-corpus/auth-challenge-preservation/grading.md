# Grading — auth-challenge-preservation

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## One contract

A rejection for a missing or unusable credential must carry the challenge
that tells the caller how to authenticate, and when several authenticators
are tried in order, the challenge that reaches the caller must be the
right one -- every one that was actually tried, not just one of them.

## What full credit looks like, per variant

**unchallenged-rejection (RED). Accept it as a correct, if unhelpful,
starting point.** It refuses every wrong or missing credential correctly,
for any chain length. Its gap is an omission (no challenge, ever), not a
wrong answer, and its own bundled suite documents exactly that omission
as its current behavior.

**chain-preserves-every-challenge (GREEN). Accept it outright.** Every
authenticator tried before the chain gives up contributes its own
challenge, in order. `oracles.py`'s `chained_rejection_preserves_every_challenge_count`
and `chained_rejection_challenge_values_uncorrupted` both hold.

**near-miss-last-challenge-only (NEAR_MISS). Refuse it, and refuse it for
the specific reason.** This variant does attach a challenge to every
rejection -- on a single authenticator, it is indistinguishable from
GREEN, which is exactly why its own bundled suite, which never tries more
than one authenticator at once, passes cleanly. The defect only appears
on a chain of two or more: only the most recently tried authenticator's
challenge survives, and every earlier one is silently overwritten.
`chained_rejection_preserves_every_challenge_count` fails against exactly
this variant. **The wrong reason to refuse it is "it doesn't attach a
challenge"** -- it does; the failure is specifically that a chain drops
every challenge but the last, not that no challenge exists at all. That
distinction matters: a reviewer who conflates this variant with RED has
refused it for the wrong reason.

**mutant-scheme-dropped-from-challenge (MUTANT).** A hard, unmissable
Layer-5 case: it collects the right number of challenges, in the right
order -- `chained_rejection_preserves_every_challenge_count` holds for
it, same as GREEN -- but every recorded challenge has had its scheme name
dropped. `chained_rejection_challenge_values_uncorrupted` fails against
it specifically. Even `single_authenticator_rejection_carries_its_challenge`
already fails for this variant; its corruption is not chain-specific, so
a reviewer does not need a multi-authenticator scenario to catch it, only
to check the value of the one challenge that does come back.

## Why one oracle never fails, and what the others isolate

- **`matching_credential_authenticates` is a control.** None of this
  pack's four variants ever mishandles a credential that actually
  verifies -- it authenticates identically everywhere. It would only fail
  if the fixture itself were broken in a way that made the other three
  oracles' results meaningless.
- **`single_authenticator_rejection_carries_its_challenge`** isolates RED
  and the mutant together: RED because no challenge exists at all, the
  mutant because its one challenge is already corrupted before a chain
  ever enters the picture. The near-miss passes this one -- correctly,
  since a single authenticator is exactly the case it does not get wrong.
- **`chained_rejection_preserves_every_challenge_count`** is THE
  NEAR-MISS KILLER, and isolates it precisely: the mutant keeps the right
  count (its defect is corrupted values, not a dropped entry), so this
  check alone does not also accuse the mutant.
- **`chained_rejection_challenge_values_uncorrupted`** is THE MUTANT
  KILLER, and isolates it precisely: the near-miss's one surviving
  challenge is a real, uncorrupted value -- it just isn't all of them --
  so this check alone does not also accuse the near-miss. RED's `True`
  here is declared vacuous in `oracles.py`'s own output (zero challenges,
  nothing to corrupt), not a verified pass -- RED already fails the other
  two checks, so this one carries no weight for it either way.

## Scoring guidance

- **Full credit** needs: RED accepted as a correct-but-unhelpful starting
  point; GREEN accepted outright; the near-miss refused specifically for
  dropping every-but-the-last challenge on a chain, not for lacking a
  challenge outright; the mutant's corrupted scheme named specifically,
  not just "something looks off."
- **Partial credit:** the near-miss refused on a correct instinct
  ("this loses information") without identifying that the loss is
  chain-specific and scoped to all-but-the-last; the mutant's presence of
  a challenge credited without checking whether its scheme is usable.
- **No credit / active miss:** the near-miss accepted on the strength of
  its own passing suite or a single-authenticator check; the near-miss
  and RED treated as the same failure; the mutant credited for "still
  having a challenge field populated" without inspecting its value; this
  pack's central judgment treated as settled by the parked-domain status
  noted in `provenance.json` -- the park is about how a bare-rubric miss
  here should be handled operationally, not a license to skip grading the
  pack's own contract.
