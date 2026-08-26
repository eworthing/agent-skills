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
decoder.onFrame { frame in
    recorded.append(frame)
    if frame.body.contains("BOOM") {
        throw DecodeConsumerError.rejected
    }
}

// A counted frame split across two feed() calls, exercising the shared
// buffering layer's leftover-bytes bookkeeping.
decoder.feed("#2\nal")
decoder.feed("pha\nbeta\n")
check(recorded == [Frame(kind: .counted, body: ["alpha", "beta"])], "a counted frame should decode its exact body, in order")

// An unbounded frame terminated by ".".
recorded = []
decoder.feed("#*\nfirst\nsecond\n.\n")
check(recorded == [Frame(kind: .unbounded, body: ["first", "second"])], "an unbounded frame should read until its terminator")

// Error-latch: once the consumer throws for a delivered frame, no later
// frame may reach it, no matter how much well-formed input follows.
recorded = []
decoder.feed("#1\nBOOM\n")
check(recorded == [Frame(kind: .counted, body: ["BOOM"])], "the frame that triggers the throw is itself still delivered")
decoder.feed("#1\nok\n")
decoder.feed("#1\nok2\n")
check(recorded.count == 1, "no frame after the throw should ever reach the consumer")

print("OK: main.swift")
