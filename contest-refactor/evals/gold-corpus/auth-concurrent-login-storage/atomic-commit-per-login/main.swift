// login_registry's own bundled test suite.
//
// Run: swiftc login_registry.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

let registry = LoginRegistry()

let pendingPrimary = registry.beginStore(kind: .primary, value: "alice-token")
registry.commitStore(pendingPrimary)
check(registry.retrieve(kind: .primary) == "alice-token", "a stored primary login should be retrievable")

let pendingSecondary = registry.beginStore(kind: .secondary, value: "bob-token")
registry.commitStore(pendingSecondary)
check(registry.retrieve(kind: .secondary) == "bob-token", "a stored secondary login should be retrievable")

check(registry.retrieve(kind: .primary) == "alice-token", "storing a second kind should not disturb the first")
check(
    LoginRegistry().retrieve(kind: .primary) == nil,
    "a kind that was never stored should have nothing retrievable"
)

print("OK: main.swift")
