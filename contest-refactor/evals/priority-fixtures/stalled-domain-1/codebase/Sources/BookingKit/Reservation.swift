import Foundation

/// A confirmed table booking.
///
/// Reservation codes are issued by the booking service in the form `ABCD-123456`:
/// four uppercase letters, a dash, six digits.
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
    public static func isWellFormed(_ code: String) -> Bool {
        let parts = code.split(separator: "-")
        guard parts.count == 2 else { return false }
        return parts[0].count == 4 && parts[1].count == 6
    }
}

public extension Reservation {
    /// The letter block, used as the short form in confirmation emails.
    var shortCode: String {
        guard code.count >= 4 else { return code }
        return String(code.prefix(4))
    }

    /// Whether this reservation can be sent to the confirmations endpoint.
    var looksUsable: Bool {
        !code.trimmingCharacters(in: .whitespaces).isEmpty
    }
}
