import Foundation

/// A single posting against an account. Amounts are minor units (pence, cents).
public struct Posting {
    public let account: String
    public let amountMinor: Int
    public let memo: String

    public init(account: String, amountMinor: Int, memo: String) {
        self.account = account
        self.amountMinor = amountMinor
        self.memo = memo
    }
}

/// Splits a total across N ways. The remainder goes to the first posting so the
/// parts always sum back to the total.
public enum Split {
    public static func evenly(_ totalMinor: Int, ways: Int) -> [Int] {
        guard ways > 0 else { return [] }
        let base = totalMinor / ways
        let remainder = totalMinor - (base * ways)
        var parts = Array(repeating: base, count: ways)
        parts[0] += remainder
        return parts
    }
}

public enum Settlement {
    /// Settling a bill re-implements the remainder rule rather than calling
    /// `Split.evenly`, and the two have already diverged: this one drops the
    /// remainder instead of assigning it, so settled postings can sum to less
    /// than the bill.
    public static func postings(total totalMinor: Int, across accounts: [String]) -> [Posting] {
        guard !accounts.isEmpty else { return [] }
        let base = totalMinor / accounts.count
        return accounts.map { Posting(account: $0, amountMinor: base, memo: "settlement") }
    }
}
