# Architectural Refactor Review — RUN_REPORT

Target: `v2-pyd/` (fieldspec.py, markers_native.py, markers_legacy.py, tags.py, test_fieldspec.py, CHANGES.md)
Protocol: method.md (Critic Method + Simplify Pressure Test), architecture-rubric.md, lens-generic.md (+ always-included lens-security.md, lens-efficiency.md)
Baseline: `python3 -m pytest -q` → 7 passed.

---

## 1. Critic phase — Findings (Evidence Chain: Claim → Source → Consequence → Remedy)

### F1 — `_resolve` mutates the caller's `namespace` dict as an undocumented side effect (Serious deduction)

- **Claim.** `_resolve` looks like a pure lookup (`namespace: dict[str, object]` read to resolve a forward reference) but silently writes into that same dict on every call. This is a hidden writer against `state_management`'s "every writer explicit" anchor and `data_flow`'s "no back-channels" anchor.
- **Source.** `fieldspec.py:78-82` (pre-fix):
  ```
  def _resolve(source: str, namespace: dict[str, object]) -> object:
      try:
          return eval(source, namespace)
      except NameError:
          return _Unresolved(source)
  ```
  CPython's `eval(source, globals)` — when given a single dict — uses it as both globals and locals and **injects a `__builtins__` key into it if absent**. Reproduced live:
  ```
  >>> ns = {"int": int}
  >>> eval("int", ns)
  >>> sorted(ns.keys())
  ['__builtins__', 'int']
  ```
  Called from `stored_field_names` (`fieldspec.py:90`) on every field, so any caller-owned `namespace` gets a stray `__builtins__` key after the first call.
- **Consequence.** A caller that reuses, compares, serializes, or asserts against its own namespace dict (e.g. `vars(record_cls)`-derived dict, or a namespace shared across multiple scan calls) observes an unexplained extra key it never put there. No test in the suite checks for this — a real, demonstrated mutation with zero regression coverage (Step 8 mutation-test gap: a regression that reintroduced or worsened this mutation would pass all 7 existing tests unnoticed, because none of them inspect `namespace` after the call).
- **Remedy.** Evaluate against a disposable copy: `eval(source, dict(namespace))`. Same resolution result, no caller-visible mutation.

### F2 — `fieldspec.py` reaches into `tags.py`'s private `_TaggedAlias` (Noticeable weakness)

- **Claim.** `tags.py` names its wrapper type `_TaggedAlias` (leading underscore = module-private, per the docstring "Generic metadata wrapper... nothing about `Tagged` itself implies that any scanner does [unwrap]"). But `fieldspec.py` imports that private name directly and does `isinstance` + dunder-attribute access on it — the underscore convention lies about what other first-party code actually depends on. This is an Interface-honesty leak: a `tags.py` maintainer renaming `_TaggedAlias` (reasonably assuming it's purely internal) silently breaks `fieldspec.py` with no import-time signal beyond a runtime crash.
- **Source.**
  - `tags.py:20-23` — `class _TaggedAlias: def __init__(self, tp, metadata): self.__tagged_type__ = tp; self.__metadata__ = metadata`
  - `fieldspec.py:20` (pre-fix) — `from tags import _TaggedAlias`
  - `fieldspec.py:71-72` (pre-fix) — `if isinstance(tp, _TaggedAlias): tp = tp.__tagged_type__`
  - Contrast: the sibling marker check in the *same file* already uses the honest pattern — `getattr(tp, "__origin__", None)` (`fieldspec.py:61`) duck-types on `_MarkerAlias`'s protocol attribute instead of importing `_MarkerAlias` and doing `isinstance`. Two different coupling idioms sit side by side for the same kind of problem.
- **Consequence.** Reduces credibility/Locality: the module boundary `tags.py` presents (public `Tagged`, private everything else) is not the boundary `fieldspec.py` actually depends on. Increases the blast radius of an internal rename in `tags.py` that looks safe by its own naming convention.
- **Remedy.** Drop the import and the `isinstance` check; duck-type on the same dunder attribute already-established as this file's convention for markers: `if hasattr(tp, "__tagged_type__"): tp = tp.__tagged_type__`.

### F3 — `_get_markers_named(name: str)` is a generic registry keyed by a string that is always `"Derived"` (Cosmetic for contest)

- **Claim.** The function is parameterized over `name: str`, but every call site in the codebase passes the literal `"Derived"` — there is no second marker name anywhere. The `if not result: raise ValueError(...)` guard inside it is consequently unreachable with current call sites (both registries always define `Derived`), which is dead defensive code riding on top of unused generality.
- **Source.**
  - `fieldspec.py:37-43`:
    ```
    @cache
    def _get_markers_named(name: str) -> tuple[object, ...]:
        result = tuple(getattr(module, name) for module in _MARKER_MODULES if hasattr(module, name))
        if not result:
            raise ValueError(f"no registry defines a marker named {name!r}")
        return result
    ```
  - Call sites: `fieldspec.py:47` (`_is_registered_marker`, itself always called with `"Derived"`), `fieldspec.py:59` and `:61` (`is_derived_marker`).
- **Consequence.** Minor — a private helper carrying speculative flexibility nobody uses, plus a guard clause that can't currently fire. Not disqualifying; not blocking any Serious concern; a "generic filler" case the rubric's own Ignore-list waves off unless part of a larger pattern.
- **Remedy considered.** Hardcode `"Derived"` and drop the parameter (and, aggressively, the guard). See SPT below — **rejected**.

### F4 — Documented gap: locally-aliased `Derived` import + unresolvable forward reference (Cosmetic for contest, accepted residual)

- **Claim.** A field whose annotation both (a) uses a local import alias for a registry's `Derived` object (`from markers_legacy import Derived as LocalDerived`) and (b) is itself an unresolvable forward reference (`LocalDerived[Missing]`) is not recognized as Derived — the regex fallback only knows the literal spelling `Derived`, not an arbitrary caller-chosen alias.
- **Source.** `fieldspec.py:23` (`_DERIVED_PATTERN`, matches literal `Derived` only) + `fieldspec.py:63-74` (`is_derived_annotation`'s regex-fallback branch) + `CHANGES.md:11-19`, which already documents this exact gap and explains why closing it in general is disproportionate ("either evaluating an annotation that can't be evaluated, or teaching the fallback every alias a caller might pick").
- **Consequence.** Real but narrow and already honestly disclosed — this is the accepted-residual case the `domain_modeling` 9-anchor itself describes ("one or two parallel-fields cases remain but are documented"). Doc-vs-code grep confirms no doc-rot: the documented limitation matches current code exactly.
- **Remedy considered.** An AST-based partial-name resolver that looks up the base identifier of the forward-ref expression against `namespace` directly (bypassing the fixed-spelling regex entirely) would close this in general, not just for enumerated aliases. See SPT below — **rejected**; the maintainers' own documented conclusion stands.

Doc-vs-code grep (`LEGACY|TEMPORARY|DEPRECATED|DO NOT|ASPIRATIONAL|carve-out|SHIM|FIXME|HACK|TODO`) over the package: no hits beyond CHANGES.md's own honest gap note above — no doc-rot pattern found.

Security lens (always-included): `_resolve` uses `eval(source, namespace)` to resolve forward-referenced type annotations. Considered under "insecure deserialization" — ruled out as a finding: `source` is always a class's own `__annotations__` text (author-controlled, already syntax-checked by the Python compiler at class-definition time), the same trust boundary `typing.get_type_hints` operates under. Not user/network-controlled input, so this does not meet the lens's "untrusted data" bar.

Efficiency lens (always-included): checked D1-D4 — no recomputed derived values, no sequential I/O loops, no startup/hot-path blocking work, no long-lived closures. `_get_markers_named` is already `@cache`d (compute-once). No efficiency findings.

---

## 2. Architect phase — Simplify Pressure Test

### SPT on F1's fix — `eval(source, namespace)` → `eval(source, dict(namespace))`

1. **Does it fix real ambiguity?** Yes — closes a mechanically demonstrated defect (namespace mutation reproduced above), not a hypothetical.
2. **Is it the smallest honest fix?** Yes — one-line change, no new abstraction, no new parameter, no new file.
3. **Does it avoid duplicate layers?** Yes — owner count for "what does resolution write to" stays at exactly one (`_resolve`) before and after; the fix removes a side effect, it does not add a second decision-maker.
4. **Does runtime behavior remain honest?** Yes — resolution *results* (what counts as Derived) are byte-identical; only the caller-visible mutation is removed. No suppression involved.
5. **Does the product improve measurably, by more than what's declined?** Yes — moves `state_management`/`data_flow` off a real, demonstrated hidden-writer hazard, for a single `dict()` copy on a non-hot path (no D3 concern per lens-efficiency). Nothing higher-value is being displaced — F2 is fixed in the same pass, not traded away for this.

**Structural gate:** No new/restructured Seam (N/A to Unified Seam Policy). No Module removed (N/A to deletion test). New regression test (`test_stored_field_names_does_not_mutate_namespace`) sits at the existing public Interface (`stored_field_names`), not against internals.

**VERDICT: PASSED.**

### SPT on F2's fix — drop `from tags import _TaggedAlias`; use `hasattr(tp, "__tagged_type__")`

1. **Does it fix real ambiguity?** Yes — removes the question "is `_TaggedAlias` really private?" entirely by depending on no name from `tags.py` at all; aligns with this file's own already-established duck-typed convention for `_MarkerAlias.__origin__`.
2. **Is it the smallest honest fix?** Yes — net deletion (one import line gone) plus a one-line predicate swap. Considered the alternative of renaming `_TaggedAlias` → `TaggedAlias` in `tags.py`: rejected as inferior — it's a larger diff (two files touched) that still leaves a hard `isinstance` coupling across the module boundary, whereas duck-typing removes the coupling outright and matches the file's existing idiom (Meta-Rule 5: prefer subtractive fixes).
3. **Does it avoid duplicate layers?** Improves this axis — collapses two different cross-module-recognition idioms (isinstance+private-import for Tagged, duck-typed dunder-attribute for Marker) down to one consistent idiom in the same function.
4. **Does runtime behavior remain honest?** Yes — `hasattr(tp, "__tagged_type__")` recognizes exactly the same runtime objects `isinstance(tp, _TaggedAlias)` did (only `_TaggedAlias` instances define that attribute anywhere in this codebase). Verified by the existing `test_tagged_wrapped_derived_field_is_excluded` and `test_is_derived_annotation_sees_through_tagged` continuing to pass unchanged.
5. **Does the product improve measurably, by more than what's declined?** Yes — removes a real Interface-honesty leak (`architecture`/`credibility` residual) for zero added complexity (a net deletion), eliminating a future silent-breakage risk in `tags.py`. Nothing of higher value is being traded off.

**Structural gate:** No new Seam proposed — if anything, a coupling is *removed* (subtractive, matching Meta-Rule 5). No Module deleted. Existing tests already exercise `fieldspec.py`'s public Interface (`is_derived_annotation`, `stored_field_names`) and needed no changes for this fix.

**VERDICT: PASSED.**

### SPT on F3's proposed fix — hardcode `"Derived"`, drop the `name` parameter (and, optionally, the now-more-obviously-dead `ValueError` guard)

1. **Does it fix real ambiguity?** Marginal-yes at best — there is no live ambiguity today, only unused generality. Nothing is currently confused or miscounted because of the parameter.
2. **Is it the smallest honest fix?** No. Removing just the parameter while keeping the guard makes the guard *more* obviously pointless (a `ValueError` with no way to vary its trigger). Removing the guard too trades away the one piece of fail-loud defense this function has, for a scenario (both registries someday stop defining `Derived`) that would otherwise fail *silently* as `False` instead of crashing at cache-warm time.
3. **Does it avoid duplicate layers?** Neutral — owner count (one function, one registry) is unaffected either way.
4. **Does runtime behavior remain honest?** The aggressive version (drop the guard) makes it *less* honest: a future regression that removed `Derived` from both registries would silently under-report instead of raising. The conservative version (keep the guard, drop only the parameter) keeps behavior identical but leaves visibly dead code.
5. **Does the product improve measurably, by more than what's declined?** No. The only nameable gain is "tidier" — no scorecard dimension moves by a citable amount for a private, single-call-site helper. This is exactly the rubric's own warning: *"'it is tidier' is not a product improvement."* The risk side (weakened fail-loud behavior, or newly-obvious dead code either way) outweighs a cosmetic gain.

**Structural gate:** N/A (no Seam involved), but note for completeness: deleting the guard doesn't make "complexity reappear elsewhere" if later needed — it's inert either way, which reinforces that touching it buys nothing now.

**VERDICT: REJECTED** (fails Q5; the aggressive variant also fails Q4). Left as-is; recorded as an open Cosmetic backlog item, not fixed this loop.

### SPT on F4's proposed fix — AST-based partial-name resolver to close the alias+unresolvable-forward-ref gap in general

1. **Does it fix real ambiguity?** Yes, in principle — parsing the forward-ref source with `ast`, resolving only the base identifier against `namespace`, and checking that against the marker registry would recognize `LocalDerived[Missing]` regardless of which alias name the caller chose, without needing to fully evaluate the failing subscript.
2. **Is it the smallest honest fix?** No. This replaces a 2-line regex with a small Python-source partial-interpreter (walk `ast.Subscript`/`ast.Attribute`/`ast.Name` nodes, handle nested `Tagged[...]` wrapping, avoid misreading string-literal metadata args as names) for a scenario that is: (a) already correctly and honestly disclosed in `CHANGES.md`, (b) unobserved in practice — no failing test, no reported caller hitting it, and (c) already correctly handled for the common real cases (bare `Derived`, module-qualified `Derived`, `Tagged`-wrapped `Derived`) by the existing 8 passing tests.
3. **Does it avoid duplicate layers?** Would not add an owner if it fully replaced the regex — neutral to slightly positive on this axis alone.
4. **Does runtime behavior remain honest?** No new suppression, but it trades a small, fully-tested surface (a documented, narrow gap) for a materially larger, less-tested surface (a mini AST walker) — a net increase in behavior surface that must now be reasoned about, for a benefit that is currently hypothetical.
5. **Does the product improve measurably, by more than what's declined?** No. The cost (new parsing/walking code, larger than the rest of the package combined, new edge cases to get right) is concretely larger than the unproven gain (closing a case with zero observed occurrences). This is the "gain is real but smaller than what you are declining" failure mode, sharpened further because the gain itself is unproven.

**Structural gate:** Would likely introduce a new internal helper/Seam for AST walking — **fails Friction Proof Before Seam Recommendation** outright: no friction has been demonstrated (no caller has hit this, no test reaches it), so a new Seam cannot be justified regardless of the other four answers.

**VERDICT: REJECTED** (fails Q2, Q5, and the Friction-Proof gate). `CHANGES.md`'s existing documented residual stands unchanged; no code change made for F4.

---

## 3. Execution phase — Fixes applied

Two edits to `fieldspec.py`, both SPT-PASSED:

1. **Removed the private cross-module import** (F2):
   ```diff
   -from tags import _TaggedAlias
   ```
   and in `is_derived_annotation`:
   ```diff
   -    if isinstance(tp, _TaggedAlias):
   +    if hasattr(tp, "__tagged_type__"):
            tp = tp.__tagged_type__
   ```

2. **Stopped `_resolve` from mutating the caller's namespace** (F1):
   ```diff
   -        return eval(source, namespace)
   +        # `eval(source, ns)` injects `__builtins__` into `ns` when it's
   +        # missing -- eval a copy so a caller's namespace is never mutated
   +        # as an undocumented side effect.
   +        return eval(source, dict(namespace))
   ```

3. **Added one regression test** in `test_fieldspec.py` (Ponytail: non-trivial logic gets one runnable check) covering F1, wired into both the pytest suite and the standalone `main()` runner:
   ```python
   def test_stored_field_names_does_not_mutate_namespace() -> None:
       namespace = dict(NAMESPACE)
       before_keys = set(namespace)
       stored_field_names({"total": "int", "cached_total": "Derived[int]"}, namespace)
       assert set(namespace) == before_keys, namespace
   ```

`tags.py`, `markers_native.py`, `markers_legacy.py`, and `CHANGES.md` were **not** modified — F3 and F4 were investigated, SPT-rejected, and left as open/accepted residuals rather than "fixed" for the sake of touching them.

### Final pytest result

```
$ python3 -m pytest -q
........                                                                 [100%]
8 passed in 0.01s

$ python3 test_fieldspec.py
OK: test_fieldspec.py
```

8/8 passing (7 original + 1 new regression test). Both the pytest entry point and the standalone `__main__` entry point pass.

---

## 4. Final scorecard

| Dimension | Pre-fix | Post-fix | Residual (post-fix) |
|---|---|---|---|
| Architecture quality | 9.0 | 9.5 (accepted) | F4 — documented alias/forward-ref gap (`CHANGES.md`) |
| State mgmt & runtime ownership | 8.0 | 9.5 (accepted) | none blocking; F1 hazard eliminated |
| Concurrency & runtime safety | 10 | 10 | no concurrency surface in this package |
| Test strategy & regression resistance | 8.0 | 9.5 (accepted) | F4's edge case remains genuinely untested, by design, and documented |
| Overall implementation credibility | 9.0 | 9.5 (accepted) | F3 — dead `ValueError` guard / unused generality, cosmetic |
| Domain modeling | 9.5 (accepted) | 9.5 (accepted) | F4 — matches the 9-anchor's own "documented parallel-fields case" language |
| Data flow & dependency design | 9.0 | 9.5 (accepted) | F1 hazard eliminated; no other back-channels found |
| Framework / platform best practices | 9.5 (accepted) | 9.5 (accepted) | unchanged; idiomatic use of `functools.cache`, dunder-protocol pattern, `__future__ annotations` |
| Code simplicity & clarity | 8.5 | 9.0 | F3 — unused generality in `_get_markers_named`, SPT-rejected this loop, left as backlog |

No dimension reaches a bare 10 post-fix: `architecture`, `state_management`, `test_strategy`, `credibility`, `domain_modeling`, `data_flow`, and `framework_idioms` each carry one named, accepted residual (F3 or F4); `simplicity` carries F3 as an explicit open backlog item (not accepted-and-closed, since it was actively considered and rejected this loop, not merely deferred).

---

## Summary

- **4 findings raised**: F1 (Serious — hidden namespace mutation via `eval`), F2 (Noticeable — private-name interface leak on `Tagged` unwrapping), F3 (Cosmetic — unused generality in `_get_markers_named`), F4 (Cosmetic, pre-existing accepted residual — documented alias + unresolvable-forward-ref gap).
- **2 fixes applied**, both SPT-PASSED on all 5 questions plus the structural gate: F1's `dict(namespace)` copy, F2's duck-typed `hasattr` check replacing the private import.
- **2 fixes SPT-rejected** (recorded, not hidden): F3's hardcode-the-parameter cleanup failed Q5 (no measurable product improvement) and partially Q4 (the aggressive variant weakens fail-loud behavior); F4's AST-based general fix failed Q2, Q5, and the Friction-Proof structural gate (no demonstrated friction to justify the new surface).
- **Tests**: 7 → 8 passing (added one regression test for F1). Both `pytest -q` and the standalone `python3 test_fieldspec.py` runner pass.
