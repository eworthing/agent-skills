// Packs three small fields -- a job ticket number, the belt lane it is
// routed to, and a handling-priority tier -- into one 64-bit word,
// because the warehouse's conveyor controller only accepts a single
// machine word per routing command.
//
// TicketID, BeltLane, and HandlingTier are distinct types: the compiler
// will not let a caller pass one where another is expected. Shifting and
// masking exist in exactly one place, ConveyorCommandWord, because that
// is the only reason a packed word exists at all -- the conveyor
// controller's wire protocol demands it. Nothing else in this file talks
// about bits; everything else talks about tickets, lanes, and tiers.

struct TicketID {
    let rawValue: UInt64

    init?(rawValue: UInt64) {
        guard rawValue <= 0xFF_FFFF_FFFF else { return nil }
        self.rawValue = rawValue
    }
}

struct BeltLane {
    let rawValue: UInt16

    init(rawValue: UInt16) {
        self.rawValue = rawValue
    }
}

struct HandlingTier {
    let rawValue: UInt8

    init(rawValue: UInt8) {
        self.rawValue = rawValue
    }
}

struct RoutingAssignment {
    let ticket: TicketID
    let lane: BeltLane
    let tier: HandlingTier
}

/// The only place in this file that shifts or masks a bit. It exists
/// solely because the conveyor controller's wire protocol is one 64-bit
/// word; nothing about tickets, lanes, or tiers requires it internally.
struct ConveyorCommandWord {
    let rawValue: UInt64

    init(rawValue: UInt64) {
        self.rawValue = rawValue
    }

    init(_ assignment: RoutingAssignment) {
        rawValue = (UInt64(assignment.ticket.rawValue) << 24)
            | (UInt64(assignment.lane.rawValue) << 8)
            | UInt64(assignment.tier.rawValue)
    }

    var assignment: RoutingAssignment {
        // Force-unwrap is total here, not a shortcut: masking with
        // 0xFF_FFFF_FFFF can only ever produce a value in TicketID's
        // valid 40-bit range, so this initializer can never return nil.
        RoutingAssignment(
            ticket: TicketID(rawValue: (rawValue >> 24) & 0xFF_FFFF_FFFF)!,
            lane: BeltLane(rawValue: UInt16((rawValue >> 8) & 0x7FFF)),
            tier: HandlingTier(rawValue: UInt8(rawValue & 0xFF))
        )
    }
}

func ticketNumber(from word: UInt64) -> UInt64 {
    ConveyorCommandWord(rawValue: word).assignment.ticket.rawValue
}

func laneNumber(from word: UInt64) -> UInt64 {
    UInt64(ConveyorCommandWord(rawValue: word).assignment.lane.rawValue)
}

func tierLevel(from word: UInt64) -> UInt64 {
    UInt64(ConveyorCommandWord(rawValue: word).assignment.tier.rawValue)
}
