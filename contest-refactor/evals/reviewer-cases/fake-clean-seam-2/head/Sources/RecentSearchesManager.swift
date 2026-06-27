import Foundation

// RecentSearchesManager retained for call-site compatibility during the
// migration; callers are expected to reference RecentSearchesRepository
// at injection sites in a follow-up loop.
typealias RecentSearchesManager = InMemoryRecentSearchesRepository
