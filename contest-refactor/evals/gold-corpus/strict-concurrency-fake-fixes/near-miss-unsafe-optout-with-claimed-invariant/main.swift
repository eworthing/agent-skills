// hit_counter's own bundled test suite (this variant).
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
counter.setup(initial: 10)
recordPageView(counter)
recordAPIHit(counter)
check(counter.currentCount == 12, "setup value plus two ordinary calls")
check(counter.statusLine() == "hits recorded: 12", "status line should reflect the count")

print("OK: main.swift")
