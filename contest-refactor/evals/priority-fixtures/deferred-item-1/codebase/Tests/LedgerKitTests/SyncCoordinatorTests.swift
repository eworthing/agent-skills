import Foundation
import Testing
@testable import LedgerKit

private final class StubEndpoint: ConfirmationsEndpoint, @unchecked Sendable {
    var uploads: [Data] = []
    func upload(_ payload: Data) async throws { uploads.append(payload) }
}

@Test func flushClearsPendingOnSuccess() async {
    let stub = StubEndpoint()
    let coordinator = SyncCoordinator(endpoint: stub)
    coordinator.enqueue(Entry(id: "a", recordedAt: Date(), amountCents: 1, memo: "m"))
    await coordinator.flush()
    #expect(coordinator.pendingCount == 0)
    #expect(stub.uploads.count == 1)
}
