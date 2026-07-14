import Foundation

/// Refreshes cached summaries for a set of feed identifiers.
public struct FeedRefresher {
    public struct Summary: Equatable, Sendable {
        public let id: String
        public let itemCount: Int

        public init(id: String, itemCount: Int) {
            self.id = id
            self.itemCount = itemCount
        }
    }

    /// Fetches one feed summary by id. Calls are concurrency-safe: the backing
    /// service imposes no serial-ordering, back-off, or rate-limit requirement,
    /// though callers must keep at most 4 requests in flight at once.
    public let fetchSummary: @Sendable (String) async throws -> Summary

    public init(fetchSummary: @escaping @Sendable (String) async throws -> Summary) {
        self.fetchSummary = fetchSummary
    }

    /// Returns fresh summaries keyed by feed id. Checks for cancellation once per
    /// id so a cancelled parent task stops the refresh promptly regardless of
    /// whether `fetchSummary` itself cooperates with cancellation.
    public func refreshAll(ids: [String]) async throws -> [String: Summary] {
        var summaries: [String: Summary] = [:]
        for id in ids {
            try Task.checkCancellation()
            summaries[id] = try await fetchSummary(id)
        }
        return summaries
    }

    /// Walks a pagination chain starting at `cursor`. Each request consumes the
    /// cursor returned by the previous one, so the calls are inherently ordered.
    /// Static because the chain depends only on `fetchPage`, never on a
    /// refresher instance. Checks for cancellation once per page for the same
    /// reason as `refreshAll`.
    public static func collectPages(
        from cursor: String,
        fetchPage: @Sendable (String) async throws -> (items: [String], nextCursor: String?)
    ) async throws -> [String] {
        var items: [String] = []
        var next: String? = cursor
        while let cursor = next {
            try Task.checkCancellation()
            let page = try await fetchPage(cursor)
            items.append(contentsOf: page.items)
            next = page.nextCursor
        }
        return items
    }
}
