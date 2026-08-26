// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// text_spool.swift in turn (never against main.swift -- two files with
// top-level statements can't coexist in one swiftc invocation), so this is
// the one place `Spool` and `diffSpools` get exercised uniformly across
// variants whose internals differ.
//
// Usage:
//   probe replace-and-diff <chunkSize> <items,comma,separated> <replaceIndex> <newText>
//
// Builds a spool from <items>, copies it, replaces the chunk at
// <replaceIndex> in the copy with <newText>, diffs the two, and prints
// three lines: the resulting full text, the changed-chunk indices, and the
// instrumented compared-units count -- everything oracles.py needs to
// check diff granularity, content correctness, and comparison cost from
// one probe invocation.

import Foundation

let args = CommandLine.arguments
guard args.count == 6, args[1] == "replace-and-diff",
    let chunkSize = Int(args[2]),
    let replaceIndex = Int(args[4])
else {
    print("usage: probe replace-and-diff <chunkSize> <items,comma,separated> <replaceIndex> <newText>")
    exit(2)
}

let items = args[3].split(separator: ",", omittingEmptySubsequences: false).map(String.init)
let newText = args[5]

let oldSpool = Spool(chunkSize: chunkSize, chunks: items)
var newSpool = oldSpool
newSpool.replaceChunk(at: replaceIndex, with: newText)

let report = diffSpools(oldSpool, newSpool)
let changedStr =
    report.changedIndices.isEmpty
    ? "none" : report.changedIndices.map(String.init).joined(separator: ",")

print("final: \(newSpool.chunkTexts.joined())")
print("changed: \(changedStr)")
print("compared: \(report.comparedUnits)")
