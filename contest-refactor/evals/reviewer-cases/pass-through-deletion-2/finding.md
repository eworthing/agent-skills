<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — SettingsStoreProxy is a pass-through Module over SettingsStore with no added policy, failure isolation, or Leverage (Priority 1)

- **Claim:** `SettingsStoreProxy` delegates every method call to `SettingsStore` without adding policy, failure isolation, throttling, validation, or retry behavior.
- **Source:** `Sources/SettingsStoreProxy.swift:10–12` — `current()` returns `await store.current` verbatim; `:14–16` — `update(_:)` calls `await store.update(settings)` verbatim; `:18–20` — `updateTheme(_:)` calls `await store.updateTheme(mode)` verbatim. Deletion test: removing the proxy and calling `SettingsStore` directly produces identical behavior with no complexity reappearing at call sites.
- **Consequence:** callers bear an extra indirection with no Leverage; two files to navigate and maintain for every change to the settings contract (Unified Seam Policy: no second Adapter, no policy/failure/platform justification).
- **Severity:** Noticeable weakness.
- **Remedy (minimal_correction_path):** delete `SettingsStoreProxy`; update callers to hold `SettingsStore` directly.
