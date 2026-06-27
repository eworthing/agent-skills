import Foundation

/// Runs a background data synchronisation loop at a configurable interval.
final class DataSyncManager {
    private let interval: TimeInterval

    init(interval: TimeInterval = 30) {
        self.interval = interval
    }

    func start() {
        // Targeted finding: unbound Task { } — no stored reference, no cancellation path.
        Task {
            while true {
                await performSync()
                try? await Task.sleep(nanoseconds: UInt64(interval * 1_000_000_000))
            }
        }
    }

    private func performSync() async {
        // Sync logic placeholder.
    }
}
