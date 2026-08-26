# Grading — auth-identity-probe-equalization

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## What this pack is actually testing

Not "can the candidate find a timing side channel." This pack's real-world
basis already extracted that mitigation into a named function whose own
docstring states the attack it prevents. **The test is whether a reviewer
who reads a correct, well-documented helper checks whether every caller
that needs it actually reaches it, or stops at "the helper is correct" and
calls it done.** `near-miss-guard-skips-equalization` is built specifically
so that reading the helper in isolation gives a clean, correct, confident
answer -- and that answer is wrong for the variant as a whole.

## What full credit looks like, per variant

**dual-entry-inconsistent-equalization (RED). Flag it, and flag it as a
cost asymmetry, not a false grant.** `sign_in` performs one unit of
equivalent work when an identity does not resolve to any account;
`reverify_for_sensitive_action` returns immediately in the same situation.
Both correctly refuse the unknown identity -- **this is not a bug that
authenticates anyone.** The finding is that verification cost differs
between the two entry points depending on whether the identity exists,
which is exactly the signal a probe uses to enumerate identities, and it
is present on only one of the two paths. A finding that describes this as
"an authentication bypass" has mischaracterized it.

**unified-equalized-verification (GREEN). Accept it outright.**
`verify_with_equalized_work` is extracted once, documented with what it
defends against, and both `sign_in` and `reverify_for_sensitive_action`
route through it uniformly. There is nothing further to ask of this
variant, and the docstring stating the defended attack is not a reason to
raise concern -- the real-world function this pack is modeled on does
exactly that, in the accepted, shipping source.

**near-miss-guard-skips-equalization (NEAR_MISS). Refuse it, and refuse it
for the call-site defect, not a helper defect.** The specific, required
reasoning: `verify_with_equalized_work` is byte-for-byte the same correct
helper as the accepted variant's. The defect is that both `sign_in` and
`reverify_for_sensitive_action` add `if account is None: return False`
*before* calling it, so the helper is dead code on precisely the path it
exists to protect. **The wrong reason to refuse this variant is "an
early-return guard is generally risky."** The right reason names the
specific mechanism: a guard that looks like a free performance
optimization ("no account, nothing to compare, why do the work") sits in
front of the one call the whole mitigation depends on, and defeats it
completely for every unknown identity. A reviewer who inspects only the
helper, finds it correct, and moves on has done half the review -- the
half that was never broken.

**mutant-unknown-identity-verifies (MUTANT).** This one is primarily a
Layer-5 execution/hidden-oracle case, not a reviewer-judgment one, and it
is a much louder bug than the near-miss: `verify_with_equalized_work`
still performs the equalizing work, then returns `True` instead of `False`
for an unresolved identity, so any nonexistent identity authenticates with
any supplied credential at all. What the pack requires is that the hidden
oracle `unknown_identity_never_authenticates` fails against it -- see
`oracles.py`. A static read that catches the flipped return value by
inspection is bonus credit, not required credit.

## Why a work counter, not wall-clock timing

`_hash_work` increments a module-level integer counter instead of doing
any real hashing or sleeping. The real-world channel this models is
elapsed time -- an actual timing attack measures wall-clock milliseconds,
not an internal counter. A counter is used here because it is exact,
instant, and identical on every machine: `equalization_work_matches`
either observes two equal integers or it doesn't, with no tolerance,
retries, or flakiness. A reviewer should understand the oracle as a
deterministic proxy for a real side channel, not mistake the counter
itself for the vulnerability.

## Scoring guidance

- **Full credit** needs: dual-entry-inconsistent-equalization flagged
  specifically as a per-path cost asymmetry (not a false grant);
  unified-equalized-verification accepted outright; near-miss-guard-skips-
  equalization refused specifically for the call-site guard bypassing a
  correct helper (not vague suspicion of early returns in general).
- **Partial credit:** dual-entry-inconsistent-equalization's asymmetry
  found but mischaracterized as authenticating an unknown identity;
  near-miss-guard-skips-equalization refused for the right instinct but
  without naming that the helper itself is correct and the defect is at
  the call site.
- **No credit / active miss:** near-miss-guard-skips-equalization accepted
  because its helper reads correctly, or because its own bundled tests
  pass; unified-equalized-verification rejected for documenting the
  mitigation it implements.
- mutant-unknown-identity-verifies is graded by the hidden oracle
  (`unknown_identity_never_authenticates`), not by reviewer narrative; do
  not penalize a candidate for missing it in a static read unless they
  also assert with confidence that an unresolved identity can never
  authenticate here.
