import Foundation

/// TARGET (domain_modeling). A reservation code has a real format — four letters,
/// a dash, six digits — but the type is a bare String, so the invariant is not
/// enforced at construction. Every consumer re-derives it, and the three copies
/// below have already drifted: `isWellFormed` accepts lowercase, `shortCode`
/// assumes the dash is at index 4 without checking, and the loader accepts
/// anything non-empty. This is the anemic-domain shape the rubric names, and the
/// fix is subtractive: one failable initialiser, three call sites deleted.
public struct Reservation {
    public let code: String
    public let guestName: String
    public let partySize: Int

    public init(code: String, guestName: String, partySize: Int) {
        self.code = code
        self.guestName = guestName
        self.partySize = partySize
    }
}

public enum ReservationCheck {
    /// Copy 1 of the format rule.
    public static func isWellFormed(_ code: String) -> Bool {
        let parts = code.split(separator: "-")
        guard parts.count == 2 else { return false }
        return parts[0].count == 4 && parts[1].count == 6
    }
}

public extension Reservation {
    /// Copy 2 of the format rule — assumes the dash position instead of finding it.
    var shortCode: String {
        guard code.count >= 4 else { return code }
        return String(code.prefix(4))
    }

    /// Copy 3 — the weakest of the three; any non-empty string passes here.
    var looksUsable: Bool {
        !code.trimmingCharacters(in: .whitespaces).isEmpty
    }
}
