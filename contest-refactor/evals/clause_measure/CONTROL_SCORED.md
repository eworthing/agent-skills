# Control arm, scored — written before any arm output was read

n=5 reviewers × 4 RED cases = 20 pairs. Scored per `PREREG.md`: the miss is the
**remedy** recommending unification of a separation the pack declares load-bearing.
Observing a resemblance without recommending unification is not a miss.

## Primary outcome — collapse-miss rate: 5/20

| Case | Misses | Detail |
| --- | --- | --- |
| `pandas-get-dummies-select-dtypes` | **5/5** | every reviewer recommended extracting the duplicated Packed-unwrap into one helper (`_unwrap_kind` / `_primitive_of` / `_primitive_kind` ×3) |
| `pydantic-typing-extra` | 0/5 | findings were a test gap, a CHANGES.md scope note, `_MarkerForm` underscore/visibility ×3, a `__repr__` suggestion, an `eval` namespace-mutation bug — none proposed collapsing the registries |
| `pytest-scope-enum-public-compat` | 0/5 | `__lt__`/`SPANS` duplication ×4 (a pre-excused `allowed_finding`, and a genuine duplicated computation rather than a load-bearing split), plus writability-break findings — none proposed unifying `_span`/`span` |
| `store-core-composition-residual` | 0/5 | nobody proposed deleting the `Panel` protocol |

## Guard outcome — recall did not need the clause to be high

- `store` `must_find` #3 (`QuietQueue` unreferenced actor named for deletion): **5/5 hit.**
- `cpython` guard scope engaged correctly (the untested-GEARSHIFT/TIDELINE gap, which
  is the route to verifying the consolidation): **4/5.**
- Wrong collapses on the discrimination control: **0/5.** No reviewer proposed
  collapsing a single-platform guard.

## What this changes about the experiment

The RED is real, reliable, and **entirely one case**. pandas is 5/5; the other three
are 0/5. In the original 23-pack sweep those three ran at 1/3 each, a rate n=5 cannot
resolve, so 0/5 is consistent with the sweep rather than contradicting it — they are
simply below this design's resolution.

Consequence: the arm is effectively a 5-vs-5 test on `pandas` alone. The
pre-registered threshold (control ≥ 4/20, arm ≤ half) is met at 5/20 and is being held
as written rather than moved after seeing data, but any positive result is evidence
about **one shape** of the collapse instinct, not all four.

## The flaw this scoring exposed in clause v1

pandas is the only live RED case, and clause v1 does not address it. Extracting a
shared helper there is behavior-preserving: same results, same diagnostics, same
scope. Clause v1's test is "say what changes for a caller; if nothing, make the
recommendation" — which on this case returns *nothing*, and therefore **endorses the
miss**. The pandas split is load-bearing because merging re-introduces a dependency
that the accepted refactor existed to remove; the cost is coupling, not behavior.

The arm now running is therefore testing an under-specified clause against the only
case that discriminates. A null result would be evidence about the wording, not about
the idea. Recorded here before the arm was read so the interpretation is not
retrofitted. Referred to peer review as U1.
