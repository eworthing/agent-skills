<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The loop_result section below records the Unified Seam Policy justification
the reviewer reads during Check 2. -->

Discovery lens: lens-apple.md

### F1 — NotificationScheduler calls UNUserNotificationCenter directly at four sites; auth errors propagate uncaught (Priority 1)

- **Claim:** `NotificationScheduler` calls `UNUserNotificationCenter.current()` inline at every scheduling and cancellation site. The auth-denied error path (`NotificationError.unauthorized`) is `throw`-propagated to callers with no isolation boundary, requiring each caller to handle UNUserNotificationCenter-specific failure modes.
- **Source:** `Sources/NotificationScheduler.swift:14` (`UNUserNotificationCenter.current()` in `scheduleReminder`), `:34` (`cancelAll`), `:40` (`pendingCount`) — direct platform API use at three method bodies; four total call sites in `ReminderViewModel`, `OnboardingCoordinator`, `SettingsViewModel`, and `AppDelegate`.
- **Consequence:** auth-denied recovery logic is duplicated across callers; no way to inject a failing or no-op adapter for tests without the real daemon (affects CI reliability). Dependency category: `true-external` (daemon-bound platform API).
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** introduce a protocol Seam at the `UNUserNotificationCenter` boundary. A single prod adapter is justified under Unified Seam Policy (b)(ii) and (b)(iii) — see loop_result below.

**loop_result Unified Seam Policy justification:** the new `LocalNotificationScheduling` protocol has one prod adapter (`UNLocalNotificationScheduler`). This satisfies Unified Seam Policy (b)(ii) failure-isolation: auth-denied and delivery-failure error paths are concentrated in one adapter instead of spreading to all four call sites — the deletion test confirms callers would otherwise each require a `catch NotificationError.unauthorized` block. It also satisfies (b)(iii) platform-isolation: `UNUserNotificationCenter` is a system daemon-bound API whose delivery behavior cannot be reliably reproduced in XCTest without the notification daemon; the seam enables injecting a controllable `NotificationSchedulingDouble` for tests. No second adapter is needed when (b)(ii) or (b)(iii) applies. Evidence recorded in loop artifacts; no open questions.
