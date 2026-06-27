import Foundation
import UserNotifications

/// Schedules, cancels, and counts local push notifications for reminders.
/// Calls UNUserNotificationCenter directly at every site — no Seam.
final class NotificationScheduler {

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
