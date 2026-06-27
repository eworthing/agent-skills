import Foundation

/// Abstraction over the recent-searches store.
protocol RecentSearchesRepository {
    func record(_ query: String)
    func remove(_ query: String)
    func clear()
    func recentQueries() -> [String]
}

/// In-memory implementation — the only conformer.
/// Maintains an ordered list capped at 20 entries; duplicates are promoted.
final class InMemoryRecentSearchesRepository: RecentSearchesRepository {
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
