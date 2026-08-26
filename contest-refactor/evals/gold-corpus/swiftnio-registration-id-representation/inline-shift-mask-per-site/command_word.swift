// Packs three small fields -- a job ticket number, the belt lane it is
// routed to, and a handling-priority tier -- into one 64-bit word,
// because the warehouse's conveyor controller only accepts a single
// machine word per routing command.
//
// Layout (bit 0 is the low bit):
//   bits 24-63 (40 bits): ticket number
//   bits  8-23 (16 bits): belt lane
//   bits  0-7  ( 8 bits): handling tier
//
// Every function below repeats the same shift-and-mask arithmetic by
// hand. It works, but the bit layout is duplicated at each call site --
// change the layout and every one of these functions has to change too.

func makeCommandWord(ticket: UInt64, lane: UInt64, tier: UInt64) -> UInt64 {
    ((ticket & 0xFF_FFFF_FFFF) << 24) | ((lane & 0xFFFF) << 8) | (tier & 0xFF)
}

func ticketNumber(from word: UInt64) -> UInt64 {
    (word >> 24) & 0xFF_FFFF_FFFF
}

func laneNumber(from word: UInt64) -> UInt64 {
    (word >> 8) & 0xFFFF
}

func tierLevel(from word: UInt64) -> UInt64 {
    word & 0xFF
}
