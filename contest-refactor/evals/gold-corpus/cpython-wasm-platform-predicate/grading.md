# Grading — cpython-wasm-platform-predicate

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm a rename didn't change behavior." Confirming
that is real work, and it's the easy half. **The real test is what the
candidate does with everything shared-flag left alone.** A Critic that has
just watched a refactor introduce a shared predicate for two platforms will
have a strong, well-earned reflex: "if these two platforms are the same
family, why does half the file still spell them out individually?" Applied
to shared-flag, that reflex is wrong on both surviving shapes -- the
single-platform guards and the two-reason pairs -- for two different
reasons, and telling those two reasons apart is the pack's actual content.

## What full credit looks like, per variant

**scattered-disjunction (RED).** Accept it. It is not a defect state -- it
is a correct, if repetitive, starting point: every site that needs "either
sandboxed platform" spells out the two-term disjunction inline, including
the three that are genuinely shared. Noting the repetition as a candidate
for a shared predicate is fair, minor feedback; it is not a required
finding, since that is exactly what shared-flag then does.

**shared-flag (GREEN). Accept it, and do not ask it to go further.** The
specific, required reasoning: (1) verify, don't assume, that the three
consolidated sites (`test_shared_temp_writable`, `test_process_fork`,
`test_large_page_alloc`) really do apply identically on both platforms --
they do, `CHANGES.md` says so and the skip sets bear it out; (2) recognize
that the five untouched sites split into two different kinds of duplication
that the new predicate cannot absorb without changing behavior: three
single-platform guards (two tideline-only, one gearshift-only) where the
*other* platform genuinely does not have the limitation, and two tests each
carrying one guard per platform, which already skip on both platforms today
but for stated, different reasons. **A candidate who flags either kind of
surviving duplication as incompleteness, or proposes finishing the job by
collapsing them into the shared predicate, has failed this pack's central
test**, even if every other observation they make is accurate.

**near-miss-collapse-all (NEAR_MISS). Refuse it, and refuse it on the right
grounds.** This is the pack's centerpiece alongside shared-flag, and the two
are meant to be seen together: a candidate who has just correctly declined
to flag shared-flag for "not consolidating everything" should not then
reward near-miss-collapse-all for doing exactly that. Every guard now uses
the shared predicate, which reads as the more disciplined, more consistent
version of the same idea -- and it silently makes `test_user_account_lookup`
and `test_dotdot_path_resolution` skip on gearshift, and
`test_symlink_target_preserved` skip on tideline, none of which used to
happen. Nothing errors. Nothing fails. The suite just quietly runs fewer
tests on each platform than it used to. **The wrong reason to refuse this
variant is "it changed more files, that's risky" found by a vague diff-size
instinct.** The right reason names the specific tests that now skip
somewhere they didn't before, and why the shared predicate cannot express
what the single-platform guards used to.

**mutant-merged-reasons (MUTANT).** This one is primarily a Layer-5
execution/hidden-oracle case, not a reviewer-judgment one. Structurally it
is almost identical to shared-flag -- same predicates, same skip
decisions, same tests running and skipping on the same platforms on every
platform -- with the two dual-guard tests' reasons collapsed into one
generic string each. A static read focused on "does the skip set match" will
plausibly pass it, because the skip set does match. What the pack requires
is that the hidden oracle `skip_reasons_preserved` fails against it -- see
`oracles.py`. A review pass that actually reads the reason strings on both
platforms for `test_unix_socket_creation` and `test_bare_thread_spawn`, and
notices they're now identical where shared-flag kept them distinct, is
bonus credit, not required credit.

## The core lesson: some duplication is the boundary, not the residue

The reflex this pack is built to catch is treating *any* code that still
names both platform predicates individually, after a shared predicate has
been introduced, as leftover work. It is not: a shared predicate can only
correctly replace a guard where the condition is genuinely the same on both
platforms. Where the condition differs (the single-platform guards) or
where the condition is coincidentally the same but the *reason* differs
(the two-reason pairs), collapsing it is not tidying up, it is changing what
the code does or what it tells you when it does it. The real-world case this
pack is modeled on is a small, boring, merged CPython PR that did exactly
the correct amount of consolidation and stopped -- and a grading pass that
rewards a candidate for wanting it to go further has failed to apply this
pack's core lesson.

## Scoring guidance

- **Full credit** needs: shared-flag accepted with the three-site
  consolidation verified (not assumed) and the five surviving guards *not*
  flagged as incomplete; near-miss-collapse-all refused specifically for the
  over-skip on named tests/platforms (not vague "bigger diff" reasoning);
  scattered-disjunction accepted as a correct, if repetitive, starting
  state.
- **Partial credit:** shared-flag accepted but the reviewer still notes the
  surviving duplication as a soft concern ("could probably be unified more")
  without escalating it to a defect; near-miss-collapse-all refused for the
  right instinct but without naming which tests/platforms are affected.
- **No credit / active miss:** shared-flag flagged as an incomplete
  refactor, or the surviving per-platform guards flagged as duplication that
  should be removed; near-miss-collapse-all accepted or preferred over
  shared-flag for being more consistent.
- mutant-merged-reasons is graded by the hidden oracle
  (`skip_reasons_preserved`), not by reviewer narrative; do not penalize a
  candidate for missing it in a static read unless they also assert with
  confidence that the two dual-guard tests still report distinct,
  platform-specific reasons.
