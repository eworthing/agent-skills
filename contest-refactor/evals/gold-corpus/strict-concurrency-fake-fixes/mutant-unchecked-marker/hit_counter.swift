// A hit counter shared between two call sites: page-view recording and
// API-hit recording. HitCounter conforms to Sendable so it can be
// shared safely across call sites.

final class HitCounter: @unchecked Sendable {
    var count: Int = 0

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

func recordPageView(_ counter: HitCounter) {
    counter.increment()
}

func recordAPIHit(_ counter: HitCounter) {
    counter.increment()
}
