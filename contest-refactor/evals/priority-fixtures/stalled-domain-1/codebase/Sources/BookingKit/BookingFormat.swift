import Foundation

/// Display helpers for the bookings list. Presentation only — nothing here is
/// persisted, sent, or used to make a booking decision.
public enum BookingFormat {
    /// Badge text for the covers count on a service summary row.
    public static func badge(_ count: Int) -> String {
        count > 999 ? "999+" : String(count)
    }

    public static func partyLabel(_ size: Int) -> String {
        switch size {
        case 1: return "1 guest"
        default: return "\(size) guests"
        }
    }

    public static func initials(_ name: String) -> String {
        name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined()
    }
}
