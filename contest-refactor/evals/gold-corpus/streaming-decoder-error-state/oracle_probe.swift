// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// frame_decoder.swift in turn (copied to a scratch file literally named
// main.swift -- swiftc only allows top-level statements in a file with
// that exact name -- never the variant's own main.swift).
//
// Usage: probe <input>, a single argument whose embedded newline
// characters separate individual protocol lines. Each line is fed to the
// decoder as its own chunk, WITH its newline, so the shared/hand-rolled
// buffering boundary is exercised on every line rather than only once.
//
// The consumer records every frame the decoder delivers, in order, and
// throws once whenever a delivered frame's body contains the sentinel
// line "BOOM" -- modelling the downstream consumer error this pack's
// error-latch exists to contain.
//
// Prints:
//   frames:<count>
//   <frame-description>   (one per line, in delivery order)
// where a frame description is `kind:[body|joined|by|pipes]`.

import Foundation

let args = CommandLine.arguments
guard args.count == 2 else {
    print("usage: probe <input>  (lines separated by embedded newlines)")
    exit(2)
}

let lines = args[1].split(separator: "\n", omittingEmptySubsequences: true).map(String.init)

let decoder = FrameDecoder()
var recorded: [Frame] = []
decoder.onFrame { frame in
    recorded.append(frame)
    if frame.body.contains("BOOM") {
        throw DecodeConsumerError.rejected
    }
}

for line in lines {
    decoder.feed(line + "\n")
}

print("frames:\(recorded.count)")
for frame in recorded {
    print(frame.description)
}
