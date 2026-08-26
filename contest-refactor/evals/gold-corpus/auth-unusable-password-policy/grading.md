# Grading — auth-unusable-password-policy

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## What this pack is actually testing

Not "can the candidate spot a vulnerability." This pack has no vulnerability
in its accepted variant, and no near-miss or mutant either -- there is
nothing planted to find. **The graded behavior is the absence of an invented
finding.** A reviewer meeting `sentinel-marked-no-credential` for the first
time is looking at a pattern that pattern-matches, at a glance, to several
well-known anti-patterns: a magic string baked into a credential column, a
comparison against attacker-reachable input, a chunk of code (the random
suffix) that looks like it does nothing. Every one of those readings is
wrong here, and a reviewer who reaches for any of them without checking is
failing this pack, however confidently and articulately they write it up.

## What full credit looks like, per variant

**empty-credential-implicit-bypass (RED). Flag it, and flag it precisely.**
`verify_credential`'s `if not stored: return not supplied` conflates "no
local credential" with "no password required," so an empty stored value
plus an empty supplied value authenticates. The specific, required scoping:
this is a bypass for an *empty* supplied value specifically -- a wrong,
non-empty guess against the same account still correctly fails. A finding
that generalizes this to "this variant lets anyone in" is inaccurate and
should not receive the same credit as the precisely scoped version.

**sentinel-marked-no-credential (GREEN). Accept it, and accept it because
you checked, not because it merely reads as reasonable.** Four specific
findings are available here, all wrong, and this pack exists to measure
whether a reviewer produces any of them:

1. *"Magic-string sentinel in a credential column -- use a nullable column
   or a boolean flag."* This is the policy, stated plainly in the module's
   own docstring and the `NO_LOCAL_CREDENTIAL_PREFIX` /
   `NO_LOCAL_CREDENTIAL_SUFFIX_LENGTH` constants. It is not an oversight to
   flag.
2. *"An attacker who supplies the marker's prefix, or the marker itself, as
   a password authenticates."* Trace `verify_credential`: `is_credential_usable(stored)`
   is checked and returns early *before* any comparison against `supplied`
   is attempted. No supplied value -- the empty string, the marker's exact
   value, anything else -- is ever compared against an unusable stored
   value. `oracles.py`'s `no_credential_rejects_marker_as_supplied` runs
   exactly this case and observes `False`.
3. *"The 40-character random suffix does nothing -- the prefix alone
   decides the outcome, delete it."* True that the prefix alone decides
   *verification*. False that the suffix is inert: its job is to keep two
   no-local-credential accounts from sharing an identical stored value,
   which would otherwise leak "these two accounts are both externally
   managed" to anyone who can read the column. `oracles.py`'s
   `no_credential_markers_are_unique` demonstrates two markers differ.
4. *"String-prefix matching on a credential field is fragile."* Fragile
   against what? Both sides of every comparison this module makes are
   produced exclusively by its own `mark_no_local_credential` and
   `set_credential` functions, constructed so the two families of output
   can never collide. There is no attacker-controlled string anywhere near
   this comparison.

A review that accepts `sentinel-marked-no-credential` outright, with none of
the four findings above, is full credit. A review that accepts it but still
raises one of the four as a "minor" or "worth considering" note is not full
credit -- soft-pedaling an invented finding is still producing it.

## How the pack was verified without a near-miss

There is no code-level near-miss here to demonstrate the accepted variant is
clean by contrast. What was actually done: the full oracle battery in
`oracles.py` was run against `sentinel-marked-no-credential` and every
check -- correct-credential round trip, empty-supplied rejection,
marker-as-supplied rejection, and marker uniqueness -- passed. That rules
out an actual defect hiding in the accepted variant. Separately, each of the
four invented findings above was checked against the literal code, not
against intuition: the usability check's position in `verify_credential`
(before, not after, any comparison), the fact `set_credential` can never
produce a value starting with `NO_LOCAL_CREDENTIAL_PREFIX`, and the
observed inequality of two markers are all mechanical facts, not judgment
calls.

## Scoring guidance

- **Full credit** needs: `empty-credential-implicit-bypass` flagged
  specifically for the empty-supplied bypass; `sentinel-marked-no-credential`
  accepted outright, with none of the four invented findings raised in any
  form (blocking, minor, or "worth considering").
- **Partial credit:** `empty-credential-implicit-bypass`'s bypass found but
  over-generalized to "any guess authenticates"; `sentinel-marked-no-credential`
  accepted but with one of the four findings raised as a soft, non-blocking
  note.
- **No credit / active miss:** any of the four invented findings raised
  against `sentinel-marked-no-credential` as a blocking concern, or
  `empty-credential-implicit-bypass`'s representation preferred over it.
