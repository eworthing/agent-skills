import Foundation

struct AppSettings: Codable, Sendable {
    var themeMode: String
    var notificationsEnabled: Bool
    var fontSize: Int
}

/// Single owner of persisted application settings.
actor SettingsStore {
    private(set) var current = AppSettings(
        themeMode: "system",
        notificationsEnabled: true,
        fontSize: 16
    )

    func update(_ settings: AppSettings) {
        current = settings
    }

    func updateTheme(_ mode: String) {
        current.themeMode = mode
    }
}
