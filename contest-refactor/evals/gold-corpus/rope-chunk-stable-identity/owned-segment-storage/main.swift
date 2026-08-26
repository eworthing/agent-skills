// text_spool's own bundled test suite (this variant).
//
// Run: swiftc text_spool.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

var spool = Spool(chunkSize: 8, chunks: ["chunk000", "chunk001", "chunk002"])
check(spool.chunkTexts.joined() == "chunk000chunk001chunk002", "initial chunk text should join in order")

spool.replaceChunk(at: 1, with: "NEWVALUE")
check(spool.chunkTexts.joined() == "chunk000NEWVALUEchunk002", "replacing a chunk should update its content in place")
check(spool.chunkTexts[0] == "chunk000", "an untouched chunk's content should be unaffected by a neighboring replace")
check(spool.chunkTexts[2] == "chunk002", "an untouched chunk's content should be unaffected by a neighboring replace")

var before = Spool(chunkSize: 8, chunks: ["aaaaaaaa", "bbbbbbbb", "cccccccc", "dddddddd"])
let after0 = before
var after = after0
after.replaceChunk(at: 2, with: "zzzzzzzz")
let report = diffSpools(before, after)
check(report.comparedUnits >= 0, "a diff should never report a negative amount of work")
check(report.changedIndices.contains(2), "a diff after a replace should at least flag the replaced position")

print("OK: main.swift")
