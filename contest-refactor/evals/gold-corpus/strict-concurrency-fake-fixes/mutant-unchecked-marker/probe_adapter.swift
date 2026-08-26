// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py the same three uniform probe entry points across all
// five variants.

func probeFinalCountAfterTwoLogicalCallers() async -> Int {
    let counter = HitCounter()
    // Simulates two callers racing on the same read-modify-write: both
    // read the starting value before either writes back. The Sendable
    // conformance on HitCounter does not change that `count` is a
    // plain, internally-accessible property here -- nothing stops this
    // from being expressed.
    let readByPageViewCaller = counter.count
    let readByAPICaller = counter.count
    counter.count = readByPageViewCaller + 1
    counter.count = readByAPICaller + 1
    return counter.count
}

func probeOrdinaryTwoCallsGiveTwo() async -> Int {
    let counter = HitCounter()
    recordPageView(counter)
    recordAPIHit(counter)
    return counter.currentCount
}

func probeInvariantViolated() async -> Bool {
    false // no claimed invariant exists in this variant to violate
}
