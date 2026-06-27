<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — Two writers to `currentTab` with no single authority (Priority 1)

- **Claim:** `TabNavigationViewModel.currentTab` is written by both `userTappedTab` and `handleNotification`, so two distinct call paths own the same navigation state without a defined authority.
- **Source:** `Sources/TabNavigationViewModel.swift:6` (`@Published var currentTab`), written at `:9` inside `userTappedTab` and at `:14` inside `handleNotification`; no single authoritative setter exists.
- **Consequence:** a push notification handler and a user tap can race to overwrite `currentTab`; the property has two writers with no precedence rule, making the tab state unpredictable when both events arrive close together.
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** introduce a single `navigateTo(_ tab: Int)` entry point; mark `currentTab` as `private(set)`; route all callers — including the notification handler — through the one setter.
