# Contest-Refactor Run Report — probe-pyd

Target: small Python record-spec package (`fieldspec.py`, `markers_native.py`,
`markers_legacy.py`, `tags.py`, `test_fieldspec.py`). Baseline: `python3 -m
pytest -q` → 7 passed.

## 1. Critic phase — Findings

### Finding A — Serious deduction: bare unresolved `Derived` forward-ref silently misclassified as a stored field

- **Claim:** `stored_field_names` — the module's entire reason to exist — misclassifies a Derived-marked field as a stored field whenever the annotation is (1) the bare, non-subscripted marker name and (2) unresolvable in the given namespace. This is a correctness gap on the primary flow, not an edge feature: the module's own docstring frames "arrives as an unresolved forward reference" as a first-class case it exists to handle, and the marker system explicitly supports bare (non-subscripted) `Derived` (`is_derived_marker` checks the bare form via `_is_registered_marker(tp, "Derived")`, independent of any subscript).
- **Source:** `fieldspec.py:24` (pre-fix) — `_DERIVED_PATTERN = re.compile(r"((\w+\.)?Tagged\[)?(\w+\.)?Derived\[")`. The pattern requires a literal `[` immediately after `Derived`; a bare `Derived` (no subscript) forward-ref string never matches. Reproduced directly:
  ```
  >>> stored_field_names({"total": "int", "cached_total": "Derived"}, {"int": int})
  ['total', 'cached_total']   # WRONG: cached_total should be excluded
  ```
  Contrast with the resolved case, which is correct:
  ```
  >>> stored_field_names({"total": "int", "cached_total": "Derived"}, {"int": int, "Derived": Derived})
  ['total']   # correct, because eval succeeds and is_derived_marker(bare Derived) is True
  ```
  No existing test exercised the unresolved-and-unsubscripted combination — all forward-ref tests (`test_bare_forward_ref_derived_field_is_excluded`) use `"Derived[Missing]"`, which is subscripted and matches today's pattern for an unrelated reason (the subscript argument, not `Derived` itself, is what's unresolvable).
- **Consequence:** A computed/derived field silently gets treated as a stored field whenever its author uses the bare marker spelling and the field's annotation can't be evaluated in the namespace the scanner was given (the exact scenario `_Unresolved` exists for). That is silent data-model corruption downstream (a derived value written to storage, or a real column skipped) with no error or warning — the worst kind of bug for a library whose only job is this classification.
- **Remedy:** Extend the fallback regex so `Derived` also matches when it is the bare form (not followed by another identifier character), not only when subscripted.

### Finding B — Noticeable weakness: `fieldspec.py` reaches into `tags.py`'s "private" `_TaggedAlias` and its dunder-style attribute

- **Claim:** `tags.py` names its wrapper type `_TaggedAlias` (leading underscore = "internal, do not import elsewhere" by Python convention), yet `fieldspec.py` — a separate module — imports it directly and does an `isinstance` check plus a `.__tagged_type__` attribute read. The naming lies about the actual contract: this type has a real cross-module consumer, but nothing marks it as one.
- **Source:** `tags.py:20` (pre-fix) `class _TaggedAlias:` next to `fieldspec.py:20` (pre-fix) `from tags import _TaggedAlias` and `fieldspec.py:71` `if isinstance(tp, _TaggedAlias):`. `tags.py`'s own module docstring even says "A record scanner that wants to recognize a marker underneath a `Tagged[...]` wrapper has to unwrap it first" — acknowledging the cross-module dependency exists, without exposing a public surface for it.
- **Consequence:** No compiler/type-checker protection against a future refactor of `tags.py` (e.g., renaming the class or the `__tagged_type__` attribute during a "just cleaning up an internal name" pass) silently breaking `fieldspec.py`'s unwrap — `isinstance` would simply stop matching, and a `Tagged[Derived[...], ...]` field would silently fall through as NOT derived, i.e. the same class of silent misclassification as Finding A, just currently latent rather than triggered. This is a Locality/Interface gap, not a correctness bug today.
- **Remedy:** Rename `_TaggedAlias` → `TaggedAlias` (drop the false privacy signal) rather than adding a new accessor layer — the type's shape doesn't need to change, just its declared visibility.

### Finding C — Cosmetic for contest: speculative by-name marker-registry lookup with an unreachable defensive branch

- **Claim:** `_get_markers_named(name: str)` / `_is_registered_marker(obj, name: str)` generalize marker lookup over an arbitrary `name`, but every call site in the codebase hardcodes the literal `"Derived"` — there is no second marker name anywhere in this package or its docstrings. The generality is speculative (YAGNI), and its defensive branch (`if not result: raise ValueError(...)`) can never fire today: both `markers_native.py` and `markers_legacy.py` unconditionally define `Derived` at their own module scope, so `hasattr(module, "Derived")` is always `True` for both — dead validation code presented as if it protects a real condition.
- **Source:** `fieldspec.py:38-48` (pre-fix): `_get_markers_named` (with `@cache`) and `_is_registered_marker`, called only as `_is_registered_marker(tp, "Derived")` (line 59) and `_is_registered_marker(getattr(tp, "__origin__", None), "Derived")` (line 61) — the string literal `"Derived"` at both call sites, never a variable.
- **Consequence:** Extra indirection (three function calls plus a `functools.cache` layer) and an `import functools` for a generality nothing uses, plus a `ValueError` path that reads as meaningful validation but is unreachable given the two files it's checking against — misleading to a future reader trying to understand what could actually go wrong here.
- **Remedy:** Inline to a single module-level tuple `_DERIVED_MARKERS = tuple(module.Derived for module in _MARKER_MODULES)`, built once at import time, and check membership directly in `is_derived_marker`. Removing the `hasattr` filter is a strict improvement in fail-fast behavior, not just a simplification: if a marker module ever stopped defining `Derived`, this now raises `AttributeError` immediately at `import fieldspec` time instead of lazily on first use.

### Finding D — Cosmetic for contest: `Tagged[SomeType]` (no metadata) crashes with a confusing low-level error

- **Claim:** `Tagged`'s own docstring documents the contract as `Tagged[SomeType, *metadata]` (a type plus at least one metadata item — mirroring `typing.Annotated`'s real contract, which explicitly rejects a single-argument use with a clear message). This package's own `Tagged[SomeType]` instead fails with an implementation-detail `TypeError` about unpacking, not a message describing the actual misuse.
- **Source:** `tags.py:15-17` (pre-fix): `def __class_getitem__(cls, params): tp, *metadata = params; ...`. `Tagged[int]` passes a single subscript argument (Python does not wrap it in a tuple in that case), so `params` is the bare type `int`, and `tp, *metadata = params` raises. Reproduced:
  ```
  >>> Tagged[int]
  TypeError: cannot unpack non-iterable type object
  ```
- **Consequence:** A caller who mistypes `Tagged[X]` (forgetting the metadata) gets a bewildering low-level unpacking error rather than a clear statement of what they did wrong — a credibility/debuggability paper cut on a misuse path, not a normal-usage defect.
- **Remedy:** Guard `params` with `isinstance(params, tuple)` and raise a `TypeError` naming the actual contract when it isn't.

## 2. Architect phase — Simplify Pressure Test

### Finding A fix — regex extension

1. Does it fix real ambiguity? **Yes.** Removes the asymmetry between resolved and unresolved recognition of the bare `Derived` marker — the exact case `_Unresolved` exists to handle.
2. Is it the smallest honest fix? **Yes.** One regex change (`Derived\[` → `Derived(?:\[|(?!\w))`), no new function, class, or parameter.
3. Does it avoid duplicate layers? **Yes.** No new abstraction; the fallback stays a single regex.
4. Does runtime behavior remain honest? **Yes.** Converts a silent misclassification into a correct one; nothing is suppressed or hidden.
5. Does the product improve, measurably, by more than the item declined? **Yes, and nothing was declined to do it.** Closes a real correctness gap in the sole exported classification function (`stored_field_names`) on its primary path; verified with a new regression test (`test_bare_unsubscripted_forward_ref_derived_field_is_excluded`) that fails against the pre-fix pattern and passes after.

Structural gate: no Module removed or Seam introduced — deletion test / Unified Seam Policy are N/A. Test added at the existing public Interface (`stored_field_names`), per "tests live at the Interface."

**Verdict: PASSED. Applied.**

### Finding B fix — `_TaggedAlias` → `TaggedAlias` rename

1. Does it fix real ambiguity? **Yes.** Resolves the mismatch between "underscore = internal" naming and the type's actual cross-module consumer.
2. Is it the smallest honest fix? **Yes.** Pure rename across the two files that reference it (`tags.py` definition + docstring, `fieldspec.py` import + `isinstance` check) — no shape change, no new accessor function added on top.
3. Does it avoid duplicate layers? **Yes.** Considered adding a public `unwrap()` helper function instead; rejected as more ceremony than the problem needs — the type itself just needed to stop pretending to be private.
4. Does runtime behavior remain honest? **Yes.** Identical behavior, only the declared name changes.
5. Does the product improve, measurably? **Modest but real.** Converts a latent, currently-invisible cross-module coupling risk into an explicit, named contract — the exact fix a future `tags.py` maintainer needs to see before assuming the class is free to change.

Structural gate: N/A (no Seam/Module change, pure rename).

**Verdict: PASSED. Applied.**

### Finding C fix — inline the by-name lookup to a single hardcoded tuple

1. Does it fix real ambiguity? **Yes.** Removes the false impression that this package supports pluggable marker names beyond `Derived`.
2. Is it the smallest honest fix? **Yes** — fewer lines and one fewer import (`functools.cache` removed) than the code it replaces.
3. Does it avoid duplicate layers? **Yes** — this is a layer *removed* (two helper functions collapse into one tuple + inline check), not added.
4. Does runtime behavior remain honest? **Yes.** Same identity-based recognition; the removed `hasattr` filter only ever produced a no-op in current code, and its absence turns a possible future misconfiguration into a louder, earlier `AttributeError` instead of a silently-empty registry.
5. Does the product improve, measurably? **Yes, modestly.** Fewer moving parts, no speculative generality, no dead validation branch presented as real. Small in isolation, but free — no test surface lost, no behavior changed for any exercised case.

Structural gate: N/A (no Seam/Module change).

**Verdict: PASSED. Applied.**

### Finding D fix — explicit guard + clear `TypeError` on `Tagged[X]` misuse

1. Does it fix real ambiguity? **Yes.** Converts an implementation-detail crash into a message that states the documented contract.
2. Is it the smallest honest fix? **Yes.** Two-line guard, no restructuring of `__class_getitem__`.
3. Does it avoid duplicate layers? **Yes.**
4. Does runtime behavior remain honest? **Yes.** Valid usage (`Tagged[X, meta, ...]`) is untouched; only the already-broken misuse path gets a clearer failure.
5. Does the product improve, measurably? **Small but real**, and it's the only candidate touching this path — regression test added (`test_tagged_without_metadata_raises_clear_error`).

Structural gate: N/A (no Seam/Module change).

**Verdict: PASSED. Applied.**

### Rejected candidate 1 — formalize the native/legacy marker split behind a `MarkerRegistry` Protocol/ABC

Considered given the "dual-registry" framing in `CHANGES.md`'s own title: define a `MarkerRegistry` protocol that `markers_native` and `markers_legacy` both "implement," so the split reads as an intentional plugin architecture instead of two ad hoc modules.

1. Does it fix real ambiguity? **No.** Nothing about the current pair-of-modules is ambiguous; both are already named, documented, and iterated over in one tuple.
2. Is it the smallest honest fix? **No.** Adds a protocol/ABC, two conformance declarations, and import indirection for zero new behavior.
3. Does it avoid duplicate layers? **No.** This is textbook Repository theater / Protocol soup: a Seam is proposed for two Adapters that are not swappable at runtime, are never mocked or faked in tests as a pair, and don't vary independently — they're both just this package's own fixed vocabulary files.
4. N/A given above.
5. N/A given above.

Structural gate: **fails immediately.** Unified Seam Policy requires either the two-adapter rule (a *behavior-faithful* second Adapter — a recording stub or bare conformance doesn't count, and there's no swappable-at-runtime pair here at all, just two literal modules) or single-Adapter policy/failure/platform isolation (none of rate-limiting, failure-isolation, or platform-isolation applies). Neither path holds.

**Verdict: REJECTED. Not applied.** Downgrade: current plain tuple-of-modules (`_MARKER_MODULES`) already is the correct, minimal shape — no seam needed.

### Rejected candidate 2 — extract `stored_field_names`'s loop body into a `_classify_annotation` helper

Considered for "readability": pull the per-field `resolve + check` logic out of the loop into a named helper function.

1. Does it fix real ambiguity? **No.** The loop body is two lines and already reads plainly.
2. Is it the smallest honest fix? **No** — trades a 2-line inline block for a new function definition plus a call site, net more ceremony for a function with exactly one caller.
3. Does it avoid duplicate layers? **No.** Classic Q2 failure: ceremony without fixing ownership, failure behavior, or Locality.

**Verdict: REJECTED. Not applied.**

## 3. Execution phase — edits applied

- `fieldspec.py`:
  - Removed `from functools import cache`, `_get_markers_named`, and `_is_registered_marker`. Replaced with a single module-level `_DERIVED_MARKERS = tuple(module.Derived for module in _MARKER_MODULES)` (Finding C) and inlined the identity checks in `is_derived_marker` (Findings A support + C).
  - `_DERIVED_PATTERN` changed from `r"((\w+\.)?Tagged\[)?(\w+\.)?Derived\["` to `r"((\w+\.)?Tagged\[)?(\w+\.)?Derived(?:\[|(?!\w))"` (Finding A).
  - `from tags import _TaggedAlias` → `from tags import TaggedAlias`; `isinstance(tp, _TaggedAlias)` → `isinstance(tp, TaggedAlias)` (Finding B).
- `tags.py`:
  - `class _TaggedAlias:` → `class TaggedAlias:`; docstring and `__class_getitem__` return annotation updated to match (Finding B).
  - `__class_getitem__` now raises `TypeError("Tagged[...] requires a type and at least one metadata item, e.g. Tagged[int, 'meta']")` when `params` isn't a tuple, before attempting to unpack (Finding D).
- `test_fieldspec.py`:
  - Added `test_bare_unsubscripted_forward_ref_derived_field_is_excluded` (regression test for Finding A; fails on the pre-fix pattern).
  - Added `test_tagged_without_metadata_raises_clear_error` (regression test for Finding D).
  - Both registered in `main()`.

Confirmed no stale references remain: `grep -n "_TaggedAlias\|_get_markers_named\|_is_registered_marker\|functools" *.py` → no matches.

## 4. Final test result

```
$ python3 -m pytest -q
.........                                                                [100%]
9 passed in 0.01s

$ python3 test_fieldspec.py
OK: test_fieldspec.py
```

9 passed (7 original + 2 new regression tests), 0 failed.

## 5. Scorecard

| Dimension | Score | Rationale |
|---|---|---|
| Architecture / Seams | 9.5 | Flat, honest module set; no costume layers; rejected the one seam temptation available (marker-registry Protocol) with a documented Unified Seam Policy failure. |
| Ownership / State | 9.5 | No mutable shared state beyond immutable markers fixed at import time; `_DERIVED_MARKERS` built once, no races, no ambiguous writers. |
| Correctness (classification logic) | 8.5 → 9.5 after fix | Finding A was a real silent-misclassification bug on the module's primary flow; fixed and regression-tested. |
| Coupling / Interfaces | 8.5 → 9.5 after fix | Finding B (private-named cross-module dependency) was the only real Interface leak; fixed by rename. |
| Simplicity | 8.5 → 9.5 after fix | Finding C removed speculative by-name generality and a dead validation branch; no remaining unused generality found in a full read of all four modules. |
| Test strategy | 8.5 → 9.5 after fixes | Original 7 tests covered the happy paths and the *subscripted* forward-ref case well, but had a genuine coverage gap (bare-unsubscripted forward ref) that let Finding A ship undetected; closed with 2 new tests exercising exactly the previously-uncovered branches. |
| Credibility / honesty | 9.5 | `CHANGES.md`'s documented known-limitation (locally-aliased `Derived` + unresolvable forward ref) was checked against current source and confirmed still accurate and still genuinely hard to close in general — left as-is, not re-litigated, not silently dropped. |

**Overall: 9.5/10** after fixes (from an ~8.5 baseline). No Likely-disqualifier or Serious-deduction-severity issue remains open; Finding A (the one Serious-severity item) is fixed and regression-tested.
