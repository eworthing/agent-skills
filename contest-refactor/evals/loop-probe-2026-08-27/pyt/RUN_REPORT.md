# Run Report — lifespan.py architectural review

Target: `lifespan.py` + `test_lifespan.py` (2 files, ~73/75 lines). Baseline:
`python3 -m pytest -q` → 7 passed.

## Findings (Evidence Chain: Claim → Source → Consequence → Remedy)

### F1 — Serious/Noticeable: `value_of` is unreferenced dead code
- **Claim:** `value_of` is a pass-through wrapper (`span.value`) with zero call
  sites anywhere in the visible source, including the module's own bundled
  test suite.
- **Source:** `lifespan.py` (pre-fix) lines 42-43:
  `def value_of(span: Span) -> str: return span.value`. `test_lifespan.py`
  line 14 imports `SPANS, Handle, higher, next_up, span_from_value` —
  `value_of` is absent. `grep -rn "value_of" . --include="*.py"` after
  deletion returns nothing, confirming no other reference existed.
- **Consequence:** Untested, uncalled public code can silently rot (e.g. if
  `Span`'s value-access pattern changed, nothing would catch a break here).
  It inflates the module's declared Interface without earning any Leverage —
  the Deletion Test passes cleanly: remove it, complexity vanishes, nothing
  reappears.
- **Remedy:** Delete `value_of`.
- **Disposition: FIXED.**

### F2 — Noticeable: duplicate ordering computation in `Span.__lt__`
- **Claim:** `Span.__lt__` rebuilt `list(self.__class__)` on every comparison
  instead of reusing the module-level `SPANS` list that exists for exactly
  this purpose — contradicting the module docstring's own claim of a single
  ordered source of truth.
- **Source:** `lifespan.py` (pre-fix) lines 29-33:
  `order = list(self.__class__)` / `return order.index(self) < order.index(other)`.
  Module-level `SPANS = list(Span)` (line 36, pre-fix), already reused by
  `next_up` at `SPANS.index(span)` (line 54, pre-fix). Docstring lines 6-8:
  "`higher` and `next_up` are the two operations everything else needs, now
  backed by one ordered enum instead of a mapping copied at each call site."
- **Consequence:** Two independently-built copies of "the ordering" existed
  in one file; a future change to how `SPANS` is derived would silently
  desync from `__lt__`. Every `<`/`<=`/`>`/`>=`/`higher()` call paid for a
  fresh list allocation it didn't need (lens-efficiency D1, recomputed
  derived value) — negligible at n=5, but the duplicate-authority shape is
  exactly what the module's own docstring claims was eliminated.
- **Remedy:** `__lt__` reuses `SPANS.index(...)` instead of rebuilding the
  list.
- **Disposition: FIXED.**

### F3 — Noticeable: `Span` ordering reflexivity untested (mutation-test gap)
- **Claim:** No test exercised `Span.X < Span.X` (self-comparison). The only
  ordering assertions loop over strictly distinct pairs.
- **Source:** `test_lifespan.py` (pre-fix) lines 52-58:
  `for i, lo in enumerate(spans): for hi in spans[i + 1 :]:` never reaches
  `i == j`. `lifespan.py` `__lt__` (the code under test).
- **Consequence (named mutation, per Method step 8):** mutating
  `order.index(self) < order.index(other)` to `<=` would make every `Span`
  "less than" itself, silently breaking `<=`/`>`/`>=` (derived via
  `total_ordering`) for equal spans — and the full suite would still pass.
  This is the module's one piece of nontrivial comparison logic, not an
  off-path helper, so it clears the Method step-8 bar for a real
  test-strategy gap.
- **Remedy:** add a reflexivity test: for every declared span,
  `not (span < span)` and `span <= span`.
- **Disposition: FIXED (test-only; no production bug — current logic was
  already correct, only untested).**

### F4 — Cosmetic for contest: `span_from_value` is a thin pass-through
- **Claim:** Same shape as F1 (Interface ≈ Implementation — Architectural
  Test #3), but with a real, current call site, unlike F1.
- **Source:** `lifespan.py` lines 38-39: `def span_from_value(value: str) ->
  Span: return Span(value)`. `test_lifespan.py` imports it (line 14) and
  calls it 5 times (lines 31, 37, 42, 48, 53).
- **Consequence:** Minor one-line indirection around enum value-lookup, but
  it has live callers and gives "construct a Span from a raw value" a
  stable, greppable boundary distinct from raw `Span(value)` construction —
  useful if validation/logging is ever added at that conversion point later.
- **Disposition: considered, SPT-REJECTED — see Architect phase below. Not
  fixed.**

### F5 — Cosmetic for contest, not elevated: cross-type guard in `__lt__` untested
- **Claim:** `if self.__class__ is not other.__class__: return
  NotImplemented` (lifespan.py line 30) has no test comparing a `Span`
  against a non-`Span` value.
- **Consequence:** Per Method step 8's third mutation-test branch, this is
  off-path defensive code (comparison-protocol plumbing, not a primary
  domain flow) — the rubric's own carve-out ("untested helper code or
  off-path utilities are not disqualifying") applies. Named for honesty, not
  elevated to a fix.
- **Disposition: not fixed, not required.**

## Architect phase — Simplify Pressure Test, verbatim per fix

### Fix A: delete `value_of` (addresses F1)
1. Does it fix real ambiguity? **Yes** — an exported, untested, uncalled
   function is an unresolved "does anything depend on this?" ambiguity; the
   Deletion Test resolves it (nothing depends on it).
2. Is it the smallest honest fix? **Yes** — straight deletion, no
   replacement needed anywhere since no call sites exist.
3. Does it avoid duplicate layers? **Yes** — deletion removes a layer, adds
   none.
4. Does runtime behavior remain honest? **Yes** — no observable behavior
   changes for any caller (there are none).
5. Does the product improve, measurably, and by more than what's declined?
   **Yes** — removes dead code (simplicity), and an untested unused public
   symbol was inflating the module's declared Interface surface for zero
   Leverage (API-surface-scope audit: zero cross-file/test use sites →
   should not exist).
   Structural gate: Deletion test on `value_of` passes cleanly (0 callers,
   complexity vanishes, nothing reappears). No Seam involved. No new test
   needed since nothing replaces it.
   **PASSED. Fix applied.**

### Fix B: `__lt__` reuses `SPANS` instead of rebuilding the list (addresses F2)
1. Does it fix real ambiguity? **Yes** — the docstring claims one ordered
   source of truth; the code had two independently-built ones. Named
   ambiguity: is the canonical order `SPANS` or `list(self.__class__)`?
2. Is it the smallest honest fix? **Yes** — one-line body change, a net
   deletion (`order = list(self.__class__)` removed), no new abstraction.
3. Does it avoid duplicate layers? **Yes** — removes a duplicate
   computation; adds nothing.
4. Does runtime behavior remain honest? **Yes** — `SPANS` and
   `list(self.__class__)` are built from the same enum in the same order;
   behavior is identical for every input. `self`/`other` are already
   guaranteed same-class by the preceding guard, so `SPANS` (built from the
   whole `Span` class) is a valid substitute.
5. Does the product improve, measurably, and by more than what's declined?
   **Yes** — collapses two sources of ordering truth into one (removes a
   real Locality/consistency hazard), and removes a per-comparison list
   allocation (lens-efficiency D1). Small in absolute terms (n=5) but real
   and directly contradicts the module's own stated design intent otherwise.
   Structural gate: no Module deleted, no new Seam. Existing
   `test_ordering_matches_declared_low_to_high` already exercises `<` at the
   Interface; the new reflexivity test (Fix C) exercises the same changed
   code path. No test regression risk.
   **PASSED. Fix applied.**

### Fix C: add `Span` ordering reflexivity test (addresses F3)
1. Does it fix real ambiguity? **Yes** — whether `X < X` is False and `X <=
   X` is True was unverified; a named mutation (`<` → `<=` in `__lt__`)
   would go undetected without it.
2. Is it the smallest honest fix? **Yes** — one small test function; no
   production code change required (current `__lt__` logic was already
   correct — this closes a coverage gap, not a bug).
3. Does it avoid duplicate layers? **Yes** — single test function, no new
   abstraction, no test helper scaffolding.
4. Does runtime behavior remain honest? **Yes** — test-only change.
5. Does the product improve, measurably, and by more than what's declined?
   **Yes** — closes a concretely-named mutation-blind-spot on the module's
   one nontrivial comparison routine (the same code Fix B touches), without
   inflating aggregate test count for its own sake (targeted at a specific
   named gap, per Method step 8, not a fake-clean test-count reward).
   Structural gate: no deletion, no new Seam — N/A, passes trivially. Test
   lives at the same Interface as existing tests (public `Span`/`<`
   comparisons). **PASSED. Fix applied.**

### Fix D (considered, not applied): delete or inline `span_from_value` (addresses F4)
1. Does it fix real ambiguity? **No** — there is no ambiguity; the function
   is a straightforward, correctly-behaving typed wrapper with a real,
   current call site (the bundled test suite calls it 5 times).
2. Is it the smallest honest fix? N/A given (1) fails, but for the record:
   inlining `Span(value)` at each of the 5 test call sites would be the
   mechanical alternative.
3. Does it avoid duplicate layers? N/A — this isn't a duplication question;
   `span_from_value` isn't duplicating another function in this file the
   way F2's `__lt__` was duplicating `SPANS`.
4. Does runtime behavior remain honest? **Yes** if removed, but that's not
   the failure point here.
5. Does the product improve, measurably, and by more than what's declined?
   **No** — removing a two-line typed public wrapper with a live call site
   moves no rubric dimension measurably. What's *declined* by keeping it:
   nothing real. What's *risked* by removing it: it is documented module
   scope ("Fixture-lifetime helpers used by this package's request
   objects") as a conversion boundary from raw values, and this fixture is
   an intentionally small slice of a larger package we cannot see — deleting
   documented, actively-used public API on an incomplete view of its
   consumers is exactly the asymmetric-risk case Meta-Rule 4 (preserve
   user-visible behavior) warns against. The gain (a few saved bytes) is
   smaller than the risk (breaking an unseen caller).
   Structural gate: Deletion Test is ambiguous here specifically because
   evidence is incomplete (real call site exists in the visible slice;
   docstring claims broader package usage we have no file to verify) — per
   Method Rule 1 ("inspect current code only," "do not generalize beyond
   evidence"), absence of proof of safety is not proof of safety. **Gate:
   FAILS to clear on Q5 and on evidence-sufficiency for API removal.**
   **REJECTED. Not applied — recorded per instructions rather than hidden.**

## Exact edits applied

`lifespan.py`:
- `Span.__lt__` body changed from
  `order = list(self.__class__)` / `return order.index(self) <
  order.index(other)` to `return SPANS.index(self) < SPANS.index(other)`
  (removes the duplicate list construction; Fix B).
- Deleted `def value_of(span: Span) -> str: return span.value` (Fix A).

`test_lifespan.py`:
- Added `test_ordering_is_not_reflexive()`, asserting `not (span < span)`
  and `span <= span` for every declared span value (Fix C).
- Registered the new test in `main()`.

## Final test result

```
$ python3 -m pytest -q
........                                                                [100%]
8 passed in 0.01s

$ python3 test_lifespan.py
OK: test_lifespan.py
```

Both entry points (pytest and the module's own `__main__` runner) pass, 8/8
(7 original + 1 new). No regressions. `grep -rn "value_of" . --include="*.py"`
confirms zero dangling references after deletion.

## Scorecard (post-fix)

| Dimension | Score | Note |
|---|---|---|
| ownership / state_management | 9.5 | Single-writer `Handle`, single ordered-truth `Span`/`SPANS` after F2 fix; no drift or multi-writer hazard found. |
| simplicity | 9.5 | Dead code removed (F1); duplicate computation removed (F2); one thin-but-live wrapper (`span_from_value`) reviewed and kept under SPT — not a defect. |
| concurrency | N/A | No async/threading surface in this module. |
| data_flow / seams | 9.5 | No Seam/protocol machinery exists or is warranted at this scale (Unified Seam Policy never triggers — no adapters, no I/O). |
| test_strategy | 9.5 | Reflexivity gap (F3) was the one nameable mutation on primary logic; closed. Cross-type guard (F5) remains an accepted, off-path residual per the rubric's own carve-out. |
| credibility | 9.5 | Module docstring's "one ordered enum, no per-call-site copies" claim is now actually true (F2 fix); previously it was contradicted by `__lt__`'s own body. |

## Summary

Findings raised: 5 (F1 dead code, F2 duplicate ordering computation, F3
reflexivity test gap, F4 thin-but-live wrapper — reviewed/kept, F5 untested
defensive guard — reviewed/kept).
Fixes applied: 3 (delete `value_of`; `__lt__` reuses `SPANS`; add
reflexivity test).
Fixes SPT-rejected: 1 (deleting/inlining `span_from_value` — real call site,
no measurable gain, asymmetric risk against an unseen package boundary).
Final `pytest -q`: **8 passed**, no failures, no regressions.
