// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// command_word.swift PLUS that variant's own grader-only probe_adapter.swift
// (copied to a scratch file literally named main.swift -- swiftc only
// allows top-level statements in a file with that exact name, and each
// variant already ships its own candidate-visible main.swift, so this is
// never compiled against a variant's own main.swift).
//
// Every variant's candidate-visible module exposes the same three decode
// functions -- ticketNumber(from:), laneNumber(from:), tierLevel(from:) --
// taking one UInt64 word, which is a legitimate, wire-shaped signature in
// every variant regardless of its internals. Encoding is NOT uniform
// across variants on purpose: the raw-shaped variants build a word from
// three bare integers, the typed variants build one from a
// RoutingAssignment. probeMakeWord(_:_:_:) is each variant's own grader-
// only adapter reconciling that difference into one call shape this probe
// can drive -- see probe_adapter.swift in each variant's directory.
//
// Usage: probe <ticket> <lane> <tier>
// Packs the three inputs into a command word via that variant's own
// probeMakeWord, then immediately reads them back out via that variant's
// own ticketNumber/laneNumber/tierLevel, and prints:
//   word:<UInt64> ticket:<UInt64> lane:<UInt64> tier:<UInt64>

import Foundation

let args = CommandLine.arguments
guard args.count == 4,
    let ticket = UInt64(args[1]),
    let lane = UInt64(args[2]),
    let tier = UInt64(args[3])
else {
    print("usage: probe <ticket> <lane> <tier>")
    exit(2)
}

let word = probeMakeWord(ticket, lane, tier)
print(
    "word:\(word) ticket:\(ticketNumber(from: word)) "
        + "lane:\(laneNumber(from: word)) tier:\(tierLevel(from: word))"
)
