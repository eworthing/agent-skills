import XCTest

@testable import FeedKit

/// Holds every transport call in flight until the test releases it, recording the
/// peak number of concurrent calls. Actor-serialized continuations only — no
/// timing sleeps, so overlap measurement is deterministic.
actor TransportGate {
    private var inFlight = 0
    private(set) var peak = 0
    private var held: [CheckedContinuation<Void, Never>] = []
    private var driver: CheckedContinuation<Void, Never>?
    private var finished = false

    func enter() {
        inFlight += 1
        peak = max(peak, inFlight)
    }

    func hold() async {
        await withCheckedContinuation { continuation in
            held.append(continuation)
            driver?.resume()
            driver = nil
        }
    }

    func exit() {
        inFlight -= 1
    }

    func finish() {
        finished = true
        driver?.resume()
        driver = nil
    }

    /// Suspends until at least one call is held.
    func waitUntilHeld() async {
        while held.isEmpty {
            await withCheckedContinuation { continuation in
                driver = continuation
            }
        }
    }

    /// Releases one held call, suspending until one is available. Returns false
    /// once the refresh finished and nothing remains held.
    func drainStep() async -> Bool {
        while true {
            if !held.isEmpty {
                held.removeFirst().resume()
                return true
            }
            if finished {
                return false
            }
            await withCheckedContinuation { continuation in
                driver = continuation
            }
        }
    }
}

final class FeedRefresherTests: XCTestCase {
    func testKeyedResultsForAllIds() async throws {
        let refresher = FeedRefresher { id in .init(id: id, itemCount: id.count) }
        let ids = (0..<12).map { "feed-\($0)" }
        let summaries = try await refresher.refreshAll(ids: ids)
        XCTAssertEqual(summaries.count, ids.count)
        for id in ids {
            XCTAssertEqual(summaries[id], .init(id: id, itemCount: id.count))
        }
    }

    func testResultsIndependentOfIdOrder() async throws {
        let refresher = FeedRefresher { id in .init(id: id, itemCount: id.count) }
        let ids = (0..<12).map { "feed-\($0)" }
        let forward = try await refresher.refreshAll(ids: ids)
        let backward = try await refresher.refreshAll(ids: ids.reversed())
        XCTAssertEqual(forward, backward)
    }

    func testPerFeedErrorPropagates() async {
        struct FetchError: Error, Equatable {
            let id: String
        }
        let refresher = FeedRefresher { id in
            if id == "feed-3" {
                throw FetchError(id: id)
            }
            return .init(id: id, itemCount: id.count)
        }
        do {
            _ = try await refresher.refreshAll(ids: (0..<8).map { "feed-\($0)" })
            XCTFail("expected FetchError")
        } catch let error as FetchError {
            XCTAssertEqual(error, FetchError(id: "feed-3"))
        } catch {
            XCTFail("unexpected error: \(error)")
        }
    }

    func testAtMostFourFetchesInFlight() async throws {
        let gate = TransportGate()
        let refresher = FeedRefresher { id in
            await gate.enter()
            await gate.hold()
            await gate.exit()
            return .init(id: id, itemCount: id.count)
        }
        let ids = (0..<24).map { "feed-\($0)" }
        let refresh = Task { try await refresher.refreshAll(ids: ids) }
        let watcher = Task {
            _ = try? await refresh.value
            await gate.finish()
        }
        while await gate.drainStep() {}
        _ = await watcher.value
        let summaries = try await refresh.value
        XCTAssertEqual(summaries.count, ids.count)
        let peak = await gate.peak
        XCTAssertLessThanOrEqual(peak, 4, "callers must keep at most 4 fetches in flight")
    }

    func testCancellingParentTaskStopsRefresh() async {
        let gate = TransportGate()
        let refresher = FeedRefresher { id in
            await gate.enter()
            await gate.hold()
            await gate.exit()
            try Task.checkCancellation()
            return .init(id: id, itemCount: id.count)
        }
        let refresh = Task { try await refresher.refreshAll(ids: (0..<6).map { "feed-\($0)" }) }
        await gate.waitUntilHeld()
        refresh.cancel()
        let watcher = Task {
            _ = try? await refresh.value
            await gate.finish()
        }
        while await gate.drainStep() {}
        _ = await watcher.value
        do {
            _ = try await refresh.value
            XCTFail("expected CancellationError")
        } catch is CancellationError {
            // expected: cancelling the parent terminates the refresh
        } catch {
            XCTFail("unexpected error: \(error)")
        }
    }

    func testPaginationChainFollowsCursors() async throws {
        let pages: [String: (items: [String], nextCursor: String?)] = [
            "p1": (["a", "b"], "p2"),
            "p2": (["c"], "p3"),
            "p3": (["d"], nil),
        ]
        struct MissingPage: Error {}
        let refresher = FeedRefresher { id in .init(id: id, itemCount: id.count) }
        let items = try await refresher.collectPages(from: "p1") { cursor in
            guard let page = pages[cursor] else { throw MissingPage() }
            return page
        }
        XCTAssertEqual(items, ["a", "b", "c", "d"])
    }
}
