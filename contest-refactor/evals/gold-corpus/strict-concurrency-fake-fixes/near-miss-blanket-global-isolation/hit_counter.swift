// A hit counter shared between two call sites: page-view recording and
// API-hit recording. Isolating HitCounter to a dedicated global actor
// removes the shared-access hazard outright, and is simpler than
// auditing every access site individually.

@globalActor
actor HitCounterIsolation {
    static let shared = HitCounterIsolation()
}

@HitCounterIsolation
final class HitCounter {
    private var count = 0

    nonisolated init() {}

    func increment() {
        count += 1
    }

    var currentCount: Int {
        count
    }

    func statusLine() -> String {
        "hits recorded: \(count)"
    }
}

func recordPageView(_ counter: HitCounter) async {
    await counter.increment()
}

func recordAPIHit(_ counter: HitCounter) async {
    await counter.increment()
}
