// Ordered, duplicate-checked containers whose "replace" operation swaps one
// member for another while it keeps its position: append the new member,
// swap it into the old member's slot, then drop the old member from the
// end. Two container shapes need this -- a plain ordered set of tags, and
// an ordered set of labels each paired with a value -- and each owns its
// own duplicate/not-found checks and its own diagnostic wording.

enum ReplaceOutcome: Equatable {
    case success
    case trapped(String)
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
        items.append(new)
        items.swapAt(pos, items.count - 1)
        items.removeLast()
        return .success
    }
}

struct Ledger {
    var roster = Roster()
    var values: [Int] = []

    var lookupCount: Int { roster.lookupCount }

    @discardableResult
    mutating func replaceLabel(_ old: String, with new: String, value: Int) -> ReplaceOutcome {
        if new != old, roster.contains(new) {
            return .trapped("label already in use: '\(new)'")
        }
        guard let pos = roster.position(of: old) else {
            return .trapped("no entry at that position")
        }
        roster.items.append(new)
        roster.items.swapAt(pos, roster.items.count - 1)
        roster.items.removeLast()
        values.append(value)
        values.swapAt(pos, values.count - 1)
        values.removeLast()
        return .success
    }
}
