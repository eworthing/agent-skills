// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py the same three uniform probe entry points across all
// five variants. `count` is private here, so unlike the unsynchronized
// and unchecked-marker variants, this adapter cannot reach in and split
// a read from a write -- increment() is the only way to touch the
// counter at all, which is the point.

func probeFinalCountAfterTwoLogicalCallers() async -> Int {
    let counter = HitCounter()
    counter.increment()
    counter.increment()
    return counter.currentCount
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
