# RUN_REPORT — settings.py architectural review

Target: `/private/tmp/claude-502/-Users-Shared-git-agent-skills/051852b6-ffb7-44f6-9d95-881320b484b5/scratchpad/spt-q3/v2-d1b/`
(`settings.py`, `test_settings.py`). Stack: generic Python — `lens-generic.md` applied
alongside `architecture-rubric.md`. Baseline `python3 -m pytest -q`: **5 passed**.

---

## Phase 1 — Critic: Findings (Evidence Chain)

### Finding 1 — `describe_source` and `effective_value` disagree on which layer "carries" a key (Serious deduction)

- **Claim**: `effective_value` treats a key as carried by a layer using *presence*
  (`key in env`), matching the module's own documented contract. `describe_source`
  — which the docstring says backs the `--explain` command — instead treats a key
  as carried using *truthiness* (`env.get(key)`). These are two independent
  implementations of the same question ("which layer wins for this key?"), and
  they answer it differently whenever the carried value is falsy (e.g. an
  explicit empty-string override). This is a real, demonstrated drift between
  two owners of the same question (`method.md` § Q3).
- **Source**:
  - `settings.py:5-7` (docstring, pre-fix): `A layer "carries" a key when the key is present, whatever the value -- an explicitly empty string is a deliberate override, not an absence.`
  - `settings.py:18` (pre-fix): `if key in env:` — presence check.
  - `settings.py:28` (pre-fix): `if env.get(key):` — truthiness check, contradicting the docstring one function up.
  - Repro executed against pre-fix code:
    ```
    env = {"retries": ""}; project = {}; user = {}; defaults = {"retries": "3"}
    effective_value(...) -> ''        # correct: env's explicit override
    describe_source(...) -> 'default' # wrong: should be 'env'
    ```
- **Consequence**: The module's stated purpose is to answer "what is this key set to" and "which layer did that come from" *consistently*. Whenever a layer's value is falsy, `describe_source` silently misreports the source, contradicting the docstring's explicit, named example (empty string). Anyone using `--explain` output to debug a config value would be told "default" for a value that is in fact an explicit env override — the exact failure mode the docstring's caveat exists to prevent. No existing test caught this (test-strategy gap, folded into the fix below).
- **Remedy**: Collapse "which layer carries this key" into one predicate that both public functions call, so they cannot drift again — see Fix B below.
- **Severity**: **Serious deduction** — a real, demonstrated data-flow/ownership hazard in one of the module's two functions (its entire public surface), but contained to the falsy-value edge case; does not corrupt state or run unbounded.

### Finding 2 — `ORDER` is declared but has zero read sites; both functions hand-roll the same precedence independently (Noticeable weakness)

- **Claim**: `ORDER = ("env", "project", "user")` reads as the intended single source of truth for layer precedence, but nothing in the module ever reads it — `grep -rn "ORDER" .` (pre-fix) returns only its own declaration line. Instead, `effective_value` and `describe_source` each hardcode the same three-layer cascade independently. This is exactly the condition that let Finding 1 happen: precedence is asserted twice, by convention, with no shared implementation to keep the two assertions in sync.
- **Source**: `settings.py:14` (declaration, pre-fix); `grep -rn "ORDER" .` in the probe directory returned only that one line — no consumer.
- **Consequence**: Dead declared authority is misleading (a reader assumes `ORDER` governs behavior) and duplicated cascades are a standing liability — the next edit to either function's layer list has to remember to mirror it in the other, with no compiler/test forcing agreement.
- **Remedy**: Same as Finding 1 — wire `ORDER` into a single shared predicate consumed by both functions, deleting the duplicate cascades.
- **Severity**: **Noticeable weakness** — doesn't threaten correctness on its own, but reduces credibility/Locality and is the structural root cause of Finding 1.

No other findings. The module has no mutable runtime state, no I/O, no concurrency, no framework surface, and no adapters/seams to evaluate — `lens-generic.md`'s concurrency, coupling/leakage, and failure-mode/observability sections are not applicable (no async, no external calls, no error-discarding constructs).

---

## Phase 2 — Architect: Simplify Pressure Test

Both findings share one root cause and one candidate remedy space. Two candidate fixes were run through SPT.

### Candidate Fix A (considered, REJECTED) — patch `describe_source` in place

Change `describe_source`'s three `.get(key)` truthiness checks to `key in ...` presence checks, leaving `effective_value`, `describe_source`, and `ORDER` as three independent, unconnected pieces (just with matching predicates today).

1. **Does it fix real ambiguity?** Yes — for the current input space, `describe_source` would now agree with `effective_value`.
2. **Is it the smallest honest fix?** On line-count, yes (3 tokens changed). But it fixes the symptom, not the ownership: `ORDER` is still unread and the two functions still each hand-roll their own copy of the precedence cascade.
3. **Does it avoid duplicate layers? Count owners.** The question is "which layer carries this key for a given `(key, env, project, user)`". After Fix A, two code paths still answer it independently (`effective_value`'s `if key in env / project / user` chain, and `describe_source`'s now-matching but textually separate chain). Per `method.md` § Q3: *"a symptom repair that restores agreement today still leaves the owner count at two and fails Q3."* **No.**
4. **Does runtime behavior remain honest?** Yes, for the cases exercised — but honesty isn't the failure mode here.
5. **Does the product improve — measurably, and by more than the item declined?** The repro is fixed today, but the drift mechanism (two independently maintained cascades) survives untouched, and `ORDER`'s dead-declaration problem (Finding 2) is left standing.

**Structural gate**: Friction proven (repro above) — but no seam/module is being added or removed, so this gate is neutral either way.

**Verdict: REJECTED at Q3.** This is exactly the anti-pattern `method.md` names by example: restoring agreement without ending the duplicate ownership. Downgraded to the consolidating fix below.

### Candidate Fix B (applied) — single shared `_carrier` predicate driven by `ORDER`

Introduce one private helper `_carrier(key, env, project, user)` that walks `ORDER` and returns the first layer name whose mapping contains `key` (presence, matching the docstring), or `None`. Rewrite `effective_value` and `describe_source` to both call it — neither hand-rolls its own cascade anymore.

1. **Does it fix real ambiguity?** Yes — "which layer carries this key" now has exactly one implementation; the two public functions read it, they don't each redefine it.
2. **Is it the smallest honest fix?** Yes — one small private function (11 lines incl. docstring) inside the same file, no new file, no class, no protocol; net diff is a like-for-like rewrite of the two existing functions plus one helper. Uses the previously-dead `ORDER` constant instead of adding new machinery.
3. **Does it avoid duplicate layers? Count owners.** "Which layer carries this key" now has exactly **one** owner (`_carrier`); `effective_value` and `describe_source` are both thin callers. **Yes.**
4. **Does runtime behavior remain honest?** Yes — this is a real fix (same presence semantics the docstring already specifies), not a suppression; all 5 pre-existing tests pass unchanged, and the previously-wrong case now returns the documented answer.
5. **Does the product improve — measurably, and by more than the item declined?** Yes, and this is not a "fifth small fix that stopped moving anything" (`method.md` § Q5) — it is the first and only fix proposed for this module, it closes a demonstrated repro (`describe_source` now returns `"env"` instead of `"default"` for an explicit empty-string override), and it retires the dead `ORDER` declaration (Finding 2) in the same motion. Concretely: `test_strategy` and `credibility` dimensions both move off their pre-fix caps (see scorecard).

**Structural gate**: Friction proven (repro). No Module is deleted (deletion test n/a — nothing removed, only de-duplicated). No new Seam is introduced (Unified Seam Policy n/a — `_carrier` is a private in-module helper, not an Interface/Adapter). Tests after the change: two new tests were added at the existing public Interface (`effective_value` / `describe_source`), not against the private `_carrier` helper, satisfying "tests live at the Interface."

**Verdict: PASSED. Applied.**

---

## Phase 3 — Execution

### Edits applied

**`settings.py`** — replaced the two independent precedence cascades with one shared, `ORDER`-driven predicate:

```python
def _carrier(key, env, project, user):
    """Name of the first layer (in ORDER) that carries key, or None.

    "Carries" means present, whatever the value -- this is the single
    predicate both effective_value and describe_source defer to, so they
    cannot disagree about which layer wins.
    """
    layers = {"env": env, "project": project, "user": user}
    for name in ORDER:
        if key in layers[name]:
            return name
    return None


def effective_value(key, env, project, user, defaults):
    layers = {"env": env, "project": project, "user": user}
    name = _carrier(key, env, project, user)
    if name is not None:
        return layers[name][key]
    return defaults.get(key)


def describe_source(key, env, project, user, defaults):
    return _carrier(key, env, project, user) or "default"
```

`ORDER` is now the module's single, actually-read declaration of layer precedence.

**`test_settings.py`** — added two regression tests covering the exact bug found (mutation-test gap closed: no prior test distinguished a presence-check from a truthiness-check on a falsy override):

```python
def test_empty_string_override_is_carried_not_default():
    # An explicit empty string is a deliberate override per the module
    # docstring, not an absence -- both functions must agree it came from env.
    assert _call(settings.effective_value, "retries", env={"retries": ""}) == ""
    assert _call(settings.describe_source, "retries", env={"retries": ""}) == "env"


def test_empty_string_override_still_beats_lower_layer():
    assert (
        _call(
            settings.describe_source,
            "retries",
            env={"retries": ""},
            project={"retries": "5"},
        )
        == "env"
    )
```

### Final test result

```
$ cd .../v2-d1b && python3 -m pytest -q
.......                                                                 [100%]
7 passed in 0.01s
```

5 original tests still pass, unmodified in behavior; 2 new tests pass. No revert was needed.

---

## Final Scorecard

Only dimensions the finding touches moved; the rest were 10 both before and after (no mutable state, no concurrency, no I/O, no framework surface, no seams/adapters to evaluate in a 40-line pure-function module).

| Dimension | Pre | Post | Why |
|---|---|---|---|
| Architecture quality | 10 | 10 | No Modules/Seams/Adapters exist to critique; not applicable. |
| State management & runtime ownership | 10 | 10 | No mutable runtime state; all inputs are read-only args. |
| Concurrency & runtime safety | 10 | 10 | Pure synchronous functions; not applicable. |
| Test strategy & regression resistance | 7 | 10 | Pre: suite could not distinguish a presence-check from a truthiness-check on a falsy override (Step 8 mutation-test gap on a primary flow — one of only two public functions). Post: gap closed by the two new tests; no further nameable gap in this module. |
| Overall implementation credibility | 7 | 10 | Pre: docstring explicitly names the presence-vs-absence contract; `describe_source` violated it — a concrete, demonstrated honesty leak. Post: both functions now provably share one implementation of the contract; nothing left to charitably accept. |
| Domain modeling | 7 | 10 | Pre: "which layer carries a key" existed only as duplicated convention across two functions, so the impossible state (disagreement) was representable. Post: `_carrier` reifies the concept once; disagreement is unrepresentable by construction. |
| Data flow & dependency design | 9 | 10 | Pre: `ORDER` declared but disconnected from the actual data flow it named. Post: `ORDER` is the live source of both functions' traversal. |
| Framework / platform best practices | 10 | 10 | Plain idiomatic Python; no framework surface. |
| Code simplicity & clarity | 7 | 10 | Pre: two near-identical cascades computing the same fact via different predicates — duplicate logic that didn't earn its keep (deletion test: removing either cascade doesn't remove complexity, it just moves the drift risk). Post: single predicate, no duplication. |

---

## Summary

- **Findings raised**: 2 (1 Serious — `describe_source`/`effective_value` disagreement on falsy-value overrides, demonstrated with a repro; 1 Noticeable — dead `ORDER` declaration / duplicated precedence cascades, the root cause of the Serious finding).
- **Fixes SPT-rejected**: 1 (Fix A — patching `describe_source`'s three lines in place; failed Q3, restores agreement without ending the two-owner duplication).
- **Fixes applied**: 1 (Fix B — consolidated both functions onto a single `ORDER`-driven `_carrier` predicate in `settings.py`; added 2 regression tests in `test_settings.py`).
- **Final `python3 -m pytest -q`**: **7 passed**, 0 failed.
