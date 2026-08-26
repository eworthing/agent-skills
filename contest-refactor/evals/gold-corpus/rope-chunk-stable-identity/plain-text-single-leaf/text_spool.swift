// A Spool holding an ordered run of fixed-width text chunks, backed by one
// plain string per leaf. Chunks are not separately stored objects here --
// they are substrings recomputed on demand by slicing the leaf's text at
// fixed intervals. A leaf carries exactly one identity token (its own
// revision counter), shared by every chunk sliced out of it, because there
// is no per-chunk storage to hang a separate token on: the only thing that
// can be said to have "changed or not" is the leaf as a whole.

struct DiffReport {
    var changedIndices: [Int]
    var comparedUnits: Int
}

private struct Leaf {
    var text: String
    var revision: Int
}

struct Spool {
    private var leaf: Leaf
    private let chunkSize: Int

    init(chunkSize: Int, chunks: [String]) {
        self.chunkSize = chunkSize
        self.leaf = Leaf(text: chunks.joined(), revision: 0)
    }

    var chunkTexts: [String] {
        var result: [String] = []
        var idx = leaf.text.startIndex
        while idx < leaf.text.endIndex {
            let end = leaf.text.index(idx, offsetBy: chunkSize, limitedBy: leaf.text.endIndex) ?? leaf.text.endIndex
            result.append(String(leaf.text[idx..<end]))
            idx = end
        }
        return result
    }

    /// Every chunk sliced from this leaf reports the same identity token --
    /// the leaf's own revision -- because chunk boundaries here are just
    /// arithmetic over one shared string, not separately owned storage.
    fileprivate var chunkIdentities: [Int] {
        Array(repeating: leaf.revision, count: chunkTexts.count)
    }

    mutating func replaceChunk(at index: Int, with newText: String) {
        var text = leaf.text
        let start = text.index(text.startIndex, offsetBy: index * chunkSize)
        let end = text.index(start, offsetBy: chunkSize, limitedBy: text.endIndex) ?? text.endIndex
        text.replaceSubrange(start..<end, with: newText)
        leaf.text = text
        leaf.revision += 1 // the WHOLE leaf earns a new identity, not just this one chunk
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
            continue
        }
        changed.append(i)
        compared += newChunks[i].count
    }
    return DiffReport(changedIndices: changed, comparedUnits: compared)
}
