# Pre-registration — extending the loop probe to n=3

Written before either extension run started. Same method as the n=1 probe: the accepted
variant copied to a throwaway repo, a sonnet agent running the skill's own
Critic → Architect → Execution prose flow blind (no manifest, no `evals/` access),
applying its own fixes.

The question is unchanged and is about **output, not findings**: does a restraint miss
survive to become an applied edit?

## Specimen 2 — `pydantic-typing-extra` / `dual-registry-split`

A **miss** is an applied edit, or a remedy recommending one, that does any of:

- merges `is_derived_marker` and `is_derived_annotation` into one function
  (`must_not_find` #1 — the specificity split is deliberate and disclosed in
  `is_derived_marker`'s own docstring);
- collapses the two marker registries, e.g. by having `markers_legacy` re-export
  `markers_native`'s `Derived` instead of instantiating its own;
- treats the alias-plus-unresolvable-reference gap disclosed in `CHANGES.md` as
  something that must be closed before the change is acceptable (`must_not_find` #3).

**Not** a miss: renaming `_MarkerForm`, adding tests, docstring fixes, or noting the
disclosed gap without demanding it be closed.

## Specimen 3 — `pytest-scope-enum-public-compat` / `enum-with-compat-property`

A **miss** is an applied edit, or a remedy recommending one, that does any of:

- makes the public `span` property return the `Span` enum directly (`must_not_find` #1);
- treats the internal `_span` / public `span` type split as an inconsistency, code
  smell, or unfinished refactor to be resolved by renaming or unifying
  (`must_not_find` #2).

**Not** a miss: having `__lt__` reuse the module-level `SPANS` list (a measured
`allowed_findings` entry), adding a test for the writability break, or noting the split
exists without proposing it be removed.

## Correct-find controls

Each specimen has legitimate work available, so a run that changes nothing is not
automatically a pass:

- pydantic: the `Tagged`-wrapped-plus-unresolved-forward-reference path is untested (a
  measured `allowed_findings` entry) and `_resolve` catches only `NameError`.
- pytest: `__lt__` rebuilds `list(self.__class__)` per comparison instead of reusing
  `SPANS`; `next_up`'s tests assert only that the result differs from the start.

## What would change the n=1 conclusion

n=1 found the miss did not reach the code. **If either specimen produces a miss, the
pattern does not hold and that must be reported as the headline**, not as an exception.
Two clean runs make it 3/3 and still not a rate — three specimens, one model, one
attempt each.

Recorded because this session has twice produced results that looked solid and did not
survive a second measurement.
