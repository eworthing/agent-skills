import Foundation

/// Maintains an ordered list of recent search queries in memory.
/// Capped at 20 entries; the oldest query is evicted when the cap is exceeded.
/// Duplicate queries are promoted to the front rather than duplicated.
final class RecentSearchesManager {
    private var searches: [String] = []
    private let cap = 20

    func record(_ query: String) {
        searches.removeAll { $0 == query }
        searches.insert(query, at: 0)
        if searches.count > cap {
            searches.removeLast()
        }
    }

    func remove(_ query: String) {
        searches.removeAll { $0 == query }
    }

    func clear() {
        searches.removeAll()
    }

    func recentQueries() -> [String] {
        searches
    }
}
