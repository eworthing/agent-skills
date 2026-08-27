# Architectural Refactor Run Report — `clustered.py`

Method: `contest-refactor/references/method.md` (Meta-Rules, Method steps 1-10, SPT), `architecture-rubric.md`, `lens-generic.md` (Python).
Target: `clustered.py` (92 lines), `test_clustered.py` (46 lines), `CHANGES.md`. Baseline `python3 -m pytest -q`: **2 passed**.

---

## Critic Phase

### Authority Map (Method step 2)

| Concern | Owner | Writers | Readers | Notes |
|---|---|---|---|---|
| `Clustered._records`, `_key` | `Clustered` instance | `__init__` only | `_buckets()` | write-once, no drift risk |
| `Lane.key`/`.values`, `Panel.key`/`.columns` | the group instance | `__init__` only | callers, `scatter()` | write-once |
| `<group>.label` | caller-external | `apply_general` (monkey-patch) | `scatter()` fallback branch | **second, later writer on a field the group classes never declare** — see F1 |

### F1 — Serious deduction (`data_flow`): Panel legends silently broken, contradicting the module's own contract

- **Claim:** `apply_plot`'s docstring and the module docstring both assert plotting "no longer depend[s] on a side effect of the aggregation path" and that `apply_plot` "forwards each group's key to the callback explicitly." That is true only for `Lane`. For any other group shape — concretely `Panel`, the library's other public group type — no key is forwarded, and `plot_legend_labels` silently returns `None` for every entry.
- **Source:** `clustered.py:70-74` (pre-fix):
  ```
  for group in groups:
      if isinstance(group, Lane):
          results.append(fn(group, key=group.key))
      else:
          results.append(fn(group))
  ```
  `clustered.py:83-85`, `scatter()`: when `key is None`, falls back to `getattr(group, "label", None)` — and nothing in the plotting path ever sets `.label` on a `Panel`. Confirmed by direct repro before any edit:
  ```
  panels = Clustered(RECORDS, key=...).panels(["x"])
  plot_legend_labels(panels)  # -> [None, None]
  ```
  Only calling the *other*, supposedly-unrelated `apply_general` first (which mutates `.label` as a side effect) makes it work — i.e. the exact coupling `CHANGES.md` claims was removed still exists, just for the other group shape.
- **Consequence:** breaks the primary documented feature (plotting) for one of the library's two public group shapes, silently (no exception, no warning — just wrong/empty legends). It also falsifies the module's and function's own docstrings, and it is the shape of bug the Step-8 "mutation-test mental model" specifically asks for: flip `isinstance(group, Lane)` to always-true and no test caught it, because `panels()` had zero test coverage (see F2).
- **Remedy:** stop gating key-forwarding on `Lane`-only `isinstance`; forward `.key` for any group that has one (both `Lane` and `Panel` set it in `__init__`), so the contract the docstrings already claim is actually true.

### F2 — Noticeable weakness (`test_strategy`): the exact path that broke had no test, and `apply_general`'s mutation contract had none either

- **Claim:** `test_clustered.py` only exercised `Clustered.lanes(...)` and `plot_legend_labels` on `Lane` groups. `Clustered.panels(...)` (half the public factory surface) and `apply_general` (the other half of the plotting/aggregation split `CHANGES.md` describes) had zero test coverage.
- **Source:** `test_clustered.py:16-34` (pre-fix) — two tests total, both keyed off `.lanes("x")`; no import or call of `apply_general`; no call of `.panels(...)`.
- **Consequence:** this is precisely why F1 shipped invisibly — per Method step 8's mutation-test mental model, the `isinstance(group, Lane)` check is a primary-flow branch with no test on its `else` arm, and `apply_general`'s only behavior (mutate `.label`, call `fn`) had no caller-side assertion anywhere in the suite.
- **Remedy:** add a `panels()` legend-labels test (which fails pre-F1-fix, passes post-fix — real regression coverage, not decorative) and a direct `apply_general` contract test.

No other findings. No concurrency, no I/O/external calls (lens-generic.md Failure modes & observability section: not applicable — no silent-swallow, retry, or telemetry surface exists in this file), no multi-writer hazard beyond the one already covered by F1, no naming-cluster or protocol-soup smell (no protocols/adapters here at all — `Lane`/`Panel` are plain value objects, not Seams), dict iteration order is insertion-order-stable in CPython 3.7+ so `_buckets()` grouping order is deterministic (no "unstable shaped output" finding).

---

## Architect Phase — Simplify Pressure Test

### Fix 1 (applied): forward `.key` uniformly in `apply_plot`, not just for `Lane`

1. **Does it fix real ambiguity?** Yes — it closes the gap between the docstring's claim and actual behavior for `Panel` groups; the ambiguity (which groups get their key forwarded) had a wrong, silent answer.
2. **Is it the smallest honest fix?** Yes — one line changes (`getattr(group, "key", None)` replacing the `isinstance`/branch), no new type, no new parameter, no new class.
3. **Does it avoid duplicate layers?** Yes — it *removes* a branch rather than adding one; `Lane` and `Panel` are handled by the same code path instead of two.
4. **Does runtime behavior remain honest?** Yes — a group that has no `.key` still gets `key=None` exactly as before (same fallback as the old `Lane`-only branch's `else` arm); groups that do have `.key` (Lane, Panel, any future group shape) now get it, matching the docstring's actual promise.
5. **Does the product improve — measurably, and by more than the item you are declining?** Yes — it fixes a silent correctness bug (`None` legends) on half the library's public group-factory surface, for the library's own headline feature (plotting). Nothing else in this review competes with that.
- **Structural gate:** no Seam added or removed, no Module deleted, nothing to check against Unified Seam Policy. Tests were added at the same public-function Interface (`plot_legend_labels`) the fix touches, satisfying "Replace, don't layer."

**PASSED.** Applied.

### Fix 2 (applied): add `panels()` legend test + `apply_general` contract test

1. **Does it fix real ambiguity?** Yes — F2's actual ambiguity was "is this path exercised at all"; now it is, on both the buggy path (would have failed pre-Fix-1) and the previously-silent `apply_general` mutation.
2. **Is it the smallest honest fix?** Yes — two small `assert`-based test functions matching the existing file's own style (no framework, no fixtures beyond the file's existing `RECORDS` constant), wired into the existing `main()`.
3. **Does it avoid duplicate layers?** Yes — extends the existing flat test-function convention; no new test infra.
4. **Does runtime behavior remain honest?** N/A to production runtime — test-only change; it makes the existing (now-honest) runtime behavior verifiable.
5. **Does the product improve — measurably, and by more than the item you are declining?** Yes — turns Fix 1 from an unverified hand-fix into a regression-guarded one, and gives `apply_general`'s only documented contract (pin `.label`, call `fn`) its first executable proof.
- **Structural gate:** tests live at the same Interfaces (`plot_legend_labels`, `apply_general`) being changed/audited — satisfies "Tests after the refactor live at the new Interface."

**PASSED.** Applied.

### Fix 3 (considered, rejected): delete `apply_general` as dead code

`apply_general` has no caller anywhere in this repo (only `apply_plot` is called, from `plot_legend_labels`); a first pass could read that as dead code to delete.

1. **Does it fix real ambiguity?** No — there is no proven ambiguity to fix. `apply_general`'s own docstring and `CHANGES.md` both assert it is "still used for aggregation," which this repo snapshot (a library module plus its bundled test file, not a full application) cannot confirm or deny — there may be external callers outside this checkout.
2. **Is it the smallest honest fix?** N/A — fails at Q1.
3. **Does it avoid duplicate layers?** N/A.
4. **Does runtime behavior remain honest?** Deleting a public function *is* a user-visible behavior change for a library (Meta-Rule 4: fixes must preserve user-visible behavior) — the opposite of what a "smallest honest fix" should do here without proof of dead-ness beyond this snapshot.
5. **Does the product improve?** No net gain identified beyond the item already claimed by Fix 2 (closing its test gap), which achieves the same regression-safety goal without the deletion risk.
- **Structural gate:** Deletion test cannot be run honestly — "imagine deleting the Module" requires seeing all callers, and this review has no visibility past this checkout's boundary.

**REJECTED** — downgraded to Fix 2 (test the contract instead of removing the function). Recorded per instructions: a fix SPT kills is a legitimate, reportable outcome, not a gap in the review.

---

## Execution Phase

**Edits applied** (both in `/private/tmp/claude-502/.../scratchpad/d5/`):

- `clustered.py` — `apply_plot`: replaced the `isinstance(group, Lane)` branch with unconditional `fn(group, key=getattr(group, "key", None))`; updated its docstring to state the real (now-uniform) contract.
- `test_clustered.py` — added `test_plot_legend_labels_for_panels` and `test_apply_general_pins_label_and_calls_fn`; wired both into `main()`; added `apply_general` to the module's import line.

`CHANGES.md` left untouched — no scope to update it, and the task did not ask for changelog maintenance; flagging only: it now slightly understates the fix (still describes only the Lane-side history). Not treated as a finding since it's documentation, not code, and out of the reviewed dimensions.

**Final `pytest -q`:** `4 passed in 0.01s` (up from the baseline's 2). **Final standalone runner** (`python3 test_clustered.py`): `OK: test_clustered.py`, exit 0.

---

## Final Scorecard

| Dimension | Score /10 | Basis |
|---|---|---|
| Ownership | 9 | Every mutable field has exactly one clear owner; the one cross-object mutation (`apply_general` pinning `.label`) is now test-covered instead of merely asserted in a docstring. |
| State management | 9 | Write-once construction throughout; no drift risk once F1 removed the accidental Lane-only special case. |
| Data flow | 9 (was ~6 pre-fix) | F1 was the one real defect: a documented contract silently false for half the public surface. Fixed and regression-tested. |
| Concurrency | N/A | No concurrency in this file. |
| Simplicity | 9 | No costume layers, no protocol soup, no unjustified seams; `Lane`/`Panel` are plain value objects earning their keep (deletion test: removing either reintroduces per-caller reshaping logic at every call site). |
| Test strategy | 8 (was ~5 pre-fix) | Both public factory shapes (`lanes`, `panels`) and both plotting/aggregation entry points now have direct coverage. Not a 9+: `Clustered.panels()`'s multi-column values themselves (not just legend keys) still lack a dedicated assertion, a residual left for the next pass rather than expanded here (Q5 leverage was in the legend-label bug, not this). |
| Credibility | 8 | Docstrings now match behavior; the one remaining soft spot is `CHANGES.md` not mentioning this fix (documentation, not code, left out of scope per Execution phase framing above). |

---

## Summary

**Findings raised:** 2 (F1 Serious — Panel legends silently broken; F2 Noticeable — missing test coverage on the exact path that broke).
**Fixes applied:** 2 (uniform key-forwarding in `apply_plot`; regression tests for panels legends + `apply_general` contract).
**Fixes SPT-rejected:** 1 (deleting `apply_general` as apparently-dead code — rejected on Q1/Q4/structural gate, no proof of dead-ness beyond this checkout, downgraded to testing its contract instead).
**Pytest:** 4 passed (baseline was 2 passed; both original tests still pass unchanged).
