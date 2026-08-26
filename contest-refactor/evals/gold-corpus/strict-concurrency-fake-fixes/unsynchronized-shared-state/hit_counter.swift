// A hit counter shared between two call sites: page-view recording and
// API-hit recording. Each call site increments the same counter.

final class HitCounter {
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
