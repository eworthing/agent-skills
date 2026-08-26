// platform_support's own bundled test suite (this variant).
//
// Run: swiftc platform_support.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

check(
    isPotentiallyAffected(platform: .anchor, version: Version(major: 6, minor: 0)),
    "an old anchor runtime should still report affected"
)
check(
    !isPotentiallyAffected(platform: .anchor, version: Version(major: 7, minor: 0)),
    "an anchor runtime at the threshold should report unaffected"
)
check(
    !isPotentiallyAffected(platform: .openfield, version: Version(major: 1, minor: 0)),
    "an unrelated platform family should never report affected"
)

print("OK: main.swift")
