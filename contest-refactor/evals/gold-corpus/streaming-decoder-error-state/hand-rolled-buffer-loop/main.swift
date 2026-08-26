// frame_decoder's own bundled test suite (this variant).
//
// Run: swiftc frame_decoder.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

var recorded: [Frame] = []
let decoder = FrameDecoder()
decoder.onFrame { frame in recorded.append(frame) }

// A counted frame split across two feed() calls, exercising the
// leftover-bytes bookkeeping.
decoder.feed("#2\nal")
decoder.feed("pha\nbeta\n")
check(recorded == [Frame(kind: .counted, body: ["alpha", "beta"])], "a counted frame should decode its exact body, in order")

// An unbounded frame terminated by ".".
recorded = []
decoder.feed("#*\nfirst\nsecond\n.\n")
check(recorded == [Frame(kind: .unbounded, body: ["first", "second"])], "an unbounded frame should read until its terminator")

print("OK: main.swift")
