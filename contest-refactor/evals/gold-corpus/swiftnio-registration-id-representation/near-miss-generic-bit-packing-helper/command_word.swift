// Packs three small fields -- a job ticket number, the belt lane it is
// routed to, and a handling-priority tier -- into one 64-bit word,
// because the warehouse's conveyor controller only accepts a single
// machine word per routing command.
//
// PackingKit is a small, generic bit-range packer: it knows nothing
// about tickets, lanes, or tiers, only about shifting and masking within
// a word. Each caller below names the bit range it wants, so the actual
// shift-and-mask arithmetic exists in exactly one place instead of being
// repeated at every call site.

enum PackingKit {
    static func packField(_ value: UInt64, shift: Int, bits: Int) -> UInt64 {
        let mask: UInt64 = (1 << bits) - 1
        return (value & mask) << shift
    }

    static func unpackField(_ word: UInt64, shift: Int, bits: Int) -> UInt64 {
        let mask: UInt64 = (1 << bits) - 1
        return (word >> shift) & mask
    }
}

func makeCommandWord(ticket: UInt64, lane: UInt64, tier: UInt64) -> UInt64 {
    PackingKit.packField(ticket, shift: 24, bits: 40)
        | PackingKit.packField(lane, shift: 8, bits: 16)
        | PackingKit.packField(tier, shift: 0, bits: 8)
}

func ticketNumber(from word: UInt64) -> UInt64 {
    PackingKit.unpackField(word, shift: 24, bits: 40)
}

func laneNumber(from word: UInt64) -> UInt64 {
    PackingKit.unpackField(word, shift: 8, bits: 16)
}

func tierLevel(from word: UInt64) -> UInt64 {
    PackingKit.unpackField(word, shift: 0, bits: 8)
}
