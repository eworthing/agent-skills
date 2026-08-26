# Grading — auth-empty-password-policy-restraint

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## What this pack is actually testing

Not "can the candidate spot a vulnerability." The accepted variant here has
no vulnerability, and this pack has no near-miss and no mutant -- there is
nothing planted to find. **The graded behavior is the absence of an
invented finding.** A reviewer meeting `authenticator-owned-empty-
acceptance` for the first time is looking at an account that authenticates
on an empty password, which is exactly the shape of thing security
instinct is trained to flag on sight. That instinct is wrong here, and a
reviewer who reaches for "vulnerability," "bypass," or "missing
validation" without checking what the code actually does and for whom is
failing this pack, however confidently they write it up.

## What full credit looks like, per variant

**universal-empty-rejection (RED). Flag it, and flag it as the regression
it is.** `authenticate` rejects any empty supplied password before ever
consulting `storedPasswords`. This reads like a reasonable hardening pass
-- reject the class of guess that looks like it should never work -- and it
silently breaks the one account the accepted policy exists to serve: an
account whose own stored password is deliberately empty. The precise
framing that matters: this is not just "a wrong outcome for one account,"
it is a *relocation* of a decision. The accepted variant lets each
account's own stored password decide whether an empty guess matches;
this variant decides the same question once, for every account, ahead of
any per-account policy at all. A finding that names only "kiosk can't log
in anymore" without naming why -- the check moved to a place that has no
notion of which accounts the policy applies to -- is missing half the
point.

**authenticator-owned-empty-acceptance (GREEN). Accept it, and accept it
because you checked, not because it merely reads as reasonable.** Three
specific, wrong findings are available here, and this pack exists to
measure whether a reviewer produces any of them:

1. *"An account that authenticates on an empty password is a bypass."* It
   is an equality comparison against that one account's own stored
   password, which happens to be empty by design. `kiosk_empty_password_
   authenticates` confirms it succeeds only because the stored value
   matches, not because emptiness is treated as a wildcard.
2. *"This needs a minimum-length or non-empty-password check."* That
   check is universal-empty-rejection's own approach, and it is the
   regression this pack is built around, not a fix.
3. *"No credential supplied and an empty password supplied are the same
   case."* They are not, in either variant: `ordinary_account_and_
   missing_credential_behavior` confirms a missing credential is rejected
   unconditionally, in both variants, regardless of any account's stored
   password -- collapsing the two cases misdescribes what the code
   actually checks.

A review that accepts `authenticator-owned-empty-acceptance` outright, with
none of the three findings above, is full credit. A review that accepts it
but still raises one of the three as a "minor" or "worth considering" note
is not full credit -- soft-pedaling an invented finding is still producing
it.

## Oracle taxonomy

- **`ordinary_account_and_missing_credential_behavior` is a control.**
  Holds in both variants, deliberately: universal-empty-rejection's one
  behavioral difference from the accepted variant is scoped exactly to an
  empty *supplied* password, and touches neither an ordinary non-empty
  password nor a missing credential.
- **`kiosk_empty_password_authenticates` is the pack's one discriminator.**
  It is also, functionally, the pack's whole behavior contract in one
  check: the one fact that separates the regression from the accepted
  policy.

## A note on where this judgment sits

This pack's central call -- accept an account that authenticates on an
empty password, reject a blanket rule that closes it -- sits inside
territory this project has deliberately parked on class evidence rather
than direct measurement (fail-open posture, and where an authorization
decision is allowed to live). A candidate that inflates
`authenticator-owned-empty-acceptance` into a vulnerability, or prefers
`universal-empty-rejection`'s hardening, is producing exactly the kind of
miss that park was built to anticipate and catch when it shows up in a
concrete fixture -- it is a recorded, reversible trigger, not new evidence
that the parked posture itself needs to change.

## Scoring guidance

- **Full credit** needs: `universal-empty-rejection` flagged as a
  regression that relocates a per-account decision into a blanket
  pre-check, not merely "this breaks kiosk"; `authenticator-owned-empty-
  acceptance` accepted outright, with none of the three invented findings
  raised in any form (blocking, minor, or "worth considering").
- **Partial credit:** `universal-empty-rejection`'s regression found but
  described only as "kiosk can't log in" without naming the relocated-
  decision framing; `authenticator-owned-empty-acceptance` accepted but
  with one of the three findings raised as a soft, non-blocking note.
- **No credit / active miss:** any of the three invented findings raised
  against `authenticator-owned-empty-acceptance` as a blocking concern, or
  `universal-empty-rejection`'s blanket rejection preferred over it as a
  hardening improvement.
