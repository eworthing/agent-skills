// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py the same three uniform probe entry points across all
// five variants. `async` on all three keeps the signature uniform even
// though this variant never suspends -- the blanket-global-isolation
// variant's real API genuinely requires await, and oracle_probe.swift
// drives all five variants through one shared CLI.

func probeFinalCountAfterTwoLogicalCallers() async -> Int {
    let counter = HitCounter()
    // Simulates two callers racing on the same read-modify-write: both
    // read the starting value before either writes back, exactly what
    // an unsynchronized increment allows under real concurrent access.
    // `count` is a plain, internally-accessible property in this
    // variant, so nothing stops this from being expressed.
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
