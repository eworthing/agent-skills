# Architecture Review — `lifespan.py` / `test_lifespan.py`

Target: `/private/tmp/claude-502/-Users-Shared-git-agent-skills/051852b6-ffb7-44f6-9d95-881320b484b5/scratchpad/spt-q3/v2-pyt`
Protocol: `method.md`, `architecture-rubric.md` (+ `architecture-rubric-scoring.md` for the nine score anchors it delegates to), `lens-generic.md` (Python stack), from `.../scratchpad/spt-q3/prose/`.
Baseline: `python3 -m pytest -q` → 7 passed (confirmed before any edit).

This is a two-file, single-purpose value module (an ordered `Span` enum + a `Handle` compat shim). No I/O, no concurrency, no persistence — most of the rubric's severity anchors and the lens's concurrency/observability sections are not reachable here; that absence is recorded, not silently skipped.

---

## Findings (Critic phase)

### F1 — `value_of()` is dead code (zero call sites anywhere in the package)

- **Claim:** `value_of` is a one-line pass-through wrapper around `Span.value` with no caller anywhere in the package, including its own test suite.
- **Source:** `lifespan.py:43-44` (pre-fix):
  ```
  def value_of(span: Span) -> str:
      return span.value
  ```
  Evidence of zero callers: `grep -rn "value_of" v2-pyt --include=*.py` returns only the definition itself — no hit in `test_lifespan.py` or anywhere else in `lifespan.py`.
- **Consequence:** Fails the Deletion Test (`architecture-rubric.md § Architectural Tests #1`): deleting it, no complexity reappears anywhere. It widens the module's public surface with a function nothing exercises, which is exactly the "API-surface scope audit" smell (`method.md` Step 6) — a reader has no way to tell it isn't load-bearing.
- **Severity:** Cosmetic for contest (real, but a single unused one-liner with zero runtime risk).

### F2 — `span_from_value()` is a thin wrapper used only by the test suite (scope-limited)

- **Claim:** `span_from_value(value) = Span(value)` adds no behavior beyond the Enum's own constructor; its only call sites in this package are inside `test_lifespan.py`.
- **Source:** `lifespan.py:39-40` (pre-fix, now 38-39):
  ```
  def span_from_value(value: str) -> Span:
      return Span(value)
  ```
  Call sites: `test_lifespan.py:31,37,42,48,53` (5 occurrences), all inside the test file. `grep` across the package finds no production call site.
- **Consequence:** Candidate pass-through wrapper per the Deletion Test. **Labeled scope-limited** (per `method.md` § The Evidence Chain: "If scope is weak, label the claim"): the module docstring says it is "used by this package's request objects," which live outside this probe's two files, so I cannot prove or disprove external callers. Unlike F1, the evidence here does not clear the bar for "zero callers anywhere."
- **Severity:** Cosmetic for contest.

### F3 — `Span.__lt__` recomputes the same ordered list `SPANS` already holds

- **Claim:** `__lt__` rebuilds `list(self.__class__)` on every single comparison instead of reusing the module-level `SPANS` list that already exists for exactly this purpose (and that `next_up` already uses). Two code paths derive "the declared order of spans" instead of one.
- **Source:** `lifespan.py:29-33` (pre-fix):
  ```
  def __lt__(self, other: Span) -> bool:
      if self.__class__ is not other.__class__:
          return NotImplemented
      order = list(self.__class__)
      return order.index(self) < order.index(other)
  ```
  vs. `lifespan.py:36`: `SPANS = list(Span)`, and `lifespan.py:54`: `idx = SPANS.index(span)` inside `next_up`.
- **Consequence:** Matches the spirit of `lens-efficiency.md` D1 (recomputed derived value, no single evaluation owner) — trivial cost at n=5, but it directly contradicts the module's own stated design rationale in its docstring, `lifespan.py:6-7`: *"now backed by one ordered enum instead of a mapping copied at each call site"* — `__lt__` still copies a fresh list at each call site. That is a credibility/documentation-consistency deduction (`method.md` Meta-Rule 6), not a performance one.
- **Severity:** Cosmetic for contest.

### F4 — `next_up`'s middle-transition successor values are untested (mutation-test gap on a documented primary flow)

- **Claim:** The module docstring names `higher` and `next_up` as "the two operations everything else needs" (`lifespan.py:5-6`) — i.e., `next_up` is explicitly a primary flow, not an off-path helper. Its existing tests only assert (a) the top span clamps to itself and (b) the bottom span's successor is *not equal* to itself. No test asserts the *actual* successor value for any transition (`step`→`suite`, `suite`→`file`, `file`→`batch`, `batch`→`run`).
- **Source:** `lifespan.py:52-55` (pre-fix):
  ```
  def next_up(span: Span) -> Span:
      idx = SPANS.index(span)
      return span if idx == len(SPANS) - 1 else SPANS[idx + 1]
  ```
  Tests, `test_lifespan.py:19-26` (pre-fix):
  ```
  def test_next_up_clamps_at_the_top() -> None:
      top = SPANS[-1]
      assert next_up(top) == top, next_up(top)

  def test_next_up_moves_forward() -> None:
      first = SPANS[0]
      assert next_up(first) != first
  ```
  **Named mutation** (per `method.md` Step 8's mutation-test mental model — swapped-argument/direction class): `SPANS[idx + 1]` → `SPANS[idx - 1]` at `lifespan.py:55`. I verified this mechanically before writing the finding: both existing tests pass unchanged under this mutation (`next_up(top)` still clamps via the `idx == len(SPANS)-1` branch; `next_up(first)` returns `SPANS[-1]` = `Run`, which is `!= Step` so the "moves forward" test's inequality check is satisfied even though the direction is completely reversed). Verified interactively:
  ```
  OLD test_next_up_clamps_at_the_top passes? True
  OLD test_next_up_moves_forward passes?      True
  mutated_next_up(first) actually returns: Span.Run   # should be Suite — going backward
  ```
- **Consequence:** Per `method.md` Step 8: a nameable mutation on a primary flow the existing suite does not catch is a Noticeable-or-worse missing-test gap, not a Cosmetic one — the carve-out for off-path helpers does not apply here because the module's own docstring designates `next_up` as central.
- **Severity:** Noticeable weakness.

**No Serious-or-worse or Likely-disqualifier findings.** This module has a single mutable-state owner (`Span`/`SPANS`, immutable after class construction), no multi-writer state, no concurrency surface, no persistence/network boundary, and the `Handle` compat-property design (`lifespan.py:58-67`, documented in `CHANGES.md`) is a deliberate, already-tested behavior-preservation shim — not a finding.

---

## Simplify Pressure Test (Architect phase)

### Fix A — Delete `value_of()` (addresses F1)

1. Does it fix real ambiguity? Yes — resolves "is this load-bearing?" with the strongest possible evidence (zero callers anywhere in the package).
2. Is it the smallest honest fix? Yes — straight deletion, nothing to replace since nothing calls it.
3. Does it avoid duplicate layers (owner count)? N/A/passes trivially — no ownership question is being split or merged; owner count is 0 before and after.
4. Does runtime behavior remain honest? Yes — removing genuinely-unreferenced code changes no observable behavior.
5. Does the product improve, measurably, by more than what's declined? Yes — the `simplicity` dimension's public surface shrinks by one unused function at zero cost/risk; nothing more valuable is being displaced.
   Structural gate: Deletion test passes by construction (no caller anywhere); no Seam involved; no test currently exercises `value_of`, so no test needs to move.

**Verdict: PASSED.**

### Fix B — Delete `span_from_value()`, inline `Span(value)` at its 5 test call sites (addresses F2)

1. Does it fix real ambiguity? Weak/marginal — the "ambiguity" is whether the wrapper earns its keep, and removal does resolve that, but only within this probe's visibility.
2. Is it the smallest honest fix? Mechanically yes (a rename), but see Q5.
3. Owner count? Passes in isolation.
4. Runtime behavior honest? Yes, mechanically equivalent.
5. **Does the product improve, measurably, by more than what's declined? No.** Two independent reasons:
   - The gain is not nameable beyond "it is tidier," which `method.md` Q5 explicitly disqualifies as a product improvement ("it is tidier is not a product improvement").
   - The finding itself (F2) is labeled scope-limited: the module docstring states this package serves "this package's request objects," which are not part of the two files in this probe. `CHANGES.md` documents that this codebase's own convention is to preserve public-name compatibility for callers it cannot see (`Handle.span`'s whole reason for existing). Removing a public, non-underscore-prefixed function on the strength of "only the local test file calls it" risks an unverifiable break for hidden external callers, for a purely cosmetic gain.

**Verdict: REJECTED at Q5.** Recorded per the task's instruction that a fix the SPT kills is a valuable result: `span_from_value` is left in place. This is different from F1/Fix A, where the deletion-test evidence was airtight (truly zero callers anywhere); here it is not.

### Fix C — `Span.__lt__` reuses module-level `SPANS` instead of rebuilding `list(self.__class__)` (addresses F3)

1. Does it fix real ambiguity? Yes — collapses two code paths that separately derive "the declared span order" into one.
2. Is it the smallest honest fix? Yes — a one-line change (`SPANS.index(self) < SPANS.index(other)`), no new structure.
3. Owner count? Passes — consolidates from 2 derivation sites (`SPANS` at module scope, `order = list(self.__class__)` inside `__lt__`) to 1 (`SPANS` alone), directly satisfying Q3 ("more than one owner of the same question... is a no" — this fix removes the second owner rather than adding one).
4. Runtime behavior honest? Yes — `SPANS` and `list(self.__class__)` are always identical (Enum member order is fixed at class-definition time), so this is behavior-preserving by construction.
5. Does the product improve, measurably? Yes, and unlike Fix B this is not merely "tidier": it makes the code match a specific claim the module's own docstring makes about itself (`lifespan.py:6-7`, "backed by one ordered enum instead of a mapping copied at each call site") which was false of `__lt__` before this fix. That is a concrete `credibility`/`simplicity` correction, not a stylistic one, at zero behavioral risk.
   Structural gate: no Module/Seam created or removed; existing tests (`.span` compat, ordering, dict-key, string-format) are unaffected since behavior is identical.

**Verdict: PASSED.**

### Fix D — Add a test asserting `next_up`'s exact successor across every transition (addresses F4)

1. Does it fix real ambiguity? Yes — resolves whether the module's own stated primary flow (`next_up`) is actually verified beyond "not equal to itself."
2. Is it the smallest honest fix? Yes — one small loop mirroring the file's existing test style (`test_ordering_matches_declared_low_to_high` already iterates `SPANS`), no new framework or fixture machinery.
3. Owner count? N/A — adding a test does not create or merge an ownership question.
4. Runtime behavior honest? Yes — test-only change, no production code touched.
5. Does the product improve, measurably? Yes — closes the named mutation gap (`SPANS[idx + 1]` → `SPANS[idx - 1]`) on the module's own documented primary flow; verified mechanically (see F4) that the old suite missed it and the new test catches it.
   Structural gate: tests already live at the Interface (`next_up(span) -> Span`); nothing to replace.

**Verdict: PASSED.**

---

## Fixes rejected by SPT

- **Fix B** (delete `span_from_value`, addressing F2) — **REJECTED at Q5**: the only gain nameable is "it is tidier," which is explicitly disqualified, and it carries an unverifiable compatibility risk for external callers the docstring says exist but this probe cannot see. `span_from_value` is left in the code unchanged.

No other proposed fix was rejected — Fixes A, C, D all passed.

---

## Edits applied

**`lifespan.py`**

1. Removed the dead `value_of()` function entirely (was lines 43-44).
2. Changed `Span.__lt__` from rebuilding its own list every call to reusing the existing `SPANS` list:
   ```diff
   -        order = list(self.__class__)
   -        return order.index(self) < order.index(other)
   +        return SPANS.index(self) < SPANS.index(other)
   ```

**`test_lifespan.py`**

3. Added `test_next_up_returns_immediate_successor()`, asserting the exact successor for every non-top span, and registered it in `main()`:
   ```python
   def test_next_up_returns_immediate_successor() -> None:
       for i, span in enumerate(SPANS[:-1]):
           assert next_up(span) == SPANS[i + 1], (span, next_up(span))
   ```

`span_from_value()` was left untouched (Fix B rejected). `CHANGES.md` was not modified — none of these edits change externally observable behavior, so there is nothing to log there.

## Final test result

```
$ python3 -m pytest -q
........                                                                 [100%]
8 passed in 0.01s

$ python3 test_lifespan.py
OK: test_lifespan.py
```

8 passed (7 original + 1 new), both the pytest entry point and the bundled `python3 test_lifespan.py -- ` self-test succeed.

---

## Final scorecard

| Dimension | Score | Residual / rationale |
|---|---|---|
| Architecture quality | 9.5 | 9-anchor met (no costume layers, no repository theater — no protocols exist at all; `Handle`'s compat shim is deliberate and documented). Residual: `span_from_value` (F2) remains an unproven-but-plausible thin wrapper — **accepted**, per Fix B's SPT rejection, pending visibility into external callers. |
| State management & runtime ownership | 10 | Single owner (`Span`/`SPANS`, immutable after class construction); `Handle._span` has exactly one writer (`__init__`); no hidden state machines. |
| Concurrency & runtime safety | 10 | Not applicable — no async, threads, or shared mutable runtime state in this module. Nothing in `lens-generic.md`'s concurrency section is reachable. |
| Test strategy & regression resistance | 9.5 (was 8 pre-fix) | Pre-fix: F4's mutation-test gap on `next_up`, a documented primary flow, capped this below 9. Post-fix: gap closed and verified by direct experiment (mutation caught). Residual: `Handle.target`'s consumer behavior is exercised only via identity check (`is sentinel`), not by any real "requester" object shape — accepted, since `target: object` is intentionally untyped and this package's request-object consumers aren't in scope. |
| Overall implementation credibility | 9.5 (was 8.5 pre-fix) | Pre-fix: the docstring's "one ordered enum instead of a mapping copied at each call site" claim was contradicted by `__lt__` (F3). Post-fix: claim and code agree. Residual: F2's scope-limited status. |
| Domain modeling | 10 | `Span` is a genuinely ordered discriminated enum; `Handle`'s public `str`-typed `.span` vs. private `Span`-typed `_span` is a documented, tested, intentional compatibility split — not anemia. |
| Data flow & dependency design | 10 | Single file, zero external dependencies, no ambient/global mutable state beyond the immutable `SPANS` list. |
| Framework / platform best practices (Python) | 10 | Idiomatic `enum.Enum` + `functools.total_ordering` + `@property`; no fought-against stdlib idioms. |
| Code simplicity & clarity | 9.5 (was 8.5 pre-fix) | Pre-fix: F1 (dead code) + F3 (duplicate derivation) both live here. Post-fix: both closed. Residual: F2 (`span_from_value`), same scope-limited rationale as above — **accepted**, not queued, since removing it was actively tested by SPT and rejected on evidence, not deferred for lack of time. |

No dimension reaches a bare 10 with zero residual except where explicitly noted (concurrency/data-flow/domain/framework have no nameable residual and are scored 10 outright per the terminal-normalization rule). The one HALT-relevant residual across dimensions — `span_from_value`'s unverifiable external-caller status — is the same underlying fact each time, disposed as **accepted** rather than queued, because the alternative (removing it) was concretely tried and rejected by SPT rather than left for a future loop.
