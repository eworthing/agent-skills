// A Spool holding an ordered run of text chunks, where each chunk owns its
// own small storage object carrying an identity token.
//
// The chunk list is materialised fresh on each read, wrapping every
// chunk's text in its own storage at that point. Keeping the read path
// uniform this way means there is only one place storage is ever built,
// so a chunk's storage can never be left over from an earlier state of
// the spool or shared between two spools by accident.

struct DiffReport {
    var changedIndices: [Int]
    var comparedUnits: Int
}

private final class SegmentStorage {
    let text: String
    let identity: Int

    private static var nextIdentity = 0

    init(text: String) {
        self.text = text
        SegmentStorage.nextIdentity += 1
        self.identity = SegmentStorage.nextIdentity
    }
}

struct Spool {
    private var backingText: [String]

    init(chunkSize: Int, chunks: [String]) {
        backingText = chunks
    }

    var chunkTexts: [String] { backingText }

    /// Rebuilds storage for every chunk on every access, which hands out a
    /// brand-new identity token each time -- even for a chunk whose text
    /// never changed.
    fileprivate var chunkIdentities: [Int] {
        backingText.map { SegmentStorage(text: $0).identity }
    }

    mutating func replaceChunk(at index: Int, with newText: String) {
        backingText[index] = newText
    }
}

/// Reports a chunk as changed unless its identity token was already present
/// somewhere in the old spool, so a chunk that merely moved position is not
/// reported as an edit.
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
