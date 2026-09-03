import Foundation

/// Ordered set of track identifiers. Uniqueness is enforced at construction,
/// so the invariant queue's `id_collection_no_uniqueness` signal must never
/// fire here.
public struct TrackSet: Hashable, Sendable {
    public let trackIDs: [UUID]

    public init(trackIDs: [UUID]) throws {
        guard Set(trackIDs).count == trackIDs.count else {
            throw TrackSetError.duplicateTrackID
        }
        self.trackIDs = trackIDs
    }
}

public enum TrackSetError: Error, Hashable, Sendable {
    case duplicateTrackID
}
