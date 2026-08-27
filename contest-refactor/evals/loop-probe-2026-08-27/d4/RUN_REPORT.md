# Contest-Refactor Run Report — probe d4

Target: `platsupport.py` (57 lines) + `test_platform_guards.py` (86 lines), a small
platform-skip-guard utility and its guarded test-fixture suite. `python3 -m pytest -q`
passed (8/8) before this run.

Scope note: I read `method.md`, `architecture-rubric.md`, and `lens-generic.md` per
the protocol. I did not load `architecture-rubric-scoring.md` (not in the assigned
reading list), so the scorecard below is qualitative against the Severity Anchors in
`architecture-rubric.md` rather than pinned to that doc's numeric anchors.

## Critic phase — findings

### Finding 1 — `collect_skips`'s actual behavior for its two named target platforms was never verified, in either invocation path

- **Claim:** The module's whole purpose (per its own docstring, "Guarded test suite
  exercising platsupport's skip machinery") is to exercise `collect_skips`. It never does,
  for the two platforms (`gearshift`, `tideline`) the guards exist for.
- **Source:**
  - `test_platform_guards.py:75` — `skipped = collect_skips(MAINLAND, ALL_TESTS)` — the
    *only* call to `collect_skips` anywhere in the codebase, and MAINLAND is the one
    platform where, by construction, no guard ever matches (all 8 guards test for
    gearshift/tideline identity). The interesting branch of `collect_skips` — a guard
    actually firing — is never taken.
  - `test_platform_guards.py:74` — `main()` is gated behind `if __name__ == "__main__"`
    (line 84-85), so it never runs under `pytest -q` at all. Empirically confirmed:
    `pytest -v` collects and runs the 8 `test_*` functions directly (matched by pytest's
    own naming convention), completely bypassing `__skip_guards__`/`collect_skips`/`main()`.
    Since every test body is an empty docstring, all 8 "pass" regardless of platform —
    `pytest -q` passing proves nothing about the skip machinery.
- **Consequence:** The one piece of real logic in this codebase (which test skips on
  which platform, and why) had zero assertions behind it under the command specified as
  this codebase's pass/fail bar (`pytest -q`), and only a trivial always-empty case
  behind it even in the alternate direct-run path. A regression here (see Finding 2)
  would ship silently.
- **Remedy:** Add a pytest-collected test asserting `collect_skips`'s real output for
  `gearshift` and `tideline` against the full expected reason map.

Severity: **Serious deduction** — real test-absence on the sole non-trivial logic in
the module, but contained to a small test-support utility, not a live product hazard.

### Finding 2 — `skip_if` records stacked guards in reverse of declaration order

- **Claim:** `skip_if`'s own docstring says "the first guard whose predicate matches
  wins the reported reason" (naturally read as: the topmost `@skip_if` in source). The
  implementation did the opposite.
- **Source:** `platsupport.py:39-43` (pre-fix):
  ```python
  def decorator(func):
      guards = list(getattr(func, "__skip_guards__", ()))
      guards.append((predicate, reason))
      func.__skip_guards__ = guards
      return func
  ```
  Decorators apply bottom-up, so the guard closest to `def` (bottom of the stack,
  textually *last*) is appended first and ends up first in the list — i.e. checked
  first by `collect_skips` (`platsupport.py:52-55`). Confirmed empirically before
  editing:
  ```
  @skip_if(is_driftplane, "outer reason")   # topmost
  @skip_if(is_gearshift, "inner reason")    # bottommost, closest to def
  def dummy(): ...
  dummy.__skip_guards__  ==  [(is_gearshift, 'inner reason'), (is_driftplane, 'outer reason')]
  ```
  The bottommost decorator's guard is first in the list — backwards from the natural
  top-to-bottom reading.
- **Consequence:** Currently inert — none of the two-guard tests in
  `test_platform_guards.py` (`test_unix_socket_creation`, `test_bare_thread_spawn`) have
  overlapping-true predicates for the same platform (`is_gearshift`/`is_tideline` are
  mutually exclusive by string equality), so no wrong reason is ever reported *today*.
  It's a landmine: the first time someone stacks `is_driftplane` under/over a
  more-specific guard on the same test (a natural next guard combination given
  `is_driftplane` already exists precisely to generalize over both), the reported skip
  reason will silently be the wrong one.
- **Remedy:** Insert new guards at index 0 instead of appending, so recorded order
  matches source declaration order.

Severity: **Noticeable weakness** — source-backed, doc-vs-implementation mismatch in
the module's only real logic, no live wrong behavior today, but reduces regression
resistance and credibility of the "first guard wins" contract for the next maintainer.

No other findings. No state-authority, ownership, concurrency, coupling, or
efficiency-lens issues — the code has no I/O, no async, no external dependency, and a
single clear writer/reader for every piece of state (`__skip_guards__`).

## Architect phase — Simplify Pressure Test

### Fix 1 — add a pytest-collected test asserting `collect_skips` for gearshift/tideline

1. Does it fix real ambiguity? **Yes** — closes the gap where the module's central logic
   was asserted only in a trivial case.
2. Smallest honest fix? **Yes** — one new test function, no new file, no new
   abstraction, reuses `ALL_TESTS`/`collect_skips` as-is.
3. Avoids duplicate layers? **Yes.**
4. Runtime behavior remains honest? **Yes** — test-only addition, touches no production
   code path.
5. Product improves measurably, by more than what's declined? **Yes** — `test_strategy`
   moves from "primary logic has zero real assertions under `pytest -q`" to "primary
   logic's output is pinned for both real target platforms." Nothing of comparable value
   was on the table to decline.

Structural gate: no Module removed (deletion test n/a), no new Seam (two-adapter
rule/Unified Seam Policy n/a), no old test left behind at a stale Interface.

**PASSED.**

### Fix 2 — `guards.append(...)` → `guards.insert(0, ...)` in `skip_if`

1. Does it fix real ambiguity? **Yes** — makes the implementation match the documented
   "first guard wins" contract.
2. Smallest honest fix? **Yes** — one line changed, plus a clarifying comment.
3. Avoids duplicate layers? **Yes.**
4. Runtime behavior remains honest? **Yes, and verified, not just claimed** — hand-traced
   that `is_gearshift`/`is_tideline` are mutually exclusive per platform across all 8
   current guarded tests, so no existing test's reported skip reason changes on any of
   the three defined platforms. Ran the full pytest suite before and after: identical
   pass count, `python3 test_platform_guards.py` direct-run output unchanged
   (`OK: test_platform_guards.py`, exit 0).
5. Product improves measurably? **Yes** — closes a live doc/implementation mismatch in
   the module's core logic, and it's provably load-bearing: I reverted just this one
   line, reran the new regression test, and it failed with exactly the predicted wrong
   reason (`'inner reason'` instead of `'outer reason'`), then restored the fix and
   confirmed it passes. Nothing of comparable value was declined in its place.

Structural gate: no Module removed, no new Seam, no stale tests left behind.

**PASSED.**

### Fix considered and REJECTED by SPT — wire `__skip_guards__` into real pytest `skipif` marks

Considered making `pytest -q` actually *skip* (not just correctly compute reasons for)
platform-inapplicable tests via a `conftest.py` hook translating `__skip_guards__` into
`pytest.mark.skipif`.

- Q1 (fixes real ambiguity)? No live ambiguity to fix here beyond what Fix 1 already
  closes — nothing in the codebase resolves "current platform" (there is no
  `sys.platform`-to-`gearshift`/`tideline`/`mainland` mapping anywhere; these are
  fictional sandboxed-runtime names, not real OS identifiers).
- Q2 (smallest honest fix)? **No** — doing this honestly requires inventing a
  platform-detection function with no spec, no call site, and no evidence it's needed.
  That's new speculative machinery, not a fix.
- Structural gate: no friction is proven for a new Seam here (Friction Proof Before
  Seam Recommendation) — nobody has shown pytest needs to auto-skip these; the fixture
  functions are empty stand-ins, not real assertions that would actually fail if run on
  the wrong platform.

**REJECTED** — fails Q1/Q2, would be scope-creep/YAGNI (inventing platform detection
that doesn't exist anywhere in the source). Left as a documented residual: if
`test_platform_guards.py`'s placeholder bodies are ever filled in with real
platform-sensitive assertions, this becomes worth revisiting — but not now.

## Execution phase — edits applied

**`platsupport.py`** (`skip_if`, lines 39-45): changed `guards.append((predicate, reason))`
to `guards.insert(0, (predicate, reason))`, with a comment explaining why (decorators
apply bottom-up; inserting at the front restores top-to-bottom declaration-order
priority).

**`test_platform_guards.py`**: added two new pytest-collected test functions between
`ALL_TESTS` and `main()`:
- `test_collect_skips_matches_expected_reasons_per_platform` — asserts `collect_skips`'s
  full output dict for both `"gearshift"` and `"tideline"` against every guard in
  `ALL_TESTS`.
- `test_skip_if_first_declared_guard_wins_on_overlap` — stacks two guards with
  overlapping-true predicates on a throwaway function and asserts the topmost one's
  reason wins; this is the regression test for Fix 2 (verified: fails on the pre-fix
  `append` logic with the exact wrong value, passes on the fix).

`main()` and the 8 original guarded stand-in functions were left untouched — Fix 1/2
don't need to touch the direct-run path to be correct, and touching it risked changing
the direct-run script's documented, user-visible output for no gain.

**Final `pytest -q`: 10 passed** (8 original + 2 new). **Direct run
(`python3 test_platform_guards.py`): exit 0, unchanged output.**

## Scorecard (qualitative — see scope note above)

| Dimension | Before | After | Why |
|---|---|---|---|
| test_strategy | ~6.5 | ~9 | Finding 1 closed: primary logic now has real assertions under `pytest -q` for both target platforms, plus a precedence regression test. |
| credibility | ~7.5 | ~9 | `skip_if`'s documented contract now matches its implementation; verified, not asserted. |
| state_management / ownership | 9.5 | 9.5 | Unchanged — single writer/reader for `__skip_guards__`, no drift, no change needed. |
| simplicity | 9.5 | 9.5 | Unchanged — no ceremony added; fixes are a 1-line logic change plus 2 plain-assert tests, no new abstractions, no new files. |
| concurrency | n/a | n/a | No async/threading surface in this code. |

## Summary

- **Findings raised:** 2 (Serious: `collect_skips` untested for its real target
  platforms under either invocation path; Noticeable: `skip_if` guard-precedence
  reversed vs. its documented contract).
- **Fixes applied:** 2 — both passed SPT (add gearshift/tideline coverage test; fix
  `append`→`insert(0)` guard order + regression test).
- **Fixes SPT-rejected:** 1 — wiring `__skip_guards__` into real pytest `skipif` marks,
  rejected for inventing unspecified platform-detection machinery (Q1/Q2 fail, no
  friction proven for a new Seam).
- **pytest:** PASS, 10/10 (was 8/8 before; 2 new tests added, no existing test changed
  or removed). Direct-run script (`python3 test_platform_guards.py`) also still exits 0
  with unchanged output.
