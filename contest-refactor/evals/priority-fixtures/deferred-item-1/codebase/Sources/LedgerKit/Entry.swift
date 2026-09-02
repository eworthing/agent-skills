import Foundation

public struct Entry: Equatable, Sendable {
    public let id: String
    public let recordedAt: Date
    public let amountCents: Int
    public let memo: String

    public init(id: String, recordedAt: Date, amountCents: Int, memo: String) {
        self.id = id
        self.recordedAt = recordedAt
        self.amountCents = amountCents
        self.memo = memo
    }
}
