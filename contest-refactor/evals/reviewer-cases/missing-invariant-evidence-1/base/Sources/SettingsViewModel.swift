import Foundation
import Combine

/// Manages user settings. All methods inherit @MainActor isolation because
/// the @Published properties are directly bound to SwiftUI views.
///
/// persist() encodes and writes to disk synchronously on the main actor —
/// the targeted finding: blocking I/O on the render thread.
@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var username: String = ""
    @Published var notificationsEnabled: Bool = true
    @Published var preferredTheme: String = "system"

    private let settingsURL: URL

    init(settingsURL: URL) {
        self.settingsURL = settingsURL
    }

    /// Blocks the main actor: JSONEncoder + Data.write run synchronously.
    func persist() {
        let payload: [String: String] = [
            "username": username,
            "notifications": notificationsEnabled ? "1" : "0",
            "theme": preferredTheme
        ]
        guard let data = try? JSONEncoder().encode(payload) else { return }
        try? data.write(to: settingsURL, options: .atomic)
    }
}
