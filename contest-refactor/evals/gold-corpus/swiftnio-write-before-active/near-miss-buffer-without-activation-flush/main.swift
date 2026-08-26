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

let early = Pipe()
check(early.write(1), "a write issued before activation should be accepted")
early.activate()
early.flush()
check(early.emitted == [1], "a write from before activation should still reach emitted once flushed")

let ready = Pipe()
ready.activate()
check(ready.write(2), "a write issued after activation should be accepted")
ready.flush()
check(ready.emitted == [2], "a flushed write should be emitted")

let ordered = Pipe()
ordered.write(1)
ordered.write(2)
ordered.write(3)
ordered.activate()
ordered.flush()
check(ordered.emitted == [1, 2, 3], "writes should emerge in the order they were issued")

print("OK: main.swift")
