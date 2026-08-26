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

let word = makeCommandWord(ticket: 1000, lane: 42, tier: 5)
check(ticketNumber(from: word) == 1000, "ticket number should round-trip")
check(laneNumber(from: word) == 42, "belt lane should round-trip")
check(tierLevel(from: word) == 5, "handling tier should round-trip")

print("OK: main.swift")
