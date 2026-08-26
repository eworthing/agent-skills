// A Spool holding an ordered run of text chunks, where each chunk owns its
// own small storage object carrying a stable identity token -- the same
// shape as the accepted design. Copying a chunk's value is meant to share
// that storage (and its token); only replacing a chunk's content should
// allocate fresh storage with a fresh token.
//
// BUG (deliberately introduced by this variant): the chunk list is rebuilt
// from scratch, wrapping every chunk's text in brand-new storage, every
// single time it is read -- not only when a chunk's content actually
// changes. A read should be free and identity-preserving; here it silently
// costs every chunk its identity, even the ones nothing touched.

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
/// somewhere in the old spool -- the same lookup the accepted design uses.
/// The defect lives entirely in how those tokens get produced, not in this
/// comparison.
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
