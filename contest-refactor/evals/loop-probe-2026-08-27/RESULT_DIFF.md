# Diff probes, n=6 — result

Graded against `PREREG_DIFF.md`, from the applied diffs and by re-running each
specimen's own behaviour, **not** from the agents' self-reports.

## Scoreboard

| # | Specimen | Verdict | What landed |
| --- | --- | --- | --- |
| d1 | `config-precedence` **RED** | **UNDER-ACTION** | patched the symptom, left two owners standing |
| d2 | `auth-unusable-password-policy` | clean | real security fix, load-bearing invariant preserved |
| d3 | `werkzeug-socket-lifecycle` | clean | dead write-only state deleted, false docstring corrected, untested conflict path covered |
| d4 | `cpython-wasm-platform-predicate` | clean (one borderline call) | per-platform skip coverage added; doc-vs-code contradiction resolved |
| d5 | `pandas-groupby-plot-imperfect-gold` | clean | **reproduced the real upstream correction** |
| d6 | `cpython-genexpr-iterability` | clean | hand-rolled loop simplified, error-timing contract intact |

**HARM: 0 of 6.** No specimen lost a load-bearing property, broke a build, or left a
suite failing. Every bundled suite passed after the run, most with net-new tests.

**UNDER-ACTION: 1 of 1.** On the only specimen where action was required, it failed.

## d5 — the strongest single result

The pack's residual, from its own manifest: the accepted variant forwards the group key
for Lane but not Panel groups, so a Panel legend silently comes back empty. *"It was
corrected 18 days later by `key-forwarded`, which forwards `(group, key)` uniformly and
adds a regression test for the Panel-legend case."*

d5 replaced the `isinstance(group, Lane)` special-case with uniform
`key=getattr(group, "key", None)` and added `test_plot_legend_labels_for_panels`. That is
the same correction shape as pandas PR #66027 — produced blind, in one pass, from source
alone. It also threaded both traps: it did not take the "no user-visible change" claim at
face value (`must_not_find` #1), and it did not reject the whole refactor over the
residual (#3).

## d1 — the failure, and why it is narrow

`must_not_find` #2 says, verbatim: *"Changing `describe_source`'s truthiness test to a
presence test restores agreement today and leaves two owners of the layer order, which is
the thing that drifted."* That is exactly and only what d1 did — verified in the file: six
membership checks still spread across two independent walks.

The correct remedy **was raised and then rejected by the Simplify Pressure Test**, on Q2
(ceremony for a four-line cascade) and Q5 (no measurable gain, only two call sites).

## What the ten observed SPT rejections actually show

Across nine probes, SPT rejected ten proposed fixes. Nine were right: inlining a
pass-through wrapper, a speculative registry `Protocol`, extracting a two-line body,
`Generic[T]` ceremony, a speculative accessor, `Optional[Listener]` restructuring, a
third-party crypto dependency, wiring a platform detector that does not exist, and
deleting apparently-dead public API whose dead-ness could not be proven from the checkout.

One was wrong: d1's consolidation.

**The pattern is not "too cautious".** d5 declined to delete `apply_general` because
dead-ness was genuinely unprovable — correct. d1 declined a consolidation whose drift had
been *demonstrated with a repro* against an explicit docstring contract — incorrect. The
evidence was there and the gate did not weigh it.

**Q2 and Q5 measure a consolidation by size and by gain. Neither asks whether the two
sites answer the same question.** Where duplication is load-bearing that heuristic is
right by accident; where it is genuine duplicate authority it is wrong. Four collapse-type
judgments across the probes came out 3 right, 1 wrong, and the wrong one is exactly the
duplicate-authority case.

## What this says about the failed prose clause

The clause tried to add restraint at **finding-raising** time. SPT already restrains at
**fix-application** time, and does it well in nine cases out of ten. The real defect is
the opposite of what the clause targeted: not too little restraint, but restraint applied
without the one distinction that matters.

If any prose change is worth making here, it is to SPT's own questions — adding a
"do these sites share one policy and have to change together?" limb — not to Meta-Rule 5.
**Unmeasured.** It is a hypothesis produced by this run, not a result.

## Limits

Nine probes, one model, one attempt each, small specimens, skill prose rather than the
full harness with `LOOP_STATE.json` and the 50 gates. Six specimens is a spread, not a
rate. The single under-action case is n=1 on that failure mode — the corpus contains
exactly one pack that can produce it, built earlier the same day.
