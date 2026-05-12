# Review Lens: Generic (non-Apple stacks)

Apply when stack detected is Rust, Go, Python, Node, Java, Kotlin, Ruby, etc. Use alongside `architecture-rubric.md` (universal) — this lens is the language-agnostic complement to `lens-apple.md`.

## Ownership & State

- Single source of truth per mutable concern. Multi-writer state = finding.
- Hidden control flow (globals, ambient context, thread-local mutation) called out.
- Concurrency-safe access discipline: locks/channels/actors used consistently per language idiom.

## Hidden State Machines

- Booleans/optionals jointly encoding one logical state → collapse to discriminated enum/sum type/tagged union (per language).
- Loading/error/empty/content modeled as flags rather than honest model.
- State that can drift across module/cache/persistence layers.
- Async flows that can leave invalid intermediate combinations.

## Concurrency & Runtime Safety (per language)

- **Rust**: `Send` + `Sync` correctness. No `unsafe` outside justified seams. `Arc<Mutex<T>>` not used where channels or `&mut self` would do. Cancellation via `tokio::select!` or equivalent, explicit.
- **Go**: goroutine lifetime tied to context. No fire-and-forget `go func()` mutating shared state. Channels closed by sender. `context.Context` threaded through.
- **Python**: asyncio task references stored, not orphaned. `asyncio.create_task` results awaited or cancelled. GIL not assumed where `multiprocessing` is used.
- **Node**: Promise chains awaited; no floating promises. AbortController for cancellation. No event-loop blocking sync I/O.
- **JVM**: Coroutine scope ownership clear. No `GlobalScope.launch` outside top-level. Structured concurrency.

## Coupling & Leakage

- Persistence/framework leakage into runtime/domain logic.
- ORM/HTTP-framework types bleeding into domain.
- Per `architecture-rubric.md` Dependency Categorization: tag each finding with its category (in-process / local-substitutable / remote-owned / true external).

## Regression Resistance

- Business logic testable deterministically without timing hacks or sleeps.
- Failure paths modeled explicitly enough to test.
- Each mutable concern: one source of truth.
- Tests live at module interfaces. Replace, don't layer.

## Incremental Test Scoping

Used when `--test-filter <pattern>` is set on the invocation. Step 0 records `test_scope: "incremental"` and `test_filter: "<pattern>"` in CURRENT_REVIEW.json discovery (first loop only). Per-stack patterns:

- pytest: `pytest -k <pattern>`  OR  `pytest tests/<dir>/`
- cargo: `cargo test <module_path>::`
- go: `go test ./pkg/<dir>/...`
- vitest: `vitest <pattern>`  OR  `vitest --changed`
- jest: `jest --testPathPattern <pattern>`
- tox: `tox -e <env> -- -k <pattern>`

Trade-off: incremental misses regressions outside `<pattern>`. G21 in [validation.md](validation.md) requires a full-suite reverify before HALT_SUCCESS when any prior loop in REVIEW_HISTORY ran incremental.

## Generic Core Questions

1. Would experienced engineers in this language respect this as high-quality?
2. Are ownership boundaries honest and clear?
3. Is concurrency handled correctly for the runtime?
4. Is the domain modeled explicitly?
5. Is code idiomatic for the language?
6. Does test strategy reinforce strong design?
