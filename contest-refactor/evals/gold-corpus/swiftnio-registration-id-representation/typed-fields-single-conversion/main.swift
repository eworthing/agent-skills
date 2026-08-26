// command_word's own bundled test suite.
//
// Run: swiftc command_word.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

let assignment = RoutingAssignment(
    ticket: TicketID(rawValue: 1000)!,
    lane: BeltLane(rawValue: 42),
    tier: HandlingTier(rawValue: 5)
)
let packed = ConveyorCommandWord(assignment)
let unpacked = packed.assignment
check(unpacked.ticket.rawValue == 1000, "ticket number should round-trip")
check(unpacked.lane.rawValue == 42, "belt lane should round-trip")
check(unpacked.tier.rawValue == 5, "handling tier should round-trip")

check(ticketNumber(from: packed.rawValue) == 1000, "decode accessor: ticket number should round-trip")
check(laneNumber(from: packed.rawValue) == 42, "decode accessor: belt lane should round-trip")
check(tierLevel(from: packed.rawValue) == 5, "decode accessor: handling tier should round-trip")

print("OK: main.swift")
