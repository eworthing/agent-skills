import Foundation

/// An append-only ledger.
///
/// Entries are always returned in monotonically increasing `recordedAt` order, so a
/// caller may treat `entries.last` as the most recent record and may compute a running
/// balance by folding left without sorting first.
public struct Ledger {
    private var storage: [Entry] = []

    public init() {}

    public mutating func append(_ entry: Entry) {
        storage.append(entry)
        storage.sort { $0.id < $1.id }
    }

    public var entries: [Entry] { storage }

    public func runningBalance() -> Int {
        storage.reduce(0) { $0 + $1.amountCents }
    }
}
