// ordered_replace's own bundled test suite (this variant).
//
// Run: swiftc ordered_replace.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

var roster = Roster(items: ["alpha", "beta", "gamma"])
check(
    roster.replace("beta", with: "delta") == .success,
    "replacing an existing tag with a new one should succeed"
)

var rosterForDuplicate = Roster(items: ["alpha", "beta", "gamma"])
if case .trapped = rosterForDuplicate.replace("alpha", with: "beta") {
} else {
    check(false, "replacing with a tag that already exists elsewhere should trap")
}

var rosterForMissing = Roster(items: ["alpha", "beta", "gamma"])
if case .trapped = rosterForMissing.replace("missing", with: "delta") {
} else {
    check(false, "replacing a tag that isn't present should trap")
}

var ledger = Ledger(roster: Roster(items: ["one", "two", "three"]), values: [1, 2, 3])
check(
    ledger.replaceLabel("two", with: "four", value: 4) == .success,
    "replacing an existing label with a new one should succeed"
)

var ledgerForDuplicate = Ledger(roster: Roster(items: ["one", "two", "three"]), values: [1, 2, 3])
if case .trapped = ledgerForDuplicate.replaceLabel("one", with: "two", value: 9) {
} else {
    check(false, "replacing with a label that already exists elsewhere should trap")
}

var ledgerForMissing = Ledger(roster: Roster(items: ["one", "two", "three"]), values: [1, 2, 3])
if case .trapped = ledgerForMissing.replaceLabel("missing", with: "four", value: 9) {
} else {
    check(false, "replacing a label that isn't present should trap")
}

print("OK: main.swift")
