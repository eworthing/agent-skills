<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — RecentSearchesManager is a bare in-memory collection with no Seam or Locality (Priority 1)

- **Claim:** `RecentSearchesManager` is a `final class` wrapping a plain `[String]` array injected at two call sites as a concrete type. The diff introduces `RecentSearchesRepository` protocol and renames the impl `InMemoryRecentSearchesRepository`, but the protocol interface is a 1:1 mirror of the implementation — same four methods, same signatures, no added policy or behavior. No test fake is added as a second Adapter.
- **Source:** `Sources/RecentSearchesRepository.swift:4` (`protocol RecentSearchesRepository`) — four methods declared verbatim matching `InMemoryRecentSearchesRepository:8`–`:32`; only one conformer exists.
- **Consequence:** The protocol/impl split passes the deletion test in neither direction: deleting the protocol collapses to one concrete type (no harm); deleting the impl leaves a protocol with no home. No policy is captured (the 20-entry cap lives inside the impl, not the Interface). No failure isolation (in-process array; no error surface). No second Adapter means the Seam is hypothetical. This is repository theater — the Interface adds no Locality, no replacement value, and no failure policy.
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** either (a) inline `InMemoryRecentSearchesRepository` back to a single type and drop the protocol (the in-process state does not need a Seam), or (b) if testability is the goal, add a behavior-faithful `FakeRecentSearchesRepository` that actually maintains its own `[String]` state so the Two-Adapter rule is met.
