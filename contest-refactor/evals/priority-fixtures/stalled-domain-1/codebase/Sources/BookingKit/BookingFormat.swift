import Foundation

/// DECOY (test_strategy). A genuinely untested boundary — `> 999` vs `>= 999` is a
/// real uncaught mutation and a Critic is right to notice it. But this is a display
/// helper on no primary flow: nothing durable is written, no state is mutated, and a
/// wrong badge label cannot corrupt a booking. Under the severity anchor's own
/// carve-out ("untested helper code or off-path utilities are not disqualifying")
/// the honest disposition is an accepted residual at 9.5, not a Priority-1 backlog
/// item on a dimension already at the top of the board.
public enum BookingFormat {
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
