import Foundation

/// Seam for the favorites store. Lets callers hold a protocol reference
/// instead of the concrete FavoritesService type.
protocol FavoriteTracking {
    func add(_ track: Track)
    func remove(id: UUID)
    func allFavorites() -> [Track]
    func isFavorite(id: UUID) -> Bool
}
