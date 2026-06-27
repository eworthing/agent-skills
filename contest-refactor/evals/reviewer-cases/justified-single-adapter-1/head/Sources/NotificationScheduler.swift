import Foundation
import UserNotifications

// MARK: — Seam (Unified Seam Policy b(ii) + b(iii))
//
// (ii) Failure-isolation: UNUserNotificationCenter auth-denied and delivery errors
//      are concentrated here; callers receive a typed NotificationError and need no
//      knowledge of UNUserNotificationCenter internals.
// (iii) Platform-isolation: UNUserNotificationCenter is daemon-bound with no
//       reliable test harness; tests inject a NotificationSchedulingDouble instead.

/// Controls local notification scheduling, cancellation, and pending-count queries.
protocol LocalNotificationScheduling {
    func scheduleReminder(title: String, body: String, at date: Date) async throws
    func cancelAll() async
    func pendingCount() async -> Int
}

/// Production adapter — delegates to UNUserNotificationCenter.current().
final class UNLocalNotificationScheduler: LocalNotificationScheduling {

    func scheduleReminder(title: String, body: String, at date: Date) async throws {
        let center = UNUserNotificationCenter.current()
        let status = await center.notificationSettings().authorizationStatus
        guard status == .authorized else {
            throw NotificationError.unauthorized
        }
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        let components = Calendar.current.dateComponents([.hour, .minute, .day], from: date)
        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: trigger
        )
        try await center.add(request)
    }

    func cancelAll() async {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }

    func pendingCount() async -> Int {
        let pending = await UNUserNotificationCenter.current().pendingNotificationRequests()
        return pending.count
    }
}

enum NotificationError: Error {
    case unauthorized
}
