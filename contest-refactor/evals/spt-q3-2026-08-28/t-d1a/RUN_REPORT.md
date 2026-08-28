# Architectural Refactor Review — `settings.py` / `test_settings.py`

Target: `/private/tmp/claude-502/-Users-Shared-git-agent-skills/051852b6-ffb7-44f6-9d95-881320b484b5/scratchpad/spt-q3/t-d1a`
Protocol: `method.md` (Meta-Rules, 10-step Method, Simplify Pressure Test), `architecture-rubric.md`, `lens-generic.md` (Python).
Baseline: `python3 -m pytest -q` → `5 passed` before any change.

Scope note: this is a 35-line module (two pure functions, no I/O, no state, no
concurrency) plus its test file. Most of the Method's steps (Seam policy,
Authority Map, actor isolation, hidden state machines, etc.) have no surface
here — recorded as "N/A, no evidence" rather than skipped silently.

---

## Critic Phase — Findings

### Finding 1 — `describe_source` silently contradicts its own documented contract for falsy overrides

**Severity: Serious deduction**

- **Claim:** The module docstring states the contract explicitly: *"A layer
  'carries' a key when the key is present, whatever the value — an explicitly
  empty string is a deliberate override, not an absence."* `effective_value`
  implements that contract correctly using presence checks. `describe_source`
  — the function backing the `--explain` command per the same docstring —
  implements a *different, undocumented* contract: truthiness, not presence.
  The two functions that are supposed to jointly answer "what value / which
  layer" can give mutually contradictory answers for the same input.
- **Source:** `settings.py:27-34` (pre-fix):
  ```
  def describe_source(key, env, project, user, defaults):
      if env.get(key):
          return "env"
      if project.get(key):
          return "project"
      if user.get(key):
          return "user"
      return "default"
  ```
  versus `effective_value` at `settings.py:18-24`, which uses `if key in env:` /
  `if key in project:` / `if key in user:`. Docstring contract at
  `settings.py:5-7`. Empirically verified before the fix:
  `effective_value("retries", {"retries": ""}, {}, {}, DEFAULTS)` → `''`
  (correct: env carries the key) while
  `describe_source("retries", {"retries": ""}, {}, {}, DEFAULTS)` → `'default'`
  (wrong: should be `'env'`). No test in `test_settings.py` exercised a
  falsy-but-present override, which is why this escaped the suite.
- **Consequence:** The `--explain` command can report the wrong layer for any
  legitimate falsy override (`""`, `"0"`, `0`, `False`, `None`) — telling a
  user their setting came from `default` when it was actually an explicit
  `env`/`project`/`user` override. That's the exact scenario the docstring
  calls out by name as the one to get right, so this isn't an edge case the
  author overlooked — it's a direct contradiction of the one invariant the
  module states in writing. Contained to one function of a two-function
  module, so not disqualifying, but it is a genuine, reachable data-flow
  honesty defect.
- **Remedy:** Change `describe_source` to use the same presence checks
  (`key in env` / `key in project` / `key in user`) that `effective_value`
  already uses. Zero new structure — align the second function with the
  pattern the first one already proves correct.

### Finding 2 — `ORDER` constant is declared but never read; both functions re-hardcode the same precedence independently

**Severity: Cosmetic for contest**

- **Claim:** `ORDER = ("env", "project", "user")` reads as the canonical
  statement of layer precedence, but neither `effective_value` nor
  `describe_source` consults it — each independently hardcodes the identical
  three-branch precedence via its own `if` chain.
- **Source:** `settings.py:14` (`ORDER = ("env", "project", "user")`);
  confirmed zero read sites via full-file read and `grep -n "ORDER"
  test_settings.py` → no matches. The same order is duplicated literally at
  `settings.py:18-23` and `settings.py:28-33` (pre-fix).
- **Consequence:** `ORDER` is an inert artifact that looks authoritative but
  isn't. A maintainer who edits `ORDER` expecting to change precedence changes
  nothing; the real precedence lives, unenforced, in two separately-maintained
  `if` chains that must be kept in sync by hand. Minor drift/comprehension
  hazard, not a live behavioral bug — it does not affect current output for
  any input.
- **Remedy candidates:** see Architect phase below — both were run through
  SPT and rejected.

No other findings. There is no mutable state, no seam/adapter surface, no
concurrency, no I/O, and no framework leakage to review in this module —
those Method steps produced no evidence and are recorded as clean by absence
of findings, not skipped.

---

## Architect Phase — Simplify Pressure Test

### Proposed fix A — align `describe_source` with `effective_value`'s presence checks (Finding 1)

1. **Does it fix real ambiguity?** Yes — resolves the direct contradiction
   between code behavior and the module's own written contract for
   falsy-but-present values.
2. **Is it the smallest honest fix?** Yes — three `.get(key)` truthy checks
   become three `key in X` presence checks, mirroring the pattern
   `effective_value` already uses two lines above. No new abstraction, no new
   parameter, no new type.
3. **Does it avoid duplicate layers (both directions)?** Yes — it removes a
   divergence between two sites that must answer consistently (Q3's "two
   sites already answer the same question" case: value and source for the
   same key must agree), and it does not introduce any new second owner of
   the question.
4. **Does runtime behavior remain honest?** Yes — this makes runtime behavior
   match the documented contract; it was the previous behavior that was
   dishonest (silently misreporting the source for falsy overrides).
5. **Does the product improve — measurably, and by more than the item
   declined?** Yes — `describe_source` (used by `--explain`, per the
   docstring) now gives a correct answer for a concrete, named input class
   (falsy overrides) instead of a wrong one. This is a correctness fix, not
   tidiness.

**Structural gate:** No seam proposed (N/A). No module removed (N/A —
deletion test doesn't apply to a same-shape bug fix). Tests added at the
existing Interface (direct calls to `effective_value`/`describe_source`,
matching the existing test file's shape) — satisfies "tests live at the
Interface."

**Verdict: PASSED.** Applied.

### Proposed fix B — wire `ORDER` into both functions via a loop over a `{name: dict}` mapping (Finding 2, remedy candidate 1)

1. **Does it fix real ambiguity?** Weak yes at best — the "ambiguity" is a
   maintenance-consistency risk, not a behavioral one; nothing currently
   computes the wrong answer because of the duplication.
2. **Is it the smallest honest fix?** No. It replaces two direct, three-line
   `if` chains with a dict literal + loop, i.e. more code and one more level
   of indirection, to deduplicate a fixed, closed set of exactly three
   layers that is not expected to grow. A smaller alternative exists (fix C,
   below) that removes the same misleading-artifact risk with a one-line
   diff.
3. **Does it avoid duplicate layers?** Mixed — it removes the *order*
   duplication but introduces a new indirection layer (the `{name: dict}`
   mapping) that wasn't there before. Not a clear win either direction.
4. **Does runtime behavior remain honest?** Yes, if implemented correctly —
   but note this buys zero additional behavior once fix A has already made
   both functions presence-based; at that point this would be a pure
   reshuffle with no behavior change at all.
5. **Does the product improve — measurably, and by more than the item
   declined?** No. For a closed, three-item, unlikely-to-change precedence
   order, deduplicating two three-line branches is not a measurable gain,
   and it costs more than the smaller alternative (fix C) that addresses the
   same underlying risk (a misleading unused constant) more cheaply.

**Verdict: REJECTED** — fails Q2 (a strictly smaller fix exists for the same
underlying concern) and Q5 (gain not measurable, and smaller than the
declined simpler alternative).

### Proposed fix C — delete the unused `ORDER` constant (Finding 2, remedy candidate 2)

1. **Does it fix real ambiguity?** Modest yes — removes the false impression
   that editing `ORDER` changes behavior.
2. **Is it the smallest honest fix?** Yes, mechanically — a one-line
   deletion.
3. **Does it avoid duplicate layers?** N/A / passes — nothing added.
4. **Does runtime behavior remain honest?** Trivially yes — `ORDER` is read
   nowhere, so removing it changes nothing.
5. **Does the product improve — measurably, and by more than the item
   declined?** No. This is exactly the anti-pattern the Method calls out by
   name: *"the gain is not nameable... 'it is tidier' is not a product
   improvement."* Deleting one unused constant does not move any scored
   dimension by a nameable amount; there is no reachable defect behind it
   (unlike Finding 1, nothing currently computes a wrong answer because
   `ORDER` exists). It is speculative future-maintainer-confusion, not
   demonstrated current harm.

**Verdict: REJECTED** — fails Q5 (no nameable product improvement; the smell
list in `architecture-rubric.md` explicitly treats this class of concern as
"smoke, not a finding" absent proof of harm, and no harm is proven here).

**Disposition of Finding 2:** left as-is. Recorded as a Cosmetic-for-contest
backlog item, not acted on. Both candidate remedies were considered and
rejected by SPT for the same underlying reason: the risk is real but too
small, and every fix attempted was either disproportionate to it (fix B) or
pure tidiness with no nameable gain (fix C).

### Proposed fix D — add `test_project_beats_user` closing a named mutation-test gap (Method step 8)

Method step 8 requires naming one source-level mutation current tests would
not catch on the primary flow before scoring `test_strategy` ≥ 9. Named
mutation: swapping the `project`/`user` check order in either function (e.g.
`if key in user: return "user"` checked before `project`) is **not** caught
by any existing test — `test_env_beats_project` only proves `env` beats
`project`; nothing sets both `project` and `user` together to prove
precedence between those two. Since this two-function module *is* the
primary flow (no off-path utilities to exempt it), this is a nameable,
in-scope gap, not a carve-out case.

1. **Does it fix real ambiguity?** Yes — closes a concrete, named hole in the
   regression net for the module's core precedence logic.
2. **Is it the smallest honest fix?** Yes — one test function, same shape as
   the existing `test_env_beats_project`.
3. **Does it avoid duplicate layers?** Yes — a new, non-overlapping case
   (project+user), not a restatement of an existing test.
4. **Does runtime behavior remain honest?** N/A — test-only change.
5. **Does the product improve — measurably, and by more than the item
   declined?** Yes — it closes the exact mutation Method step 8 requires be
   named before `test_strategy` can score ≥ 9; without it, that mutation was
   live and unguarded.

**Structural gate:** Test added at the existing Interface (direct function
calls), same shape as sibling tests — satisfies "tests live at the
Interface," no layering.

**Verdict: PASSED.** Applied.

---

## Execution Phase — Edits Applied

**`settings.py`** — `describe_source` changed from truthy checks to presence
checks (Fix A):

```diff
 def describe_source(key, env, project, user, defaults):
-    if env.get(key):
+    if key in env:
         return "env"
-    if project.get(key):
+    if key in project:
         return "project"
-    if user.get(key):
+    if key in user:
         return "user"
     return "default"
```

**`test_settings.py`** — two regression tests added after
`test_source_reports_user` (Fix A regression coverage + Fix D):

```python
def test_falsy_override_still_counts_as_carried():
    # A layer that explicitly sets a key to "" is a deliberate override, not an
    # absence (per settings.py's module docstring) -- effective_value and
    # describe_source must agree on that.
    assert _call(settings.effective_value, "retries", env={"retries": ""}) == ""
    assert _call(settings.describe_source, "retries", env={"retries": ""}) == "env"


def test_project_beats_user():
    assert (
        _call(
            settings.effective_value, "retries", project={"retries": "5"}, user={"retries": "1"}
        )
        == "5"
    )
    assert (
        _call(
            settings.describe_source, "retries", project={"retries": "5"}, user={"retries": "1"}
        )
        == "project"
    )
```

No other files touched. `ORDER` left untouched (Finding 2, both remedies
rejected by SPT).

### Final test result

```
$ python3 -m pytest -q
.......                                                                  [100%]
7 passed in 0.01s

$ python3 test_settings.py
ok
```

5 original tests + 2 new tests, all passing. No test broke; nothing needed a
revert.

---

## Final Scorecard

Qualitative, 1–10 scale. `architecture-rubric-scoring.md` (the per-dimension
numeric anchor table) was not in scope for this review per the protocol's
reading list, so anchors below are derived from `architecture-rubric.md`'s
Severity Anchors and the Method's dimension vocabulary rather than the
missing numeric table.

| Dimension | Pre-fix | Post-fix | Why |
|---|---|---|---|
| Architecture / Seams | 9.5 | 9.5 | No seam/adapter surface exists or is warranted (in-process pure functions, closed 3-layer precedence, `lens-generic.md` Dependency Categorization: none apply). Nothing to fault or add. |
| Ownership / State | 9.0 | 9.0 | No mutable state, single writer of nothing (pure functions). Unaffected by Finding 1/2; the unused `ORDER` constant is a minor, unfixed drift-hazard smell (Finding 2), not a state-ownership defect. |
| Data flow / contract honesty | 6.5 | 9.5 | Pre-fix: `describe_source` directly contradicted the module's own documented contract for a named, reachable input class (Finding 1) — Serious deduction. Post-fix: behavior matches the documented contract; verified by new regression test. |
| Concurrency | 10 | 10 | N/A — no async/threading/shared mutable state in scope. |
| Test strategy | 7.5 | 9.5 | Pre-fix: the exact defect class in Finding 1 was untested, and the project-vs-user precedence mutation (Method step 8) was unguarded. Post-fix: both gaps closed with regression tests at the existing Interface; not claiming a perfect 10 since not every falsy-value variant (`0`, `False`, `None`) has its own test, only the representative `""` case. |
| Simplicity | 9.5 | 9.5 | Module is already minimal — two small pure functions, no ceremony. The one candidate "simplification" (wiring `ORDER` in) was tested under SPT and rejected as net-neutral-to-negative (fix B). |

**Verdict:** No disqualifiers. One Serious deduction found and fixed
(Finding 1). One Cosmetic finding recorded and deliberately left unfixed
after two candidate remedies failed SPT (Finding 2) — an honest "found but
not worth touching" outcome, not an oversight.
