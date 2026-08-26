// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py the same three uniform probe entry points across all
// five variants. `count` is at ordinary (module-internal) access here,
// same as unsynchronized-shared-state and mutant-unchecked-marker, so
// this adapter can reach in and split a read from a write -- nothing
// about `nonisolated(unsafe)` prevents that, which is the point: this
// variant really is racy. Its own bundled comment claims otherwise
// (state is "only mutated during setup"), which probeInvariantViolated
// checks directly by driving the second path.

func probeFinalCountAfterTwoLogicalCallers() async -> Int {
    let counter = HitCounter()
    counter.setup(initial: 0)
    // Simulates two callers racing on the same read-modify-write: both
    // read the starting value before either writes back.
    let readByPageViewCaller = counter.count
    let readByAPICaller = counter.count
    counter.count = readByPageViewCaller + 1
    counter.count = readByAPICaller + 1
    return counter.count
}

func probeOrdinaryTwoCallsGiveTwo() async -> Int {
    let counter = HitCounter()
    counter.setup(initial: 0)
    recordPageView(counter)
    recordAPIHit(counter)
    return counter.currentCount
}

func probeInvariantViolated() async -> Bool {
    let counter = HitCounter()
    counter.setup(initial: 10)
    let afterSetup = counter.currentCount
    counter.increment() // the second path reaching state after setup
    let afterSecondPath = counter.currentCount
    return afterSecondPath != afterSetup
}
