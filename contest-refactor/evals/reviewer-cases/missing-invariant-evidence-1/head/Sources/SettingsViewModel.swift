import Foundation
import Combine

/// Manages user settings. @Published mutations stay on the main actor via
/// MainActor.run; encoding and disk I/O run nonisolated to avoid blocking.
final class SettingsViewModel: ObservableObject {
    @Published var username: String = ""
    @Published var notificationsEnabled: Bool = true
    @Published var preferredTheme: String = "system"

    private let settingsURL: URL

    init(settingsURL: URL) {
        self.settingsURL = settingsURL
    }

    /// Captures published state on the main actor, then encodes and writes
    /// off the main thread.  Callers must await this method.
    func persist() async {
        let snapshot = await MainActor.run {
            (username, notificationsEnabled, preferredTheme)
        }
        let payload: [String: String] = [
            "username": snapshot.0,
            "notifications": snapshot.1 ? "1" : "0",
            "theme": snapshot.2
        ]
        guard let data = try? JSONEncoder().encode(payload) else { return }
        try? data.write(to: settingsURL, options: .atomic)
    }
}
