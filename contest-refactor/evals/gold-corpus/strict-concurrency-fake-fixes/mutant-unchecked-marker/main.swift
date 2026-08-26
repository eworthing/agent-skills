// hit_counter's own bundled test suite.
//
// Run: swiftc hit_counter.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

let counter = HitCounter()
recordPageView(counter)
recordAPIHit(counter)
check(counter.currentCount == 2, "two ordinary calls should both be recorded")
check(counter.statusLine() == "hits recorded: 2", "status line should reflect the count")

print("OK: main.swift")
