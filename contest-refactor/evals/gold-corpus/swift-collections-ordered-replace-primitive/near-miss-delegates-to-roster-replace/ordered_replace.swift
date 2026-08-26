// Ordered, duplicate-checked containers whose "replace" operation swaps one
// member for another while it keeps its position. Each container owns its
// own duplicate/not-found checks and its own diagnostic wording; the
// three-step move itself -- append the new member, swap it into the old
// member's slot, drop the old member from the end -- is the one piece
// shared between them, taking the position each caller already resolved
// rather than re-resolving it.

enum ReplaceOutcome: Equatable {
    case success
    case trapped(String)
}

/// Moves `new` into `storage` at `position`, dropping whatever was there.
/// Takes an already-resolved position rather than looking one up itself.
func moveIntoPlace<T>(_ storage: inout [T], new: T, replacingPositionOf position: Int) {
    storage.append(new)
    storage.swapAt(position, storage.count - 1)
    storage.removeLast()
}

struct Roster {
    var items: [String] = []
    var lookupCount = 0

    func contains(_ tag: String) -> Bool {
        items.contains(tag)
    }

    mutating func position(of tag: String) -> Int? {
        lookupCount += 1
        return items.firstIndex(of: tag)
    }

    @discardableResult
    mutating func replace(_ old: String, with new: String) -> ReplaceOutcome {
        if new != old, contains(new) {
            return .trapped("member already present")
        }
        guard let pos = position(of: old) else {
            return .trapped("position outside roster")
        }
        moveIntoPlace(&items, new: new, replacingPositionOf: pos)
        return .success
    }
}

struct Ledger {
    var roster = Roster()
    var values: [Int] = []

    var lookupCount: Int { roster.lookupCount }

    /// Delegates the label-side check and move to Roster's own public
    /// replace -- one call covers duplicate checking, not-found checking,
    /// and the move together, instead of repeating that logic here.
    @discardableResult
    mutating func replaceLabel(_ old: String, with new: String, value: Int) -> ReplaceOutcome {
        switch roster.replace(old, with: new) {
        case .trapped(let message):
            return .trapped(message)
        case .success:
            break
        }
        guard let pos = roster.position(of: new) else {
            return .trapped("no entry at that position")
        }
        moveIntoPlace(&values, new: value, replacingPositionOf: pos)
        return .success
    }
}
