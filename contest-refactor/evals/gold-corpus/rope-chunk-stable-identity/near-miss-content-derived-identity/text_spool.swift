// A Spool holding an ordered run of text chunks, where each chunk is still
// its own value -- but its "identity" is derived from its own content (a
// hash of its text) rather than from a separate piece of storage. This
// looks like it gives a diff the same cheap identity comparison as owning
// storage would, while being simpler to write: no storage object, no
// counter to allocate from. It also means a chunk's identity depends on
// nothing but the chunk itself, so two spools built by different routes
// agree about which chunks they share without having to coordinate on a
// counter first.

struct DiffReport {
    var changedIndices: [Int]
    var comparedUnits: Int
}

private struct Segment {
    var text: String
    var identity: Int { text.hashValue }
}

struct Spool {
    private var segments: [Segment]

    init(chunkSize: Int, chunks: [String]) {
        segments = chunks.map { Segment(text: $0) }
    }

    var chunkTexts: [String] { segments.map(\.text) }

    mutating func replaceChunk(at index: Int, with newText: String) {
        segments[index] = Segment(text: newText)
    }
}

/// Reports a chunk as changed unless its identity token was already present
/// somewhere in the old spool. Because that token has to be derived from
/// the chunk's own text, every chunk on both sides has to be read in full
/// just to compute it -- and two chunks with equal text produce the same
/// token, so an edit that lands on someone else's existing text is
/// indistinguishable from that text having been there all along.
func diffSpools(_ old: Spool, _ new: Spool) -> DiffReport {
    var compared = 0
    var oldIdentitySet: Set<Int> = []
    for text in old.chunkTexts {
        compared += text.count // computing the identity means reading every byte, for every old chunk
        oldIdentitySet.insert(Segment(text: text).identity)
    }
    let newChunks = new.chunkTexts
    var changed: [Int] = []
    for i in 0..<newChunks.count {
        compared += newChunks[i].count // and again for every new chunk, to compute its identity
        let identity = Segment(text: newChunks[i]).identity
        if oldIdentitySet.contains(identity) {
            continue
        }
        changed.append(i)
    }
    return DiffReport(changedIndices: changed, comparedUnits: compared)
}
