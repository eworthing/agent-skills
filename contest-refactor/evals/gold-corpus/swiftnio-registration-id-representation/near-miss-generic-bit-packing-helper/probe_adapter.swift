// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py one uniform encode entry point, probeMakeWord, across
// all four variants, without requiring the variants themselves to share
// a public encode signature -- see provenance.json's expected_judgment
// for why a shared candidate-visible encode signature was itself the
// defect in an earlier draft of this pack.
//
// This variant's own makeCommandWord IS the raw, untyped encode API a
// candidate sees, so this adapter is a pure pass-through.

func probeMakeWord(_ ticket: UInt64, _ lane: UInt64, _ tier: UInt64) -> UInt64 {
    makeCommandWord(ticket: ticket, lane: lane, tier: tier)
}
