# Architectural Refactor Review — v2-d1a

Target: `settings.py` (34 lines) + `test_settings.py` (38 lines), a four-layer
settings-resolution module (env > project > user > defaults). Lens: generic
(`lens-generic.md`), stack-universal Python. Method: `method.md` Critic/SPT
protocol. Rubric: `architecture-rubric.md` + `architecture-rubric-scoring.md`.

Baseline: `python3 -m pytest -q` → **5 passed**.

---

## Critic Phase — Findings

### F1 — Serious deduction: `describe_source` disagrees with `effective_value` about which layer "carries" a key

- **Claim:** The module docstring (lines 3–7) declares one contract for the
  whole module: *"A layer carries a key when the key is present, whatever
  the value — an explicitly empty string is a deliberate override, not an
  absence."* `effective_value` implements that contract (`if key in env:
  ...`). `describe_source` implements a **different** contract (`if
  env.get(key): ...`), which treats an explicitly-set empty string as
  absent. Two code paths answer the same question — "which layer wins?" —
  with different, silently divergent logic.
- **Source:** `settings.py:18` (`if key in env:`) vs. `settings.py:28`
  (`if env.get(key):`) — same pattern repeated at lines 20/30 (project) and
  22/32 (user). Confirmed with a live repro before editing:
  ```
  env = {"retries": ""}; defaults = {"retries": "3"}
  effective_value(...) -> ''        # correct per docstring: env carries the key
  describe_source(...) -> 'default' # wrong: claims no layer carries it
  ```
- **Consequence:** This is a demonstrated drift bug (Q3's own bar: "a
  demonstrated disagreement between them is a bug — drift with a repro"),
  not a hypothetical. `describe_source` is documented as backing the
  `--explain` command (docstring lines 9–11) — a user asking "why is
  `retries` set to `''`?" would be told `"default"`, contradicting the
  actual effective value and the module's own stated contract. It is an
  ownership hazard over "which layer wins," and a credibility leak (code
  contradicts its own docstring). Primarily weakens **Data flow and
  dependency design** and **Overall implementation credibility**;
  secondarily **Domain modeling** (the "carries a key" domain rule isn't
  uniformly enforced) and **Code simplicity/clarity** (duplicated
  four-branch traversal a reader must manually cross-check for agreement).
- **Remedy:** Collapse the two independent traversals into one shared
  decision point that both public functions consume, so there is exactly
  one owner of "which layer carries this key."

### F2 — Noticeable weakness: no test distinguishes project-vs-user precedence

- **Claim:** Method Step 8's mutation-test mental model: name one
  source-level mutation the current suite would not catch. Swapping the
  order of the `project`/`user` checks in `effective_value` (and the
  matching pair in `describe_source`) is undetected by any existing test.
- **Source:** `test_settings.py` — `test_project_used_when_no_env` (line
  17-18) sets `project` only (`user` defaults to `{}` via `_call`);
  `test_source_reports_user` (line 30-31) sets `user` only. No test sets
  **both** `project` and `user` for the same key to prove `project` wins.
  Verified: reordering the `project`/`user` branches in the pre-fix
  `settings.py` (lines 20-23 and 30-32) still passes all 5 original tests.
- **Consequence:** This module's entire behavior *is* the four-layer
  precedence order — there is no other flow to be "off-path" from, so per
  Step 8's own carve-out this lands on the primary flow, not an excluded
  helper. An undetected precedence-order regression here is a real
  regression-resistance gap. Weakens **Test strategy and regression
  resistance**.
- **Remedy:** Add a direct test, at the public Interface, asserting
  `project` beats `user` for both `effective_value` and `describe_source`.

### F3 — Cosmetic for contest: `ORDER` constant declared but never read

- **Claim:** `ORDER = ("env", "project", "user")` (line 14) is dead — no
  other line in the file or test suite references it.
- **Source:** `grep -rn "ORDER" v2-d1a/*.py` → only the declaration at
  `settings.py:14`.
- **Consequence:** Minor — a reader has to notice the constant is inert.
  It also reads as an authorial hint that the layer order was meant to
  drive both functions from one place, which F1's fix now does. Weakens
  **Code simplicity and clarity** only marginally; not independently
  worth a dedicated edit.
- **Remedy:** Folded into F1's fix — `ORDER` now drives `_resolve`'s
  traversal instead of sitting unused. No separate SPT run; see F1.

No findings on: architecture/module graph (single flat module, no seams,
no costume layers, no repository theater/protocol soup — nothing to flag
at this scope); state ownership (no mutable state — all inputs are
caller-supplied read-only dicts); concurrency (none present); framework
idioms (plain stdlib Python, nothing to fault); doc-rot grep
(`LEGACY|TEMPORARY|DEPRECATED|...`) — zero hits.

---

## Architect Phase — Simplify Pressure Test

### Fix 1 (for F1 + F3): extract a single `_resolve(key, env, project, user)` owner

Proposed diff: replace the two independent four-branch traversals with one
private helper returning `(layer_name, value_or_MISSING)`, keyed off
`ORDER`; `effective_value` and `describe_source` each become a thin
projection of that one result.

1. **Does it fix real ambiguity?** Yes. The ambiguity was "does an
   env/project/user layer carrying an explicit falsy value (e.g. `""`)
   count as carrying the key" — the two functions answered differently.
   The fix makes both read the same decision, matching the documented
   contract (presence, not truthiness).
2. **Is it the smallest honest fix?** Considered the smaller alternative
   of just changing `describe_source`'s three `.get(key)` truthy checks
   to `key in layer` checks (a 3-line patch, no extraction). Rejected:
   that patch fixes today's *symptom* but leaves two independently
   hand-written traversals of the same three layers standing — nothing
   stops them from drifting again on the next edit (e.g. adding a fourth
   layer would require remembering to update both). The smallest fix that
   is also *honest under Q3* is the one-owner extraction. **PASSED** —
   ~15 line diff, no new files, no new public surface.
3. **Does it avoid duplicate layers? (owner count)** The question is
   "which layer carries key K?" Before the fix: 2 owners (the two
   traversals), proven to disagree by the repro above. After the fix: 1
   owner (`_resolve`); `effective_value` and `describe_source` only
   format its result differently. **PASSED** — owner count 1.
4. **Does runtime behavior remain honest?** Yes for the documented
   contract; the one behavior change is fixing the demonstrated
   contradiction, not hiding it — `describe_source` now reports the
   layer that `effective_value` actually reads from. No suppression, no
   `type: ignore`-style hiding. **PASSED.**
5. **Does the product improve — measurably, and by more than the item
   declined?** Nothing was declined ahead of this fix (F1 is the first
   and highest-priority finding). Gain is concrete and named: closes a
   demonstrated contract-violation with a reproducible repro, on the
   entirety of this module's logic (there is no other code in scope this
   would be traded against). Moves **Data flow and dependency design**
   and **Overall implementation credibility** off their residual-blocking
   defect. **PASSED.**

**Structural gate:**
- Friction proven — yes, via the live repro (not hypothetical); Q3's own
  bar for consolidation.
- Deletion test for any Module being removed — N/A, no Module/file
  removed, only an internal helper extracted within the same file.
- Unified Seam Policy for any new Seam — N/A, `_resolve` is a private
  in-module helper, not an externally-consumed Interface/Adapter; no new
  Seam is being justified.
- Tests after refactor live at the new Interface — yes; the public
  Interface (`effective_value`, `describe_source`) is unchanged, so the
  existing test file continues to test at the correct surface; no test
  needed to move.

**Verdict: PASSED.** Applied as written in Fix 1 above.

### Fix 2 (for F2): add `test_project_beats_user` at the public Interface

1. **Does it fix real ambiguity?** It doesn't touch production code — it
   closes a coverage gap where a real, source-level mutation (swapping
   the project/user check order) would go undetected. Yes, this is a
   genuine ambiguity: "is precedence actually enforced, or just assumed?"
2. **Is it the smallest honest fix?** Yes — one new test function
   asserting both public functions, no fixtures, no framework, reusing
   the existing `_call` helper. Nothing smaller closes the named
   mutation.
3. **Does it avoid duplicate layers?** N/A/yes — a test addition doesn't
   introduce a second code-path owner; it only observes the single
   owner (`_resolve` after Fix 1).
4. **Does runtime behavior remain honest?** Yes — test-only change, zero
   production behavior change.
5. **Does the product improve — measurably, and by more than the item
   declined?** Yes, and nameable: closes the exact mutation-test gap
   identified in F2 on the module's only (hence primary) flow, moving
   **Test strategy and regression resistance** off its residual. Nothing
   of comparable value was declined to do this.

**Structural gate:** Friction proven (named, source-backed mutation, not
hypothetical) · Deletion test N/A (no Module removed) · Seam Policy N/A
(no Seam) · Tests live at the Interface — yes, added directly against
`settings.effective_value` / `settings.describe_source`, the same public
Interface every other test in the file already uses.

**Verdict: PASSED.** Applied — folded the F1-regression check
(`test_empty_string_is_a_deliberate_override`, proving the F1 repro is now
fixed) into the same test-file edit, since it is the direct regression
test for Fix 1 and shares the same SPT reasoning (smallest honest,
single-owner, honest behavior, measurable gain, on the primary flow).

### Fixes SPT rejected

**None.** Every fix proposed above passed SPT as designed. The rejected
*alternative* under Fix 1, Q2 (patch `describe_source`'s truthy checks
in place, without extracting a shared owner) was discarded before being
written as a candidate fix — it fails Q3 (leaves two owners standing) —
and is recorded above as the considered-and-declined smaller diff, not as
a separately-applied-then-reverted fix.

No fix was proposed for F3 independently; it is fully resolved as a
byproduct of Fix 1 (`ORDER` now drives `_resolve`'s traversal), so it was
never run through SPT as its own item.

---

## Execution Phase — Edits Applied

**`settings.py`** — replaced the two independent four-branch traversals
with one shared `_resolve` helper driven by `ORDER`:

```python
ORDER = ("env", "project", "user")

_MISSING = object()


def _resolve(key, env, project, user):
    """Return (layer_name, value) for the first layer in ORDER carrying key.

    "Carries" means the key is present, per the module contract above: an
    explicit empty string is a deliberate override, not an absence. Both
    public functions below resolve through this one check so they cannot
    disagree about which layer wins.
    """
    for name, layer in zip(ORDER, (env, project, user)):
        if key in layer:
            return name, layer[key]
    return None, _MISSING


def effective_value(key, env, project, user, defaults):
    _, value = _resolve(key, env, project, user)
    if value is _MISSING:
        return defaults.get(key)
    return value


def describe_source(key, env, project, user, defaults):
    name, _ = _resolve(key, env, project, user)
    return name or "default"
```

Public signatures of `effective_value` and `describe_source` are
unchanged (same params, same call sites work unmodified).

**`test_settings.py`** — added two tests:

```python
def test_empty_string_is_a_deliberate_override():
    assert _call(settings.effective_value, "mode", env={"mode": ""}) == ""
    assert _call(settings.describe_source, "mode", env={"mode": ""}) == "env"


def test_project_beats_user():
    assert (
        _call(settings.effective_value, "retries", project={"retries": "5"}, user={"retries": "1"})
        == "5"
    )
    assert (
        _call(settings.describe_source, "retries", project={"retries": "5"}, user={"retries": "1"})
        == "project"
    )
```

**Final `python3 -m pytest -q` result: 7 passed** (5 original + 2 new;
none modified, none removed).

---

## Final Scorecard

| Dimension | Pre-fix | Post-fix | Residual after fix |
|---|---|---|---|
| Architecture quality | 9 | 9.5 | Accepted — single flat module, appropriately unadorned for its scope; no seam/costume/theater to name. |
| State management and runtime ownership | 10 | 10 | None — no mutable state exists in this module (pure functions over caller-supplied read-only dicts). |
| Concurrency and runtime safety | 10 | 10 | None — no async/concurrency surface in scope. |
| Test strategy and regression resistance | 7 (F2) | 9.5 | Accepted — precedence and the empty-string-override contract are now directly asserted at the public Interface; no further nameable mutation on this flow. |
| Overall implementation credibility | 6 (F1) | 9.5 | Accepted — the docstring's "carries a key" contract is now enforced by one code path instead of contradicted by a second; nothing left that the docstring claims and the code doesn't do. |
| Domain modeling | 8 (F1) | 9.5 | Accepted — "which layer carries a key" is now one decision (`_resolve`), matching the documented domain rule; `ORDER` is a live part of that decision rather than a dead hint. |
| Data flow and dependency design | 6 (F1) | 9.5 | Accepted — one owner computes "which layer wins"; both public functions are thin, honest projections of it. |
| Framework / platform best practices | 10 | 10 | None — idiomatic stdlib Python throughout. |
| Code simplicity and clarity | 7 (F1, F3) | 9.5 | Accepted — no dead constant, no duplicated four-branch traversal a reader must cross-check by hand. |

Score anchors and residual-disposition rules per `architecture-rubric-scoring.md`. This is a lightweight review-and-apply pass, not a full contest-refactor loop — no JSON schema, findings registry, or HALT-state machinery was produced (none was asked for); the scorecard is a self-contained artifact of this run.

---

## Summary

- **Findings raised:** 3 — F1 (Serious: `describe_source`/`effective_value` ownership drift, demonstrated repro), F2 (Noticeable: missing project-vs-user precedence test coverage on the module's only flow), F3 (Cosmetic: unused `ORDER` constant).
- **Fixes applied:** 2 — (1) consolidated both functions onto one `_resolve` owner in `settings.py`, resolving F1 and F3 together; (2) added `test_empty_string_is_a_deliberate_override` and `test_project_beats_user` to `test_settings.py`, resolving F2 and locking in F1's fix as a regression test.
- **Fixes SPT rejected:** 0 applied-then-reverted fixes. One smaller alternative (patch `describe_source`'s truthy checks in place without extracting a shared owner) was considered and discarded pre-application because it fails Q3 (leaves two independent owners of "which layer wins" standing) — recorded above under Fix 1, Q2.
- **Final pytest result:** `python3 -m pytest -q` → **7 passed**, 0 failed (started at 5 passed, 0 removed, 2 added).
