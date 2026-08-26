// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py the same three uniform probe entry points across all
// five variants. Every call here needs await -- this variant's real API
// genuinely requires it, which is exactly the topology cost this pack's
// unrelated_call_site_stays_callable oracle measures separately.

func probeFinalCountAfterTwoLogicalCallers() async -> Int {
    let counter = HitCounter()
    await counter.increment()
    await counter.increment()
    return await counter.currentCount
}

func probeOrdinaryTwoCallsGiveTwo() async -> Int {
    let counter = HitCounter()
    await recordPageView(counter)
    await recordAPIHit(counter)
    return await counter.currentCount
}

func probeInvariantViolated() async -> Bool {
    false // no claimed invariant exists in this variant to violate
}
