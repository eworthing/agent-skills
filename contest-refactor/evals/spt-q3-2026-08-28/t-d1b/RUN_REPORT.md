# Run Report — settings.py review

Target: `settings.py` + `test_settings.py` (2 files, 35 + 24 lines, no I/O, no concurrency, no external deps). Protocol: `method.md` Meta-Rules + Method steps + SPT gate, `architecture-rubric.md`, `lens-generic.md`.

## Critic phase — Findings

### Finding 1 — `describe_source` and `effective_value` disagree on which layer "carries" a key

**Claim:** The module docstring defines a single authority rule — "a layer carries a key when the key is present, whatever the value -- an explicitly empty string is a deliberate override, not an absence" — but the two functions implement that rule with two different, independently-drifted tests: `effective_value` checks presence (`key in layer`), `describe_source` checks truthiness (`layer.get(key)`). This is exactly the Q3 "two sites answer the same question" pattern from `method.md`, and it had already drifted.

**Source:**
- `settings.py:5-7` (docstring): `A layer "carries" a key when the key is present, whatever the value -- an explicitly empty string is a deliberate override, not an absence.`
- `settings.py:18-23` (`effective_value`, membership check): `if key in env: return env[key]` / `if key in project: return project[key]` / `if key in user: return user[key]`
- `settings.py:28-33` (`describe_source`, truthy check — the defect): `if env.get(key): return "env"` / `if project.get(key): return "project"` / `if user.get(key): return "user"`

**Consequence:** For any key whose value is explicitly `""` in a higher-priority layer (the exact case the docstring calls out as a *deliberate override, not an absence*), `effective_value` correctly returns `""` from that layer, but `describe_source` skips that layer (empty string is falsy) and reports a lower-priority layer or `"default"` instead. Per the docstring, `describe_source` is "what the `--explain` command prints" — so the primary user-facing diagnostic for this module can name the wrong layer for the value the user is actually getting. This is a real, reachable, source-proven data-flow hazard, but it is contained to one small module with no fan-out — **Serious deduction**, not a disqualifier.

**Remedy:** Consolidate the layer-cascade decision into one internal helper both functions call, so there is exactly one place that decides "which layer carries this key" (see Architect phase below).

### Finding 2 — `ORDER` is declared but never read

**Claim:** `ORDER = ("env", "project", "user")` (`settings.py:14`) documents the intended cascade order but neither function consumes it; each hardcodes its own `if/elif` chain in that same order instead.

**Source:** `settings.py:14` (`ORDER = ("env", "project", "user")`) vs. `settings.py:18-23` and `settings.py:28-33` (both re-literal the same three-layer order inline).

**Consequence:** Cosmetic — dead declaration, and the reason the two inline cascades in Finding 1 were free to drift out of sync in the first place (nothing forced them to share one source of truth for order or for the "carries" test).

**Remedy:** Fold `ORDER` into the consolidation from Finding 1's fix as the loop driver, rather than deleting it or leaving it unused.

## Architect phase — Simplify Pressure Test

### Proposed fix (covers Finding 1 and Finding 2 together)

Add a private `_find(key, env, project, user)` helper that walks `ORDER` and returns `(layer_name, layer_dict)` for the first layer where `key in layer`, using membership (not truthiness). Rewrite `effective_value` and `describe_source` to both call it. No public signature changes.

I considered the smaller alternative first — just changing `describe_source`'s three `.get(key)` truthy checks to `key in ...` membership checks in place, without adding a helper — and rejected it in favor of consolidation, per the SPT Q3 discussion below.

**SPT answers:**

1. **Does it fix real ambiguity?** Yes. It removes the actual disagreement between the two functions about which layer produced the returned value.
2. **Is it the smallest honest fix?** Yes. One ~10-line private helper, reusing the existing (previously dead) `ORDER` constant. No new public API, no new file, no new class or protocol.
3. **Does it avoid duplicate layers, both directions?** Yes, and this is the reason consolidation (not the smaller patch-in-place) was chosen: `effective_value` and `describe_source` were already two independent sites answering the identical question ("which layer carries this key"), and a demonstrated disagreement between them (a real repro, not a hypothetical) is exactly the case `method.md` names as *not* ceremony — "the parallel cascades it replaces are the defect, not the cost." Patching only `describe_source`'s three lines would have fixed today's symptom but left two independent cascades standing, free to drift again the next time either one is edited (e.g., a future fourth layer). Consolidating into one `_find` closes the drift class, not just this instance of it.
4. **Does runtime behavior remain honest?** Yes. Every previously-passing test scenario is unchanged (verified below); only the previously-wrong edge case (explicit empty-string override) changes, and it changes to match the module's own documented contract — nothing is hidden or suppressed.
5. **Does the product improve measurably, by more than what's declined?** Yes. It eliminates a demonstrated bug class in the module whose whole purpose is answering "what is this value and which layer set it," verified by a new regression test that fails on the pre-fix code and passes after. There is no higher-value competing item being declined — this is the only structural finding in a 35-line module.

**Structural gate:**
- Friction proven: yes — a working repro (env value `""`) shows the two functions disagreeing, which is stronger than a taste objection.
- Deletion test for any Module being removed: not applicable — no Module is removed; `_find` is a new private helper, not a replacement for an existing one.
- Unified Seam Policy for any new Seam: not applicable — `_find` is a private in-file implementation detail, not an Interface/Seam exposed to callers; the two-adapter / single-adapter tests don't apply to it.
- Tests live at the new Interface: yes — the public Interface (`effective_value`, `describe_source`) is unchanged, so no old tests become stale; the new regression test calls the public functions, not `_find` directly.

**Verdict: PASSED.** Applied.

**Finding 2 disposition:** resolved as a byproduct of Finding 1's fix (`ORDER` now drives `_find`'s iteration) — no separate fix was proposed or needed, so no separate SPT run applies.

No fixes were rejected by SPT — the only structural finding in this module had one honest fix, and it passed on all five questions plus the gate.

## Execution phase — edits applied

**`settings.py`** — replaced the two independent, drifted cascades with one shared `_find` helper (uses `ORDER`, membership-tested):

```python
def _find(key, env, project, user):
    """Return (layer_name, layer_dict) for the first layer carrying `key`.
    ...
    """
    for name, layer in zip(ORDER, (env, project, user)):
        if key in layer:
            return name, layer
    return None, None


def effective_value(key, env, project, user, defaults):
    _, layer = _find(key, env, project, user)
    if layer is None:
        return defaults.get(key)
    return layer[key]


def describe_source(key, env, project, user, defaults):
    name, _ = _find(key, env, project, user)
    return name or "default"
```

**`test_settings.py`** — added one regression test at the existing Interface (the only non-trivial-logic path needed a runnable check):

```python
def test_empty_string_override_is_carried():
    assert _call(settings.effective_value, "mode", env={"mode": ""}) == ""
    assert _call(settings.describe_source, "mode", env={"mode": ""}) == "env"
```

This test fails against the pre-fix `describe_source` (old truthy check would report `"default"` instead of `"env"`) and passes against the fix — it is the executable evidence for Finding 1's Consequence and Remedy.

## Test result

Before fix: `python3 -m pytest -q` → 5 passed.
After fix: `python3 -m pytest -q` → **6 passed** (5 original + 1 new regression test), `python3 test_settings.py` → `ok`.

## Scorecard

Small, dependency-free, stateless module (no concurrency, no I/O, no persistence) — most dimensions are near-ceiling by construction; the one applicable defect is scoped narrowly.

| Dimension | Before | After | Basis |
|---|---|---|---|
| Ownership | 9.5 | 9.5 | Two pure, stateless module-level functions; no mutable state, no ambiguity about who writes what. |
| Data flow | 6.5 | 9.5 | Finding 1: two independent cascades disagreed on source-of-truth for falsy-but-present values. Fixed by consolidation; verified by repro-based regression test. |
| Concurrency | 10 | 10 | Not applicable — no async, no shared mutable state, no threads. |
| Test strategy | 7.5 | 9.5 | Existing tests covered the four documented precedence scenarios but missed the docstring's own explicit-empty-string-override contract (Method Step 8 mutation-test check: flipping `.get(key)` truthy→membership was a nameable, primary-flow mutation the old suite would not have caught). One regression test now covers it at the Interface both callers share. |
| Simplicity | 9.5 | 9.5→10 | Already minimal; consolidation removed the last duplication (two inline cascades → one) without adding ceremony. |
| Credibility | 6.5 | 9.5 | Doc-vs-code mismatch (docstring's "carries" contract vs. `describe_source`'s truthy check) is a doc-rot pattern per `method.md` Step 6; code now matches the documented contract. |
| Framework idioms | 9.5 | 9.5 | Idiomatic plain Python throughout; no framework/ORM leakage (none present to leak). |

## Honesty note

One structural finding was identified, its fix passed SPT on all five questions plus the gate, and was applied. No fix was rejected by SPT in this run — the module is small enough that there was exactly one real defect and one honest way to fix it; nothing else in the code warranted a finding, and no additional restructuring was proposed or needed.
