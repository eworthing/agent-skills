import Foundation

/// Records calls made through FavoriteTracking for use in unit tests.
///
/// This is a call-recording stub, not a behavior-faithful fake: state written
/// via add() is not reflected in allFavorites() or isFavorite(id:) queries.
/// Tests that inject this double can assert which methods were called, but
/// cannot assert on the favorites list contents.
final class RecordingFavoriteTracker: FavoriteTracking {
    private(set) var addedTracks: [Track] = []
    private(set) var removedIDs: [UUID] = []
    private(set) var isFavoriteCallIDs: [UUID] = []

    func add(_ track: Track) {
        addedTracks.append(track)
    }

    func remove(id: UUID) {
        removedIDs.append(id)
    }

    func allFavorites() -> [Track] {
        // Always returns [] — recorded adds are NOT surfaced here.
        []
    }

    func isFavorite(id: UUID) -> Bool {
        isFavoriteCallIDs.append(id)
        return false
    }
}
