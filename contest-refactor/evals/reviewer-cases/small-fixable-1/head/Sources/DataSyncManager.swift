import Foundation

/// Runs a background data synchronisation loop at a configurable interval.
final class DataSyncManager {
    private let interval: TimeInterval
    private var syncTask: Task<Void, Never>?

    init(interval: TimeInterval = 30) {
        self.interval = interval
    }

    deinit {
        syncTask?.cancel()
    }

    func start() {
        syncTask = Task {
            while !Task.isCancelled {
                do {
                    try await performSync()
                } catch {
                    // Residual unbound Task { } — fires telemetry with no stored
                    // reference and no cancellation path. Should be stored.
                    Task {
                        await sendErrorToTelemetry(error)
                    }
                }
                try? await Task.sleep(nanoseconds: UInt64(interval * 1_000_000_000))
            }
        }
    }

    private func performSync() async throws {
        // Sync logic placeholder.
    }

    private func sendErrorToTelemetry(_ error: Error) async {
        // Send error metadata to telemetry service.
    }
}
