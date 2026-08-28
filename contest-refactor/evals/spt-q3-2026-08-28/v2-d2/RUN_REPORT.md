# Architectural Refactor Review — `v2-d2` probe

Target: `credential_policy.py` (60 lines) + `test_credential_policy.py` (52 lines).
Method applied: `method.md` (Meta-Rules, Method steps, Simplify Pressure Test),
`architecture-rubric.md` (full), `lens-generic.md` (full), exactly as scoped by
the protocol. `lens-security.md` / `lens-efficiency.md` were **not** in the
assigned protocol and were deliberately not loaded — see "Scope note" at the
end for why that matters to one observation below.

Baseline: `python3 -m pytest -q` → `3 passed in 0.01s` (confirmed before any edit).

---

## Critic phase

### Step 2 — Authority Map (mutable runtime concerns)

None. The module is four pure functions plus three module-level constants
(`NO_LOCAL_CREDENTIAL_PREFIX`, `NO_LOCAL_CREDENTIAL_SUFFIX_LENGTH`,
`_SUFFIX_ALPHABET`). No stored/mutable state, no writers, no persistence seam
in view. Authority Map is vacuous by design — nothing to flag under "state
with no authority," "stable workflow identity," or "causal runtime context."

### Step 3 — Architecture / Seams

No protocol, no adapter, no DI. This is a flat policy module, not a Seam
construct — the two-adapter rule and Unified Seam Policy don't apply because
nothing here claims to be a Seam. Deletion test: deleting the module would
push the sentinel-vs-encoded distinction (`NO_LOCAL_CREDENTIAL_PREFIX`
disjointness) back into every caller — it earns its keep. No costume layers,
no repository theater, no protocol soup. `rg` for
`LEGACY|TEMPORARY|DEPRECATED|DO NOT|ASPIRATIONAL|carve-out|SHIM|FIXME|HACK|TODO`
across both files: **0 hits**.

### Step 7 — Hidden state machines

None, and the module's own docstring explains it explicitly avoided the
smell: "stores a sentinel instead of a nullable column or a separate flag."
This is the state-machine collapse the rubric asks for, already done.

### Step 8 — Tests and regressions (mutation-test mental model)

`is_credential_usable(stored)` returns `False` for two input classes:
`stored is None` and `stored` is a no-local-credential marker
(`credential_policy.py:21-23`). `verify_credential` guards on exactly this
(`credential_policy.py:57-58`) — and per the module's own opening docstring,
*this guard is the entire reason the module exists*: "an account with no
local credential of its own... [gets a sentinel so it] can never be mistaken"
for a real one.

Before this pass, `test_credential_policy.py` never called `verify_credential`
with `stored` set to a marker or to `None`. The only marker-touching test
(`test_no_local_credential_marker_exists`, line 27-29) checks `isinstance(marker, str)`
— it says nothing about `verify_credential`'s behavior against that marker.
That is a zero-coverage gap on the module's headline contract.

**Honest mutation-test result (I ran this, not just asserted it):** I tried
mutating `credential_policy.py` to delete the `if not is_credential_usable(stored): return False`
guard entirely and replayed both the old and new tests against the mutant.
*No test — old or new — caught it*, because `set_credential`'s output always
starts with the literal `"$enc$"` and a marker always starts with
`NO_LOCAL_CREDENTIAL_PREFIX` (`"~"`); those are disjoint by construction, so
`set_credential(supplied) == stored` is already `False` for `stored` = marker
or `None`, guard or no guard. I record this rather than hide it: the naive
"delete the guard" mutation is not what the new tests catch.

What the new tests *do* catch: I then mutated `NO_LOCAL_CREDENTIAL_PREFIX`
from `"~"` to `"$"` (a plausible one-character drift — e.g. someone picks a
prefix that overlaps the `"$enc$"` literal) and replayed the original 3 tests
against that mutant: `test_correct_credential_verifies` broke immediately,
so that specific drift was already caught incidentally. The real, previously
uncaught gap is narrower and more honest to state directly: **before this
fix, nothing in the suite ever exercised `verify_credential(marker, ...)` or
`verify_credential(None, ...)` at all** — the module's central promise was
untested as an end-to-end contract, resting entirely on the reader trusting
that the two literals stay disjoint. That is the finding; the two new tests
close exactly that hole by asserting the documented contract directly at the
public Interface, per Step 8's Authority-Map cross-check ("confirm at least
one test file exercises its mutation paths through the Interface").

**Finding F1 — Evidence Chain**

- **Claim:** `verify_credential`'s core guarantee — a no-local-credential
  account (or a `None`/absent credential) can never be verified against any
  supplied value — had no direct test. The only test touching a marker
  checked its type, not its interaction with `verify_credential`.
- **Source:** `credential_policy.py:50-59` (`verify_credential`, guard at
  57-58); `test_credential_policy.py:27-29` (`test_no_local_credential_marker_exists`,
  the only pre-existing marker-adjacent test, an `isinstance` check only).
- **Consequence:** Weakens regression resistance and test strategy on the
  one behavior this module exists to guarantee (per its own module
  docstring). A future edit to either `NO_LOCAL_CREDENTIAL_PREFIX` or
  `set_credential`'s literal prefix that let the two spaces overlap would
  ship with all 3 original tests green.
- **Remedy:** Add direct tests asserting the contract at the public
  Interface: `verify_credential(mark_no_local_credential(), anything) is False`
  and `verify_credential(None, anything) is False`. No production code
  change required — the guard is already correct.
- **Severity:** Noticeable weakness (Step 8's mutation-test rule floors this
  at "Noticeable-or-worse" for a gap on the module's primary/only flow; there
  is no live runtime hazard today, so it does not rise to Serious).

No second in-scope architecture finding was produced. I looked for
ownership/seam/concurrency/coupling/naming/hidden-state-machine smells per
Steps 2–7 and Method Step 6's mandatory doc-vs-code grep and naming audit;
none returned evidence. **If I rejected nothing else, it is because nothing
else met the Evidence Chain bar within the assigned lens** — see the scope
note at the end for one thing I deliberately did not turn into a scored
finding, and why.

---

## Architect phase — Simplify Pressure Test

### Fix candidate 1 — add `verify_credential` marker/`None` regression tests (for F1)

1. **Does it fix real ambiguity?** Yes — it removes reliance on an unstated
   assumption (the two literal prefixes stay disjoint) and pins the
   documented contract as an explicit, checked assertion.
2. **Is it the smallest honest fix?** Yes — two one-line `assert` functions
   in the existing bare-function test style; no new fixtures, no framework,
   no production-code change.
3. **Does it avoid duplicate layers?** Yes — no new owner of any question;
   it exercises the existing single guard through the existing single public
   function.
4. **Does runtime behavior remain honest?** Yes — purely additive tests;
   `credential_policy.py` is untouched.
5. **Does the product improve — measurably, and by more than the item
   declined?** Yes, and nothing competing was declined to take it: it moves
   the previously-zero-coverage input space of `verify_credential` (stored =
   marker, stored = `None`) to directly asserted, closing exactly the gap
   Step 8's Authority-Map cross-check calls out. I am explicit that it does
   **not** catch the single "delete the guard" mutation (see mutation-test
   note above) — the honest gain is turning an implicit, untested contract
   into an explicit, tested one, not a specific mutation kill.

**Structural gate:** Friction proven (zero-coverage gap demonstrated above,
not asserted). Deletion test: N/A, no module removed. Unified Seam Policy:
N/A, no seam added. Tests live at the new/same Interface: yes — both new
tests call the same public functions (`mark_no_local_credential`,
`verify_credential`) the existing tests already use.

**Verdict: PASSED.** Applied.

### Fix candidate 2 — replace `set_credential`'s reversible transform with a real one-way hash

Considered because `set_credential` (`credential_policy.py:40-47`) is
`"$enc$" + raw[::-1]` — trivially invertible, not a hash. I ran it through
SPT anyway even though I ultimately did not score it as a Critic finding
(see scope note), because it is the obvious temptation this file invites and
the task specifically wants rejected fixes recorded, not just passed ones.

1. **Does it fix real ambiguity?** No — there is no ambiguity to resolve.
   The docstring says "Encode," never "hash" or "securely hash," and every
   caller-visible contract (`is_credential_usable`, the disjoint-prefix
   guarantee) is fully satisfied by the current transform. This targets a
   weakness, not a stated-but-broken promise.
2. **Is it the smallest honest fix?** No. Swapping the transform changes the
   stored-value format for every already-stored credential in any real
   deployment of this module; making that safe needs a migration or
   dual-format verify path, which is not "smallest," it's a new subsystem.
3. **Does it avoid duplicate layers?** Not evaluated — fails earlier.
4. **Does runtime behavior remain honest?** No, and not in the sanctioned
   way. Meta-Rule 4 allows behavior changes only when the *existing*
   behavior is itself the finding being fixed — but here the interface never
   promised irreversibility, so "the existing behavior" isn't a broken
   promise, it's a design choice this review has no evidence was meant to be
   stronger. Changing it silently breaks verification for every previously
   stored value with no migration path in view.
5. **Does the product improve measurably, by more than what's declined?**
   No — for this file, in isolation, with no persistence layer or migration
   plan visible, the downside (every existing stored credential stops
   verifying) is a correctness regression larger than the security gain
   this narrow change could honestly claim without the missing migration
   design.

**Structural gate:** Friction not proven (no evidence the interface promised
more than it delivers). Fails independent of the rest.

**Verdict: REJECTED.** Reasons: fails Q1 (no ambiguity, only weakness),
fails Q2 (needs a migration/versioning subsystem to be safe, not a small
diff), fails Q4/Meta-Rule 4 (silent behavior change with no sanctioned
finding backing it and no migration path), fails Q5 (net harm outweighs
gain without that missing migration design). Not applied.

---

## Execution phase

**Edit applied** — `test_credential_policy.py`: added two test functions
and wired them into `main()`:

```python
def test_no_local_credential_marker_never_verifies() -> None:
    marker = mark_no_local_credential()
    assert verify_credential(marker, "anything") is False


def test_missing_credential_never_verifies() -> None:
    assert verify_credential(None, "anything") is False
```

(plus the corresponding two calls added to `main()`). No change to
`credential_policy.py`.

**Final test run:**

```
$ python3 -m pytest -q
.....                                                                    [100%]
5 passed in 0.01s
```

`python3 test_credential_policy.py` (standalone invocation) also passes:
`OK: test_credential_policy.py`.

---

## Scorecard

| Dimension | Before | After | Basis |
|---|---|---|---|
| Module & Seam design | 9.5 | 9.5 | No seam construct present or needed; deletion test passes (module earns its keep); no costume layers / repository theater / protocol soup. |
| Ownership & state | 10 | 10 | No mutable runtime state; single source of truth for both constants. |
| Concurrency & runtime safety | 10 | 10 | No concurrency in this file. Nothing to violate. |
| Coupling & leakage | 10 | 10 | stdlib-only (`secrets`, `string`); no framework/ORM/persistence leakage. |
| Hidden state machines | 10 | 10 | Sentinel-over-flag design explicitly avoids the boolean/optional-soup smell. |
| Test strategy / regression resistance | 7.5 | 9.5 | F1: the module's headline contract (marker/`None` never verifies) had zero direct test coverage; closed by fix 1. Residual: the disjoint-literal invariant itself (`"$enc$"` vs `NO_LOCAL_CREDENTIAL_PREFIX`) still has no direct assertion tying the two together — noted, not raised to a finding since no drift was observed in source, purely a residual to watch if either literal is ever touched. |
| Simplicity & credibility | 9.5 | 9.5 | No naming smells (no `*Manager`/`*Service` clutter), no doc-rot markers (`rg` swept, 0 hits), docstrings match behavior. |

No dimension regressed. One dimension (test strategy) moved from the fix.

---

## Scope note (read before treating this as a complete security review)

`set_credential` (`credential_policy.py:40-47`) is a reversible transform
(string reversal), not a one-way hash — anyone who reads the stored value
recovers the original credential outright. That is real and I am not hiding
it. I did **not** score it as an architecture-rubric finding or run it
through severity anchors, because architecture-rubric.md's vocabulary
(Module/Interface/Seam/Adapter/Depth/Leverage/Locality) and its severity
anchors are built for ownership/seam/state/data-flow/concurrency concerns,
not cryptographic algorithm strength — and `lens-security.md`, the file that
would actually ground that judgment, was not part of this task's assigned
protocol (only `method.md`, `architecture-rubric.md`, `lens-generic.md`
were). Scoring it anyway would be borrowing a rubric this review was not
given. I ran the "fix" through SPT regardless (candidate 2 above) so the
rejection is on record, and I flag it here as the top candidate for a
follow-up pass if a security-lens review is actually wanted. Same reasoning
applies to `set_credential(supplied) == stored` using `==` rather than
`hmac.compare_digest` (a timing-side-channel concern) — noted, not scored,
same reason.
