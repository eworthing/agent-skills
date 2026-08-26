# Grading — auth-session-carryover

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm signing in rotates the session token."
Confirming that is real work, and it's the easy half. **The real test is
whether the candidate checks a second, independent contract that looks
identical to the first in every common scenario.** Rotating a token and
discarding a session are two different operations that happen to agree in
almost every case a naive test suite would cover -- they only diverge when
a session changes hands between principals, or when a principal's
credentials change out from under an existing session. A Critic who tests
only the common cases sees two indistinguishable, equally simple
implementations and has no reason to prefer one.

## What full credit looks like, per variant

**no-rekey-sign-in (RED).** Accept it. It is not a defect state -- it is a
correct, if naive, starting point: it records the incoming principal's
identity and credential stamp and touches nothing else. Noting that this
leaves the session token fixed (a fixation risk) and lets data carry across
principals is fair, motivating context; it is not a required finding, since
that is exactly what rekey-or-discard-sign-in then fixes.

**rekey-or-discard-sign-in (GREEN). Accept it without reservation.** The
specific, required reasoning: (1) verify, don't assume, that a session with
no prior principal retains its data across a first sign-in -- this is a
documented, deliberate contract, not a side effect; (2) verify that a
session changing principals, or the same principal's credential stamp no
longer matching, results in the session being discarded, not merely
re-keyed. Both directions need to be checked independently; checking only
one cannot distinguish this variant from near-miss-always-rekey.

**near-miss-always-rekey (NEAR_MISS). Refuse it, and refuse it on the right
grounds.** This is the pack's centerpiece alongside rekey-or-discard-sign-in.
Always rotating the token is a genuine, correct fix for session fixation,
and it genuinely does preserve the anonymous-retention contract -- a
candidate who tests only those two properties will find nothing wrong. **The
wrong reason to refuse this variant is "it doesn't have a discard branch,
that seems risky" found by structural pattern-matching alone.** The right
reason names what specifically breaks: rotating a token never clears a
session's data, so signing in as a second principal (or the same principal
after a credential change) over an existing session carries the first
principal's data forward, silently, with nothing raising.

**mutant-identity-only-check (MUTANT).** This one is primarily a Layer-5
execution/hidden-oracle case, not a reviewer-judgment one. Structurally it
is almost identical to rekey-or-discard-sign-in -- same first-sign-in
rotation, same different-principal discard -- with the credential-stamp
half of the discard condition removed. For any scenario that doesn't
involve the same principal's credentials changing, this is invisible. What
the pack requires is that the hidden oracle
`credential_change_invalidates_session` fails against it -- see
`oracles.py`. A review pass that constructs exactly that scenario and
notices the miss is bonus credit, not required credit.

**mutant-always-discard (MUTANT).** The mirror image of near-miss-always-rekey,
also a Layer-5 execution case. It discards the session on every sign-in,
unconditionally -- no condition at all, which looks, if anything, *more*
careful than rekey-or-discard-sign-in: it trivially defeats fixation and
trivially prevents any cross-principal or stale-credential carryover. What
it breaks is the other contract: discarding unconditionally also clears an
anonymous session's data on a principal's very first sign-in, which the
pack requires be retained. What the pack requires is that the hidden
oracle `anonymous_data_is_retained_on_first_sign_in` fails against it --
see `oracles.py`. Do not credit this variant for looking more secure; that
is exactly the instinct `must_not_find` is guarding against.

## The core lesson: two operations that agree in the common case are still two operations

A token rotation and a full discard produce the same *token* behavior in
every scenario near-miss-always-rekey's own test suite covers, and the same
*data* behavior in every scenario except the one that matters. Telling
"passes every test I wrote" apart from "preserves every contract the
original made" is the pack's actual content. The real-world case this pack
is modeled on is Django's own session-fixation handling, which chooses
between exactly these two operations based on a two-part condition
(identity and credential-hash); collapsing that choice to "always rotate"
is a plausible, well-intentioned simplification that a credential-rotation
or principal-switch scenario -- not covered by casual testing -- is the
only thing that exposes.

## Scoring guidance

- **Full credit** needs: rekey-or-discard-sign-in accepted with both the
  retention contract and the discard contract verified independently (not
  assumed from one direction); near-miss-always-rekey refused specifically
  for carrying data across a principal or credential change (not vague
  "missing a branch" reasoning); no-rekey-sign-in accepted as a correct, if
  naive, starting state.
- **Partial credit:** rekey-or-discard-sign-in accepted but only one
  direction (retention or discard) actually verified; near-miss-always-rekey
  refused for the right instinct but without naming which specific scenario
  (cross-principal, or same-principal-changed-credentials) leaks data.
- **No credit / active miss:** near-miss-always-rekey accepted or preferred
  over rekey-or-discard-sign-in for "uniformly defeating fixation";
  rekey-or-discard-sign-in rejected or flagged for discarding on every
  sign-in "to be safe," which would break the retention contract in the
  opposite direction.
- mutant-identity-only-check and mutant-always-discard are both graded by
  hidden oracles (`credential_change_invalidates_session` and
  `anonymous_data_is_retained_on_first_sign_in`, respectively), not by
  reviewer narrative; do not penalize a candidate for missing either in a
  static read unless they also assert with confidence that the relevant
  contract holds without constructing the scenario that would test it.
