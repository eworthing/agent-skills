// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py one uniform encode entry point, probeMakeWord, across
// all four variants, without requiring the variants themselves to share
// a public encode signature.
//
// This variant's own construction path is fully typed --
// RoutingAssignment's own initializer, taking TicketID/BeltLane/
// HandlingTier -- and that is the path this adapter drives; it exists
// only to hand the grader's probe binary raw integers to call it with,
// not to give a candidate a way around the typed construction path.
func probeMakeWord(_ ticket: UInt64, _ lane: UInt64, _ tier: UInt64) -> UInt64 {
    let assignment = RoutingAssignment(
        ticket: TicketID(rawValue: ticket)!,
        lane: BeltLane(rawValue: UInt16(lane)),
        tier: HandlingTier(rawValue: UInt8(tier))
    )
    return ConveyorCommandWord(assignment).rawValue
}
