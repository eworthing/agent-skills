# Grading — auth-login-redirect-target

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm the return target still points at the right
page." Confirming that is real work, and it's the easy half. **The real
test is two separate restraint calls in the same function: an asymmetric
rule that looks like it should be tidied into one behavior, and a stapled
attribute pair that looks unused because its reader lives in a different
file.** Both invite a natural "clean this up" instinct, and both are wrong
to act on here.

## What full credit looks like, per variant

**bare-relative-target (RED).** Accept it. It is not a defect state -- it
is a correct, if lossy, starting point: it always returns the bare request
path, dropping the query string and never looking at the sign-in endpoint's
own host at all. Noting that this loses in-page state and would misdirect a
cross-host sign-in deployment is fair, motivating context; it is not a
required finding, since that is exactly what scoped-absolute-target then
fixes.

**scoped-absolute-target (GREEN). Accept it, and do not ask it to collapse
the same-host/cross-host split, or to delete the stapled attributes.** The
specific, required reasoning: (1) verify, don't assume, that a hostless or
same-host sign-in endpoint gets a relative target with its query string
intact, *and* that a cross-host sign-in endpoint gets the full absolute
target -- checking one direction does not confirm the other; (2) recognize
that `entry_url`/`return_param_name` being unread inside `gate.py` itself is
not evidence they are dead -- `gate_scan.py`, in the same pack, is the
reader. **A candidate who proposes deleting the staple because "nothing in
this function uses it" has failed this pack's central test**, even if every
other observation they make is accurate, because the consumer was one file
away and available to check.

**near-miss-always-relative (NEAR_MISS). Refuse it, and refuse it on the
right grounds.** This is the pack's centerpiece alongside
scoped-absolute-target: correctly preserving the query string reads as a
strict improvement over bare-relative-target, and in a same-host deployment
-- which is what any test suite run against a single local server models by
default -- it is indistinguishable from scoped-absolute-target. **The wrong
reason to refuse this variant is "it's always relative, that seems
incomplete" found by pattern alone.** The right reason names the specific
deployment shape where it breaks: a sign-in endpoint on a different host
gets a bare relative return target back, which resolves against the
sign-in host rather than the application host the principal actually came
from -- and nothing about a same-host test run can surface that.

**mutant-trusts-forwarded-host (MUTANT).** This one is primarily a Layer-5
execution/hidden-oracle case, not a reviewer-judgment one. Structurally it
is almost identical to scoped-absolute-target -- same downgrade logic, same
default -- with "the current URL" built from a client-claimed
forwarded-host value instead of the request's own verified host. For any
ordinary request that never sets a forwarded-host claim, this is invisible.
What the pack requires is that the hidden oracle
`spoofed_forwarded_host_never_leaks_into_target` fails against it -- see
`oracles.py`. A review pass that constructs a forged forwarded-host request
and notices the leak is bonus credit, not required credit.

**mutant-unstapled-view (MUTANT).** The second, independent Layer-5 case --
it tests the restraint axis, not the redirect-target axis. Its `request.py`
and `redirect_target.py` are byte-identical to scoped-absolute-target;
`gate.py` simply never staples `entry_url`/`return_param_name` onto the
wrapped view. Every redirect it produces is correct. What the pack requires
is that the hidden oracle `entry_endpoint_reflectable_without_reparsing`
fails against it -- see `oracles.py`: `gate_scan.entry_endpoint_for` and
`return_param_name_for` come back `None` instead of the values the
decorator was actually called with. This is what makes the restraint case
in scoped-absolute-target more than an assertion: the consumer really does
break when the staple is removed, in this same pack, not just in a claim
about Django's middleware.

## The core lesson: an asymmetric rule is not automatically an inconsistency, and "unread here" is not "unread"

`scoped-absolute-target`'s same-host-relative / cross-host-absolute split
looks, on a quick read, like it should pick one behavior and keep it. It
can't, without breaking one deployment shape or leaking the calling host
into the other. Its stapled attributes look, on an even quicker read, like
dead weight, because the one file being reviewed never reads them. The
real-world case this pack is modeled on is Django's own login-redirect
handling, which makes exactly this asymmetric choice and staples exactly
this metadata for a middleware that lives in a different module entirely.
A grading pass that rewards "simplifying" either shape without checking the
deployment consequence or the other file has failed to apply this pack's
core lesson.

## Scoring guidance

- **Full credit** needs: scoped-absolute-target accepted with both the
  same-host and cross-host directions verified, and the stapled attributes
  recognized as consumed elsewhere rather than proposed for deletion;
  near-miss-always-relative refused specifically for the cross-host case
  (not vague "always relative seems incomplete" reasoning); bare-relative-target
  accepted as a correct, if lossy, starting state.
- **Partial credit:** scoped-absolute-target accepted but only one
  direction of the host comparison actually verified, or the staple flagged
  as a soft concern without a deletion recommendation; near-miss-always-relative
  refused for the right instinct but without naming the cross-host scenario
  specifically.
- **No credit / active miss:** scoped-absolute-target flagged for deleting
  the stapled attributes, or for collapsing the host-scoped split to one
  behavior; near-miss-always-relative accepted or preferred over
  scoped-absolute-target for "consistently relative."
- mutant-trusts-forwarded-host and mutant-unstapled-view are both graded by
  hidden oracles (`spoofed_forwarded_host_never_leaks_into_target` and
  `entry_endpoint_reflectable_without_reparsing`, respectively), not by
  reviewer narrative; do not penalize a candidate for missing either in a
  static read unless they also assert with confidence that the relevant
  property holds without constructing the scenario that would test it.
