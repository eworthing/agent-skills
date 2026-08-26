// pipe_support's own bundled test suite (this variant).
//
// Run: swiftc pipe_support.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

let notReady = Pipe()
check(
    !notReady.write(1),
    "a write issued before activation should be rejected"
)

let ready = Pipe()
ready.activate()
check(ready.write(1), "a write issued after activation should be accepted")
ready.flush()
check(ready.emitted == [1], "a flushed write should be emitted")

print("OK: main.swift")
