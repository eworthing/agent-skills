import Foundation

public protocol ConfirmationsEndpoint: Sendable {
    func upload(_ payload: Data) async throws
}

/// Uploads pending entries to the third-party confirmations endpoint.
public final class SyncCoordinator: @unchecked Sendable {
    private var pending: [Entry] = []
    private let endpoint: ConfirmationsEndpoint
    private let policy: RetryPolicy
    private let queue = DispatchQueue(label: "ledgerkit.sync")

    public init(endpoint: ConfirmationsEndpoint, policy: RetryPolicy = RetryPolicy()) {
        self.endpoint = endpoint
        self.policy = policy
    }

    public func enqueue(_ entry: Entry) {
        queue.sync { pending.append(entry) }
    }

    public func flush() async {
        let batch = queue.sync { pending }
        for entry in batch {
            var attempt = 1
            while true {
                do {
                    try await endpoint.upload(Data(entry.id.utf8))
                    queue.sync { pending.removeAll { $0.id == entry.id } }
                    break
                } catch {
                    guard policy.shouldRetry(attempt: attempt, error: error) else { break }
                    attempt += 1
                }
            }
        }
    }

    public var pendingCount: Int { queue.sync { pending.count } }
}
