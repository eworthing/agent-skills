import Foundation

/// Refreshes cached summaries for a set of feed identifiers.
struct FeedRefresher {
    struct Summary: Equatable, Sendable {
        let id: String
        let itemCount: Int
    }

    /// Fetches one feed summary by id. Calls are concurrency-safe: the backing
    /// service imposes no serial-ordering, back-off, or rate-limit requirement,
    /// though callers must keep at most 4 requests in flight at once.
    let fetchSummary: @Sendable (String) async throws -> Summary

    /// Returns fresh summaries keyed by feed id.
    func refreshAll(ids: [String]) async throws -> [String: Summary] {
        var summaries: [String: Summary] = [:]
        for id in ids {
            summaries[id] = try await fetchSummary(id)
        }
        return summaries
    }

    /// Walks a pagination chain starting at `cursor`. Each request consumes the
    /// cursor returned by the previous one, so the calls are inherently ordered.
    func collectPages(
        from cursor: String,
        fetchPage: @Sendable (String) async throws -> (items: [String], nextCursor: String?)
    ) async throws -> [String] {
        var items: [String] = []
        var next: String? = cursor
        while let cursor = next {
            let page = try await fetchPage(cursor)
            items.append(contentsOf: page.items)
            next = page.nextCursor
        }
        return items
    }
}
