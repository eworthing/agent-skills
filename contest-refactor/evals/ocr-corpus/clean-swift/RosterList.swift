import Foundation

/// Ordered roster of member identifiers -- the same uniqueness-at-construction
/// shape as `TrackSet`, in a second aggregate, so the restraint corpus is not
/// resting on a single example.
public struct RosterList: Hashable, Sendable {
    public let memberIDs: [UUID]

    public init(memberIDs: [UUID]) throws {
        guard Set(memberIDs).count == memberIDs.count else {
            throw RosterListError.duplicateMemberID
        }
        self.memberIDs = memberIDs
    }
}

public enum RosterListError: Error, Hashable, Sendable {
    case duplicateMemberID
}
