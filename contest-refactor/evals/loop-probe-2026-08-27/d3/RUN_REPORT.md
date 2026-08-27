# Architecture Review — service_listener.py

Target: `service_listener.py` (159 lines) + `test_service_listener.py` (65 lines), a synchronous
simulation of listener-socket provisioning (bind/reuse/inheritance/backlog/handoff), no real I/O.
Stack lens: `lens-generic.md` (Python). Baseline: `python3 -m pytest -q` — 5 passed.

---

## Critic phase — Findings

### Finding 1 — Bind-conflict path is completely untested (Serious deduction)

- **Claim:** `Service.__init__`'s only failure-handling branch (`EndpointInUseError` → print → `terminate(1)`) has zero test coverage, despite `terminate()`'s own docstring claiming it exists specifically to make that path testable.
- **Source:**
  - `service_listener.py:81-87` — `terminate()`: `"""...A thin, overridable wrapper around the real exit call so a test can observe that this path was taken without actually ending the process."""`
  - `service_listener.py:110-115` — the only call site: `except EndpointInUseError: print(...); terminate(1); return`
  - `test_service_listener.py` (pre-fix, 5 tests) — none binds the same endpoint twice or monkeypatches `terminate`.
- **Consequence:** This is the one non-trivial branch in the module — the safety net stopping two `Service`s from silently colliding on a port. A mutation deleting the `except` clause, changing `terminate(1)` to `terminate(0)`, or dropping the stderr message would pass the full suite. `test_strategy` and `credibility` both take the hit: the docstring's testability claim was aspirational, not real.
- **Remedy:** Add a test that occupies an endpoint, monkeypatches `service_listener.terminate` to a recorder, constructs a conflicting `Service`, and asserts `terminate` was called with `1`.

### Finding 2 — `start_with_handoff`'s only test can't catch a capture-order regression (Serious deduction)

- **Claim:** The sole test of `start_with_handoff` — the function whose own docstring calls it "the shape a warm restart uses" — only asserts `isinstance(descriptor_id, int)`.
- **Source:**
  - `service_listener.py:154-157` — `descriptor_id = listener.descriptor_id` then `listener.close()` then `return descriptor_id`. Correctness depends on capturing the id **before** closing (a closed listener reports `-1`, per `descriptor_id`'s own docstring at `service_listener.py:46-49`).
  - `test_service_listener.py:33-35` (pre-fix) — `assert isinstance(descriptor_id, int)`.
- **Consequence:** `-1` is still an `int`. Swapping the two lines (close, then read) — the exact kind of mutation Step 8's mutation-test model asks for — silently returns a dead descriptor id to "the successor" and the test still passes. Real regression risk on a named primary flow.
- **Remedy:** Add `assert descriptor_id >= 0` alongside the existing `isinstance` check.

### Finding 3 — Two write-only "state with no authority" sites (Noticeable weakness)

- **Claim:** Two pieces of state are written but never read by anything — application or test.
- **Source:**
  - `service_listener.py:19` (pre-fix) `_OPEN_DESCRIPTORS: set[int] = set()`, written at `:40` (`.add`) and `:70` (`.discard`), read nowhere. The `Listener` class docstring (`:28-32`, pre-fix) claimed this makes a leaked instance *"observable from outside"* — but no function ever exposed the set, so the claim was never true even on its own terms.
  - `service_listener.py:64` (pre-fix) `self.backlog = backlog` in `activate()`, read nowhere — including by `test_provisioned_listener_has_reuse_and_inheritance_enabled`, which asserts the two sibling attributes (`reuse_enabled`, `inheritable`) set in the same constructor sequence but skips `backlog`.
- **Consequence:** `_OPEN_DESCRIPTORS` is dead ledger state duplicating what `descriptor_id` already reports per-instance (canon smell: *state with no authority*), plus a doc/code honesty gap. `backlog` is the one simulated socket option with no test-side observation, and — unlike `_endpoint`, which defaults to `None` in `__init__` — has no declared default, so a `Listener` that never reaches `activate()` (e.g. the `bind=False` placeholder) has no `.backlog` attribute at all until something sets it.
- **Remedy:** Delete the dead `_OPEN_DESCRIPTORS` ledger and its two mutation sites, correct the docstring; give `backlog` a `None` default matching `_endpoint`'s convention, and extend the existing reuse/inheritance test to assert it.

### Flagged, not fixed — `start_with_handoff` may release the endpoint prematurely (unresolved question, scope-limited)

`start_with_handoff`'s `listener.close()` (`service_listener.py:157`, unchanged) discards the endpoint from `_BOUND_ENDPOINTS` as a side effect of closing. In a real warm-restart, the successor is still occupying that port, so the ledger arguably should stay "in use" until the successor takes over — but this codebase has no successor-side code (no `Listener.from_descriptor_id()` or equivalent), and `_BOUND_ENDPOINTS` is a plain module global that wouldn't survive a real cross-process handoff anyway. I cannot derive the correct behavior from source, docs, or tests — this is exactly the "chain cannot be shown" case in the Evidence Chain rule. I did not design or attempt a fix; recording it as an open question rather than manufacturing a finding.

---

## Architect phase — Simplify Pressure Test

### Fix A (Finding 1) — add bind-conflict test — **PASSED**

1. Does it fix real ambiguity? **Yes** — whether the conflict path still fires correctly is currently unverifiable.
2. Is it the smallest honest fix? **Yes** — one test function, no production change.
3. Does it avoid duplicate layers? **Yes** — reuses existing `Service`/`provision_listener`.
4. Does runtime behavior remain honest? **Yes** — test-only; production code unchanged.
5. Does the product improve, by more than what's declined? **Yes** — closes the only untested failure path in the module; nothing of comparable value was on the table to decline.
Structural gate: no Module removed, no new Seam, N/A — passes vacuously.

### Fix B (Finding 2) — strengthen handoff assertion — **PASSED**

1. Real ambiguity? **Yes** — the capture-before-close invariant was unverified.
2. Smallest honest fix? **Yes** — one added assertion line.
3. Avoids duplicate layers? **Yes**.
4. Runtime honest? **Yes** — test-only.
5. Product improves more than declined? **Yes** — closes a named mutation-test gap on the "warm restart" primary flow; trivial cost.
Structural gate: N/A — passes vacuously.

### Fix C (Finding 3) — delete dead ledger, default + test `backlog` — **PASSED**

1. Real ambiguity? **Yes** — dead state posing as a documented feature, and an untested activation step.
2. Smallest honest fix? **Yes** — subtraction (`_OPEN_DESCRIPTORS`) plus one default plus one assertion, following the exact pattern already used for `_endpoint`, `reuse_enabled`, `inheritable`.
3. Avoids duplicate layers? **Yes** — no new abstraction added.
4. Runtime honest? **Yes** — `_OPEN_DESCRIPTORS` had no reader, so removing it changes nothing observable; `backlog`'s default only fills a previously-undefined attribute.
5. Product improves more than declined? **Yes** — removes a false docstring claim and closes the last unasserted constructor-set attribute; the rejected alternative (adding an accessor, see below) would have cost more for less.
Structural gate: no Module removed (attribute/global deletion, not a Module), no new Seam, tests-at-Interface N/A — passes vacuously.

### Rejected candidate 1 — add `open_descriptor_count()` accessor instead of deleting `_OPEN_DESCRIPTORS`

1. Fixes real ambiguity? Partially — it would make the docstring's claim true, but doesn't address that nothing needs it.
2. Smallest honest fix? **No** — deletion is strictly smaller.
3. Avoids duplicate layers? **No** — adds public API surface with zero current callers.
4. Runtime honest? Yes (neutral).
5. Product improves by more than declined? **No** — purely speculative (YAGNI); declines the simpler, safer subtractive fix for no present value.
**REJECTED** — fails Q2, Q3, Q5.

### Rejected candidate 2 — make `Service.listener` `Optional[Listener]` instead of a throwaway placeholder

1. Fixes real ambiguity? **No** — the current `bind=False` placeholder-then-close behavior is already the documented, intentional fix from `CHANGES.md` (a prior bug: it used to leak).
2. Smallest honest fix? **No** — introduces `None`-checks at every `self.listener` use site (`close()`, `start_service`'s `adopt` overwrite), which is more ceremony than one cheap throwaway allocation.
3. Avoids duplicate layers? Neutral — no new layer, but worse Locality (type-narrowing scattered across the class).
4. Runtime honest? Yes (neutral).
5. Product improves by more than declined? **No** — the "gain" (avoiding one object churn) is not measurable; the cost (Optional-typing burden) is larger.
**REJECTED** — fails Q2 and Q5.

---

## Execution phase

### Edits applied

**`service_listener.py`**
- Deleted `_OPEN_DESCRIPTORS: set[int] = set()` (module global) and its two mutation sites (`.add()` in `Listener.__init__`, `.discard()` in `Listener.close()`).
- Rewrote the `Listener` class docstring to drop the false "observable from outside" ledger claim; now points to `descriptor_id` as the real observability contract.
- Added `self.backlog: int | None = None` to `Listener.__init__`, matching the existing `_endpoint` default-then-set-later convention.

**`test_service_listener.py`**
- Added `import service_listener` and `DEFAULT_BACKLOG`, `Service` to the existing import.
- `test_start_with_handoff_returns_an_int`: added `assert descriptor_id >= 0`.
- Renamed `test_provisioned_listener_has_reuse_and_inheritance_enabled` → `test_provisioned_listener_has_reuse_inheritance_and_backlog_set`; added `assert listener.backlog == DEFAULT_BACKLOG`.
- Added `test_bind_conflict_prints_and_terminates_instead_of_raising` (monkeypatches `service_listener.terminate`, occupies an endpoint, constructs a conflicting `Service`, asserts `terminate` was called with `1`).
- Updated `main()` to call the renamed and new test functions.

No behavior changes to any caller-visible contract: every endpoint that bound before still binds the same way with the same reuse/inheritance/backlog settings.

### Final test result

```
$ python3 -m pytest -q
......                                                                   [100%]
6 passed in 0.01s

$ python3 test_service_listener.py
endpoint already in use: ('conflict', 8906)
OK: test_service_listener.py
(exit 0)
```

(The stderr line is the production code's own conflict message, fired legitimately by the new test — not a failure.)

---

## Final Scorecard

| Dimension | Score | Residual (accepted) |
|---|---|---|
| Architecture quality | 9 | `Service(endpoint, bind=False)` builds-then-immediately-closes a throwaway `Listener()` placeholder (`:103-107`) rather than an `Optional` field — SPT-rejected as a fix (see above), accepted as-is. |
| State management & runtime ownership | 9 | The `start_with_handoff` endpoint-release question above — genuinely underspecified from source, flagged not fixed. |
| Concurrency & runtime safety | 9 | N/A in practice — module is fully synchronous, no asyncio/threads; no concurrent-access test exists because there's no concurrency to race. |
| Test strategy & regression resistance | 9 | Same handoff-release question — its correct behavior can't be asserted until the ledger-during-handoff contract is decided. |
| Overall implementation credibility | 9 | As above; both prior doc/behavior mismatches (Findings 1 & 3) are now closed. |
| Domain modeling | 9 | Endpoint modeled as a bare `tuple[str, int]` rather than a small named type — no proven ambiguity or harm found, so not promoted to a finding. |
| Data flow & dependency design | 9 | `_BOUND_ENDPOINTS` module global is a deliberate, honest model of a process-wide OS resource (ports are genuinely global) — not a smell here. |
| Framework / platform idioms (Python) | 9 | None named. |
| Code simplicity & clarity | 9 | `provision_listener` is a thin wrapper over `start_service(...).listener`, but earns its keep across 5 real call sites (4 tests + `start_with_handoff`) — deletion test doesn't justify removing it. |

Every dimension anchors at 9 ("contest-grade... few honesty leaks... remaining complexity earns its keep") rather than 9.5+, because the `start_with_handoff` ledger question is a real, unresolved gap I chose not to paper over with a guessed fix.
