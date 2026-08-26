// A Spool holding an ordered run of text chunks, where each chunk owns its
// own small storage object carrying a stable identity token. Copying a
// chunk's value shares that storage (and its token); only replacing a
// chunk's content allocates fresh storage with a fresh token. A diff can
// therefore tell "this chunk is the same one I last saw" by comparing
// tokens alone -- without reading a single byte of its text -- and only
// has to read the chunks whose tokens don't turn up in the old set.

struct DiffReport {
    var changedIndices: [Int]
    var comparedUnits: Int
}

private final class SegmentStorage {
    var text: String
    let identity: Int

    private static var nextIdentity = 0

    init(text: String) {
        self.text = text
        SegmentStorage.nextIdentity += 1
        self.identity = SegmentStorage.nextIdentity
    }
}

private struct Segment {
    var storage: SegmentStorage
    var text: String { storage.text }
    var identity: Int { storage.identity }

    init(text: String) { storage = SegmentStorage(text: text) }
}

struct Spool {
    private var segments: [Segment]

    init(chunkSize: Int, chunks: [String]) {
        segments = chunks.map { Segment(text: $0) }
    }

    var chunkTexts: [String] { segments.map(\.text) }

    fileprivate var chunkIdentities: [Int] { segments.map(\.identity) }

    mutating func replaceChunk(at index: Int, with newText: String) {
        segments[index] = Segment(text: newText) // a fresh chunk earns a fresh identity
    }
}

/// Reports a chunk as changed unless its identity token was already present
/// somewhere in the old spool -- a lookup, not a positional comparison, so
/// that a chunk which merely moved is not mistaken for a new one.
func diffSpools(_ old: Spool, _ new: Spool) -> DiffReport {
    let oldIdentitySet = Set(old.chunkIdentities)
    let newChunks = new.chunkTexts
    let newIdentities = new.chunkIdentities
    var changed: [Int] = []
    var compared = 0
    for i in 0..<newChunks.count {
        if oldIdentitySet.contains(newIdentities[i]) {
            continue // identity says this exact chunk already existed -- never touch its bytes
        }
        changed.append(i)
        compared += newChunks[i].count
    }
    return DiffReport(changedIndices: changed, comparedUnits: compared)
}
