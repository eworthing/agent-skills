import Foundation

struct Track: Identifiable, Equatable {
    let id: UUID
    let title: String
    let artist: String
}

/// Manages the in-memory set of user-favorited tracks.
/// Injected as a concrete type into FavoritesViewModel, SearchResultsViewModel,
/// and ProfileViewModel — no protocol boundary at any injection site.
final class FavoritesService {
    private var favorites: [Track] = []

    func add(_ track: Track) {
        guard !favorites.contains(where: { $0.id == track.id }) else { return }
        favorites.append(track)
    }

    func remove(id: UUID) {
        favorites.removeAll { $0.id == id }
    }

    func allFavorites() -> [Track] {
        favorites
    }

    func isFavorite(id: UUID) -> Bool {
        favorites.contains { $0.id == id }
    }
}
